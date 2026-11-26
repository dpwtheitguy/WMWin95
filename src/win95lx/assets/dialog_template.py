"""Bounded reader for standard Win32 DLGTEMPLATE resources (not executables)."""
import struct

def parse_dialog(data):
    offset=0
    def take(fmt):
        nonlocal offset
        size=struct.calcsize(fmt)
        if offset+size>len(data):raise ValueError('Truncated dialog template')
        result=struct.unpack_from(fmt,data,offset);offset+=size
        return result[0] if len(result)==1 else result
    def text():
        nonlocal offset
        first=take('<H')
        if first==0:return ''
        if first==65535:return take('<H')
        words=[first]
        for _ in range(4096):
            value=take('<H')
            if not value:break
            words.append(value)
        else:raise ValueError('Dialog string exceeds limit')
        try:return struct.pack('<'+'H'*len(words),*words).decode('utf-16le')
        except UnicodeError as error:raise ValueError('Invalid dialog string') from error
    if len(data)<18:raise ValueError('Truncated dialog header')
    if data[2:4]==b'\xff\xff':raise ValueError('Extended dialog templates are not supported')
    style,extended,count,x,y,width,height=take('<IIHhhhh')
    if count>2048:raise ValueError('Too many dialog controls')
    result={'style':style,'extended_style':extended,'rect':[x,y,width,height],
            'menu':text(),'class':text(),'caption':text(),'controls':[]}
    if style&64:result['font']={'points':take('<H'),'face':text()}
    for _ in range(count):
        offset=(offset+3)&~3
        style,extended,x,y,w,h,identifier=take('<IIhhhhH')
        control={'style':style,'extended_style':extended,'rect':[x,y,w,h],'id':identifier,'class':text(),'text':text()}
        size=take('<H')
        if offset+size>len(data):raise ValueError('Truncated dialog creation data')
        offset+=size;result['controls'].append(control)
    return result

def pixel_rect(rect,*,origin,base):
    """Convert using a measured page client origin and its actual font base.

    Property pages vary by CPL and shell version; painted group-box borders
    cannot establish the HWND origin. GetWindowRect/native probe is preferred.
    """
    def muldiv(value,numerator,denominator):return (value*numerator+denominator//2)//denominator
    x,y,w,h=rect
    return (origin[0]+muldiv(x,base[0],4),origin[1]+muldiv(y,base[1],8),muldiv(w,base[0],4),muldiv(h,base[1],8))
