"""Selection and caret model for shared single-line classic edit controls."""
from dataclasses import dataclass

@dataclass
class TextEntry:
    text: str=''
    cursor: int=0
    anchor: int=0

    @property
    def selection(self):return sorted((self.cursor,self.anchor))

    def select_all(self):self.anchor=0;self.cursor=len(self.text)

    def replace(self,value):
        left,right=self.selection
        self.text=self.text[:left]+value+self.text[right:]
        self.cursor=left+len(value);self.anchor=self.cursor

    def key(self,name,text='',ctrl=False,shift=False):
        if ctrl and name.lower()=='a':self.select_all();return True
        if name in ('Left','Right','Home','End'):
            left,right=self.selection
            if name=='Home':cursor=0
            elif name=='End':cursor=len(self.text)
            elif left!=right and not shift:cursor=left if name=='Left' else right
            else:cursor=max(0,min(len(self.text),self.cursor+(-1 if name=='Left' else 1)))
            self.cursor=cursor
            if not shift:self.anchor=cursor
            return True
        if name in ('BackSpace','Delete'):
            if self.cursor==self.anchor:
                if name=='BackSpace':self.anchor=max(0,self.cursor-1)
                else:self.anchor=min(len(self.text),self.cursor+1)
            self.replace('');return True
        if not ctrl and text and text.isprintable():self.replace(text);return True
        return False
