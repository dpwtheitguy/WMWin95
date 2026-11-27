"""Measured Windows 95 BUTTON painting, contained within the HWND rectangle."""
from dataclasses import dataclass
from win95lx.shell.widgets import FACE,LIGHT,SHADOW,BLACK


def parse_label(label):
    """Resolve Win32 '&' mnemonics and literal '&&' without measuring markers."""
    if not isinstance(label,str):raise TypeError('A button label must be text.')
    visible=[];mnemonic=None;index=0
    while index<len(label):
        char=label[index]
        if char=='&':
            if index+1<len(label) and label[index+1]=='&':visible.append('&');index+=2;continue
            if index+1<len(label):
                if mnemonic is None:mnemonic=len(visible)
                index+=1;continue
            index+=1;continue
        visible.append(char);index+=1
    return ''.join(visible),mnemonic

@dataclass(frozen=True)
class ButtonMetrics:
    rect:tuple
    text:str
    text_origin:tuple
    mnemonic:int|None
    focus_rect:tuple|None
    default:bool
    focused:bool
    pressed:bool
    enabled:bool
    def contains(self,x,y):
        left,top,width,height=self.rect
        return left<=x<left+width and top<=y<top+height


def metrics(font,label,rect,*,default=False,focused=False,pressed=False,enabled=True,mnemonic=None):
    if len(rect)!=4 or any(type(value) is not int for value in rect) or rect[2]<4 or rect[3]<4:raise ValueError('Button bounds must be integer pixels and at least 4 by 4.')
    if any(type(value) is not bool for value in (default,focused,pressed,enabled)):raise TypeError('Button states must be boolean.')
    text,index=parse_label(label)
    if mnemonic is not None:
        index=mnemonic if type(mnemonic) is int else text.casefold().find(str(mnemonic).casefold())
        if not 0<=index<len(text):index=None
    pressed=pressed and enabled;focused=focused and enabled
    x,y,w,h=rect
    # Win95's 23px MS Sans Serif button puts the 13px cell at y+4,
    # one pixel above ordinary integer-box centering. Press adds (1,1).
    origin=(x+(w-font.width(text))//2+int(pressed),y+(h-font.height)//2-1+int(pressed))
    inset=4 if default else 3
    focus=(x+inset,y+inset,w-2*inset,h-2*inset) if focused and w>2*inset and h>2*inset else None
    return ButtonMetrics(tuple(rect),text,origin,index,focus,default,focused,pressed,enabled)


def resolve_default(designated,focused,enabled):
    """Return one enabled command ID, or None when no default is available.

    `enabled` maps command IDs to enabled flags. Focus on a non-command control
    restores the designated command; disabled commands cannot acquire default.
    """
    if focused in enabled and enabled[focused]:return focused
    if designated in enabled and enabled[designated]:return designated
    return None


def outline(p,rect,color):
    x,y,w,h=rect
    if w<=0 or h<=0:return
    p.fill(x,y,w,1,color);p.fill(x,y+h-1,w,1,color);p.fill(x,y,1,h,color);p.fill(x+w-1,y,1,h,color)


def draw_command_button(p,label,rect,*,default=False,focused=False,pressed=False,enabled=True,mnemonic=None):
    """Draw native states; return measured text/focus/hit geometry.

    `rect` is the actual HWND/hit rectangle. A default outline is painted
    INSIDE it. The painter's original bitmap font must match the reference.
    """
    state=metrics(p.font,label,rect,default=default,focused=focused,pressed=pressed,enabled=enabled,mnemonic=mnemonic)
    x,y,w,h=state.rect;p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip();p.fill(x,y,w,h,FACE)
    if state.pressed:
        if state.default:
            outline(p,(x,y,w,h),BLACK);outline(p,(x+1,y+1,w-2,h-2),SHADOW)
        else:
            p.fill(x,y,w-1,1,BLACK);p.fill(x,y,1,h-1,BLACK)
            p.fill(x+w-1,y,1,h,LIGHT);p.fill(x,y+h-1,w,1,LIGHT)
            p.fill(x+1,y+1,w-3,1,SHADOW);p.fill(x+1,y+1,1,h-3,SHADOW)
    else:
        inset=int(state.default)
        if inset:outline(p,(x,y,w,h),BLACK)
        bx,by,bw,bh=x+inset,y+inset,w-2*inset,h-2*inset
        p.fill(bx,by,bw,1,LIGHT);p.fill(bx,by,1,bh,LIGHT)
        p.fill(bx+bw-1,by,1,bh,BLACK);p.fill(bx,by+bh-1,bw,1,BLACK)
        if bw>2 and bh>2:
            p.fill(bx+bw-2,by+1,1,bh-2,SHADOW);p.fill(bx+1,by+bh-2,bw-2,1,SHADOW)
    tx,ty=state.text_origin
    def text(color,dx=0,dy=0):
        p.text(state.text,tx+dx,ty+dy,color)
        if state.mnemonic is not None:
            index=state.mnemonic;p.fill(tx+dx+p.font.width(state.text[:index]),ty+dy+12,p.font.width(state.text[index]),1,color)
    if state.enabled:text(BLACK)
    else:text(LIGHT,1,1);text(SHADOW)
    if state.focus_rect:outline(p,state.focus_rect,BLACK)
    p.cr.restore();return state
