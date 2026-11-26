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
