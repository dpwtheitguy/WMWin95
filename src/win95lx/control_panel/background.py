"""Display Properties Background tab and its native list scrollbar."""

from win95lx.control_panel.wallpaper import paint_wallpaper, paint_pattern
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.shell.widgets import BLACK, LIGHT, NAVY, SHADOW, TEAL

LIST_X, LIST_Y = 36, 287
LIST_WIDTH, LIST_HEIGHT = 229, 92
ROW_HEIGHT = 17
VISIBLE_ROWS = LIST_HEIGHT // ROW_HEIGHT
SCROLL_X = 265
ARROW = 16
TRACK_Y = LIST_Y + ARROW
TRACK_HEIGHT = LIST_HEIGHT - 2 * ARROW
THUMB_HEIGHT = 21
MODE_X, MODE_Y, MODE_WIDTH = 294, 361, 75
MODES = ('center', 'tile')


def scrollbar(maximum):
    return VerticalScrollbar(LIST_HEIGHT, maximum, ARROW, THUMB_HEIGHT)


def copy_rect(p, image, x, y, rect):
    left, top, width, height = rect
    p.cr.save()
    p.cr.rectangle(x, y, width, height)
    p.cr.clip()
    p.image(image, x-left, y-top)
    p.cr.restore()


def draw(p, win, shell):
    x, y = win.x, win.y
    frame = shell.background_frame
    selected = shell.pending_wallpaper
    mode = shell.pending_wallpaper_mode
    dirty = ((selected,mode,shell.pending_pattern_rows) !=
             (shell.wallpaper.name,shell.wallpaper.mode,shell.wallpaper.pattern_rows))

    if frame:
        p.image(frame, x, y)
        if win is not shell.state.active:
            p.fill(x+3, y+3, 361, 18, SHADOW)
            p.text(win.title, x+5, y+5, LIGHT, bold=True)
    else:
        p.bevel(x+9, y+49, 386, 360)
        p.bevel(x+110, y+60, 184, 146)
        p.bevel(x+24, y+249, 356, 145)
        p.text('Wallpaper', x+32, y+242)
        p.text('Select an HTML Document or a picture:', x+33, y+266)
        p.bevel(x+34, y+285, 248, 96, True)
        p.text('Display:', x+294, y+344)
        p.button('Background', x+9, y+29, 74, 21, pressed=True)
        p.button('Settings', x+270, y+30, 50, 20)

    if selected != '(None)' or frame is None or any(shell.pending_pattern_rows):
        p.fill(x+125, y+76, 153, 113, TEAL)
        p.cr.save()
        p.cr.translate(x+125, y+76)
        p.cr.scale(153/shell.width, 113/shell.height)
        paint_pattern(p,shell.pending_pattern_rows,0,0,shell.width,shell.height)
        paint_wallpaper(p, shell.wallpaper_surface(selected, shell.display_preferences.palette), mode, 0, 0,
                        shell.width, shell.height)
        p.cr.restore()

    static_list = frame is not None and shell.wallpaper_scroll == 0 and selected == '(None)'
    draw_list(p, shell, x, y, frame, static_list)
    draw_scrollbar(p, shell, win, frame, static_list)

    combo = shell.wallpaper_combo
    if selected != '(None)':
        cx, cy = x+MODE_X, y+MODE_Y
        if shell.background_enabled:
            copy_rect(p, shell.background_enabled, cx, cy, (MODE_X, MODE_Y, MODE_WIDTH, combo.height))
        else:
            p.bevel(cx, cy, MODE_WIDTH, combo.height, sunken=True)
            p.button('▼', cx+57, cy+2, 16, 17)
        focused = combo.focused and not combo.expanded and win is shell.state.active
        p.fill(cx+3, cy+2, 54, 17, LIGHT)
        if focused:
            p.fill(cx+3, cy+3, 53, 15, BLACK)
            p.fill(cx+4, cy+4, 51, 13, NAVY)
        p.text(mode.title(), cx+4, cy+4, LIGHT if focused else BLACK)
        shell.hit(cx, cy, MODE_WIDTH, combo.height, ('wallpaper-mode',))
    elif not frame:
        p.button('Center', x+MODE_X, y+MODE_Y, MODE_WIDTH, combo.height)

    for label, bx, by, width, height, action in (
        ('Browse...', 294, 285, 75, 23, ('wallpaper-help', 'Browse')),
        ('Pattern...', 294, 314, 75, 23, ('wallpaper-help', 'Pattern')),
        ('OK', 158, 415, 75, 23, ('wallpaper-apply', win, True)),
        ('Cancel', 239, 415, 75, 23, ('close', win)),
        ('Apply', 320, 415, 75, 23, ('wallpaper-apply', win, False)),
    ):
        if frame is None:
            p.button(label, x+bx, y+by, width, height, default=label == 'OK')
        if label != 'Apply' or dirty:
            shell.hit(x+bx, y+by, width, height, action)
    if dirty and shell.background_enabled:
        copy_rect(p, shell.background_enabled, x+320, y+415, (320,415,75,23))
    if shell.wallpaper_error:
        p.text('Could not save wallpaper.', x+27, y+394)
    shell.hit(x+270, y+30, 50, 20, ('display-tab', 'settings'))
    shell.hit(x+364, y+3, 17, 16, ('wallpaper-help', 'Background'))
    shell.hit(x+382, y+3, 17, 16, ('close', win))
    if selected != '(None)' and combo.expanded and win is shell.state.active:
        combo.draw_list(p, x+MODE_X, y+MODE_Y, MODE_WIDTH)


def draw_list(p, shell, x, y, frame, static):
    if not static:
        p.fill(x+LIST_X, y+LIST_Y, LIST_WIDTH, LIST_HEIGHT, LIGHT)
        p.cr.save()
        p.cr.rectangle(x+LIST_X, y+LIST_Y, LIST_WIDTH, LIST_HEIGHT)
        p.cr.clip()
    names = shell.wallpaper.names
    for index, name in enumerate(names[shell.wallpaper_scroll:shell.wallpaper_scroll+VISIBLE_ROWS+1]):
        yy = y+LIST_Y+ROW_HEIGHT*index
        if not static:
            active = name == shell.pending_wallpaper
            if frame:
                row = 287 if name == '(None)' else 304
                copy_rect(p, frame, x+37, yy, (37,row,17,17))
            if active:
                p.fill(x+55, yy+1, p.font.width(name)+4, 15, NAVY)
            p.text(name, x+57, yy+1, LIGHT if active else BLACK)
        height = min(ROW_HEIGHT, y+LIST_Y+LIST_HEIGHT-yy)
        shell.hit(x+LIST_X, yy, LIST_WIDTH, height, ('wallpaper-select', name))
    if not static:
        p.cr.restore()


def draw_scrollbar(p, shell, win, frame, static):
    x, y = win.x+SCROLL_X, win.y
    control = scrollbar(shell.wallpaper_max_scroll)
    thumb = LIST_Y + control.thumb_top(shell.wallpaper_scroll)
    if not static:
        def artwork(painter, dest_x, dest_y, part):
            source_y, height = {'up':(287,ARROW), 'thumb':(303,THUMB_HEIGHT),
                                'down':(363,ARROW)}[part]
            copy_rect(painter, frame, dest_x, dest_y, (265,source_y,ARROW,height))
        control.draw(p, x, y+LIST_Y, shell.wallpaper_scroll, artwork if frame else None)
    shell.hit(x, y+LIST_Y, ARROW, ARROW, ('wallpaper-scroll', -1))
    shell.hit(x, y+TRACK_Y, ARROW, thumb-TRACK_Y, ('wallpaper-scroll', -VISIBLE_ROWS))
    shell.hit(x, y+thumb, ARROW, THUMB_HEIGHT, ('wallpaper-thumb', win, y+thumb))
    shell.hit(x, y+thumb+THUMB_HEIGHT, ARROW, TRACK_Y+TRACK_HEIGHT-thumb-THUMB_HEIGHT,
              ('wallpaper-scroll', VISIBLE_ROWS))
    shell.hit(x, y+TRACK_Y+TRACK_HEIGHT, ARROW, ARROW, ('wallpaper-scroll', 1))
