"""Read original Windows FNT glyphs and uncompressed icon DIBs without substitution."""
import struct

def word(b,p):return struct.unpack_from('<H',b,p)[0]
def dword(b,p):return struct.unpack_from('<I',b,p)[0]
class BitmapFont:
    def __init__(self,data):
        self.data=data; version=word(data,0)
        if version not in (0x200,0x300) or word(data,66)&1:raise ValueError('Unsupported FNT font')
        if dword(data,2)>len(data):raise ValueError('Truncated FNT')
        self.height=word(data,88); self.ascent=word(data,74); self.points=word(data,68); self.first=data[95]; self.last=data[96]; self.default=self.first+data[97]
        face=dword(data,105); self.face=data[face:].split(b'\0')[0].decode('cp1252'); self.glyphs={}; table=118 if version==0x200 else 148; step=4 if version==0x200 else 6
        for code in range(self.first,self.last+1):
            p=table+(code-self.first)*step; width=word(data,p); offset=word(data,p+2) if step==4 else dword(data,p+2)
            size=((width+7)//8)*self.height
            if offset+size>len(data):raise ValueError('Truncated glyph')
            points=[(x,y) for y in range(self.height) for x in range(width) if data[offset+(x//8)*self.height+y] & (128>>(x%8))]
            self.glyphs[code]=(width,points)
    def glyph(self,char):
        try:code=char.encode('cp1252')[0]
        except UnicodeEncodeError:code=self.default
        return self.glyphs.get(code,self.glyphs[self.default])
    def width(self,text,bold=False):return sum(self.glyph(c)[0]+int(bold) for c in text)

def icon_dib(data):
    if len(data)<40 or dword(data,0)!=40:raise ValueError('Unsupported DIB header')
    w,combined=struct.unpack_from('<ii',data,4); h=abs(combined)//2; bpp=word(data,14)
    if w<=0 or h<=0 or bpp not in (1,4,8,24,32) or dword(data,16):raise ValueError('Unsupported icon DIB')
    colors=(dword(data,32) or 1<<bpp) if bpp<=8 else 0; start=40+colors*4; stride=((w*bpp+31)//32)*4; maskstride=((w+31)//32)*4; maskstart=start+stride*h
    if maskstart+maskstride*h>len(data):raise ValueError('Truncated icon')
    palette=[tuple(data[40+i*4+j] for j in (2,1,0)) for i in range(colors)]; pixels=[]
    for y in range(h):
        row=(h-1-y) if combined>0 else y
        for x in range(w):
            p=start+row*stride
            if bpp<=8:
                byte=data[p+x*bpp//8]; shift=8-bpp-(x*bpp%8); rgb=palette[(byte>>shift)&((1<<bpp)-1)]
            else:rgb=tuple(data[p+x*(bpp//8)+j] for j in (2,1,0))
            transparent=data[maskstart+row*maskstride+x//8]&(128>>(x%8)); pixels.append(rgb+(0 if transparent else 255,))
    return w,h,pixels


def rle4_bitmap(data):
    """Decode a bottom-up 4-bit Windows bitmap resource."""
    header, width, height, planes, depth, compression = struct.unpack_from('<IiiHHI', data)
    if header != 40 or width < 1 or height < 1 or (planes, depth, compression) != (1, 4, 2):
        raise ValueError('Unsupported RLE4 bitmap')
    colors = dword(data, 32) or 16
    palette = [tuple(data[40 + i * 4 + offset] for offset in (2, 1, 0)) + (255,)
               for i in range(colors)]
    pixels = [palette[0]] * (width * height)
    offset = 40 + colors * 4
    x, y = 0, height - 1
    while offset + 2 <= len(data):
        count, value = data[offset:offset + 2]
        offset += 2
        if count:
            run = [value >> 4 if i % 2 == 0 else value & 15 for i in range(count)]
        elif value == 0:
            x, y = 0, y - 1
            continue
        elif value == 1:
            return width, height, pixels
        elif value == 2:
            dx, dy = data[offset:offset + 2]
            offset += 2
            x += dx
            y -= dy
            continue
        else:
            length = (value + 1) // 2
            if offset + length > len(data):
                raise ValueError('Truncated RLE4 literal run')
            run = [data[offset + i // 2] >> 4 if i % 2 == 0 else
                   data[offset + i // 2] & 15 for i in range(value)]
            offset += length + length % 2
        if not 0 <= y < height or x + len(run) > width:
            raise ValueError('RLE4 run outside bitmap')
        start = y * width + x
        pixels[start:start + len(run)] = [palette[index] for index in run]
        x += len(run)
    raise ValueError('Missing RLE4 end marker')
