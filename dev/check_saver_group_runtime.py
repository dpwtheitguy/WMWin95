#!/usr/bin/env python3
"""Production runtime proof on a disposable guest X11 display and state tree."""
import argparse,ctypes,hashlib,json,os,select,shutil,subprocess,sys,tarfile,tempfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--xvfb',type=Path,required=True);p.add_argument('--config-helper',type=Path,required=True);a=p.parse_args()
assert os.uname().nodename=='win95lx-dev'
if shutil.disk_usage('/tmp').free<1024**3:raise RuntimeError('Need1GiB free for isolated runtime proof.')
a.output.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(a.source.resolve()))
from win95lx.control_panel.screensaver_runtime import ScreenSaverCatalog,WineScreenSaverRuntime
import win95lx.control_panel.screensaver_runtime as runtime_module
runtime_sha256=hashlib.sha256(Path(runtime_module.__file__).read_bytes()).hexdigest()
checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='w95uat-group-runtime-')as tmp:
 root=Path(tmp);r,w=os.pipe();server=subprocess.Popen([str(a.xvfb),'-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
 instances=[];commands=[];captures=[];logfiles=[]
 try:
  assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();assert display!=':0';os.close(r);os.environ['DISPLAY']=display
  import gi;gi.require_version('Gdk','3.0');from gi.repository import Gdk
  owned=Gdk.Display.open(display);assert owned;Gdk.DisplayManager.get().set_default_display(owned)
  def run(command,**kwargs):
   commands.append({'kind':'run','argv':command,'prefix':kwargs['env']['WINEPREFIX']});return subprocess.run(command,**kwargs)
  trace=[True]
  def spawn(command,**kwargs):
   commands.append({'kind':'spawn','argv':command,'prefix':kwargs['env']['WINEPREFIX']})
   if trace[0]:
    log=(a.output/'first-config-font.log').open('w');logfiles.append(log);kwargs['stderr']=log;kwargs['stdout']=log;kwargs['env']={**kwargs['env'],'WINEDEBUG':'-all,err+all,+font'};trace[0]=False
   return subprocess.Popen(command,**kwargs)
  catalog=ScreenSaverCatalog.load(a.assets/'catalog.json');runtime=WineScreenSaverRuntime(catalog,root/'state',run=run,popen=spawn);instances.append(runtime)
  legacy=root/'state/plus95-nature/prefix';legacy.mkdir(parents=True);(legacy/'user.reg').write_text('legacy-disposable-fixture-keep')
  start=time.perf_counter();runtime.prepare('plus95-nature');cold=(time.perf_counter()-start)*1000
  start=time.perf_counter();runtime.prepare('plus95-travel');warm=(time.perf_counter()-start)*1000
  start=time.perf_counter()
  for identity in catalog.presentations:runtime.prepare(identity)
  all_ms=(time.perf_counter()-start)*1000
  assert all(runtime.ready(i)for i in catalog.presentations)
  assert len({runtime.prefix(i)for i in catalog.presentations})==1
  assert sum(c['argv'][0]=='wineboot'for c in commands)==1
  assert (legacy/'user.reg').read_text()=='legacy-disposable-fixture-keep'
  size=int(subprocess.check_output(['du','-sb',str(root/'state')],text=True).split()[0]);assert size<1024**3
  prefix=runtime.prefix('plus95-nature');other=WineScreenSaverRuntime(catalog,root/'state',run=run,popen=spawn);instances.append(other)
  def capture(name):
   Gdk.Display.get_default().sync();pix=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),0,0,800,600);assert pix;pix.savev(str(a.output/(name+'.png')),'png',[],[]);digest=hashlib.sha256(bytes(pix.get_pixels())).hexdigest();captures.append({'name':name,'pixels_sha256':digest});return digest
  def configure(identity,*,readonly=False,lens=False,check_other=False):
   for marker in('config-read-only','config-cancel-change','config-target-lens','config-target-wallpaper','config-target-pipes','config-target-text3d','config-target-maze'):(prefix/'drive_c'/marker).unlink(missing_ok=True)
   if readonly:(prefix/'drive_c/config-read-only').write_text('read')
   if lens:(prefix/'drive_c/config-target-lens').write_text('lens')
   process=runtime.launch(identity,'configure');time.sleep(3);capture(identity+'-configure')
   if check_other:
    before=len(commands)
    try:other.launch('plus95-travel');raise AssertionError('Parallel group launch admitted.')
    except RuntimeError:pass
    other.stop();other.prepare('plus95-travel');assert len(commands)==before and process.poll()is None
   subprocess.run(['wine',str(a.config_helper)],env=runtime.environment(identity),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=10)
   value=(prefix/'drive_c/config-state.txt').read_text();process.wait(timeout=8);runtime.stop();return value
  mute_nature=configure('plus95-nature',check_other=True);mute_travel=configure('plus95-travel',readonly=True)
  assert mute_nature=='0 1'and mute_travel=='1 1'
  science=configure('plus95-science',lens=True);sixties=configure('plus95-sixties',readonly=True,lens=True);science_again=configure('plus95-science',readonly=True,lens=True)
  assert science=='0 1'and sixties=='0 0'and science_again=='1 1'
  x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(display.encode());x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p];xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
  frames={}
  for identity in('plus95-nature','win95-ssmaze','win95-sstext3d','win95-sspipes','win95-ss3dfo','win95-ssflwbox'):
   xt.XTestFakeMotionEvent(d,-1,400,300,0);x.XFlush(d);process=runtime.launch(identity);time.sleep(3);first=capture(identity+'-3s');time.sleep(2);last=capture(identity+'-5s');assert first!=last and process.poll()is None
   xt.XTestFakeMotionEvent(d,-1,30,30,0);x.XFlush(d);code=process.wait(timeout=5);assert code==0;runtime.stop();frames[identity]={'changed':True,'mouse_exit':code}
  x.XCloseDisplay(d)
  for instance in instances:instance.close()
  for log in logfiles:log.close()
  fontlog=(a.output/'first-config-font.log').read_text(errors='replace');assert 'sserife.fon'in fontlog and 'Chosen: L"MS Sans Serif Regular"'in fontlog
  with tarfile.open(a.output/'shared-prefix-registry.tar.gz','w:gz')as archive:
   for file in prefix.glob('*.reg'):archive.add(file,arcname=file.name)
  report={'runtime_sha256':runtime_sha256,'checker_sha256':checker_sha256,'catalog_sha256':hashlib.sha256((a.assets/'catalog.json').read_bytes()).hexdigest(),'viewport':[800,600],'presentations':len(catalog.presentations),'prefixes':1,'state_bytes':size,'cold_prepare_ms':cold,'warm_second_prepare_ms':warm,'remaining_packages_prepare_ms':all_ms,'wineboot_calls':sum(c['argv'][0]=='wineboot'for c in commands),'shared_mute_states':[mute_nature,mute_travel],'basename_states':{'Science_first':science,'Sixties':sixties,'Science_reopen':science_again},'group_exclusion_verified':True,'idle_stop_did_not_kill_other':True,'legacy_fixture_untouched':True,'original_bitmap_font_selected':True,'frames':frames,'commands':commands,'captures':captures,'scope':'Actual production runtime in owned temporary guest state; no user preferences/current prefix mutated. Native-reference pixel acceptance separate.'}
  (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('presentations','prefixes','state_bytes','cold_prepare_ms','warm_second_prepare_ms','remaining_packages_prepare_ms','shared_mute_states','basename_states')},indent=2))
 finally:
  for instance in instances:
   try:instance.close()
   except Exception:pass
  for log in logfiles:
   if not log.closed:log.close()
  server.terminate();server.wait(timeout=5)
 (a.output/'cleanup.json').write_text(json.dumps({'owned_xvfb_exit':server.returncode,'temporary_state_removed_on_exit':True})+'\n')
