"""Plus! Desktop Themes dialog using the existing session preference providers."""
from dataclasses import replace
from pathlib import Path
import json
import cairo
from gi.repository import GdkPixbuf,Gdk
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.theme_preferences import ThemeController, CurrentPreferenceProvider, PreferenceProvider, PointerThemeProvider, WallpaperProvider, COMPONENTS, UNSUPPORTED
from win95lx.shell.widgets import Painter, FACE, BLACK, LIGHT, SHADOW, NAVY, TEAL
from win95lx.shell.system_menu import options, WindowOperation, ARROWS
from win95lx.apps.fonts import FontMenu


def controller_for(shell, config=None):
    from win95lx.control_panel.sound_preferences import SoundBackend, SoundPreferences, BUILTINS
    from win95lx.control_panel.preferences import PreferenceController
    config = Path(config) if config else Path.home()/'.config/win95lx'
    data = json.loads((shell.assets/'themes-library.json').read_text())['themes']
    from win95lx.control_panel.theme_store import ThemeStore
    from win95lx.control_panel.theme_icons import IconThemeProvider
    from win95lx.control_panel.theme_appearance import AppearanceProvider
    from win95lx.control_panel.theme_preferences import ScreensaverThemeProvider
    from win95lx.apps.screensaver_host import host_for
    import shutil
    saver_host=host_for(shell)
    saver_available=saver_host.runtime is not None and saver_host.catalog is not None and callable(getattr(saver_host,'restore_theme',None)) and all(shutil.which(command)for command in (saver_host.runtime.wine,saver_host.runtime.wineboot,saver_host.runtime.wineserver))
    themes = {}
    profile = [None]
    result = None
    def refresh_profile():
        palette=shell.display_preferences.palette
        if profile[0]==palette:return
        resolved={}
        for name,theme in data.items():
            wallpaper=theme['wallpaper'];native=wallpaper.get('native_256')
            file=native['file'] if palette==1 and native else wallpaper['file']
            resolved[name]={**theme,'wallpaper':{**wallpaper,'file':str(shell.assets/file) if file else ''}}
            if 'icons' in theme:
                resolved[name]['icons']={role:{size:str((shell.assets/path).resolve()) for size,path in sizes.items()} for role,sizes in theme['icons'].items()}
        if result is None:themes.update(resolved)
        else:result.refresh_catalog(builtins=resolved)
        profile[0]=palette
    refresh_profile()
    sounds = PreferenceController(config/'sounds.json', SoundBackend(shell.assets), SoundPreferences)
    factory = {**BUILTINS,**json.loads((shell.assets/'sound-library.json').read_text())['schemes']}
    def sound(value, previous):
        if isinstance(value,dict):return replace(previous,scheme=value['scheme'],events=dict(value['events'])).validate()
        return previous.select(value, factory)
    def refresh_wallpaper():
        # Persistence alone does not update the shell image cache. Decode before
        # repaint so Apply affects the actual desktop, including rollback.
        wallpaper = shell.wallpaper
        path = wallpaper.custom.get(wallpaper.name)
        if path:
            shell.wallpaper_images[wallpaper.name] = shell.load_background_image(path)
        shell.wallpaper_surface.cache_clear()
        shell.area.queue_draw()
    result = ThemeController(themes, {'wallpaper': WallpaperProvider(shell.wallpaper, refresh_wallpaper, assets=shell.assets),
        'pointers': PointerThemeProvider(config/'mouse.json', lambda:shell.mouse_preferences, shell.apply_mouse_preferences, shell.pointer_library.names), 'sounds': CurrentPreferenceProvider(sounds, sound)}, config/'theme.json')
    result.providers['icons']=IconThemeProvider(shell,config/'theme-icons.json')
    for component in ('colors','fonts','metrics'):
        result.providers[component]=AppearanceProvider(component,config/('theme-'+component+'.json'))
    if saver_available:result.providers['screensaver']=ScreensaverThemeProvider(saver_host)
    from win95lx.control_panel.theme_import import import_theme
    def legacy_loader(data,path):return import_theme(data,path,result.capture_current(),config/'theme-icon-cache',shell.assets)
    result.attach_store(ThemeStore(config/'themes',dict(themes),legacy_loader=legacy_loader))
    def preflight(components):
        refresh_profile()
        conflicts=[label for component,kind,label in (('pointers','mouse','Mouse Properties'),('sounds','sounds','Sounds Properties'))
                   if component in components and kind in shell.accessory_windows]
        if 'wallpaper' in components and any(window.kind=='display' for window in shell.state.windows):
            conflicts.append('Display Properties')
        if conflicts:
            raise ValueError('Close '+ ' and '.join(conflicts)+' before applying these theme components. Your pending settings have been kept.')
    result.preflight=preflight
    result.refresh_profile=refresh_profile
    matches={
        'wallpaper':lambda value: result.providers['wallpaper'].export_current()['file']==(str(Path(value['file']).resolve()) if value['file'] else '') and all(result.providers['wallpaper'].export_current().get(key)==value.get(key,default) for key,default in (('mode','center'),('pattern','(None)'),('pattern_rows',[0]*8))),
        'pointers':lambda value: shell.mouse_preferences.scheme==(value['scheme'] if isinstance(value,dict) else value) and shell.mouse_preferences.overrides==(value.get('overrides',{}) if isinstance(value,dict) else {}),
        'sounds':lambda value: sounds.applied.scheme==(value['scheme'] if isinstance(value,dict) else value) and sounds.applied.events==(value['events'] if isinstance(value,dict) else factory[value]),
        'icons':lambda value:result.providers['icons'].export_current()==value,
    }
    for component in ('colors','fonts','metrics'):matches[component]=result.providers[component].matches
    if 'screensaver'in result.providers:matches['screensaver']=result.providers['screensaver'].matches
    result.reconcile_current(matches)
    return result


class DesktopThemesWindow(PropertySheet):
    title = 'Desktop Themes'
    size = (591,449)
    asset_prefix = 'themes'
    tabs = ('main',)
    tab_rects = ()
    buttons = ((339,412,75,23),(420,412,75,23),(501,412,75,23))

    def __init__(self, shell, controller=None):
        super().__init__(shell)
        self.controller = controller or controller_for(shell)
        self.refresh_names()
        self.focus_action = ('theme',)
        self.menu_popup = None
        self.operation = None
        self.checks={state:cairo.ImageSurface.create_from_png(str(self.assets/f'accessibility-check-{state}.png')) for state in ('checked','unchecked')}
        self.disabled_check=cairo.ImageSurface.create_from_png(str(self.assets/'themes-check-disabled-checked.png'))
        self.preview_layer=cairo.ImageSurface.create_from_png(str(self.assets/'themes-preview-current-layer.png'))
        self.preview_images = {}
        self.popup_window = None
        self.saver_host=self.controller.providers['screensaver'].host if 'screensaver'in self.controller.providers else None
        self.saver_listener=self.saver_host.subscribe(self.area.queue_draw) if self.saver_host else None
        self.warm_saver()
        self.connect('destroy', self.cleanup)

    def refresh_names(self):
        self.names=('Current Windows settings',*sorted(self.controller.themes,key=str.casefold),'Other...')

    def cleanup(self, *_):
        if self.saver_host and self.saver_listener:self.saver_host.unsubscribe(self.saver_listener)
        if self.popup_window: self.popup_window.destroy(); self.popup_window = None
        if self.menu_popup: self.menu_popup.destroy(); self.menu_popup = None
        if hasattr(self.controller, 'close'): self.controller.close()

    def selected_saver(self):
        current=self.controller.pending
        if current is not None:return self.controller.themes[current.name].get('screensaver',{}).get('saver','')
        return self.saver_host.applied.saver if self.saver_host else ''

    def warm_saver(self):
        host=self.saver_host
        identity=self.selected_saver()
        if host and identity and host.session_mode is None and not host.runtime.ready(identity):
            available,reason=host.available('fullscreen',identity)
            if available:host.warm(identity)

    def saver_preparing(self):
        current=self.controller.pending
        return bool(self.saver_host and current is not None and 'screensaver'in current.components and self.selected_saver() and not self.saver_host.runtime.ready(self.selected_saver()))

    def button(self,p,label,rect,action,enabled=True,reason=None):
        if action[0]in('ok','apply')and self.saver_preparing():
            enabled=False
            reason='The selected screen saver is being prepared. Other theme options remain available.' if self.saver_host.busy else 'The selected screen saver could not be prepared. Clear Screen saver to apply the other theme options.'
        return super().button(p,label,rect,action,enabled,reason)

    def draw(self, area, cr):
        if hasattr(self.controller,'refresh_profile'):self.controller.refresh_profile()
        result=super().draw(area,cr)
        w,h=self.size
        # Native EXE has Minimize and disabled Maximize; the CPL base sheet's
        # wide caption drag rectangle would otherwise cover the Minimize button.
        self.hits=[(rect,action) for rect,action in self.hits if action not in (('help',),('caption',))]
        self.hit((21,3,w-76,17),('caption',))
        self.hit((3,3,18,17),('system',))
        self.hit((w-55,4,16,15),('minimize',))
        self.disabled.append(((w-39,4,16,15),'This window has a fixed size and cannot be maximized.'))
        if not self.caption_active:
            p=Painter(cr,self.shell.font)
            # Preserve original caption icon/text origins, not the CPL's title
            # origin, and restore all three EXE caption buttons after base fill.
            p.fill(3,3,w-6,17,SHADOW)
            self.sprite(p,(4,4,16,15),4,4)
            p.text(self.title,20,4,LIGHT,bold=True)
            for x in (w-55,w-39,w-21):self.sprite(p,(x,4,16,15),x,4)
        if self.pressed==('minimize',) and self.press_inside:
            p=Painter(cr,self.shell.font);p.bevel(w-55,4,16,15,sunken=True);p.fill(w-50,14,6,2,BLACK)
        return result

    def caption_focus(self, active):
        if not active and self.menu_popup is not None:return False
        return super().caption_focus(active)

    def system_menu(self):
        if self.menu_popup is not None:self.menu_popup.finish()
        rows=[(label,('system',command),enabled,
               'This window has a fixed size.' if command in ('size','maximize') else '',
               'Alt+F4' if command=='close' else '')
              for command,label,mnemonic,enabled in options(resizable=False,minimizable=True,maximized=False)]
        rows.insert(len(rows)-1,None)
        self.menu_popup=ThemeSystemMenu(self,rows,3,126,top=21)

    def command(self, command):
        if isinstance(command,tuple) and command[0]=='system':command=command[1]
        if command=='minimize':
            self.focus_action=getattr(self,'caption_client_focus',self.focus_action)
            self.hide()
            self.shell.get_window().focus(Gdk.CURRENT_TIME)
            self.shell.area.queue_draw()
        elif command=='move':
            pointer=self.get_display().get_default_seat().get_pointer().get_position()
            self.operation=WindowOperation.begin('move',(*self.get_position(),*self.get_size()),(pointer.x,pointer.y))
        elif command=='close':self.action(('cancel',))
        self.area.queue_draw()

    def press(self, area, event):
        if event.button==1 and self.contains((3,3,18,17),event.x,event.y):
            self.system_menu();return True
        if event.button==1 and self.contains((self.size[0]-55,4,16,15),event.x,event.y) and self.pressed!=('minimize',):
            # GTK can send a second double-click press for the same hold.
            self.caption_client_focus=self.focus_action
        if self.operation is not None and event.button==1:
            self.operation=None;return True
        return super().press(area,event)

    def release(self, area, event):
        action=self.pressed
        result=super().release(area,event)
        if action==('minimize',):
            self.focus_action=getattr(self,'caption_client_focus',self.focus_action)
            self.area.queue_draw()
        return result

    def motion(self, area, event):
        if self.operation is not None:
            screen=self.get_screen();x,y,w,h=self.operation.motion(event.x_root,event.y_root,(screen.get_width(),screen.get_height()))
            self.move(x,y);return True
        if self.pressed==('minimize',):
            inside=self.contains((self.size[0]-55,4,16,15),event.x,event.y)
            if inside!=self.press_inside:self.press_inside=inside;self.area.queue_draw()
        return super().motion(area,event)

    def focus_outline(self,p,x,y,w,h):
        for dx in range(w):
            if dx%2==0:p.fill(x+dx,y,1,1,BLACK);p.fill(x+dx,y+h-1,1,1,BLACK)
        for dy in range(h):
            if dy%2==0:p.fill(x,y+dy,1,1,BLACK);p.fill(x+w-1,y+dy,1,1,BLACK)

    def focus_order(self):
        # Caption close shares Cancel's command ID, but must not place Cancel
        # before the native Theme field in keyboard tab order.
        enabled={action for rect,action in self.hits}
        return [action for action in [('theme',),('save',),('delete',),('theme-saver-preview',),*((('component',name) for name in COMPONENTS)),('ok',),('cancel',),('apply',)] if action in enabled]

    def draw_content(self, p):
        current = self.controller.pending
        # Clear the original static preview; it must not falsely show a theme
        # which has not been selected or successfully applied to this session.
        p.fill(15,67,393,333,TEAL)
        if current:
            theme = self.controller.themes[current.name]
            path = theme['wallpaper']['file']
            if path not in self.preview_images:
                try:self.preview_images[path]=GdkPixbuf.Pixbuf.new_from_file(path).scale_simple(392,332,GdkPixbuf.InterpType.NEAREST) if path else None
                except Exception:self.preview_images[path]=None
            pixbuf=self.preview_images[path]
            from gi.repository import Gdk
            p.cr.save(); p.cr.rectangle(16,68,392,332); p.cr.clip()
            if pixbuf is not None:
                Gdk.cairo_set_source_pixbuf(p.cr,pixbuf,16,68);p.cr.paint()
            p.cr.restore()
        else:
            image = self.shell.wallpaper_surface(self.shell.wallpaper.name, self.shell.display_preferences.palette)
            if image is not None:
                p.cr.save();p.cr.rectangle(15,67,393,333);p.cr.clip()
                p.cr.translate(15,67);p.cr.scale(393/image.get_width(),333/image.get_height())
                p.cr.set_source_surface(image);p.cr.paint();p.cr.restore()
        p.image(self.preview_layer,15,67)
        p.fill(15,408,315,30,FACE)
        if current:p.text("Preview of '"+current.name+"'",99,415)
        p.fill(62,35,183,17,LIGHT)
        label=current.name if current else 'Current Windows settings'
        if self.focus_action==('theme',):
            p.fill(63,36,181,15,BLACK);p.fill(64,37,179,13,NAVY)
            p.text(label,64,37,LIGHT)
        else:p.text(label,64,37)
        self.hit((60,33,202,21),('theme',))
        p.fill(437,185,132,195,FACE)
        for index, (label, component) in enumerate((('Screen saver','screensaver'),('Sound events','sounds'),('Mouse pointers','pointers'),('Desktop wallpaper','wallpaper'),('Icons','icons'),('Colors','colors'),('Font names and styles','fonts'),('Font and window sizes','metrics'))):
            x,y=438,(185,210,234,258,283,307,331,356)[index]
            p.fill(x,y,132,19,FACE)
            active = current is not None and component in self.controller.providers and component in theme
            selected = current is None or component in current.components
            p.image(self.checks['checked' if selected else 'unchecked'],x,y)
            if not active:
                if selected:p.image(self.disabled_check,x,y)
                else:p.fill(x+2,y+2,9,9,FACE)
            if active:p.text(label,x+18,y+1,BLACK)
            else:p.text(label,x+19,y+2,LIGHT);p.text(label,x+18,y+1,SHADOW)
            if active and self.focus_action==('component',component):self.focus_outline(p,x+18,y,p.font.width(label)+2,16)
            if active:self.hit((x,y,132,19),('component',component))
            else:
                reason=UNSUPPORTED.get('fonts' if component=='metrics' else component,'Select a theme first.')
                if component=='screensaver':reason='Select a theme first.' if current is None else 'Windows screen saver support is not installed on this computer.' if component not in self.controller.providers else 'This theme does not include a screen saver.'
                self.disabled.append(((x,y,132,19),reason))
        self.button(p,'&Save As...',(270,31,69,23),('save',),enabled=current is None,reason='Select Current Windows settings to save your desktop.')
        self.button(p,'&Delete',(345,31,69,23),('delete',),enabled=current is not None,reason='Current Windows settings cannot be deleted.')
        identity=self.selected_saver()
        saver_enabled=bool(self.saver_host and identity and self.saver_host.runtime.ready(identity))
        self.button(p,'Sc&reen Saver',(434,49,134,23),('theme-saver-preview',),enabled=saver_enabled,reason='Select a theme with an available screen saver and wait for preparation to finish.')
        for rect,label,reason in (((434,79,134,23),'Pointers, Sounds, etc...','Use the Mouse and Sounds properties to customize these settings.'),):
            self.button(p,label,rect,('unavailable',),enabled=False,reason=reason)

    def action(self, action):
        if action[0]=='theme-saver-preview':
            if self.saver_host:self.saver_host.launch('fullscreen',self.selected_saver(),self)
            return
        if action[0] in ('save','delete'):
            from win95lx.apps.theme_dialogs import choose_theme_file,confirm_theme_delete,ThemeQuestion,run_dialog,Gtk
            from win95lx.control_panel.theme_store import ThemeExistsError
            store=self.controller.store
            try:
                if action[0]=='delete':
                    current=self.controller.pending
                    if current is None:return
                    token=store.token(current.name)
                    if confirm_theme_delete(self,current.name):self.controller.delete_theme(current.name,expected=token)
                else:
                    if self.controller.pending is not None:return
                    store.directory.mkdir(parents=True,exist_ok=True)
                    path=choose_theme_file(self,store.directory,saving=True,store=store)
                    if not path:return
                    token=store.token_path(path)
                    try:self.controller.save_current(path=path)
                    except ThemeExistsError:
                        question=ThemeQuestion(self,'This theme already exists. Do you want to replace it?')
                        try:answer=run_dialog(question)==Gtk.ResponseType.YES
                        finally:question.destroy()
                        if answer:self.controller.save_current(path=path,overwrite=True,expected=token)
                self.refresh_names()
            except OSError:self.error('The theme file could not be changed. Check the folder and try again.')
            except (ValueError,RuntimeError) as error:self.error(error)
            self.area.queue_draw();return
        if action[0]=='system':self.system_menu();return
        if action[0]=='minimize':self.command('minimize');return
        if action[0]=='theme':
            from win95lx.apps.choice_dialog import ChoicePopup
            index=self.names.index(self.controller.pending.name) if self.controller.pending else 0
            self.popup_window=ChoicePopup(self,(60,33,202,21),self.names,index,self.choose)
            return
        if action[0]=='component':
            current=self.controller.pending;components=list(current.components);component=action[1]
            if component in components:components.remove(component)
            else:components.append(component)
            self.controller.select(current.name,components);self.warm_saver();self.area.queue_draw();return
        if action[0] in ('ok','apply') and self.controller.pending is None:
            self.controller.cancel()
            if action[0]=='ok': self.destroy()
            else: self.area.queue_draw()
            return
        super().action(action)

    def choose(self, index):
        if index == 0:
            self.controller.pending = None
        elif self.names[index]=='Other...':
            from win95lx.apps.theme_dialogs import choose_theme_file
            store=self.controller.store
            try:
                if store.is_default_directory:store.directory.mkdir(parents=True,exist_ok=True)
            except OSError:
                self.error('The themes folder could not be opened. Check the folder and try again.');return
            path=choose_theme_file(self,store.directory,saving=False,store=store)
            if path:
                try:
                    store=self.controller.store
                    if path.parent.resolve()==store.default_directory.resolve() and path.stem in store.builtins and not path.exists():
                        store.use_directory(store.default_directory);self.controller.refresh_catalog();self.controller.select(path.stem)
                    else:self.controller.open_theme(path)
                    self.refresh_names()
                except OSError:self.error('The theme file could not be opened. Check the folder and try again.')
                except ValueError as error:self.error(error)
        else:
            self.controller.select(self.names[index])
        self.warm_saver();self.area.queue_draw()

    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        if self.saver_host and self.saver_host.busy and self.saver_host.session_mode=='fullscreen':
            self.saver_host.stop_preview();return True
        if self.operation is not None:
            if name=='Escape':
                self.move(*self.operation.original[:2]);self.operation=None;return True
            if name in ('Return','KP_Enter'):
                self.operation=None;return True
            if name in ARROWS:
                screen=self.get_screen();x,y,w,h=self.operation.step(*ARROWS[name],(screen.get_width(),screen.get_height()))
                self.move(x,y);return True
        if event.state&Gdk.ModifierType.MOD1_MASK and name=='space':
            self.system_menu();return True
        if event.state&Gdk.ModifierType.MOD1_MASK and name and name.casefold()=='t':
            self.focus_action=('theme',);self.area.queue_draw();return True
        if self.focus_action==('theme',) and name in ('Up','Down','Home','End') and not event.state&Gdk.ModifierType.MOD1_MASK:
            current=self.names.index(self.controller.pending.name) if self.controller.pending else 0
            index=0 if name=='Home' else len(self.names)-1 if name=='End' else min(len(self.names)-1,max(0,current+(1 if name=='Down' else -1)))
            self.choose(index);return True
        if self.focus_action==('theme',) and (name=='F4' or name=='Down' and event.state&Gdk.ModifierType.MOD1_MASK):
            self.action(('theme',));return True
        return super().key(window,event)


class ThemeSystemMenu(FontMenu):
    """Use the shared popup, with native system-menu mnemonic distinctions."""
    def key(self, window, event):
        name=Gdk.keyval_name(event.keyval)
        if name=='F4' and event.state&Gdk.ModifierType.MOD1_MASK:
            parent=self.parent;self.finish(restore_focus=False);parent.command('close');return True
        if name=='Escape' and event.state&Gdk.ModifierType.CONTROL_MASK:
            parent=self.parent;self.finish(restore_focus=False);parent.shell.key(parent.shell,event);return True
        if name=='space' and event.state&Gdk.ModifierType.MOD1_MASK:return self.finish()
        if name and len(name)==1:
            command=next((command for command,label,mnemonic,enabled in options(resizable=False,minimizable=True,maximized=False)
                          if enabled and mnemonic==name.casefold()),None)
            if command:
                index=next(index for index,row in enumerate(self.rows) if row and row[1]==('system',command))
                return self.finish(index)
        return super().key(window,event)
