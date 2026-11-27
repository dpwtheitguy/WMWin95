#!/usr/bin/env python3
"""Sounds Properties interactions, original regions, source library and routing."""
import argparse,json,hashlib,sys,subprocess,time,os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    display=Gdk.Display.get_default()
    assert display and 'X11' in type(display).__name__ and display.get_name()==os.environ.get('DISPLAY'), 'Run this check on the intended isolated X11 display.'
    from win95lx.apps.sounds import SoundsWindow
    from win95lx.control_panel.sound_preferences import wave_details,KEYS
    from win95lx.sound import SoundPlayer,play_event
    from win95lx.apps.dialogs import FileDialog
    from check_menu_seams import flush_draws
    from check_reference_ui import compare_region
    from pixels import read
    checks=[];comparisons=[];library=json.loads((ROOT/'private/shell-assets/sound-library.json').read_text())
    unique={row['file'] for row in library['sources']}
    for row in library['sources']:
        path=ROOT/'private/shell-assets'/row['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];wave_details(path)
    checks.append(f"Library: {len(library['sources'])} source WAVs, {len(unique)} unique audio files; every digest and WAV header validated")
    with TemporaryDirectory() as directory,patch('pathlib.Path.home',return_value=Path(directory)),patch('win95lx.shell.app.play_event') as event:
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        player=Mock();player.playing=False
        window=SoundsWindow(shell,player);window.show_all();flush_draws(Gtk)
        def capture(name):
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,366,448);window.draw(window.area,cairo.Context(surface));path=a.output/(name+'.png');surface.write_to_png(str(path));return read(path)
        try:
            actual=capture('sounds-default');ref=ROOT/'private/screenshots/cpl-20261126/plus-sounds-index1.png'
            # Scheme text differs because the original has an unnamed customized
            # scheme. Compare independent static borders and native event rows.
            for name,rect in [('caption-tabs',(0,0,366,61)),('default-events',(24,77,316,124)),('bottom-commands',(0,405,366,43))]:
                x,y,w,h=rect;diff=compare_region(actual,read(ref),(66+x,66+y,w,h),(x,y));comparisons.append({'region':name,'differing_pixels':diff});assert diff==0,(name,diff)
            # Independent native capture includes both GroupBox padding and
            # complete combo bevel: a text-only comparison missed this defect.
            from dataclasses import replace
            previous=window.controller.pending
            window.controller.pending=replace(previous,scheme='Windows Default')
            selected=capture('sounds-scheme-native-placement')
            native=read(ROOT/'private/screenshots/command-buttons-20261126/sounds-field-selected3-native.png')
            rect=(24,329,310,25)
            diff=compare_region(selected,native,(132+rect[0],120+rect[1],rect[2],rect[3]),rect[:2])
            comparisons.append({'region':'scheme-field-border-padding-and-text','differing_pixels':diff})
            assert diff==0,('scheme-field-border-padding-and-text',diff)
            # Custom long names must clip within the client without repainting
            # the native arrow or either surrounding border.
            window.controller.pending=replace(previous,scheme='A very long custom sound scheme '*8)
            long=capture('sounds-scheme-long-name')
            for border in ((24,329,11,25),(315,329,19,25),(35,329,280,5),(35,351,280,3)):
                x,y,w,h=border
                assert compare_region(long,selected,border,(x,y))==0,border
            window.controller.pending=previous
            capture('sounds-command-mnemonics')
            with patch('win95lx.apps.dialogs.name_dialog',return_value=None) as save:
                window.key(window,SimpleNamespace(keyval=Gdk.KEY_s,state=Gdk.ModifierType.MOD1_MASK))
                save.assert_called_once()
            assert window.focus_action==('save-scheme',)
            window.focus_action=None
            e=lambda x,y:SimpleNamespace(x=x,y=y,button=1)
            window.press(window.area,e(100,100));window.release(window.area,e(100,100));assert window.event=='SystemAsterisk'
            window.action(('play',));player.play.assert_called_once_with(ROOT/'private/shell-assets/sound-chord.wav')
            window.action(('stop',));assert player.stop.called
            window.focus_action=('events',);window.key(window,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert window.event=='EmptyRecycleBin'
            capture('sounds-last-event');window.key(window,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));assert window.event is None
            window.choose_event(1);window.assign('');assert window.value()==''
            window.action(('name',));flush_draws(Gtk);popup=window.popup_window;popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));assert window.value()
            window.action(('scheme',));popup=window.popup_window;popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0));assert window.controller.pending.scheme==''
            checks.append('Pointer event selection; keyboard Home/End scroll; Play/Stop; Name popup selection and scheme Escape')
            custom=Path(directory)/'chosen.wav';custom.write_bytes((ROOT/'private/shell-assets/sound-ding.wav').read_bytes())
            with patch('win95lx.apps.dialogs.choose_file',return_value=custom):window.action(('browse',))
            assert window.value()==str(custom)
            chooser=FileDialog(window,custom.parent,(('Sounds (*.wav)',('*.wav','*.WAV')),));chooser.show_all();flush_draws(Gtk);assert chooser.folder==custom.parent;chooser.destroy()
            with patch('win95lx.apps.dialogs.name_dialog',return_value='My Sounds'):window.action(('save-scheme',))
            assert window.controller.pending.scheme=='My Sounds';window.action(('apply',));assert window.controller.path.exists()
            capture('sounds-applied-custom')
            with patch('win95lx.sound._player.play') as run:
                assert play_event(window.assets,'SystemAsterisk');run.assert_called_once_with(custom)
            # An invalid edited file neither replaces persisted settings nor
            # changes the backend. Error reporting remains on the native path.
            window.assign(str(Path(directory)/'missing.wav'))
            with patch.object(window,'error') as error:window.action(('apply',));error.assert_called_once()
            assert window.controller.applied.scheme=='My Sounds';window.controller.cancel()
            for index,name in enumerate(window.factory):
                if name.startswith('Plus! / '):
                    window.select_scheme(index);window.controller.pending.validate()
                    for filename in window.controller.pending.events.values():
                        if filename:wave_details(window.assets/filename)
            window.select_scheme(1);window.action(('apply',))
            with patch('win95lx.sound._player.play') as run:
                for key in KEYS:assert not play_event(window.assets,key)
                run.assert_not_called()
            window.select_scheme((tuple(window.factory)+tuple(window.controller.pending.schemes)).index('My Sounds'))
            with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.NO):window.action(('delete-scheme',))
            assert 'My Sounds' in window.controller.pending.schemes
            with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):window.action(('delete-scheme',))
            assert 'My Sounds' not in window.controller.pending.schemes
            window.action(('cancel',));window=None
            reopened=SoundsWindow(shell,player);assert reopened.controller.pending.scheme=='No Sounds';reopened.destroy()
            checks.append('Browse WAV and real shared file dialog; custom scheme save/delete confirmation; Apply, failure rollback, Cancel, reopen and live event dispatch; No Sounds suppresses every event')
            event.reset_mock();shell.open('computer');win=shell.state.active;assert event.call_args.args[1]=='Open'
            event.reset_mock();shell.open('computer');event.assert_not_called()
            shell.action(('minimize',win));assert event.call_args.args[1]=='Minimize'
            event.reset_mock();shell.action(('minimize',win));event.assert_not_called()
            shell.show_start();assert event.call_args.args[1]=='MenuPopup'
            event.reset_mock();shell.show_start();event.assert_not_called()
            shell.action(('close',win));assert event.call_args.args[1]=='Close'
            checks.append('Shell events fire for newly opened/closed/minimized windows and opening Start; reused windows, repeated minimize and closing Start stay silent')
            from win95lx.shell.accessories import style_menus
            menu=Gtk.Menu();item=Gtk.MenuItem(label='Test');menu.append(item)
            style_menus(menu);style_menus(menu)
            with patch('win95lx.sound.notify') as notify:
                # Hooks close over the function, so install on a fresh menu.
                menu2=Gtk.Menu();item2=Gtk.MenuItem(label='Test');menu2.append(item2);style_menus(menu2);style_menus(menu2)
                order=[];notify.side_effect=lambda *_:order.append('sound');item2.connect('activate',lambda *_:order.append('action'))
                item2.activate();assert notify.call_count==1 and order==['sound','action']
                item2.set_sensitive(False);item2.activate();assert notify.call_count==1
                menu2.destroy()
            menu.destroy()
            from win95lx.apps.dialogs import message_box
            with patch('win95lx.sound.notify') as notify,patch('win95lx.apps.dialogs.run_dialog',return_value=Gtk.ResponseType.OK):
                for kind,key in ((Gtk.MessageType.INFO,'SystemAsterisk'),(Gtk.MessageType.ERROR,'SystemHand'),(Gtk.MessageType.QUESTION,'SystemQuestion'),(Gtk.MessageType.WARNING,'SystemExclamation')):
                    notify.reset_mock();message_box(shell,'Sound routing','Test',kind);notify.assert_called_once_with(shell,key)
            checks.append('All twelve Plus schemes resolve every assigned WAV; menu sound fires once before the action; disabled items stay silent; four message categories each dispatch once')
            # Exercise the real local ALSA decoder without sending test audio
            # to the user's speakers. This verifies process and Stop behavior;
            # audible hardware playback remains a separate guest check.
            real=SoundPlayer();original_popen=subprocess.Popen
            def decoder(command,**kwargs):return original_popen(['aplay','-q','-D','null',command[-1]],**kwargs)
            with patch('win95lx.sound.shutil.which',return_value='/usr/bin/aplay'),patch('win95lx.sound.subprocess.Popen',side_effect=decoder):
                process=real.play(ROOT/'private/shell-assets/sound-ding.wav');assert process.wait(timeout=10)==0;assert not real.playing
                real.play(ROOT/'private/shell-assets/sound-mssound.wav');real.stop();assert not real.playing
            checks.append('Real ALSA WAV decoding exits successfully; replacing/stopping playback reaps the process (null sink, no hardware-audibility claim)')
        finally:
            if window:window.destroy()
            for accessory in tuple(shell.accessory_windows.values()):accessory.destroy()
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    report={'checks':checks,'comparisons':comparisons,'source_wavs':len(library['sources']),'unique_wavs':len(unique),'failed':0}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
