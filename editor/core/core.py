import os
import json
import shutil
import platform
from PySide2.QtCore import QSize, QStandardPaths
from PySide2.QtGui import QColor, Qt, QFontDatabase

def load_nuke_function_descriptions(json_path):
    """Loads Nuke function descriptions from JSON."""
    with open(json_path, "r") as file:
        data = json.load(file)
    return {func["name"]: func["doc"] for func in data}

def ensure_py_extension(file_path):
    """Normalize file path to a .py extension."""
    if file_path.endswith(".py"):
        return file_path
    return f"{file_path}.py"

def write_python_file(file_path, content="", mode="w", encoding="utf-8", ensure_dir=False):
    """Create or update a Python file and return the normalized path."""
    normalized_path = ensure_py_extension(file_path)
    if ensure_dir:
        os.makedirs(os.path.dirname(normalized_path), exist_ok=True)
    with open(normalized_path, mode, encoding=encoding) as file:
        if content is not None:
            file.write(content)
    return normalized_path

def get_unique_python_path(file_path):
    """Return a non-colliding .py path by appending a numeric suffix."""
    normalized_path = ensure_py_extension(file_path)
    if not os.path.exists(normalized_path):
        return normalized_path
    base, ext = os.path.splitext(normalized_path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1

class PathFromOS:
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.icons_path = os.path.join(self.project_root, 'editor', 'ui', 'icons')
        self.json_path = os.path.join(self.project_root, 'assets')
        self.nuke_ref_path = os.path.join(self.project_root, 'assets', 'nuke.py')
        self.nukescripts_ref_path = os.path.join(self.project_root, 'assets', 'nukescripts.py')
        self.assets_path = os.path.join(self.project_root, 'assets')

        
        self.user_data_path = self._get_writable_dir(
            QStandardPaths.AppDataLocation,
            os.path.join(os.path.expanduser("~"), ".nuke"),
        )
        self.user_cache_path = self._get_writable_dir(
            QStandardPaths.CacheLocation,
            os.path.join(os.path.expanduser("~"), ".nuke"),
        )
        self.user_cache_path = os.path.join(self.user_cache_path, "cache")
        os.makedirs(self.user_cache_path, exist_ok=True)

        
        self.json_dynamic_path = os.path.join(self.user_cache_path, "dynamic_data")
        os.makedirs(self.json_dynamic_path, exist_ok=True)

        
        self.recent_projects_path = os.path.join(self.user_data_path, "recent_projects.json")
        self._ensure_file(
            self.recent_projects_path,
            os.path.join(self.assets_path, "recent_projects.json"),
            default_content={"recent_paths": []},
        )

        
        self.settings_db = self.user_data_path
        self.settings_path = os.path.join(self.settings_db, "settings.json")
        self.settings_example_path = os.path.join(self.project_root, "editor", "settings", "settings.json.example")
        self.settings_legacy_path = os.path.join(self.project_root, "editor", "settings", "settings.json")
        self._ensure_file(self.settings_path, self.settings_example_path, self.settings_legacy_path)



    def _get_writable_dir(self, qt_location, fallback_path):
        path = QStandardPaths.writableLocation(qt_location)
        if not path:
            path = fallback_path
        if os.path.basename(path) != "CodeEditor_v02":
            path = os.path.join(path, "CodeEditor_v02")
        os.makedirs(path, exist_ok=True)
        return path

    def _ensure_file(self, target_path, source_path=None, legacy_path=None, default_content=None):
        if os.path.exists(target_path):
            return
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        if legacy_path and os.path.exists(legacy_path):
            shutil.copy2(legacy_path, target_path)
            return
        if source_path and os.path.exists(source_path):
            shutil.copy2(source_path, target_path)
            return
        if default_content is not None:
            with open(target_path, "w", encoding="utf-8") as file:
                json.dump(default_content, file, indent=4)


class CodeEditorSettings:
    def __init__(self):
        """Loads code editor settings."""
        self.settings_json = os.path.join(PathFromOS().settings_db, "settings.json")
        
        self.temp_codes = "# from love import StopWars"

        
        self.main_font_size = 14  
        self.main_default_font = "Consolas"  
        self.ctrlWheel = True  

        with open(self.settings_json, "r") as file:
            settings = json.load(file)
            code_editor_settings = settings.get("Code Editor",{})

        self.main_font_size = code_editor_settings.get("default_font_size", self.main_font_size)
        selected_font = code_editor_settings.get("default_selected_font", self.main_default_font)
        self.main_default_font = self._resolve_default_font(selected_font)
        self.ctrlWheel = code_editor_settings.get("is_wheel_zoom", self.ctrlWheel)

        
        self.code_background_color = QColor(45, 45, 45)

        
        self.line_spacing_size = 1.2
        self.line_number_weight = False
        self.line_number_color = QColor(100, 100, 100)
        self.line_number_draw_line = QColor(100, 100, 100)
        self.line_number_background_color = QColor(45, 45, 45)

        
        inteder_line_onOff = 250
        self.intender_color = QColor(62, 62, 62, inteder_line_onOff)
        self.intender_width = 1.5

        
        line_opacity = 50
        self.clicked_line_color = QColor(75, 75, 75, line_opacity)

        
        self.setToolbar_area = Qt.TopToolBarArea
        tb_icon_sizeX= 25
        tb_icon_sizeY= 25
        self.toolbar_icon_size = QSize(tb_icon_sizeX,tb_icon_sizeY)

        
        self.ENABLE_COMPLETER = True
        self.ENABLE_COMPLETION_POPUP = True
        self.ENABLE_FUZZY_COMPLETION = True
        self.ENABLE_INLINE_GHOSTING = True
        self.GHOSTING_OPACITY = 100
        self.GHOSTING_COLOR = QColor(175, 175, 175, self.GHOSTING_OPACITY)
        self.CREATE_NODE_COMPLETER = True  

        disable_completer = code_editor_settings.get("disable_smart_compilation", False)
        disable_completion_popup = code_editor_settings.get("disable_completion_popup", False)
        disable_fuzzy = code_editor_settings.get("disable_fuzzy_compilation", False)
        disable_ghosting = code_editor_settings.get("disable_suggestion", False)
        disable_node_completer = code_editor_settings.get("disable_node_completer", False)

        self.ENABLE_COMPLETER = not disable_completer
        self.ENABLE_COMPLETION_POPUP = not disable_completion_popup
        self.ENABLE_FUZZY_COMPLETION = not disable_fuzzy
        self.ENABLE_INLINE_GHOSTING = not disable_ghosting
        self.CREATE_NODE_COMPLETER = not disable_node_completer

        
        self.ENABLE_CODE_FOLDING = code_editor_settings.get("enable_code_folding", True)
        self.line_spacing_size = code_editor_settings.get("line_spacing_size", self.line_spacing_size)
        self.enable_autosave = code_editor_settings.get("enable_autosave", False)
        self.autosave_interval = code_editor_settings.get("autosave_interval", 5)
        self.tab_size = code_editor_settings.get("tab_size", 4)
        self.use_spaces_for_tabs = code_editor_settings.get("use_spaces_for_tabs", True)

        
        self.OUTLINER_DOCK_POS = Qt.LeftDockWidgetArea
        self.HEADER_DOCK_POS = Qt.LeftDockWidgetArea
        self.WORKPLACE_DOCK_POS = Qt.RightDockWidgetArea
        self.OUTPUT_DOCK_POS = Qt.BottomDockWidgetArea

        self.OUTLINER_VISIBLE = True
        self.HEADER_VISIBLE = True
        self.WORKPLACE_VISIBLE = True
        self.OUTPUT_VISIBLE = True

        def set_focus_mode():
            self.OUTLINER_VISIBLE = False
            self.HEADER_VISIBLE = False
            self.WORKPLACE_VISIBLE = False
            self.OUTPUT_VISIBLE = False

        def set_default_mode():
            self.OUTLINER_VISIBLE = True
            self.HEADER_VISIBLE = True
            self.WORKPLACE_VISIBLE = True
            self.OUTPUT_VISIBLE = True

        interface_mode = settings.get("General", {}).get("default_interface_mode", "")
        if interface_mode == "Mumen Rider (Professional)":
            set_default_mode()

        elif interface_mode == "Saitama (immersive)":
            set_focus_mode()

        
        self.keyboard_shortcuts = self._load_keyboard_shortcuts()

    def _resolve_default_font(self, preferred_font):
        available_fonts = set(QFontDatabase().families())
        if preferred_font in available_fonts:
            return preferred_font

        system = platform.system()
        if system == "Windows":
            fallbacks = ["Consolas", "Cascadia Mono", "Courier New"]
        elif system == "Darwin":
            fallbacks = ["Menlo", "Monaco", "SF Mono", "Courier"]
        else:
            fallbacks = ["DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono", "Monospace"]

        for font in fallbacks:
            if font in available_fonts:
                return font

        return "Monospace"

    def _load_keyboard_shortcuts(self):
        """Load keyboard shortcuts from settings.json"""
        try:
            with open(self.settings_json, "r") as file:
                settings = json.load(file)
                return settings.get("Keyboard", {})
        except Exception:
            return {}

    def get_shortcut(self, command_name):
        """
        Get keyboard shortcut for a command.
        Returns the custom shortcut if defined, otherwise returns the default.

        Args:
            command_name (str): Name of the command (e.g., "Duplicate Line", "Save", etc.)

        Returns:
            str: Keyboard shortcut (e.g., "Ctrl+D", "Ctrl+S")
        """
        
        default_shortcuts = {
            
            "New Project": "Ctrl+N",
            "New File": "Ctrl+Shift+N",
            "Open File": "Ctrl+O",
            "Save": "Ctrl+S",
            "Save As": "Ctrl+Shift+S",
            "Close Tab": "Ctrl+W",
            "Exit": "Ctrl+Q",

            
            "Undo": "Ctrl+Z",
            "Redo": "Ctrl+Y",
            "Cut": "Ctrl+X",
            "Copy": "Ctrl+C",
            "Paste": "Ctrl+V",
            "Select All": "Ctrl+A",
            "Find": "Ctrl+F",
            "Replace": "Ctrl+Shift+R",
            "Go to Line": "Ctrl+G",
            "Comment Toggle": "Ctrl+/",
            "Duplicate Line": "Ctrl+D",
            "Delete Line": "Ctrl+Shift+K",
            "Move Line Up": "Alt+Up",
            "Move Line Down": "Alt+Down",
            "Smart Home": "Home",
            "Smart End": "End",

            
            "Zoom In": "Ctrl++",
            "Zoom Out": "Ctrl+-",
            "Reset Zoom": "Ctrl+0",
            "Show Whitespace": "Ctrl+Shift+W",

            
            "Run Code": "F5",
            "Execute Selected or All": "Ctrl+Enter",
            "Execute All Code": "Ctrl+Shift+Enter",
            "Execute Current Line": "Ctrl+Alt+Enter",
        }

        
        return self.keyboard_shortcuts.get(command_name, default_shortcuts.get(command_name, ""))
