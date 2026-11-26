"""Drop zones measured from the Windows 95 large-icon folder view."""

def folder_drop_rect(x, y, label_width, desktop=False):
    width = min(76 if desktop else 75,max(49,label_width+8))
    center = x+(37 if desktop else 32)
    return center-width//2,y-1,width,54


def contains(rect,x,y):
    left,top,width,height = rect
    return left <= x < left+width and top <= y < top+height


def drag_started(dx,dy):
    return max(abs(dx),abs(dy))>=4
