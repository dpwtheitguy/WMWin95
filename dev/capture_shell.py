#!/usr/bin/env python3
"""Record reproducible implementation screens. These are not original references."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));from qmp import QMP
from ppm_to_png import convert
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);q=QMP(ROOT/'private/run/xubuntu.qmp');records=[];actions=[]
def key(names):
    q.call('send-key',{'keys':[{'type':'qcode','data':x} for x in names.split('-')],'hold-time':70});time.sleep(.2);actions.append({'key':names})
def click(x,y,double=False):
    q.call('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(x*32767/799)}},{'type':'abs','data':{'axis':'y','value':round(y*32767/599)}}]})
    for _ in range(2 if double else 1):
        q.call('input-send-event',{'events':[{'type':'btn','data':{'down':True,'button':'left'}}]});time.sleep(.04);q.call('input-send-event',{'events':[{'type':'btn','data':{'down':False,'button':'left'}}]});time.sleep(.08)
    time.sleep(.2);actions.append({'click':[x,y],'double':double})
def capture(name):
    time.sleep(.25);ppm=a.output/(name+'.ppm');png=a.output/(name+'.png');q.call('screendump',{'filename':str(ppm.resolve())});convert(ppm,png);records.append({'screen':name,'file':png.name,'sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'actions_since_start':list(actions)})
try:
    key('esc')
    for _ in range(8):key('alt-f4')
    capture('clean-desktop');key('ctrl-esc');capture('start-menu');key('esc');click(44,27,True);capture('my-computer');key('alt-ret');capture('system-properties');key('alt-f4');click(250,145,True);capture('control-panel');click(168,160,True);capture('display-properties');key('ctrl-esc');click(90,550);capture('close-desktop-dialog');key('esc')
finally:q.close()
manifest={'kind':'implementation-smoke-captures','reference_comparison_performed':False,'pixel_accuracy_claimed':False,'resolution':[800,600],'screens':records,'code_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'src').rglob('*.py')},'config':json.loads((ROOT/'config/xfce-prototype.json').read_text())};(a.output/'capture-run.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Recorded',len(records),'implementation screens in',a.output)
