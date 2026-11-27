"""Geometry and input state for a classic drop-down list ComboBox."""

from dataclasses import dataclass


@dataclass
class ComboBox:
    choices: tuple[str, ...]
    value: int = 0
    focused: bool = False
    expanded: bool = False

    height = 21
    row_height = 13

    def open(self):
        self.focused = self.expanded = True

    def step(self, direction):
        self.value = min(len(self.choices)-1, max(0, self.value+direction)) if self.choices else 0

    def row_at(self, x, y, width):
        offset = y-self.height-1
        if 0 <= x < width and 0 <= offset < len(self.choices)*self.row_height:
            return int(offset//self.row_height)
        return None

    def draw_list(self, p, x, y, width):
        from win95lx.shell.widgets import BLACK, LIGHT, NAVY

        if width<=0:return
        y += self.height
        height=len(self.choices)*self.row_height+2
        p.cr.save()
        p.cr.rectangle(x,y,width,height);p.cr.clip()
        p.fill(x,y,width,height,BLACK)
        # The control owns its border and its text client separately. A Cairo
        # popup shares the shell canvas, so GTK child-window clipping cannot
        # protect adjacent controls from a long label.
        p.cr.rectangle(x+1,y+1,max(0,width-2),max(0,height-2));p.cr.clip()
        for index, label in enumerate(self.choices):
            top = y+1+index*self.row_height
            selected = index == self.value
            p.fill(x+1, top, max(0,width-2), self.row_height, (255,255,0) if selected else LIGHT)
            if selected:
                p.fill(x+2, top+1, max(0,width-4), self.row_height-2, NAVY)
            p.text(label, x+3, top, LIGHT if selected else BLACK)
        p.cr.restore()
