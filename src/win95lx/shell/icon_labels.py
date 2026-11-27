"""Icon-cell word wrapping that preserves native glyph sizes."""
def wrap_label(text,font,width=70,max_lines=2):
    lines=[];remaining=text.strip()
    while remaining and len(lines)<max_lines:
        if font.width(remaining)<=width:lines.append(remaining);break
        end=0
        while end<len(remaining) and font.width(remaining[:end+1])<=width:end+=1
        if len(lines)==max_lines-1:
            while end and font.width(remaining[:end]+'...')>width:end-=1
            lines.append(remaining[:end].rstrip()+'...');break
        space=remaining.rfind(' ',0,end+1)
        if space>0:end=space
        if end<=0:end=1
        lines.append(remaining[:end].rstrip());remaining=remaining[end:].lstrip()
    return tuple(lines or ('',))


def icon_label_metrics(text,font,center_x,top,*,width=70,max_lines=2):
    """Native icon-label geometry:13px lines, a shared multiline highlight.

    `top` is the text-cell origin, not the first ink row (glyph ink is lower).
    Original desktop32px icons use top=icon_y+36 and center=icon_x+16.
    Pass max_lines=None for the measured Classic unlimited desktop profile.
    """
    lines=wrap_label(text,font,width,max(1,len(text)) if max_lines is None else max_lines);longest=max(font.width(line)for line in lines)
    origins=tuple((center_x-font.width(line)//2,top+13*i)for i,line in enumerate(lines))
    # Even-width strings are centered with integer division in the same way
    # as the native label union. The rectangle adds two pixels on each side.
    rectangle=(center_x-longest//2-2,top,longest+4,13*len(lines)+2)
    return {'lines':lines,'origins':origins,'rect':rectangle}


# Measured profiles, not a user-facing preset switch. Classic4.00 shows every
# wrapped line; IE4 truncates unselected labels and expands selected labels.
DESKTOP_LABEL_PROFILES={'classic':{'normal_lines':None,'selected_lines':None},'ie4':{'normal_lines':2,'selected_lines':None}}


def focus_color_for(background):
    """Win95 standard VGA palette-index inversion, proven on five colors.

    This is not RGB inversion. Unknown/non-VGA palette entries require a
    separately measured override; never pretend this models True Color.
    """
    from win95lx.control_panel.display_preferences import VGA
    try:return VGA[VGA.index(tuple(background))^15]
    except (ValueError,TypeError)as error:raise ValueError('Focus inversion requires a standard VGA color or an explicit override.')from error


def draw_icon_label(p,text,center_x,top,*,width=70,max_lines='profile',selected=False,focused=False,active=True,desktop=False,focus_color=None,desktop_color=(0,128,128),text_color=None,profile='ie4'):
    """Paint measured classic icon text without altering icon compositing.

    Desktop profile: system-color opaque label union; inactive
    desktop selection is hidden. Standard256-color VGA focus uses palette-index XOR15 (not RGB XOR).
    desktop_color describes the system desktop color, not a sampled wallpaper
    pixel. Silver desktop text is black; teal/red/black text is white, as
    independently measured. Other text/palette profiles need explicit overrides.
    Explorer's inactive-selection behavior is not certified by this helper.
    """
    from win95lx.shell.widgets import NAVY,LIGHT,BLACK
    selected=bool(selected and(active or not desktop));focused=bool(focused and active)
    if max_lines=='profile':
        settings=DESKTOP_LABEL_PROFILES[profile];max_lines=settings['selected_lines'if selected else'normal_lines']if desktop else 2
    result=icon_label_metrics(text,p.font,center_x,top,width=width,max_lines=max_lines)
    x,y,w,h=result['rect']
    if selected:p.fill(x,y,w,h,NAVY)
    elif desktop:p.fill(x,y,w,h,desktop_color)
    if focused:
        color=focus_color if focus_color is not None else focus_color_for(NAVY if selected else desktop_color)if desktop or selected else BLACK
        p.fill(x,y,w,1,color);p.fill(x,y+h-1,w,1,color);p.fill(x,y,1,h,color);p.fill(x+w-1,y,1,h,color)
    color=LIGHT if selected else text_color if text_color is not None else BLACK if not desktop or tuple(desktop_color)==(192,192,192) else LIGHT
    for line,(left,top)in zip(result['lines'],result['origins']):p.text(line,left,top,color)
    return result
