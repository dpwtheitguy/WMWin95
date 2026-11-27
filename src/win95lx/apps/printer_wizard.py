"""Measured Add Printer wizard with bounded create-only guest service work."""
from dataclasses import replace
import cairo
from gi.repository import Gdk,GLib
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.printer_installation import PrinterWizardState,PrinterError,INSTALLATION_BLOCKER,InstallationDiscovery,PrinterInstallationClient,PartialInstallation
from win95lx.shell.command_button import draw_command_button,resolve_default,parse_label
from win95lx.shell.text_entry import TextEntry
from win95lx.shell.icon_labels import wrap_label
from win95lx.shell.widgets import Painter,FACE,LIGHT,NAVY,BLACK,SHADOW

class PrinterWizardWindow(PropertySheet):
    size=(441,323);title='Add Printer Wizard';tabs=('welcome','driver','port','name','testpage');asset_prefix='printer-wizard';buttons=()
    def __init__(self,shell,discovery=None,client=None,on_installed=None):
        self.client=client or PrinterInstallationClient();self.on_installed=on_installed;self.busy=False;self.installing=False;self.closed=False;self.service_error=None;self.installed=None;self.entry_offsets={};self.list_tops={};self.list_rows={};self.list_rects={};self.list_ensure=set();self.scroll_drag=None;self.discovery=discovery or InstallationDiscovery((),(),(),());self.state=PrinterWizardState();self.endpoint_entry=TextEntry();self.name_entry=TextEntry();self.manufacturer='Generic';self.list_scroll=0
        super().__init__(shell);self.radio_images={state:cairo.ImageSurface.create_from_png(str(self.assets/f'network-radio-{state}.png'))for state in ('normal-unchecked','normal-checked','pressed-unchecked','pressed-checked','disabled-unchecked','disabled-checked')};self.focus_action=('next',)
        self.connect('destroy',self.destroyed);self.area.connect('scroll-event',self.scroll)
        self.connect('delete-event',lambda *_:True if self.installing else False)
        if discovery is None:self.work(self.client.discover,self.discovered)
    def paragraph(self,p,text,x,y,width):
        for line in wrap_label(text,p.font,width,20):p.text(line,x,y);y+=13
    def draw(self,area,cr):
        self.tab=self.state.page;self.hits=[];self.disabled=[];self.button_specs=[];self.command_mnemonics={};self.command_actions=set();p=Painter(cr,self.shell.font);p.image(self.frames[self.tab],0,0)
        # Native wizard HWND has a plain caption without a Close button.
        self.hit((3,3,435,20),('caption',))
        if not self.caption_active:
            p.fill(3,3,414,17,SHADOW);p.text(self.title,5,4,LIGHT,bold=True)
        if self.tab==1:
            p.fill(14,33,414,228,FACE);self.sprite(p,(14,33,32,32),14,33)
            self.paragraph(p,'Select the manufacturer and model of your printer. Choose IPP Everywhere for a compatible network printer.',59,33,369)
            p.menu_text('Manufacturers:',14,105,mnemonic=0);p.menu_text('Printers:',170,105,mnemonic=0)
            manufacturers=sorted({d.manufacturer for d in self.discovery.drivers},key=str.casefold)
            self.list_box(p,(14,121,150,98),[(name,('manufacturer',name))for name in manufacturers],self.manufacturer)
            drivers=[d for d in self.discovery.drivers if d.manufacturer==self.manufacturer]
            self.list_box(p,(170,121,258,98),[(d.label,('driver',d.ident))for d in drivers],self.state.driver)
            self.button(p,'&Have Disk...',(329,225,99,23),('have-disk',),False,'These printer drivers are not compatible with this computer. Install a compatible printer driver package first.')
        elif self.tab>0:
            p.fill(152,33,276,228,FACE)
            if self.tab==2:
                self.paragraph(p,'Type the address of the printer you want to add.',152,33,276)
                p.menu_text('Printer address:',152,100,mnemonic=8);self.entry(p,(152,119,276,23),self.endpoint_entry,('entry','endpoint'))
                self.paragraph(p,'Example: ipp://printer/ipp/print',152,151,276)
                if not self.discovery.endpoints:self.paragraph(p,'No printers were found. You can type a printer address.',152,181,276)
            elif self.tab==3:
                self.paragraph(p,'Type a name for this printer. Existing printer names cannot be replaced by this wizard.',152,33,258)
                p.menu_text('Printer name:',152,100,mnemonic=0);self.entry(p,(152,119,276,23),self.name_entry,('entry','name'))
            else:
                self.paragraph(p,'You can print a test page after the printer is installed.',152,33,276)
                from win95lx.apps.network import draw_network_radio
                for label,y,value in (('&Yes (recommended)',116,True),('&No',139,False)):
                    action=('test',value);draw_network_radio(p,label,(152,y,276,16),self.radio_images,checked=self.state.print_test_page==value,focused=self.focus_action==action,pressed=self.pressed==action and self.press_inside);self.hit((152,y,276,16),action)
                self.paragraph(p,'Adding the printer...'if self.busy else 'Choose Finish to add this printer.',152,177,276)
        if self.tab==0 and(self.busy or self.service_error):
            p.fill(152,218,276,43,FACE);self.paragraph(p,'Looking for printers and drivers...'if self.busy else self.service_error,152,218,276)
        self.button(p,'< &Back',(193,287,75,23),('back',),self.tab>0 and not self.busy)
        self.button(p,'Finish'if self.tab==4 else'Next >',(268,287,75,23),('finish',)if self.tab==4 else('next',),not self.busy and bool(self.discovery.drivers) and not self.service_error, self.service_error)
        self.button(p,'Cancel',(353,287,75,23),('cancel',),not self.installing,'Wait for the current printer operation to finish.')
        enabled={action:active for _,_,action,active in self.button_specs};default=resolve_default(('finish',)if self.tab==4 else('next',),self.focus_action,enabled)
        for label,rect,action,active in self.button_specs:
            draw_command_button(p,label,rect,enabled=active,default=action==default,focused=self.caption_active and action==self.focus_action,pressed=action==self.pressed and self.press_inside)
            text,index=parse_label(label)
            if active and index is not None:self.command_mnemonics[text[index].casefold()]=action
        return False
    def destroyed(self,*_):self.closed=True
    def work(self,operation,complete):
        import threading
        self.busy=True;self.area.queue_draw()
        def run():
            value=error=None
            try:value=operation()
            except Exception as caught:error=caught
            def done():
                if not self.closed:
                    self.busy=False;self.installing=False;complete(value,error);self.area.queue_draw()
                return False
            GLib.idle_add(done)
        threading.Thread(target=run,name='win95lx-printer-installation',daemon=True).start()
    def discovered(self,value,error):
        if error:self.service_error=str(error);return
        self.discovery=value;self.service_error=None
        if self.discovery.endpoints:self.endpoint_entry.replace(self.discovery.endpoints[0].uri)
        self.focus_action=('next',)
    def completed(self,value,error):
        if value:self.installed=value
        if isinstance(error,PartialInstallation):self.installed=error
        if self.installed is not None and self.on_installed:self.on_installed()
        if error:self.error(error)
        if self.installed is not None:self.destroy()
    def finish(self):
        try:plan=replace(self.state,endpoint=self.endpoint_entry.text,name=self.name_entry.text).plan().validate(self.discovery)
        except PrinterError as error:self.error(error);return
        def install():
            result=self.client.install(plan)
            if plan.make_user_default:
                from win95lx.control_panel.printer_preferences import Printers
                try:Printers().set_default(result.queue)
                except Exception as error:raise PartialInstallation(result.queue,'your default printer could not be changed')from error
            if plan.print_test_page:
                from win95lx.control_panel.printer_preferences import Printers
                try:job=Printers().print_test_page(result.queue)
                except Exception as error:raise PartialInstallation(result.queue,'the test page could not be printed')from error
                result=replace(result,test_job=job)
            return result
        self.installing=True;self.work(install,self.completed)
    def list_box(self,p,rect,rows,selection):
        from win95lx.shell.scrollbar import VerticalScrollbar
        x,y,w,h=rect;kind=rows[0][1][0]if rows else'driver';self.list_rows[kind]=rows;self.list_rects[kind]=rect
        selected=next((i for i,(label,action)in enumerate(rows)if selection in(label,action[1])),0);page=(h-4)//13
        top=self.list_tops.get(kind,0)
        if kind in self.list_ensure:
            if selected<top:top=selected
            if selected>=top+page:top=selected-page+1
            self.list_ensure.discard(kind)
        top=max(0,min(top,max(0,len(rows)-page)));self.list_tops[kind]=top
        overflow=len(rows)>page;client=w-4-(16 if overflow else 0)
        p.bevel(x,y,w,h,True);p.fill(x+2,y+2,w-4,h-4,LIGHT)
        for i,(label,action)in enumerate(rows[top:top+page]):
            yy=y+2+i*13;active=selection in(label,action[1]);p.fill(x+2,yy,client,13,NAVY if active else LIGHT)
            p.cr.save();p.cr.rectangle(x+2,yy,client,13);p.cr.clip();p.text(label,x+3,yy,LIGHT if active else BLACK);p.cr.restore()
            if self.focus_action==action:self.focus_outline(p,x+2,yy,client,13,LIGHT if active else BLACK)
            if not self.busy:self.hit((x+2,yy,client,13),action)
        if overflow:
            bar=VerticalScrollbar.for_page(h-4,max(0,len(rows)-page),page)
            bar.draw(p,x+w-18,y+2,top)

    def entry(self,p,rect,entry,action):
        x,y,w,h=rect;p.bevel(x,y,w,h,True);p.fill(x+2,y+2,w-4,h-4,LIGHT)
        if not self.busy:self.hit(rect,action)
        cursor=p.font.width(entry.text[:entry.cursor]);offset=self.entry_offsets.get(action[1],0)
        if cursor-offset>w-9:offset=cursor-w+9
        if cursor<offset:offset=cursor
        self.entry_offsets[action[1]]=max(0,offset);left,right=entry.selection
        p.cr.save();p.cr.rectangle(x+3,y+3,w-6,h-6);p.cr.clip()
        if self.focus_action==action and left!=right:p.fill(x+4-offset+p.font.width(entry.text[:left]),y+4,p.font.width(entry.text[left:right]),13,NAVY)
        p.text(entry.text,x+4-offset,y+4)
        if self.focus_action==action:
            if left!=right:
                p.cr.save();p.cr.rectangle(x+4-offset+p.font.width(entry.text[:left]),y+4,p.font.width(entry.text[left:right]),13);p.cr.clip();p.text(entry.text,x+4-offset,y+4,LIGHT);p.cr.restore()
            else:p.fill(x+4-offset+cursor,y+4,1,13,BLACK)
        p.cr.restore()
    def entry_click(self,action,event):
        entry=self.endpoint_entry if action[1]=='endpoint'else self.name_entry;offset=self.entry_offsets.get(action[1],0)
        rect=next(rect for rect,a in self.hits if a==action);px=event.x-rect[0]-4+offset
        entry.cursor=min(range(len(entry.text)+1),key=lambda n:abs(self.shell.font.width(entry.text[:n])-px));entry.anchor=entry.cursor
    def focus_order(self):
        order=[]
        if self.tab==1:
            for kind in('manufacturer','driver'):
                rows=self.list_rows.get(kind,[]);value=self.manufacturer if kind=='manufacturer'else self.state.driver
                order.extend([next((action for label,action in rows if value in(label,action[1])),rows[0][1]if rows else None)])
        elif self.tab==2:order=[('entry','endpoint')]
        elif self.tab==3:order=[('entry','name')]
        elif self.tab==4:order=[('test',self.state.print_test_page)]
        order.extend(action for _,_,action,enabled in self.button_specs if enabled)
        return [a for a in order if a is not None]
    @staticmethod
    def focus_outline(p,x,y,w,h,color):
        for xx in range(x,x+w,2):p.fill(xx,y,1,1,color);p.fill(xx,y+h-1,1,1,color)
        for yy in range(y,y+h,2):p.fill(x,yy,1,1,color);p.fill(x+w-1,yy,1,1,color)
    def press(self,area,event):
        if event.button==1 and not self.busy and self.tab==1:
            from win95lx.shell.scrollbar import VerticalScrollbar
            for kind,rect in self.list_rects.items():
                x,y,w,h=rect;rows=self.list_rows[kind];page=(h-4)//13;maximum=max(0,len(rows)-page)
                if maximum and self.contains((x+w-18,y+2,16,h-4),event.x,event.y):
                    bar=VerticalScrollbar.for_page(h-4,maximum,page);value=self.list_tops.get(kind,0);py=event.y-y-2;thumb=bar.thumb_top(value)
                    if py<16:value-=1
                    elif py>=bar.height-16:value+=1
                    elif thumb<=py<thumb+bar.thumb:self.scroll_drag=(kind,bar,py-thumb,y+2)
                    else:value+=-page if py<thumb else page
                    self.list_tops[kind]=max(0,min(maximum,value));self.area.queue_draw();return True
        return super().press(area,event)
    def motion(self,area,event):
        if self.scroll_drag:
            kind,bar,offset,origin=self.scroll_drag;self.list_tops[kind]=bar.value_at(event.y-origin-offset);self.area.queue_draw();return True
        return super().motion(area,event)
    def release(self,area,event):
        if self.scroll_drag:self.scroll_drag=None;self.area.queue_draw();return True
        return super().release(area,event)
    def scroll(self,area,event):
        if self.busy:return True
        for kind,rect in self.list_rects.items():
            if self.tab==1 and self.contains(rect,event.x,event.y):
                rows=self.list_rows[kind];page=(rect[3]-4)//13;step=-3 if event.direction==Gdk.ScrollDirection.UP else 3
                self.list_tops[kind]=max(0,min(max(0,len(rows)-page),self.list_tops.get(kind,0)+step));self.area.queue_draw();return True
        return False
    def action(self,action):
        kind=action[0]
        if self.busy and not(kind=='cancel'and not self.installing):return
        if kind in('manufacturer','driver'):self.list_ensure.add(kind);self.focus_action=action
        if kind=='finish':self.finish();return
        if kind in('next','ok','back'):
            try:self.state=replace(self.state,endpoint=self.endpoint_entry.text,name=self.name_entry.text);self.state=self.state.previous()if kind=='back'else self.state.next(self.discovery)
            except PrinterError as error:self.error(error);return
            self.tab=self.state.page;self.focus_action=('entry','endpoint')if self.tab==2 else('entry','name')if self.tab==3 else('next',)
            if self.tab==1:
                # Actual inventories may have many manufacturers/models before
                # Generic/IPP Everywhere. Reveal both selected values once on
                # entry, without fighting manual viewport scrolling afterward.
                self.list_ensure.update(('manufacturer','driver'))
                self.focus_action=('manufacturer',self.manufacturer)
        elif kind=='manufacturer':
            self.manufacturer=action[1];self.state=replace(self.state,driver=next(d.ident for d in self.discovery.drivers if d.manufacturer==action[1]));self.list_tops['driver']=0;self.list_ensure.add('driver')
        elif kind=='driver':self.state=replace(self.state,driver=action[1])
        elif kind=='test':self.state=replace(self.state,print_test_page=action[1])
        elif kind=='list-scroll':
            rows=self.list_rows[action[1]];value=self.manufacturer if action[1]=='manufacturer'else self.state.driver;index=next((i for i,(label,a)in enumerate(rows)if value in(label,a[1])),0);self.action(rows[min(len(rows)-1,index+1)][1])
        elif kind=='entry':self.focus_action=action
        elif kind=='cancel':self.destroy();return
        self.area.queue_draw()
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)or'';ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK);shift=bool(event.state&Gdk.ModifierType.SHIFT_MASK)
        if self.busy:
            if not self.installing and(not ctrl and name=='Escape'or name=='F4'and event.state&Gdk.ModifierType.MOD1_MASK):self.action(('cancel',))
            return True
        if ctrl and name in('Tab','ISO_Left_Tab'):return True
        if self.focus_action and self.focus_action[0]in('manufacturer','driver')and name in('Up','Down','Home','End','Page_Up','Page_Down'):
            rows=self.list_rows[self.focus_action[0]];index=next((i for i,(_,a)in enumerate(rows)if a==self.focus_action),0)
            index=0 if name=='Home'else len(rows)-1 if name=='End'else max(0,min(len(rows)-1,index+({'Up':-1,'Down':1,'Page_Up':-7,'Page_Down':7}[name])))
            self.focus_action=rows[index][1];self.action(self.focus_action);return True
        if self.focus_action and self.focus_action[0]=='test'and name in('Up','Down','Left','Right'):
            self.focus_action=('test',not self.state.print_test_page);self.action(self.focus_action);return True
        if name in('Return','KP_Enter'):
            self.action(self.focus_action if self.focus_action in self.command_actions else ('finish',)if self.tab==4 else('next',));return True
        if self.focus_action and self.focus_action[0]=='entry':
            entry=self.endpoint_entry if self.focus_action[1]=='endpoint'else self.name_entry
            if entry.key(name,event.string or'',ctrl,shift):self.area.queue_draw();return True
        return super().key(window,event)
