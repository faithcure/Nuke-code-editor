# Nuke Python IDE – Install Guide

This package installs the CodeEditor into your Nuke user directory and wires the menu entry.

## Package Contents
- `CodeEditor_v02/` (project folder)
- `INSTALL.md` (this file)

## Quick Install (All OS)
1) Unzip the package.
2) Copy the `CodeEditor_v02` folder into your Nuke user directory:
   - Windows: `C:\Users\<user>\.nuke\`
   - macOS: `~/Library/Application Support/Foundry/Nuke/` (or `~/.nuke/` if used)
   - Linux: `~/.nuke/`
3) Add the startup hook below to your `init.py` in the Nuke user directory.
   - If the file does not exist, create it.

## Required Hook
### init.py (in your Nuke user directory)
```python
# CodeEditor_v02 init hook
import nuke
nuke.pluginAddPath("./CodeEditor_v02")
```

## Verify
- Restart Nuke.
- You should see a "Python IDE" entry in the menu.
- Launch it and confirm the workspace shows your project files.

## Uninstall
- Remove `CodeEditor_v02` from your Nuke user directory.
- Remove the hook lines from `init.py` and `menu.py`.

## Notes
- If you use a custom Nuke user directory, install there instead of the default paths above.
- If you already have an `init.py` or `menu.py`, merge the hooks into your existing files (do not overwrite).

## Donate Link (Optional)
The plugin includes a `Donate...` menu item (both in Nuke menu and inside the IDE Help menu).

To enable it, set your donation URL in one of these ways:
- Edit `editor/donate.py` and set `DONATE_URL` (recommended for distribution)
- Or set environment variable `CODEEDITOR_V02_DONATE_URL`
- Or add `General.donate_url` to the user settings.json
