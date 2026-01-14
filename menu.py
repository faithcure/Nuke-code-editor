"""
Nuke Python IDE - Menu Integration
This file is automatically loaded by Nuke when using nuke.pluginAddPath()
"""

import nuke
import sys
import os
import importlib

def launch_python_ide_window():
    """Launch Python IDE as a standalone window"""
    try:
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        
        import init_ide
        importlib.reload(init_ide)

        
        init_ide.ide_start_reload()

    except Exception as e:
        import traceback
        error_msg = f"Failed to launch Python IDE:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        nuke.message(error_msg)

def launch_python_ide_panel():
    """Launch Python IDE as a dockable panel"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        import init_ide
        importlib.reload(init_ide)

        init_ide.ide_start_panel()

    except Exception as e:
        import traceback
        error_msg = f"Failed to launch Python IDE panel:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        nuke.message(error_msg)

try:
    import nukescripts.panels

    python_menu = nuke.menu("Nuke").addMenu("Python")

    
    python_menu.addCommand("Python IDE/Open as Window", launch_python_ide_window, "Ctrl+Shift+E")
    python_menu.addCommand("Python IDE/Open as Panel", launch_python_ide_panel)
    python_menu.addSeparator()

    # Menu added (silenced)
except Exception as e:
    print(f"Warning: Failed to add Python IDE menu: {e}")
