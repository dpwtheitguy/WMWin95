#!/usr/bin/env python3
"""Volume tray preference, live controls and recording-state isolation."""
import argparse,json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tests')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.volume_popup import VolumePopup
    from win95lx.control_panel.audio_preferences import AudioPreferences,PulseAudio
    from win95lx.apps.multimedia import MultimediaWindow
    from test_audio_preferences import FakePulse
    from check_menu_seams import flush_draws
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
            popup=VolumePopup(shell,volume[0],backend);flush_draws(Gtk);assert popup.get_window().get_cursor() is not None
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert backend.preferences().playback_volume==0
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));assert backend.preferences().playback_volume==100
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));assert backend.preferences().playback_volume==98
            popup.toggle_mute();assert not backend.inventory()['sinks'][0].muted
            popup.press(popup.area,SimpleNamespace(button=1,x=41,y=68));popup.release(popup.area,SimpleNamespace(button=1,x=41,y=68));assert 49<=backend.preferences().playback_volume<=51
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,popup.width,popup.height);popup.draw(popup.area,cairo.Context(surface));surface.write_to_png(str(a.output/'volume-popup.png'))
            assert fake.rows['sources'][0]['volume']==recording and fake.default['source']==default_source
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0));assert popup.finished
            window.action(('tray',));window.action(('cancel',));assert shell.audio_preferences.tray
            reopened=MultimediaWindow(shell,backend);assert reopened.controller.pending.tray;reopened.action(('tray',));reopened.action(('apply',));assert not shell.audio_preferences.tray;reopened.destroy()
            render();assert not any(action[0]=='volume-tray-open' for *_,action in shell.hits)
        finally:
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    report={'checks':['tray hidden by default; pending change does not show it; Apply shows native icon and hit target; two tray icons do not overlap','popup pointer and Home/End/arrow volume, mute and Escape work; recording channels/default stay unchanged','Cancel preserves applied icon state; reopen reads persisted setting; Apply hide removes hit target'],
            'failed':0,'pixel_scope':'Popup geometry is based on original SNDVOL32 dialog106; native screenshot acceptance is pending. Functional test uses deterministic audio service; real service integration is covered by check_multimedia.'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
