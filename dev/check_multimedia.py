#!/usr/bin/env python3
"""Multimedia UI, original regions and real isolated Pulse device transactions."""
import argparse,json,sys,subprocess,time
from pathlib import Path
from dataclasses import replace
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev'),str(ROOT/'tests')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.multimedia import MultimediaWindow,UnavailableAudio,QUALITY_REASON,VIDEO_REASON,MIDI_REASON,CD_REASON
    from win95lx.control_panel.audio_preferences import PulseAudio
    from win95lx.control_panel.preferences import PreferenceController
    from test_audio_preferences import FakePulse
    from check_menu_seams import flush_draws
    from check_reference_ui import compare_region
    from pixels import read
    checks=[];comparisons=[];render_times=[]
    with TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        backend=PulseAudio(FakePulse().run);window=MultimediaWindow(shell,backend);window.show_all();flush_draws(Gtk)
        def capture(win,name):
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,366,448);win.caption_active=True;win.draw(win.area,cairo.Context(surface));path=a.output/(name+'.png');surface.write_to_png(str(path));return read(path)
        try:
            for index,tab in enumerate(window.tabs):
                window.action(('tab',index));actual=capture(window,'multimedia-'+tab)
                source=read(ROOT/'private/screenshots/cpl-20261126/classic-reviewed-run2'/f'multimedia-{tab}.png')
                regions=[('caption-tabs',(0,0,366,61)),('bottom-commands',(0,405,366,43))]
                if tab=='audio':regions.append(('playback-recording-group-right-border',(340,68,3,296)))
                for name,rect in regions:
                    x,y,w,h=rect;diff=compare_region(actual,source,(22+x,22+y,w,h),(x,y));comparisons.append({'tab':tab,'region':name,'differing_pixels':diff});assert diff==0,(tab,name,diff)
            window.action(('tab',0));flush_draws(Gtk)
            actual=capture(window,'enabled-audio-combos')
            source=read(ROOT/'private/screenshots/cpl-20261126/classic-reviewed-run2/multimedia-video.png')
            for field,y in (('playback',139),('recording',287)):
                diff=compare_region(actual,source,(22+318,22+279,16,16),(311,y));comparisons.append({'control':field+'-enabled-combo-arrow','differing_pixels':diff});assert diff==0,(field,diff)
            for _ in range(20):
                surface=cairo.ImageSurface(cairo.FORMAT_RGB24,366,448);started=time.perf_counter();window.draw(window.area,cairo.Context(surface));render_times.append((time.perf_counter()-started)*1000)
            e=lambda x,y:SimpleNamespace(x=x,y=y,button=1)
            window.press(window.area,e(229,100));window.release(window.area,e(229,100));assert window.controller.pending.playback_volume==50
            window.focus_action=('slider','recording');window.key(window,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));assert window.controller.pending.recording_volume==0
            window.key(window,SimpleNamespace(keyval=Gdk.KEY_Right,state=0));assert window.controller.pending.recording_volume==1
            assert backend.preferences().playback_volume==100
            window.action(('device','sinks'));flush_draws(Gtk);window.popup_window.key(window.popup_window,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));window.popup_window.key(window.popup_window,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));assert window.controller.pending.playback=='headphones';assert window.controller.pending.playback_volume==25
            window.action(('tray',));window.action(('apply',));assert backend.preferences().playback=='headphones' and backend.preferences().recording_volume==1;assert shell.audio_preferences.tray
            window.update(playback_volume=10);window.action(('cancel',));window=None
            backend.set_playback_volume(68)
            reopened=MultimediaWindow(shell,backend);assert reopened.controller.pending.playback_volume==68 and reopened.controller.pending.tray
            backend.set_playback_volume(57);reopened.action(('tray',));reopened.action(('apply',));assert backend.preferences().playback_volume==57
            reopened.action(('tab',0));capture(reopened,'audio-reopened-actual-level');assert any(reason==QUALITY_REASON for rect,reason in reopened.disabled)
            for index,reason in ((1,VIDEO_REASON),(2,MIDI_REASON),(3,CD_REASON)):
                reopened.action(('tab',index));capture(reopened,'disabled-'+reopened.tabs[index]);assert any(reason==text for rect,text in reopened.disabled)
            reopened.action(('tab',4));reopened.key(reopened,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert reopened.device_selection==len(reopened.device_rows())-1
            with patch('win95lx.apps.dialogs.message_box') as message:reopened.action(('properties',));message.assert_called_once()
            reopened.destroy()
            checks.append('Pointer volume trackbar; keyboard endpoints and steps; native device popup selection; pending isolation, Apply, tray callback, Cancel; actual external level wins on reopen; disabled controls have accessible reasons; real inventory properties')
            no_devices=FakePulse();no_devices.rows={'sinks':[],'sources':[]};empty=MultimediaWindow(shell,PulseAudio(no_devices.run));empty.show_all();flush_draws(Gtk);capture(empty,'no-audio-devices');assert ('slider','playback') not in empty.focus_order() and ('tray',) not in empty.focus_order();assert empty.disabled;empty.destroy()
            unavailable=MultimediaWindow(shell,UnavailableAudio());unavailable.show_all();flush_draws(Gtk)
            with patch.object(unavailable,'error') as error:unavailable.action(('ok',));error.assert_not_called()
            checks.append('Missing playback/recording endpoints are disabled by capability; monitor sources are not represented as microphones')
        finally:
            if window:window.destroy()
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    # Own modules only: never change a physical endpoint or the user's existing
    # master levels. The modules are unloaded even when assertions fail.
    command=PulseAudio.command;modules=[];state=None;backend=PulseAudio()
    try:
        modules.append(command('load-module','module-null-sink','sink_name=win95lx_multimedia_qa','sink_properties=device.description=Win95LX_Multimedia_QA').strip())
        modules.append(command('load-module','module-null-sink','sink_name=win95lx_multimedia_qa2','sink_properties=device.description=Win95LX_Multimedia_QA2').strip())
        modules.append(command('load-module','module-remap-source','master=win95lx_multimedia_qa.monitor','source_name=win95lx_multimedia_mic','source_properties=device.description=Win95LX_Multimedia_Test_Input').strip())
        time.sleep(.2);state=backend.snapshot();prefs=backend.preferences()
        pending=replace(prefs,playback='win95lx_multimedia_qa2',playback_volume=37,recording='win95lx_multimedia_mic',recording_volume=63)
        backend.apply(pending);actual=backend.preferences();assert actual.playback==pending.playback and actual.recording==pending.recording;assert actual.playback_volume==37 and actual.recording_volume==63
        backend.set_playback_mute(True);assert next(d for d in backend.inventory()['sinks'] if d.name==actual.playback).muted
        backend.set_playback_mute(False);backend.set_playback_volume(44);assert backend.preferences().playback_volume==44
        checks.append('Real PipeWire/Pulse owned null output and remapped input: default device changes, playback/recording levels, mute, volume popup API and readback')
    finally:
        if state:backend.restore(state)
        for module in reversed(modules):command('unload-module',module)
    import statistics
    from evidence import identity
    references=[ROOT/'private/screenshots/cpl-20261126/classic-reviewed-run2'/f'multimedia-{tab}.png' for tab in MultimediaWindow.tabs]
    report={**identity(ROOT,Path(__file__).resolve(),references),'render_median_ms':round(statistics.median(render_times),3),'render_frames':len(render_times),'checks':checks,'comparisons':comparisons,'failed':0,'pixel_scope':'Only named original static regions; active audio controls and changed/disabled states are not whole-sheet pixel accepted.'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
