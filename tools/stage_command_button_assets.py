"""Stage measured native command-button states and build their Win32 harness.

Only original Win32 BUTTON controls produce the reference pixels. Generated
Windows executables, source captures and original assets stay project-private.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

NATIVE_SOURCE=r'''
#define WINVER 0x0400
#define _WIN32_WINNT 0x0400
#define _WIN32_WINDOWS 0x0400
#include <windows.h>
static HWND owner,button;static HFONT font;static int width;
static char json[65536];static unsigned used;
static void add(const char *p){while(*p&&used<sizeof(json)-1)json[used++]=*p++;}
static void number(LONG value){char s[32];wsprintfA(s,"%ld",value);add(s);}
static int save(const char *path,const void *data,DWORD size){
 HANDLE file=CreateFileA(path,GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);DWORD written=0;
 if(file==INVALID_HANDLE_VALUE)return 0;int okay=WriteFile(file,data,size,&written,0)&&written==size;
 if(okay)okay=FlushFileBuffers(file);CloseHandle(file);return okay;
}
static void pump(void){MSG msg;DWORD until=GetTickCount()+50;do{
 while(PeekMessageA(&msg,0,0,0,PM_REMOVE)){TranslateMessage(&msg);DispatchMessageA(&msg);}Sleep(1);
 }while(GetTickCount()<until);}
static int bitmap(const char *path){
 LONG w=width+4,h=27;DWORD stride=(w*3+3)&~3,size=stride*h;HDC dc=GetWindowDC(owner),memory=CreateCompatibleDC(dc);
 HBITMAP image=CreateCompatibleBitmap(dc,w,h);HGDIOBJ old=SelectObject(memory,image);int okay=BitBlt(memory,0,0,w,h,dc,10,10,SRCCOPY);
 SelectObject(memory,old);BITMAPINFO info;unsigned char *clear=(unsigned char*)&info;for(unsigned i=0;i<sizeof(info);i++)clear[i]=0;
 info.bmiHeader.biSize=40;info.bmiHeader.biWidth=w;info.bmiHeader.biHeight=h;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=24;info.bmiHeader.biSizeImage=size;
 unsigned char *data=LocalAlloc(LMEM_FIXED,54+size);if(!data)okay=0;
 if(okay){BITMAPFILEHEADER *file=(BITMAPFILEHEADER*)data;file->bfType=0x4d42;file->bfSize=54+size;file->bfReserved1=file->bfReserved2=0;file->bfOffBits=54;
 for(unsigned i=0;i<40;i++)data[14+i]=((unsigned char*)&info.bmiHeader)[i];okay=GetDIBits(dc,image,0,h,data+54,&info,DIB_RGB_COLORS)==h;
 if(okay)okay=save(path,data,54+size);}
 if(data)LocalFree(data);DeleteObject(image);DeleteDC(memory);ReleaseDC(owner,dc);return okay;
}
struct State{const char *name;int def,focus,press,enabled;};
static const struct State states[]={
 {"normal",0,0,0,1},{"default",1,0,0,1},{"focused",0,1,0,1},{"focusdefault",1,1,0,1},
 {"pressed",0,0,1,1},{"pressfocus",1,1,1,1},{"disabled",0,0,0,0},{"disabledefault",1,0,0,0}};
static const char *labels[]={"OK","Cancel","&Apply","A&dd...","&Properties..."};
void entry(void){
 HINSTANCE instance=GetModuleHandleA(0);WNDCLASSA cls;unsigned char *clear=(unsigned char*)&cls;for(unsigned i=0;i<sizeof(cls);i++)clear[i]=0;
 cls.lpfnWndProc=DefWindowProcA;cls.hInstance=instance;cls.lpszClassName="Win95LXCommandReference";cls.hbrBackground=GetSysColorBrush(COLOR_BTNFACE);RegisterClassA(&cls);
 owner=CreateWindowExA(0,cls.lpszClassName,"Win95LX Command Button Reference",WS_POPUP|WS_VISIBLE,200,200,240,100,0,0,instance,0);
 if(!owner)ExitProcess(1);font=CreateFontA(-11,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,ANSI_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,DEFAULT_QUALITY,VARIABLE_PITCH|FF_SWISS,"MS Sans Serif");
 if(!font)ExitProcess(2);ShowWindow(owner,SW_SHOW);SetForegroundWindow(owner);SetCursorPos(GetSystemMetrics(SM_CXSCREEN)-2,GetSystemMetrics(SM_CYSCREEN)-2);
 CreateDirectoryA("C:\\W95BTNS",0);add("{\"schema\":1,\"font_points\":8,\"requested_height\":23,\"margin\":2,\"states\":[");int first=1;
 for(unsigned sz=0;sz<2;sz++){width=sz?108:75;
  for(unsigned label=0;label<sizeof(labels)/sizeof(labels[0]);label++){
   button=CreateWindowExA(0,"BUTTON",labels[label],WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_PUSHBUTTON,12,12,width,23,owner,(HMENU)100,instance,0);
   SendMessageA(button,WM_SETFONT,(WPARAM)font,TRUE);
   for(unsigned state=0;state<sizeof(states)/sizeof(states[0]);state++){
    const struct State *s=&states[state];EnableWindow(button,TRUE);SetFocus(owner);SendMessageA(button,BM_SETSTATE,FALSE,0);
    SendMessageA(button,BM_SETSTYLE,s->def?BS_DEFPUSHBUTTON:BS_PUSHBUTTON,TRUE);EnableWindow(button,s->enabled);
    if(s->focus)SetFocus(button);SendMessageA(button,BM_SETSTATE,s->press,0);
    RedrawWindow(owner,0,0,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);pump();
    char path[80];wsprintfA(path,"C:\\W95BTNS\\B%u%u%u.BMP",sz,label,state);int okay=bitmap(path);
    RECT rect;GetWindowRect(button,&rect);HDC dc=GetDC(button);HGDIOBJ old=SelectObject(dc,font);TEXTMETRICA metrics;GetTextMetricsA(dc,&metrics);SelectObject(dc,old);ReleaseDC(button,dc);
    if(!first)add(",");first=0;add("{\"size_index\":");number(sz);add(",\"label_index\":");number(label);add(",\"state_index\":");number(state);
    add(",\"width\":");number(rect.right-rect.left);add(",\"height\":");number(rect.bottom-rect.top);add(",\"bm_state\":");number(SendMessageA(button,BM_GETSTATE,0,0));
    add(",\"style\":");number(GetWindowLongA(button,GWL_STYLE));add(",\"font_height\":");number(metrics.tmHeight);add(",\"font_ascent\":");number(metrics.tmAscent);add(",\"saved\":");add(okay?"true":"false");add("}");
   }DestroyWindow(button);
  }
 }
 add("]}");int okay=save("C:\\W95BTNS\\STATES.JSN",json,used);DestroyWindow(owner);DeleteObject(font);ExitProcess(okay?0:3);
}
'''

def build_harness(output,source_code=None):
    output.mkdir(parents=True,exist_ok=False);source=output/'command-buttons.c';source.write_text(source_code or NATIVE_SOURCE)
    prefix=ROOT/'private/cross-tools/root';compiler=prefix/'usr/bin/i686-w64-mingw32-gcc-posix';target=output/'W95BTNS.EXE'
    env={**os.environ,'PATH':str(prefix/'usr/bin')+':'+os.environ['PATH'],'GCC_EXEC_PREFIX':str(prefix/'usr/lib/gcc')+'/'}
    subprocess.run([str(compiler),'-Os','-march=i386','-mtune=pentium','-mno-sse','-mno-sse2','-mno-mmx','-std=c99','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fno-builtin','-fno-stack-protector','-ffreestanding','-nostdlib',
        '-I'+str(prefix/'usr/i686-w64-mingw32/include'),'-L'+str(prefix/'usr/i686-w64-mingw32/lib'),'-Wl,--entry,_entry,--subsystem,windows,--major-subsystem-version,4,--minor-subsystem-version,0,--major-os-version,4,--minor-os-version,0,--no-insert-timestamp',str(source),'-o',str(target),'-lgdi32','-luser32','-lkernel32'],env=env,check=True)
    print(target)

LABELS=('OK','Cancel','&Apply','A&dd...','&Properties...')
STATE_NAMES=('normal','default','focused','focusdefault','pressed','pressfocus','disabled','disabledefault')

def read_bmp(path):
    import struct
    data=Path(path).read_bytes()
    if len(data)<54 or data[:2]!=b'BM':raise ValueError('Invalid native capture BMP.')
    offset=struct.unpack_from('<I',data,10)[0];header,width,height,planes,bits,compression=struct.unpack_from('<IiiHHI',data,14)
    if header!=40 or not 1<=width<=4096 or not 1<=abs(height)<=4096 or (planes,bits,compression)!=(1,24,0):raise ValueError('Unsupported native capture BMP.')
    stride=(width*3+3)&~3
    if offset<54 or offset+stride*abs(height)>len(data):raise ValueError('Truncated native capture BMP.')
    pixels=[]
    for y in range(abs(height)):
        row=abs(height)-1-y if height>0 else y
        for x in range(width):
            b,g,r=data[offset+row*stride+x*3:offset+row*stride+x*3+3];pixels.append((r,g,b,255))
    return width,abs(height),pixels

def stage(output):
    sys.path.insert(0,str(ROOT/'tools'));from pixels import write
    source=ROOT/'private/reference-tools/command-buttons-native/W95BTNS';manifest=source/'STATES.JSN';metadata=json.loads(manifest.read_text());rows=[];catalog=[]
    if len(metadata['states'])!=80 or any(not row['saved'] or row['font_height']!=13 for row in metadata['states']):raise ValueError('The native button matrix is incomplete or uses another font size.')
    output.mkdir(parents=True,exist_ok=True)
    for row in metadata['states']:
        size,label,state=row['size_index'],row['label_index'],row['state_index']
        if size not in (0,1) or not 0<=label<5 or not 0<=state<8:raise ValueError('Invalid native button index.')
        expected_focus=state in (2,3,5);expected_press=state in (4,5);expected_default=state in (1,3,5,7);expected_disabled=state in (6,7)
        if bool(row['bm_state']&8)!=expected_focus or bool(row['bm_state']&4)!=expected_press or bool(row['style']&1)!=expected_default or bool(row['style']&0x08000000)!=expected_disabled:raise ValueError('Native button state differs from its requested label.')
        original=source/f'B{size}{label}{state}.BMP';w,h,pixels=read_bmp(original)
        if (w,h)!=(row['width']+4,row['height']+4):raise ValueError('Button HWND bounds do not match the captured margins.')
        filename=f'command-button-{size}{label}{state}.png';write(output/filename,w,h,pixels)
        values={'raw_label':LABELS[label],'state':STATE_NAMES[state],'button_rect':[2,2,row['width'],row['height']],'font_height':row['font_height'],'bm_state':row['bm_state'],'native_style':row['style'],'file':filename,'png_sha256':hashlib.sha256((output/filename).read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
        catalog.append(values);rows.append({'source':str(original.relative_to(ROOT)),'type':'WIN32_BUTTON_CAPTURE','profile':'classic','output':filename,**values})
    from pixels import read
    cpl=(
      ('cpl-20261126/ie4-keyboard-add-focused.png',(132,120),(33,202,108,23),'A&dd...','focusdefault'),
      ('command-buttons-20261126/classic-keyboard-language-next-focus.png',(0,0),(147,202,108,23),'P&roperties','focusdefault'),
      ('command-buttons-20261126/classic-keyboard-language-next-focus.png',(0,0),(33,202,108,23),'A&dd...','normal'),
      ('command-buttons-20261126/classic-keyboard-language-next-focus.png',(0,0),(261,202,108,23),'Re&move','disabled'),
      ('command-buttons-20261126/classic-keyboard-language-next-focus.png',(0,0),(158,415,75,23),'OK','normal'),
      ('command-buttons-20261126/classic-keyboard-language-next-focus.png',(0,0),(261,236,108,23),'&Set as Default','disabled'),
      ('command-buttons-20261126/classic-keyboard-language-initial.png',(33,55),(177,133,75,23),'OK','focusdefault'),
      ('command-buttons-20261126/classic-keyboard-language-tab1.png',(33,55),(257,133,75,23),'Cancel','focusdefault'),
    )
    for index,(name,origin,rect,label,state) in enumerate(cpl):
        original=ROOT/'private/screenshots'/name;sw,sh,pixels=read(original);x,y=origin[0]+rect[0],origin[1]+rect[1];w,h=rect[2:]
        filename=f'command-button-cpl-{index}.png';write(output/filename,w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
        values={'raw_label':label,'state':state,'button_rect':[0,0,w,h],'file':filename,'png_sha256':hashlib.sha256((output/filename).read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
        catalog.append(values);rows.append({'source':str(original.relative_to(ROOT)),'type':'SCREEN_CAPTURE_CONTROL','rectangle':[x,y,w,h],'output':filename,**values})
    harness=ROOT/'private/reference-tools/command-buttons-v2/command-buttons.c';binary=harness.with_name('W95BTNS.EXE')
    data={'schema':1,'profile':'Windows 95 OSR2.5 classic; 800x600, 256 colors, 96 dpi','capture':'Original Win32 BUTTON controls, GetWindowDC/BitBlt/GetDIBits; 2 pixel parent-background margin',
          'harness_source_sha256':hashlib.sha256(harness.read_bytes()).hexdigest(),'harness_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'native_metadata_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'cases':catalog}
    (output/'command-button-references.json').write_text(json.dumps(data,indent=2)+'\n')
    rows.append({'source':str(manifest.relative_to(ROOT)),'type':'CONTROL_STATE_CATALOG','output':'command-button-references.json','source_sha256':data['native_metadata_sha256']})
    return rows


SPY_SOURCE=r'''
#define WINVER 0x0400
#define _WIN32_WINNT 0x0400
#include <windows.h>
static char data[65536];static unsigned used;static RECT owner_rect;static HWND add_button;static int first;
static void add(const char *p){while(*p&&used<sizeof(data)-1)data[used++]=*p++;}
static void number(LONG v){char s[32];wsprintfA(s,"%ld",v);add(s);}
static void quote(const char *p){static const char hex[]="0123456789abcdef";add("\"");for(unsigned i=0;p[i];i++){unsigned c=(unsigned char)p[i];if(c=='"'||c=='\\'){char s[3]={'\\',(char)c,0};add(s);}else if(c>=32&&c<127){char s[2]={(char)c,0};add(s);}else{char s[7]={'\\','u','0','0',hex[c>>4],hex[c&15],0};add(s);}}add("\"");}
static int save(const char *path){HANDLE f=CreateFileA(path,GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);DWORD n=0;if(f==INVALID_HANDLE_VALUE)return 0;int ok=WriteFile(f,data,used,&n,0)&&n==used;if(ok)ok=FlushFileBuffers(f);CloseHandle(f);return ok;}
static void pump(void){MSG m;while(PeekMessageA(&m,0,0,0,PM_REMOVE)){TranslateMessage(&m);DispatchMessageA(&m);}Sleep(20);}
static BOOL CALLBACK child(HWND window,LPARAM ignored){
 (void)ignored;char cls[80],text[512],normalized[512];GetClassNameA(window,cls,sizeof(cls));
 if(lstrcmpiA(cls,"Button"))return TRUE;GetWindowTextA(window,text,sizeof(text));unsigned at=0;
 for(unsigned i=0;text[i];i++)if(text[i]!='&')normalized[at++]=text[i];normalized[at]=0;if(!lstrcmpiA(normalized,"Add..."))add_button=window;
 if(!first)add(",");first=0;RECT r;GetWindowRect(window,&r);add("{\"id\":");number(GetDlgCtrlID(window));add(",\"text\":");quote(text);add(",\"rect\":[");number(r.left-owner_rect.left);add(",");number(r.top-owner_rect.top);add(",");number(r.right-r.left);add(",");number(r.bottom-r.top);add("],\"style\":");number(GetWindowLongA(window,GWL_STYLE));add(",\"state\":");number(SendMessageA(window,BM_GETSTATE,0,0));add(",\"enabled\":");add(IsWindowEnabled(window)?"true":"false");add(",\"visible\":");add(IsWindowVisible(window)?"true":"false");
 HFONT font=(HFONT)SendMessageA(window,WM_GETFONT,0,0);HDC dc=GetDC(window);HGDIOBJ old=SelectObject(dc,font?font:GetStockObject(SYSTEM_FONT));TEXTMETRICA tm;GetTextMetricsA(dc,&tm);GetTextFaceA(dc,sizeof(text),text);add(",\"font_face\":");quote(text);add(",\"font_height\":");number(tm.tmHeight);add(",\"ascent\":");number(tm.tmAscent);add(",\"external_leading\":");number(tm.tmExternalLeading);add("}");SelectObject(dc,old);ReleaseDC(window,dc);return TRUE;
}
static int dump(HWND window,const char *path){used=0;first=1;GetWindowRect(window,&owner_rect);add("{\"origin\":[");number(owner_rect.left);add(",");number(owner_rect.top);add("],\"size\":[");number(owner_rect.right-owner_rect.left);add(",");number(owner_rect.bottom-owner_rect.top);add("],\"buttons\":[");EnumChildWindows(window,child,0);add("]}");return save(path);}
void entry(void){HWND keyboard=FindWindowA(0,"Keyboard Properties");if(!keyboard){WinExec("control keyboard",SW_SHOWNORMAL);for(unsigned i=0;i<150&&!keyboard;i++){pump();keyboard=FindWindowA(0,"Keyboard Properties");}}if(!keyboard)ExitProcess(1);
 SetForegroundWindow(keyboard);SendMessageA(keyboard,WM_USER+101,1,0);for(unsigned i=0;i<10;i++)pump();int ok=dump(keyboard,"A:\\KEYBOARD.JSN");
 if(add_button){PostMessageA(add_button,BM_CLICK,0,0);HWND dialog=0;for(unsigned i=0;i<150&&!dialog;i++){pump();dialog=FindWindowA(0,"Add Language");}if(dialog){ok=ok&&dump(dialog,"A:\\ADDLANG.JSN");PostMessageA(dialog,WM_COMMAND,IDCANCEL,0);}}
 ExitProcess(ok?0:2);
}
'''


SOUNDS_SPY_SOURCE=SPY_SOURCE
SOUNDS_SPY_SOURCE=SOUNDS_SPY_SOURCE.replace('if(lstrcmpiA(cls,"Button"))return TRUE;GetWindowTextA', 'GetWindowTextA')
SOUNDS_SPY_SOURCE=SOUNDS_SPY_SOURCE.replace('add("{\\\"id\\\":");', 'add("{\\\"class\\\":");quote(cls);add(",\\\"id\\\":");')
# Inject client and formatting bounds before the font fields, keeping native
# RECT coordinates rather than deriving them from a painted bevel.
SOUNDS_SPY_SOURCE=SOUNDS_SPY_SOURCE.replace('HFONT font=', r'''
 RECT client;GetClientRect(window,&client);POINT zero={0,0};ClientToScreen(window,&zero);add(",\"client_rect\":[");number(client.left);add(",");number(client.top);add(",");number(client.right);add(",");number(client.bottom);add("],\"client_origin\":[");number(zero.x-owner_rect.left);add(",");number(zero.y-owner_rect.top);add("]");
 if(!lstrcmpiA(cls,"Edit")){RECT edit;SendMessageA(window,EM_GETRECT,0,(LPARAM)&edit);add(",\"format_rect\":[");number(edit.left);add(",");number(edit.top);add(",");number(edit.right);add(",");number(edit.bottom);add("]");}
 if(!lstrcmpiA(cls,"ComboBox")){LONG type=GetWindowLongA(window,GWL_STYLE)&3;add(",\"combo_type\":");number(type);add(",\"selection\":");number(SendMessageA(window,CB_GETCURSEL,0,0));add(",\"field_item_height\":");number(SendMessageA(window,CB_GETITEMHEIGHT,(WPARAM)-1,0));add(",\"items\":[");LRESULT count=SendMessageA(window,CB_GETCOUNT,0,0);for(LRESULT i=0;i<count;i++){if(i)add(",");SendMessageA(window,CB_GETLBTEXT,i,(LPARAM)text);quote(text);}add("]");if(r.top-owner_rect.top>300&&r.right-r.left>250)add_button=window;}
 HFONT font=
''')
SOUNDS_SPY_SOURCE=SOUNDS_SPY_SOURCE.replace('\\\"buttons\\\"','\\\"controls\\\"')
SOUNDS_SPY_SOURCE=SOUNDS_SPY_SOURCE[:SOUNDS_SPY_SOURCE.index('void entry(void)')]+r'''
void entry(void){HWND window=FindWindowA(0,"Sounds Properties");if(!window){WinExec("control mmsys.cpl @1",SW_SHOWNORMAL);for(unsigned i=0;i<250&&!window;i++){pump();window=FindWindowA(0,"Sounds Properties");}}if(!window)ExitProcess(1);SetForegroundWindow(window);for(unsigned i=0;i<10;i++)pump();int ok=dump(window,"A:\\SOUNDS.JSN");
 if(add_button){LRESULT index=SendMessageA(add_button,CB_FINDSTRINGEXACT,(WPARAM)-1,(LPARAM)"Windows Default");if(index==CB_ERR)index=1;if(index!=CB_ERR){SendMessageA(add_button,CB_SETCURSEL,index,0);SendMessageA(GetParent(add_button),WM_COMMAND,MAKEWPARAM(GetDlgCtrlID(add_button),CBN_SELCHANGE),(LPARAM)add_button);for(unsigned i=0;i<10;i++)pump();ok=ok&&dump(window,"A:\\SNDSEL.JSN");}}
 SetCursorPos(GetSystemMetrics(SM_CXSCREEN)-2,GetSystemMetrics(SM_CYSCREEN)-2);ExitProcess(ok?0:2);}
'''

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--build-harness',type=Path);p.add_argument('--build-spy',type=Path);p.add_argument('--build-sounds-spy',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.build_harness:
        if not a.build_harness.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Native harness files belong under private/.')
        build_harness(a.build_harness)
    elif a.build_spy:
        if not a.build_spy.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Native spy files belong under private/.')
        build_harness(a.build_spy,SPY_SOURCE)
    elif a.build_sounds_spy:
        if not a.build_sounds_spy.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Native spy files belong under private/.')
        build_harness(a.build_sounds_spy,SOUNDS_SPY_SOURCE)
    elif a.output:
        if not a.output.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Original captures belong under private/.')
        print(json.dumps({'records':len(stage(a.output))}))
    else:p.error('Choose --build-harness or --output.')
