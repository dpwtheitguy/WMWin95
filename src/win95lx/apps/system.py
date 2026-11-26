"""Native System Properties with actual guest inventory and performance facts."""
from gi.repository import Gtk,Gdk
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.system_info import inventory,system_summary
from win95lx.shell.widgets import FACE,BLACK,LIGHT,NAVY,SHADOW
from win95lx.shell.scrollbar import VerticalScrollbar

class SystemWindow(PropertySheet):
    title='System Properties';asset_prefix='system';size=(408,448)
    tabs=('general','devices','hardware-profiles','performance')
    tab_rects=((10,29,49,22),(59,29,92,22),(151,29,95,22),(246,29,73,22))
    buttons=((245,415,75,23),(326,415,75,23))
    def __init__(self,shell):
        super().__init__(shell);self.summary=system_summary();self.devices=inventory();self.selection=0;self.scroll=0;self.by_connection=False
    def rows(self):
        rows=[('Computer',None)]
        if self.by_connection:return rows+[(device.name,device) for device in self.devices]
        category=None
        for device in self.devices:
            if device.category!=category:category=device.category;rows.append((category,None))
            rows.append((device.name,device))
        return rows
    def draw_content(self,p):
        info=self.summary
        if self.tab==0:
            p.fill(210,66,189,241,FACE)
            for label,x,y,bold in (('System:',214,70,False),('Win95LX',232,88,False),('Compatibility Edition',232,106,False),
                                   ('Registered to:',214,150,False),('Current user',232,169,False),('Computer:',214,252,False),
                                   (info['architecture'],232,270,False),(f"{info['memory']/1048576:.1f}MB RAM",232,288,False)):
                p.text(label,x,y,bold=bold)
        elif self.tab==1:
            rows=self.rows();self.selection=min(self.selection,len(rows)-1);self.scroll=min(self.scroll,max(0,len(rows)-16))
            p.fill(30,92,332,262,LIGHT)
            for row,(label,device) in enumerate(rows[self.scroll:self.scroll+16]):
                index=self.scroll+row;y=93+row*16;x=49 if device is None else 68
                image=(30,92,16,16) if index==0 else (49,140,16,16) if device is None else (68,189,16,16)
                self.sprite(p,image,x-19,y)
                width=min(360-x,p.font.width(label)+2)
                if index==self.selection:p.fill(x,y,width,13,NAVY)
                p.cr.save();p.cr.rectangle(x,y,360-x,15);p.cr.clip();p.text(label,x,y,LIGHT if index==self.selection else BLACK);p.cr.restore()
                self.hit((30,y,332,16),('device',index))
            VerticalScrollbar(264,max(0,len(rows)-16)).draw(p,363,91,self.scroll)
            self.hit((363,91,16,16),('scroll',-1));self.hit((363,339,16,16),('scroll',1))
            self.hit((363,107,16,110),('scroll',-16));self.hit((363,217,16,122),('scroll',16))
            self.hit((28,65,142,20),('group',False));self.hit((179,65,175,20),('group',True))
            if self.by_connection:
                self.sprite(p,(179,68,13,13),28,68);self.sprite(p,(28,68,13,13),179,68)
            self.button(p,'Properties',(28,365,84,23),('properties',),rows[self.selection][1] is not None,'Select a device to view its properties.')
            self.hit((118,365,84,23),('refresh',))
            self.button(p,'Remove',(208,365,84,23),('remove',),False,'Device removal: administrative device-policy integration is unfinished. Windows drivers cannot be installed or removed here; Refresh and device properties use the actual devices.')
            self.button(p,'Print...',(298,365,83,23),('print',),False,'Printing the device inventory: the native CUPS print-dialog integration is unfinished.')
        elif self.tab==2:
            p.fill(30,157,348,90,LIGHT);p.fill(30,157,348,13,NAVY);p.text('Current Configuration',32,157,LIGHT)
            reason='Hardware boot profiles: integration with the boot loader and device policy is unfinished. The current session remains active; no profile choice is simulated.'
            for label,rect in (('Copy...',(28,269,114,23)),('Rename...',(147,269,114,23)),('Delete',(267,269,114,23))):self.button(p,label,rect,('profile',label),False,reason)
        else:
            p.fill(153,84,229,122,FACE)
            memory=info['memory'];available=round(info['available']*100/max(1,memory))
            values=(f'{memory/1048576:.1f}MB of RAM',f'{available}% available','Native file system',f"{info['swap']/1048576:.1f}MB swap",'Not enabled','No PCMCIA sockets detected')
            for index,value in enumerate(values):p.text(value,154,85+21*index)
            p.fill(42,237,326,53,LIGHT);p.text('Memory and disk statistics are live.',44,239)
            self.button(p,'Details...',(295,295,75,23),('details',))
            for label,rect,key in (('File System...',(40,355,105,23),'filesystem'),('Graphics...',(151,355,105,23),'graphics'),('Virtual Memory...',(262,355,108,23),'memory')):
                self.button(p,label,rect,(key,))
    def action(self,action):
        kind=action[0]
        if kind=='device':self.selection=action[1]
        elif kind=='scroll':self.scroll=max(0,min(max(0,len(self.rows())-16),self.scroll+action[1]))
        elif kind=='group':self.by_connection=action[1];self.scroll=self.selection=0
        elif kind=='refresh':self.devices=inventory();self.summary=system_summary()
        elif kind=='properties':
            device=self.rows()[self.selection][1]
            if device:self.message('Device Properties',device.name+'\nType: '+device.category+'\nStatus: '+device.status+'\nDriver: '+(device.driver or 'Managed by the system')+'\nLocation: '+device.path)
        elif kind in ('details','filesystem','graphics','memory'):
            self.summary=system_summary();info=self.summary
            if kind=='filesystem':text=f"Capacity: {info['disk_total']:,} bytes\nFree space: {info['disk_free']:,} bytes\nFile-system cache is managed automatically."
            elif kind=='graphics':text=f'{self.get_screen().get_width()} by {self.get_screen().get_height()} pixels\nDisplay settings can be changed in Display Properties.'
            else:text=f"Physical memory: {info['memory']:,} bytes\nAvailable: {info['available']:,} bytes\nSwap space: {info['swap']:,} bytes\nFree swap: {info['swap_free']:,} bytes\nVirtual memory is managed automatically."
            self.message({'filesystem':'File System Properties','graphics':'Graphics Properties','memory':'Virtual Memory'}.get(kind,'Performance Details'),text)
        else:return super().action(action)
        self.area.queue_draw()
    def message(self,title,text):
        from win95lx.apps.dialogs import message_box
        message_box(self,title,text,Gtk.MessageType.INFO)
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        if self.tab==1 and name in ('Up','Down','Home','End','Page_Up','Page_Down'):
            count=len(self.rows());self.selection=0 if name=='Home' else count-1 if name=='End' else max(0,min(count-1,self.selection+{'Up':-1,'Down':1,'Page_Up':-16,'Page_Down':16}[name]));self.scroll=max(0,min(self.scroll,self.selection));self.scroll=max(self.scroll,self.selection-15);self.area.queue_draw();return True
        return super().key(window,event)
