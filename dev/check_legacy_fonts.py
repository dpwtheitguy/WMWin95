#!/usr/bin/env python3
"""Verify real legacy FON import and compare old/native cache paths in isolation."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[]
    source_code='''from pathlib import Path
import subprocess,time,json
from win95lx.control_panel.font_catalog import FontCatalog
c=FontCatalog()
if MODE=='command':
 def cache():
  subprocess.run(['fc-cache','-f',str(c.root)],check=True,capture_output=True);c.scanner.refresh()
 c.cache=cache
start=time.perf_counter();faces=c.install(Path(SOURCE));elapsed=time.perf_counter()-start
out=subprocess.check_output(['fc-list','--format','%{file}\\n'],text=True);assert str(faces[0].path) in out
result={'mode':MODE,'font':Path(SOURCE).name,'format':faces[0].format,'faces':len(faces),'install_seconds':elapsed,'cross_process_visible':True}
start=time.perf_counter();c.remove(faces[0].path);result['remove_seconds']=time.perf_counter()-start
out=subprocess.check_output(['fc-list','--format','%{file}\\n'],text=True);assert str(faces[0].path) not in out
result['cross_process_removed']=True;print(json.dumps(result))
'''
    for filename,mode in (('arial.ttf','command'),('arial.ttf','native'),('sserife.fon','native')):
        source=ROOT/'private/cabsets/windows95'/filename
        with tempfile.TemporaryDirectory() as directory:
            env={**os.environ,'HOME':directory,'XDG_CONFIG_HOME':directory+'/.config','XDG_CACHE_HOME':directory+'/.cache','XDG_DATA_HOME':directory+'/.local/share','PYTHONPATH':str(ROOT/'src')}
            code=source_code.replace('SOURCE',repr(str(source))).replace('MODE',repr(mode))
            result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,check=True);row=json.loads(result.stdout);rows.append(row);print(json.dumps(row),flush=True)
    report={'checks':rows,'host_fonts_changed':False,'scope':'Disposable HOME and Fontconfig cache, real cross-process fc-list readback; elapsed operation time, not end-to-end UI latency.'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
