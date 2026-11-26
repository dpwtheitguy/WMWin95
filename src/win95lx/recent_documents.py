"""Recent document history shared by the shell and accessory applications."""

import fcntl
import json
from pathlib import Path

LIMIT = 15


class RecentDocuments:
    def __init__(self, path=None):
        self.path = path or Path.home()/'.config'/'win95lx'/'recent-documents.json'

    def paths(self):
        try:
            values = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return []
        if not isinstance(values,list):
            return []
        return list(dict.fromkeys(Path(value) for value in values if isinstance(value,str) and Path(value).is_absolute()))[:LIMIT]

    def add(self, path):
        document = Path(path).resolve()
        if not document.is_file():
            return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            entries = [document, *(entry for entry in self.paths() if entry != document)][:LIMIT]
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps([str(entry) for entry in entries])+'\n')
            temporary.replace(self.path)

    def entries(self):
        paths = [path for path in self.paths() if path.is_file()]
        return sorted(paths,key=lambda path:(path.name.casefold(),str(path).casefold()))


def record_document(path):
    try:
        RecentDocuments().add(path)
    except OSError as error:
        print(f'Could not update recent documents: {error}',flush=True)
