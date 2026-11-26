"""Persist folder-browsing policy without tying navigation to window creation."""
from dataclasses import dataclass,asdict
import json

@dataclass(frozen=True)
class BrowsingPreferences:
    single_window:bool=True

    @classmethod
    def load(cls,path):
        try:
            value=json.loads(path.read_text())['single_window']
            if type(value) is bool:return cls(value)
        except (OSError,ValueError,KeyError,TypeError):pass
        return cls()

    def save(self,path):
        path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(asdict(self))+'\n');temp.replace(path)
