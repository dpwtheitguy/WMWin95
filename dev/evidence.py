"""Build identities shared by fidelity acceptance reports."""
import hashlib

def identity(root,script,references=()):
    digest=hashlib.sha256()
    for path in sorted(path for path in (root/'src').rglob('*') if path.suffix in ('.py','.c','.h')):
        digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    native={}
    try:
        from win95lx.assets.native_palette import library
        lib=library()
        if lib:
            from pathlib import Path
            native={'path':lib._name,'sha256':hashlib.sha256(Path(lib._name).read_bytes()).hexdigest()}
    except ImportError:pass
    return {'identity_schema':2,'source_sha256':digest.hexdigest(),'native_palette':native,
            'assets_manifest_sha256':hashlib.sha256((root/'private/shell-assets/manifest.json').read_bytes()).hexdigest(),
            'test_script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
            'reference_sha256':{str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in references}}
