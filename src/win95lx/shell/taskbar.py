"""Task buttons measured from the Windows 95 reference at native pixels."""

START_X = 66
MAX_BUTTON_WIDTH = 160
BUTTON_HEIGHT = 22
BUTTON_GAP = 3


def title_that_fits(font, title, width, bold):
    if font.width(title, bold) <= width:
        return title
    suffix = '...'
    if font.width(suffix, bold) > width:
        return ''
    while title and font.width(title + suffix, bold) > width:
        title = title[:-1]
    return title + suffix


def draw_task_button(p, title, icon, x, y, width, active):
    from win95lx.shell.widgets import BLACK, FACE, LIGHT, SHADOW

    if active:
        p.fill(x, y, width, BUTTON_HEIGHT, LIGHT)
        p.fill(x, y, width-1, 1, BLACK)
        p.fill(x, y, 1, BUTTON_HEIGHT-1, BLACK)
        p.fill(x+1, y+1, width-3, 1, SHADOW)
        p.fill(x+1, y+1, 1, BUTTON_HEIGHT-3, SHADOW)
        p.fill(x+width-2, y+1, 1, BUTTON_HEIGHT-2, FACE)
        p.fill(x+1, y+BUTTON_HEIGHT-2, width-2, 1, FACE)
    else:
        p.bevel(x, y, width, BUTTON_HEIGHT)

    p.cr.save()
    p.cr.rectangle(x+2, y+2, width-4, BUTTON_HEIGHT-4)
    p.cr.clip()
    text_x = x+4
    if icon and width >= 24:
        if icon.get_width() == 16 and icon.get_height() == 16:
            p.image(icon, x+3, y+3)
        else:
            p.cr.save()
            p.cr.translate(x+3, y+3)
            p.cr.scale(16/icon.get_width(), 16/icon.get_height())
            p.image(icon, 0, 0)
            p.cr.restore()
        text_x = x+21
    label = title_that_fits(p.font, title, x+width-4-text_x, active)
    p.text(label, text_x, y+3, bold=active)
    p.cr.restore()


def button_width(count, right_edge):
    available = right_edge-START_X
    if not count or available < 1:
        return 0
    return min(MAX_BUTTON_WIDTH, max(1, (available+BUTTON_GAP)//count-BUTTON_GAP))
