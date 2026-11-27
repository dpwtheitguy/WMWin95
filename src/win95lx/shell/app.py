"""Experimental Win95LX shell surface. Run only in the dedicated Linux guest.

Original bitmap assets are required. This is not a complete window manager,
Windows compatibility layer or a pixel-verified replica.
"""
import argparse,datetime,fnmatch,json,os,subprocess,time
from dataclasses import replace
from functools import lru_cache
from threading import Thread
from pathlib import Path
import gi

gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib,GdkPixbuf,Gio
import cairo
from win95lx.assets.bitmap import BitmapFont
from win95lx.shell.model import DesktopState
from win95lx.shell.menu_layout import POPUP_GUTTER, POPUP_ROW_HEIGHT, popup_width
from win95lx.shell.desktop_icons import DesktopIcons, ShortcutIcons, desktop_file_slots, ICON_WIDTH, ICON_HEIGHT
from win95lx.shell import accessories, explorer_chrome, start_menu as menu, taskbar
from win95lx.shell.shortcut_folders import FOLDER_TITLES, ShortcutFolders
from win95lx.shell.shutdown_dialog import ShutdownDialog, is_development_guest
from win95lx.shell.run_dialog import RunDialog
from win95lx.shell.start_context import StartContext, SystemContext
from win95lx.shell.system_menu import ARROWS, MENU_WIDTH, WindowOperation, options as system_options
from win95lx.display_modes import DISPLAY_MODES, discover_modes, remember_resolution, set_resolution
from win95lx.explorer.trash import TrashStore
from win95lx.explorer.file_operations import FileClipboard, child_name, move_entry
from win95lx.explorer.drive_browser import DriveBrowser, SCROLLBAR_WIDTH
from win95lx.shell.drop_geometry import contains, folder_drop_rect, drag_started
from win95lx.shell.combo_box import ComboBox
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.control_panel.applets import APPLETS
from win95lx.control_panel import catalog as cpl_catalog
from win95lx.control_panel import background, display_settings
from win95lx.control_panel.display_preferences import DisplayPreferences, FONT_SIZES, PALETTES, color_surface
from win95lx.control_panel.wallpaper import BITMAPS, Wallpaper, paint_wallpaper, paint_pattern
from win95lx.recent_documents import RecentDocuments
from win95lx.sound import play_startup,play_event
from win95lx.shell.widgets import Painter,FACE,LIGHT,SHADOW,BLACK,NAVY,TEAL
RECYCLE_TARGET = '::recycle-bin::'


class ScaledPointer:
    def __init__(self, event, scale):
        self.event = event
        self.x, self.y = event.x/scale, event.y/scale

    def __getattr__(self, name):
        return getattr(self.event, name)


from win95lx.shell import explorer_menu, computer_view


class Shell(Gtk.Window):
    def __init__(self,assets):
        super().__init__(title='Win95LX Development Shell');self.set_decorated(False);self.set_default_size(800,600);self.move(0,0);self.fullscreen();self.state=DesktopState();self.assets=assets;self.font=BitmapFont((assets/'ms-sans-serif-8.fnt').read_bytes());self.images={};self.small_images={};self.hits=[];self.drag=None;self.clock=None;self.popup=None;self.item_selection=None;self.pending_resolution=None
        self.accessory_windows = {}
        from win95lx.control_panel.audio_preferences import AudioPreferences
        self.audio_preferences=AudioPreferences();self.audio_muted=False;self.volume_popup=None
        try:
            saved=json.loads((Path.home()/'.config/win95lx/multimedia.json').read_text())
            if isinstance(saved,dict) and type(saved.get('tray')) is bool:self.audio_preferences=replace(self.audio_preferences,tray=saved['tray'])
        except (OSError,ValueError,TypeError):pass
        for name in ('volume','volume-muted'):
            icon=assets/(name+'-icon.png')
            if icon.exists():self.small_images[name]=cairo.ImageSurface.create_from_png(str(icon))
        self.namespace_drag = None
        self.namespace_item_drag = self.namespace_item_point = None
        self.task_order = []
        self.active_task = None
        self.desktop_icons = DesktopIcons()
        self.shortcut_icons = ShortcutIcons()
        self.shortcut_drag = None
        self.shortcut_drag_point = None
        self.icon_drag = None
        self.icon_drag_point = None
        self.shutdown_dialog = ShutdownDialog(assets)
        self.run_dialog = RunDialog()
        self.shutdown_windows = []
        self.cursors = {}
        self.menu_hit_start = 0
        self.start_context = None
        from win95lx.explorer.browsing import BrowsingPreferences
        self.browsing_path=Path.home()/'.config/win95lx/folders.json'
        self.browsing_preferences=BrowsingPreferences.load(self.browsing_path)
        self.window_operation = None
        self.shortcut_folders = ShortcutFolders()
        self.shortcut_drop = None
        self.explorer_menu_art = {}
        for part in ('left', 'middle', 'right'):
            path = assets / f'explorer-menu-{part}.png'
            if path.is_file():
                self.explorer_menu_art[part] = cairo.ImageSurface.create_from_png(str(path))
        if (assets/'mouse-icon.png').exists():self.images['mouse']=cairo.ImageSurface.create_from_png(str(assets/'mouse-icon.png'))
        if (assets/'mouse-icon-small.png').exists():self.small_images['mouse']=cairo.ImageSurface.create_from_png(str(assets/'mouse-icon-small.png'))
        self.wallpaper_images = {}
        for label, filename in BITMAPS.items():
            path = assets / f'wallpaper-{filename}'
            if path.is_file():
                try:
                    bitmap = GdkPixbuf.Pixbuf.new_from_file(str(path))
                    image = cairo.ImageSurface(cairo.FORMAT_RGB24, bitmap.get_width(), bitmap.get_height())
                    cr = cairo.Context(image)
                    Gdk.cairo_set_source_pixbuf(cr, bitmap, 0, 0)
                    cr.paint()
                    self.wallpaper_images[label] = image
                except GLib.Error as error:
                    print(f'Could not read wallpaper {filename}: {error}', flush=True)
        self.wallpaper = Wallpaper({BITMAPS[label] for label in self.wallpaper_images})
        for label,path in self.wallpaper.custom.items():
            try:
                self.wallpaper_images[label] = self.load_background_image(path)
            except (GLib.Error,OSError):
                if label == self.wallpaper.name:
                    self.wallpaper.name = '(None)'
        patterns_path = assets/'desktop-patterns.json'
        self.desktop_patterns = json.loads(patterns_path.read_text()) if patterns_path.is_file() else {}
        self.pending_pattern,self.pending_pattern_rows = self.wallpaper.pattern,self.wallpaper.pattern_rows
        frame = assets / 'background-frame-clean.png'
        enabled = assets / 'background-frame-clouds.png'
        self.background_frame = cairo.ImageSurface.create_from_png(str(frame)) if frame.is_file() else None
        self.background_enabled = cairo.ImageSurface.create_from_png(str(enabled)) if enabled.is_file() else None
        path = assets / 'display-settings.png'
        self.settings_frame = cairo.ImageSurface.create_from_png(str(path)) if path.is_file() else None
        path = assets / 'display-settings-apply.png'
        self.settings_apply = cairo.ImageSurface.create_from_png(str(path)) if path.is_file() else None
        path = assets/'display-settings-checkbox-checked.png'
        self.settings_checked = cairo.ImageSurface.create_from_png(str(path)) if path.is_file() else None
        self.display_preferences_path = Path.home()/'.config'/'win95lx'/'display.json'
        self.display_preferences = DisplayPreferences.load(self.display_preferences_path)
        self.pending_display = self.display_preferences
        self.display_combos = {'palette': ComboBox(PALETTES), 'font': ComboBox(FONT_SIZES)}
        self.pointer_scale = 1
        self.resolution_drag = None
        self.resolution_focus = None
        self.resolution_trial = None
        self.resolution_error = ''
        self.wallpaper_drag = None
        self.pending_wallpaper = self.wallpaper.name
        self.wallpaper_combo = ComboBox(tuple(mode.title() for mode in background.MODES),
                                            background.MODES.index(self.wallpaper.mode))
        self.wallpaper_scroll = 0
        self.wallpaper_error = False
        self.display_tab = 'background'
        self.menu_path = []
        self.dialog_input = ''
        self.dialog_error = ''
        self.find_results = None
        self.suspended = False
        documents = Path.home()/'Win95LXDrive'
        documents.mkdir(exist_ok=True)
        self.drive = DriveBrowser(Path('/') if is_development_guest() else documents)
        self.desktop_folder = (Path.home() if is_development_guest() else documents)/'Desktop'
        self.desktop_files = []
        self.desktop_file_defaults = {}
        self.refresh_desktop_files()
        self.drive_scroll_drag = None
        self.file_clipboard = FileClipboard()
        self.trash = TrashStore()
        self.trash_selection = set()
        self.drive_selection = set()
        self.drive_anchor = None
        self.file_drag = None
        self.file_drag_origin = None
        self.file_drag_toggle = False
        self.file_drag_point = None
        self.file_hover = None
        mark=assets/'menu-check.png'
        if mark.is_file():self.images['menu-check']=cairo.ImageSurface.create_from_png(str(mark))
        self.address_window = None
        from win95lx.shell.text_entry import TextEntry
        self.address_entry=TextEntry()
        self.address_text = ""
        self.work_offline = False
        self.drive_menu_highlight = None
        self.drive_menu_rows = []
        for path in assets.glob('shell32-group-*.png'):self.images[int(path.stem.split('-')[-1])]=cairo.ImageSurface.create_from_png(str(path))
        for path in assets.glob('shell32-small-*.png'):
            self.small_images[int(path.stem.split('-')[-1])]=cairo.ImageSurface.create_from_png(str(path))
        for kind in accessories.APPLICATIONS:
            icon = assets / f'accessory-{kind}.png'
            if icon.exists():
                self.small_images[kind] = cairo.ImageSurface.create_from_png(str(icon))
            large_icon = assets / f'accessory-{kind}-32.png'
            if large_icon.exists():
                self.images[kind] = cairo.ImageSurface.create_from_png(str(large_icon))
        selected_folder_icon = assets/'explorer-folder-selected-32.png'
        if selected_folder_icon.is_file():
            self.images['folder-selected'] = cairo.ImageSurface.create_from_png(str(selected_folder_icon))
        folder_icon = assets/'explorer-folder-32.png'
        if folder_icon.is_file():
            self.images[4] = cairo.ImageSurface.create_from_png(str(folder_icon))
        start_flag = assets/'start-flag.png'
        if start_flag.exists():
            self.images['start'] = cairo.ImageSurface.create_from_png(str(start_flag))
        display_icon = assets/'display-applet.png'
        if display_icon.exists():
            self.images['display'] = cairo.ImageSurface.create_from_png(str(display_icon))
        for applet in cpl_catalog.implemented():
            for size,mapping in ((32,self.images),(16,self.small_images)):
                icon=assets/f'cpl-{applet.key}-{size}.png'
                if icon.exists():
                    mapping['cpl-'+applet.key]=cairo.ImageSurface.create_from_png(str(icon))
                    mapping[applet.key]=mapping['cpl-'+applet.key]
        for name in ('printer','printer-default','printer-add'):
            for size,mapping in ((32,self.images),(16,self.small_images)):
                path=assets/f'{name}-{size}.png'
                if path.exists():mapping[name]=cairo.ImageSurface.create_from_png(str(path))
        for ident, filename in (
            ('banner', 'start-banner.png'), ('computer', 'my-computer-32.png'),
            ('favorites', 'start-favorites.png'), ('settings', 'start-settings.png'),
            ('find', 'start-find.png'), ('start-up', 'start-button-up.png'),
            ('start-down', 'start-button-down.png'),
        ):
            path = assets / filename
            if path.exists():
                self.images[ident] = cairo.ImageSurface.create_from_png(str(path))
        computer_small = assets / 'my-computer-16.png'
        if computer_small.exists():
            self.small_images['computer'] = cairo.ImageSurface.create_from_png(str(computer_small))
        self.area=Gtk.DrawingArea();self.add(self.area);self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK);self.area.connect('draw',self.draw);self.area.connect('button-press-event',self.press);self.area.connect('button-release-event',self.release);self.area.connect('motion-notify-event',self.motion);self.connect('key-press-event',self.key);self.connect('destroy',Gtk.main_quit)
        screen = self.get_screen()
        self.area.add_events(Gdk.EventMask.SCROLL_MASK)
        self.area.connect('scroll-event', self.scroll_wallpaper)
        accessories.install_menu_style(screen)
        Gtk.Settings.get_for_screen(screen).set_property('gtk-xft-dpi', self.display_preferences.dpi*1024)
        screen.connect('size-changed', self.resize_to_display)
        self.width, self.height = screen.get_width(), screen.get_height()
        self.detected_resolution_modes=discover_modes()
        self.keyboard_preferences=None;self.keyboard_groups=None
        self.connect('destroy',lambda *_:self.keyboard_groups.close() if self.keyboard_groups else None)
        self.set_default_size(self.width, self.height)
        from win95lx.assets.cursors import PointerLibrary
        self.pointer_library=PointerLibrary(assets);self.cursor_animation_timer=None;self.cursor_animation_epoch=GLib.get_monotonic_time()
        from win95lx.control_panel.mouse_preferences import MousePreferences,X11Mouse
        mouse_path=Path.home()/'.config/win95lx/mouse.json'
        self.mouse_preferences=MousePreferences.load(mouse_path)
        Gtk.Settings.get_default().set_property('gtk-double-click-time',self.mouse_preferences.double_click_ms)
        if mouse_path.exists():
            try:
                backend=X11Mouse()
                try:backend.apply(self.mouse_preferences)
                finally:backend.close()
            except RuntimeError as error:print('Could not restore mouse settings:',error,flush=True)
        keyboard_path=Path.home()/'.config/win95lx/keyboard.json'
        if keyboard_path.exists():
            from win95lx.control_panel.keyboard_preferences import X11Keyboard,KeyboardPreferences,apply_session
            from win95lx.control_panel.preferences import PreferenceController
            try:
                controller=PreferenceController(keyboard_path,X11Keyboard(),KeyboardPreferences,lambda prefs:apply_session(Gtk.Settings.get_default(),prefs))
                controller.apply();self.keyboard_preferences=controller.applied
            except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:print('Could not restore keyboard settings:',error,flush=True)
        access_path=Path.home()/'.config/win95lx/accessibility.json'
        if access_path.exists():
            from win95lx.control_panel.access_preferences import apply_saved_session,XKBAccess
            try:apply_saved_session(access_path,XKBAccess())
            except (OSError,RuntimeError,ValueError,TypeError) as error:print('Could not restore accessibility settings:',error,flush=True)
        self.connect('realize',self.cursor)
        GLib.timeout_add_seconds(1,self.tick)
    def resize_to_display(self, screen):
        from win95lx.shell.window_bounds import fit_bounds
        width, height = screen.get_width(), screen.get_height()
        self.resize(width, height)
        scale = self.display_preferences.dpi/96
        width, height = int(width/scale), int(height/scale)
        for window in self.state.windows:
            if window.restored_bounds is not None:
                window.width, window.height = width, height-28
            window.x,window.y,window.width,window.height=fit_bounds((window.x,window.y,window.width,window.height),(width,height),resizable=window.kind in ('computer','control','printers','drive','recycle','start-folder'))

    def cursor_for(self, name):
        prefs=self.mouse_preferences
        if name in prefs.overrides and Path(prefs.overrides[name]).exists():
            path=Path(prefs.overrides[name]);data=path.read_bytes()
            hotspot=[int.from_bytes(data[10:12],'little'),int.from_bytes(data[12:14],'little')]
        else:
            frame=self.pointer_library.frame(prefs.scheme,name,(GLib.get_monotonic_time()-self.cursor_animation_epoch)/1000)
            path=self.assets/frame['file'];hotspot=frame['hotspot']
        key=(name,str(path),tuple(hotspot))
        if key not in self.cursors:
            pixbuf=GdkPixbuf.Pixbuf.new_from_file(str(path))
            self.cursors[key]=Gdk.Cursor.new_from_pixbuf(self.get_display(),pixbuf,*hotspot)
        return self.cursors[key]

    def refresh_mouse_cursors(self):
        if not self.get_window():self.cursor_animation_timer=None;return False
        self.cursor()
        for window in self.accessory_windows.values():
            if window.get_window():
                cursor=self.cursor_for('arrow')
                if window.get_window().get_cursor()!=cursor:window.get_window().set_cursor(cursor)
            view=getattr(window,'view',None)
            if isinstance(view,Gtk.TextView) and view.get_window(Gtk.TextWindowType.TEXT):
                text_window=view.get_window(Gtk.TextWindowType.TEXT);cursor=self.cursor_for('beam')
                if text_window.get_cursor()!=cursor:text_window.set_cursor(cursor)
        return True

    def cursor(self, *_):
        if _:self.cursor_animation_epoch=GLib.get_monotonic_time()
        cursor = self.cursor_for('arrow')
        if cursor:
            if self.get_window().get_cursor()!=cursor:self.get_window().set_cursor(cursor)
            root=Gdk.get_default_root_window()
            if root.get_cursor()!=cursor:root.set_cursor(cursor)
        if any(len(self.pointer_library.definition(self.mouse_preferences.scheme,role)['sequence'])>1 for role in ('arrow','beam')) and self.cursor_animation_timer is None:
            self.cursor_animation_timer=GLib.timeout_add(16,self.refresh_mouse_cursors)

    def tick(self):self.area.queue_draw();return True
    def hit(self,x,y,w,h,action):self.hits.append((x,y,w,h,action))
    def button(self,p,label,x,y,w,h,action,pressed=False):p.button(label,x,y,w,h,pressed);self.hit(x,y,w,h,action)
    def shortcut_image(self,path,default):
        from win95lx.explorer.namespace import read_shortcut
        link=read_shortcut(path)
        if not link:return default
        if link.kind=='namespace':return {'control':36,'computer':'computer','drive':9,**{applet.key:applet.key for applet in cpl_catalog.implemented()}}[link.target]
        target=Path(link.target)
        return 4 if target.is_dir() else self.drive_file_icon(target.name)

    def icon(self,p,ident,label,x,y,action,selected=False,*,image_offset=0,label_offset=0):
        shortcut=label.casefold().endswith('.desktop')
        if shortcut:
            if action[0]=='item' and action[1].kind=='drive':
                browser=self.browser_for(action[1]);ident=self.shortcut_image(browser.view.resolve(browser.directory/label),ident)
        image = self.images.get('folder-selected') if ident == 4 and selected else self.images.get(ident)
        if image is not None:
            if selected and ident!=4:p.selected_image(image,x+16+image_offset,y)
            else:p.image(image,x+16+image_offset,y)
        if shortcut and 30 in self.images:p.image(self.images[30],x+16+image_offset,y)
        if image is None and ident in self.small_images:p.image(self.small_images[ident],x+24,y+8)
        from win95lx.explorer.namespace import display_name
        if action[0]=='item' and action[1].kind=='control':
            from win95lx.shell.icon_labels import wrap_label
            lines=wrap_label(display_name(label),self.font)
            for row,line in enumerate(lines):
                width=self.font.width(line);left=x+(64-width)//2+label_offset;top=y+36+13*row
                if selected:p.fill(left-1,top+1,width+2,13,NAVY)
                p.text(line,left,top,LIGHT if selected else BLACK)
            self.hit(x,y,70,max(54,36+13*len(lines)),action);return
        label = taskbar.title_that_fits(self.font, display_name(label), ICON_WIDTH-4, False)
        width=self.font.width(label)
        if selected:
            if action[0]=='item' and action[1].kind=='computer' and action[1].focus_item in (None,action[3]):
                p.fill(x+(64-width)//2-2+label_offset,y+36,width+4,15,(255,255,0))
            p.fill(x+(64-width)//2-1+label_offset,y+37,width+2,13,NAVY)
        p.text(label,x+(64-width)//2+label_offset,y+36,SHADOW if ident=='printer-add' else LIGHT if selected else BLACK);self.hit(x,y,70,54,action)
    @property
    def drive(self):
        win = self.state.active
        return win.browser if win and win.kind == 'drive' and win.browser else self._drive

    @drive.setter
    def drive(self, browser):
        self._drive = browser

    @property
    def drive_selection(self):
        return self.drive.selection

    @drive_selection.setter
    def drive_selection(self, selection):
        self.drive.selection = selection

    @property
    def drive_anchor(self):
        return self.drive.anchor

    @drive_anchor.setter
    def drive_anchor(self, anchor):
        self.drive.anchor = anchor

    def browser_for(self, win):
        if win.browser is None:
            win.browser = DriveBrowser(self._drive.view.root)
        return win.browser

    def refresh_desktop_files(self):
        try:
            relative = self.desktop_folder.relative_to(self._drive.view.root)
            self.desktop_files = self._drive.view.entries(relative)
        except (OSError, ValueError, RuntimeError):
            self.desktop_files = []

    def open_desktop_item(self, kind):
        if not kind.startswith('file:'):
            self.open(kind)
            return
        name = kind[5:]
        folder = next((folder for label, folder in self.desktop_files if label == name), None)
        if folder is None:
            return
        relative = self.desktop_folder.relative_to(self._drive.view.root)/name
        if folder:
            self.open('drive', relative)
        else:
            self.open_drive_file(relative)

    def navigate_namespace(self,win,kind,folder=None,*,new_window=False):
        if kind in cpl_catalog.BY_KEY and kind not in ('display','printers'):self.open(kind);return
        if kind not in ('computer','control','printers','drive') or new_window or not self.browsing_preferences.single_window:
            self.open(kind,folder)
            return
        from copy import deepcopy
        browser=None
        if kind=='drive':
            browser=DriveBrowser(self._drive.view.root)
            try:browser.navigate(folder or '.')
            except (OSError,ValueError,RuntimeError) as error:
                from win95lx.apps.dialogs import message_box
                message_box(self,'Explorer',str(error),Gtk.MessageType.ERROR)
                return
        win.back_history.append((win.kind,win.title,win.folder,deepcopy(win.browser)))
        win.forward_history.clear()
        win.kind=kind;win.folder=folder;win.browser=browser
        win.title=browser.title if browser else {'computer':'My Computer','control':'Control Panel','printers':'Printers'}[kind]
        self.item_selection=None;win.focus_item=None;self.popup=None
        if kind=='printers':self.refresh_printers()
        self.state.windows.remove(win);self.state.windows.append(win)

    def navigate_history(self,win,back=True):
        from copy import deepcopy
        source,destination=(win.back_history,win.forward_history) if back else (win.forward_history,win.back_history)
        if source:
            destination.append((win.kind,win.title,win.folder,deepcopy(win.browser)))
            win.kind,win.title,win.folder,win.browser=source.pop()
            self.item_selection=None;win.focus_item=None;self.popup=None

    def open(self,kind,folder=None):
        if kind in cpl_catalog.targets().values() and kind not in ('display','printers'):
            self.launch_accessory(kind);return
        if kind == 'drive':
            try:
                folder = self._drive.view.resolve(folder or '.').relative_to(self._drive.view.root)
                self._drive.view.entries(folder)
            except (OSError, RuntimeError, ValueError) as error:
                from win95lx.apps.dialogs import message_box
                message_box(self, 'Explorer', str(error), Gtk.MessageType.ERROR)
                return
        existing = next((win for win in self.state.windows if win.kind == kind and win.folder == folder), None)
        self.state.open(kind, folder)
        if existing is None:play_event(self.assets,'Open')
        self.menu_path.clear()
        self.popup=None
        if kind == 'drive':
            if existing is None:
                self.navigate_drive(self.state.active, folder)
        if kind=='display':
            self.display_tab = 'background'
            self.state.active.width, self.state.active.height = display_settings.FRAME_SIZE
            self.resize_to_display(self.get_screen())
            self.pending_wallpaper = self.wallpaper.name
            self.pending_pattern,self.pending_pattern_rows = self.wallpaper.pattern,self.wallpaper.pattern_rows
            self.wallpaper_combo = ComboBox(tuple(mode.title() for mode in background.MODES),
                                            background.MODES.index(self.wallpaper.mode))
            self.wallpaper_scroll = min(self.wallpaper.names.index(self.pending_wallpaper),
                                        self.wallpaper_max_scroll)
            self.wallpaper_error = False
            self.applied_resolution = self.pending_resolution = (self.get_screen().get_width(), self.get_screen().get_height())
            self.pending_display = self.display_preferences
            self.reset_display_combos()
            self.resolution_focus = None
            self.resolution_error = ''
        if kind=='printers':self.refresh_printers()
        self.resize_to_display(self.get_screen())
        self.area.queue_draw()
    def printer_namespace(self):
        if not hasattr(self,'printer_provider'):
            from win95lx.apps.printers import PrinterNamespace
            self.printer_provider=PrinterNamespace()
        return self.printer_provider

    def refresh_printers(self):
        if getattr(self,'printer_loading',False):return
        provider=self.printer_namespace();self.printer_loading=True
        def work():
            try:result,error=provider.load(),None
            except Exception as exc:result,error=None,str(exc)
            def publish():
                self.printer_loading=False
                if not self.get_realized():return False
                if error:provider.error=error;provider.printers=()
                else:provider.publish(result)
                self.area.queue_draw();return False
            GLib.idle_add(publish)
        Thread(target=work,name='win95lx-printer-inventory',daemon=True).start()

    def apply_mouse_preferences(self,prefs):
        prefs.validate()
        if prefs.scheme not in self.pointer_library.names:raise ValueError('The selected pointer scheme is not installed.')
        for path in prefs.overrides.values():
            if not Path(path).is_file():raise FileNotFoundError('The selected pointer file cannot be found.')
            GdkPixbuf.Pixbuf.new_from_file(str(path))
        self.mouse_preferences=prefs;self.cursor_animation_epoch=GLib.get_monotonic_time()
        if self.cursor_animation_timer:GLib.source_remove(self.cursor_animation_timer);self.cursor_animation_timer=None
        Gtk.Settings.get_default().set_property('gtk-double-click-time',prefs.double_click_ms)
        self.cursors.clear()
        if self.get_window():self.cursor()
        for window in self.accessory_windows.values():
            if window.get_window():
                cursor=self.cursor_for('arrow')
                if window.get_window().get_cursor()!=cursor:window.get_window().set_cursor(cursor)
            view=getattr(window,'view',None)
            if isinstance(view,Gtk.TextView) and view.get_window(Gtk.TextWindowType.TEXT):
                text_window=view.get_window(Gtk.TextWindowType.TEXT);cursor=self.cursor_for('beam')
                if text_window.get_cursor()!=cursor:text_window.set_cursor(cursor)

    def launch_accessory(self, kind):
        self.state.start_open = False
        self.menu_path.clear()
        self.popup = None
        window = self.accessory_windows.get(kind)
        if window is None:
            try:
                window = accessories.build(kind, self)
            except (ImportError, AttributeError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                if kind in cpl_catalog.BY_KEY:
                    from win95lx.apps.dialogs import message_box
                    message_box(self,cpl_catalog.BY_KEY[kind].label+' Properties',str(error),Gtk.MessageType.ERROR)
                    return
                print(f'Could not start {kind}: {error}', flush=True)
                self.state.dialog = 'run'
                self.dialog_error = 'This program could not be started.'
                return
            self.accessory_windows[kind] = window
            window.connect('destroy', self.accessory_closed, kind)
            play_event(self.assets,'Open')
            window.connect('notify::title', lambda *_: self.area.queue_draw())
            window.connect('notify::is-active', lambda *_: self.area.queue_draw())
        window.show_all()
        window.present()

    def accessory_closed(self, window, kind):
        play_event(self.assets,'Close')
        del self.accessory_windows[kind]
        if self.get_window():
            self.get_window().focus(Gdk.CURRENT_TIME)
        self.area.queue_draw()

    def draw(self,area,cr):
        self.pointer_scale = self.display_preferences.dpi/96
        pixel_width,pixel_height = area.get_allocated_width(),area.get_allocated_height()
        width,height = int(pixel_width/self.pointer_scale),int(pixel_height/self.pointer_scale)
        palette = self.display_preferences.palette
        if palette == 3:
            target = cr
        else:
            frame = cairo.ImageSurface(cairo.FORMAT_RGB24,pixel_width,pixel_height)
            target = cairo.Context(frame)
        target.save()
        target.scale(self.pointer_scale,self.pointer_scale)
        try:
            self.draw_desktop(Painter(target,self.font),width,height)
        finally:
            target.restore()
        if palette != 3:
            cr.set_source_surface(color_surface(frame,palette),0,0)
            cr.paint()

    def draw_desktop(self, p, width, height):
        self.width, self.height = width, height
        self.hits = []
        p.fill(0,0,width+1,height+1,TEAL)
        if self.state.dialog == 'shutdown':
            self.shutdown_dialog.draw(self, p)
            return
        if self.suspended:
            p.fill(0,0,width,height,BLACK)
            return
        paint_pattern(p,self.wallpaper.pattern_rows,0,0,width,height)
        paint_wallpaper(p, self.wallpaper_images.get(self.wallpaper.name),
                        self.wallpaper.mode, 0, 0, width, height)
        desktop_items = (
            ('computer' if 'computer' in self.images else 16, 'My Computer', 'computer'),
            (33 if self.trash.entries() else 32, 'Recycle Bin', 'recycle'),
        )
        occupied = [self.desktop_icons.position(name,width,height) for name in ('computer','recycle')]
        occupied.extend(self.desktop_icons.position(name,width,height)
                        for name in self.desktop_icons.positions if name.startswith('file:'))
        slots = tuple(desktop_file_slots(self.desktop_files, height, occupied))
        self.desktop_file_defaults = {f'file:{label}': point for label, _, point in slots}
        desktop_items += tuple((4 if folder else self.drive_file_icon(label), label, f'file:{label}')
                               for label, folder, _ in slots)
        for ident,label,kind in desktop_items:
            x, y = self.desktop_icons.position(kind, width, height, self.desktop_file_defaults.get(kind))
            if self.icon_drag and self.icon_drag[0] == kind and self.icon_drag_point is not None:
                x, y = self.icon_drag_point
            shortcut=kind.startswith('file:') and label.casefold().endswith('.desktop')
            if shortcut:ident=self.shortcut_image(self.desktop_folder/label,ident)
            if ident in self.images:
                if self.state.selection==kind:p.selected_image(self.images[ident],x+21,y)
                else:p.image(self.images[ident], x+21, y)
            if shortcut and 30 in self.images:p.image(self.images[30],x+21,y)
            from win95lx.explorer.namespace import display_name
            label = taskbar.title_that_fits(self.font, display_name(label), ICON_WIDTH-4, False)
            label_width=self.font.width(label)
            label_x=x+37-label_width//2
            selected=self.state.selection==kind
            if kind.startswith('file:'):
                selected = selected or self.file_hover == (None,self.desktop_folder.relative_to(self._drive.view.root)/kind[5:])
            elif kind == 'recycle':
                selected = selected or self.file_hover == (None,RECYCLE_TARGET)
            if selected:
                p.fill(label_x-1,y+35,label_width+2,15,NAVY)
            p.text(label,label_x,y+35,LIGHT)
            self.hit(x,y,ICON_WIDTH,ICON_HEIGHT,('desktop',kind))
        for win in self.state.windows:
            if not win.minimized:self.window(p,win)
        if self.file_drag and self.file_drag_point:
            win,label,start_x,start_y = self.file_drag
            gx,gy = self.file_drag_point
            browser = self.browser_for(win)
            directory = next((folder for name,folder in browser.entries if name == label),False)
            icon = self.images.get(4 if directory else self.drive_file_icon(label))
            if icon:
                _,point,_,_=self.file_drag_origin
                ix=win.x+explorer_chrome.PANE_X+point[0]+16+gx-start_x
                iy=win.y+explorer_chrome.PANE_Y+point[1]+gy-start_y
                p.drag_image(icon,ix,iy)
        bar=height-28
        p.fill(0,bar,width,28,FACE)
        p.fill(0,bar+1,width,1,LIGHT)
        start_image=self.images.get('start-down' if self.state.start_open else 'start-up')
        if start_image:
            p.image(start_image,2,bar+4)
        else:
            self.draw_start_button(p,bar)
        self.hit(2,bar+4,54,22,('start',))
        tray = self.display_preferences.tray
        language=bool(self.keyboard_preferences and self.keyboard_preferences.indicator and len(self.keyboard_preferences.layouts)>1)
        volume=bool(self.audio_preferences.tray)
        self.draw_tasks(p, bar, width-(95 if tray else 75)-(24 if language else 0)-(24 if volume else 0))
        if language:
            from win95lx.control_panel.keyboard_preferences import KeyboardGroups
            try:
                if self.keyboard_groups is None:self.keyboard_groups=KeyboardGroups()
                index=self.keyboard_groups.current();code=self.keyboard_preferences.layouts[min(index,len(self.keyboard_preferences.layouts)-1)]
            except RuntimeError:code=self.keyboard_preferences.layouts[0]
            left=width-(112 if tray else 88)-(24 if volume else 0)
            p.fill(left,bar+6,19,17,NAVY);p.text({'us':'En','gb':'En','de':'De','fr':'Fr','es':'Es'}.get(code,code[:2].title()),left+2,bar+8,LIGHT)
            self.hit(left,bar+4,22,22,('keyboard-language-menu',))
        if tray:
            p.bevel(width-88,bar+4,22,22,True)
            icon = self.small_images.get('display') or self.images.get('display')
            if icon:
                p.cr.save()
                p.cr.translate(width-85,bar+7)
                p.cr.scale(16/icon.get_width(),16/icon.get_height())
                p.image(icon,0,0)
                p.cr.restore()
            self.hit(width-88,bar+4,22,22,('display-tray-open',))
        if volume:
            left=width-(112 if tray else 88)
            icon=self.small_images.get('volume-muted' if self.audio_muted else 'volume')
            if icon:p.image(icon,left+3,bar+7)
            self.hit(left,bar+4,22,22,('volume-tray-open',left))
        p.fill(width-69,bar+4,1,22,SHADOW)
        p.fill(width-68,bar+4,1,22,LIGHT)
        p.bevel(width-65,bar+4,63,22,True)
        from win95lx.control_panel.regional_preferences import current as current_regional
        clock=self.clock or current_regional().short_time(datetime.datetime.now())
        p.text(clock,width-34-self.font.width(clock)//2,bar+8)
        self.menu_hit_start=len(self.hits)
        if self.state.start_open:self.startmenu(p)
        if self.state.start_open:
            self.submenu_draw(p)
        if self.popup:self.context(p,*self.popup)
        if self.start_context:
            self.start_context.draw(p)
        if self.state.dialog:self.dialog(p)

    def draw_tasks(self, painter, bar, right_edge):
        internal = self.state.windows
        native = {window: kind for kind, window in self.accessory_windows.items()}
        open_tasks = [*internal, *native]
        self.task_order = [window for window in self.task_order
                           if any(window is task for task in open_tasks)]
        self.task_order.extend(window for window in open_tasks
                               if not any(window is task for task in self.task_order))
        active_native = next((window for window in native if window.is_active()), None)
        self.active_task = active_native if active_native is not None else self.state.active
        width = taskbar.button_width(len(self.task_order), right_edge)
        if width < 5:
            return
        for index, window in enumerate(self.task_order):
            x = taskbar.START_X+index*(width+taskbar.BUTTON_GAP)
            if isinstance(window, Gtk.Window):
                title, icon = window.get_title(), native[window]
                action = ('accessory-task', window)
            else:
                title = window.title
                icon = {'computer':'computer', 'control':36, 'drive':9, 'display':'display',
                        'system':'computer', 'recycle':32, 'start-folder':4}.get(window.kind)
                action = ('task', window)
            image = self.small_images.get(icon) or self.images.get(icon)
            taskbar.draw_task_button(painter, title, image, x, bar+4, width, window is self.active_task)
            self.hit(x, bar+4, width, taskbar.BUTTON_HEIGHT, action)

    def draw_start_button(self,p,bar):
        p.bevel(2,bar+4,54,22,self.state.start_open)
        if 'start' in self.images:
            p.image(self.images['start'],6,bar+7)
        elif 40 in self.small_images:
            p.image(self.small_images[40],6,bar+7)
        elif 40 in self.images:
            p.cr.save();p.cr.translate(6,bar+7);p.cr.scale(.5,.5);p.image(self.images[40],0,0);p.cr.restore()
        p.text('Start',25,bar+8,bold=True)
    def window(self,p,win):
        browser = self.browser_for(win) if win.kind == 'drive' else None
        x, y, w, h = computer_view.geometry(win) if win.kind in ('computer','control','printers') else (win.x,win.y,win.width,win.height)
        explorer = win.kind in ('computer','control','printers','drive','recycle','start-folder')
        resizable = explorer or win.kind == 'notepad'
        active = win is self.state.active
        p.window_frame(x,y,w,h)
        p.fill(x+4,y+4,w-8,18,NAVY if active else SHADOW)
        p.cr.save()
        p.cr.rectangle(x+(24 if resizable else 7),y+4,w-(85 if resizable else 32),18)
        p.cr.clip()
        p.text(win.title,x+(24 if resizable else 7),y+(6 if resizable else 4),LIGHT,bold=True)
        p.cr.restore()
        ident = {'computer':'computer' if 'computer' in self.images else 16,'control':36,
                 'printers':'cpl-printers','drive':9,'notepad':2,'recycle':32,'start-folder':4}.get(win.kind)
        if resizable and ident in self.small_images:
            p.cr.save()
            p.cr.rectangle(x+5,y+5,15 if win.kind=='computer' else 16,16);p.cr.clip()
            p.image(self.small_images[ident],x+5,y+5)
            p.cr.restore()
        elif resizable and ident in self.images:
            p.cr.save()
            p.cr.translate(x+5,y+5)
            p.cr.scale(.5,.5)
            p.image(self.images[ident],0,0)
            p.cr.restore()
        self.hit(x,y,w,22,('drag',win))
        if ident is not None:
            self.hit(x+4,y+4,18,18,('system-menu',win))
        buttons = [(w-21,'close','close')]
        if resizable:
            buttons.extend((
                (w-55,'minimize','minimize'),
                (w-39,'restore' if win.restored_bounds else 'maximize','maximize'),
            ))
        for offset, symbol, action in buttons:
            if win.kind in ('computer','control','printers') and win.restored_bounds is not None:offset-=1
            p.caption_button(symbol,x+offset,y+6)
            self.hit(x+offset,y+6,16,14,(action,win))
        if explorer:
            if win.kind in ('control','printers') or win.kind=='computer' and (win.toolbar or win.address_bar or win.web_view):
                from copy import copy
                frame=copy(win);frame.x,frame.y,frame.width,frame.height=x,y,w,h
                explorer_chrome.draw(p,frame,self.explorer_menu_art,
                    lambda hx,hy,hw,hh,action:self.hit(hx,hy,hw,hh,
                        (action[0],win,*action[2:]) if len(action)>1 and action[1] is frame else action))
                computer_view.draw(self,p,win)
                return
            explorer_chrome.draw(p, win, self.explorer_menu_art, self.hit)
            items={'computer':[(9,'(C:)','drive'),(36,'Control Panel','control')],'control':cpl_catalog.entries(),'recycle':[]}.get(win.kind)
            if win.kind == 'start-folder':
                items = [(icon, label, ('start-folder', action[1]) if action[0] == 'submenu' else action)
                         for label, icon, action in self.shortcut_folders.entries(win.folder)]
            columns = 4
            if win.kind == 'recycle':
                items = [(4 if directory else self.drive_file_icon(original.name), original.name,
                          ('trash-entry',key)) for key,original,directory in self.trash.entries()]
            if win.kind == 'drive':
                pane_width, pane_height = self.drive_pane_size(win)
                columns, _, maximum = browser.grid(pane_width, pane_height)
                items = [(4 if directory else self.drive_file_icon(name), name, ('drive-entry', win, name, directory))
                         for name, directory in browser.page(pane_width, pane_height)]
                if maximum:
                    self.draw_drive_scrollbar(p, win, pane_height, maximum)
            for i,(ident,label,kind) in enumerate(items or []):
                point = (10+(i%columns)*102, 10+(i//columns)*69)
                if win.kind == 'start-folder':
                    point = self.shortcut_position(win, label, point)
                elif win.kind == 'drive':
                    point = browser.icon_position(i, columns)
                    point = self.shortcut_icons.position(
                        'drive:'+str(browser.view.resolve(browser.directory)), label, point)
                xx, yy = x+explorer_chrome.PANE_X+point[0], y+explorer_chrome.PANE_Y+point[1]
                if win.kind == 'drive':
                    left, top = x+explorer_chrome.PANE_X, y+explorer_chrome.PANE_Y
                    pane_width,pane_height = self.drive_pane_size(win)
                    pane_width -= 16 if maximum else 0
                    p.cr.save()
                    p.cr.rectangle(left,top,pane_width,pane_height)
                    p.cr.clip()
                self.icon(p, ident, label, xx, yy, ('item', win, kind, label, point),
                          (label in browser.selection or self.file_hover == (win,browser.directory/label) if win.kind == 'drive' else self.item_selection in ((win,label),(win,None))) or self.shortcut_drop == (win, label))
                if win.kind == 'drive':
                    p.cr.restore()
                    hx,hy,hw,hh,action = self.hits.pop()
                    clip_x,clip_y = max(hx,left),max(hy,top)
                    clip_right,clip_bottom = min(hx+hw,left+pane_width),min(hy+hh,top+pane_height)
                    if clip_x < clip_right and clip_y < clip_bottom:
                        self.hit(clip_x,clip_y,clip_right-clip_x,clip_bottom-clip_y,action)
            count = len(browser.entries) if win.kind == 'drive' else len(items or [])
            p.bevel(x+4,y+h-19,w-8,15,True)
            p.text(str(count)+' object(s)',x+8,y+h-18)
        elif win.kind=='display':
            if self.display_tab == 'background':
                background.draw(p, win, self)
                return
            display_settings.draw(p, win, self)
        elif win.kind in APPLETS:APPLETS[win.kind](p,win,self.button)
    @staticmethod
    def drive_pane_size(win):
        return (win.width-2*explorer_chrome.PANE_X,
                win.height-explorer_chrome.PANE_Y-explorer_chrome.PANE_BOTTOM)

    def draw_drive_scrollbar(self, p, win, height, maximum):
        browser = self.browser_for(win)
        x = win.x+win.width-explorer_chrome.PANE_X-SCROLLBAR_WIDTH
        y = win.y+explorer_chrome.PANE_Y
        bar = VerticalScrollbar(height, maximum)
        bar.draw(p, x, y, browser.scroll)
        thumb = bar.thumb_top(browser.scroll)
        _, rows, _ = browser.grid(*self.drive_pane_size(win))
        self.hit(x, y, SCROLLBAR_WIDTH, bar.arrow, ('drive-scroll', win, -1))
        self.hit(x, y+bar.arrow, SCROLLBAR_WIDTH, thumb-bar.arrow, ('drive-scroll', win, -rows))
        self.hit(x, y+thumb, SCROLLBAR_WIDTH, bar.thumb, ('drive-thumb', win, y+thumb))
        end = height-bar.arrow
        self.hit(x, y+thumb+bar.thumb, SCROLLBAR_WIDTH, end-thumb-bar.thumb,
                 ('drive-scroll', win, rows))
        self.hit(x, y+end, SCROLLBAR_WIDTH, bar.arrow, ('drive-scroll', win, 1))

    def navigate_drive(self, win, directory):
        from win95lx.apps.dialogs import message_box

        browser = self.browser_for(win)
        try:
            browser.navigate(directory)
        except (OSError, RuntimeError) as error:
            message_box(self, '(C:)', str(error), Gtk.MessageType.ERROR)
            return
        win.folder = browser.directory
        win.title = browser.title
        browser.selection.clear()
        browser.anchor = None
        self.refresh_desktop_files()
        self.item_selection = None
        self.popup = None

    def edit_drive_selection(self, name, modifiers):
        names = [entry[0] for entry in self.drive.entries]
        if modifiers & Gdk.ModifierType.SHIFT_MASK and self.drive_anchor in names:
            start, end = sorted((names.index(self.drive_anchor), names.index(name)))
            self.drive_selection.update(names[start:end+1])
        elif modifiers & Gdk.ModifierType.CONTROL_MASK:
            self.drive_selection.symmetric_difference_update((name,))
            self.drive_anchor = name
        else:
            self.drive_selection = {name}
            self.drive_anchor = name

    def drive_edit(self, win, command):
        from win95lx.apps.dialogs import message_box

        browser = self.browser_for(win)
        directory = browser.directory
        sources = tuple(directory/name for name in sorted(browser.selection))
        if self.popup is not None:play_event(self.assets,'MenuCommand')
        self.popup = None
        if command in ('open','explore'):
            for source in sources:
                if browser.view.resolve(source).is_dir():self.open('drive',source)
                else:self.open_drive_file(source)
            return
        if command=='find':
            self.action(('find',))
            return
        if command in ('cut', 'copy'):
            if sources:
                self.file_clipboard = FileClipboard(sources, command == 'cut')
            return
        if command in ('select-all', 'invert'):
            all_names = {name for name, _ in browser.entries}
            browser.selection = all_names if command == 'select-all' else all_names-browser.selection
            return
        try:
            if command=='shortcut':
                from win95lx.explorer.namespace import create_file_shortcut
                for source in sources:create_file_shortcut(browser.view.resolve(directory),browser.view.resolve(source))
                self.refresh_file_views()
            elif command=='paste-shortcut':
                from win95lx.explorer.namespace import create_file_shortcut
                for source in self.file_clipboard.sources:create_file_shortcut(browser.view.resolve(directory),browser.view.resolve(source))
                self.refresh_file_views()
            elif command == 'paste' and self.file_clipboard.sources:
                remaining = self.transfer_files(self.file_clipboard.sources, directory,
                                                copy=not self.file_clipboard.move)
                if self.file_clipboard.move:
                    self.file_clipboard = FileClipboard(remaining, True)
            elif command in ('new-folder','rename') and (command == 'new-folder' or len(sources) == 1):
                folder = browser.view.resolve(directory)
                original = sources[0].name if command == 'rename' else 'New Folder'
                shortcut_rename=command=='rename' and original.casefold().endswith('.desktop')
                if shortcut_rename:original=Path(original).stem
                label = 'Rename' if command == 'rename' else 'New Folder'
                from win95lx.apps.dialogs import name_dialog
                name = name_dialog(self, label, original)
                if name is not None and (command != 'rename' or name != original):
                    if shortcut_rename and not name.casefold().endswith('.desktop'):name+='.desktop'
                    target = folder/child_name(name)
                    if command == 'rename':
                        move_entry(folder/sources[0].name, target)
                    else:
                        target.mkdir()
                    self.refresh_file_views()
                    browser.selection = {name}
                    browser.anchor = name
            elif command == 'properties' and len(sources) == 1:
                path = browser.view.resolve(sources[0].parent)/sources[0].name
                info = path.lstat()
                label = 'Folder' if path.is_dir() else 'File'
                message_box(self, f'{path.name} Properties', f'{label}: {path.name}\nSize: {info.st_size:,} bytes',
                            Gtk.MessageType.INFO)
            elif command == 'trash' and sources:
                self.trash_files(sources)
        except (OSError, ValueError, RuntimeError, GLib.Error) as error:
            message_box(self, 'Explorer', str(error), Gtk.MessageType.ERROR)
            self.navigate_drive(win, directory)

    @staticmethod
    def drive_file_icon(name):
        suffix = Path(name).suffix.casefold()
        if suffix == '.rtf':
            return 'wordpad'
        if suffix=='.txt':return 152
        if suffix=='.ini':return 151
        if suffix in ('.conf', '.log', '.md'):
            return 152
        return 1

    def open_drive_entry(self, win, name, directory, new_window=False):

        relative = self.browser_for(win).directory/name
        if directory:
            self.navigate_namespace(win,'drive',relative,new_window=new_window)
        else:
            self.open_drive_file(relative)

    def open_drive_file(self, relative):
        from win95lx.apps.dialogs import message_box

        try:
            path = self._drive.view.resolve(relative)
            if not path.is_file():
                raise OSError('This item is not a regular file.')
        except (OSError, RuntimeError) as error:
            message_box(self, '(C:)', str(error), Gtk.MessageType.ERROR)
            return
        if path.suffix.casefold()=='.desktop':
            from win95lx.explorer.namespace import resolve_shortcut
            try:
                target=resolve_shortcut(path)
                if target.kind=='namespace':self.open(target.target)
                else:
                    destination=Path(target.target).relative_to(self._drive.view.root)
                    if Path(target.target).is_dir():self.open('drive',destination)
                    else:self.open_drive_file(destination)
            except (OSError,ValueError,RuntimeError) as error:
                message_box(self,'Problem with Shortcut',str(error),Gtk.MessageType.ERROR)
            return
        if path.suffix.casefold() == '.rtf':
            kind, load = 'wordpad', 'load'
        elif path.suffix.casefold() in ('.txt', '.ini', '.conf', '.log', '.md'):
            kind, load = 'notepad', 'open_path'
        else:
            message_box(self, '(C:)', 'There is no Win95LX app associated with this file.',
                        Gtk.MessageType.INFO)
            return
        existing = self.accessory_windows.get(kind)
        if existing is not None and not existing.confirm_discard():
            return
        self.launch_accessory(kind)
        window = self.accessory_windows.get(kind)
        if window is not None:
            getattr(window, load)(path)

    @staticmethod
    def clamp_shortcut(win, x, y):
        return (max(0, min(x, win.width-2*explorer_chrome.PANE_X-ICON_WIDTH)),
                max(0, min(y, win.height-explorer_chrome.PANE_Y-explorer_chrome.PANE_BOTTOM-ICON_HEIGHT)))

    def shortcut_position(self, win, label, default):
        if self.shortcut_drag and self.shortcut_drag[:2] == (win, label):
            if self.shortcut_drag_point is not None:
                return self.shortcut_drag_point
        return self.clamp_shortcut(win, *self.shortcut_icons.position(win.folder, label, default))

    def menu_origin(self):
        return 2, self.height - menu.HEIGHT - 24

    def startmenu(self, p):
        x, y = self.menu_origin()
        p.window_frame(x,y,menu.WIDTH,menu.HEIGHT)
        p.fill(x+menu.WIDTH-1,y,1,1,BLACK)
        p.fill(x,y+menu.HEIGHT-1,1,1,BLACK)
        p.fill(x+3,y+3,21,menu.HEIGHT-6,SHADOW)
        if 'banner' in self.images:
            p.image(self.images['banner'],x+3,y+menu.HEIGHT-133)
        separator = y+258
        p.fill(x+26,separator,117,1,SHADOW)
        p.fill(x+26,separator+1,117,1,LIGHT)
        for index,(label,icon,mnemonic,action) in enumerate(menu.ROWS):
            row_y = menu.row_top(y,index)
            selected = index == self.state.menu_index
            color = LIGHT if selected else BLACK
            if selected:
                p.fill(x+24,row_y,121,menu.ROW_HEIGHT,NAVY)
            image = self.images.get(icon) or self.images.get(menu.FALLBACK_ICONS.get(icon))
            if image:
                p.image(image,x+29,row_y+(3 if index==2 else 2)-(1 if index>=7 else 0))
            text_y = row_y+(11 if index>=7 else 12)
            p.text(label,x+63,text_y,color)
            position = label.lower().find(mnemonic)
            if position>=0:
                underline_x=x+63+self.font.width(label[:position])
                p.fill(underline_x,text_y+12,self.font.width(label[position]),1,color)
            if index in menu.SUBMENUS:
                for column,height in enumerate((7,5,3,1)):
                    p.fill(x+137+column,row_y+17-height//2,1,height,color)
            self.hit(x+24,row_y,121,menu.ROW_HEIGHT,action or ('menu',index))

    def submenu_entries(self, key):
        if key == 2:
            documents = RecentDocuments().entries()
            duplicate_names = {path.name for path in documents if sum(other.name == path.name for other in documents)>1}
            return (('My Documents',4,('documents-folder',)),)+tuple(((path.stem if path.suffix.lower() in ('.txt','.rtf') else path.name)+(f' ({path.parent.name})' if path.name in duplicate_names else ''),
                          self.drive_file_icon(path.name), ('recent-document',str(path)))
                         for path in documents)
        return self.shortcut_folders.entries(key) or (('(Empty)', None, ('empty',)),)

    def submenu_geometry(self):
        x, y = self.menu_origin()
        width = menu.WIDTH
        row_y = menu.row_top(y, self.state.menu_index)
        for key, selected in self.menu_path:
            options = self.submenu_entries(key)
            height = 6 + 20 * len(options)
            x = min(x + width - 3, self.width - 154)
            y = min(row_y - 3, self.height - 28 - height)
            width = 154
            yield x, y, width, height
            row_y = y + 3 + selected * 20

    def submenu_draw(self, p):
        for depth, ((key, selection), geometry) in enumerate(zip(self.menu_path, self.submenu_geometry())):
            x, y, width, height = geometry
            p.window_frame(x, y, width, height)
            for row, (label, icon, action) in enumerate(self.submenu_entries(key)):
                yy = y + 3 + row * 20
                selected = selection == row
                color = LIGHT if selected else BLACK
                if selected:
                    p.fill(x+3, yy, width-6, 20, NAVY)
                image = self.small_images.get(icon)
                if image:
                    p.image(image, x+5, yy+2)
                elif icon in self.images:
                    p.cr.save()
                    p.cr.translate(x+5, yy+2)
                    p.cr.scale(.5, .5)
                    p.image(self.images[icon], 0, 0)
                    p.cr.restore()
                p.text(label, x+24, yy+3, color)
                if action[0] == 'submenu':
                    for column, arrow_height in enumerate((7, 5, 3, 1)):
                        p.fill(x+width-10+column, yy+9-arrow_height//2, 1, arrow_height, color)
                self.hit(x+3, yy, width-6, 20, ('submenu-row', depth, row))

    def select_submenu_row(self, depth, row, *, hover=False):
        key, current = self.menu_path[depth]
        action = self.submenu_entries(key)[row][2]
        if row != current:
            self.menu_path[depth:] = [(key, row)]
        if action[0] == 'submenu':
            if len(self.menu_path) == depth + 1:
                self.menu_path.append((action[1], 0))
        elif not hover:
            play_event(self.assets,'MenuCommand')
            self.action(action)

    def show_start(self):
        self.start_context = None
        self.state.start_open = not self.state.start_open
        self.state.menu_index = -1
        self.popup = None
        self.menu_path.clear()
        if self.state.start_open:play_event(self.assets,'MenuPopup')

    def choose_menu_row(self, index):
        self.state.menu_index = index
        if index in menu.SUBMENUS:
            self.menu_path[:] = [(index, 0)]
        else:
            play_event(self.assets,'MenuCommand')
            self.action(menu.ROWS[index][3])

    def namespace_file_rows(self,win):
        selection=(self.item_selection[1] or '*') if self.item_selection and self.item_selection[0] is win else None
        if win.kind=='computer':return explorer_menu.computer_file_rows(self.work_offline,selection)
        from win95lx.explorer.commands import Context,Item,file_commands,Command
        if win.kind=='printers':
            return (Command('Open','open','o',selection is not None),None,Command('Close','close','c',True))
        names=() if selection is None else cpl_catalog.labels() if selection=='*' else (selection,)
        return file_commands(Context('control',tuple(Item('applet',name,False) for name in names)))

    def context(self,p,x,y,kind):
        if isinstance(kind, tuple):
            win, menu = kind
            browser = self.browser_for(win) if win.kind == 'drive' else None
            if win.kind in ('computer','control','printers') and menu == 'File':
                self.drive_menu_rows = explorer_menu.draw(
                    p,x,y,self.namespace_file_rows(win),
                    self.drive_menu_highlight,self.images.get('menu-check'),self.hit,win)
                return
            options = {
                'File': [('Close',('close',win))],
                'Edit': [('Select All',('select-all',win))],
                'View': ([('Standard Buttons',('computer-view-toggle',win,'toolbar')),
                          ('Address Bar',('computer-view-toggle',win,'address_bar')),
                          ('as Web Page',('computer-view-toggle',win,'web_view')),
                          ('Refresh',('dismiss',))] if win.kind in ('computer','control','printers') else [('Refresh',('dismiss',))]),
                'Go': [('My Computer',('open','computer')),('(C:)',('open','drive'))],
                'Favorites': [('Control Panel',('open','control'))],
                'Help': [('About Win95LX',('about',))],
                'Item': [],
            }[menu]
            if win.kind in ('computer','control','printers') and menu=='View':
                options=options[:-1]+[(label,('namespace-view',win,mode)) for mode,label in
                    (('large','Large Icons'),('small','Small Icons'),('list','List'),('details','Details'))]+[
                    ('Auto Arrange',('namespace-auto',win)),('Refresh',('dismiss',))]
            if win.kind=='printers' and menu=='View':
                options=[(label,('printer-refresh',) if action==('dismiss',) else action) for label,action in options]
            if win.kind == 'recycle' and menu == 'File':
                options = [('Restore',('trash-command','restore')),
                           ('Empty Recycle Bin',('trash-command','empty')),
                           ('Close',('close',win))]
            if win.kind == 'drive' and menu in ('File','Edit','Item'):
                self.drive_menu(p, x, y, win, menu)
                return
            if win.kind == 'drive':
                if menu == 'View':
                    options = [('Refresh', ('drive-navigate', win, browser.directory))]
                elif menu == 'Go' and browser.directory != Path('.'):
                    options.insert(0, ('Up One Level', ('drive-navigate', win, browser.directory.parent)))
            if menu == 'Go' and win.kind == 'start-folder' and win.folder is not None:
                parent = {0:None, 'accessories':0, 'games':'accessories'}[win.folder]
                options.insert(0, ('Up One Level', ('start-folder', parent)))
        elif kind and kind.startswith('file:'):
            options = [('Open', ('open',kind))]
        else:options=[('Open',('open',kind)),('Properties',('open','system' if kind=='computer' else 'display'))] if kind else [('Properties',('open','display')), ('Refresh',('desktop-refresh',)), ('New Folder',('desktop-new-folder',))]
        if isinstance(kind, tuple):
            width = popup_width(self.font, [label for label, _ in options])
            p.window_frame(x, y, width, len(options)*POPUP_ROW_HEIGHT+6)
            for index, (label, action) in enumerate(options):
                row = y+3+index*POPUP_ROW_HEIGHT
                checked=(action[0]=='namespace-view' and action[1].namespace_view==action[2]
                         or action[0]=='namespace-auto' and action[1].namespace_auto
                         or action[0]=='computer-view-toggle' and getattr(action[1],action[2]))
                if checked and 'menu-check' in self.images:p.image(self.images['menu-check'],x+5,row+4)
                p.text(label, x+POPUP_GUTTER, row+1)
                self.hit(x+3, row, width-6, POPUP_ROW_HEIGHT, action)
        else:
            p.bevel(x,y,130,len(options)*22+6)
            for i,(label,action) in enumerate(options):
                p.text(label,x+8,y+6+i*22)
                self.hit(x+3,y+3+i*22,124,22,action)

    def drive_menu(self, p, x, y, win, menu):
        browser = self.browser_for(win)
        selected = bool(browser.selection)
        single = len(browser.selection) == 1
        cut_copy_paste = (('Cut','Ctrl+X','cut',selected), ('Copy','Ctrl+C','copy',selected),
                          ('Paste','Ctrl+V','paste',bool(self.file_clipboard.sources)))
        file_rows = (('New Folder','','new-folder',True), ('Delete','','trash',selected),
                     ('Rename','','rename',single), ('Properties','','properties',single))
        if selected and menu=='File':
            from win95lx.explorer.commands import Context,Item,file_commands
            entries=tuple(Item('folder' if browser.view.resolve(browser.directory/name).is_dir() else 'shortcut' if name.casefold().endswith('.desktop') else 'file',name) for name in sorted(browser.selection))
            profile=file_commands(Context('filesystem',entries))
            file_rows=tuple(None if row is None else (row.label,'',row.command,row.enabled) for row in profile[:-2])
        from win95lx.explorer.edit_commands import EditContext,edit_rows
        import os
        edit_context=EditContext(len(browser.selection),len(browser.entries),
            bool(self.file_clipboard.sources),os.access(browser.view.resolve(browser.directory),os.W_OK))
        rows = {
            'Edit': edit_rows(edit_context),
            'File': (*file_rows, None, ('Close','','close',True)),
            'Item': (*cut_copy_paste, None, *file_rows),
        }[menu]
        width = 122 if menu == 'File' else 154 if menu == 'Edit' else 156
        height = (5 if menu=='Edit' else 4)+sum(9 if row is None else 17 for row in rows)
        x, y = max(0,min(x,self.width-width)), max(0,min(y,self.height-height))
        p.window_frame(x,y,width,height)
        self.drive_menu_rows = []
        self.hit(x,y,width,height,('dismiss',))
        top = y+2
        for row in rows:
            if row is None:
                p.fill(x+2,top+(3 if menu=='Edit' else 4),width-4,1,SHADOW)
                p.fill(x+2,top+(4 if menu=='Edit' else 5),width-4,1,LIGHT)
                top += 9
                continue
            label, shortcut, command, enabled = row
            action = None
            if enabled:
                action = ('close',win) if command == 'close' else ('drive-edit',win,command)
                self.hit(x+2,top,width-4,17,action)
            selected = self.drive_menu_highlight == command and enabled
            if selected:
                p.fill(x+2,top,width-4,17,NAVY)
            color = LIGHT if selected else BLACK if enabled else SHADOW
            tx,ty=(-1,1) if menu=='Edit' else (0,0)
            mnemonic={'new-folder':'n','trash':'d','rename':'m','properties':'r','close':'c',
                      'undo':'u','cut':'t','copy':'c','paste':'p','paste-shortcut':6,'select-all':'a','invert':'i'}.get(command)
            if not enabled:
                p.menu_text(label,x+25+tx,top+1+ty,LIGHT,mnemonic)
                p.text(shortcut,x+107+tx,top+1+ty,LIGHT)
            if command=='open':p.text(label,x+24,top,color,bold=True)
            else:p.menu_text(label,x+24+tx,top+ty,color,mnemonic)
            p.text(shortcut,x+106+tx,top+ty,color)
            if action:
                self.drive_menu_rows.append((x+2,top,command,action))
            top += 17

    def dialog(self,p):
        kind = self.state.dialog
        if kind == 'run':
            self.run_dialog.draw(self, p)
            return
        if kind == 'resolution-confirm':
            seconds = max(0, round(self.resolution_trial[3]-time.monotonic()))
            display_settings.draw_confirmation(p, self, seconds)
            return
        titles = {'about':'About Win95LX',
                  'help':'Win95LX Help', 'find':'Find: Files or Folders'}
        width = 350
        height = 238 if kind=='find' else 166
        x,y = (self.width-width)//2,(self.height-height)//2
        p.window_frame(x,y,width,height)
        p.fill(x+4,y+4,width-8,18,NAVY)
        p.text(titles[kind],x+7,y+5,LIGHT,bold=True)
        if kind == 'find':
            p.text('Search for files and folders on C:.',x+16,y+38)
            p.text('Named:',x+16,y+68)
            p.bevel(x+62,y+64,270,21,True)
            p.fill(x+64,y+66,266,17,LIGHT)
            p.cr.save()
            p.cr.rectangle(x+65,y+66,263,17)
            p.cr.clip()
            p.text(self.dialog_input+'|',x+67,y+67)
            p.cr.restore()
            if self.dialog_error:
                p.text(self.dialog_error,x+16,y+92)
            if self.find_results is not None:
                for row,name in enumerate(self.find_results):
                    p.text(name[:43],x+18,y+94+row*15)
                if not self.find_results:
                    p.text('No matching files or folders.',x+18,y+94)
            self.button(p,'Find Now',x+168,y+height-36,75,23,('dialog-submit',))
            self.button(p,'Cancel',x+251,y+height-36,75,23,('cancel',))
        else:
            if kind=='help':
                p.text('Ctrl+Esc opens the Start menu.',x+18,y+43)
                p.text('Use the arrow keys to move between entries.',x+18,y+65)
                p.text('Double-click My Computer to open C:.',x+18,y+87)
            else:
                p.text('Win95LX - Development Preview',x+18,y+43,bold=True)
                p.text('Original privately extracted Windows assets.',x+18,y+65)
            self.button(p,'OK',x+251,y+129,75,23,('cancel',))

    def submit_dialog(self):
        kind=self.state.dialog
        if kind=='find':
            query=self.dialog_input.strip().casefold()
            if not query:
                self.dialog_error='Enter a file or folder name.'
                return
            try:
                entries=self.drive.view.entries()
            except OSError:
                self.dialog_error='C: could not be read.'
                return
            self.dialog_error=''
            self.find_results=[name for name,_ in entries
                               if fnmatch.fnmatchcase(name.casefold(),query)
                               or query in name.casefold()][:6]
        else:
            self.state.dialog=None

    def action(self,action,event=None):
        kind=action[0]
        if kind=='printer-queue':
            key='printer:'+action[1]
            existing=self.accessory_windows.get(key)
            if existing is not None:existing.present();return
            window=self.printer_namespace().open(self,action[1])
            self.accessory_windows[key]=window
            window.connect('destroy',lambda *_:self.accessory_windows.pop(key,None) if self.accessory_windows.get(key) is window else None)
            return
        if kind=='printer-refresh':self.refresh_printers();return
        if kind=='printer-add':
            from win95lx.apps.dialogs import message_box
            message_box(self,'Add Printer','The Add Printer Wizard is not implemented yet. Existing printers configured on this computer can be opened and managed here.',Gtk.MessageType.INFO)
            return
        if self.state.dialog == 'shutdown':
            if kind == 'shutdown-option':
                self.shutdown_dialog.selection = action[1]
                self.shutdown_dialog.focus = 0
            elif kind == 'shutdown-button':
                self.shutdown_button(action[1])
            self.area.queue_draw()
            return
        if self.state.dialog == 'run':
            if self.run_dialog.handle_action(self, action):
                self.area.queue_draw()
            return
        if self.state.dialog == 'resolution-confirm':
            if kind == 'resolution-confirm':
                self.finish_resolution_trial(action[1])
            return
        if self.state.dialog and kind not in ('exit','cancel','dialog-submit'):return
        if kind=='start':
            self.show_start()
        elif kind=='menu':
            self.choose_menu_row(action[1])
        elif kind=='start-folder':
            self.shortcut_drag = self.shortcut_drag_point = self.shortcut_drop = None
            self.item_selection = None
            folder = action[1]
            self.open('start-folder', folder)
            self.state.active.title = FOLDER_TITLES[folder]
        elif kind == 'documents-folder':
            folder = (Path.home()/'Documents' if is_development_guest()
                      else self._drive.view.root/'Documents')
            try:
                folder.mkdir(parents=True,exist_ok=True)
                relative = folder.relative_to(self._drive.view.root)
            except (OSError,ValueError) as error:
                from win95lx.apps.dialogs import message_box
                message_box(self,'My Documents',str(error),Gtk.MessageType.ERROR)
            else:
                self.open('drive',relative)
        elif kind == 'recent-document':
            from win95lx.apps.dialogs import message_box
            self.state.start_open = False
            self.menu_path.clear()
            try:
                relative = Path(action[1]).resolve().relative_to(self._drive.view.root)
            except (OSError,ValueError) as error:
                message_box(self,'Documents',str(error),Gtk.MessageType.ERROR)
            else:
                self.open_drive_file(relative)
        elif kind == 'trash-entry':
            from win95lx.apps.dialogs import message_box
            self.trash_selection = {action[1]}
            record = next((entry for entry in self.trash.entries() if entry[0]==action[1]),None)
            if record:
                answer = message_box(self,f'{record[1].name} Properties',
                                     f'Original location: {record[1].parent}',
                                     Gtk.MessageType.INFO,
                                     (('Restore',Gtk.ResponseType.APPLY),('Close',Gtk.ResponseType.CLOSE)),
                                     Gtk.ResponseType.CLOSE)
                if answer == Gtk.ResponseType.APPLY:
                    self.trash_command('restore')
        elif kind == 'trash-command':
            self.trash_command(action[1])
        elif kind=='drive-edit':
            self.drive_edit(*action[1:])
        elif kind=='drive-entry':
            self.open_drive_entry(*action[1:],new_window=bool(event and getattr(event,'state',0)&Gdk.ModifierType.SHIFT_MASK))
        elif kind=='drive-navigate':
            self.navigate_drive(*action[1:])
        elif kind=='info-scroll':
            action[1].info_scroll=max(0,min(action[1].info_scroll_max,action[1].info_scroll+action[2]))
        elif kind=='drive-scroll':
            browser = self.browser_for(action[1])
            browser.scroll += action[2]
            browser.grid(*self.drive_pane_size(action[1]))
        elif kind=='drive-thumb' and event:
            self.drive_scroll_drag = action[1], event.y-action[2]
        elif kind=='shortcut-properties':
            from win95lx.apps.dialogs import message_box
            label, target = action[1:]
            message_box(self, f'{label} Properties', f'Shortcut\n\nTarget: {target}',
                        Gtk.MessageType.INFO)
        elif kind=='system-menu':
            if event and event.type == Gdk.EventType._2BUTTON_PRESS:
                self.action(('close', action[1]))
            else:
                self.open_system_menu(action[1])
        elif kind=='system-command':
            self.system_command(action[1], action[2])
        elif kind=='submenu-row':
            self.select_submenu_row(action[1], action[2])
        elif kind in ('help','run','find'):
            self.state.start_open=False
            self.menu_path.clear()
            self.state.dialog=kind
            if kind == 'run':
                self.run_dialog.reset()
            self.dialog_input=''
            self.dialog_error=''
            self.find_results=None
        elif kind=='suspend':
            self.state.start_open=False
            self.menu_path.clear()
            self.suspended=True
        elif kind=='dialog-submit':
            self.submit_dialog()

        elif kind=='desktop':
            self.state.selection=action[1]
            if event and event.type == Gdk.EventType._2BUTTON_PRESS:
                self.icon_drag = self.icon_drag_point = None
                self.open_desktop_item(action[1])
            elif event and event.button == 1:
                point = self.desktop_icons.position(action[1], self.width, self.height,
                                                    self.desktop_file_defaults.get(action[1]))
                self.icon_drag = action[1], point, event.x, event.y
        elif kind=='open' and action[1]:self.open_desktop_item(action[1])
        elif kind=='accessory':self.launch_accessory(action[1])
        elif kind=='accessory-task':
            window = action[1]
            if window.is_active():
                window.hide()
                self.get_window().focus(Gdk.CURRENT_TIME)
            else:
                window.show_all()
                window.present()
        elif kind=='item':
            win, target, label, point = action[1:]
            previous=self.item_selection
            win.focus_item=label
            win.info_scroll=0
            self.item_selection = (win, label)
            if win.kind=='computer' and event and getattr(event,'state',0)&Gdk.ModifierType.CONTROL_MASK:
                if previous==(win,None):self.item_selection=(win,'Control Panel' if label=='(C:)' else '(C:)')
                elif previous==(win,label):self.item_selection=None
                elif previous and previous[0] is win:self.item_selection=(win,None)
            elif win.kind=='computer' and event and getattr(event,'state',0)&Gdk.ModifierType.SHIFT_MASK and previous and previous[0] is win:
                self.item_selection=(win,None)
            self.state.selection = None
            if win.kind == 'recycle':
                self.trash_selection = {target[1]}
            if win.kind == 'drive':
                self.state.windows.remove(win)
                self.state.windows.append(win)
            if event and event.type == Gdk.EventType._2BUTTON_PRESS and target:
                self.namespace_item_drag=self.namespace_item_point=None
                self.file_drag = None
                self.shortcut_drag = self.shortcut_drag_point = None
                if isinstance(target, tuple):
                    self.action(target)
                else:
                    self.navigate_namespace(win,target,new_window=bool(getattr(event,'state',0)&Gdk.ModifierType.SHIFT_MASK)) if win.kind in ('computer','control','printers') else self.open(target)
            elif event and event.button == 1 and win.kind == 'drive':
                self.state.windows.remove(win)
                self.state.windows.append(win)
                modifiers = getattr(event, 'state', 0)
                self.file_drag_toggle = bool(modifiers & Gdk.ModifierType.CONTROL_MASK and label in self.drive_selection)
                if not self.file_drag_toggle and (label not in self.drive_selection or modifiers & (
                        Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)):
                    self.edit_drive_selection(label, modifiers)
                self.file_drag_point = None
                self.file_drag_origin = label, point, event.x, event.y
                self.file_drag = win, label, event.x, event.y
            elif event and event.button == 1 and win.kind in ('computer','control','printers'):
                if not win.namespace_auto and win.namespace_view in ('large','small'):
                    self.namespace_item_drag=(win,label,point,event.x,event.y,win.namespace_scroll)
                    self.namespace_item_point=None
            elif event and event.button == 1 and win.kind == 'start-folder':
                self.state.windows.remove(win)
                self.state.windows.append(win)
                self.shortcut_drag = win, label, target, point, event.x, event.y
        elif kind=='display-tab':
            self.display_tab = action[1]
            self.resolution_focus = None
        elif kind=='wallpaper-select':
            self.pending_wallpaper = action[1]
        elif kind=='wallpaper-scroll':
            self.wallpaper_scroll = max(0, min(self.wallpaper_scroll+action[1], self.wallpaper_max_scroll))
        elif kind=='wallpaper-thumb' and event:
            self.wallpaper_drag = (action[1], event.y-action[2])
        elif kind=='wallpaper-help' and action[1] == 'Browse':
            self.browse_background()
        elif kind=='wallpaper-help' and action[1] == 'Pattern':
            from win95lx.control_panel.pattern_dialog import choose_pattern
            result = choose_pattern(self,self.desktop_patterns,self.pending_pattern,self.pending_pattern_rows)
            if result is not None:
                self.pending_pattern,self.pending_pattern_rows = result
        elif kind=='wallpaper-help':
            from win95lx.apps.dialogs import message_box
            message = {
                'Browse': 'Choose one of the wallpapers in the list.',
                'Pattern': 'Desktop patterns are unavailable in this build.',
                'Background': 'Select a wallpaper and choose Center or Tile. Select Apply to save it.',
            }[action[1]]
            message_box(self, 'Display Properties', message, Gtk.MessageType.INFO)
        elif kind=='wallpaper-mode':
            self.wallpaper_combo.open()
        elif kind=='wallpaper-apply':
            try:
                self.wallpaper.apply(self.pending_wallpaper,self.pending_wallpaper_mode,
                                     self.pending_pattern,self.pending_pattern_rows)
            except OSError:
                self.wallpaper_error = True
            else:
                self.wallpaper_error = False
                if action[2]:
                    self.state.windows.remove(action[1])
        elif kind == 'display-combo':
            self.resolution_focus = action[1]
            self.display_combos[action[1]].open()
        elif kind == 'display-tray':
            self.resolution_focus = 'tray'
            self.pending_display = replace(self.pending_display, tray=not self.pending_display.tray)
        elif kind=='keyboard-language-menu':
            from win95lx.control_panel.keyboard_preferences import LAYOUT_NAMES
            prefs=self.keyboard_preferences
            if prefs:
                rows=[(LAYOUT_NAMES.get(code,code),('keyboard-language-select',index)) for index,code in enumerate(prefs.layouts)]
                self.start_context=StartContext(self.width-230,self.height-28-6-17*len(rows),rows,230,self.width,self.height)
        elif kind=='keyboard-language-select':
            from win95lx.control_panel.keyboard_preferences import KeyboardGroups
            try:
                if self.keyboard_groups is None:self.keyboard_groups=KeyboardGroups()
                self.keyboard_groups.select(action[1])
            except (RuntimeError,ValueError) as error:
                from win95lx.apps.dialogs import message_box
                message_box(self,'Keyboard Properties',str(error),Gtk.MessageType.ERROR)
            self.start_context=None
        elif kind == 'volume-tray-open':
            if self.volume_popup:self.volume_popup.finish()
            else:
                from win95lx.apps.volume_popup import VolumePopup
                try:
                    self.volume_popup=VolumePopup(self,action[1])
                    self.volume_popup.connect('destroy',lambda *_:setattr(self,'volume_popup',None))
                except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
                    from win95lx.apps.dialogs import message_box
                    message_box(self,'Volume Control',str(error),Gtk.MessageType.ERROR)
        elif kind == 'display-tray-open':
            self.open('display')
            self.display_tab = 'settings'
        elif kind == 'display-advanced':
            self.resolution_focus = 'advanced'
            self.open_advanced_display()
        elif kind == 'resolution-slider' and event and event.button == 1:
            win, top = action[1:]
            self.state.windows.remove(win)
            self.state.windows.append(win)
            self.resolution_focus = top
            index = self.resolution_modes.index(self.pending_resolution)
            modes=self.resolution_modes
            center = display_settings.slider_center(index,len(modes),modes.index((800,600)) if (800,600) in modes else 0)
            offset = event.x-win.x-center
            if abs(offset) > 5:
                offset = 0
                self.move_resolution_slider(win, event.x)
            self.resolution_drag = win, offset
        elif kind == 'resolution-apply':
            self.try_resolution(*action[1:])
        elif kind == 'resolution-help':
            from win95lx.apps.dialogs import message_box
            message_box(self, 'Display Properties',
                        'Use Desktop area or Screen area to change the guest resolution. '
                        'Both sliders control the same display.', Gtk.MessageType.INFO)
        elif kind=='close':self.state.windows.remove(action[1]);self.popup=None;play_event(self.assets,'Close')
        elif kind=='minimize':
            if not action[1].minimized:play_event(self.assets,'Minimize')
            action[1].minimized=True
        elif kind=='task':
            win=action[1]
            if win is self.active_task:win.minimized=True
            else:self.state.windows.remove(win);win.minimized=False;self.state.windows.append(win)
        elif kind in ('drag','maximize'):
            win=action[1]
            self.state.windows.remove(win)
            self.state.windows.append(win)
            resizable=win.kind in ('computer','control','drive','recycle','notepad','start-folder')
            if resizable and (kind=='maximize' or event.type==Gdk.EventType._2BUTTON_PRESS):
                self.drag=None
                if win.restored_bounds is None:
                    play_event(self.assets,'Maximize')
                    win.restored_bounds=(win.x,win.y,win.width,win.height)
                    win.x,win.y,win.width,win.height=0,0,self.width,self.height-28
                else:
                    play_event(self.assets,'RestoreDown')
                    win.x,win.y,win.width,win.height=win.restored_bounds
                    win.restored_bounds=None
                    self.resize_to_display(self.get_screen())
            elif win.restored_bounds is None:
                self.drag=(win,event.x-win.x,event.y-win.y)
        elif kind=='shutdown':self.open_shutdown()
        elif kind=='about':
            from win95lx.apps.dialogs import about_dialog
            self.popup = None
            self.area.queue_draw()
            about_dialog(self, 'Win95LX')
        elif kind=='cancel':self.state.dialog=None
        elif kind=='exit':
            for window in tuple(self.accessory_windows.values()):
                if window.emit('delete-event', None):
                    return
            self.destroy()
        elif kind in ('file-menu','window-menu'):
            win=action[1]
            self.state.windows.remove(win)
            self.state.windows.append(win)
            menu,offset=action[2:] if kind=='window-menu' else ('File',7)
            self.drive_menu_highlight = None
            left = offset-8 if win.kind == 'drive' and menu == 'Edit' else offset-9 if menu == 'File' else offset-5
            dx,dy=(-4,-5) if win.kind in ('computer','control','printers') and win.restored_bounds is not None else (0,0)
            self.popup=(win.x+left+dx,win.y+explorer_chrome.POPUP_TOP+dy,(win,menu))
            play_event(self.assets,'MenuPopup')
        elif kind=='namespace-view':
            win,mode=action[1:];win.namespace_view=mode;win.namespace_scroll=(0,0);win.namespace_positions=();self.popup=None
        elif kind=='namespace-auto':
            win=action[1];win.namespace_auto=not win.namespace_auto;self.popup=None
            try:self.shortcut_icons.move('namespace:'+win.kind,'$auto',(int(win.namespace_auto),0))
            except OSError as error:print(f'Could not save namespace arrangement: {error}',flush=True)
        elif kind=='namespace-thumb':
            win,axis,x,y,length,maximum,thumb=action[1:]
            coordinate=(event.x-x if axis==0 else event.y-y) if event else thumb
            self.namespace_drag=(win,axis,x,y,length,maximum,coordinate-thumb)
        elif kind=='namespace-scroll':
            win,axis,delta=action[1:];position=list(win.namespace_scroll);position[axis]=max(0,position[axis]+delta);win.namespace_scroll=tuple(position)
        elif kind=='computer-view-toggle':
            setattr(action[1],action[2],not getattr(action[1],action[2]))
            self.popup=None
        elif kind=='explorer-tool':
            self.popup=None
            win,command=action[1:]
            if command=='views':
                xx,yy,_,_=computer_view.geometry(win)
                self.popup=(xx+557,yy+90,(win,'View'))
            elif command=='properties':
                if self.item_selection==(win,'(C:)'):
                    self.action(('computer-menu',win,'properties'))
                elif self.item_selection and self.item_selection[0] is win and self.item_selection[1] in cpl_catalog.targets():
                    self.open(cpl_catalog.targets()[self.item_selection[1]])
                elif win.kind=='computer' and (not self.item_selection or self.item_selection[0] is not win):
                    self.open('system')
            elif command=='back':
                self.navigate_history(win,True)
            elif command=='forward':
                self.navigate_history(win,False)
            elif command=='up' and win.kind in ('control','printers'):
                self.navigate_namespace(win,'control' if win.kind=='printers' else 'computer')
            elif command=='refresh' and win.kind=='printers':self.refresh_printers()
        elif kind=='explorer-address':
            self.address_window=action[1]
            self.address_text=action[1].title
            self.address_entry.text=self.address_text
            self.address_entry.select_all()
        elif kind=='explorer-locations':
            xx,yy,_,_=computer_view.geometry(action[1])
            self.popup=(xx+58,yy+112,(action[1],'Go'))
        elif kind=='computer-menu':
            if self.popup is not None:play_event(self.assets,'MenuCommand')
            self.popup=None
            if action[2]=='offline':
                self.work_offline=not self.work_offline
            elif action[2] in ('open','explore') and action[1].kind=='printers':
                win=action[1]
                selection=self.item_selection[1] if self.item_selection and self.item_selection[0] is win else None
                target=next((target for _,label,target in self.printer_namespace().entries() if label==selection),None)
                if target:self.action(target)
            elif action[2] in ('open','explore'):
                selection=self.item_selection[1] if self.item_selection and self.item_selection[0] is action[1] else None
                labels=(selection,) if selection else (cpl_catalog.labels() if action[1].kind=='control' else ('(C:)','Control Panel'))
                for label in labels:
                    self.navigate_namespace(action[1],{'(C:)':'drive','Control Panel':'control',**cpl_catalog.targets()}[label],new_window=action[2]=='explore' or len(labels)>1)
            elif action[2]=='find':
                self.action(('find',))
            elif action[2]=='format':
                from win95lx.apps.dialogs import message_box
                message_box(self,'Format',"Windows cannot format this drive because it is in use.",Gtk.MessageType.ERROR)
            elif action[2]=='computer':
                self.item_selection=None
            elif action[2]=='properties' and self.item_selection and self.item_selection[0] is action[1] and self.item_selection[1] in cpl_catalog.targets():
                self.open(cpl_catalog.targets()[self.item_selection[1]])
            elif action[2]=='properties' and self.item_selection and self.item_selection==(action[1],'(C:)'):
                import shutil
                from win95lx.apps.dialogs import message_box
                usage=shutil.disk_usage(self._drive.view.root)
                message_box(self,'(C:) Properties',f'Type: Local Disk\nUsed space: {usage.used:,} bytes\nFree space: {usage.free:,} bytes\nCapacity: {usage.total:,} bytes',Gtk.MessageType.INFO)
            elif action[2]=='shortcut' and self.item_selection and self.item_selection[0] is action[1]:
                from win95lx.apps.dialogs import message_box, YES_NO
                answer=message_box(self,'Shortcut','Windows cannot create a shortcut here.\nDo you want the shortcut to be placed on the desktop instead?',Gtk.MessageType.QUESTION,YES_NO,Gtk.ResponseType.YES,profile='shortcut')
                if answer==Gtk.ResponseType.YES:
                    from win95lx.explorer.namespace import create_shortcut
                    try:
                        labels=(self.item_selection[1],) if self.item_selection[1] else (cpl_catalog.labels() if action[1].kind=='control' else ('(C:)','Control Panel'))
                        for label in labels:create_shortcut(self.desktop_folder,label)
                        self.refresh_desktop_files()
                    except (OSError,KeyError) as error:
                        message_box(self,'Create Shortcut',str(error),Gtk.MessageType.ERROR)
        elif kind=='select-all':
            self.item_selection=(action[1],None)
            self.popup=None
        elif kind=='desktop-new-folder':
            from win95lx.apps.dialogs import name_dialog, message_box
            self.popup = None
            self.area.queue_draw()
            name = name_dialog(self, 'New Folder', 'New Folder')
            if name is not None:
                try:
                    relative = self.desktop_folder.relative_to(self._drive.view.root)
                    folder = self.drive.view.resolve(relative)
                    folder.mkdir(exist_ok=True)
                    (folder/child_name(name)).mkdir()
                except (OSError, RuntimeError, ValueError) as error:
                    message_box(self, 'New Folder', str(error), Gtk.MessageType.ERROR)
                self.refresh_desktop_files()
        elif kind=='desktop-refresh':
            self.refresh_desktop_files()
            self.popup = None
        elif kind=='dismiss':
            self.popup=None
        self.area.queue_draw()

    def open_shutdown(self):
        self.state.start_open = False
        self.menu_path.clear()
        self.popup = None
        self.state.dialog = 'shutdown'
        self.shutdown_dialog.reset()
        self.shutdown_windows = [window for window in self.accessory_windows.values()
                                 if window.get_visible()]
        for window in self.shutdown_windows:
            window.hide()
        self.get_window().focus(Gdk.CURRENT_TIME)

    def shutdown_button(self, button):
        from win95lx.apps.dialogs import message_box

        selection = self.shutdown_dialog.selection
        if button == 2:
            message_box(self, 'Shut Down Windows',
                        'Shut down turns off this virtual machine. Restart boots Win95LX again. '
                        'MS-DOS mode is unavailable in this guest.',
                        Gtk.MessageType.INFO)
            return
        if button == 0 and selection == 2:
            message_box(self, 'Shut Down Windows', 'MS-DOS mode is unavailable in this guest.',
                        Gtk.MessageType.INFO)
            return
        if button == 0 and not is_development_guest():
            message_box(self, 'Shut Down Windows', 'Power controls are available inside the Win95LX guest.',
                        Gtk.MessageType.INFO)
            return
        self.state.dialog = None
        for window in self.shutdown_windows:
            window.show_all()
        self.shutdown_windows.clear()
        if button == 1:
            return
        for window in tuple(self.accessory_windows.values()):
            if window.emit('delete-event', None):
                return
        command = 'poweroff' if selection == 0 else 'reboot'
        try:
            subprocess.run(['systemctl', '--no-ask-password', command], check=True,
                           capture_output=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            message_box(self, 'Shut Down Windows', 'The guest could not complete the request.',
                        Gtk.MessageType.ERROR)

    @staticmethod
    def system_profile(win):
        resizable = win.kind in ('computer','control','printers','drive','recycle','start-folder')
        return system_options(resizable=resizable, minimizable=resizable,
                              maximized=win.restored_bounds is not None)

    def open_system_menu(self, win):
        self.popup = None
        self.state.start_open = False
        self.menu_path.clear()
        self.state.windows.remove(win)
        self.state.windows.append(win)
        rows = [(label, ('system-command', win, command) if enabled else None)
                for command, label, _, enabled in self.system_profile(win)]
        rows.insert(-1, None)
        self.start_context = SystemContext(win, rows, MENU_WIDTH, self.width, self.height)

    def system_command(self, win, command):
        if command in ('close', 'minimize'):
            self.action((command, win))
        elif command in ('restore', 'maximize'):
            self.action(('maximize', win))
        elif command in ('move', 'size'):
            pointer = self.get_display().get_default_seat().get_pointer().get_position()
            self.window_operation = win, WindowOperation.begin(
                command, (win.x,win.y,win.width,win.height), (pointer.x/self.pointer_scale,pointer.y/self.pointer_scale))

    @staticmethod
    def apply_window_operation(win, bounds):
        win.x, win.y, win.width, win.height = bounds

    def open_start_context(self, event):
        x, y = event.x, event.y
        if 2 <= x < 56 and self.height-24 <= y < self.height-2:
            self.state.start_open = False
            self.menu_path.clear()
            rows = [('Open', ('start-folder', None)), ('Explore', ('start-folder', None)),
                    ('Find...', ('find',))]
            width = 82
        elif self.state.start_open:
            target = next((action for xx, yy, width, height, action in reversed(self.hits[self.menu_hit_start:])
                           if xx <= x < xx+width and yy <= y < yy+height), None)
            if not target or target[0] != 'submenu-row':
                return True
            depth, row = target[1:]
            if depth >= len(self.menu_path):
                return True
            key, _ = self.menu_path[depth]
            label, _, action = self.submenu_entries(key)[row]
            if action[0] == 'submenu':
                action = ('start-folder', action[1])
            rows = [('Open', action), None, ('Send To', None), None, ('Cut', None), ('Copy', None),
                    None, ('Create Shortcut', None), ('Delete', None), None,
                    ('Properties', ('shortcut-properties', label,
                                    action[1] if len(action)>1 else label))]
            width = 121
        else:
            return False
        self.popup = None
        self.start_context = StartContext(x, y, rows, width, self.width, self.height)
        self.area.queue_draw()
        return True

    @property
    def resolution_modes(self):
        return tuple(sorted(set(getattr(self,'detected_resolution_modes',DISPLAY_MODES)) | {self.applied_resolution},
                            key=lambda mode: (mode[0]*mode[1], *mode)))

    def move_resolution_slider(self, win, pointer_x):
        modes = self.resolution_modes
        self.pending_resolution = modes[display_settings.slider_index(pointer_x-win.x,len(modes),modes.index((800,600)) if (800,600) in modes else 0)]
        self.resolution_error = ''

    def try_resolution(self, win, close):
        if self.pending_resolution == self.applied_resolution:
            if self.commit_display_preferences() and close:
                self.state.windows.remove(win)
            return
        try:
            set_resolution(*self.pending_resolution)
        except (OSError, subprocess.SubprocessError, ValueError, StopIteration):
            self.resolution_error = 'This display could not switch to that mode.'
            return
        self.resolution_trial = (win, self.pending_resolution, close, time.monotonic()+15)
        self.state.dialog = 'resolution-confirm'
        GLib.timeout_add(250, self.tick_resolution_trial, self.resolution_trial)

    def tick_resolution_trial(self, trial):
        if self.resolution_trial is not trial:
            return GLib.SOURCE_REMOVE
        if time.monotonic() >= trial[3]:
            self.finish_resolution_trial(False)
            return GLib.SOURCE_REMOVE
        self.area.queue_draw()
        return GLib.SOURCE_CONTINUE

    def finish_resolution_trial(self, keep):
        win, mode, close, _ = self.resolution_trial
        self.resolution_trial = self.state.dialog = None
        if keep:
            self.applied_resolution = mode
            try:
                remember_resolution(*mode)
            except OSError:
                self.resolution_error = 'Could not save the display mode for next login.'
            else:
                if self.commit_display_preferences() and close:
                    self.state.windows.remove(win)
        else:
            try:
                set_resolution(*self.applied_resolution)
            except (OSError, subprocess.SubprocessError, ValueError, StopIteration):
                self.resolution_error = 'Could not restore the previous display mode.'
                self.applied_resolution = mode
            self.pending_resolution = self.applied_resolution
        self.area.queue_draw()

    @staticmethod
    def load_background_image(path):
        image = GdkPixbuf.Pixbuf.new_from_file(str(path))
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24,image.get_width(),image.get_height())
        context = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(context,image,0,0)
        context.paint()
        return surface

    def browse_background(self):
        from win95lx.apps.dialogs import choose_file,message_box
        current = self.wallpaper.custom.get(self.pending_wallpaper)
        path = choose_file(self,Path(current) if current else None,(
            ('Pictures',('*.bmp','*.png','*.jpg','*.jpeg','*.gif'), ''),
            ('All Files',('*',),''),
        ))
        if path is None:
            return
        try:
            image = self.load_background_image(path)
        except (GLib.Error,OSError) as error:
            message_box(self,'Display Properties',f'Could not load the picture.\n{error}',Gtk.MessageType.ERROR)
            return
        label = self.wallpaper.register(path)
        self.wallpaper_images[label] = image
        self.wallpaper_surface.cache_clear()
        self.pending_wallpaper = label
        self.wallpaper_scroll = min(self.wallpaper.names.index(label),self.wallpaper_max_scroll)
        self.wallpaper_error = False

    @lru_cache(maxsize=16)
    def wallpaper_surface(self, name, palette):
        image = self.wallpaper_images.get(name)
        return color_surface(image, palette) if image is not None else None

    def reset_display_combos(self):
        self.display_combos['palette'].value = self.pending_display.palette
        self.display_combos['font'].value = {96:0, 120:1}.get(self.pending_display.dpi, 2)
        for combo in self.display_combos.values():
            combo.expanded = combo.focused = False

    def commit_display_preferences(self):
        if self.display_preferences == self.pending_display:
            return True
        try:
            self.pending_display.save(self.display_preferences_path)
        except OSError:
            self.resolution_error = 'Could not save the display preferences.'
            return False
        self.display_preferences = self.pending_display
        Gtk.Settings.get_for_screen(self.get_screen()).set_property(
            'gtk-xft-dpi', self.display_preferences.dpi*1024)
        self.resize_to_display(self.get_screen())
        for window in Gtk.Window.list_toplevels():
            window.queue_draw()
        return True

    def select_display_combo(self, name, value):
        if name == 'palette':
            self.pending_display = replace(self.pending_display, palette=value)
        elif value == 2:
            dialog = Gtk.Dialog(title='Custom Font Size', transient_for=self, modal=True)
            dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'OK', Gtk.ResponseType.OK)
            box = dialog.get_content_area()
            box.set_border_width(12)
            box.add(Gtk.Label(label='Font size (96–120 dpi)'))
            dpi = Gtk.SpinButton.new_with_range(96, 120, 1)
            dpi.set_value(self.pending_display.dpi)
            box.add(dpi)
            dialog.show_all()
            if dialog.run() == Gtk.ResponseType.OK:
                self.pending_display = replace(self.pending_display, dpi=dpi.get_value_as_int())
            dialog.destroy()
            self.reset_display_combos()
        else:
            self.pending_display = replace(self.pending_display, dpi=(96,120)[value])
        self.display_combos[name].value = (self.pending_display.palette if name == 'palette'
                                           else {96:0,120:1}.get(self.pending_display.dpi,2))

    def open_advanced_display(self):
        dialog = Gtk.Dialog(title='Advanced Display Properties', transient_for=self, modal=True)
        dialog.add_button('OK', Gtk.ResponseType.OK)
        notebook = Gtk.Notebook()
        notebook.set_border_width(8)
        for title, description in (
            ('Adapter', 'Win95LX virtual display\n\nX11 RandR mode switching'),
            ('Monitor', f'Virtual monitor\n\nCurrent mode: {self.applied_resolution[0]} by {self.applied_resolution[1]} pixels'),
            ('Performance', 'Color conversion and font scaling apply to the Win95LX shell.'),
        ):
            label = Gtk.Label(label=description, xalign=0)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(12)
            label.set_margin_bottom(12)
            notebook.append_page(label, Gtk.Label(label=title))
        dialog.get_content_area().add(notebook)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def resolution_key(self, name, alt=False, shift=False):
        win = self.state.active
        if (not win or win.kind != 'display' or self.display_tab != 'settings'
                or self.state.start_open or self.state.dialog):
            return False
        focus = self.resolution_focus
        combo = self.display_combos.get(focus)
        if combo and (name == 'F4' or alt and name in ('Up', 'Down')):
            combo.expanded = not combo.expanded
        elif alt:
            return False
        elif combo and name in ('Up','Down'):
            combo.step(1 if name == 'Down' else -1)
            if not combo.expanded and (focus != 'font' or combo.value != 2):
                self.select_display_combo(focus, combo.value)
        elif combo and combo.expanded and name in ('Return','KP_Enter','Escape'):
            combo.expanded = False
            if name != 'Escape':
                self.select_display_combo(focus, combo.value)
            else:
                self.reset_display_combos()
        elif name == 'Tab':
            if combo:
                self.reset_display_combos()
            order = display_settings.FOCUS_ORDER
            index = order.index(focus) if focus in order else (-1 if not shift else 0)
            self.resolution_focus = order[(index+(-1 if shift else 1))%len(order)]
        elif name == 'space' and focus in ('tray','advanced'):
            self.action(('display-tray' if focus == 'tray' else 'display-advanced',))
        elif name in ('Left', 'Right', 'Home', 'End') and focus in display_settings.SLIDERS:
            modes = self.resolution_modes
            index = modes.index(self.pending_resolution)
            index = {'Left': max(0,index-1), 'Right': min(len(modes)-1,index+1),
                     'Home': 0, 'End': len(modes)-1}[name]
            self.pending_resolution = modes[index]
            self.resolution_error = ''
        elif name in ('Return', 'KP_Enter'):
            self.try_resolution(win, True)
        elif name == 'Escape':
            self.action(('close', win))
        else:
            return False
        return True

    @property
    def pending_wallpaper_mode(self):
        return background.MODES[self.wallpaper_combo.value]

    def wallpaper_combo_available(self):
        win = self.state.active
        return (win is not None and win.kind == 'display' and self.display_tab == 'background'
                and self.pending_wallpaper != '(None)' and not self.state.start_open
                and not self.state.dialog)

    def wallpaper_combo_key(self, name, alt):
        if not self.wallpaper_combo_available():
            return False
        combo = self.wallpaper_combo
        if alt and name in ('d', 'D'):
            combo.focused = True
        elif combo.focused and (name == 'F4' or alt and name in ('Up', 'Down')):
            if combo.expanded:
                combo.expanded = False
            else:
                combo.open()
        elif combo.focused and name in ('Up', 'Down') and not alt:
            combo.step(1 if name == 'Down' else -1)
        elif combo.expanded and name in ('Return', 'KP_Enter', 'Escape', 'Tab'):
            combo.expanded = False
            if name == 'Tab':
                combo.focused = False
        else:
            return False
        return True

    @property
    def wallpaper_max_scroll(self):
        return max(0, len(self.wallpaper.names)-background.VISIBLE_ROWS)

    def scroll_wallpaper(self, _area, event):
        if self.pointer_scale != 1:
            event = ScaledPointer(event, self.pointer_scale)
        win = self.state.active
        if win and win.kind in ('control','printers') and not self.state.start_open and not self.state.dialog and not self.popup:
            x,y,w,h=win.namespace_viewport
            if x<=event.x<x+w and y<=event.y<y+h and event.direction in (Gdk.ScrollDirection.UP,Gdk.ScrollDirection.DOWN):
                axis=0 if win.namespace_view=='list' or win.namespace_layout and not win.namespace_layout.vertical else 1
                self.action(('namespace-scroll',win,axis,-51 if event.direction==Gdk.ScrollDirection.UP else 51));return True
        if win and win.kind in ('computer','control','printers') and win.web_view and not self.state.start_open and not self.state.dialog and not self.popup:
            left,top,width,height=computer_view.geometry(win)
            if left<=event.x<left+width*.3 and top+118<=event.y<top+height-24 and event.direction in (Gdk.ScrollDirection.UP,Gdk.ScrollDirection.DOWN):
                self.action(('info-scroll',win,-39 if event.direction==Gdk.ScrollDirection.UP else 39))
                return True
        if (win and win.kind=='drive' and not self.state.start_open and not self.state.dialog
                and win.x <= event.x < win.x+win.width
                and win.y+explorer_chrome.PANE_Y <= event.y < win.y+win.height-explorer_chrome.PANE_BOTTOM
                and event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN)):
            self.action(('drive-scroll', win, -1 if event.direction == Gdk.ScrollDirection.UP else 1))
            return True
        if (self.state.start_open or self.state.dialog or not win or win.kind != 'display'
                or self.display_tab != 'background'):
            return False
        if (win.x+34 <= event.x < win.x+282 and win.y+285 <= event.y < win.y+381
                and event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN)):
            self.action(('wallpaper-scroll', -1 if event.direction == Gdk.ScrollDirection.UP else 1))
            return True
        return False

    def press(self,area,event):
        if self.pointer_scale != 1:
            event = ScaledPointer(event, self.pointer_scale)
        if event.button == 1:
            self.get_window().focus(event.time)
        if self.suspended:
            self.suspended=False
            self.area.queue_draw()
            return True
        if self.window_operation and event.button == 1:
            self.window_operation = None
            return True
        if self.start_context:
            context = self.start_context
            if (isinstance(context, SystemContext) and event.type == Gdk.EventType._2BUTTON_PRESS
                    and context.window.x+4 <= event.x < context.window.x+22
                    and context.window.y+4 <= event.y < context.window.y+22):
                self.start_context = None
                self.action(('close', context.window))
                return True
            row = self.start_context.at(event.x, event.y)
            self.start_context = None
            if row and event.button == 1:
                self.action(row[1][1], event)
            self.area.queue_draw()
            return True
        combo = self.wallpaper_combo
        if combo.expanded and self.wallpaper_combo_available():
            win = self.state.active
            row = combo.row_at(event.x-win.x-background.MODE_X,
                               event.y-win.y-background.MODE_Y, background.MODE_WIDTH)
            combo.expanded = False
            if row is not None and event.button == 1:
                combo.value = row
            self.area.queue_draw()
            return True
        combo.focused = False
        win = self.state.active
        if win and win.kind == 'display' and self.display_tab == 'settings' and not self.state.dialog:
            for name, combo in self.display_combos.items():
                if combo.expanded:
                    left, top = display_settings.COMBOS[name]
                    row = combo.row_at(event.x-win.x-left, event.y-win.y-top, display_settings.COMBO_WIDTH)
                    combo.expanded = False
                    if row is not None and event.button == 1:
                        self.select_display_combo(name, row)
                    else:
                        self.reset_display_combos()
                    self.area.queue_draw()
                    return True
        if self.state.dialog and event.button==3:
            return True
        if event.button == 3 and self.open_start_context(event):
            return True
        if event.button == 3:
            win = self.state.active
            if win and win.kind == 'recycle' and win.x <= event.x < win.x+win.width and win.y+54 <= event.y < win.y+win.height:
                item = next((action for hx,hy,w,h,action in reversed(self.hits)
                             if action[0]=='item' and action[1] is win
                             and hx <= event.x < hx+w and hy <= event.y < hy+h),None)
                if item:
                    self.trash_selection = {item[2][1]}
                rows = [('Restore',('trash-command','restore')),
                        ('Delete',('trash-command','delete')),
                        None,('Empty Recycle Bin',('trash-command','empty'))]
                self.start_context = StartContext(event.x,event.y,rows,156,self.width,self.height)
                self.area.queue_draw()
                return True
        if event.button == 3:
            win = self.state.active
            if win and win.kind == 'drive' and not self.state.start_open and (
                    win.x+explorer_chrome.PANE_X <= event.x < win.x+win.width
                    and win.y+explorer_chrome.PANE_Y <= event.y < win.y+win.height):
                hit = next((action for x,y,w,h,action in reversed(self.hits)
                            if x <= event.x < x+w and y <= event.y < y+h
                            and action[0] == 'item' and action[1] is win), None)
                if hit and hit[3] not in self.drive_selection:
                    self.edit_drive_selection(hit[3], 0)
                elif not hit:
                    self.drive_selection.clear()
                    self.drive_anchor = None
                self.drive_menu_highlight = None
                self.popup = (int(event.x),int(event.y),(win,'Item'))
                self.area.queue_draw()
                return True
        if event.button==3:
            target=next((a for x,y,w,h,a in reversed(self.hits) if x<=event.x<x+w and y<=event.y<y+h and a[0]=='desktop'),None);self.popup=(min(int(event.x),self.width-133),min(int(event.y),self.height-90),target[1] if target else None);self.area.queue_draw();return True
        hits=self.hits
        if self.state.start_open:
            hits=[hit for hit in self.hits[:self.menu_hit_start] if hit[4]==('start',)]
            hits.extend(self.hits[self.menu_hit_start:])
        for x,y,w,h,action in reversed(hits):
            if x<=event.x<x+w and y<=event.y<y+h:self.action(action,event);return True
        for win in reversed(self.state.windows):
            if not win.minimized and win.x <= event.x < win.x+win.width and win.y <= event.y < win.y+win.height:
                if win.kind=='computer':
                    self.item_selection=None
                    self.state.windows.remove(win)
                    self.state.windows.append(win)
                if win.kind == 'drive':
                    self.state.windows.remove(win)
                    self.state.windows.append(win)
                    self.browser_for(win).selection.clear()
                    self.browser_for(win).anchor = None
                break
        self.menu_path.clear()
        self.state.start_open=False;self.popup=None;self.state.selection=None;self.area.queue_draw();return True
    def shortcut_drop_target(self, x, y):
        for win in reversed(self.state.windows):
            if win.minimized or not (win.x <= x < win.x+win.width and win.y <= y < win.y+win.height):
                continue
            if win.kind != 'start-folder' or not (
                win.x+explorer_chrome.PANE_X <= x < win.x+win.width-explorer_chrome.PANE_X
                and win.y+explorer_chrome.PANE_Y <= y < win.y+win.height-explorer_chrome.PANE_BOTTOM
            ):
                return None
            for hx, hy, width, height, action in reversed(self.hits):
                if (action[0] == 'item' and action[1] is win and action[2][0] == 'start-folder'
                        and hx <= x < hx+width and hy <= y < hy+height):
                    return win, action[3], action[2][1]
            return win, None, win.folder
        return None

    def file_drop_destination(self, x, y, sources=()):
        for win in reversed(self.state.windows):
            if win.minimized or not (win.x <= x < win.x+win.width and win.y <= y < win.y+win.height):
                continue
            if win.kind == 'recycle' and y >= win.y+explorer_chrome.PANE_Y:
                return win,RECYCLE_TARGET
            if win.kind != 'drive' or not (
                    win.x+explorer_chrome.PANE_X <= x < win.x+win.width-explorer_chrome.PANE_X
                    and win.y+explorer_chrome.PANE_Y <= y < win.y+win.height-explorer_chrome.PANE_BOTTOM):
                return None
            browser = self.browser_for(win)
            folder = browser.directory
            for hx,hy,w,h,action in reversed(self.hits):
                if action[0] != 'item' or action[1] is not win or not action[2][3]:
                    continue
                if browser.directory/action[3] in sources:
                    continue
                px,py = action[4]
                rect = folder_drop_rect(win.x+explorer_chrome.PANE_X+px,
                                        win.y+explorer_chrome.PANE_Y+py,
                                        min(72,self.font.width(action[3])))
                if contains(rect,x,y):
                    folder /= action[3]
                    break
            return win, folder
        if 0 <= x < self.width and 0 <= y < self.height-28:
            for hx,hy,w,h,action in self.hits:
                if action == ('desktop','recycle') and contains(
                        folder_drop_rect(hx,hy,self.font.width('Recycle Bin'),True),x,y):
                    return None,RECYCLE_TARGET
                if action[0] == 'desktop' and action[1].startswith('file:') and contains(
                        folder_drop_rect(hx,hy,min(72,self.font.width(action[1][5:])),True),x,y):
                    name = action[1][5:]
                    relative = self.desktop_folder.relative_to(self._drive.view.root)/name
                    if (name,True) in self.desktop_files and relative not in sources:
                        return None, relative
            return None, self.desktop_folder.relative_to(self._drive.view.root)
        return None

    def refresh_file_views(self):
        from win95lx.apps.dialogs import message_box
        self.refresh_desktop_files()
        for win in self.state.windows:
            if win.kind == 'drive':
                browser = self.browser_for(win)
                try:
                    browser.refresh()
                    browser.grid(*self.drive_pane_size(win))
                except OSError as error:
                    message_box(self, 'Explorer', str(error), Gtk.MessageType.ERROR)

    def trash_files(self, sources):
        from win95lx.apps.dialogs import message_box,YES_NO
        sources = tuple(sources)
        answer = message_box(self,'Confirm File Delete',
                             f'Send {len(sources)} selected item(s) to the Recycle Bin?',
                             Gtk.MessageType.QUESTION,YES_NO,Gtk.ResponseType.NO)
        if answer != Gtk.ResponseType.YES:
            return sources
        remaining = []
        for source in sources:
            try:
                self.trash.put(self._drive.view.resolve(source.parent)/source.name)
            except OSError as error:
                remaining.append(source)
                message_box(self,'Error Deleting File',str(error),Gtk.MessageType.ERROR)
                continue
            for win in tuple(self.state.windows):
                if win.kind == 'drive' and self.browser_for(win).directory.is_relative_to(source):
                    self.state.windows.remove(win)
        self.refresh_file_views()
        self.area.queue_draw()
        return tuple(remaining)

    def trash_command(self, command):
        from win95lx.apps.dialogs import message_box,YES_NO
        records = self.trash.entries()
        names = [key for key,_,_ in records if command == 'empty' or key in self.trash_selection]
        if command in ('delete','empty') and names:
            answer = message_box(self,'Confirm File Delete',
                                 'Permanently delete the selected Recycle Bin items?',
                                 Gtk.MessageType.WARNING,YES_NO,Gtk.ResponseType.NO)
            if answer != Gtk.ResponseType.YES:
                return
        deleted=0
        for name in names:
            try:
                if command == 'restore':
                    self.trash.restore(name)
                else:
                    self.trash.delete(name);deleted+=1
            except (OSError,StopIteration) as error:
                message_box(self,'Recycle Bin',str(error),Gtk.MessageType.ERROR)
        if command=='empty' and deleted:play_event(self.assets,'EmptyRecycleBin')
        self.trash_selection.clear()
        self.refresh_file_views()
        self.area.queue_draw()

    def transfer_files(self, sources, destination, copy=False):
        from win95lx.apps.dialogs import message_box
        sources = tuple(sources)
        if destination == RECYCLE_TARGET:
            return self.trash_files(sources)
        remaining = sources
        try:
            clipboard, errors = FileClipboard(sources, not copy).transfer(self._drive.view, destination)
            remaining = clipboard.sources
            if not copy:
                for source in sources:
                    if source in remaining:
                        continue
                    moved = Path(destination)/source.name
                    for win in self.state.windows:
                        if win.kind != 'drive':
                            continue
                        browser = self.browser_for(win)
                        if browser.directory.is_relative_to(source):
                            browser.directory = moved/browser.directory.relative_to(source)
                            win.folder, win.title = browser.directory, browser.title
        except (OSError, RuntimeError) as error:
            errors = [str(error)]
        self.refresh_file_views()
        if errors:
            message_box(self, 'Error Copying or Moving File', '\n'.join(errors), Gtk.MessageType.ERROR)
        return remaining

    def drop_drive_selection(self, win, event):
        browser = self.browser_for(win)
        sources = tuple(browser.directory/name for name in sorted(browser.selection))
        destination = self.file_drop_destination(event.x,event.y,sources)
        if destination is None:
            return
        target_win, folder = destination
        copy = bool(getattr(event,'state',0) & Gdk.ModifierType.CONTROL_MASK)
        if target_win is win and folder == browser.directory and not copy:
            if not copy and self.file_drag_origin:
                label, point, start_x, start_y = self.file_drag_origin
                x = max(0,min(int(point[0]+event.x-start_x),win.width-90))
                y = max(0,min(int(point[1]+event.y-start_y),win.height-140))
                try:
                    self.shortcut_icons.move('drive:'+str(browser.view.resolve(folder)),label,(x,y))
                except OSError as error:
                    print(f'Could not save icon position: {error}',flush=True)
            return
        self.transfer_files(sources, folder, copy)

    def release(self, _area, event):
        if self.pointer_scale != 1 and (self.file_drag or self.shortcut_drag or self.icon_drag or self.namespace_item_drag):
            event = ScaledPointer(event, self.pointer_scale)
        if event.button==1 and self.namespace_item_drag:
            win,label,point,start_x,start_y,initial_scroll=self.namespace_item_drag
            started=self.namespace_item_point is not None or drag_started(event.x-start_x,event.y-start_y)
            if started and not win.namespace_auto and win.namespace_view in ('large','small') and contains(win.namespace_viewport,event.x,event.y):
                from win95lx.explorer.namespace_layout import drag_position
                position=drag_position(point,(start_x,start_y),(event.x,event.y),initial_scroll,win.namespace_scroll,win.namespace_layout.viewport,win.namespace_layout.cell)
                try:
                    self.shortcut_icons.move('namespace:'+win.kind+':'+win.namespace_view,label,position)
                    self.namespace_item_point=position
                except OSError as error:print(f'Could not save namespace icon position: {error}',flush=True)
            self.namespace_item_drag=self.namespace_item_point=None
            self.area.queue_draw()
        if event.button == 1:
            self.namespace_drag = None
            self.wallpaper_drag = self.drive_scroll_drag = self.resolution_drag = None
        if event.button == 1 and self.file_drag:
            win, label, start_x, start_y = self.file_drag
            self.file_drag = None
            if self.file_drag_point is not None or drag_started(event.x-start_x,event.y-start_y):
                self.drop_drive_selection(win, event)
            elif self.file_drag_toggle:
                self.browser_for(win).selection.discard(label)
            elif not getattr(event,'state',0) & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
                self.edit_drive_selection(label, 0)
            self.file_drag_origin = self.file_drag_point = self.file_hover = None
        if event.button == 1 and self.shortcut_drag:
            win, label, target, point, start_x, start_y = self.shortcut_drag
            if self.shortcut_drag_point is not None:
                dx,dy=int(event.x-start_x),int(event.y-start_y)
                self.shortcut_drag_point=self.clamp_shortcut(win,point[0]+dx,point[1]+dy)
                try:
                    destination = self.shortcut_drop_target(event.x, event.y)
                    if (target[0] == 'accessory' and destination is not None
                            and destination[2] != win.folder and self.shortcut_folders.accepts(destination[2])):
                        self.shortcut_folders.move(target[1], destination[2])
                        self.item_selection = None
                    elif destination is not None and destination[0] is win:
                        self.shortcut_icons.move(win.folder, label, self.shortcut_drag_point)
                except OSError as error:
                    print(f'Could not save shortcut move: {error}', flush=True)
            self.shortcut_drag = self.shortcut_drag_point = self.shortcut_drop = None
            self.area.queue_draw()
        if event.button == 1 and self.icon_drag:
            if self.icon_drag_point is not None:
                _kind,point,start_x,start_y=self.icon_drag
                dx,dy=int(event.x-start_x),int(event.y-start_y)
                self.icon_drag_point=self.desktop_icons.clamp(point[0]+dx,point[1]+dy,self.width,self.height)
                try:
                    kind = self.icon_drag[0]
                    source = (self.desktop_folder.relative_to(self._drive.view.root)/kind[5:]
                              if kind.startswith('file:') else None)
                    destination = self.file_drop_destination(event.x,event.y,(source,) if source else ())
                    if kind.startswith('file:') and destination and (
                            destination[1] != self.desktop_folder.relative_to(self._drive.view.root)):
                        source = self.desktop_folder.relative_to(self._drive.view.root)/kind[5:]
                        self.transfer_files((source,),destination[1],
                                            bool(getattr(event,'state',0) & Gdk.ModifierType.CONTROL_MASK))
                    else:
                        self.desktop_icons.move(kind, self.icon_drag_point)
                except OSError as error:
                    print(f'Could not save desktop icon position: {error}', flush=True)
            self.icon_drag = self.icon_drag_point = self.file_hover = None
            self.area.queue_draw()
        self.drag = None
        return True
    def motion(self,area,event):
        if self.pointer_scale != 1:
            event = ScaledPointer(event, self.pointer_scale)
        if self.namespace_item_drag:
            win,label,point,start_x,start_y,initial_scroll=self.namespace_item_drag
            if self.namespace_item_point is not None or drag_started(event.x-start_x,event.y-start_y):
                from win95lx.explorer.namespace_layout import drag_position
                self.namespace_item_point=drag_position(point,(start_x,start_y),(event.x,event.y),initial_scroll,win.namespace_scroll,win.namespace_layout.viewport,win.namespace_layout.cell)
                self.area.queue_draw()
            return True
        if self.namespace_drag:
            win,axis,x,y,length,maximum,offset=self.namespace_drag
            value=VerticalScrollbar(length,maximum).value_at((event.x-x if axis==0 else event.y-y)-offset)
            position=list(win.namespace_scroll);position[axis]=value;win.namespace_scroll=tuple(position);self.area.queue_draw();return True
        if self.window_operation:
            win, operation = self.window_operation
            self.apply_window_operation(win, operation.motion(event.x,event.y,(self.width,self.height)))
            self.area.queue_draw()
        elif self.start_context:
            row = self.start_context.at(event.x, event.y)
            self.start_context.selected = row[0] if row else None
            self.area.queue_draw()
        elif self.resolution_drag:
            win, offset = self.resolution_drag
            self.move_resolution_slider(win, event.x-offset)
            self.area.queue_draw()
        elif self.wallpaper_drag:
            win, offset = self.wallpaper_drag
            control = background.scrollbar(self.wallpaper_max_scroll)
            self.wallpaper_scroll = control.value_at(event.y-offset-win.y-background.LIST_Y)
            self.area.queue_draw()
        elif self.drive_scroll_drag:
            win, offset = self.drive_scroll_drag
            _, height = self.drive_pane_size(win)
            _, _, maximum = self.browser_for(win).grid(*self.drive_pane_size(win))
            bar = VerticalScrollbar(height, maximum)
            self.browser_for(win).scroll = bar.value_at(event.y-offset-win.y-explorer_chrome.PANE_Y)
            self.area.queue_draw()
        elif self.file_drag:
            _,_,start_x,start_y = self.file_drag
            if self.file_drag_point is not None or drag_started(event.x-start_x,event.y-start_y):
                self.file_drag_point = event.x,event.y
                win,_,_,_ = self.file_drag
                browser = self.browser_for(win)
                sources = tuple(browser.directory/name for name in browser.selection)
                self.file_hover = self.file_drop_destination(event.x,event.y,sources)
                self.area.queue_draw()
        elif self.shortcut_drag:
            win, _label, target, (x, y), start_x, start_y = self.shortcut_drag
            dx, dy = int(event.x-start_x), int(event.y-start_y)
            if self.shortcut_drag_point is not None or drag_started(dx,dy):
                self.shortcut_drag_point = self.clamp_shortcut(win, x+dx, y+dy)
                destination = self.shortcut_drop_target(event.x, event.y) if target[0]=='accessory' else None
                self.shortcut_drop = destination[:2] if destination else None
                self.area.queue_draw()
        elif self.icon_drag:
            _name, (x, y), start_x, start_y = self.icon_drag
            dx, dy = int(event.x-start_x), int(event.y-start_y)
            if self.icon_drag_point is not None or drag_started(dx,dy):
                self.icon_drag_point = self.desktop_icons.clamp(x+dx, y+dy, self.width, self.height)
                source = self.desktop_folder.relative_to(self._drive.view.root)/_name[5:] if _name.startswith('file:') else None
                self.file_hover = self.file_drop_destination(event.x,event.y,(source,) if source else ())
                self.area.queue_draw()
        elif self.drag:
            win,dx,dy=self.drag;win.x=max(0,min(int(event.x-dx),self.width-80));win.y=max(0,min(int(event.y-dy),self.height-55));self.area.queue_draw()
        elif self.is_drive_menu_open():
            self.drive_menu_highlight = next((command for x,y,command,_ in self.drive_menu_rows
                                              if x <= event.x < x+(118 if self.popup[2][0].kind in ('computer','control','printers') else 152) and y <= event.y < y+17), None)
            self.area.queue_draw()
        elif self.state.start_open:
            for depth, (x, y, width, height) in reversed(list(enumerate(self.submenu_geometry()))):
                if x+3 <= event.x < x+width-3 and y+3 <= event.y < y+height-3:
                    row = int((event.y-y-3)//20)
                    self.select_submenu_row(depth, row, hover=True)
                    self.area.queue_draw()
                    return True
            x, y = self.menu_origin()
            if x+24 <= event.x < x+145:
                for index in range(len(menu.ROWS)):
                    row_y = menu.row_top(y, index)
                    if row_y <= event.y < row_y + menu.ROW_HEIGHT:
                        if index != self.state.menu_index or (index in menu.SUBMENUS and not self.menu_path):
                            self.state.menu_index = index
                            self.menu_path[:] = [(index, 0)] if index in menu.SUBMENUS else []
                            self.area.queue_draw()
                        break
        return True

    def is_drive_menu_open(self):
        if not self.popup:
            return False
        context = self.popup[2]
        return isinstance(context, tuple) and (context[0].kind == 'drive' and context[1] in ('Edit','File','Item') or context[0].kind in ('computer','control','printers') and context[1]=='File')

    def drive_menu_key(self, name, alt):
        win = self.state.active
        if not win or win.kind not in ('drive','computer','control','printers') or self.state.dialog or self.state.start_open:
            return False
        if alt and name.lower() in (('e','f') if win.kind=='drive' else ('f',)):
            label, offset = ('Edit',55) if name.lower() == 'e' else ('File',24)
            self.action(('window-menu',win,label,offset))
            if win.kind in ('computer','control','printers'):
                selection=(self.item_selection[1] or '*') if self.item_selection and self.item_selection[0] is win else None
                self.drive_menu_highlight=next(row.command for row in self.namespace_file_rows(win) if row and row.enabled)
            else:
                self.drive_menu_highlight = 'new-folder' if label=='File' else 'undo'
            return True
        if alt or not self.is_drive_menu_open():
            return False
        if win.kind in ('computer','control','printers') and len(name)==1:
            selection=(self.item_selection[1] or '*') if self.item_selection and self.item_selection[0] is win else None
            row=next((row for row in self.namespace_file_rows(win)
                      if row and row.enabled and row.mnemonic==name.lower()),None)
            if row:
                self.action(('close',win) if row.command=='close' else ('computer-menu',win,row.command))
                return True
        if name in ('Up','Down') and self.drive_menu_rows:
            commands = [command for _,_,command,_ in self.drive_menu_rows]
            position = commands.index(self.drive_menu_highlight) if self.drive_menu_highlight in commands else (-1 if name=='Down' else 0)
            self.drive_menu_highlight = commands[(position+(1 if name=='Down' else -1))%len(commands)]
        elif name in ('Return','KP_Enter'):
            row = next((row for row in self.drive_menu_rows if row[2] == self.drive_menu_highlight), None)
            if row:
                self.action(row[3])
        elif name == 'Escape':
            self.popup = None
        else:
            return False
        return True

    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        ctrl=event.state&Gdk.ModifierType.CONTROL_MASK
        alt=event.state&Gdk.ModifierType.MOD1_MASK
        if self.suspended:
            self.suspended=False
        elif self.window_operation:
            win, operation = self.window_operation
            if name in ARROWS:
                self.apply_window_operation(win, operation.step(*ARROWS[name], (self.width,self.height)))
            elif name in ('Escape', 'Return', 'KP_Enter'):
                if name == 'Escape':
                    self.apply_window_operation(win, operation.original)
                self.window_operation = None
        elif self.start_context:
            if name == 'Escape':
                self.start_context = None
            elif name in ('Up', 'Down'):
                positions = [y for y, row in self.start_context.entries() if row and row[1]]
                current = self.start_context.selected
                step = 1 if name == 'Down' else -1
                index = positions.index(current) if current in positions else (-1 if step == 1 else 0)
                self.start_context.selected = positions[(index+step) % len(positions)]
            elif name == 'Return' and self.start_context.selected is not None:
                context = self.start_context
                row = context.at(context.x+4, context.selected)
                self.start_context = None
                if row:
                    self.action(row[1][1])
        elif self.address_window is not None:
            if name=='Escape':
                self.address_window=None
            elif name in ('Return','KP_Enter'):
                value=self.address_text.strip()
                self.address_window=None
                if value.casefold() in ('my computer',''):
                    pass
                elif value.casefold()=='control panel':
                    self.open('control')
                else:
                    location=value.replace('\\','/')
                    if location[:2].casefold()=='c:':location=location[2:]
                    self.open('drive',location.lstrip('/') or '.')
            else:
                self.address_entry.key(name,event.string,bool(ctrl),bool(event.state&Gdk.ModifierType.SHIFT_MASK))
                self.address_text=self.address_entry.text
        elif self.state.dialog == 'shutdown':
            self.shutdown_dialog.key(self, name, bool(event.state & Gdk.ModifierType.SHIFT_MASK))
        elif self.state.dialog == 'run':
            self.run_dialog.handle_key(self, event)
        elif self.state.dialog == 'resolution-confirm':
            if name in ('Escape', 'Return', 'KP_Enter', 'n', 'N'):
                self.finish_resolution_trial(False)
            elif name in ('y', 'Y'):
                self.finish_resolution_trial(True)
        elif not ctrl and self.drive_menu_key(name, alt):
            pass
        elif not ctrl and self.resolution_key(name, alt, bool(event.state & Gdk.ModifierType.SHIFT_MASK)):
            pass
        elif not ctrl and self.wallpaper_combo_key(name, alt):
            pass
        elif name=='Escape' and not ctrl:
            self.namespace_item_drag=self.namespace_item_point=None
            self.shortcut_drag = self.shortcut_drag_point = self.shortcut_drop = None
            self.file_drag = self.file_drag_origin = self.file_drag_point = self.file_hover = None
            self.icon_drag = self.icon_drag_point = None
            if self.state.start_open and self.menu_path:
                self.menu_path.pop()
            else:
                self.state.escape()
                self.popup=None
        elif self.state.dialog:
            if name=='Return':
                self.submit_dialog()
            elif self.state.dialog == 'find' and not ctrl and not alt:
                if name=='BackSpace':
                    self.dialog_input=self.dialog_input[:-1]
                elif event.string and event.string.isprintable() and len(self.dialog_input)<60:
                    self.dialog_input+=event.string
                self.dialog_error=''
        elif name in ('r', 'R') and event.state & Gdk.ModifierType.MOD4_MASK:
            self.action(('run',))
        elif name in ('Super_L','Super_R') or ctrl and name=='Escape':
            self.show_start()
        elif alt and name=='space' and self.state.active:
            self.open_system_menu(self.state.active)
        elif alt and name=='F4':
            self.state.close()
        elif alt and name=='Tab':
            self.state.cycle()
        elif self.state.start_open:
            if name in ('Up','Down'):
                direction=1 if name=='Down' else -1
                if self.menu_path:
                    key, selection = self.menu_path[-1]
                    self.menu_path[-1] = (key, (selection+direction) % len(self.submenu_entries(key)))
                else:
                    current=self.state.menu_index
                    if current<0:
                        current=-1 if direction==1 else 0
                    self.state.menu_index=(current+direction)%len(menu.ROWS)
            elif name=='Left':
                if self.menu_path:
                    self.menu_path.pop()
            elif name in ('Return','Right'):
                index=self.state.menu_index
                if self.menu_path:
                    key, row = self.menu_path[-1]
                    action = self.submenu_entries(key)[row][2]
                    if name=='Return' or action[0]=='submenu':
                        self.select_submenu_row(len(self.menu_path)-1, row)
                elif index>=0 and (name=='Return' or index in menu.SUBMENUS):
                    self.choose_menu_row(index)
            elif len(name or '')==1:
                match=next((i for i,row in enumerate(menu.ROWS) if row[2]==name.lower()),None)
                if match is not None:
                    self.choose_menu_row(match)
        elif self.state.active and self.state.active.kind in ('computer','control','printers') and name in ('Left','Right','Up','Down','Home','End'):
            from win95lx.explorer.namespace_layout import reveal
            win=self.state.active;labels=[label for _,label,_ in self.printer_namespace().entries()] if win.kind=='printers' else list(cpl_catalog.labels()) if win.kind=='control' else ['(C:)','Control Panel'];layout=win.namespace_layout
            if labels and layout:
                current=labels.index(win.focus_item) if win.focus_item in labels else 0
                if name=='Home':index=0
                elif name=='End':index=len(labels)-1
                else:
                    x,y=layout.positions[current];axis=0 if name in ('Left','Right') else 1;direction=-1 if name in ('Left','Up') else 1
                    candidates=[i for i,pos in enumerate(layout.positions) if (pos[axis]-(x,y)[axis])*direction>0]
                    index=min(candidates,key=lambda i:(abs(layout.positions[i][1-axis]-(x,y)[1-axis]),abs(layout.positions[i][axis]-(x,y)[axis]))) if candidates else current
                win.focus_item=labels[index];self.item_selection=(win,labels[index]);win.info_scroll=0;win.namespace_scroll=reveal(layout,index)
        elif (self.state.active and self.state.active.kind == 'drive'
              and ((ctrl and name.lower() in ('x','c','v','a','w'))
                   or name in ('Delete','F2','F5') or alt and name == 'Return')):
            win = self.state.active
            command = {'x':'cut','c':'copy','v':'paste','a':'select-all','w':'close',
                       'delete':'trash','f2':'rename','f5':'refresh','return':'properties'}[name.lower()]
            if command == 'close':
                self.action(('close', win))
            elif command == 'refresh':
                self.navigate_drive(win, self.drive.directory)
            else:
                self.action(('drive-edit', win, command))
        elif name=='F5' and self.state.active and self.state.active.kind=='printers':self.refresh_printers()
        elif name=='F5' and not self.state.active:
            self.action(('desktop-refresh',))
        elif alt and name=='Return' and self.state.selection=='computer':self.open('system')
        elif name=='Return' and self.state.selection:self.open_desktop_item(self.state.selection)
        elif name=='BackSpace' and self.state.active and self.state.active.kind=='drive':
            self.navigate_drive(self.state.active, self.drive.directory.parent)
        elif (name=='BackSpace' and self.state.active and self.state.active.kind=='start-folder'
              and self.state.active.folder is not None):
            parent = {0:None, 'accessories':0, 'games':'accessories'}[self.state.active.folder]
            self.action(('start-folder', parent))
        elif name=='Return' and self.item_selection and self.item_selection[0] is self.state.active:
            active=self.state.active.kind;label=self.item_selection[1]
            if active=='printers':
                target=next((target for _,caption,target in self.printer_namespace().entries() if caption==label),None)
                if target:self.action(target)
            if active == 'drive':
                entry = next((item for item in self.drive.entries if item[0]==label), None)
                if entry:
                    self.open_drive_entry(self.state.active, *entry)
            if active == 'start-folder':
                folder = self.state.active.folder
                row = next((entry for entry in self.shortcut_folders.entries(folder) if entry[0]==label), None)
                if row:
                    action = row[2]
                    self.action(('start-folder', action[1]) if action[0]=='submenu' else action)
            target={('computer','(C:)'):'drive',('computer','Control Panel'):'control',**{('control',name):kind for name,kind in cpl_catalog.targets().items()}}.get((active,label))
            if target:self.open(target)
        self.area.queue_draw();return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assets',type=Path,required=True);args=parser.parse_args()
    if os.environ.get('XDG_SESSION_TYPE') not in ('x11',None):parser.error('Use the dedicated X11 development session')
    if not (args.assets/'ms-sans-serif-8.fnt').is_file():parser.error('Original private font bundle required; no fallback is used')
    app=Shell(args.assets)
    app.show_all()
    if os.environ.get('WIN95LX_STARTUP_SOUND') == '1':
        def start_audio():
            Thread(target=play_startup, args=(args.assets,), daemon=True).start()
            return GLib.SOURCE_REMOVE
        GLib.idle_add(start_audio)
    Gtk.main()
if __name__=='__main__':main()
