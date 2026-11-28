"""Measured Display Properties Screen Saver page using shared command controls."""
import cairo
from win95lx.apps.screensaver_host import host_for
from win95lx.shell.widgets import BLACK,LIGHT,NAVY,SHADOW,FACE
from win95lx.shell.command_button import draw_command_button

COMBO=(33,261,173,21)

def frame_for(shell):
    if not hasattr(shell,'screen_saver_frame'):
        path=shell.assets/'display-screen-saver.png'
        shell.screen_saver_frame=cairo.ImageSurface.create_from_png(str(path)) if path.is_file() else None
    return shell.screen_saver_frame

def draw(p,win,shell):
    host=host_for(shell);x,y=win.x,win.y;frame=frame_for(shell)
    if frame:p.image(frame,x,y)
    else:
        p.bevel(x+9,y+49,386,360);p.text('Screen Saver',x+32,y+242)
    selected=host.pending.saver!='';label=host.names[host.ids.index(host.pending.saver)] if host.pending.saver in host.ids else '(Unavailable)'
    p.cr.save();p.cr.rectangle(x+35,y+263,153,17);p.cr.clip();p.fill(x+35,y+263,153,17,LIGHT)
    focused=host.focus=='selection' and win is shell.state.active
    if focused:
        p.fill(x+36,y+264,151,15,BLACK);p.fill(x+37,y+265,149,13,NAVY)
    p.text(label,x+(37 if focused else 36),y+(265 if focused else 264),LIGHT if focused else BLACK);p.cr.restore()
    shell.hit(x+33,y+261,173,21,('saver-select',win))
    for label,mode,rect in (('Se&ttings...','configure',(211,259,75,23)),('Pre&view','fullscreen',(292,259,75,23))):
        available,reason=host.available(mode)
        bx,by,w,h=rect;draw_command_button(p,label,(x+bx,y+by,w,h),enabled=available,focused=host.focus==mode,default=host.focus==mode)
        shell.hit(x+bx,y+by,w,h,('saver-launch',win,mode))
    # Native authenticated locking is not delegated to an original Win32 saver.
    shell.hit(x+33,y+288,199,23,('saver-reason',win,'Password protection is managed by the session lock service. It is not provided by a legacy screen saver.'))
    if selected:
        p.fill(x+244,y+293,26,15,FACE);p.text('Wait:',x+244,y+293);p.fill(x+244,y+305,p.font.width('W'),1,BLACK)
    p.fill(x+275,y+292,26,16,LIGHT if selected else FACE);p.text(str(host.pending.wait_minutes),x+276,y+293,BLACK if selected else SHADOW)
    shell.hit(x+273,y+290,28,20,('saver-wait-focus',win))
    if selected:
        if not hasattr(shell,'screen_saver_spin'):
            shell.screen_saver_spin=cairo.ImageSurface.create_from_png(str(shell.assets/'display-screen-saver-spin-enabled.png'))
        p.image(shell.screen_saver_spin,x+301,y+290)
    for upper,rect in ((True,(301,290,17,10)),(False,(301,300,17,10))):
        bx,by,w,h=rect;shell.hit(x+bx,y+by,w,h,('saver-wait',win,1 if upper else -1))
    if selected:
        p.fill(x+324,y+293,42,15,FACE);p.text('minutes',x+324,y+293)
    # Keep native disabled monitor-power controls; expose their limitation.
    shell.hit(x+24,y+324,357,70,('saver-reason',win,'Monitor standby and power-off settings are managed by the Power Properties applet.'))
    for label,bx,command,enabled in (('OK',158,'ok',True),('Cancel',239,'cancel',True),('&Apply',320,'apply',host.dirty)):
        draw_command_button(p,label,(x+bx,y+415,75,23),default=host.focus==command or host.focus not in ('ok','cancel','apply','fullscreen','configure') and command=='ok',focused=host.focus==command,enabled=enabled)
        if enabled:shell.hit(x+bx,y+415,75,23,('saver-command',win,command))
    text=host.error or host.status
    if text:
        p.fill(x+16,y+395,370,13,FACE);p.cr.save();p.cr.rectangle(x+16,y+395,370,13);p.cr.clip();p.text(text,x+17,y+395);p.cr.restore()
    shell.hit(x+9,y+29,72,21,('display-tab','background'))
    shell.hit(x+270,y+29,49,21,('display-tab','settings'))
    for left,width,label in ((159,67,'Appearance'),(226,43,'Web')):
        shell.hit(x+left,y+29,width,21,('saver-reason',win,label+' settings are not implemented on this page yet.'))
    shell.hit(x+364,y+3,17,16,('saver-reason',win,'Select a screen saver, adjust Wait, then choose Apply. Preview and Settings prepare compatibility components in the background.'))
    shell.hit(x+382,y+3,17,16,('close',win))


def action(shell,action):
    from gi.repository import Gtk
    from win95lx.apps.dialogs import message_box
    host=host_for(shell);kind=action[0];win=action[1]
    if kind=='saver-select':
        from win95lx.apps.choice_dialog import ChoicePopup
        # ChoicePopup's shared owner API also serves Cairo shell consumers.
        shell.shell=shell
        index=host.ids.index(host.pending.saver) if host.pending.saver in host.ids else 0
        host.popup=ChoicePopup(shell,(win.x+33,win.y+261,173,21),host.names,index,host.select)
    elif kind=='saver-launch':
        host.focus=action[2];available,reason=host.available(action[2])
        if available:host.launch(action[2])
        else:message_box(shell,'Display Properties',reason,Gtk.MessageType.INFO)
    elif kind=='saver-wait-focus':host.focus='wait';host.wait_digits=''
    elif kind=='saver-wait' and host.pending.saver:host.set_wait(host.pending.wait_minutes+action[2])
    elif kind=='saver-reason':message_box(shell,'Display Properties',action[2],Gtk.MessageType.INFO)
    elif kind=='saver-command':
        command=action[2];host.focus=command
        if command=='cancel':host.cancel();shell.state.windows.remove(win)
        else:
            try:host.apply()
            except (OSError,ValueError,RuntimeError) as error:message_box(shell,'Display Properties',str(error),Gtk.MessageType.ERROR)
            else:
                if command=='ok':host.stop_preview();shell.state.windows.remove(win)
    shell.area.queue_draw()


def key(shell,event):
    from gi.repository import Gdk
    host=host_for(shell);name=Gdk.keyval_name(event.keyval)or'';alt=event.state&Gdk.ModifierType.MOD1_MASK
    win=shell.state.active
    if host.tasks and host.busy and host.session_mode is not None:
        if host.session_mode=='fullscreen' or name=='Escape':host.stop_preview()
        return True
    if alt and name.casefold() in ('s','t','v','w'):
        field={'s':'selection','t':'configure','v':'fullscreen','w':'wait'}[name.casefold()];host.focus=field
        if field in ('configure','fullscreen'):host.launch(field)
        shell.area.queue_draw();return True
    if name in ('Tab','ISO_Left_Tab'):
        fields=['selection']+([mode for mode in ('configure','fullscreen')if host.available(mode)[0]])+(['wait']if host.pending.saver else[])+['ok','cancel']+(['apply']if host.dirty else[])
        index=fields.index(host.focus) if host.focus in fields else 0
        host.focus=fields[(index+(-1 if name=='ISO_Left_Tab' or event.state&Gdk.ModifierType.SHIFT_MASK else 1))%len(fields)];shell.area.queue_draw();return True
    if host.focus=='selection' and name in ('Up','Down','Home','End') and not alt:
        index=host.ids.index(host.pending.saver) if host.pending.saver in host.ids else 0
        index=0 if name=='Home' else len(host.ids)-1 if name=='End' else max(0,min(len(host.ids)-1,index+(1 if name=='Down' else -1)))
        host.select(index);return True
    if host.focus=='selection' and (name=='F4' or name=='Down' and alt):action(shell,('saver-select',win));return True
    if host.focus=='wait' and host.pending.saver:
        if name in ('Up','Down'):host.set_wait(host.pending.wait_minutes+(1 if name=='Up' else -1));return True
        if name.isdigit():host.type_wait(name);return True
    if name in ('Return','KP_Enter','space'):
        if host.focus in ('configure','fullscreen'):host.launch(host.focus)
        else:action(shell,('saver-command',win,host.focus if host.focus in ('ok','cancel','apply') else 'ok'))
        return True
    if name=='Escape':action(shell,('saver-command',win,'cancel'));return True
    return False
