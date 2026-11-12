# Win95LX dialog migration

Order within each group reflects expected use in the development guest. Capture native references on the local Windows 95 VM before making pixel-match claims. The first implementation covers the shared editor Open, Save As, file replacement, and unsaved changes. App names identify separate reference states where behavior differs.

| Priority | Dialog |
| ---: | --- |
| 1 | Open file |
| 2 | Save As |
| 3 | Confirm file replacement |
| 4 | Notepad unsaved changes |
| 5 | WordPad unsaved changes |
| 6 | File not found |
| 7 | Access denied |
| 8 | Invalid file name |
| 9 | WordPad unsupported or lossy RTF |
| 10 | Browse for Folder |
| 11 | Find in Notepad |
| 12 | Notepad search completed |
| 13 | WordPad Find |
| 14 | WordPad Replace |
| 15 | Font selection |
| 16 | Print |
| 17 | Page Setup |
| 18 | Print Setup |
| 19 | Printing progress |
| 20 | Printer unavailable |
| 21 | Run |
| 22 | Run command not found |
| 23 | Find Files or Folders |
| 24 | Shut Down Windows |
| 25 | Taskbar Properties |
| 26 | Folder Options |
| 27 | Create Shortcut |
| 28 | Open With |
| 29 | File Properties |
| 30 | Shortcut Properties |
| 31 | Confirm File Delete |
| 32 | Confirm Multiple File Delete |
| 33 | Empty Recycle Bin |
| 34 | Restore item with conflicting name |
| 35 | File copy progress |
| 36 | File move progress |
| 37 | Confirm Folder Replace |
| 38 | File in use |
| 39 | Disk full |
| 40 | Drive not ready |
| 41 | Display Properties |
| 42 | Confirm Display Settings |
| 43 | Mouse Properties |
| 44 | Keyboard Properties |
| 45 | Sounds Properties |
| 46 | Date/Time Properties |
| 47 | System Properties |
| 48 | Add/Remove Programs Properties |
| 49 | Windows Update or Win95LX update confirmation |
| 50 | Update progress and restart required |

For each dialog, verify the title and icon, button order, default action, Escape, focus return, and error states. Preserve the underlying file or update operation when replacing its UI. Update references depend on the installed Windows 95 edition and its Desktop Update components.

## Pointer follow-up

Verify the normal arrow in the shell, menus, and modal windows. Test the I-beam in text fields, sizing arrows at window edges, and busy, unavailable, move, and help states. Check cursor hotspot alignment and visual size separately when resizing the host viewer.
