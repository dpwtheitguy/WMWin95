#!/usr/bin/env python3
"""Inspect and preserve an ISO's El Torito boot catalog and floppy-emulation image."""
import argparse,hashlib,json,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('iso',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
with a.iso.open('rb') as f:
    descriptor=None
    for sector in range(16,64):
        f.seek(sector*2048);b=f.read(2048)
        if b[1:6]!=b'CD001':raise ValueError('Invalid ISO descriptor')
        if b[0]==0 and b[7:39].rstrip(b'\0 ')==b'EL TORITO SPECIFICATION':descriptor=b;break
        if b[0]==255:break
    if descriptor is None:raise ValueError('No El Torito boot descriptor')
    catalog_lba=struct.unpack_from('<I',descriptor,71)[0];f.seek(catalog_lba*2048);catalog=f.read(2048);valid=catalog[30:32]==b'\x55\xaa' and sum(struct.unpack('<16H',catalog[:32]))&65535==0
    if not valid:raise ValueError('Invalid boot catalog validation entry')
    media=catalog[33];boot_lba=struct.unpack_from('<I',catalog,40)[0];length={1:1200*1024,2:1440*1024,3:2880*1024}.get(media)
    if length is None:raise ValueError('Only floppy-emulation boot images are supported')
    f.seek(boot_lba*2048);image=f.read(length)
    if len(image)!=length:raise ValueError('Truncated image')
(a.output/'boot-catalog.bin').write_bytes(catalog);(a.output/'boot-floppy.img').write_bytes(image)
r={'source_iso':str(a.iso.resolve()),'catalog_lba':catalog_lba,'validation_checksum_ok':valid,'bootable':catalog[32]==0x88,'media_type':media,'boot_image_lba':boot_lba,'image_size':length,'boot_image_sha256':hashlib.sha256(image).hexdigest(),'note':'Embedded boot media is not independently authenticated as original Microsoft release media.'}
(a.output/'boot.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
