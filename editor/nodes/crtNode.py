import importlib
import os.path
from PySide2.QtCore import QObject
from PySide2.QtWidgets import QPlainTextEdit

from editor.core import PathFromOS
import json
import re
from editor.core import CodeEditorSettings

try:
    import nuke
except ImportError:
    nuke = None

class createNodesCode(QObject):
    def __init__(self):
        super().__init__()

        self.createNodesMenu = {
            "Create Node": lambda: self.createNodeMenu(),
            
            "Count 'by' Nodes": lambda: self.countByNodes(),
            "Change 'by' Knob(s)": lambda: self.changeByKnob(),
            "Expand Menu": lambda: self.expandMenu(),
        }

    def createNodeMenu(self):
        """
        Opens a UI for creating nodes with advanced options.
        source: dialogs/crtNodeDialogs.py
        """
        try:
            import editor.ui.dialogs.crtNodeDialogs
            importlib.reload(editor.ui.dialogs.crtNodeDialogs)
            from editor.ui.dialogs.crtNodeDialogs import show_nuke_node_creator
            pass
            show_nuke_node_creator()
        except Exception as e:
            import traceback
            error_msg = f"Error opening Create Node dialog:\n{str(e)}\n{traceback.format_exc()}"
            pass
            import nuke
            nuke.message(error_msg)

    def countByNodes(self):
        pass

    def changeByKnob(self):
        pass

    def expandMenu(self):
        pass
