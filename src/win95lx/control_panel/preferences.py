"""Pending property-sheet edits with atomic persistence and backend rollback."""
from dataclasses import asdict
import json

def save_preferences(value,path):
    value.validate();path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(asdict(value),indent=2)+'\n')
        temporary.replace(path)
    finally:
        if temporary.exists():temporary.unlink()

class PreferenceController:
    def __init__(self,path,backend,kind,apply_session=lambda value:None):
        self.path,self.backend,self.apply_session=path,backend,apply_session
        self.applied=backend.preferences()
        if path.exists():
            try:self.applied=kind(**json.loads(path.read_text())).validate()
            except (OSError,ValueError,TypeError):pass
        self.pending=self.applied

    def cancel(self):self.pending=self.applied

    def apply(self):
        self.pending.validate();before=self.backend.snapshot()
        try:
            self.backend.apply(self.pending)
            self.apply_session(self.pending)
            save_preferences(self.pending,self.path)
        except Exception:
            self.backend.restore(before)
            self.apply_session(self.applied)
            raise
        self.applied=self.pending
