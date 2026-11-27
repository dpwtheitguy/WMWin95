"""Native Printers namespace research/staging; not registered in asset build yet."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]

def build_probe(output):
    # Reuse the independently reviewed Win32 metadata/GDI code, not its CPL
    # alias table or page assumptions. The generated binary remains private.
    from stage_command_button_assets import build_harness
    original=(ROOT/'tools/native/w95probe.c').read_text();prefix=original[:original.index('struct Applet')]
    prefix='\n'.join(line for line in prefix.splitlines()if not line.startswith('static unsigned length('))+'\n'
    prefix=prefix.replace('GetWindowTextA(window,text,sizeof(text));','SendMessageA(window,WM_GETTEXT,sizeof(text),(LPARAM)text);')
    prefix=prefix.replace('add(",\\\"font\\\":");font(window);','add(",\\\"native_style\\\":");number(style);if(equal(name,"Button")){add(",\\\"button_state\\\":");number(SendMessageA(window,BM_GETSTATE,0,0));}add(",\\\"font\\\":");font(window);')
    source=prefix+r'''
static int has(const char *s,const char *needle){for(;*s;s++){const char*a=s,*b=needle;while(*a&&*a==*b){a++;b++;}if(!*b)return 1;}return 0;}
static HWND list_view;
static BOOL CALLBACK find_list(HWND window,LPARAM unused){char cls[128];(void)unused;GetClassNameA(window,cls,sizeof(cls));if(equal(cls,"SysListView32"))list_view=window;return TRUE;}
static void menu(HMENU item){
 add("[");int count=GetMenuItemCount(item);char text[512];
 for(int i=0;i<count;i++){if(i)add(",");GetMenuStringA(item,i,text,sizeof(text),MF_BYPOSITION);add("{\"label\":");quote(text);add(",\"id\":");number(GetMenuItemID(item,i));add(",\"flags\":");number(GetMenuState(item,i,MF_BYPOSITION));HMENU sub=GetSubMenu(item,i);if(sub){add(",\"items\":");menu(sub);}add("}");}add("]");
}
void entry(void){
 int wizard=has(GetCommandLineA(),"wizard");const char*caption=wizard?"Add Printer Wizard":has(GetCommandLineA(),"queue")?"w95uatreference":has(GetCommandLineA(),"props")?"w95uatreference Properties":"Printers";
 target=FindWindowA(0,caption);if(!target&&!wizard)WinExec("control printers",SW_SHOWNORMAL);
 for(unsigned i=0;i<100&&!target;i++){Sleep(100);target=FindWindowA(0,caption);}if(!target)ExitProcess(2);
 if(has(GetCommandLineA(),"activate")){EnumChildWindows(target,find_list,0);if(!list_view)ExitProcess(8);MSG message;PeekMessageA(&message,0,0,0,PM_NOREMOVE);DWORD thread=GetWindowThreadProcessId(list_view,0);AttachThreadInput(GetCurrentThreadId(),thread,TRUE);SetForegroundWindow(target);SetFocus(list_view);AttachThreadInput(GetCurrentThreadId(),thread,FALSE);PostMessageA(list_view,WM_KEYDOWN,VK_END,0);Sleep(200);PostMessageA(list_view,WM_KEYDOWN,VK_RETURN,0);Sleep(400);ExitProcess(0);}
 SetForegroundWindow(target);ShowWindow(target,SW_RESTORE);SetCursorPos(GetSystemMetrics(SM_CXSCREEN)-2,GetSystemMetrics(SM_CYSCREEN)-2);
 RedrawWindow(target,0,0,RDW_FRAME|RDW_ERASE|RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);Sleep(300);
 GetWindowRect(target,&window_rect);add("{\"title\":");quote(caption);add(",\"origin\":[");number(window_rect.left);add(",");number(window_rect.top);add("],\"size\":[");number(window_rect.right-window_rect.left);add(",");number(window_rect.bottom-window_rect.top);add("],\"controls\":[");first_control=1;EnumChildWindows(target,child,0);add("]");
 HMENU main=GetMenu(target);if(main){add(",\"menus\":");menu(main);}add("}");
 if(overflow||!save("A:\\PRINTERS.JSN",output,used))ExitProcess(3);ExitProcess(bitmap("A:\\PRINTERS.BMP")?0:4);
}
'''
    return build_harness(output,source)

def stage(output):
    """Only stage captures after native HWND metadata is present/reviewed."""
    from stage_command_button_assets import read_bmp
    from pixels import write
    source=ROOT/'private/reference-tools/printers-native-20261127/queue-real'
    metadata=json.loads((source/'PRINTERS.JSN').read_text())
    w,h,pixels=read_bmp(source/'PRINTERS.BMP')
    if metadata['size']!=[562,185] or (w,h)!=(562,185):raise ValueError('Printer queue HWND geometry changed.')
    if not any(c['class']=='SysHeader32' and c['rect']==[6,44,550,17] for c in metadata['controls']):raise ValueError('Printer queue header is unverified.')
    # Preserve measured frame/header chrome; queue title, rows and status are
    # rendered from current Linux data. No reference job/user data is shipped.
    for x,y,cw,ch,color in ((24,4,458,18,(0,0,128,255)),(6,61,550,100,(255,255,255,255)),(5,164,530,16,(192,192,192,255))):
        for yy in range(y,y+ch):pixels[yy*w+x:yy*w+x+cw]=[color]*cw
    output.mkdir(parents=True,exist_ok=True);name='printers-queue-frame.png';write(output/name,w,h,pixels)
    records=[{'source':str((source/'PRINTERS.BMP').relative_to(ROOT)),'type':'SCREEN_CAPTURE_CONTROL','profile':'plus-ie4','output':name,'dimensions':[w,h],'reference_sha256':hashlib.sha256((source/'PRINTERS.BMP').read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256((source/'PRINTERS.JSN').read_bytes()).hexdigest(),'scope':'Queue frame/header only; anomalous native Help branding excluded.'}]
    from resources import extract
    from win95lx.assets.bitmap import icon_dib,word
    library=ROOT/'private/cabsets/windows95/shell32.dll';resources=list(extract(library.read_bytes()))
    for ident,label in ((17,'printer'),(139,'printer-add'),(140,'printer-default')):
        group=next(d for k,j,l,d,f in resources if k==14 and j==ident)
        entries=[group[6+i*14:20+i*14]for i in range(word(group,4))]
        for size in (16,32):
            entry=next(e for e in entries if e[:2]==bytes((size,size)));image_id=word(entry,12)
            raw=next(d for k,j,l,d,f in resources if k==3 and j==image_id);iw,ih,icon=icon_dib(raw)
            dest=f'{label}-{size}.png';write(output/dest,iw,ih,icon)
            records.append({'source':'shell32.dll','type':'GROUP_ICON','id':ident,'image_id':image_id,'output':dest,'dimensions':[iw,ih],'source_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'scope':'Add32 matched native folder at177,178; printer16 matched queue at6,5; default icon is original resource, placement acceptance pending.'})
    folder=ROOT/'private/reference-tools/printers-native-20261127/folder'
    fw,fh,fp=read_bmp(folder/'PRINTERS.BMP')
    if (fw,fh)!=(512,461):raise ValueError('Printers folder dimensions changed.')
    for label,rect in (('web-computer',(8,122,84,84)),('web-heading',(114,140,120,24))):
        x,y,cw,ch=rect;dest='explorer-printers-'+label+'.png'
        write(output/dest,cw,ch,[fp[yy*fw+xx] for yy in range(y,y+ch) for xx in range(x,x+cw)])
        records.append({'source':str((folder/'PRINTERS.BMP').relative_to(ROOT)),'output':dest,'type':'SCREEN_CAPTURE_CONTROL','region':rect,'reference_sha256':hashlib.sha256((folder/'PRINTERS.BMP').read_bytes()).hexdigest()})
    for size in (16,32):
        data=(output/f'printer-{size}.png').read_bytes();(output/f'cpl-printers-{size}.png').write_bytes(data)
    return records

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--build-probe',type=Path);a=p.parse_args()
    if a.build_probe:
        if ROOT/'private'not in a.build_probe.resolve().parents:p.error('Generated reference tools must remain private.')
        print(build_probe(a.build_probe))
