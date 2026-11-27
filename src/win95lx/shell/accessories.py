"""Classic captions for GTK accessories in the standalone X11 session."""

from importlib import import_module
from pathlib import Path

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GObject

from win95lx.shell.menu_layout import NOTEPAD_FILE_WIDTH, NOTEPAD_HELP_WIDTH, POPUP_GUTTER
from win95lx.shell.system_menu import ARROWS, COMMANDS, MENU_WIDTH, WindowOperation, options
from win95lx.shell.widgets import FACE, LIGHT, NAVY, SHADOW, Painter

# Window bounds from the original 800×600 accessory captures.
REFERENCE_BOUNDS = {
    'notepad': (68, 65, 600, 412),
    'wordpad': (110, 110, 600, 411),
    'calc': (88, 88, 276, 272),
}

APPLICATIONS = {
    'notepad': ('notepad', 'NotepadWindow'),
    'wordpad': ('wordpad', 'build_window'),
    'calc': ('calculator', 'build_window'),
    'winmine': ('minesweeper', 'build_window'),
}

# Explicit GTK gadget-node backgrounds prevent theme white/transparent troughs.
# The generated RGB tile is checked as actual GTK pixels at1x/2x scale.
# Default gray stipple is a requested policy; some reference versions
# expose white tracks and must be recorded as explicit visual exceptions.
def _scrollbar_style():
    roots=('scrollbar.win95-app-scrollbar','.win95-scrollbars scrollbar','scrollbar.notepad-scrollbar','.win95-wordpad scrollbar','.win95-file scrollbar','.win95-native-file scrollbar')
    resource=Path(__file__).parent/'resources/scrollbar-track.png'
    double=resource.with_name('scrollbar-track@2.png')
    image='-gtk-scaled(url("'+resource.as_uri()+'"),url("'+double.as_uri()+'"))' if resource.is_file() and double.is_file() else 'none'
    def rule(suffix,body):return ', '.join(root+suffix for root in roots)+' {'+body+'}\n'
    css=rule('', '-GtkScrollbar-has-backward-stepper:true;-GtkScrollbar-has-forward-stepper:true;border:0;padding:0;margin:0;border-radius:0;opacity:1;transition:none;animation:none;')
    background='background-color:#c0c0c0;background-image:'+image+';background-repeat:repeat;background-size:2px 2px;border-radius:0;box-shadow:none;opacity:1;transition:none;animation:none;'
    for suffix in ('',' contents',' trough'):css+=rule(suffix,background)
    css+=rule(' slider','background:#c0c0c0;border:1px solid;border-color:#fff #000 #000 #fff;border-radius:0;box-shadow:inset -1px -1px #808080;min-width:6px;min-height:6px;margin:0;padding:0;opacity:1;transition:none;animation:none;')
    css+=rule(' button','background:#c0c0c0;color:#000;border:1px solid;border-color:#fff #000 #000 #fff;border-radius:0;box-shadow:inset -1px -1px #808080;min-width:14px;min-height:14px;margin:0;padding:0;opacity:1;transition:none;animation:none;')
    css+=rule(' button:disabled','color:#808080;opacity:1;')
    css+=rule('.win95-unscrollable slider','background:none;border-color:transparent;box-shadow:none;opacity:0;')
    css+=rule('.win95-unscrollable button','color:#808080;')
    css+=rule(' button:active','border-color:#808080 #fff #fff #808080;box-shadow:inset 1px 1px #000;')
    css+=rule('.vertical','min-width:16px;')+rule('.horizontal','min-height:16px;')
    css+=rule('.vertical slider','min-width:14px;')+rule('.horizontal slider','min-height:14px;')
    # Explicit native IE4 profiles: exposed tracks measured solid white in
    # Notepad, WordPad and the common file dialog. Do not infer all controls
    # share one color just because the global default is stippled gray.
    white=('scrollbar.notepad-scrollbar','.win95-wordpad scrollbar','.win95-file scrollbar','.win95-native-file scrollbar')
    for suffix in ('',' contents',' trough'):
        css+=', '.join(root+suffix for root in white)+' {background-color:#fff;background-image:none;}\n'
    return css.encode()

SCROLLBAR_STYLE=_scrollbar_style()

def style_scrollbars(scroller):
    """Track native no-range appearance without disabling a text editor.

    GTK does not mark a range with upper==page_size insensitive: its slider
    fills the track. Native editors hide that thumb. Adjustment changes update
    only a CSS class; value changes do not cause repeated style invalidations.
    """
    if getattr(scroller,'_win95_scrollbar_styled',False):return
    scroller._win95_scrollbar_styled=True;bindings=[];notify=[]
    scroller._win95_scrollbar_connections=bindings
    def update(*_):
        for bar,adjustment in ((scroller.get_hscrollbar(),scroller.get_hadjustment()),(scroller.get_vscrollbar(),scroller.get_vadjustment())):
            context=bar.get_style_context();context.add_class('win95-app-scrollbar')
            absent=adjustment.get_upper()-adjustment.get_lower()<=adjustment.get_page_size()+1e-9
            if absent and not context.has_class('win95-unscrollable'):context.add_class('win95-unscrollable')
            elif not absent and context.has_class('win95-unscrollable'):context.remove_class('win95-unscrollable')
    def clear():
        for adjustment,handler in bindings:
            if adjustment.handler_is_connected(handler):adjustment.disconnect(handler)
        bindings.clear()
    def bind(*_):
        clear()
        for adjustment in(scroller.get_hadjustment(),scroller.get_vadjustment()):bindings.append((adjustment,adjustment.connect('changed',update)))
        update()
    def cleanup(*_):
        clear()
        for handler in notify:
            if scroller.handler_is_connected(handler):scroller.disconnect(handler)
        notify.clear();scroller._win95_scrollbar_styled=False
    notify.extend(scroller.connect('notify::'+name,bind)for name in('hadjustment','vadjustment'))
    scroller.connect('destroy',cleanup);bind()


MENU_STYLE = b"""
.win95-app-menubar, .win95-app-menu {
    background: #c0c0c0;
    background-image: none;
    color: black;
    font: 11px "Liberation Sans";
    border-radius: 0;
    box-shadow: none;
    padding: 0;
}
.win95-app-menubar {
    border: 0;
    margin: 0;
}
.win95-app-menubar > menuitem {
    padding: 0 6px;
    min-height: 20px;
}
.win95-app-menubar.notepad-menu > menuitem,
.win95-app-menubar.wordpad-menubar > menuitem { min-height: 19px; }
.win95-app-menu {
    padding: 1px;
    border: 2px solid;
    border-color: #fff #404040 #404040 #fff;
}
.win95-app-menu.notepad-file-menu, .win95-app-menu.notepad-edit-menu { padding-bottom: 5px; }
.win95-app-menu.notepad-edit-menu > menuitem { padding: 0; min-height: 17px; }
.win95-app-menu > menuitem {
    min-height: 17px;
    padding: 0 16px 0 @GUTTER@px;
}
.win95-app-menu.has-checks > menuitem { padding-left: 0; }
.win95-app-menu > separator {
    min-height: 1px;
    margin: 4px 1px;
    background: #808080;
}
.win95-app-menubar > menuitem:hover, .win95-app-menu > menuitem:hover {
    background: #000080;
    color: white;
}
.win95-app-menu > menuitem:disabled {
    color: #808080;
}
.win95-app-menu > menuitem > check:not(:checked) { opacity: 0; }
cursor-handle { opacity: 0; }
""".replace(b"@GUTTER@", str(POPUP_GUTTER-1).encode()) + SCROLLBAR_STYLE


_menu_sound_hook=None

def menu_sound_emission(_hint,_count,values):
    item=values[0]
    if getattr(item,'win95_sound_hook',False) and item.get_sensitive():
        from win95lx.sound import notify
        notify(item,'MenuCommand')
    return True

def style_menus(widget):
    global _menu_sound_hook
    if isinstance(widget,Gtk.Menu) and not getattr(widget,'win95_sound_hook',False):
        from win95lx.sound import notify
        widget.connect('map',lambda menu:notify(menu,'MenuPopup'))
        widget.win95_sound_hook=True
    if isinstance(widget,Gtk.MenuItem) and not isinstance(widget,Gtk.SeparatorMenuItem) and widget.get_submenu() is None:
        widget.win95_sound_hook=True
        if _menu_sound_hook is None:
            _menu_sound_hook=GObject.signal_add_emission_hook(GObject.signal_lookup('activate',Gtk.MenuItem),0,menu_sound_emission)
    if isinstance(widget, Gtk.MenuBar):
        widget.get_style_context().add_class('win95-app-menubar')
    elif isinstance(widget, Gtk.Menu):
        context = widget.get_style_context()
        context.add_class('win95-app-menu')
        if any(isinstance(child, Gtk.CheckMenuItem) for child in widget.get_children()):
            context.add_class('has-checks')
        widget.set_reserve_toggle_size(False)
        if not getattr(widget,'win95_palette_installed',False):
            anchor=getattr(widget,'win95_palette_owner',None) or widget.get_attach_widget()
            owner=anchor.get_toplevel() if anchor is not None else None
            while isinstance(owner,Gtk.Window) and not hasattr(owner,'display_preferences'):
                owner=owner.get_transient_for()
            if owner is not None and hasattr(owner,'display_preferences'):
                from win95lx.control_panel.display_preferences import install_palette_filter
                install_palette_filter(widget,lambda owner=owner:owner.display_preferences.palette)
                widget.win95_palette_installed=True
        if context.has_class('notepad-file-menu'):
            widget.set_size_request(NOTEPAD_FILE_WIDTH, -1)
        elif context.has_class('notepad-help-menu'):
            widget.set_size_request(NOTEPAD_HELP_WIDTH, -1)
    if isinstance(widget, Gtk.MenuItem) and widget.get_submenu():
        style_menus(widget.get_submenu())
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            style_menus(child)


def install_menu_style(screen):
    provider = Gtk.CssProvider()
    provider.load_from_data(MENU_STYLE)
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)


def build(kind, shell):
    if kind=='accessibility':
        from win95lx.apps.accessibility import AccessibilityWindow
        return AccessibilityWindow(shell)
    if kind=='fonts':
        from win95lx.apps.fonts import FontsWindow
        return FontsWindow(shell)
    if kind=='multimedia':
        from win95lx.apps.multimedia import MultimediaWindow
        return MultimediaWindow(shell)
    if kind=='sounds':
        from win95lx.apps.sounds import SoundsWindow
        return SoundsWindow(shell)
    if kind=='regional':
        from win95lx.apps.regional import RegionalWindow
        return RegionalWindow(shell)
    if kind=='datetime':
        from win95lx.apps.datetime import DateTimeWindow
        return DateTimeWindow(shell)
    if kind=='system':
        from win95lx.apps.system import SystemWindow
        return SystemWindow(shell)
    if kind=='keyboard':
        from win95lx.apps.keyboard import KeyboardWindow
        return KeyboardWindow(shell)
    if kind=='mouse':
        from win95lx.apps.mouse import MouseWindow
        return MouseWindow(shell)
    module, factory = APPLICATIONS[kind]
    create = getattr(import_module(f'win95lx.apps.{module}'), factory)
    window = create(shell.assets) if kind == 'wordpad' else create()
    focus = window.get_focus()
    window.set_transient_for(shell)
    window.dialog_assets = shell.assets
    from win95lx.control_panel.display_preferences import install_palette_filter
    install_palette_filter(window,lambda: shell.display_preferences.palette)
    window.set_decorated(False)
    window.connect('realize', lambda widget: widget.get_window().set_cursor(shell.cursor_for('arrow')))
    if kind in ('notepad', 'wordpad'):
        def set_editor_cursor(view):
            text_window = view.get_window(Gtk.TextWindowType.TEXT)
            if text_window:
                text_window.set_cursor(shell.cursor_for('beam'))
        window.view.connect_after('realize', set_editor_cursor)
    icon_path = shell.assets / f'accessory-{kind}.png'
    if icon_path.exists():
        window.set_icon(GdkPixbuf.Pixbuf.new_from_file(str(icon_path)))

    content = window.get_child()
    style_menus(content)
    window.remove(content)
    frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    style = Gtk.CssProvider()
    style.load_from_data(b"""
        box.win95-accessory-frame {
            background: #c0c0c0;
            border: 1px solid;
            border-color: #fff #000 #000 #fff;
            box-shadow: inset -1px -1px #808080;
            padding: 3px;
        }
    """)
    context = frame.get_style_context()
    context.add_class('win95-accessory-frame')
    context.add_provider(style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window.add(frame)

    caption = Gtk.DrawingArea()
    caption.set_size_request(-1, 18)
    caption.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                       Gdk.EventMask.BUTTON_MOTION_MASK)
    frame.pack_start(caption, False, False, 0)
    frame.pack_start(content, True, True, 0)
    if focus:
        window.set_focus(focus)
    drag = None
    restored_bounds = None
    operation = None
    grabbed = False

    def toggle_maximize():
        nonlocal restored_bounds
        if not window.get_resizable():
            return
        if restored_bounds is None:
            restored_bounds = (*window.get_position(), *window.get_size())
            window.move(0, 0)
            window.resize(shell.width, shell.height - 28)
        else:
            x, y, width, height = restored_bounds
            restored_bounds = None
            window.move(x, y)
            window.resize(width, height)
        caption.queue_draw()

    def minimize():
        window.hide()
        shell.get_window().focus(Gdk.CURRENT_TIME)

    def apply_bounds(bounds):
        x, y, width, height = bounds
        window.move(x, y)
        if operation is not None and operation.command == 'size':
            window.resize(width, height)

    def end_operation(cancel=False):
        nonlocal operation, grabbed
        if cancel:
            apply_bounds(operation.original)
        operation = None
        if grabbed:
            window.get_display().get_default_seat().ungrab()
            grabbed = False

    def begin_operation(command):
        nonlocal operation, grabbed
        seat = window.get_display().get_default_seat()
        pointer = seat.get_pointer().get_position()
        operation = WindowOperation.begin(command, (*window.get_position(), *window.get_size()),
                                          (pointer.x, pointer.y))
        window.get_window().focus(Gdk.CURRENT_TIME)
        grabbed = seat.grab(window.get_window(), Gdk.SeatCapabilities.POINTER, False,
                            shell.cursor_for('move' if command == 'move' else 'size1'),
                            None, None, None) == Gdk.GrabStatus.SUCCESS
        return GLib.SOURCE_REMOVE

    def system_command(_item, command):
        if command in ('restore', 'maximize'):
            toggle_maximize()
        elif command == 'minimize':
            minimize()
        elif command == 'close':
            window.close()
        else:
            GLib.idle_add(begin_operation, command)

    system_menu = Gtk.Menu()
    system_menu.attach_to_widget(window, None)
    system_items = []
    for command, label, mnemonic in COMMANDS:
        if command == 'close':
            system_menu.append(Gtk.SeparatorMenuItem())
        offset = label.casefold().index(mnemonic)
        item = Gtk.MenuItem.new_with_mnemonic(label[:offset]+'_'+label[offset:])
        if command == 'close':
            item.get_child().set_markup_with_mnemonic('<b>_Close</b>')
            item.get_child().set_accel(Gdk.KEY_F4, Gdk.ModifierType.MOD1_MASK)
        item.connect('activate', system_command, command)
        system_items.append(item)
        system_menu.append(item)
    style_menus(system_menu)
    system_menu.set_size_request(MENU_WIDTH, -1)

    def show_system_menu(event=None):
        profile = options(resizable=window.get_resizable(), minimizable=True,
                          maximized=restored_bounds is not None)
        for item, (_, _, _, enabled) in zip(system_items, profile):
            item.set_sensitive(enabled)
        system_menu.show_all()
        anchor = Gdk.Rectangle()
        anchor.x, anchor.y, anchor.width, anchor.height = 4, 22, 1, 1
        system_menu.popup_at_rect(window.get_window(), anchor, Gdk.Gravity.NORTH_WEST,
                                  Gdk.Gravity.NORTH_WEST, event)
        system_menu.select_first(False)

    def draw(area, context):
        width = area.get_allocated_width()
        painter = Painter(context, shell.font)
        painter.fill(0, 0, width, 18, NAVY if window.is_active() else SHADOW)
        icon = shell.small_images.get(kind)
        if icon:
            painter.image(icon, 2, 1)
        context.save()
        title_x = 18 if kind == 'winmine' else 20
        context.rectangle(title_x, 0, width - 54 - title_x, 18)
        context.clip()
        painter.text(window.get_title() or '', title_x, 2, LIGHT, bold=True)
        context.restore()
        painter.caption_button('minimize', width - 52, 2)
        painter.caption_button('restore' if restored_bounds else 'maximize', width - 36, 2)
        if not window.get_resizable():
            painter.fill(width - 33, 6, 9, 9, SHADOW)
            painter.fill(width - 32, 8, 7, 6, FACE)
        painter.caption_button('close', width - 18, 2)

    def press(area, event):
        nonlocal drag
        if event.button != 1:
            return False
        width = area.get_allocated_width()
        if event.x >= width - 18:
            window.close()
        elif event.x >= width - 36:
            toggle_maximize()
        elif event.x >= width - 52:
            minimize()
        elif event.x < 19:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                window.close()
            else:
                show_system_menu(event)
        elif event.type == Gdk.EventType._2BUTTON_PRESS:
            drag = None
            toggle_maximize()
        elif restored_bounds is None:
            x, y = window.get_position()
            drag = event.x_root - x, event.y_root - y
        return True

    def move(_area, event):
        if drag is None:
            return False
        x = max(0, min(int(event.x_root - drag[0]), shell.width - 80))
        y = max(0, min(int(event.y_root - drag[1]), shell.height - 50))
        window.move(x, y)
        return True

    def release(_area, _event):
        nonlocal drag
        drag = None
        return True

    def key(_controller, keyval, _keycode, state):
        name = Gdk.keyval_name(keyval)
        if operation is not None:
            if name in ARROWS:
                apply_bounds(operation.step(*ARROWS[name], (shell.width,shell.height)))
            elif name in ('Escape', 'Return', 'KP_Enter'):
                end_operation(cancel=name == 'Escape')
            return True
        if keyval == Gdk.KEY_space and state & Gdk.ModifierType.MOD1_MASK:
            show_system_menu(Gtk.get_current_event())
            return True
        if keyval == Gdk.KEY_F4 and state & Gdk.ModifierType.MOD1_MASK:
            window.close()
            return True
        return False

    def operation_motion(_widget, event):
        if operation is None:
            return False
        apply_bounds(operation.motion(event.x_root, event.y_root, (shell.width,shell.height)))
        return True

    def operation_press(_widget, event):
        if operation is not None and event.button == 1:
            end_operation()
            return True
        return False

    caption.connect('draw', draw)
    caption.connect('button-press-event', press)
    caption.connect('motion-notify-event', move)
    caption.connect('button-release-event', release)
    controller = Gtk.EventControllerKey.new(window)
    controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
    controller.connect('key-pressed', key)
    window.win95_key_controller = controller
    window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
    window.connect('button-press-event', operation_press)
    window.connect('motion-notify-event', operation_motion)
    window.connect('destroy', lambda *_: end_operation() if operation is not None else None)
    window.connect('notify::title', lambda *_: caption.queue_draw())
    window.connect('notify::is-active', lambda *_: caption.queue_draw())
    if kind in REFERENCE_BOUNDS:
        x, y, width, height = REFERENCE_BOUNDS[kind]
        window.set_default_size(width, height)
    else:
        x, y = 100, 65
    window.move(x, y)
    return window
