"""Classic captions for GTK accessories in the standalone X11 session."""

from importlib import import_module

from gi.repository import Gdk, GdkPixbuf, Gtk

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

MENU_STYLE = b"""
.win95-app-menubar, .win95-app-menu {
    background: #c0c0c0;
    color: black;
    font: 11px "Liberation Sans";
    border-radius: 0;
    box-shadow: none;
    padding: 0;
}
.win95-app-menubar > menuitem {
    padding: 0 6px;
    min-height: 20px;
}
.win95-app-menubar.notepad-menu > menuitem { min-height: 19px; }
.win95-app-menu {
    padding: 1px;
    border: 2px solid;
    border-color: #fff #404040 #404040 #fff;
}
.win95-app-menu > menuitem {
    min-height: 16px;
    padding: 0 8px;
}
.win95-app-menu > separator {
    min-height: 1px;
    margin: 2px 1px;
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
"""


def style_menus(widget):
    if isinstance(widget, Gtk.MenuBar):
        widget.get_style_context().add_class('win95-app-menubar')
    elif isinstance(widget, Gtk.Menu):
        widget.get_style_context().add_class('win95-app-menu')
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
    module, factory = APPLICATIONS[kind]
    create = getattr(import_module(f'win95lx.apps.{module}'), factory)
    window = create(shell.assets) if kind == 'wordpad' else create()
    focus = window.get_focus()
    window.set_transient_for(shell)
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
            window.hide()
            shell.get_window().focus(Gdk.CURRENT_TIME)
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

    def key(_window, event):
        if event.keyval == Gdk.KEY_F4 and event.state & Gdk.ModifierType.MOD1_MASK:
            window.close()
            return True
        return False

    caption.connect('draw', draw)
    caption.connect('button-press-event', press)
    caption.connect('motion-notify-event', move)
    caption.connect('button-release-event', release)
    window.connect('key-press-event', key)
    window.connect('notify::title', lambda *_: caption.queue_draw())
    window.connect('notify::is-active', lambda *_: caption.queue_draw())
    if kind in REFERENCE_BOUNDS:
        x, y, width, height = REFERENCE_BOUNDS[kind]
        window.set_default_size(width, height)
    else:
        x, y = 100, 65
    window.move(x, y)
    return window
