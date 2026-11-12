#!/usr/bin/env python3
"""Extract raw PE/NE resources, preserving names, IDs and language IDs."""
import argparse, hashlib, json, struct
from pathlib import Path
TYPES={1:'CURSOR',2:'BITMAP',3:'ICON',4:'MENU',5:'DIALOG',6:'STRING',7:'FONTDIR',8:'FONT',9:'ACCELERATOR',10:'RCDATA',12:'GROUP_CURSOR',14:'GROUP_ICON',16:'VERSION',24:'MANIFEST'}
def u16(b,p): return struct.unpack_from('<H',b,p)[0]
def u32(b,p): return struct.unpack_from('<I',b,p)[0]
def extract(b):
    if b[:2]!=b'MZ': raise ValueError('Not MZ executable')
    base=u32(b,60); signature=b[base:base+2]
    if signature==b'NE':
        start=base+u16(b,base+36); end=base+u16(b,base+38)
        if start==end: return
        shift=u16(b,start); p=start+2
        def name(value):
            if value&32768: return value&32767
            off=start+value; return b[off+1:off+1+b[off]].decode('cp1252')
        while p<end:
            kind=u16(b,p)
            if not kind: break
            count=u16(b,p+2); p+=8
            for _ in range(count):
                offset=u16(b,p)<<shift; size=u16(b,p+2)<<shift; ident=name(u16(b,p+6)); p+=12
                if offset+size>len(b): raise ValueError('NE resource exceeds file')
                yield name(kind),ident,None,b[offset:offset+size],'NE'
    elif signature==b'PE':
        count=u16(b,base+6); optsize=u16(b,base+20); opt=base+24; magic=u16(b,opt)
        if magic not in (0x10b,0x20b): raise ValueError('Unsupported PE optional header')
        dd=opt+(96 if magic==0x10b else 112); resource=u32(b,dd+16)
        if not resource: return
        sections=opt+optsize
        def rva(value):
            for i in range(count):
                s=sections+40*i; virtual=u32(b,s+12); size=max(u32(b,s+8),u32(b,s+16))
                if virtual<=value<virtual+size: return u32(b,s+20)+value-virtual
            raise ValueError('Unmapped RVA')
        root=rva(resource)
        def walk(relative,path,depth=0):
            if depth>3: raise ValueError('Invalid resource depth')
            p=root+relative; n=u16(b,p+12)+u16(b,p+14)
            for i in range(n):
                at=p+16+8*i; ident=u32(b,at); target=u32(b,at+4)
                if ident&0x80000000:
                    st=root+(ident&0x7fffffff); size=u16(b,st); ident=b[st+2:st+2+2*size].decode('utf-16le')
                chain=path+[ident]
                if target&0x80000000: yield from walk(target&0x7fffffff,chain,depth+1)
                else:
                    at=root+target; offset=rva(u32(b,at)); size=u32(b,at+4)
                    if len(chain)!=3 or offset+size>len(b): raise ValueError('Malformed PE resource')
                    yield *chain,b[offset:offset+size],'PE'
        yield from walk(0,[])
    else: raise ValueError('Unsupported executable header '+repr(signature))
def dimensions(kind,data):
    try:
        if kind==1: data=data[4:]
        if kind in (1,2,3) and u32(data,0)>=40:
            w,h=struct.unpack_from('<ii',data,4); return [abs(w),abs(h)//(2 if kind in (1,3) else 1)]
    except struct.error: pass
    return None

def main():
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); p.add_argument('--output',type=Path,default=Path('private/resources')); args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False); rows=[]
    for source in sorted(args.root.rglob('*')):
        if not source.is_file(): continue
        ext=source.suffix.lower(); relative=source.relative_to(args.root)
        if ext not in ('.exe','.dll','.cpl','.drv','.fon','.ico','.cur','.ani','.bmp','.wav','.ttf','.fnt'): continue
        b=source.read_bytes(); common={'source_file':str(relative),'source_sha256':hashlib.sha256(b).hexdigest()}
        if ext in ('.exe','.dll','.cpl','.drv','.fon'):
            try:
                count=0
                for kind,ident,language,data,fmt in extract(b):
                    dest=args.output/relative/str(kind).encode().hex()/str(language).encode().hex()/ (str(ident).encode().hex()+'.bin'); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
                    rows.append(dict(common,resource_type=TYPES.get(kind,str(kind)),identifier=ident,language=language,dimensions=dimensions(kind,data),format=fmt+' raw resource',extraction_status='extracted',output=str(dest),sha256=hashlib.sha256(data).hexdigest())); count+=1
                if not count: rows.append(dict(common,resource_type=None,identifier=None,dimensions=None,format='executable',extraction_status='no_resources'))
            except Exception as e: rows.append(dict(common,resource_type=None,identifier=None,dimensions=None,format='executable',extraction_status='unsupported_or_failed',error=str(e)))
        else:
            dest=args.output/'loose'/relative; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(b)
            rows.append(dict(common,resource_type=ext[1:].upper(),identifier=source.name,dimensions=dimensions(2,b[14:]) if ext=='.bmp' else None,format=ext[1:],extraction_status='copied_original',output=str(dest)))
    (args.output/'inventory.json').write_text(json.dumps({'schema_version':1,'resources':rows},indent=2)+'\n')
    print(json.dumps({'records':len(rows),'failed_or_unsupported':sum(r['extraction_status']=='unsupported_or_failed' for r in rows)}))
if __name__=='__main__': main()
