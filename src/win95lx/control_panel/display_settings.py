"""Windows 95 Settings layout with shared resolution slider geometry."""

FRAME_SIZE = (404, 448)
SLIDERS = (253, 321)
THUMB = (275, 253, 11, 21)
MIN_CENTER, MAX_CENTER = 280, 322
COMBOS = {'palette': (33, 251), 'font': (33, 319)}
COMBO_WIDTH = 155
FOCUS_ORDER = ('palette', SLIDERS[0], 'font', SLIDERS[1], 'tray', 'advanced')


def slider_center(index, count):
    return MIN_CENTER + round((MAX_CENTER-MIN_CENTER)*index/(count-1))


def slider_index(x, count):
    position = min(MAX_CENTER, max(MIN_CENTER, x))
    return round((position-MIN_CENTER)*(count-1)/(MAX_CENTER-MIN_CENTER))


def draw(p, win, shell):
    from win95lx.control_panel.background import copy_rect
    from win95lx.shell.widgets import BLACK, FACE, LIGHT, SHADOW, TEAL

    x, y = win.x, win.y
    frame = shell.settings_frame
    mode = shell.pending_resolution
    modes = shell.resolution_modes
    index = modes.index(mode)
    changed = mode != shell.applied_resolution or shell.pending_display != shell.display_preferences
    center = slider_center(index, len(modes))
    if frame:
        p.image(frame, x, y)
        if win is not shell.state.active:
            p.fill(x+3, y+3, 398, 17, SHADOW)
            p.text(win.title, x+5, y+4, LIGHT, bold=True)
    else:
        p.bevel(x+9, y+49, 386, 360)
        p.bevel(x+110, y+60, 184, 146)
        p.fill(x+125, y+76, 153, 113, TEAL)
        p.button('Background', x+9, y+29, 72, 21)
        p.button('Settings', x+270, y+29, 52, 21, pressed=True)

    for top, label in zip(SLIDERS, ('Desktop area', 'Screen area')):
        if not frame:
            p.text(label, x+215, y+top-17)
            p.text('Less', x+215, y+top-2)
            p.text('More', x+343, y+top-2)
        if not frame or center != MIN_CENTER:
            track_x, track_width = (275, 11) if frame else (255, 72)
            p.fill(x+track_x, y+top, track_width, 21, FACE)
            for row, color in enumerate((SHADOW, BLACK, FACE, LIGHT), 7):
                p.fill(x+track_x, y+top+row, track_width, 1, color)
            if frame:
                copy_rect(p, frame, x+center-5, y+top, THUMB)
            else:
                p.bevel(x+center-5, y+top, 11, 21)
        if not frame or mode != (800, 600):
            text = f'{mode[0]} by {mode[1]} pixels'
            p.fill(x+213, y+top+25, 162, 17, FACE)
            p.text(text, x+293-p.font.width(text)//2, y+top+26)
        if shell.resolution_focus == top and win is shell.state.active:
            for dot in range(253, 329, 2):
                p.fill(x+dot, y+top-1, 1, 1, BLACK)
                p.fill(x+dot, y+top+21, 1, 1, BLACK)
            for dot in range(-1, 22, 2):
                p.fill(x+253, y+top+dot, 1, 1, BLACK)
                p.fill(x+328, y+top+dot, 1, 1, BLACK)
        shell.hit(x+254, y+top, 74, 21, ('resolution-slider', win, top))
    if changed and shell.settings_apply:
        p.image(shell.settings_apply, x+320, y+415)
    elif not frame or changed:
        p.button('Apply', x+320, y+415, 75, 23)
    if changed:
        shell.hit(x+320, y+415, 75, 23, ('resolution-apply', win, False))
    for label, offset, action in (
        ('OK', 158, ('resolution-apply', win, True)),
        ('Cancel', 239, ('close', win)),
    ):
        if not frame:
            p.button(label, x+offset, y+415, 75, 23)
        shell.hit(x+offset, y+415, 75, 23, action)
    if shell.resolution_error:
        p.fill(x+11, y+394, 380, 14, FACE)
        p.text(shell.resolution_error, x+17, y+394)
    shell.hit(x+9, y+29, 72, 21, ('display-tab', 'background'))
    shell.hit(x+364, y+3, 17, 16, ('resolution-help',))
    shell.hit(x+382, y+3, 17, 16, ('close', win))
    draw_options(p, win, shell)


def draw_options(p, win, shell):
    from win95lx.shell.widgets import BLACK, FACE, LIGHT, NAVY, SHADOW

    x, y = win.x, win.y
    for name, (left, top) in COMBOS.items():
        combo = shell.display_combos[name]
        focused = shell.resolution_focus == name and not combo.expanded
        if not shell.settings_frame:
            p.bevel(x+left, y+top, COMBO_WIDTH, combo.height, True)
            p.button('v', x+left+137, y+top+2, 16, 17)
        if combo.value != (1 if name == 'palette' else 0) or shell.resolution_focus is not None:
            p.fill(x+left+3, y+top+3, 133, 15, NAVY if focused else LIGHT)
            p.text(combo.choices[combo.value], x+left+3, y+top+4, LIGHT if focused else BLACK)
        shell.hit(x+left, y+top, COMBO_WIDTH, combo.height, ('display-combo', name))
    options = shell.pending_display
    if options.palette != 1:
        for column in range(154):
            hue = column*6//154
            base = ((255,0,0),(255,255,0),(0,255,0),(0,255,255),(0,0,255),(255,0,255))
            color = base[hue] if options.palette == 0 else tuple(
                (a*(154-column*6%154)+b*(column*6%154))//154
                for a,b in zip(base[hue], base[(hue+1)%6]))
            p.fill(x+34+column, y+277, 1, 14, color)
    if options.dpi != 96:
        p.fill(x+33, y+347, 159, 15, FACE)
        p.text(f'{options.dpi*100//96}% of normal size ({options.dpi} dpi)', x+33, y+347)
    if options.tray:
        if shell.settings_checked:
            p.image(shell.settings_checked,x+24,y+380)
        else:
            for offset in range(3):
                p.fill(x+27+offset,y+385+offset,1,2,BLACK)
            for offset in range(5):
                p.fill(x+29+offset,y+387-offset,1,2,BLACK)
    if not shell.settings_frame:
        p.text('Show settings icon on task bar', x+41, y+379)
        p.button('Advanced Properties', x+238, y+376, 141, 23)
    if shell.resolution_focus in ('tray', 'advanced'):
        left, top, width = (40,379,151) if shell.resolution_focus == 'tray' else (242,379,133)
        for offset in range(0,width,2):
            p.fill(x+left+offset, y+top, 1, 1, SHADOW)
            p.fill(x+left+offset, y+top+15, 1, 1, SHADOW)
    shell.hit(x+24, y+376, 175, 23, ('display-tray',))
    shell.hit(x+238, y+376, 141, 23, ('display-advanced',))
    for name, (left, top) in COMBOS.items():
        combo = shell.display_combos[name]
        if combo.expanded and win is shell.state.active:
            combo.draw_list(p, x+left, y+top, COMBO_WIDTH)



def draw_confirmation(p, shell, seconds):
    from win95lx.shell.widgets import LIGHT, NAVY

    width, height = 292, 122
    x, y = (shell.width-width)//2, (shell.height-height)//2
    p.window_frame(x, y, width, height)
    p.fill(x+3, y+3, width-6, 18, NAVY)
    p.text('Display Settings', x+7, y+4, LIGHT, bold=True)
    p.text('Do you want to keep these settings?', x+15, y+36)
    p.text(f'The previous mode returns in {seconds} seconds.', x+15, y+55)
    shell.button(p, 'Yes', x+118, y+86, 75, 23, ('resolution-confirm', True))
    p.button('No', x+200, y+86, 75, 23, default=True)
    shell.hit(x+200, y+86, 75, 23, ('resolution-confirm', False))
