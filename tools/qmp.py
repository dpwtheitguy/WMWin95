#!/usr/bin/env python3
"""Control project VMs over local QMP: status, framebuffer capture, keys and power."""
import argparse,json,socket,time
from pathlib import Path
class QMP:
    def __init__(self,path):
        self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); self.socket.settimeout(15); self.socket.connect(str(path)); self.stream=self.socket.makefile('rwb'); greeting=json.loads(self.stream.readline())
        if 'QMP' not in greeting: raise RuntimeError('Not a QMP endpoint')
        self.call('qmp_capabilities')
    def call(self,command,arguments=None):
        self.stream.write((json.dumps({'execute':command,'arguments':arguments or {}})+'\n').encode()); self.stream.flush()
        while True:
            line=self.stream.readline()
            if not line: raise RuntimeError('QMP disconnected')
            value=json.loads(line)
            if 'error' in value: raise RuntimeError(value['error'])
            if 'return' in value: return value['return']
    def close(self): self.stream.close(); self.socket.close()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--socket',type=Path,default=Path('private/run/xubuntu.qmp')); sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('status'); sub.add_parser('pause'); sub.add_parser('resume'); cap=sub.add_parser('capture'); cap.add_argument('output',type=Path); keys=sub.add_parser('key'); keys.add_argument('keys',help='QEMU key names, e.g. ret or ctrl-alt-f2'); typing=sub.add_parser('type'); typing.add_argument('text',help='US-layout ASCII text; newline presses Enter'); click=sub.add_parser('click'); click.add_argument('x',type=int); click.add_argument('y',type=int); click.add_argument('--width',type=int,default=800); click.add_argument('--height',type=int,default=600); click.add_argument('--double',action='store_true'); sub.add_parser('powerdown'); sub.add_parser('quit')
    a=p.parse_args(); q=QMP(a.socket)
    try:
        if a.action=='status': result={'status':q.call('query-status'),'kvm':q.call('query-kvm'),'version':q.call('query-version')}
        elif a.action in ('pause','resume'):result=q.call('stop' if a.action=='pause' else 'cont')
        elif a.action=='capture':
            if a.output.exists(): p.error('Capture output exists; use a new filename')
            a.output.parent.mkdir(parents=True,exist_ok=True); result=q.call('screendump',{'filename':str(a.output.resolve())})
        elif a.action=='type':
            punctuation={' ':('spc',False),'\n':('ret',False),'-':('minus',False),'_':('minus',True),'/':('slash',False),'.':('dot',False),':':('semicolon',True),';':('semicolon',False),'$':('4',True),'"':('apostrophe',True),"'":('apostrophe',False),'=':('equal',False),'\\':('backslash',False),'>':('dot',True),'[':('bracket_left',False),']':('bracket_right',False),'|':('backslash',True),'(':('9',True),')':('0',True)}
            events=[]
            if len(a.text)>512: p.error('Text limited to 512 characters per call')
            for char in a.text:
                if char.isascii() and char.isalnum(): key=char.lower(); shift=char.isupper()
                elif char in punctuation: key,shift=punctuation[char]
                else: p.error('Unsupported US-layout character: '+repr(char))
                events.append(([{'type':'qcode','data':'shift'}] if shift else [])+[{'type':'qcode','data':key}])
            for keys in events:
                q.call('send-key',{'keys':keys,'hold-time':20}); time.sleep(0.04)
            result={'characters_sent':len(a.text)}
        elif a.action=='click':
            if not (0<=a.x<a.width and 0<=a.y<a.height): p.error('Pointer outside framebuffer')
            q.call('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(a.x*32767/(a.width-1))}},{'type':'abs','data':{'axis':'y','value':round(a.y*32767/(a.height-1))}}]})
            for _ in range(2 if a.double else 1):
                q.call('input-send-event',{'events':[{'type':'btn','data':{'down':True,'button':'left'}}]}); time.sleep(.04); q.call('input-send-event',{'events':[{'type':'btn','data':{'down':False,'button':'left'}}]}); time.sleep(.08)
            result={'clicked':[a.x,a.y]}
        elif a.action=='key':
            result=q.call('send-key',{'keys':[{'type':'qcode','data':key} for key in a.keys.split('-')],'hold-time':100});time.sleep(.2)
        else: result=q.call('system_powerdown' if a.action=='powerdown' else 'quit')
        print(json.dumps(result,indent=2))
    finally:q.close()
if __name__=='__main__':main()
