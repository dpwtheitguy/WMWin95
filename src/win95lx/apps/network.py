"""Native-sized Network property sheets with pending, service-owned IPv4 edits.

Not registered until isolated service and visual acceptance checks are complete.
"""
from dataclasses import replace
from threading import Thread
from gi.repository import Gtk,Gdk,GLib
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.network_preferences import NetworkManager,NetworkController,NetworkState,IPv4Entry,NetworkError
from win95lx.shell.widgets import FACE,BLACK,LIGHT,NAVY,SHADOW

SHARING='File and printer sharing is unavailable: the sharing service and its configuration integration are not installed.'
COMPONENTS='Installing Windows network components is unavailable. Network devices and connection profiles are managed by the running system.'

def draw_network_radio(p,raw_label,rect,images,*,checked=False,enabled=True,focused=False,pressed=False):
    """Measured single-line Win95 USER radio profile; not a generic OCX skin.

    Native scope: standard colors,96dpi,13px MS Sans Serif,16px HWND height.
    Source-state glyphs include normal/pressed/disabled checked and unchecked.
    """
    from win95lx.shell.command_button import parse_label
    label,mnemonic=parse_label(raw_label);x,y,w,h=rect
    if h!=16 or p.font.height!=13:raise ValueError('Unsupported Network radio font/height profile')
    state='disabled' if not enabled else 'pressed' if pressed else 'normal'
    key=state+('-checked' if checked else '-unchecked')
    p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip();p.fill(x,y,w,h,FACE)
    p.image(images[key],x,y+1)
    if not enabled:p.menu_text(label,x+19,y+2,LIGHT,mnemonic)
    p.menu_text(label,x+18,y+1,BLACK if enabled else SHADOW,mnemonic)
    focus=(x+17,y,p.font.width(label)+2,h) if focused and enabled else None
    if focus:
        fx,fy,fw,fh=focus
        p.fill(fx,fy,fw,1,BLACK);p.fill(fx,fy+fh-1,fw,1,BLACK);p.fill(fx,fy,1,fh,BLACK);p.fill(fx+fw-1,fy,1,fh,BLACK)
    p.cr.restore()
    return {'label':label,'mnemonic':mnemonic,'text_origin':(x+18,y+1),'focus_rect':focus,'rect':tuple(rect)}


class NetworkWindow(PropertySheet):
    title='Network';asset_prefix='network';size=(366,460)
    tabs=('configuration','identification','access')
    tab_rects=((10,29,76,22),(86,29,71,22),(157,29,82,22))
    buttons=((202,427,75,23),(283,427,75,23))
    def __init__(self,shell,backend=None):
        self.loading=self.busy=True;self.closed=False;self.load_error=None;self.list_top=0;self.list_drag=None;self.selected=0
        super().__init__(shell)
        if backend is None:
            from win95lx.control_panel.network_service import installed_backend
            backend=installed_backend()
        self.controller=NetworkController(backend,NetworkState('localhost'))
        self.connect('destroy',lambda *_:setattr(self,'closed',True))
        self.connect('delete-event',lambda *_:self.busy and not self.loading)
        self.area.connect('scroll-event',self.scroll_connections)
        def load():
            state=error=None
            try:state=self.controller.backend.preferences().validate()
            except Exception as caught:error=caught
            GLib.idle_add(self.loaded,state,error)
        Thread(target=load,daemon=True,name='win95lx-network-inventory').start()
    def loaded(self,state,error):
        if self.closed:return False
        self.loading=self.busy=False
        if error:self.load_error=str(error)if isinstance(error,(NetworkError,ValueError))else'The network connections could not be identified. Close this window and try again.'
        else:
            self.controller.applied=self.controller.pending=state
            if state.connections:self.focus_action=('connection',0)
        self.area.queue_draw();return False
    def button(self,p,label,rect,action,enabled=True,reason=None):
        if action==('ok',):enabled=enabled and not self.busy and not self.load_error
        if action==('cancel',):enabled=enabled and not(self.busy and not self.loading)
        return super().button(p,label,rect,action,enabled,reason)
    def draw_content(self,p):
        if self.loading or self.load_error:
            from win95lx.shell.icon_labels import wrap_label
            p.fill(13,53,340,366,FACE)
            text=self.load_error or'Please wait while your network connections are identified.'
            for index,line in enumerate(wrap_label(text,p.font,300,20)):p.text(line,30,88+index*15)
            return
        state=self.controller.pending
        if self.tab==0:
            p.fill(30,88,306,100,LIGHT)
            rows=state.connections
            self.list_top=max(0,min(max(0,len(rows)-5),self.list_top))
            row_width=290 if len(rows)>5 else 306
            p.cr.save();p.cr.rectangle(30,88,row_width,100);p.cr.clip()
            for offset,c in enumerate(rows[self.list_top:self.list_top+5]):
                index=self.list_top+offset;y=89+offset*18;selected=index==self.selected
                if selected:p.fill(30,y,306,17,NAVY)
                p.text('TCP/IP -> '+c.name,48,y+2,LIGHT if selected else BLACK)
                self.hit((30,y,row_width,17),('connection',index))
            p.cr.restore()
            if len(rows)>5:
                from win95lx.shell.scrollbar import VerticalScrollbar
                bar=VerticalScrollbar.for_page(100,len(rows)-5,5);bar.draw(p,320,88,self.list_top)
                top=bar.thumb_top(self.list_top)
                for rect,action in (((320,88,16,16),('connections-scroll',-1)),((320,172,16,16),('connections-scroll',1)),((320,88+top,16,bar.thumb),('connections-thumb',bar))):self.hit(rect,action)
                if top>16:self.hit((320,104,16,top-16),('connections-scroll',-5))
                end=top+bar.thumb
                if end<84:self.hit((320,88+end,16,84-end),('connections-scroll',5))
            self.button(p,'Add...',(28,210,99,23),('add',),False,COMPONENTS)
            self.button(p,'Remove',(133,210,100,23),('remove',),False,'Connection-profile removal has not been implemented in this applet.')
            self.button(p,'Properties',(239,210,100,23),('properties',),bool(rows),'No network connection is available.')
            p.fill(30,261,289,16,FACE);p.text('Current network connection',32,262,SHADOW);p.fill(323,265,8,5,FACE)
            self.disabled.append(((28,259,310,21),'Network logon clients require the file sharing service; changing the login method is not available.'))
            self.button(p,'File and Print Sharing...',(28,292,147,26),('sharing',),False,SHARING)
            p.fill(30,345,306,53,FACE)
            if rows:
                c=rows[min(self.selected,len(rows)-1)]
                p.cr.save();p.cr.rectangle(30,345,306,53);p.cr.clip()
                for n,text in enumerate(('TCP/IP network connection',c.name,'Connected' if c.active else 'Not connected')):p.text(text,39,348+15*n)
                p.cr.restore()
        elif self.tab==1:
            # Keep native captions and framing; replace source machine values.
            self.disabled.extend([((28,142,310,115),'Computer-name changes are temporarily unavailable until the stable guest identity runtime is deployed.'),((28,220,310,84),SHARING)])
            for x,y,w,h,text in ((115,149,152,23,state.hostname),(115,189,152,23,state.workgroup),(115,230,218,23,state.description)):
                p.fill(x+2,y+2,w-4,h-4,FACE);p.text(text,x+4,y+5,SHADOW)
        else:
            p.fill(28,83,303,278,FACE)
            for n,line in enumerate(('File and printer sharing is unavailable.','The sharing service and its configuration','integration are not installed.')):p.text(line,30,88+n*15,SHADOW)
            self.disabled.append(((28,83,303,278),SHARING))
    def help(self):
        from win95lx.apps.dialogs import message_box
        message_box(self,self.title,'Select a TCP/IP connection and choose Properties. Changes are pending until you choose OK. Cancel discards pending changes.\n\n'+COMPONENTS+'\n\n'+SHARING,Gtk.MessageType.INFO)
    def action(self,action):
        kind=action[0]
        if self.load_error and kind not in('cancel','help','tab'):return
        if self.busy:
            if self.loading and kind=='cancel':return super().action(action)
            return
        if kind=='connection':self.selected=action[1]
        elif kind=='connections-scroll':self.list_top=max(0,min(max(0,len(self.controller.pending.connections)-5),self.list_top+action[1]))
        elif kind=='connections-thumb':self.list_drag=(action[1],action[1].thumb_top(self.list_top),self.get_display().get_default_seat().get_pointer().get_position().y)
        elif kind=='properties':
            rows=self.controller.pending.connections
            if rows:TCPIPWindow(self,rows[min(self.selected,len(rows)-1)]).show_all()
        elif kind=='ok':
            self.busy=True;self.area.set_sensitive(False)
            def worker():
                error=None
                try:self.controller.apply()
                except Exception as caught:error=caught if isinstance(caught,(OSError,ValueError,RuntimeError))else NetworkError('The network settings could not be applied. Reopen Network to check the current settings.')
                GLib.idle_add(self.finished,error)
            Thread(target=worker,daemon=True).start();return
        else:return super().action(action)
        self.area.queue_draw()
    def finished(self,error):
        if self.closed:return False
        self.busy=False;self.area.set_sensitive(True)
        if error:self.error(error)
        else:self.destroy()
        return False
    def focus_order(self):
        order=super().focus_order()
        order=[a for a in order if a[0]not in('connection','connections-scroll','connections-thumb')]
        if self.tab==0 and self.controller.pending.connections and not self.loading:order.insert(0,('connection',self.selected))
        return order
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)or''
        if self.busy:
            if event.state&Gdk.ModifierType.CONTROL_MASK and name=='Escape':return super().key(window,event)
            if self.loading and name in('Escape','F1'):return super().key(window,event)
            return True
        rows=self.controller.pending.connections
        if self.tab==0 and rows and self.focus_action and self.focus_action[0]=='connection' and name in('Up','Down','Home','End','Page_Up','Page_Down'):
            self.selected=0 if name=='Home'else len(rows)-1 if name=='End'else max(0,min(len(rows)-1,self.selected+{'Up':-1,'Down':1,'Page_Up':-5,'Page_Down':5}[name]))
            self.list_top=max(0,min(max(0,len(rows)-5),min(self.list_top,self.selected)if self.selected<self.list_top else max(self.list_top,self.selected-4)))
            self.focus_action=('connection',self.selected);self.area.queue_draw();return True
        return super().key(window,event)
    def scroll_connections(self,area,event):
        if not self.busy and self.tab==0 and 30<=event.x<336 and 88<=event.y<188:
            self.action(('connections-scroll',-1 if event.direction==Gdk.ScrollDirection.UP else 1));return True
        return False
    def press(self,area,event):
        if event.button==1 and not self.busy:
            for rect,action in reversed(self.hits):
                if action[0].startswith('connections-')and self.contains(rect,event.x,event.y):
                    self.focus_action=('connection',self.selected)
                    if action[0]=='connections-thumb':self.list_drag=(action[1],action[1].thumb_top(self.list_top),event.y_root)
                    else:self.action(action)
                    return True
        return super().press(area,event)
    def motion(self,area,event):
        if self.list_drag:
            bar,top,origin=self.list_drag;self.list_top=bar.value_at(top+event.y_root-origin);self.area.queue_draw();return True
        return super().motion(area,event)
    def release(self,area,event):
        if self.list_drag:self.list_drag=None;self.pressed=None;self.area.queue_draw();return True
        return super().release(area,event)

class TCPIPWindow(PropertySheet):
    title='TCP/IP Properties';asset_prefix='network-tcpip';size=(356,437)
    tabs=('bindings','advanced','netbios','dns','gateway','wins','ip')
    buttons=((191,404,75,23),(272,404,75,23))
    tab_rects=()
    def __init__(self,parent,connection):
        self.parent=parent;self.connection=connection
        super().__init__(parent.shell);self.set_transient_for(parent);self.set_modal(True);self.tab=6
        from win95lx.shell.text_entry import TextEntry
        self.pending=connection.ipv4;self.dns_selection=0;self.search_selection=0;self.text_entries={'host':TextEntry(text=self.pending.dhcp_hostname),'domain':TextEntry(),'suffix':TextEntry()};self.entries={'address':IPv4Entry(self.pending.address),'netmask':IPv4Entry(self.pending.netmask),'gateway':IPv4Entry(self.pending.gateway),'dns':IPv4Entry()}
        from win95lx.assets.bitmap import BitmapFont
        self.ip_font=BitmapFont((self.assets/'network-ip-system.fnt').read_bytes())
        import cairo
        self.radio_images={state:cairo.ImageSurface.create_from_png(str(self.assets/f'network-radio-{state}.png')) for state in ('normal-unchecked','normal-checked','pressed-unchecked','pressed-checked','disabled-unchecked','disabled-checked')}
        self.focus_action=None
    def radio(self,p,label,rect,action,checked,enabled=True):
        geometry=draw_network_radio(p,label,rect,self.radio_images,checked=checked,enabled=enabled,
            focused=self.caption_active and self.focus_action==action,
            pressed=self.pressed==action and self.press_inside)
        if enabled:
            self.hit(rect,action)
            if geometry['mnemonic'] is not None:self.command_mnemonics[geometry['label'][geometry['mnemonic']].casefold()]=action
    def ip_entry(self,p,name,rect,enabled=True):
        x,y,w,h=rect;p.bevel(x,y,w,h,True);p.fill(x+2,y+2,w-4,h-4,LIGHT if enabled else FACE)
        from win95lx.shell.widgets import Painter
        text_painter=Painter(p.cr,self.ip_font)
        editor=self.entries[name]
        for i,field in enumerate(editor.fields):
            left=x+2+i*33
            if enabled:self.hit((left,y+2,29,h-4),('ip',name,i))
            text_painter.text(field.text,left+max(0,(29-self.ip_font.width(field.text))//2),y+2,BLACK if enabled else SHADOW)
            if i<3:text_painter.text('.',left+29,y+2,BLACK if enabled else SHADOW)
            if enabled and self.focus_action==('ip',name,i):
                a,b=field.selection
                tx=left+max(0,(29-self.ip_font.width(field.text))//2)
                if a!=b:
                    p.fill(tx,y+2,self.ip_font.width(field.text),17,NAVY);text_painter.text(field.text,tx,y+2,LIGHT)
                else:p.fill(tx+self.ip_font.width(field.text[:field.cursor]),y+2,1,17,BLACK)
    def draw_content(self,p):
        # Source two-row tabs rotate their selected row to the bottom.
        row_a=(('Bindings',0),('Advanced',1),('NetBIOS',2));row_b=(('DNS Configuration',3),('Gateway',4),('WINS Configuration',5),('IP Address',6))
        for row,y in ((row_a,48 if self.tab<3 else 29),(row_b,29 if self.tab<3 else 48)):
            geometry=((11,106),(117,118),(235,110)) if len(row)==3 else ((11,103),(114,57),(171,108),(279,66))
            for (label,index),(x,width) in zip(row,geometry):self.hit((x,y,width,21),('tab',index))
        if self.tab==6:
            manual=self.pending.method=='manual'
            self.radio(p,'&Obtain an IP address automatically',(36,173,248,16),('method','auto'),not manual)
            self.radio(p,'&Specify an IP address:',(36,197,125,16),('method','manual'),manual)
            for name,label,y in (('address','IP Address:',232),('netmask','Subnet Mask:',267)):
                p.fill(57,y,80,20,FACE);p.text(label,58,y+1,BLACK if manual else SHADOW);self.ip_entry(p,name,(141,y,135,21),manual)
        elif self.tab==4:
            self.ip_entry(p,'gateway',(37,191,135,21))
            self.button(p,'Add',(187,191,75,23),('gateway-add',))
            p.fill(45,258,127,69,LIGHT)
            if self.pending.gateway:p.text(self.pending.gateway,47,259)
            self.button(p,'Remove',(187,256,75,23),('gateway-remove',),bool(self.pending.gateway),'No gateway is installed.')
        elif self.tab==3:
            enabled=self.pending.manual_dns
            self.radio(p,'D&isable DNS',(36,85,87,16),('dns-mode',False),not enabled)
            self.radio(p,'&Enable DNS',(36,111,78,16),('dns-mode',True),enabled)
            for label,x,y,w in (('Host:',36,144,27),('DNS Server Search Order',36,180,126),('Domain Suffix Search Order',37,301,132)):
                p.fill(x,y,w,15,FACE)
                if not enabled:p.text(label,x+1,y+1,LIGHT)
                p.text(label,x,y,BLACK if enabled else SHADOW)
            # Native Win16 page clips the bottom list at its y=394 boundary.
            p.cr.save();p.cr.rectangle(13,69,330,325);p.cr.clip()
            for name,rect in (('host',(66,141,90,23)),('domain',(229,141,90,23)),('suffix',(51,323,135,23))):
                self.text_entry(p,name,rect,enabled and name!='domain')
                if name=='domain':self.disabled.append((rect,'The separate primary DNS suffix is not implemented; DNS search domains can be edited below.'))
            self.ip_entry(p,'dns',(51,201,135,23),enabled)
            for name,y,values,index in (('dns',230,self.pending.dns,self.dns_selection),('search',352,self.pending.search,self.search_selection)):
                p.fill(53,y+2,131,53,LIGHT if enabled else FACE)
                for n,value in enumerate(values[:3]):
                    yy=y+2+n*16;selected=n==index
                    if selected and enabled:p.fill(53,yy,131,16,NAVY)
                    p.text(value,55,yy+1,LIGHT if selected and enabled else BLACK if enabled else SHADOW)
                    if enabled and yy<394:self.hit((53,yy,131,min(16,394-yy)),('list',name,n))
                self.button(p,'Add',(208,y-29,75,23),(name+'-add',),enabled,'Enable DNS to enter manual server and search settings.')
                self.button(p,'Remove',(208,y,75,23),(name+'-remove',),enabled and bool(values),'Select an installed server or search domain.')
            p.cr.restore()
        else:
            p.fill(28,82,303,307,FACE)
            text={'bindings':('Network client bindings are unavailable.','The file sharing service is not installed.'),'advanced':('Additional TCP/IP options are not implemented.','Existing connection options are preserved.'),'netbios':('NetBIOS configuration is unavailable.','The file sharing service is not installed.'),'wins':('WINS configuration is unavailable.','The file sharing service is not installed.')}[self.tabs[self.tab]]
            for n,line in enumerate(text):p.text(line,32,90+17*n,SHADOW)
            self.disabled.append(((28,82,303,307),' '.join(text)))
    def text_entry(self,p,name,rect,enabled):
        x,y,w,h=rect;entry=self.text_entries[name];p.bevel(x,y,w,h,True);p.fill(x+2,y+2,w-4,h-4,LIGHT if enabled else FACE)
        p.cr.save();p.cr.rectangle(x+3,y+2,w-6,h-4);p.cr.clip();p.text(entry.text,x+4,y+4,BLACK if enabled else SHADOW);p.cr.restore()
        if enabled:self.hit(rect,('entry',name))
    def action(self,action):
        kind=action[0]
        if kind=='ip':self.entries[action[1]].focus(action[2])
        elif kind=='method':
            self.pending=self.pending.set_method(action[1])
            if action[1]=='auto':self.entries['address']=IPv4Entry();self.entries['netmask']=IPv4Entry()
        elif kind=='dns-mode':
            self.pending=replace(self.pending,manual_dns=action[1],dns=self.pending.dns if action[1] else (),search=self.pending.search if action[1] else ())
        elif kind=='list':
            if action[1]=='dns':self.dns_selection=action[2]
            else:self.search_selection=action[2]
        elif kind in ('dns-add','search-add','dns-remove','search-remove'):
            from win95lx.control_panel.network_preferences import ipv4,domain
            field='dns' if kind.startswith('dns') else 'search';values=list(getattr(self.pending,field))
            try:
                if kind.endswith('add'):
                    value=ipv4(self.entries['dns'].text,'DNS server address') if field=='dns' else domain(self.text_entries['suffix'].text)
                    if not value:raise ValueError('Enter a search domain.')
                    if value not in values:values.append(value)
                    if len(values)>6:raise ValueError('Use at most six servers or search domains.')
                elif values:
                    index=self.dns_selection if field=='dns' else self.search_selection;values.pop(min(index,len(values)-1))
                self.pending=replace(self.pending,**{field:tuple(values)})
            except ValueError as error:self.error(error)
        elif kind=='gateway-add':
            try:
                from win95lx.control_panel.network_preferences import ipv4
                gateway=ipv4(self.entries['gateway'].text,'gateway address')
                if self.pending.gateway and self.pending.gateway!=gateway:raise ValueError('Multiple ordered gateway configuration is not implemented. Remove the current gateway before adding another.')
                self.pending=replace(self.pending,gateway=gateway)
            except ValueError as error:self.error(error)
        elif kind=='gateway-remove':self.pending=replace(self.pending,gateway='');self.entries['gateway']=IPv4Entry()
        elif kind=='ok':
            try:
                pending=replace(self.pending,dhcp_hostname=self.text_entries['host'].text,address=self.entries['address'].text if self.pending.method=='manual' else '',netmask=self.entries['netmask'].text if self.pending.method=='manual' else '').validate()
                self.parent.controller.pending=self.parent.controller.pending.change_connection(self.connection.uuid,ipv4=pending)
            except ValueError as error:self.error(error);return
            self.parent.area.queue_draw();self.destroy();return
        else:return super().action(action)
        self.area.queue_draw()
    def help(self):
        from win95lx.apps.dialogs import message_box
        message_box(self,self.title,'Choose OK to keep these edits pending in Network. Choose OK in Network to apply them. Cancel discards the edits in this dialog. Unavailable controls explain the missing integration when pointed at.',Gtk.MessageType.INFO)
    def entry_click(self,action,event):self.text_entries[action[1]].select_all()
    def motion(self,area,event):
        if self.pressed and self.pressed[0] in ('method','dns-mode'):
            inside=any(action==self.pressed and self.contains(rect,event.x,event.y) for rect,action in self.hits)
            if inside!=self.press_inside:self.press_inside=inside;self.area.queue_draw()
        return super().motion(area,event)
    def focus_order(self):
        order=[]
        for action in super().focus_order():
            if action[0]=='ip':action=('ip',action[1],0)
            if action not in order:order.append(action)
        return order
    def focus_changed(self):
        if self.focus_action and self.focus_action[0]=='ip':self.entries[self.focus_action[1]].focus(0)
        elif self.focus_action and self.focus_action[0]=='entry':self.text_entries[self.focus_action[1]].select_all()
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK)
        if event.state&Gdk.ModifierType.MOD1_MASK:return super().key(window,event)
        if self.focus_action and self.focus_action[0] in ('method','dns-mode') and name in ('Left','Right','Up','Down'):
            kind=self.focus_action[0];value=('manual' if self.focus_action[1]=='auto' else 'auto') if kind=='method' else not self.focus_action[1]
            self.focus_action=(kind,value);self.action(self.focus_action);return True
        if self.focus_action and self.focus_action[0]=='ip':
            editor=self.entries[self.focus_action[1]]
            if name in ('Tab','ISO_Left_Tab'):self.focus_action=('ip',self.focus_action[1],0)
            elif ctrl and name in ('v','V'):
                text=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
                if text is not None:
                    if not editor.key('',text):self.error(ValueError('Enter a valid IP address with four fields, from 0 through 255.'))
                    self.focus_action=('ip',self.focus_action[1],editor.index);self.area.queue_draw()
                return True
        if self.focus_action and self.focus_action[0]=='entry' and name not in ('Tab','ISO_Left_Tab','Return','KP_Enter','Escape','F1'):
            value=Gdk.keyval_to_unicode(event.keyval);ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK);shift=bool(event.state&Gdk.ModifierType.SHIFT_MASK)
            self.text_entries[self.focus_action[1]].key(name,chr(value) if value and not ctrl else '',ctrl,shift);self.area.queue_draw();return True
        if self.focus_action and self.focus_action[0]=='ip' and name not in ('Tab','ISO_Left_Tab','Return','KP_Enter','Escape','F1'):
            editor=self.entries[self.focus_action[1]];ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK);shift=bool(event.state&Gdk.ModifierType.SHIFT_MASK)
            value=Gdk.keyval_to_unicode(event.keyval);text=chr(value) if value and not ctrl else ''
            editor.key(name,text,ctrl,shift);self.focus_action=('ip',self.focus_action[1],editor.index);self.area.queue_draw();return True
        return super().key(window,event)
