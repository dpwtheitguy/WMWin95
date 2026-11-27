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
    from win95lx.control_panel.sound_preferences import SoundBackend, SoundPreferences
    from win95lx.control_panel.preferences import PreferenceController
    config = Path(config) if config else Path.home()/'.config/win95lx'
    data = json.loads((shell.assets/'themes-library.json').read_text())['themes']
    themes = {}
    profile = [None]
    def refresh_profile():
        palette=shell.display_preferences.palette
        if profile[0]==palette:return
        for name,theme in data.items():
            wallpaper=theme['wallpaper'];native=wallpaper.get('native_256')
            file=native['file'] if palette==1 and native else wallpaper['file']
            themes[name]={**theme,'wallpaper':{**wallpaper,'file':str(shell.assets/file)}}
        profile[0]=palette
    refresh_profile()
    sounds = PreferenceController(config/'sounds.json', SoundBackend(shell.assets), SoundPreferences)
    factory = json.loads((shell.assets/'sound-library.json').read_text())['schemes']
    def sound(value, previous): return previous.select(value, factory)
    def refresh_wallpaper():
        # Persistence alone does not update the shell image cache. Decode before
        # repaint so Apply affects the actual desktop, including rollback.
        wallpaper = shell.wallpaper
        path = wallpaper.custom.get(wallpaper.name)
        if path:
            shell.wallpaper_images[wallpaper.name] = shell.load_background_image(path)
        shell.wallpaper_surface.cache_clear()
        shell.area.queue_draw()
    result = ThemeController(themes, {'wallpaper': WallpaperProvider(shell.wallpaper, refresh_wallpaper),
        'pointers': PointerThemeProvider(config/'mouse.json', lambda:shell.mouse_preferences, shell.apply_mouse_preferences, shell.pointer_library.names), 'sounds': CurrentPreferenceProvider(sounds, sound)}, config/'theme.json')
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
    result.reconcile_current({
        'wallpaper':lambda value: shell.wallpaper.custom.get(shell.wallpaper.name)==str(Path(value['file']).resolve()) and shell.wallpaper.mode==value['mode'],
        'pointers':lambda value:shell.mouse_preferences.scheme==value and not shell.mouse_preferences.overrides,
        'sounds':lambda value:sounds.applied.scheme==value and sounds.applied.events==factory[value],
    })
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
        self.names = ('Current Windows settings', *sorted(self.controller.themes, key=str.casefold))
        self.focus_action = ('theme',)
        self.menu_popup = None
        self.operation = None
        self.checks={state:cairo.ImageSurface.create_from_png(str(self.assets/f'accessibility-check-{state}.png')) for state in ('checked','unchecked')}
        self.disabled_check=cairo.ImageSurface.create_from_png(str(self.assets/'themes-check-disabled-checked.png'))
        self.preview_layer=cairo.ImageSurface.create_from_png(str(self.assets/'themes-preview-current-layer.png'))
        self.preview_images = {}
        self.popup_window = None
        self.connect('destroy', self.cleanup)

    def cleanup(self, *_):
        if self.popup_window: self.popup_window.destroy(); self.popup_window = None
        if self.menu_popup: self.menu_popup.destroy(); self.menu_popup = None
        if hasattr(self.controller, 'close'): self.controller.close()

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
        return [action for action in [('theme',),*((('component',name) for name in COMPONENTS)),('ok',),('cancel',),('apply',)] if action in enabled]

    def draw_content(self, p):
        current = self.controller.pending
        # Clear the original static preview; it must not falsely show a theme
        # which has not been selected or successfully applied to this session.
        p.fill(15,67,393,333,TEAL)
        if current:
            theme = self.controller.themes[current.name]
            path = theme['wallpaper']['file']
            if path not in self.preview_images:
                self.preview_images[path]=GdkPixbuf.Pixbuf.new_from_file(path).scale_simple(392,332,GdkPixbuf.InterpType.NEAREST)
            pixbuf=self.preview_images[path]
            from gi.repository import Gdk
            p.cr.save(); p.cr.rectangle(16,68,392,332); p.cr.clip()
            Gdk.cairo_set_source_pixbuf(p.cr,pixbuf,16,68)
            p.cr.paint(); p.cr.restore()
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
            active = component in COMPONENTS and current is not None
            selected = current is None or component in current.components
            p.image(self.checks['checked' if selected else 'unchecked'],x,y)
            if not active:
                if selected:p.image(self.disabled_check,x,y)
                else:p.fill(x+2,y+2,9,9,FACE)
            if active:p.text(label,x+18,y+1,BLACK)
            else:p.text(label,x+19,y+2,LIGHT);p.text(label,x+18,y+1,SHADOW)
            if active and self.focus_action==('component',component):self.focus_outline(p,x+18,y,p.font.width(label)+2,16)
            if active:self.hit((x,y,132,19),('component',component))
            else:self.disabled.append(((x,y,132,19),UNSUPPORTED.get('fonts' if component=='metrics' else component,'Select a theme first.')))
        for rect, reason in (((270,31,69,23),'Saving custom desktop themes is not available in this version.'),((345,31,69,23),'Removing installed theme packages is not available in this version.'),((434,49,134,23),UNSUPPORTED['screensaver']),((434,79,134,23),'The pointers and sounds preview is not available in this version. Choose Apply to use the selected pointers and sounds.')):
            x,y,w,h=rect;p.button('',x,y,w,h);self.disabled.append((rect,reason))
        for label,x,y in (('Save As...',279,36),('Delete',363,36),('Screen Saver',465,54),('Pointers, Sounds, etc...',445,84)):
            p.text(label,x,y,SHADOW)

    def action(self, action):
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
            self.controller.select(current.name,components);self.area.queue_draw();return
        if action[0] in ('ok','apply') and self.controller.pending is None:
            self.controller.cancel()
            if action[0]=='ok': self.destroy()
            else: self.area.queue_draw()
            return
        super().action(action)

    def choose(self, index):
        if index == 0:
            self.controller.pending = None
        else:
            self.controller.select(self.names[index])
        self.area.queue_draw()

    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
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
