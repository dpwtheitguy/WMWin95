"""Shared classic controls drawn on integer pixels with original bitmap glyphs."""
import cairo
FACE=(192,192,192);LIGHT=(255,255,255);SHADOW=(128,128,128);BLACK=(0,0,0);NAVY=(0,0,128);TEAL=(0,128,128)
class Painter:
    def __init__(self,cr,font):self.cr=cr;self.font=font;cr.set_antialias(cairo.ANTIALIAS_NONE)
    def fill(self,x,y,w,h,color):
        self.cr.set_source_rgb(*(v/255 for v in color));self.cr.rectangle(int(x),int(y),int(w),int(h));self.cr.fill()
    def text(self,text,x,y,color=BLACK,bold=False):
        self.cr.set_source_rgb(*(v/255 for v in color))
        for char in text:
            width,points=self.font.glyph(char)
            for xx,yy in points:self.cr.rectangle(int(x+xx),int(y+yy),2 if bold else 1,1)
            x+=width+int(bold)
        self.cr.fill()
    def bevel(self,x,y,w,h,sunken=False):
        self.fill(x,y,w,h,FACE)
        a,b=(SHADOW,LIGHT) if sunken else (LIGHT,BLACK)
        self.fill(x,y,w,1,a);self.fill(x,y,1,h,a);self.fill(x+w-1,y,1,h,b);self.fill(x,y+h-1,w,1,b)
        if not sunken:self.fill(x+w-2,y+1,1,h-2,SHADOW);self.fill(x+1,y+h-2,w-2,1,SHADOW)
    def window_frame(self, x, y, width, height):
        self.fill(x, y, width, height, FACE)
        self.fill(x+1, y+1, width-2, 1, LIGHT)
        self.fill(x+1, y+1, 1, height-2, LIGHT)
        self.fill(x+width-2, y+1, 1, height-2, SHADOW)
        self.fill(x+1, y+height-2, width-2, 1, SHADOW)
        self.fill(x+width-1, y+1, 1, height-1, BLACK)
        self.fill(x+1, y+height-1, width-1, 1, BLACK)

    def caption_button(self, symbol, x, y):
        self.bevel(x, y, 16, 14)
        if symbol == 'minimize':
            self.fill(x+4, y+9, 6, 2, BLACK)
        elif symbol == 'maximize':
            self.fill(x+3, y+2, 9, 9, BLACK)
            self.fill(x+4, y+4, 7, 6, FACE)
        elif symbol == 'restore':
            self.fill(x+6, y+2, 7, 7, BLACK)
            self.fill(x+7, y+4, 5, 4, FACE)
            self.fill(x+3, y+5, 7, 7, BLACK)
            self.fill(x+4, y+7, 5, 4, FACE)
        else:
            for row, offset in enumerate((0, 1, 2, 3, 2, 1, 0)):
                self.fill(x+4+offset, y+3+row, 2, 1, BLACK)
                self.fill(x+10-offset, y+3+row, 2, 1, BLACK)

    def button(self,label,x,y,w,h,pressed=False,default=False):
        if default:self.fill(x-1,y-1,w+2,h+2,BLACK)
        self.bevel(x,y,w,h,pressed);tx=x+(w-self.font.width(label))//2+int(pressed);self.text(label,tx,y+(h-self.font.height)//2+int(pressed))
    def image(self,surface,x,y):self.cr.set_source_surface(surface,int(x),int(y));self.cr.paint()
