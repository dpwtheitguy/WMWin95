"""Decode BI_RLE8 frames, retaining the previous image for AVI delta frames."""
def decode(data,width,height,previous=None):
    if not 0<width<=4096 or not 0<height<=4096:raise ValueError('Invalid bitmap size.')
    pixels=list(previous) if previous is not None else [0]*(width*height)
    if len(pixels)!=width*height:raise ValueError('Invalid previous frame.')
    x,y,pos=0,height-1,0
    def put(values):
        nonlocal x
        if not 0<=y<height or x+len(values)>width:raise ValueError('RLE pixels exceed bitmap bounds.')
        pixels[y*width+x:y*width+x+len(values)]=values;x+=len(values)
    while pos+2<=len(data):
        count,value=data[pos:pos+2];pos+=2
        if count:put([value]*count)
        elif value==0:x=0;y-=1
        elif value==1:return pixels
        elif value==2:
            if pos+2>len(data):raise ValueError('Truncated RLE delta.')
            dx,dy=data[pos:pos+2];pos+=2;x+=dx;y-=dy
            if not 0<=x<=width or not 0<=y<height:raise ValueError('RLE delta exceeds bitmap bounds.')
        else:
            if pos+value>len(data):raise ValueError('Truncated RLE run.')
            put(data[pos:pos+value]);pos+=value+(value%2)
    raise ValueError('Missing RLE end marker.')
