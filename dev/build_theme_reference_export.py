#!/usr/bin/env python3
"""Build the private native Plus theme-conversion exporter; never run a VM.

Open Desktop Themes in an owned, checkpointed original reference first. The
probe applies its theme choices and copies original generated wallpapers into
C:\\W95THM2, refusing a preexisting output directory. Run it only in that
reference, collect CATALOG.TXT/BMPs from an offline export, then restore and verify
the checkpoint. It does not modify source media, vendor code, or the host.
"""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from stage_command_button_assets import build_harness

NATIVE_SOURCE = r"""#include <windows.h>
static HWND combo,apply;static char logbuf[6000];static unsigned used;
static void text(const char*s){while(*s&&used<5800)logbuf[used++]=*s++;}
static void number(unsigned n){char b[20];unsigned k=0;do{b[k++]=(char)('0'+n%10);n/=10;}while(n);while(k)logbuf[used++]=b[--k];}
static int equal(const char*a,const char*b){while(*a||*b){if(*a=='&'){a++;continue;}char x=*a,y=*b;if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;a++;b++;}return 1;}
static BOOL CALLBACK child(HWND window,LPARAM unused){char cls[128],label[256];(void)unused;GetClassNameA(window,cls,sizeof(cls));GetWindowTextA(window,label,sizeof(label));if(equal(cls,"ComboBox"))combo=window;if(equal(cls,"Button")&&equal(label,"Apply"))apply=window;return TRUE;}
void entry(void){HWND target=FindWindowA(0,"Desktop Themes");if(!target)ExitProcess(2);EnumChildWindows(target,child,0);if(!combo||!apply)ExitProcess(3);SetForegroundWindow(target);if(!CreateDirectoryA("C:\\W95THM2",0))ExitProcess(5);HDC dc=GetDC(0);text("bits=");number(GetDeviceCaps(dc,BITSPIXEL));text(" width=");number(GetDeviceCaps(dc,HORZRES));text(" height=");number(GetDeviceCaps(dc,VERTRES));text("\r\n");ReleaseDC(0,dc);
HMODULE lib=LoadLibraryA("advapi32.dll");typedef LONG (WINAPI *Open)(HKEY,LPCSTR,DWORD,REGSAM,PHKEY);typedef LONG(WINAPI *Query)(HKEY,LPCSTR,LPDWORD,LPDWORD,LPBYTE,LPDWORD);Open open=(Open)GetProcAddress(lib,"RegOpenKeyExA");Query query=(Query)GetProcAddress(lib,"RegQueryValueExA");HKEY key;if(open(HKEY_CURRENT_USER,"Control Panel\\Desktop",0,KEY_QUERY_VALUE,&key))ExitProcess(4);
unsigned count=(unsigned)SendMessageA(combo,CB_GETCOUNT,0,0);for(unsigned i=1;i<count;i++){char label[256],path[1024];SendMessageA(combo,CB_GETLBTEXT,i,(LPARAM)label);SendMessageA(combo,CB_SETCURSEL,i,0);SendMessageA(GetParent(combo),WM_COMMAND,MAKEWPARAM(GetDlgCtrlID(combo),CBN_SELCHANGE),(LPARAM)combo);SendMessageA(GetParent(combo),WM_COMMAND,MAKEWPARAM(GetDlgCtrlID(combo),CBN_SELENDOK),(LPARAM)combo);Sleep(400);SendMessageA(apply,BM_CLICK,0,0);Sleep(1000);DWORD size=sizeof(path);LONG status=query(key,"Wallpaper",0,0,(LPBYTE)path,&size);char dest[]="C:\\W95THM2\\T00.BMP";dest[12]=(char)('0'+i/10);dest[13]=(char)('0'+i%10);BOOL copied=status?FALSE:CopyFileA(path,dest,TRUE);if(copied){HANDLE f=CreateFileA(dest,GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ,0,OPEN_EXISTING,0,0);FlushFileBuffers(f);CloseHandle(f);}number(i);text("\t");text(label);text("\t");text(path);text("\t");text(dest);text("\t");number(copied?1:0);text("\r\n");}
DWORD n;HANDLE f=CreateFileA("C:\\W95THM2\\CATALOG.TXT",GENERIC_WRITE,0,0,CREATE_NEW,0,0);WriteFile(f,logbuf,used,&n,0);FlushFileBuffers(f);CloseHandle(f);f=CreateFileA("A:\\DONE.TXT",GENERIC_WRITE,0,0,CREATE_ALWAYS,0,0);WriteFile(f,logbuf,used,&n,0);FlushFileBuffers(f);CloseHandle(f);ExitProcess(0);}
"""

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if ROOT/'private' not in args.output.resolve().parents:
        parser.error('Generated native tools must remain project-private.')
    build_harness(args.output,NATIVE_SOURCE)

if __name__=='__main__':main()
