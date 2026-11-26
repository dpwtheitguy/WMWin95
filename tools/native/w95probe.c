/* Win95LX reference probe. Original Win32 APIs only; no C runtime dependency.
 * Reads native control geometry/state and captures the selected property sheet.
 * Output stays on the reference VM's C: drive. It never changes a setting.
 */
#define WINVER 0x0400
#define _WIN32_WINNT 0x0400
#define _WIN32_WINDOWS 0x0400
#include <windows.h>

static char output[262144];
static unsigned used;static int overflow,first_control;
static HWND target;static RECT window_rect;

static unsigned length(const char *s){unsigned n=0;while(s[n])n++;return n;}
static int equal(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static void add(const char *s){while(*s){if(used+1<sizeof(output))output[used++]=*s;else overflow=1;s++;}}
static void number(LONG value){char text[32];wsprintfA(text,"%ld",value);add(text);}
static void quote(const char *s){
    static const char hex[]="0123456789abcdef";
    static const WORD cp1252[32]={0x20ac,0x81,0x201a,0x192,0x201e,0x2026,0x2020,0x2021,0x2c6,0x2030,0x160,0x2039,0x152,0x8d,0x17d,0x8f,0x90,0x2018,0x2019,0x201c,0x201d,0x2022,0x2013,0x2014,0x2dc,0x2122,0x161,0x203a,0x153,0x9d,0x17e,0x178};
    add("\"");
    for(unsigned i=0;s[i];i++){
        unsigned c=(unsigned char)s[i];
        if(c=='"')add("\\\"");else if(c=='\\')add("\\\\");
        else if(c>=32&&c<127){char single[2]={(char)c,0};add(single);}
        else{if(c>=128&&c<160)c=cp1252[c-128];char escaped[7]={'\\','u',hex[c>>12&15],hex[c>>8&15],hex[c>>4&15],hex[c&15],0};add(escaped);}
    }
    add("\"");
}
static void rect(const RECT *r){add("[");number(r->left-window_rect.left);add(",");number(r->top-window_rect.top);add(",");number(r->right-r->left);add(",");number(r->bottom-r->top);add("]");}
static void font(HWND window){
    HDC dc=GetDC(window);HFONT hf=(HFONT)SendMessageA(window,WM_GETFONT,0,0);
    HGDIOBJ previous=SelectObject(dc,hf?hf:GetStockObject(SYSTEM_FONT));TEXTMETRICA metrics;LOGFONTA lf;SIZE extent;
    GetTextMetricsA(dc,&metrics);GetTextExtentPoint32A(dc,"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",52,&extent);
    add("{\"height\":");number(metrics.tmHeight);add(",\"ascent\":");number(metrics.tmAscent);add(",\"descent\":");number(metrics.tmDescent);
    add(",\"internal_leading\":");number(metrics.tmInternalLeading);add(",\"average_width\":");number(metrics.tmAveCharWidth);
    add(",\"dialog_base_x\":");number((extent.cx/26+1)/2);add(",\"weight\":");number(metrics.tmWeight);
    if(hf&&GetObjectA(hf,sizeof(lf),&lf)){add(",\"face\":");quote(lf.lfFaceName);}
    add("}");SelectObject(dc,previous);ReleaseDC(window,dc);
}
static BOOL CALLBACK child(HWND window,LPARAM unused){
    char name[128],text[512];RECT bounds;LONG style=GetWindowLongA(window,GWL_STYLE);
    (void)unused;GetClassNameA(window,name,sizeof(name));GetWindowTextA(window,text,sizeof(text));GetWindowRect(window,&bounds);
    if(!first_control)add(",");
    first_control=0;
    add("{\"id\":");number(GetDlgCtrlID(window));add(",\"class\":");quote(name);add(",\"text\":");
    /* Original System Properties can contain the owner's OEM license. */
    int private_text=0;
    for(unsigned i=0;text[i];i++)if(text[i]=='O'&&text[i+1]=='E'&&text[i+2]=='M')private_text=1;
    quote(private_text?"[private license]":text);
    add(",\"rect\":");rect(&bounds);add(",\"enabled\":");add(IsWindowEnabled(window)?"true":"false");
    add(",\"visible\":");add(IsWindowVisible(window)?"true":"false");add(",\"tab_stop\":");add(style&WS_TABSTOP?"true":"false");
    add(",\"font\":");font(window);
    if(equal(name,"msctls_trackbar32")){
        add(",\"range_min\":");number((LONG)SendMessageA(window,WM_USER+1,0,0));
        add(",\"range_max\":");number((LONG)SendMessageA(window,WM_USER+2,0,0));
        add(",\"position\":");number((LONG)SendMessageA(window,WM_USER,0,0));
    }
    if(equal(name,"ComboBox")){
        LONG count=(LONG)SendMessageA(window,CB_GETCOUNT,0,0);
        add(",\"selection\":");number((LONG)SendMessageA(window,CB_GETCURSEL,0,0));add(",\"choices\":[");
        if((style&CBS_HASSTRINGS)||!(style&(CBS_OWNERDRAWFIXED|CBS_OWNERDRAWVARIABLE))){
            int first=1;
            for(LONG i=0;i<count&&i<256;i++){
                LONG size=(LONG)SendMessageA(window,CB_GETLBTEXTLEN,i,0);
                if(size>=0&&size<511){SendMessageA(window,CB_GETLBTEXT,i,(LPARAM)text);if(!first)add(",");first=0;quote(text);}
            }
        }
        add("]");
    }
    add("}");return !overflow;
}
static int save(const char *path,const void *data,DWORD size){
    HANDLE file=CreateFileA(path,GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);DWORD written=0;
    if(file==INVALID_HANDLE_VALUE)return 0;
    int okay=WriteFile(file,data,size,&written,0)&&written==size;
    if(okay)okay=FlushFileBuffers(file);
    CloseHandle(file);return okay;
}
static int bitmap(const char *path){
    LONG width=window_rect.right-window_rect.left,height=window_rect.bottom-window_rect.top;
    if(width<=0||height<=0||width>4096||height>4096)return 0;
    DWORD stride=((width*3+3)&~3),size=stride*height;
    if(size>64*1024*1024)return 0;
    HDC dc=GetWindowDC(target),memory=CreateCompatibleDC(dc);HBITMAP image=CreateCompatibleBitmap(dc,width,height);
    HGDIOBJ previous=SelectObject(memory,image);int okay=BitBlt(memory,0,0,width,height,dc,0,0,SRCCOPY);
    SelectObject(memory,previous);BITMAPINFO info;
    unsigned char *zero=(unsigned char*)&info;for(unsigned i=0;i<sizeof(info);i++)zero[i]=0;
    info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=height;
    info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=24;info.bmiHeader.biCompression=BI_RGB;info.bmiHeader.biSizeImage=size;
    unsigned char *buffer=LocalAlloc(LMEM_FIXED,54+size);
    if(!buffer)okay=0;
    if(okay){
        BITMAPFILEHEADER *file=(BITMAPFILEHEADER*)buffer;file->bfType=0x4d42;file->bfSize=54+size;file->bfReserved1=file->bfReserved2=0;file->bfOffBits=54;
        unsigned char *header=(unsigned char*)&info.bmiHeader;for(unsigned i=0;i<40;i++)buffer[14+i]=header[i];
        okay=GetDIBits(dc,image,0,height,buffer+54,&info,DIB_RGB_COLORS)==height;
        if(okay)okay=save(path,buffer,54+size);
    }
    if(buffer)LocalFree(buffer);
    DeleteObject(image);DeleteDC(memory);ReleaseDC(target,dc);return okay;
}

struct Applet {const char *name,*title,*command;};
static const struct Applet applets[]={
    {"keyboard","Keyboard Properties","control keyboard"},{"datetime","Date/Time Properties","control timedate.cpl"},
    {"mouse","Mouse Properties","control mouse"},{"regional","Regional Settings Properties","control intl.cpl"},
    {"system","System Properties","control sysdm.cpl"},{"sounds","Sounds Properties","control mmsys.cpl @1"},
    {"multimed","Multimedia Properties","control mmsys.cpl"},{"network","Network","control netcpl.cpl"},
    {"password","Passwords Properties","control password.cpl"},{"access","Accessibility Properties","control access.cpl"},
    {"addrem","Add/Remove Programs Properties","control appwiz.cpl"},{"display","Display Properties","control desk.cpl"}
};
void entry(void){
    char alias[16],path[64],title[128];unsigned index=0;const char *command=GetCommandLineA();
    if(*command=='"'){command++;while(*command&&*command!='"')command++;if(*command)command++;}
    else while(*command&&*command!=' ')command++;
    while(*command==' ')command++;
    while(*command&&*command!=' '&&index<15){char c=*command++;alias[index++]=(c>='A'&&c<='Z')?c+32:c;}
    alias[index]=0;while(*command==' ')command++;
    unsigned page=(*command>='0'&&*command<='9')?*command-'0':0;
    const struct Applet *applet=0;
    for(unsigned i=0;i<sizeof(applets)/sizeof(applets[0]);i++)if(equal(alias,applets[i].name))applet=&applets[i];
    CreateDirectoryA("C:\\W95PROBE",0);
    if(!applet){const char *error="{\"error\":\"Unknown applet\"}";save("C:\\W95PROBE\\ERROR.JSN",error,length(error));ExitProcess(2);}
    target=FindWindowA(0,applet->title);
    if(!target)WinExec(applet->command,SW_SHOWNORMAL);
    for(unsigned i=0;i<100&&!target;i++){Sleep(100);target=FindWindowA(0,applet->title);}
    if(!target){const char *error="{\"error\":\"Applet did not open\"}";save("C:\\W95PROBE\\ERROR.JSN",error,length(error));ExitProcess(3);}
    SetForegroundWindow(target);ShowWindow(target,SW_RESTORE);Sleep(500);
    if(FindWindowExA(target,0,"SysTabControl32",0))SendMessageA(target,WM_USER+101,page,0);
    SetCursorPos(GetSystemMetrics(SM_CXSCREEN)-2,GetSystemMetrics(SM_CYSCREEN)-2);
    RedrawWindow(target,0,0,RDW_FRAME|RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);Sleep(200);
    GetWindowRect(target,&window_rect);GetWindowTextA(target,title,sizeof(title));OSVERSIONINFOA version;
    unsigned char *clear=(unsigned char*)&version;for(unsigned i=0;i<sizeof(version);i++)clear[i]=0;
    version.dwOSVersionInfoSize=sizeof(version);GetVersionExA(&version);
    add("{\"probe_version\":1,\"applet\":");quote(alias);add(",\"title\":");quote(title);
    add(",\"page\":");number(page);add(",\"windows_major\":");number(version.dwMajorVersion);add(",\"windows_minor\":");number(version.dwMinorVersion);
    add(",\"windows_build\":");number(version.dwBuildNumber&65535);add(",\"service_pack\":");quote(version.szCSDVersion);
    add(",\"origin\":[");number(window_rect.left);add(",");number(window_rect.top);add("],\"size\":[");number(window_rect.right-window_rect.left);add(",");number(window_rect.bottom-window_rect.top);add("]");
    HDC dc=GetDC(target);add(",\"display_depth\":");number(GetDeviceCaps(dc,BITSPIXEL)*GetDeviceCaps(dc,PLANES));add(",\"dpi\":[");number(GetDeviceCaps(dc,LOGPIXELSX));add(",");number(GetDeviceCaps(dc,LOGPIXELSY));add("]");ReleaseDC(target,dc);
    SYSTEMTIME now;GetLocalTime(&now);char stamp[32];wsprintfA(stamp,"%04u-%02u-%02uT%02u:%02u:%02u",now.wYear,now.wMonth,now.wDay,now.wHour,now.wMinute,now.wSecond);add(",\"local_time\":");quote(stamp);
    add(",\"controls\":[");first_control=1;EnumChildWindows(target,child,0);add("]}");
    wsprintfA(path,"C:\\W95PROBE\\%s-%u.JSN",alias,page);
    if(overflow||!save(path,output,used))ExitProcess(4);
    wsprintfA(path,"C:\\W95PROBE\\%s-%u.BMP",alias,page);ExitProcess(bitmap(path)?0:5);
}
