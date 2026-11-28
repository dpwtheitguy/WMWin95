#!/usr/bin/env python3
"""Stage private original95/Plus screensavers without executing media programs."""
import argparse
import hashlib
import json
import os
import fcntl
from pathlib import Path
import shutil
import tempfile
import struct

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = {'bezier':'Beziers','scrnsave':'Blank Screen','ssflywin':'Flying Windows','ssmarque':'Marquee','ssmyst':'Mystify Your Mind','ssstars':'Starfield Simulation','ss3dfo':'3D Flying Objects','ssflwbox':'3D Flower Box','ssmaze':'3D Maze','sspipes':'3D Pipes','sstext3d':'3D Text'}
PLUS = {'nature':('Nature','NATURE.DLL'),'dangerous':('Dangerous Creatures','DANGEROU.DLL'),'davinci':('Leonardo da Vinci','DAVINCI.DLL'),'golden-era':('The Golden Era','MODERNE.DLL'),'sports':('Sports','SPORTS.DLL'),'mystery':('Mystery','MYSTERY.DLL'),'inside-computer':('Inside your Computer','PCINSIDE.DLL'),'travel':('Travel','TRAVEL.DLL')}


def stage(output, classic=None, plus=None):
    output = Path(output)
    classic = Path(classic or ROOT/'private/cabsets/windows95')
    plus = Path(plus or ROOT/'private/cabsets/plus95')
    if output.exists():
        raise FileExistsError('Choose an unused screensaver output directory.')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.screensavers-', dir=output.parent))
    document={'schema':1,'runtime_groups':{'trusted95':{'trust':'builtin95','profile':'classic95'}},'font_profiles':{},'presentations':{}}
    def font_profile():
        import sys
        sys.path.insert(0,str(ROOT/'src'))
        from win95lx.control_panel.theme_appearance import DEFAULT_COLORS
        fonts=temporary/'font-profiles'/'classic95';fonts.mkdir(parents=True)
        hashes={}
        for name in ('sserife.fon','vgasys.fon'):
            source=classic/name
            if source.is_symlink()or not 64<=source.stat().st_size<=2*1024*1024:raise ValueError('Invalid original bitmap font source.')
            raw=source.read_bytes()
            if source.is_symlink()or len(raw)<64 or len(raw)>2*1024*1024 or raw[:2]!=b'MZ':raise ValueError('Invalid original bitmap font.')
            offset=struct.unpack_from('<I',raw,60)[0]
            if raw[offset:offset+2]!=b'NE':raise ValueError('Original bitmap font must be an NE container.')
            (fonts/name).write_bytes(raw);hashes[name]=hashlib.sha256(raw).hexdigest()
        document['font_profiles']['classic95']={'directory':'font-profiles/classic95','files':hashes,'colors':DEFAULT_COLORS,'recipe':1}
    def package(identity, label, product, executable, files):
        folder = temporary/identity
        folder.mkdir()
        hashes, provenance = {}, []
        for installed, source in files.items():
            raw = source.read_bytes()
            if source.is_symlink() or len(raw) < 64 or not raw.startswith(b'MZ'):
                raise ValueError('A screensaver dependency is not an executable resource.')
            offset = struct.unpack_from('<I', raw, 60)[0]
            if offset + 26 > len(raw) or raw[offset:offset+4] != b'PE\0\0' or struct.unpack_from('<H',raw,offset+4)[0] != 0x14c or struct.unpack_from('<H',raw,offset+24)[0] != 0x10b:
                raise ValueError('A screensaver dependency is not a PE32 Intel386 executable.')
            digest = hashlib.sha256(raw).hexdigest()
            (folder/installed).write_bytes(raw)
            hashes[installed] = digest
            provenance.append({'source':str(source), 'installed':installed, 'sha256':digest})
        document['presentations'][identity] = {'label':label,'product':product,'runtime_group':'trusted95','architecture':'win32','directory':identity,'executable':executable,'files':hashes,'modes':['fullscreen','configure','preview'],'provenance':provenance,'mode_status':{'fullscreen':'probe-supported' if product=='Plus95' else 'unverified','configure':'probe-supported' if identity=='plus95-nature' else 'unverified','preview':'probe-supported' if identity=='plus95-nature' else 'unverified'},'acceptance':'Compatibility candidates; see per-engine probe evidence, not whole-product pixel acceptance.'}
    try:
        font_profile()
        for stem,label in CLASSIC.items():
            package('win95-'+stem,label,'Windows95',stem+'.scr',{stem+'.scr':classic/(stem+'.scr')})
        for key,(alias,library) in PLUS.items():
            package('plus95-'+key,alias,'Plus95',alias+'.scr',{alias+'.scr':plus/'WL32SCR.EXE',alias+'.dll':plus/library,'WL32DLL.DLL':plus/'WL32DLL.DLL','WILDLB32.DLL':plus/'WILDLB32.DLL'})
        for key,alias,source in [('windows95','Windows 95','BLOCKS.SCR'),('sixties',"The 60's USA",'LENS.SCR'),('science','Science','LENS.SCR')]:
            package('plus95-'+key,alias,'Plus95',alias+'.scr',{alias+'.scr':plus/source})
        (temporary/'.win95lx-screensavers').write_text('1\n')
        (temporary/'catalog.json').write_text(json.dumps(document,indent=2)+'\n')
        temporary.rename(output)
        return document
    except BaseException:
        shutil.rmtree(temporary)
        raise


def stage_bundle(output, classic=None, plus=None):
    """Idempotent replacement of our marked generated bundle only."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / ('.' + output.name + '.stage.lock')
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX)
        if not output.exists():
            return stage(output, classic, plus)
        marker = output / '.win95lx-screensavers'
        if output.is_symlink() or marker.is_symlink() or not marker.is_file() or marker.read_text() != '1\n':
            raise ValueError('Refusing to replace an unowned screensaver directory.')
        workspace = Path(tempfile.mkdtemp(prefix='.screensavers-rebuild-',dir=output.parent))
        replacement, backup = workspace/'replacement', workspace/'previous'
        try:
            document = stage(replacement,classic,plus)
            output.rename(backup)
            try:
                replacement.rename(output)
            except BaseException:
                backup.rename(output)
                raise
            return document
        finally:
            shutil.rmtree(workspace)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(len(stage(args.output)['presentations']))
