#!/usr/bin/env python3
"""Actual guest modes, native-size Start pixels and QMP absolute pointer input."""
import argparse,json,re,shlex,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from qmp import QMP
from pixels import read
from win95lx.shell.start_menu import HEIGHT,WIDTH
MODES=((640,480),(800,600),(1024,768),(1280,720),(1366,768),(1920,1080),(2560,1440),(3440,1440),(3840,2160),(5120,2880),(7680,4320))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    ssh=['ssh','-i',str(ROOT/'private/run/guest_ed25519'),'-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(ROOT/'private/run/installed_known_hosts'),'-p','22295','developer@127.0.0.1']
    password=json.loads((ROOT/'private/run/development-credentials.json').read_text())['password']
    def guest(code):
        command='test "$(hostname)" = win95lx-dev && export DISPLAY=:0 XAUTHORITY=/run/lightdm/root/:0 && export PYTHONPATH=/opt/win95lx/current/src && python3 -c '+shlex.quote(code)
        result=subprocess.run(ssh+['sudo -S -p "" /bin/sh -c '+shlex.quote(command)],input=password+'\n',capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        return result.stdout
    current=guest("import subprocess;print(subprocess.check_output(['xrandr','--query'],text=True))")
    original=tuple(map(int,re.search(r'current (\d+) x (\d+)',current).groups()))
    q=QMP(ROOT/'private/run/xubuntu.qmp');rows=[];baseline=None
    def key(name):q.call('send-key',{'keys':[{'type':'qcode','data':name}],'hold-time':60});time.sleep(.15)
    try:
        for width,height in MODES:
            key('esc');guest(f'from win95lx.display_modes import set_resolution;set_resolution({width},{height})');time.sleep(.6)
            # Use framebuffer coordinates and the actual current guest size;
            # never reuse the 800x600 normalization for a larger display.
            q.call('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(26*32767/(width-1))}},{'type':'abs','data':{'axis':'y','value':round((height-14)*32767/(height-1))}}]})
            for down in (True,False):q.call('input-send-event',{'events':[{'type':'btn','data':{'down':down,'button':'left'}}]});time.sleep(.05)
            time.sleep(.3);path=a.output/f'{width}x{height}-start.png';q.call('screendump',{'filename':str(path.resolve()),'format':'png'})
            w,h,pixels=read(path);assert (w,h)==(width,height)
            x,y=2,height-HEIGHT-24
            # The fixed native menu should retain identical pixels at every
            # size. Its open state must come from this real pointer click.
            crop=tuple(pixels[(y+yy)*w+x+xx] for yy in range(HEIGHT) for xx in range(WIDTH))
            assert len(set(crop))>8,'Start menu did not open under the real pointer'
            if baseline is None:baseline=crop
            difference=sum(a!=b for a,b in zip(baseline,crop))
            rows.append({'mode':[width,height],'pointer_opened_start':True,'native_menu_difference':difference,'capture':path.name})
            assert difference==0,rows[-1]
            key('esc');print(json.dumps(rows[-1]),flush=True)
    finally:
        key('esc');guest(f'from win95lx.display_modes import set_resolution;set_resolution({original[0]},{original[1]})');q.close()
        (a.output/'report.json').write_text(json.dumps({'original_mode':original,'restored':True,'checks':rows,'scope':'Actual driver mode and QMP absolute pointer at Start; fixed native Start pixels across sizes. Host fractional zoom and all applet controls require separate checks.'},indent=2)+'\n')
if __name__=='__main__':main()
