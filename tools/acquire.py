#!/usr/bin/env python3
"""Read-only media inventory/extraction via system libarchive. No mounts or execution."""
import argparse, ctypes as C, ctypes.util, hashlib, json
from pathlib import Path

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def unpack(source, target):
    lib = C.CDLL(ctypes.util.find_library('archive'))
    for name, args, result in [('archive_read_new', [], C.c_void_p), ('archive_read_support_filter_all',[C.c_void_p], C.c_int), ('archive_read_support_format_all',[C.c_void_p], C.c_int), ('archive_read_open_filename',[C.c_void_p,C.c_char_p,C.c_size_t],C.c_int), ('archive_read_next_header',[C.c_void_p,C.POINTER(C.c_void_p)],C.c_int), ('archive_entry_pathname',[C.c_void_p],C.c_char_p), ('archive_entry_filetype',[C.c_void_p],C.c_uint), ('archive_read_data',[C.c_void_p,C.c_void_p,C.c_size_t],C.c_ssize_t), ('archive_error_string',[C.c_void_p],C.c_char_p), ('archive_read_free',[C.c_void_p],C.c_int)]:
        fn=getattr(lib,name); fn.argtypes=args; fn.restype=result
    a=lib.archive_read_new(); rows=[]
    def error():
        return (lib.archive_error_string(a) or b'archive error').decode(errors='replace')
    try:
        lib.archive_read_support_filter_all(a); lib.archive_read_support_format_all(a)
        if lib.archive_read_open_filename(a,bytes(source),10240)<0: raise RuntimeError(error())
        entry=C.c_void_p(); buf=C.create_string_buffer(65536)
        while True:
            rc=lib.archive_read_next_header(a,C.byref(entry))
            if rc==1: break
            if rc<0: raise RuntimeError(error())
            name=lib.archive_entry_pathname(entry).decode(errors='replace')
            if lib.archive_entry_filetype(entry)!=0o100000: continue
            dest=target/name
            if not dest.resolve().is_relative_to(target.resolve()): raise ValueError('unsafe archive path: '+name)
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists(): raise FileExistsError(dest)
            try:
                with dest.open('xb') as out:
                    while True:
                        n=lib.archive_read_data(a,buf,len(buf))
                        if n<0: raise RuntimeError(error())
                        if n==0: break
                        out.write(buf.raw[:n])
                rows.append({'source':str(source),'name':name,'output':str(dest),'sha256':sha(dest),'status':'extracted'})
            except Exception as e:
                dest.unlink(missing_ok=True)
                rows.append({'source':str(source),'name':name,'status':'failed','error':str(e)})
    finally: lib.archive_read_free(a)
    return rows

def main():
    p=argparse.ArgumentParser(); p.add_argument('iso',type=Path); p.add_argument('--output',type=Path,default=Path('private/reference')); args=p.parse_args()
    root=args.output; root.mkdir(parents=True,exist_ok=True)
    if (root/'inventory.json').exists(): p.error('Use a new output directory; existing reference is preserved.')
    before=sha(args.iso)
    report={'schema_version':1,'iso':str(args.iso.resolve()),'sha256':before,'files':[],'failures':[]}
    try:
        report['files']=unpack(args.iso,root/'media')
        for row in list(report['files']):
            if row['name'].lower().endswith('.cab') and row['status']=='extracted':
                try: report['files']+=unpack(Path(row['output']),root/'cabs'/row['name'])
                except Exception as e: report['failures'].append({'source':row['name'],'error':str(e)})
    except Exception as e: report['failures'].append({'source':str(args.iso),'error':str(e)})
    report['source_unchanged']=sha(args.iso)==before
    (root/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'sha256':before,'files':len(report['files']),'failures':len(report['failures']),'source_unchanged':report['source_unchanged']}))
if __name__=='__main__': main()
