"""Native printer queue view backed by CUPS, without a second shell namespace.

Queue management and Add Printer have separate bounded acceptance reports.
All service calls run on one serialized worker; drawing never waits for CUPS.
"""
from concurrent.futures import ThreadPoolExecutor
import re
from gi.repository import Gtk,Gdk,GLib,GdkPixbuf
from win95lx.apps.fonts import FontWindow,FontMenu
from win95lx.control_panel.printer_preferences import Printers,PrinterError
from win95lx.shell.widgets import BLACK,LIGHT,NAVY,FACE,SHADOW

def printer_label(printer):
    return printer.description if re.fullmatch('w95lx_[0-9a-f]{32}',printer.name)and printer.description else printer.name

class PrinterQueueWindow(FontWindow):
    def __init__(self,shell,name,backend=None,*,label=None):
        self.name=name;self.backend=backend or Printers();self.jobs=();self.printer=None;self.capability=None;self.selected=None;self.scroll=0;self.busy=False;self.closed=False;self.status=True;self.notice='Connecting to printer...'
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='win95lx-printer')
        self.initial_label=label or ('Printer'if re.fullmatch('w95lx_[0-9a-f]{32}',name)else name)
        super().__init__(shell,self.initial_label,(562,185),'printers-queue-frame.png')
        icon=self.assets/'printer-16.png'
        if icon.exists():self.set_icon(GdkPixbuf.Pixbuf.new_from_file(str(icon)))
        self.connect('destroy',self.cleanup)
        self.refresh();self.timer=GLib.timeout_add_seconds(3,self.tick)
    def cleanup(self,*_):
        if self.closed:return
        self.closed=True
        if getattr(self,'timer',None):GLib.source_remove(self.timer);self.timer=None
        if self.menu_popup:self.menu_popup.finish(restore_focus=False)
        self.executor.shutdown(wait=False,cancel_futures=True)
    def tick(self):
        if self.closed:return False
        if not self.busy:self.refresh()
        return True
    def submit(self,operation,*,announce=True):
        if self.closed or self.busy:return False
        self.busy=True
        if announce:self.notice='Please wait...'
        self.area.queue_draw();future=self.executor.submit(operation)
        def complete():
            if self.closed:return False
            self.busy=False
            try:
                self.printer,self.jobs,self.capability=future.result();self.notice='';self.set_title(printer_label(self.printer))
                if self.selected not in {job.ident for job in self.jobs}:self.selected=None
            except Exception as error:
                self.printer=None;self.jobs=();self.selected=None
                self.notice=str(error) if isinstance(error,PrinterError) else 'The printing service could not complete the operation.'
                if announce:self.error(PrinterError(self.notice))
            self.area.queue_draw();return False
        future.add_done_callback(lambda _:GLib.idle_add(complete));return True
    def snapshot(self):return self.backend.printer(self.name),self.backend.jobs(self.name),self.backend.capabilities()
    def refresh(self):return self.submit(self.snapshot,announce=False)
    def selected_job(self):return next((j for j in self.jobs if j.ident==self.selected),None)
    def visible_rows(self):return max(1,(self.get_size()[1]-(24 if self.status else 4)-63)//17)
    def set_scroll(self,value):self.scroll=max(0,min(max(0,len(self.jobs)-self.visible_rows()),value));self.area.queue_draw()
    def rows(self,menu):
        job=self.selected_job();admin=bool(self.capability and self.capability.administration);available=not self.busy and self.printer is not None
        if menu=='Printer':return [('Set As Default','default',available,''),('Print Test Page','test',available,''),None,('Close','close',True,'')]
        if menu=='Document':return [('Cancel Printing','cancel',available and job is not None and (job.owner==self.backend.user or admin),'Select one of your documents to cancel printing.')]
        if menu=='View':return [('Status Bar','status',True,''),('Refresh','refresh',not self.busy,'','F5')]
        return [('About Printers','about',True,'')]
    def command(self,command):
        if isinstance(command,tuple) and command[0]=='menu':
            name,x=command[1:];self.menu_popup=FontMenu(self,self.rows(name),x,160,top=42);return
        if isinstance(command,tuple) and command[0]=='job':self.selected=command[1];self.area.queue_draw();return
        if isinstance(command,tuple) and command[0]=='scroll':self.set_scroll(self.scroll+command[1]);return
        if isinstance(command,tuple) and command[0]=='thumb':
            self.thumb_drag=(self.get_display().get_default_seat().get_pointer().get_position().y,self.scroll,command[1]);return
        if command in ('default','test','cancel'):
            job=self.selected_job()
            def operation():
                if command=='default':self.backend.set_default(self.name)
                elif command=='test':self.backend.print_test_page(self.name)
                elif job:self.backend.cancel(self.name,job.ident)
                return self.snapshot()
            self.submit(operation);return
        if command=='refresh':self.refresh();return
        if command=='status':self.status=not self.status;self.area.queue_draw();return
        if command=='about':
            from win95lx.apps.dialogs import message_box
            message_box(self,'Printers','Windows 95 style printer queues. Printing is provided by the system printing service.',Gtk.MessageType.INFO);return
        return super().command(command)
    def draw(self,area,cr):
        from win95lx.shell.widgets import Painter
        p=Painter(cr,self.shell.font);w,h=self.get_size();self.chrome(p,w,h)
        # Replace the captured reference title even at native dimensions.
        p.fill(24,4,w-80,18,NAVY if self.caption_active else SHADOW);p.cr.save();p.cr.rectangle(24,4,w-80,18);p.cr.clip();p.text(printer_label(self.printer)if self.printer else self.initial_label,24,6,LIGHT,bold=True);p.cr.restore()
        p.fill(4,23,w-8,19,FACE)
        for name,x,width in (('Printer',10,42),('Document',52,61),('View',113,35),('Help',148,34)):
            p.menu_text(name,x,25,mnemonic=0);self.hit((x-4,23,width,19),('menu',name,x-4))
        bottom=h-24 if self.status else h-4
        if (w,h)!=self.native_size or not self.status:p.bevel(4,42,w-8,bottom-42,sunken=True)
        p.fill(6,44,w-12,max(0,bottom-44),LIGHT)
        columns=(('Document Name',185),('Status',80),('Owner',80),('Progress',80),('Started At',max(125,w-437)));x=6
        for label,width in columns:
            width=min(width,max(0,w-6-x))
            if not width:break
            p.bevel(x,44,width,17);p.text(label,x+6,46);x+=width
        self.scroll=min(self.scroll,max(0,len(self.jobs)-self.visible_rows()))
        for index,job in enumerate(self.jobs[self.scroll:]):
            y=63+index*17
            if y+17>bottom-2:break
            selected=job.ident==self.selected
            if selected:p.fill(6,y,w-12,17,NAVY)
            color=LIGHT if selected else BLACK;x=9
            for value,width in ((job.title,185),(job.status,80),(job.owner,80),(f'{job.kilobytes} KB',80)):
                cr.save();cr.rectangle(x,y,width-5,17);cr.clip();p.text(value,x,y+2,color);cr.restore();x+=width
            self.hit((6,y,w-12,17),('job',job.ident))
        if len(self.jobs)>self.visible_rows():
            from win95lx.shell.scrollbar import VerticalScrollbar
            height=bottom-61;bar=VerticalScrollbar.for_page(height,len(self.jobs)-self.visible_rows(),self.visible_rows());bar.draw(p,w-22,61,self.scroll,track='window')
            self.hit((w-22,61+bar.thumb_top(self.scroll),16,bar.thumb),('thumb',bar))
            self.hit((w-22,61,16,16),('scroll',-1));self.hit((w-22,bottom-16,16,16),('scroll',1))
            self.hit((w-22,77,16,max(0,bar.thumb_top(self.scroll)-16)),('scroll',-self.visible_rows()))
            after=61+bar.thumb_top(self.scroll)+bar.thumb;self.hit((w-22,after,16,max(0,bottom-16-after)),('scroll',self.visible_rows()))
        if self.status:
            if (w,h)!=self.native_size:p.bevel(4,h-22,w-8,18,sunken=True)
            p.fill(5,h-21,max(0,w-32),16,FACE);p.text(self.notice or f'{len(self.jobs)} jobs in queue',7,h-20)
        return False
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval);alt=bool(event.state&Gdk.ModifierType.MOD1_MASK)
        if name=='F5':self.refresh();return True
        if name=='Delete' and self.selected_job():
            if self.rows('Document')[0][2]:self.command('cancel')
            return True
        if name in ('Up','Down') and self.jobs:
            ids=[job.ident for job in self.jobs];index=ids.index(self.selected) if self.selected in ids else -1;index=(index+(-1 if name=='Up' else 1))%len(ids);self.selected=ids[index]
            if index<self.scroll:self.set_scroll(index)
            elif index>=self.scroll+self.visible_rows():self.set_scroll(index-self.visible_rows()+1)
            self.area.queue_draw();return True
        if alt and name and name.lower() in ('p','d','v','h'):
            target={'p':('Printer',6),'d':('Document',48),'v':('View',109),'h':('Help',144)}[name.lower()];self.command(('menu',*target));return True
        return super().key(window,event)
    def wheel(self,area,event):
        if event.direction==Gdk.ScrollDirection.UP:self.set_scroll(self.scroll-3)
        elif event.direction==Gdk.ScrollDirection.DOWN:self.set_scroll(self.scroll+3)
        else:return False
        return True
    def motion(self,area,event):
        if getattr(self,'thumb_drag',None):
            y,value,bar=self.thumb_drag;self.set_scroll(bar.value_at(bar.thumb_top(value)+event.y_root-y));return True
        return super().motion(area,event)
    def release(self,area,event):
        self.thumb_drag=None;return super().release(area,event)

class PrinterNamespace:
    """Explorer adapter: immutable inventory snapshots, no duplicate chrome.

    Call load() on the shell's service worker, then publish() on its GTK loop.
    Entry targets are structured tuples, never executable shell strings.
    """
    title='Printers'
    def __init__(self,backend=None):self.backend=backend or Printers();self.printers=();self.capability=None;self.error=None
    def load(self):return self.backend.inventory(),self.backend.capabilities()
    def publish(self,snapshot):self.printers,self.capability=snapshot;self.error=None
    def entries(self):
        ordered=sorted(self.printers,key=lambda p:(printer_label(p).casefold(),p.name.casefold()));labels=[printer_label(p)for p in ordered]
        return (('printer-add','Add Printer',('printer-add',)),)+tuple(('printer-default' if printer.default else 'printer',label+(' ('+printer.name+')'if sum(other.casefold()==label.casefold()for other in labels)>1 else''),('printer-queue',printer.name))for printer,label in zip(ordered,labels))
    def description(self,name):
        printer=next((p for p in self.printers if p.name==name),None)
        if printer is None:return 'Adds a printer using the Add Printer Wizard.' if name=='Add Printer' else ''
        return '\n'.join(text for text in(printer.description,printer.status,printer.location,printer.model)if text)
    def open(self,shell,name):
        printer=next((printer for printer in self.printers if printer.name==name),None)
        window=PrinterQueueWindow(shell,name,self.backend,label=printer_label(printer)if printer else None);window.show_all();return window
