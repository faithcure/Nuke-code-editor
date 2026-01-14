# Nuke Code Editor (CodeEditor_v02)

A Python IDE / code editor plugin embedded in Foundry Nuke.

> [!IMPORTANT]
> This plugin has been tested **on Windows only**. It has **not** been tested on macOS/Linux.

> [!NOTE]
> The plugin folder name is **`CodeEditor_v02`** (legacy working name). Keep this folder name for now.

---

## ✨ Features
- ⚡ **IDE experience inside Nuke:** Write/run code in Nuke and see output/tracebacks instantly
- 🧩 **Node Creator Pro:** Search nodes, edit knobs, and **generate ready-to-run Python** (with favorites + filtering)
- ✍️ **Smart editor:** Syntax highlighting (Pygments), auto-completion, code folding, line numbers, indentation helpers
- ▶️ **Run options:** Run selection or the whole file; quick experiments via Output/Console
- 🗂️ **Project workflow:** Create/open a project folder, tabbed file management, recent projects
- 🌐 **GitHub menu:** Commit / pull / push / status directly from the IDE
- ⚙️ **Settings:** Autosave, tab size, shortcuts, and behavior (per-user)

---

## 📥 Download (Git Clone)
GitHub “Download ZIP” will usually extract as `Nuke-code-editor-main`. If you want a clean folder name, use `git clone`.

**Windows (recommended): clone directly into your Nuke user folder**
```powershell
cd $env:USERPROFILE\.nuke
git clone https://github.com/faithcure/Nuke-code-editor.git CodeEditor_v02
```

**Update later**
```powershell
cd $env:USERPROFILE\.nuke\CodeEditor_v02
git pull
```

---

## ⚙️ Installation
1. Ensure the plugin folder is named `CodeEditor_v02` and placed in your Nuke user directory:
   - 🪟 Windows: `C:\Users\<user>\.nuke\`
   - 🍎 macOS: `~/Library/Application Support/Foundry/Nuke/` (or `~/.nuke/` on some setups)
   - 🐧 Linux: `~/.nuke/`
2. Add the hook below to your `init.py` in the Nuke user directory (create it if it doesn’t exist):

```python
# CodeEditor_v02 init hook
import nuke, os
nuke.pluginAddPath(os.path.join(os.path.dirname(__file__), "CodeEditor_v02"))
```

---

## 🚀 Launch
- Restart Nuke.
- From the menu: `Nuke > Python > Python IDE > Open as Window` (or `Open as Panel`)

---

## 🧹 Uninstall
- Remove the `CodeEditor_v02` folder from your Nuke user directory.
- Remove the hook lines you added to `init.py` / `menu.py`.

---

## 🐞 Bug Reports / Requests
For bugs, suggestions, and feature requests: https://github.com/faithcure/Nuke-code-editor/issues

---

## 👤 Contact
- 🌍 Web: https://www.fatihunal.net
- ✉️ Email: fatihunal@gmail.com
- 🎬 IMDb: https://www.imdb.com/name/nm10028691/?ref_=nv_sr_srsg_1_tt_0_nm_6_q_fatih%2520%25C3%25BCnal
- 💼 LinkedIn: https://www.linkedin.com/in/fatih-mehmet-unal/

---

## 💝 Donate Link (Optional)
---

## 🧾 License
Apache-2.0: `LICENSE`. Third-party dependencies ship under their own licenses (see `third_party/`).
