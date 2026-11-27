"""Shared classic controls drawn on integer pixels with original bitmap glyphs."""
import cairo
from functools import lru_cache
FACE=(192,192,192);LIGHT=(255,255,255);SHADOW=(128,128,128);BLACK=(0,0,0);NAVY=(0,0,128);TEAL=(0,128,128)
@lru_cache(maxsize=8)
def drag_mask(width,height):
    stride=cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8,width)
    pixels=bytearray(stride*height)
    for y in range(height):
        for x in range(width):
            pixels[y*stride+x]=255 if (x+y)%2==0 else 0
    return cairo.ImageSurface.create_for_data(pixels,cairo.FORMAT_A8,width,height,stride)


class Painter:
    def __init__(self,cr,font):self.cr=cr;self.font=font;cr.set_antialias(cairo.ANTIALIAS_NONE)
    def fill(self,x,y,w,h,color):
        self.cr.set_source_rgb(*(v/255 for v in color));self.cr.rectangle(int(x),int(y),int(w),int(h));self.cr.fill()
    def selected_image(self,image,x,y):
        import sys
        self.image(image,x,y)
        width,height=image.get_width(),image.get_height()
        stride=cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8,width)
        mask=bytearray(stride*height);data=image.get_data();source_stride=image.get_stride()
        for yy in range(height):
            for xx in range(width):
                alpha=255 if image.get_format()==cairo.FORMAT_RGB24 else data[yy*source_stride+xx*4+(3 if sys.byteorder=='little' else 0)]
                if (xx+yy)%2==0:mask[yy*stride+xx]=alpha if isinstance(alpha,int) else alpha[0]
        surface=cairo.ImageSurface.create_for_data(mask,cairo.FORMAT_A8,width,height,stride)
        self.cr.save();self.cr.set_source_rgb(0,0,.5);self.cr.mask_surface(surface,x,y);self.cr.restore()

    def text(self,text,x,y,color=BLACK,bold=False):
        self.cr.set_source_rgb(*(v/255 for v in color))
        for char in text:
            width,points=self.font.glyph(char)
            for xx,yy in points:self.cr.rectangle(int(x+xx),int(y+yy),2 if bold else 1,1)
            x+=width+int(bold)
        self.cr.fill()
    def menu_text(self,label,x,y,color=BLACK,mnemonic=None):
        self.text(label,x,y,color)
        if mnemonic is not None and mnemonic != '':
            index=mnemonic if isinstance(mnemonic,int) else label.casefold().find(mnemonic.casefold())
            if 0<=index<len(label):
                self.fill(x+self.font.width(label[:index]),y+12,self.font.width(label[index]),1,color)

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
            self.fill(x+5, y+2, 6, 6, BLACK)
            self.fill(x+6, y+4, 4, 3, FACE)
            self.fill(x+3, y+5, 6, 6, BLACK)
            self.fill(x+4, y+7, 4, 3, FACE)
        else:
            for row, offset in enumerate((0, 1, 2, 3, 2, 1, 0)):
                self.fill(x+4+offset, y+3+row, 2, 1, BLACK)
                self.fill(x+10-offset, y+3+row, 2, 1, BLACK)

    def button(self,label,x,y,w,h,pressed=False,default=False):
        if default:self.fill(x-1,y-1,w+2,h+2,BLACK)
        self.bevel(x,y,w,h,pressed);tx=x+(w-self.font.width(label))//2+int(pressed);self.text(label,tx,y+(h-self.font.height)//2+int(pressed))
    def toolbar_band_edges(self,width,height,raised_width,top_extent=None,bottom_extent=None):
        if top_extent is not None and top_extent<width:
            self.fill(top_extent,0,width-top_extent,1,FACE)
        if bottom_extent is not None and bottom_extent<width:
            self.fill(bottom_extent,height-1,width-bottom_extent,1,FACE)
        self.fill(raised_width-2,1,1,height-2,SHADOW)
        self.fill(raised_width-1,1,1,height-2,LIGHT)

    def drag_image(self,surface,x,y):
        self.cr.save()
        self.cr.set_source_surface(surface,int(x),int(y))
        self.cr.mask_surface(drag_mask(surface.get_width(),surface.get_height()),int(x),int(y))
        self.cr.restore()

    def image(self,surface,x,y):self.cr.set_source_surface(surface,int(x),int(y));self.cr.paint()
