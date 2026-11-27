"""Lazy per-window folder-tree state, independent of GTK and paint-time I/O.

An adapter submits LoadRequest to a worker running DirectorySource.scan(), then
applies its immutable result on the UI thread. This is not a rendered TreeView
or an accepted Windows 95 Explorer launch path.
"""
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

Key=tuple[str,...]

def validate_key(key):
    if not isinstance(key,tuple) or any(not isinstance(p,str) or p in ('','.','..') or '/' in p or '\0' in p for p in key):
        raise ValueError('Invalid folder key.')
    return key

@dataclass(frozen=True)
class Entry:
    name:str
    link:bool=False
    blocked:str=''
    def __post_init__(self):validate_key((self.name,))

@dataclass(frozen=True)
class LoadRequest:
    key:Key
    generation:int
    show_hidden:bool=False
    def __post_init__(self):validate_key(self.key)

@dataclass(frozen=True)
class LoadResult:
    request:LoadRequest
    entries:tuple[Entry,...]=()
    error:str=''

@dataclass
class Node:
    key:Key
    label:str
    link:bool=False
    blocked:str=''
    children:tuple[Key,...]=()
    status:str='unloaded'
    error:str=''
    generation:int=0

@dataclass(frozen=True)
class Row:
    key:Key
    label:str
    depth:int
    expanded:bool
    selected:bool
    status:str
    blocked:str
    error:str

class FolderTree:
    """One instance per Explorer window; no filesystem access in this class."""
    def __init__(self,label='(C:)',*,show_hidden=False):
        self.nodes={():Node((),label)};self.expanded=set();self.selected=()
        self.show_hidden=show_hidden;self.scroll=0;self._generation=0

    def request_expand(self,key,*,refresh=False):
        validate_key(key);node=self.nodes[key]
        if node.blocked:return None
        self.expanded.add(key)
        if node.status in ('ready','loading') and not refresh:return None
        self._generation+=1;node.generation=self._generation;node.status='loading';node.error=''
        return LoadRequest(key,node.generation,self.show_hidden)

    def collapse(self,key):
        validate_key(key);self.nodes[key];self.expanded.discard(key)
        if self.selected!=key and self.selected[:len(key)]==key:self.selected=key

    def apply(self,result):
        """Ignore stale/missing requests; a collapsed node never reopens itself."""
        key=result.request.key;node=self.nodes.get(key)
        if node is None or node.generation!=result.request.generation or node.status!='loading':return False
        if result.error:
            node.status='error';node.error=result.error;return True
        names=[entry.name for entry in result.entries]
        if len(names)!=len(set(names)):raise ValueError('Duplicate folder entries.')
        children=tuple(key+(entry.name,) for entry in result.entries)
        removed=set(node.children)-set(children)
        for old in tuple(self.nodes):
            if any(old[:len(prefix)]==prefix for prefix in removed):
                del self.nodes[old];self.expanded.discard(old)
                if self.selected==old:self.selected=key
        for entry,child in zip(result.entries,children):
            previous=self.nodes.get(child)
            if previous is None or previous.link!=entry.link or previous.blocked!=entry.blocked:
                if previous is not None:
                    for old in tuple(self.nodes):
                        if old!=child and old[:len(child)]==child:
                            del self.nodes[old];self.expanded.discard(old)
                            if self.selected==old:self.selected=child
                self.nodes[child]=Node(child,entry.name,entry.link,entry.blocked)
                if entry.blocked:self.expanded.discard(child)
        node.children=children;node.status='ready';node.error='';return True

    def iter_rows(self):
        stack=[((),0)]
        while stack:
            key,depth=stack.pop();node=self.nodes[key]
            yield Row(key,node.label,depth,key in self.expanded,key==self.selected,node.status,node.blocked,node.error)
            if key in self.expanded:stack.extend((child,depth+1) for child in reversed(node.children))

    def page(self,start,count):
        if start<0 or count<0:raise ValueError('Invalid tree viewport.')
        return tuple(islice(self.iter_rows(),start,start+count))

    def select(self,key):
        validate_key(key)
        if not any(row.key==key for row in self.iter_rows()):raise ValueError('Folder is not visible.')
        self.selected=key

    def key(self,name):
        """Right/Left and visible-row navigation; returned load runs elsewhere."""
        rows=tuple(self.iter_rows());index=next(i for i,row in enumerate(rows) if row.key==self.selected)
        node=self.nodes[self.selected]
        if name=='Right':
            if self.selected not in self.expanded:return self.request_expand(self.selected)
            if node.children:self.selected=node.children[0]
        elif name=='Left':
            if self.selected in self.expanded:self.collapse(self.selected)
            elif self.selected:self.selected=self.selected[:-1]
        elif name in ('Up','Down','Home','End'):
            target=0 if name=='Home' else len(rows)-1 if name=='End' else max(0,min(len(rows)-1,index+(-1 if name=='Up' else 1)))
            self.selected=rows[target].key
        return None

class DirectorySource:
    """Read-only filesystem adapter. Run scan on a worker, not during drawing."""
    def __init__(self,root):self.root=Path(root).resolve(strict=True)
    def scan(self,request):
        try:
            validate_key(request.key);path=self.root.joinpath(*request.key).resolve(strict=True)
            if not path.is_relative_to(self.root):return LoadResult(request,error='outside-root')
            ancestors={self.root.joinpath(*request.key[:i]).resolve(strict=True) for i in range(len(request.key))}
            if path in ancestors:return LoadResult(request,error='folder-cycle')
            entries=[]
            for item in path.iterdir():
                if item.name.startswith('.') and not request.show_hidden:continue
                try:
                    target=item.resolve(strict=True)
                    if not target.is_relative_to(self.root) or not item.is_dir():continue
                    entries.append(Entry(item.name,item.is_symlink(),'folder-cycle' if target in ancestors|{path} else ''))
                except (OSError,RuntimeError):continue
            entries.sort(key=lambda item:(item.name.casefold(),item.name))
            return LoadResult(request,tuple(entries))
        except PermissionError:return LoadResult(request,error='access-denied')
        except FileNotFoundError:return LoadResult(request,error='folder-missing')
        except (OSError,RuntimeError):return LoadResult(request,error='folder-unavailable')
