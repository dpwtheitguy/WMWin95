#!/usr/bin/env python3
"""Volume tray preference, live controls and recording-state isolation."""
import argparse,json,sys,time,threading,subprocess,os,statistics,copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tests')]

def check_isolated_audio(output):
    from win95lx.control_panel.audio_preferences import PulseAudio
    from win95lx.control_panel.audio_updates import PlaybackUpdates
    import queue
    with TemporaryDirectory(prefix='win95lx-pulse-') as directory:
        root=Path(directory);socket=root/'native';runtime=root/'runtime';runtime.mkdir(mode=0o700);state=root/'state';state.mkdir()
        env={**os.environ,'PULSE_RUNTIME_PATH':str(runtime),'PULSE_STATE_PATH':str(state),'XDG_RUNTIME_DIR':str(runtime)}
        log=(output/'isolated-pulse.log').open('w')
        process=subprocess.Popen(['pulseaudio','-n','--daemonize=no','--exit-idle-time=-1','--use-pid-file=no','--log-target=stderr','--load=module-native-protocol-unix socket='+str(socket)+' auth-anonymous=1','--load=module-null-sink sink_name=win95lx_qa channels=2 channel_map=front-left,front-right'],env=env,stdout=log,stderr=log)
        def run(*args):return subprocess.run(['pactl','--server=unix:'+str(socket),*args],check=True,capture_output=True,text=True,timeout=5,env=env).stdout
        session=None
        try:
            until=time.monotonic()+5
            while time.monotonic()<until:
                if process.poll()is not None:raise RuntimeError('Private audio server exited; inspect isolated-pulse.log')
                if socket.exists():
                    try:run('info');break
                    except subprocess.SubprocessError:pass
                time.sleep(.02)
            else:raise RuntimeError('Private audio server did not start')
            backend=PulseAudio(run);before=backend.snapshot();target=before['playback'];assert target=='win95lx_qa'
            run('set-sink-volume',target,'65536','32768');run('set-sink-mute',target,'1');recording=backend.snapshot()['devices']['sources'];defaults=(run('get-default-sink'),run('get-default-source'))
            q=queue.Queue();messages=[];session=PlaybackUpdates(backend,q.put,messages.append);assert session.wait_idle(5)
            for value in(0,100,23,84,17,100):session.submit(volume=value);assert session.wait_idle(5)
            session.submit(volume=73,muted=False);session.close();assert session.wait_closed(5);assert not session.worker.is_alive()
            actual=backend.snapshot();endpoint=next(d for d in actual['devices']['sinks']if d.name==target)
            assert endpoint.channels==(47841,23920)and not endpoint.muted
            assert actual['devices']['sources']==recording
            assert defaults==(run('get-default-sink'),run('get-default-source'))
            # A second owned endpoint proves default changes do not redirect a
            # queued intent to a different device. No user defaults are touched.
            other=run('load-module','module-null-sink','sink_name=win95lx_qa_other').strip()
            q=queue.Queue();messages=[];session=PlaybackUpdates(backend,q.put,messages.append);assert session.wait_idle(5)
            old_before=backend.inventory()['sinks'];run('set-default-sink','win95lx_qa_other');session.submit(volume=1);assert session.wait_closed(5)
            while not q.empty():q.get_nowait()()
            assert messages[-1].error and backend.inventory()['sinks']==old_before
            run('set-default-sink',target);run('unload-module',other)
            # A vanished server is a real failure path, not a fake callback.
            q=queue.Queue();messages=[];session=PlaybackUpdates(backend,q.put,messages.append);assert session.wait_idle(5)
            process.terminate();process.wait(timeout=3);session.submit(volume=1);assert session.wait_closed(5)
            while not q.empty():q.get_nowait()()
            assert messages[-1].error and messages[-1].endpoint is None
            return {'server':'Owned private PulseAudio daemon and disposable null sinks; no user server connection','channels':endpoint.channels,'muted':endpoint.muted,'recording_and_defaults_unchanged':True,'default_change_rejected':True,'server_failure_reported':True,'worker_exited':True}
        finally:
            if session:session.close();session.wait_closed(5)
            if process.poll()is None:process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--real-audio',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    display=Gdk.Display.get_default();assert display and 'X11' in type(display).__name__ and display.get_name()==os.environ.get('DISPLAY'),'Use an isolated matching X11 display.'
    from win95lx.apps.volume_popup import VolumePopup
    from win95lx.control_panel.audio_preferences import AudioPreferences,PulseAudio
    from win95lx.apps.multimedia import MultimediaWindow
    from test_audio_preferences import FakePulse
    from check_menu_seams import flush_draws
    def settle(popup):
        until=time.monotonic()+5
        while time.monotonic()<until:
            flush_draws(Gtk)
            if popup.updates.wait_idle(.001):flush_draws(Gtk);return
            time.sleep(.002)
        raise AssertionError('Audio worker did not settle')
    timings={};sessions=[]
    with TemporaryDirectory() as directory,patch('pathlib.Path.home',return_value=Path(directory)):
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        def render():
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,800,600);shell.draw(shell.area,cairo.Context(surface));return surface
        try:
            render();assert not any(action[0]=='volume-tray-open' for *_,action in shell.hits)
            fake=FakePulse();backend=PulseAudio(fake.run);window=MultimediaWindow(shell,backend);window.show_all();flush_draws(Gtk)
            window.action(('tray',));assert not shell.audio_preferences.tray;window.action(('apply',));assert shell.audio_preferences.tray
            surface=render();surface.write_to_png(str(a.output/'tray-enabled.png'))
            hit=next(hit for hit in shell.hits if hit[4][0]=='volume-tray-open');assert hit[2:4]==(22,22)
            shell.display_preferences=replace(shell.display_preferences,tray=True);shell.keyboard_preferences=None;render()
            volume=next(hit for hit in shell.hits if hit[4][0]=='volume-tray-open');display=next(hit for hit in shell.hits if hit[4][0]=='display-tray-open');assert volume[0]+volume[2]<=display[0]
            recording=fake.rows['sources'][0]['volume'].copy();default_source=fake.default['source']
            popup=VolumePopup(shell,volume[0],backend);sessions.append(popup.updates);settle(popup);assert popup.get_window().get_cursor() is not None
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_End,state=0));settle(popup);assert backend.preferences().playback_volume==0
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));settle(popup);assert backend.preferences().playback_volume==100
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));settle(popup);assert backend.preferences().playback_volume==98
            popup.toggle_mute();settle(popup);assert not backend.inventory()['sinks'][0].muted
            popup.press(popup.area,SimpleNamespace(button=1,x=41,y=68));popup.release(popup.area,SimpleNamespace(button=1,x=41,y=68));settle(popup);assert 49<=backend.preferences().playback_volume<=51
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,popup.width,popup.height);popup.draw(popup.area,cairo.Context(surface));surface.write_to_png(str(a.output/'volume-popup.png'))
            assert fake.rows['sources'][0]['volume']==recording and fake.default['source']==default_source
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0));assert popup.finished
            assert popup.updates.wait_closed(2) and not popup.updates.worker.is_alive()
            # Real GTK feedback under a deliberately slow deterministic service.
            slow_fake=FakePulse()
            def slow_run(*args):time.sleep(.020);return slow_fake.run(*args)
            start=time.perf_counter();slow=VolumePopup(shell,volume[0],PulseAudio(slow_run));sessions.append(slow.updates);timings['constructor_ms']=(time.perf_counter()-start)*1000
            assert timings['constructor_ms']<50
            first_paint=[];slow.area.connect('draw',lambda *_:first_paint.append((time.perf_counter()-start)*1000)or False)
            settle(slow);timings['first_paint_ms']=min(first_paint);assert timings['first_paint_ms']<50
            latencies=[];draw_latency=[];event_draw=[];heartbeats=[];last=time.perf_counter();requested=[None]
            def painted(*_):
                if requested[0]is not None:event_draw.append((time.perf_counter()-requested[0])*1000);requested[0]=None
                return False
            slow.area.connect('draw',painted)
            def heartbeat():
                nonlocal last
                now=time.perf_counter();heartbeats.append((now-last)*1000);last=now;return True
            from gi.repository import GLib
            timer=GLib.timeout_add(8,heartbeat)
            for value in range(40):
                started=time.perf_counter()
                if requested[0]is None:requested[0]=started
                slow.change(value);latencies.append((time.perf_counter()-started)*1000);assert slow.volume==value
                # Paint immediately in a real drawing area; the backend is busy.
                surface=cairo.ImageSurface(cairo.FORMAT_RGB24,slow.width,slow.height);slow.draw(slow.area,cairo.Context(surface));draw_latency.append((time.perf_counter()-started)*1000)
                while Gtk.events_pending():Gtk.main_iteration_do(False)
                time.sleep(.002)
            slow.change(73);slow.toggle_mute();slow.finish();assert slow.updates.wait_closed(5);GLib.source_remove(timer);flush_draws(Gtk)
            assert not slow.updates.worker.is_alive();assert slow.updates.backend.inventory()['sinks'][0].percent==73
            timings.update(max_handler_ms=max(latencies),max_direct_paint_ms=max(draw_latency),max_event_to_draw_ms=max(event_draw,default=0),max_heartbeat_gap_ms=max(heartbeats,default=0),volume_writes=sum(call[0]=='set-sink-volume'for call in slow_fake.calls))
            assert timings['max_handler_ms']<50 and timings['max_direct_paint_ms']<50 and timings['max_event_to_draw_ms']<50
            assert timings['volume_writes']<40
            # Changing default rejects pending old-device intent; native error is
            # patched here to avoid a test-only modal loop.
            changed=FakePulse();changed_popup=VolumePopup(shell,volume[0],PulseAudio(changed.run));sessions.append(changed_popup.updates);settle(changed_popup);changed.default['sink']='headphones';before=copy.deepcopy(changed.rows)
            with patch.object(changed_popup,'show_error') as error:
                changed_popup.change(1);settle(changed_popup);assert error.called
            assert changed.rows==before;changed_popup.finish();assert changed_popup.updates.wait_closed(2)
            failed=FakePulse();failed_popup=VolumePopup(shell,volume[0],PulseAudio(failed.run));sessions.append(failed_popup.updates);settle(failed_popup);failed.fail='set-sink-volume'
            with patch.object(failed_popup,'show_error') as error:
                failed_popup.change(1);settle(failed_popup);assert error.called and failed_popup.volume==100
            failed_popup.finish();assert failed_popup.updates.wait_closed(2)
            # Close/reopen ordering must retain the newest popup's intent.
            reopening=FakePulse()
            def reopening_run(*args):time.sleep(.005);return reopening.run(*args)
            old_popup=VolumePopup(shell,volume[0],PulseAudio(reopening_run));sessions.append(old_popup.updates);settle(old_popup);old_popup.change(10);old_popup.finish()
            new_popup=VolumePopup(shell,volume[0],PulseAudio(reopening_run));sessions.append(new_popup.updates);new_popup.change(80);new_popup.finish();assert new_popup.updates.wait_closed(5)
            assert new_popup.updates.backend.inventory()['sinks'][0].percent==80
            # A failed final intent reports to the live shell, never the dead popup.
            closed_fake=FakePulse();closed_popup=VolumePopup(shell,volume[0],PulseAudio(closed_fake.run));sessions.append(closed_popup.updates);settle(closed_popup);closed_fake.fail='set-sink-volume'
            with patch('win95lx.apps.dialogs.message_box') as message:
                closed_popup.change(1);closed_popup.finish();assert closed_popup.updates.wait_closed(2);flush_draws(Gtk);message.assert_called_once();assert shell.audio_muted
            assert all(not session.worker.is_alive()for session in sessions)
            window.action(('tray',));window.action(('cancel',));assert shell.audio_preferences.tray
            reopened=MultimediaWindow(shell,backend);assert reopened.controller.pending.tray;reopened.action(('tray',));reopened.action(('apply',));assert not shell.audio_preferences.tray;reopened.destroy()
            render();assert not any(action[0]=='volume-tray-open' for *_,action in shell.hits)
        finally:
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    real=check_isolated_audio(a.output) if a.real_audio else None
    report={'latency':timings,'real_audio':real,'checks':['tray hidden by default; pending change does not show it; Apply shows native icon and hit target; two tray icons do not overlap','popup pointer and Home/End/arrow volume, mute and Escape work; recording channels/default stay unchanged','Cancel preserves applied icon state; reopen reads persisted setting; Apply hide removes hit target'],
            'async_checks':['Immediate constructor/optimistic drawing with20ms fake service; coalesced final73/mute; no worker survives popup close','Default change rejects stale intent; channel/recording/default invariants also covered by unit tests'],'failed':0,'pixel_scope':'Popup geometry is based on original SNDVOL32 dialog106; native screenshot acceptance is pending. Functional test uses deterministic audio service; real service coverage is available with --real-audio using an owned private server; check_multimedia also covers actual guest endpoint selection.'}
    from evidence import identity
    report.update(identity(ROOT,Path(__file__).resolve()))
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
