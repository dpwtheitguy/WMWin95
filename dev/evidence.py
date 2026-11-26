"""Build identities shared by fidelity acceptance reports."""
import hashlib

def identity(root,script,references=()):
    digest=hashlib.sha256()
    for path in sorted((root/'src').rglob('*.py')):
        digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    return {'source_sha256':digest.hexdigest(),
            'assets_manifest_sha256':hashlib.sha256((root/'private/shell-assets/manifest.json').read_bytes()).hexdigest(),
            'test_script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
            'reference_sha256':{str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in references}}
