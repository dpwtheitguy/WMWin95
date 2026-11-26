#!/usr/bin/env python3
"""Per-applet native pixels, real X11 effects and Control Panel entry routes."""
import argparse,json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
from pixels import read
from check_reference_ui import compare_region

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.keyboard import KeyboardWindow,DRIVER_REASON
    from win95lx.apps.system import SystemWindow
    from win95lx.apps.datetime import DateTimeWindow
    from win95lx.apps.regional import RegionalWindow,FIELDS
    from win95lx.apps.choice_dialog import LanguageDialog,ChoicePopup
    from win95lx.control_panel.keyboard_preferences import X11Keyboard,KeyboardPreferences
    from win95lx.control_panel.datetime_settings import DateTimePreferences
    from win95lx.control_panel.regional_preferences import regional_preset,current as current_regional
    from datetime import datetime
    from win95lx.control_panel.catalog import labels,targets
    from check_menu_seams import flush_draws
    checks=[];comparisons=[];references=[];failures=[]
    settings=Gtk.Settings.get_default();previous=(settings.get_property('gtk-cursor-blink'),settings.get_property('gtk-cursor-blink-time'))
    backend=X11Keyboard();original=backend.snapshot()
    with TemporaryDirectory() as directory,patch('pathlib.Path.home',return_value=Path(directory)):
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        window=None
        try:
            backend.apply(KeyboardPreferences());settings.set_property('gtk-cursor-blink',True);settings.set_property('gtk-cursor-blink-time',1060)
            window=KeyboardWindow(shell,backend);window.show_all();flush_draws(Gtk)
            window.controller.applied=window.controller.pending=KeyboardPreferences()
            def capture(win,name):
                surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*win.size);win.draw(win.area,cairo.Context(surface));path=a.output/(name+'.png');surface.write_to_png(str(path));return read(path)
            for tab_index,name in enumerate(('speed','language')):
                window.action(('tab',tab_index));actual=capture(window,'keyboard-'+name)
                for profile,folder,origin in (('classic','classic-reviewed-run2',(66,66)),('ie4','ie4-run2',(110,110)),('plus','plus-run2',(110,110))):
                    path=ROOT/'private/screenshots/cpl-20261126'/folder/f'keyboard-{name}.png';references.append(path)
                    if profile=='ie4':
                        path=ROOT/'private/screenshots/cpl-20261126'/('ie4-keyboard-clean-second.png' if name=='speed' else 'ie4-keyboard-language-clean.png');origin=(44,44);references.append(path)
                    difference=compare_region(actual,read(path),(*origin,404,448),(0,0));comparisons.append({'applet':'keyboard','tab':name,'profile':profile,'differing_pixels':difference});assert difference==0,(name,profile,difference)
            window.action(('tab',0));capture(window,'keyboard-before-drag')
            event=lambda x,y:SimpleNamespace(x=x,y=y,button=1)
            window.press(window.area,event(140,124));window.release(window.area,event(140,124));assert window.controller.pending.delay_ms==1000
            window.key(window,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert window.controller.pending.delay_ms==250
            window.press(window.area,event(314,199));window.release(window.area,event(314,199));assert window.controller.pending.rate==32
            assert backend.snapshot()[:2]==(250,16)
            window.action(('apply',));assert backend.snapshot()[:2]==(250,32)
            assert json.loads(window.controller.path.read_text())['rate']==32
            window.update(rate=5);window.controller.cancel();assert window.controller.pending.rate==32
            checks.append('Keyboard: pointer and keyboard slider bounds, real X11 Apply, pending Cancel and persisted repeat')
            window.action(('tab',0));capture(window,'keyboard-applied-speed')
            window.press(window.area,event(60,265));window.release(window.area,event(60,265))
            for char in 'Win95':window.key(window,SimpleNamespace(keyval=Gdk.unicode_to_keyval(ord(char)),state=0))
            assert window.test_entry.text=='Win95';capture(window,'keyboard-typing-test')
            window.update(layouts=('us','gb'),variants=('',''),switch='alt_shift',indicator=True);window.action(('apply',))
            assert backend.snapshot()[2]['layout']=='us,gb';assert 'grp:alt_shift_toggle' in backend.snapshot()[2]['options']
            from win95lx.control_panel.keyboard_preferences import KeyboardGroups
            group=KeyboardGroups();group.select(1);assert group.current()==1;group.select(0);group.close()
            shell.action(('keyboard-language-menu',));assert len(shell.start_context.rows)==2
            shell.action(('keyboard-language-select',1));assert shell.keyboard_groups.current()==1
            shell.action(('keyboard-language-select',0))
            window.action(('tab',1));capture(window,'keyboard-two-languages');window.language_selection=1;window.action(('default',));assert window.controller.pending.layouts==('gb','us')
            window.language_selection=1;window.action(('remove',));assert window.controller.pending.layouts==('gb',)
            window.controller.cancel();assert window.controller.pending.layouts==('us','gb')
            # Opening Properties and accepting the same language must retain
            # a nondefault XKB variant rather than silently replacing it.
            window.update(layouts=('us',),variants=('intl',));window.language_selection=0
            with patch('win95lx.apps.choice_dialog.choose_language',return_value='us'):
                window.action(('properties',))
            assert window.controller.pending.variants==('intl',)
            window.update(layouts=('us','gb','de','fr'),variants=('','','',''))
            window.action(('tab',1));flush_draws(Gtk)
            assert ('add',) not in window.focus_order()
            assert any('four layouts' in reason for rect,reason in window.disabled)
            window.controller.cancel()
            checks.append('Keyboard: XKB language installation and switching, default reorder, Remove, Cancel, retained variants and four-layout capacity')
            window.action(('tab',2));capture(window,'keyboard-general')
            assert any(reason==DRIVER_REASON for rect,reason in window.disabled)
            checks.append('Keyboard: incompatible driver replacement is disabled with a concrete Help/tooltip reason')
            # Dialog pointer and keyboard paths use a real native-drawn popup.
            dialog=LanguageDialog(window,(('English (United States)','us'),('English (United Kingdom)','gb')))
            flush_draws(Gtk);dialog.key(dialog,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));assert dialog.value==1
            chosen=[];popup=ChoicePopup(dialog,dialog.rect,[label for label,code in dialog.layouts],0,chosen.append);flush_draws(Gtk)
            popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));assert chosen==[1]
            popup=ChoicePopup(dialog,dialog.rect,[label for label,code in dialog.layouts],0,chosen.append);popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0));assert chosen==[1]
            dialog.destroy();checks.append('Keyboard: native Add Language selector keyboard commit and popup Escape')
            window.destroy();window=None
            shell.open('control');panel=shell.state.active;shell.item_selection=(panel,'Keyboard');shell.action(('computer-menu',panel,'open'));assert 'keyboard' in shell.accessory_windows
            actual=shell.accessory_windows['keyboard'];shell.action(('computer-menu',panel,'properties'));assert shell.accessory_windows['keyboard'] is actual
            actual.action(('cancel',));shell.key(shell,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));assert 'keyboard' in shell.accessory_windows
            shell.accessory_windows['keyboard'].action(('cancel',))
            from win95lx.explorer.namespace import create_shortcut,resolve_shortcut
            link=create_shortcut(Path(directory)/'Desktop','Keyboard');assert resolve_shortcut(link).target=='keyboard'
            assert shell.shortcut_image(link,1)=='keyboard'
            checks.append('Keyboard: Control Panel Open, Properties, Enter, single-instance reuse and shortcut')
            system=SystemWindow(shell);system.show_all();flush_draws(Gtk)
            for index,name in enumerate(system.tabs):system.action(('tab',index));capture(system,'system-'+name)
            assert system.summary['memory']>0;system.action(('tab',1));rows=system.rows();system.action(('group',True));assert system.by_connection
            system.action(('refresh',));assert len(system.rows())>=1
            system.action(('group',False));system.key(system,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert system.selection==len(system.rows())-1
            system.key(system,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));assert system.selection==0
            system.destroy();checks.append('System: actual memory/device inventory, refresh, type/connection views and keyboard endpoints')
            class ClockBackend:
                def __init__(self):self.value=DateTimePreferences();self.edited=None;self.fail=False
                def preferences(self):return self.value
                def snapshot(self):return self.value,self.edited
                def restore(self,value):self.value,self.edited=value
                def apply(self,value,edited):
                    self.value,self.edited=value,edited
                    if self.fail:raise RuntimeError('Clock update rejected')
            clock=ClockBackend();date=DateTimeWindow(shell,clock);date.show_all();flush_draws(Gtk)
            date.controller.edited=datetime(1997,11,1,13,25,18);capture(date,'datetime-calendar-and-clock')
            date.controller.edited=datetime(2024,1,31,23,59,59);date.edit(month=2);assert date.value().day==29
            date.segment=2;date.step_time(1);assert date.value()==datetime(2024,3,1,0,0,0)
            date.controller.edited=None;date.action(('tab',1));actual=capture(date,'datetime-timezone')
            for profile,stem,origin in (('classic','windows95-classic',(22,22)),('ie4','windows95',(88,88)),('plus','windows95-plus-reference',(44,44))):
                path=ROOT/'private/screenshots/cpl-20261126'/(stem+'-datetime-timezone-repaint.png');references.append(path)
                if profile=='ie4':path=ROOT/'private/screenshots/cpl-20261126/ie4-datetime-safe-pointer.png';origin=(44,44);references.append(path)
                for suffix,rect in (('complete-timezone-sheet',(0,0,404,341)),):
                    difference=compare_region(actual,read(path),(origin[0]+rect[0],origin[1]+rect[1],rect[2],rect[3]),rect[:2])
                    comparisons.append({'applet':'datetime','state':suffix,'profile':profile,'differing_pixels':difference})
                    if difference:failures.append([profile,suffix,difference])
            date.action(('daylight',));assert not date.controller.pending.daylight
            index=next(index for index,row in enumerate(date.zones) if row[1]=='Asia/Kolkata');date.select_zone(index)
            date.action(('apply',));assert clock.value.zone=='Asia/Kolkata' and not clock.value.daylight
            saved=json.loads(date.controller.path.read_text());assert saved['zone']=='Asia/Kolkata' and 'edited' not in saved
            date.controller.edited=datetime(2026,11,26,12);date.action(('cancel',));assert clock.edited is None
            checks.append('Date/Time: leap-year calendar, midnight rollover, native map/caption/buttons in all three profiles, zone and DST Apply, Cancel without replaying a clock edit')
            regional=RegionalWindow(shell);regional.show_all();flush_draws(Gtk)
            for index,name in enumerate(regional.tabs):regional.action(('tab',index));capture(regional,'regional-'+name)
            regional.region_selected(4);assert regional.controller.pending.decimal==','
            regional.action(('tab',1));regional.action(('field','digits'));regional.key(regional,SimpleNamespace(keyval=Gdk.KEY_3,state=0));assert regional.commit_entry();assert regional.controller.pending.digits==3
            regional.selected('leading_zero','.7');assert not regional.controller.pending.leading_zero
            regional.selected('measurement','U.S.');regional.selected('list_separator',';')
            regional.action(('apply',));assert current_regional().decimal==',' and current_regional().digits==3
            shell.launch_accessory('calc');calculator=shell.accessory_windows['calc'];calculator.press('1');calculator.press('.');calculator.press('5')
            assert calculator.readout.get_text()=='1,5';assert calculator.decimal_button.get_label()==','
            calculator.paste_text(None,'1.234,56');assert calculator.readout.get_text()=='1234,56'
            shell.launch_accessory('notepad');notepad=shell.accessory_windows['notepad'];notepad.insert_date();text=notepad.buffer.get_text(*notepad.buffer.get_bounds(),True)
            assert current_regional().date(datetime.now()) in text
            shell.launch_accessory('wordpad');wordpad=shell.accessory_windows['wordpad'];wordpad.insert_datetime();text=wordpad.buffer.get_text(*wordpad.buffer.get_bounds(),True)
            assert text==current_regional().date(datetime.now())
            regional.region_selected(0);regional.action(('cancel',));assert current_regional().decimal==','
            checks.append('Regional Settings: five tabs, numeric entry, symbol/style selection, Apply and Cancel; live Calculator decimal/keypad/paste, Notepad timestamp and WordPad date use applied settings')
        finally:
            if window:window.destroy()
            for accessory in tuple(shell.accessory_windows.values()):accessory.destroy()
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy();backend.restore(original)
            settings.set_property('gtk-cursor-blink',previous[0]);settings.set_property('gtk-cursor-blink-time',previous[1])
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),references),'checks':checks,'comparisons':comparisons,'failures':failures,'failed':len(failures)}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
