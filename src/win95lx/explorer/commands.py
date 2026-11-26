"""Selection-aware File menu profiles. Renderers and dispatchers consume stable IDs."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Command:
    label:str
    command:str
    mnemonic:str=''
    enabled:bool=True
    checked:bool=False
    default:bool=False

@dataclass(frozen=True)
class Item:
    kind:str
    name:str
    writable:bool=True
    printable:bool=False

@dataclass(frozen=True)
class Context:
    container:str
    items:tuple[Item,...]=()
    offline:bool=False


def file_commands(context):
    items=context.items;n=len(items);single=n==1
    namespace=context.container in ('computer','control')
    tail=(None,Command('My Computer','computer',checked=True),None,
          Command('Work Offline','offline','w',checked=context.offline),Command('Close','close','c')) if context.container=='computer' else (None,Command('Close','close','c'))
    if not n and context.container=='control':return (Command('Close','close','c'),)
    if not n and namespace:
        return (Command('Create Shortcut','shortcut','s',False),Command('Delete','delete','d',False),
                Command('Rename','rename','m',False),Command('Properties','properties','r',False),*tail)
    if not n:
        return (Command('New Folder','new-folder','n'),Command('Delete','trash','d',False),
                Command('Rename','rename','m',False),Command('Properties','properties','r',False),*tail)
    rows=[Command('Open','open','o',default=True)]
    if all(item.kind in ('folder','drive') for item in items):
        rows += [Command('Explore','explore','e'),Command('Find...','find','f',single)]
    if single and items[0].printable:rows.append(Command('Print','print','p'))
    if single and items[0].kind=='drive':rows += [None,Command('Format...','format','a')]
    deletable=not namespace and all(item.writable for item in items)
    rows += [None,Command('Create Shortcut','shortcut','s'),
             Command('Delete','trash' if not namespace else 'delete','d',deletable),
             Command('Rename','rename','m',single and deletable),
             Command('Properties','properties','r',single and items[0].kind!='system-folder'),*tail]
    return tuple(rows)


def namespace_context(selection=None,offline=False):
    names=() if selection is None else ('(C:)','Control Panel') if selection=='*' else (selection,) if isinstance(selection,str) else tuple(selection)
    return Context('computer',tuple(Item('drive' if name=='(C:)' else 'system-folder',name,False) for name in names),offline)
