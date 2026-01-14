"""
Nuke Python IDE - Initialization
This file is automatically loaded by Nuke when using nuke.pluginAddPath()
"""

import sys
import os


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


modules_path = os.path.join(current_dir, "third_party")
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)


try:
    import init_ide

    
    init_ide.add_panel_to_pane()

    
    init_ide.check_startup_settings()

    print("Nuke Python IDE initialized successfully!")
except Exception as e:
    print(f"Warning: Failed to initialize Nuke Python IDE: {e}")
