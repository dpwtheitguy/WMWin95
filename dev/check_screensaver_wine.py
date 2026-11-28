#!/usr/bin/env python3
"""Isolated Wine compatibility research. Never uses an existing X display or prefix."""
import os,sys,json,time,subprocess,tempfile,ctypes,select,shutil,atexit,hashlib,tarfile
from pathlib import Path
import argparse
# These Win32 fixtures are original test code, not proprietary saver resources.
HELPER_SOURCES={'preview_host.c': '#include <windows.h>\nstatic LRESULT CALLBACK proc(HWND w,UINT m,WPARAM a,LPARAM b){if(m==WM_TIMER){static int ticks=0;if(++ticks>=80||GetFileAttributesA("C:\\\\preview-close")!=INVALID_FILE_ATTRIBUTES)DestroyWindow(w);return 0;}if(m==WM_DESTROY){PostQuitMessage(0);return 0;}return DefWindowProcA(w,m,a,b);}\nvoid entry(void){HINSTANCE instance=GetModuleHandleA(0);WNDCLASSA c={0};c.lpfnWndProc=proc;c.hInstance=instance;c.lpszClassName="W95OwnedSaverPreview";c.hbrBackground=(HBRUSH)GetStockObject(GRAY_BRUSH);RegisterClassA(&c);HWND w=CreateWindowExA(0,c.lpszClassName,"Owned saver preview",WS_OVERLAPPEDWINDOW|WS_VISIBLE,40,40,340,280,0,0,instance,0);HWND child=CreateWindowExA(0,"STATIC","",WS_CHILD|WS_VISIBLE|SS_BLACKRECT,10,10,300,200,w,0,instance,0);char buffer[32];unsigned long n=(unsigned long)child;int length=0;do{buffer[length++]=(char)(\'0\'+n%10);n/=10;}while(n);for(int i=0;i<length/2;i++){char t=buffer[i];buffer[i]=buffer[length-1-i];buffer[length-1-i]=t;}DWORD written;HANDLE file=CreateFileA("C:\\\\preview-hwnd.txt",GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);WriteFile(file,buffer,(DWORD)length,&written,0);CloseHandle(file);SetTimer(w,1,250,0);MSG message;while(GetMessageA(&message,0,0,0)>0){TranslateMessage(&message);DispatchMessageA(&message);}ExitProcess(0);}\n', 'background_host.c': '#include <windows.h>\nstatic LRESULT CALLBACK proc(HWND w,UINT m,WPARAM a,LPARAM b){if(m==WM_TIMER){static int ticks=0;if(++ticks>=120||GetFileAttributesA("C:\\\\background-close")!=INVALID_FILE_ATTRIBUTES)DestroyWindow(w);return 0;}if(m==WM_DESTROY){PostQuitMessage(0);return 0;}if(m==WM_PAINT){PAINTSTRUCT ps;HDC dc=BeginPaint(w,&ps);for(int y=0;y<600;y+=40)for(int x=0;x<800;x+=40){RECT r={x,y,x+40,y+40};HBRUSH brush=CreateSolidBrush(RGB((x/40)%2?240:20,(y/40)%2?210:40,((x+y)/40)%2?180:30));FillRect(dc,&r,brush);DeleteObject(brush);}SetTextColor(dc,RGB(255,255,255));SetBkColor(dc,RGB(0,0,0));TextOutA(dc,100,100,"Win95LX owned patterned background",33);EndPaint(w,&ps);return 0;}return DefWindowProcA(w,m,a,b);}\nvoid entry(void){HINSTANCE instance=GetModuleHandleA(0);WNDCLASSA c={0};c.lpfnWndProc=proc;c.hInstance=instance;c.lpszClassName="W95OwnedSaverBackground";RegisterClassA(&c);HWND w=CreateWindowExA(0,c.lpszClassName,"Owned patterned background",WS_POPUP|WS_VISIBLE,0,0,800,600,0,0,instance,0);UpdateWindow(w);DWORD count;HANDLE f=CreateFileA("C:\\\\background-ready",GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);WriteFile(f,"ready",5,&count,0);CloseHandle(f);SetTimer(w,1,250,0);MSG message;while(GetMessageA(&message,0,0,0)>0){TranslateMessage(&message);DispatchMessageA(&message);}ExitProcess(0);}\n', 'config_parameter_editor.c': '#include <windows.h>\nstatic HWND checkbox,alternative,okay,cancel;static int mode;\nstatic BOOL CALLBACK children(HWND w,LPARAM data){(void)data;char text[128],clean[128],cls[64];GetWindowTextA(w,text,128);int j=0;for(int i=0;text[i]&&j<127;i++)if(text[i]!=\'&\')clean[j++]=text[i];clean[j]=0;GetClassNameA(w,cls,64);if(lstrcmpiA(cls,"Button"))return TRUE;if((mode==0&&!lstrcmpiA(clean,"Mute Sound"))||(mode==1&&!lstrcmpiA(clean,"Black Hole"))||(mode==2&&!lstrcmpiA(clean,"Use Wallpaper"))||(mode==3&&!lstrcmpiA(clean,"Multiple"))||(mode==4&&!lstrcmpiA(clean,"Time"))||(mode==5&&!lstrcmpiA(clean,"Maze Overlay")))checkbox=w;if((mode==1&&!lstrcmpiA(clean,"Glass Sphere"))||(mode==3&&!lstrcmpiA(clean,"Single"))||(mode==4&&!lstrcmpiA(clean,"Text")))alternative=w;if(!lstrcmpiA(clean,"OK"))okay=w;if(!lstrcmpiA(clean,"Cancel"))cancel=w;return TRUE;}\nstatic BOOL CALLBACK windows(HWND w,LPARAM data){(void)data;if(!IsWindowVisible(w))return TRUE;EnumChildWindows(w,children,0);return checkbox&&okay&&cancel?FALSE:TRUE;}\nvoid entry(void){if(GetFileAttributesA("C:\\\\config-target-lens")!=INVALID_FILE_ATTRIBUTES)mode=1;else if(GetFileAttributesA("C:\\\\config-target-wallpaper")!=INVALID_FILE_ATTRIBUTES)mode=2;if(GetFileAttributesA("C:\\\\config-target-pipes")!=INVALID_FILE_ATTRIBUTES)mode=3;else if(GetFileAttributesA("C:\\\\config-target-text3d")!=INVALID_FILE_ATTRIBUTES)mode=4;if(GetFileAttributesA("C:\\\\config-target-maze")!=INVALID_FILE_ATTRIBUTES)mode=5;EnumWindows(windows,0);if(!checkbox||!okay||!cancel||((mode==1||mode==3||mode==4)&&!alternative))ExitProcess(2);int before=(int)SendMessageA(checkbox,BM_GETCHECK,0,0);BOOL readonly=GetFileAttributesA("C:\\\\config-read-only")!=INVALID_FILE_ATTRIBUTES;if(!readonly)SendMessageA((mode==1||mode==3||mode==4)&&before?alternative:checkbox,BM_CLICK,0,0);int after=(int)SendMessageA(checkbox,BM_GETCHECK,0,0);char value[3]={(char)(\'0\'+before),\' \',(char)(\'0\'+after)};DWORD written;HANDLE f=CreateFileA("C:\\\\config-state.txt",GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);WriteFile(f,value,3,&written,0);CloseHandle(f);BOOL cancelchange=GetFileAttributesA("C:\\\\config-cancel-change")!=INVALID_FILE_ATTRIBUTES;PostMessageA(readonly||cancelchange?cancel:okay,BM_CLICK,0,0);ExitProcess(0);}\n'}
p=argparse.ArgumentParser();p.add_argument('--keep-prefix',action='store_true');p.add_argument('--emit-helper-sources',type=Path);p.add_argument('--media',type=Path);p.add_argument('--output',type=Path);p.add_argument('--xvfb',type=Path);p.add_argument('--preview-host',type=Path);p.add_argument('--config-editor',type=Path);p.add_argument('--post-save-launch',action='store_true');p.add_argument('--first-delay',type=float,default=3);p.add_argument('--second-delay',type=float,default=4);p.add_argument('--background-host',type=Path);p.add_argument('--dismiss',choices=('mouse','keyboard'),default='mouse');p.add_argument('--repeat',type=int,choices=range(1,6),default=1);p.add_argument('--maze-win95',action='store_true');p.add_argument('--classic-fonts',type=Path);p.add_argument('--classic-colors',action='store_true');p.add_argument('--debug-profile',choices=('load','wgl','font','relay'),default='load');p.add_argument('--size',default='800x600');p.add_argument('--mode',choices=('s','c','p'),default='s');p.add_argument('--cases',default='nature-missing,nature-wrong-alias,nature-complete,stars,blocks,lens,mystify');args=p.parse_args()
if args.emit_helper_sources:
 args.emit_helper_sources.mkdir(parents=True,exist_ok=False)
 for name,source in HELPER_SOURCES.items():(args.emit_helper_sources/name).write_text(source)
 print(args.emit_helper_sources);raise SystemExit(0)
if not all((args.media,args.output,args.xvfb)):p.error('--media, --output and --xvfb are required for execution.')
if args.config_editor and (args.mode!='c' or args.repeat not in (2,3)):p.error('Config proof requires /c with repeat2(save/read) or3(save/cancel/read).')
if not 1<=args.first_delay<=10 or not 1<=args.second_delay<=10:p.error('Capture delays must each be1..10seconds.')
try:viewport_width,viewport_height=map(int,args.size.split('x'))
except ValueError:p.error('Use WIDTHxHEIGHT for the owned viewport.')
if not 320<=viewport_width<=4096 or not 200<=viewport_height<=2160:p.error('Owned viewport out of bounds.')
checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
helper_sha256={name:hashlib.sha256(path.read_bytes()).hexdigest()for name,path in (('preview',args.preview_host),('background',args.background_host),('config',args.config_editor))if path is not None}
media=args.media.resolve();assert media.is_dir();args.output.mkdir(parents=True,exist_ok=False)
if shutil.disk_usage(tempfile.gettempdir()).free<1024**3:p.error('At least1GiB free is required for a disposable Wine prefix.')
root=Path(tempfile.mkdtemp(prefix='w95uat-saver-compat-'));out=args.output.resolve()
r,w=os.pipe();server=subprocess.Popen([str(args.xvfb.resolve()),'-displayfd',str(w),'-screen','0',args.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
atexit.register(lambda:server.terminate() if server.poll() is None else None)
assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();assert display!=':0';assert server.poll()is None;os.close(r)
os.environ['DISPLAY']=display
base={**os.environ,'DISPLAY':display,'WINEPREFIX':str(root/'prefix'),'WINEARCH':'win32','WINEDEBUG':'-all','WINEDLLOVERRIDES':'winemenubuilder.exe=d;mscoree,mshtml='};results=[]
try:
 prefix_started=time.monotonic()
 with (out/'wineboot.log').open('w')as log:subprocess.run(['wineboot','-u'],env=base,stdout=log,stderr=log,check=True,timeout=45)
 prefix_seconds=time.monotonic()-prefix_started
 if args.classic_fonts or args.classic_colors or args.maze_win95 or args.debug_profile=='relay':
  lines=['Windows Registry Editor Version 5.00','']
  if args.classic_fonts:
   fonts=root/'prefix/drive_c/windows/Fonts'
   if fonts.is_symlink() or not fonts.resolve().is_relative_to((root/'prefix').resolve()):raise ValueError('Unsafe prefix font folder.')
   fonts.mkdir(parents=True,exist_ok=True)
   for filename in ('sserife.fon','vgasys.fon'):
    source=args.classic_fonts/filename
    if not source.is_file():raise ValueError('Original bitmap font is missing: '+filename)
    destination_font=fonts/filename
    if destination_font.is_symlink():raise ValueError('Refusing a linked prefix font.')
    shutil.copy2(source,destination_font)
   lines+=['[HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts]','"MS Sans Serif (Win95 original)"="sserife.fon"','"System (Win95 original)"="vgasys.fon"','', '[HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows NT\\CurrentVersion\\FontSubstitutes]','"MS Shell Dlg"="MS Sans Serif"','"MS Shell Dlg 2"="MS Sans Serif"','']
  if args.classic_colors:
   lines+=['[HKEY_CURRENT_USER\\Control Panel\\Colors]']
   for role,value in {'ActiveTitle':'0 0 128','InactiveTitle':'128 128 128','TitleText':'255 255 255','ButtonFace':'192 192 192','ButtonText':'0 0 0','ButtonHilight':'255 255 255','ButtonShadow':'128 128 128','ButtonDkShadow':'0 0 0','ButtonLight':'192 192 192','Window':'255 255 255','WindowText':'0 0 0','Menu':'192 192 192','MenuText':'0 0 0','GrayText':'128 128 128','Hilight':'0 0 128','HilightText':'255 255 255'}.items():lines.append('"'+role+'"="'+value+'"')
  if args.maze_win95:lines+=['[HKEY_CURRENT_USER\\Software\\Wine\\AppDefaults\\ssmaze.scr]','"Version"="win95"','']
  if args.debug_profile=='relay':lines+=['[HKEY_CURRENT_USER\\Software\\Wine\\Debug]','"RelayInclude"="gdi32.ChoosePixelFormat;gdi32.SetPixelFormat;gdi32.DescribePixelFormat;gdi32.CreateDIBSection;opengl32.wglCreateContext;opengl32.wglMakeCurrent;kernel32.GetLastError;kernel32.GetVersion"','']
  registry=root/'classic-appearance.reg';registry.write_text('\n'.join(lines)+'\n',encoding='utf-16')
  with(out/'appearance-setup.log').open('w')as log:
   subprocess.run(['wine','regedit','/S',str(registry)],env=base,stdout=log,stderr=log,check=True,timeout=20)
   subprocess.run(['wineserver','-k'],env=base,stdout=log,stderr=log,timeout=5)

 import gi;gi.require_version('Gdk','3.0');from gi.repository import Gdk
 assert server.poll()is None,'Owned X server exited.'
 owned=Gdk.Display.open(display)
 if owned is None:raise RuntimeError('Cannot open owned display '+repr(display))
 Gdk.DisplayManager.get().set_default_display(owned)
 def capture(name):
  Gdk.Display.get_default().sync();pix=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),0,0,viewport_width,viewport_height);pix.savev(str(out/(name+'.png')),'png',[],[])
  data=bytes(pix.get_pixels());channels=pix.get_n_channels();stride=pix.get_rowstride();rgb=[data[y*stride+x*channels:y*stride+x*channels+3]for y in range(viewport_height)for x in range(viewport_width)]
  import hashlib
  return {'pixel_sha256':hashlib.sha256(data).hexdigest(),'nonblack_pixels':sum(p!=b'\0\0\0'for p in rgb),'unique_colors':len(set(rgb))}
 x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(display.encode());x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p];xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
 themes={'dangerous':('Dangerous Creatures','DANGEROU.DLL'),'davinci':('Leonardo da Vinci','DAVINCI.DLL'),'modern':('The Golden Era','MODERNE.DLL'),'sports':('Sports','SPORTS.DLL'),'mystery':('Mystery','MYSTERY.DLL'),'pcinside':('Inside your Computer','PCINSIDE.DLL'),'travel':('Travel','TRAVEL.DLL')}
 cases={'nature-missing':'Nature.scr','nature-wrong-alias':'Nature.scr','nature-complete':'Nature.scr','stars':'ssstars.scr','blocks':'BLOCKS.SCR','lens':'LENS.SCR','mystify':'ssmyst.scr'}
 aliases={'windows95':('Windows 95.scr','BLOCKS.SCR'),'science':('Science.scr','LENS.SCR'),'sixties':("The 60's USA.scr",'LENS.SCR')}
 cases.update({'pipes':'sspipes.scr','text3d':'sstext3d.scr','maze':'ssmaze.scr','flyingobjects':'ss3dfo.scr','flowerbox':'ssflwbox.scr','bezier':'bezier.scr','flywin':'ssflywin.scr','marquee':'ssmarque.scr','blank':'scrnsave.scr'})
 cases.update({key:installed for key,(installed,_)in aliases.items()})
 cases.update({key:alias+'.scr'for key,(alias,_)in themes.items()})
 for name,iteration in ((name,i)for name in args.cases.split(',')for i in range(args.repeat)):
  if args.config_editor and name not in themes and name not in ('nature-complete','lens','blocks','windows95','science','sixties','pipes','text3d','maze'):raise ValueError('Config checkbox proof is limited to original Plus shared-engine aliases.')
  label=name+'-repeat'+str(iteration+1) if args.repeat>1 else name
  if name not in cases:raise ValueError('Unknown bounded probe case.')
  file=cases[name];folder=root/label;folder.mkdir()
  if name.startswith('nature'):
   shutil.copy2(media/'WL32SCR.EXE',folder/file);shutil.copy2(media/'NATURE.DLL',folder/'Nature.dll');shutil.copy2(media/'WILDLB32.DLL',folder/'WILDLB32.DLL')
   if name=='nature-wrong-alias':shutil.copy2(media/'NATURE.DLL',folder/'WL32DLL.DLL')
   if name=='nature-complete':shutil.copy2(media/'WL32DLL.DLL',folder/'WL32DLL.DLL')
  elif name in themes:
   alias,library=themes[name];shutil.copy2(media/'WL32SCR.EXE',folder/file);shutil.copy2(media/library,folder/(alias+'.dll'))
   for shared in ('WL32DLL.DLL','WILDLB32.DLL'):shutil.copy2(media/shared,folder/shared)
  elif name in aliases:shutil.copy2(media/aliases[name][1],folder/file)
  else:shutil.copy2(media/file,folder/file)
  xt.XTestFakeMotionEvent(d,-1,400,300,0);x.XFlush(d);time.sleep(.2)
  env={**base,'WINEDEBUG':{'load':'-all,+loaddll','wgl':'-all,err+all,+wgl','font':'-all,err+all,+font','relay':'-all,err+all,+relay,+wgl,+dib'}[args.debug_profile]}
  with(out/(label+'.log')).open('w')as log:
   host=None;background=None;command=['wine',str(folder/file),'/'+args.mode]
   if args.background_host is not None and args.mode=='s':
    ready=root/'prefix/drive_c/background-ready';background_close=root/'prefix/drive_c/background-close';ready.unlink(missing_ok=True);background_close.unlink(missing_ok=True)
    background=subprocess.Popen(['wine',str(args.background_host.resolve())],env=env,stdout=log,stderr=log)
    deadline=time.monotonic()+8
    while not ready.exists() and time.monotonic()<deadline:time.sleep(.05)
    if not ready.exists():raise RuntimeError('Owned patterned Win32 background did not initialize.')
    capture(label+'-background')
   if args.mode=='p':
    if args.preview_host is None:raise ValueError('Preview requires the owned Win32 helper executable.')
    handlefile=root/'prefix/drive_c/preview-hwnd.txt';closefile=root/'prefix/drive_c/preview-close';handlefile.unlink(missing_ok=True);closefile.unlink(missing_ok=True)
    host=subprocess.Popen(['wine',str(args.preview_host.resolve())],env=env,stdout=log,stderr=log)
    deadline=time.monotonic()+8
    while not handlefile.exists() and time.monotonic()<deadline:time.sleep(.05)
    if not handlefile.exists():raise RuntimeError('Owned Win32 preview host did not publish HWND.')
    handle=handlefile.read_text().strip();assert handle.isdecimal();command.append(handle);capture(label+'-preview-host')
   config_state=None
   if args.config_editor:
    marker=root/'prefix/drive_c/config-read-only';marker.unlink(missing_ok=True)
    for target in ('lens','wallpaper','pipes','text3d','maze'):(root/('prefix/drive_c/config-target-'+target)).unlink(missing_ok=True)
    if name in ('lens','blocks','windows95','science','sixties'):(root/('prefix/drive_c/config-target-'+('lens' if name in ('lens','science','sixties') else 'wallpaper'))).write_text('native parameter target')
    if name in ('pipes','text3d','maze'):(root/('prefix/drive_c/config-target-'+name)).write_text('stock3D radio target')
    cancel_marker=root/'prefix/drive_c/config-cancel-change';cancel_marker.unlink(missing_ok=True)
    if iteration==args.repeat-1:marker.write_text('read only')
    elif iteration==1:cancel_marker.write_text('cancel pending modification')
   start=time.monotonic();p=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=log)
   time.sleep(args.first_delay);first=capture(label+f'-{args.first_delay:g}s');time.sleep(args.second_delay);last=capture(label+f'-{args.first_delay+args.second_delay:g}s');alive=p.poll()is None
   if args.mode=='s' and args.dismiss=='mouse':xt.XTestFakeMotionEvent(d,-1,30,30,0)
   if args.config_editor:
    subprocess.run(['wine',str(args.config_editor.resolve())],env=env,stdout=log,stderr=log,check=True,timeout=8)
    config_state=(root/'prefix/drive_c/config-state.txt').read_text()
   elif args.mode=='c' or args.mode=='s' and args.dismiss=='keyboard':
    x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
    xt.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    code=x.XKeysymToKeycode(d,0xff1b);xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0)
   x.XFlush(d)
   if args.mode=='p':closefile.write_text('close')
   try:code=p.wait(timeout=5);dismissed=True
   except subprocess.TimeoutExpired:p.terminate();code=p.wait(timeout=4);dismissed=False
   post_save=None
   if args.config_editor and args.post_save_launch and iteration==0:
    xt.XTestFakeMotionEvent(d,-1,400,300,0);x.XFlush(d)
    trial=subprocess.Popen(['wine',str(folder/file),'/s'],cwd=folder,env=env,stdout=log,stderr=log)
    time.sleep(3);post_save=capture(label+'-post-save-fullscreen');post_save['alive']=trial.poll()is None
    xt.XTestFakeMotionEvent(d,-1,30,30,0);x.XFlush(d)
    try:post_save['exit']=trial.wait(timeout=5);post_save['dismissed']=True
    except subprocess.TimeoutExpired:trial.terminate();trial.wait(timeout=3);post_save['dismissed']=False
   results.append({'name':name,'iteration':iteration+1,'folder':str(folder),'installed_files':{item.name:hashlib.sha256(item.read_bytes()).hexdigest()for item in folder.iterdir()if item.is_file()},'frame3':first,'frame7':last,'frame_changed':first['pixel_sha256']!=last['pixel_sha256'],'alive7':alive,'config_parameter':('Maze Overlay' if name=='maze' else 'Multiple pipes radio' if name=='pipes' else 'Time radio' if name=='text3d' else 'Black Hole radio' if name in ('lens','science','sixties') else 'Use Wallpaper' if name in ('blocks','windows95') else 'Mute Sound') if args.config_editor else None,'config_state_before_after':config_state,'post_save_launch':post_save,'dismissal_input':('Win32 control then OK' if iteration==0 else 'Win32 read then Cancel' if iteration==args.repeat-1 else 'Win32 control then Cancel') if args.config_editor else args.dismiss if args.mode=='s' else 'parent-destroy' if args.mode=='p' else 'Escape','dismissed':dismissed,'exit':code,'elapsed':time.monotonic()-start})
  if background is not None:
   background_close.write_text('close')
   try:background.wait(timeout=3)
   except subprocess.TimeoutExpired:background.terminate();background.wait(timeout=3)
  if host is not None:
   try:host.wait(timeout=3)
   except subprocess.TimeoutExpired:host.terminate();host.wait(timeout=3)
  time.sleep(.3)
 if args.config_editor:
  for name in args.cases.split(','):
   group=[r for r in results if r['name']==name];before,after=map(int,group[0]['config_state_before_after'].split());assert after==1-before
   assert group[-1]['config_state_before_after']==f'{after} {after}','Saved native setting did not persist on reopen.'
   if args.repeat==3:assert group[1]['config_state_before_after']==f'{after} {before}','Cancel modification did not pass through the checkbox handler.'
   if args.post_save_launch:
    launched=group[0]['post_save_launch'];assert launched['alive'] and launched['dismissed'] and launched['nonblack_pixels']>0,'Post-save saver launch failed.'
 (out/'report.json').write_text(json.dumps({'root':str(root),'viewport':[viewport_width,viewport_height],'checker_sha256':checker_sha256,'helper_sha256':helper_sha256,'wine_version':subprocess.check_output(['wine','--version'],env=base,text=True).strip(),'prefix_init_seconds':prefix_seconds,'maze_win95':args.maze_win95,'classic_font_sha256':{name:hashlib.sha256((args.classic_fonts/name).read_bytes()).hexdigest()for name in ('sserife.fon','vgasys.fon')}if args.classic_fonts else {},'classic_fonts':bool(args.classic_fonts),'classic_colors':args.classic_colors,'debug_profile':args.debug_profile,'capture_delays':[args.first_delay,args.second_delay],'mode':args.mode,'display':display,'server_pid':server.pid,'results':results},indent=2)+'\n');print((out/'report.json').read_text())
finally:
 subprocess.run(['wineserver','-k'],env=base,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5);subprocess.run(['wineserver','-w'],env=base,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5);server.terminate();server.wait(timeout=5)
 registry_archive=out/'prefix-registry.tar.gz';archive_error=None
 try:
  with tarfile.open(registry_archive,'w:gz')as archive:
   for pattern in ('prefix/*.reg','prefix/drive_c/windows/*.ini'):
    for file in root.glob(pattern):
     if file.is_file()and not file.is_symlink()and file.resolve().is_relative_to(root):archive.add(file,arcname=str(file.relative_to(root)),recursive=False)
 except OSError as error:archive_error=str(error)
 if not args.keep_prefix:shutil.rmtree(root)
 (out/'cleanup.json').write_text(json.dumps({'owned_xvfb_returncode':server.returncode,'owned_wineserver_wait_returned':True,'prefix_removed':not args.keep_prefix,'registry_archive_error':archive_error,'registry_archive_sha256':hashlib.sha256(registry_archive.read_bytes()).hexdigest()if archive_error is None else None})+'\n')
