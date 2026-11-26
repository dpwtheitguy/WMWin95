"""Private original TrueType glyphs staged at measured native pixel sizes."""
import json

class RasterFont:
    def __init__(self,path):
        data=json.loads(path.read_text());self.height=data['height'];self.glyphs=data['glyphs']
    def glyph(self,char):return self.glyphs.get(char,self.glyphs.get('?',(7,[])))
    def width(self,text,bold=False):return sum(self.glyph(c)[0]+bool(bold) for c in text)
