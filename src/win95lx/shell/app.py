"""Experimental Win95LX shell surface. Run only in the dedicated Linux guest.

Original bitmap assets are required. This is not a complete window manager,
Windows compatibility layer or a pixel-verified replica.
"""
import argparse,datetime,fnmatch,json,os,subprocess
from threading import Thread
from pathlib import Path
import gi

gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib,GdkPixbuf
import cairo
from win95lx.assets.bitmap import BitmapFont
from win95lx.shell.model import DesktopState
from win95lx.shell.desktop_icons import DesktopIcons, ICON_WIDTH, ICON_HEIGHT
from win95lx.shell import accessories, start_menu as menu
from win95lx.shell.shutdown_dialog import ShutdownDialog, is_development_guest
from win95lx.shell.run_dialog import RunDialog
from win95lx.display_modes import DISPLAY_MODES, remember_resolution, set_resolution
from win95lx.explorer.presentation import DriveView
from win95lx.control_panel.applets import APPLETS
from win95lx.sound import play_startup
from win95lx.shell.widgets import Painter,FACE,LIGHT,SHADOW,BLACK,NAVY,TEAL
class Shell(Gtk.Window):
    def __init__(self,assets):
        super().__init__(title='Win95LX Development Shell');self.set_decorated(False);self.set_default_size(800,600);self.move(0,0);self.fullscreen();self.state=DesktopState();self.assets=assets;self.font=BitmapFont((assets/'ms-sans-serif-8.fnt').read_bytes());self.images={};self.small_images={};self.hits=[];self.drag=None;self.clock=None;self.popup=None;self.item_selection=None;self.pending_resolution=None;self.resolution_error=False
        self.accessory_windows = {}
        self.desktop_icons = DesktopIcons()
        self.icon_drag = None
        self.icon_drag_point = None
        self.shutdown_dialog = ShutdownDialog(assets)
        self.run_dialog = RunDialog()
        self.shutdown_windows = []
        self.cursors = {}
        self.menu_hit_start = 0
        self.menu_path = []
        self.dialog_input = ''
        self.dialog_error = ''
        self.find_results = None
        self.suspended = False
        self.drive=Path.home()/'Win95LXDrive';self.drive.mkdir(exist_ok=True);self.driveview=DriveView(self.drive)
        for path in assets.glob('shell32-group-*.png'):self.images[int(path.stem.split('-')[-1])]=cairo.ImageSurface.create_from_png(str(path))
        for path in assets.glob('shell32-small-*.png'):
            self.small_images[int(path.stem.split('-')[-1])]=cairo.ImageSurface.create_from_png(str(path))
        for kind in accessories.APPLICATIONS:
            icon = assets / f'accessory-{kind}.png'
            if icon.exists():
                self.small_images[kind] = cairo.ImageSurface.create_from_png(str(icon))
        start_flag = assets/'start-flag.png'
        if start_flag.exists():
            self.images['start'] = cairo.ImageSurface.create_from_png(str(start_flag))
        display_icon = assets/'display-applet.png'
        if display_icon.exists():
            self.images['display'] = cairo.ImageSurface.create_from_png(str(display_icon))
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
        accessories.install_menu_style(screen)
        screen.connect('size-changed', self.resize_to_display)
        self.width, self.height = screen.get_width(), screen.get_height()
        self.set_default_size(self.width, self.height)
        self.connect('realize',self.cursor)
        GLib.timeout_add_seconds(1,self.tick)
    def resize_to_display(self, screen):
        width, height = screen.get_width(), screen.get_height()
        self.resize(width, height)
        for window in self.state.windows:
            if window.restored_bounds is not None:
                window.width, window.height = width, height-28
            window.x = max(0, min(window.x, width - window.width))
            window.y = max(0, min(window.y, height - 28 - window.height))

    def cursor_for(self, name):
        if name in self.cursors:
            return self.cursors[name]
        path = self.assets / f'{name}.png'
        metadata = self.assets / f'{name}-cursor.json'
        if name == 'arrow' and not metadata.exists():
            metadata = self.assets / 'cursor.json'
        if path.exists() and metadata.exists():
            hotspot = json.loads(metadata.read_text())['hotspot']
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
            self.cursors[name] = Gdk.Cursor.new_from_pixbuf(self.get_display(), pixbuf, *hotspot)
        return self.cursors.get(name)

    def cursor(self, *_):
        cursor = self.cursor_for('arrow')
        if cursor:
            self.get_window().set_cursor(cursor)
            Gdk.get_default_root_window().set_cursor(cursor)

    def tick(self):self.area.queue_draw();return True
    def hit(self,x,y,w,h,action):self.hits.append((x,y,w,h,action))
    def button(self,p,label,x,y,w,h,action,pressed=False):p.button(label,x,y,w,h,pressed);self.hit(x,y,w,h,action)
    def icon(self,p,ident,label,x,y,action,selected=False):
        if ident in self.images:p.image(self.images[ident],x+16,y)
        width=self.font.width(label)
        if selected:p.fill(x+(64-width)//2-2,y+35,width+4,15,NAVY)
        p.text(label,x+(64-width)//2,y+36,LIGHT if selected else BLACK);self.hit(x,y,70,54,action)
    def open(self,kind):
        self.state.open(kind)
        self.menu_path.clear()
        self.popup=None
        if kind=='display':
            self.pending_resolution=(self.width,self.height)
            self.resolution_error=False
        self.area.queue_draw()
    def launch_accessory(self, kind):
        self.state.start_open = False
        self.menu_path.clear()
        self.popup = None
        window = self.accessory_windows.get(kind)
        if window is None:
            try:
                window = accessories.build(kind, self)
            except (ImportError, AttributeError) as error:
                print(f'Could not start {kind}: {error}', flush=True)
                self.state.dialog = 'run'
                self.dialog_error = 'This program could not be started.'
                return
            self.accessory_windows[kind] = window
            window.connect('destroy', self.accessory_closed, kind)
            window.connect('notify::title', lambda *_: self.area.queue_draw())
            window.connect('notify::is-active', lambda *_: self.area.queue_draw())
        window.show_all()
        window.present()

    def accessory_closed(self, window, kind):
        del self.accessory_windows[kind]
        if self.get_window():
            self.get_window().focus(Gdk.CURRENT_TIME)
        self.area.queue_draw()

    def draw(self,area,cr):
        width=area.get_allocated_width();height=area.get_allocated_height();self.width=width;self.height=height;self.hits=[];p=Painter(cr,self.font);p.fill(0,0,width,height,TEAL)
        if self.state.dialog == 'shutdown':
            self.shutdown_dialog.draw(self, p)
            return
        if self.suspended:
            p.fill(0,0,width,height,BLACK)
            return
        desktop_items = (
            ('computer' if 'computer' in self.images else 16, 'My Computer', 'computer'),
            (32, 'Recycle Bin', 'recycle'),
        )
        for ident,label,kind in desktop_items:
            x, y = self.desktop_icons.position(kind, width, height)
            if self.icon_drag and self.icon_drag[0] == kind and self.icon_drag_point is not None:
                x, y = self.icon_drag_point
            if ident in self.images:
                p.image(self.images[ident], x+21, y)
            label_width=self.font.width(label)
            label_x=x+37-label_width//2
            selected=self.state.selection==kind
            if selected:
                p.fill(label_x-1,y+35,label_width+2,15,NAVY)
            p.text(label,label_x,y+35,LIGHT)
            self.hit(x,y,ICON_WIDTH,ICON_HEIGHT,('desktop',kind))
        for win in self.state.windows:
            if not win.minimized:self.window(p,win)
        bar=height-28
        p.fill(0,bar,width,28,FACE)
        p.fill(0,bar+1,width,1,LIGHT)
        start_image=self.images.get('start-down' if self.state.start_open else 'start-up')
        if start_image:
            p.image(start_image,2,bar+4)
        else:
            self.draw_start_button(p,bar)
        self.hit(2,bar+4,54,22,('start',))
        tasks = [(win.title, ('task', win), win is self.state.active)
                 for win in self.state.windows]
        tasks.extend((win.get_title(), ('accessory-task', win), win.is_active())
                     for win in self.accessory_windows.values())
        for index, (title, action, active) in enumerate(tasks):
            x=66+index*148
            if x+145>width-86:break
            self.button(p,title[:21],x,bar+4,144,22,action,active)
        p.fill(width-69,bar+4,1,22,SHADOW)
        p.fill(width-68,bar+4,1,22,LIGHT)
        p.bevel(width-65,bar+4,63,22,True)
        clock=self.clock or datetime.datetime.now().strftime('%I:%M %p').lstrip('0')
        p.text(clock,width-34-self.font.width(clock)//2,bar+8)
        self.menu_hit_start=len(self.hits)
        if self.state.start_open:self.startmenu(p)
        if self.state.start_open:
            self.submenu_draw(p)
        if self.popup:self.context(p,*self.popup)
        if self.state.dialog:self.dialog(p)

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
        x, y, w, h = win.x, win.y, win.width, win.height
        explorer = win.kind in ('computer','control','drive','recycle')
        resizable = explorer or win.kind == 'notepad'
        active = win is self.state.active
        p.window_frame(x,y,w,h)
        p.fill(x+4,y+4,w-8,18,NAVY if active else SHADOW)
        p.text(win.title,x+(27 if resizable else 7),y+4,LIGHT,bold=True)
        ident = {'computer':'computer' if 'computer' in self.images else 16,'control':36,'drive':9,'notepad':2,'recycle':32}.get(win.kind)
        if resizable and ident in self.small_images:
            p.image(self.small_images[ident],x+5,y+5)
        elif resizable and ident in self.images:
            p.cr.save()
            p.cr.translate(x+5,y+5)
            p.cr.scale(.5,.5)
            p.image(self.images[ident],0,0)
            p.cr.restore()
        self.hit(x,y,w,22,('drag',win))
        buttons = [(w-21,'close','close')]
        if resizable:
            buttons.extend((
                (w-55,'minimize','minimize'),
                (w-39,'restore' if win.restored_bounds else 'maximize','maximize'),
            ))
        for offset, symbol, action in buttons:
            p.caption_button(symbol,x+offset,y+6)
            self.hit(x+offset,y+6,16,14,(action,win))
        if explorer:
            p.fill(x+4,y+23,w-8,1,SHADOW)
            p.fill(x+5,y+24,w-10,1,LIGHT)
            labels = ((16,'File'),(55,'Edit'),(89,'View'),(127,'Go'),(158,'Favorites'),(216,'Help'))
            for offset,label in labels:
                p.text(label,x+offset,y+29)
                self.hit(x+offset-5,y+25,p.font.width(label)+10,20,('window-menu',win,label,offset))
            p.bevel(x+4,y+46,w-8,h-68,True)
            p.fill(x+6,y+48,w-12,h-72,LIGHT)
            items={'computer':[(9,'(C:)','drive'),(36,'Control Panel','control')],'control':[(('display' if 'display' in self.images else 147),'Display','display')],'recycle':[]}.get(win.kind)
            if win.kind=='drive':items=[(4 if directory else 1,name,None) for name,directory in self.driveview.entries()][:12]
            for i,(ident,label,kind) in enumerate(items or []):
                xx=x+16+(i%4)*102;yy=y+58+(i//4)*69
                self.icon(p,ident,label,xx,yy,('item',win,kind,label),self.item_selection in ((win.kind,label),(win.kind,None)))
            p.bevel(x+4,y+h-19,w-8,15,True);p.text(str(len(items or []))+' object(s)',x+8,y+h-18)
        elif win.kind=='display':
            APPLETS[win.kind](p,win,self.button,self.pending_resolution or (self.width,self.height),self.resolution_error)
        elif win.kind in APPLETS:APPLETS[win.kind](p,win,self.button)
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

    def submenu_geometry(self):
        x, y = self.menu_origin()
        width = menu.WIDTH
        row_y = menu.row_top(y, self.state.menu_index)
        for key, selected in self.menu_path:
            options = menu.SUBMENUS[key]
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
            for row, (label, icon, action) in enumerate(menu.SUBMENUS[key]):
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
        action = menu.SUBMENUS[key][row][2]
        if row != current:
            self.menu_path[depth:] = [(key, row)]
        if action[0] == 'submenu':
            if len(self.menu_path) == depth + 1:
                self.menu_path.append((action[1], 0))
        elif not hover:
            self.action(action)

    def show_start(self):
        self.state.start_open = not self.state.start_open
        self.state.menu_index = -1
        self.popup = None
        self.menu_path.clear()

    def choose_menu_row(self, index):
        self.state.menu_index = index
        if index in menu.SUBMENUS:
            self.menu_path[:] = [(index, 0)]
        else:
            self.action(menu.ROWS[index][3])

    def context(self,p,x,y,kind):
        if isinstance(kind,tuple):
            win, menu = kind
            options = {
                'File': [('Close',('close',win))],
                'Edit': [('Select All',('select-all',win))],
                'View': [('Refresh',('dismiss',))],
                'Go': [('My Computer',('open','computer')),('(C:)',('open','drive'))],
                'Favorites': [('Control Panel',('open','control'))],
                'Help': [('About Win95LX',('about',))],
            }[menu]
        else:options=[('Open',('open',kind)),('Properties',('open','system' if kind=='computer' else 'display'))] if kind else [('Properties',('open','display'))]
        p.bevel(x,y,130,len(options)*22+6)
        for i,(label,action) in enumerate(options):p.text(label,x+8,y+6+i*22);self.hit(x+3,y+3+i*22,124,22,action)
    def dialog(self,p):
        kind = self.state.dialog
        if kind == 'run':
            self.run_dialog.draw(self, p)
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
                entries=self.driveview.entries()
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
        if self.state.dialog and kind not in ('exit','cancel','dialog-submit'):return
        if kind=='start':
            self.show_start()
        elif kind=='menu':
            self.choose_menu_row(action[1])
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
                self.open(action[1])
            elif event and event.button == 1:
                point = self.desktop_icons.position(action[1], self.width, self.height)
                self.icon_drag = action[1], point, event.x, event.y
        elif kind=='open' and action[1]:self.open(action[1])
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
            self.item_selection=(action[1].kind,action[3]);self.state.selection=None
            if event and event.type==Gdk.EventType._2BUTTON_PRESS and action[2]:self.open(action[2])
        elif kind=='resolution-step':
            mode=self.pending_resolution
            index=DISPLAY_MODES.index(mode) if mode in DISPLAY_MODES else 0
            self.pending_resolution=DISPLAY_MODES[(index+action[1])%len(DISPLAY_MODES)]
            self.resolution_error=False
        elif kind=='resolution-apply':
            try:
                set_resolution(*self.pending_resolution)
            except (OSError, subprocess.SubprocessError, ValueError, StopIteration):
                self.resolution_error=True
            else:
                try:
                    remember_resolution(*self.pending_resolution)
                except OSError as error:
                    print(f'Could not save the display mode: {error}', flush=True)
                self.state.windows.remove(action[1])
        elif kind=='close':self.state.windows.remove(action[1]);self.popup=None
        elif kind=='minimize':action[1].minimized=True
        elif kind=='task':
            win=action[1]
            if win is self.state.active:win.minimized=True
            else:self.state.windows.remove(win);win.minimized=False;self.state.windows.append(win)
        elif kind in ('drag','maximize'):
            win=action[1]
            self.state.windows.remove(win)
            self.state.windows.append(win)
            resizable=win.kind in ('computer','control','drive','recycle','notepad')
            if resizable and (kind=='maximize' or event.type==Gdk.EventType._2BUTTON_PRESS):
                self.drag=None
                if win.restored_bounds is None:
                    win.restored_bounds=(win.x,win.y,win.width,win.height)
                    win.x,win.y,win.width,win.height=0,0,self.width,self.height-28
                else:
                    win.x,win.y,win.width,win.height=win.restored_bounds
                    win.restored_bounds=None
                    self.resize_to_display(self.get_screen())
            elif win.restored_bounds is None:
                self.drag=(win,event.x-win.x,event.y-win.y)
        elif kind=='shutdown':self.open_shutdown()
        elif kind=='about':self.popup=None;self.state.dialog='about'
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
            self.popup=(win.x+offset-5,win.y+45,(win,menu))
        elif kind=='select-all':
            self.item_selection=(action[1].kind,None)
            self.popup=None
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

    def press(self,area,event):
        if event.button == 1:
            self.get_window().focus(event.time)
        if self.suspended:
            self.suspended=False
            self.area.queue_draw()
            return True
        if self.state.dialog and event.button==3:
            return True
        if event.button==3:
            target=next((a for x,y,w,h,a in reversed(self.hits) if x<=event.x<x+w and y<=event.y<y+h and a[0]=='desktop'),None);self.popup=(min(int(event.x),self.width-133),min(int(event.y),self.height-90),target[1] if target else None);self.area.queue_draw();return True
        hits=self.hits
        if self.state.start_open:
            hits=[hit for hit in self.hits[:self.menu_hit_start] if hit[4]==('start',)]
            hits.extend(self.hits[self.menu_hit_start:])
        for x,y,w,h,action in reversed(hits):
            if x<=event.x<x+w and y<=event.y<y+h:self.action(action,event);return True
        self.menu_path.clear()
        self.state.start_open=False;self.popup=None;self.state.selection=None;self.area.queue_draw();return True
    def release(self, _area, event):
        if event.button == 1 and self.icon_drag:
            if self.icon_drag_point is not None:
                try:
                    self.desktop_icons.move(self.icon_drag[0], self.icon_drag_point)
                except OSError as error:
                    print(f'Could not save desktop icon position: {error}', flush=True)
            self.icon_drag = self.icon_drag_point = None
            self.area.queue_draw()
        self.drag = None
        return True
    def motion(self,area,event):
        if self.icon_drag:
            _name, (x, y), start_x, start_y = self.icon_drag
            dx, dy = int(event.x-start_x), int(event.y-start_y)
            if self.icon_drag_point is not None or max(abs(dx), abs(dy)) >= 4:
                self.icon_drag_point = self.desktop_icons.clamp(x+dx, y+dy, self.width, self.height)
                self.area.queue_draw()
        elif self.drag:
            win,dx,dy=self.drag;win.x=max(0,min(int(event.x-dx),self.width-80));win.y=max(0,min(int(event.y-dy),self.height-55));self.area.queue_draw()
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

    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        ctrl=event.state&Gdk.ModifierType.CONTROL_MASK
        alt=event.state&Gdk.ModifierType.MOD1_MASK
        if self.suspended:
            self.suspended=False
        elif self.state.dialog == 'shutdown':
            self.shutdown_dialog.key(self, name, bool(event.state & Gdk.ModifierType.SHIFT_MASK))
        elif self.state.dialog == 'run':
            self.run_dialog.handle_key(self, event)
        elif name=='Escape' and not ctrl:
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
        elif alt and name=='F4':
            self.state.close()
        elif alt and name=='Tab':
            self.state.cycle()
        elif self.state.start_open:
            if name in ('Up','Down'):
                direction=1 if name=='Down' else -1
                if self.menu_path:
                    key, selection = self.menu_path[-1]
                    self.menu_path[-1] = (key, (selection+direction) % len(menu.SUBMENUS[key]))
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
                    action = menu.SUBMENUS[key][row][2]
                    if name=='Return' or action[0]=='submenu':
                        self.select_submenu_row(len(self.menu_path)-1, row)
                elif index>=0 and (name=='Return' or index in menu.SUBMENUS):
                    self.choose_menu_row(index)
            elif len(name or '')==1:
                match=next((i for i,row in enumerate(menu.ROWS) if row[2]==name.lower()),None)
                if match is not None:
                    self.choose_menu_row(match)
        elif alt and name=='Return' and self.state.selection=='computer':self.open('system')
        elif name=='Return' and self.state.selection:self.open(self.state.selection)
        elif name=='Return' and self.item_selection and self.state.active:
            active=self.state.active.kind;label=self.item_selection[1]
            target={('computer','(C:)'):'drive',('computer','Control Panel'):'control',('control','Display'):'display'}.get((active,label))
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
