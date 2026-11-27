"""Measured virtual-object right-drop menu; other context profiles are unchanged."""
from win95lx.shell.start_context import StartContext
from win95lx.shell.widgets import BLACK,LIGHT,NAVY,SHADOW

class NamespaceDropContext(StartContext):
    @classmethod
    def at_drop(cls,x,y,rows,width,screen_width,screen_height):
        return cls(x-width,y,rows,width,screen_width-1,screen_height-1)

    def draw(self,p):
        p.window_frame(self.x,self.y,self.width,self.height)
        p.fill(self.x+self.width-1,self.y,1,1,BLACK);p.fill(self.x,self.y+self.height-1,1,1,BLACK)
        for index,(y,row) in enumerate(self.entries()):
            if row is None:
                p.fill(self.x+3,y+3,self.width-6,1,SHADOW);p.fill(self.x+3,y+4,self.width-6,1,LIGHT);continue
            label,action=row;selected=self.selected==y;color=LIGHT if selected else BLACK
            if selected:p.fill(self.x+3,y,self.width-6,17,NAVY)
            p.text(label,self.x+24,y+1,color,bold=index==0)
            if index==0:
                p.fill(self.x+25+p.font.width('Create ',True),y+13,p.font.width('S',True)+1,1,color)


def drag_image_origin(viewport,point,start,pointer,initial_scroll,*,image_x=16):
    """Screen image origin preserving the exact source pointer grab offset."""
    return (round(viewport[0]+point[0]-initial_scroll[0]+image_x+pointer[0]-start[0]),
            round(viewport[1]+point[1]-initial_scroll[1]+pointer[1]-start[1]))
