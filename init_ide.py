import os
import sys
import json
import importlib
from PySide2.QtWidgets import QApplication, QProgressDialog
from PySide2.QtCore import Qt, QTimer
from editor.core import PathFromOS


project_dir = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.join(project_dir, "third_party")
settings_path = PathFromOS().settings_path
PANEL_ID = "com.faithcure.PythonIDE"


if modules_path not in sys.path:
    sys.path.insert(0, modules_path)



def _create_progress(app):
    progress = QProgressDialog("Starting Nuke Code Editor...", "Cancel", 0, 6)
    progress.setWindowTitle("Launching IDE")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)
    app.processEvents()
    return progress

def _show_instance_message(message):
    try:
        import nuke
        nuke.message(message)
    except Exception:
        print(message)


def _find_editor_instance(app, editor_cls):
    for widget in app.allWidgets():
        try:
            if widget.property("codeeditor_v02_instance") is True:
                return widget
        except Exception:
            continue
    return None


def ide_start_reload():
    """
    Start or reload the Python code editor.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    progress = _create_progress(app)

    progress.setLabelText("Loading editor modules...")
    progress.setValue(1)
    app.processEvents()

    from editor import editor_window
    importlib.reload(editor_window)

    EditorApp = editor_window.EditorApp

    
    existing = _find_editor_instance(app, EditorApp)
    if existing:
        if getattr(existing, "as_panel", False):
            try:
                existing.close()
                existing.deleteLater()
                app.processEvents()
            except Exception:
                pass
        else:
            progress.close()
            if existing.isMinimized():
                existing.showNormal()
            if not existing.isVisible():
                existing.show()
            existing.raise_()
            existing.activateWindow()
            return
        existing = _find_editor_instance(app, EditorApp)
        if existing and getattr(existing, "as_panel", False):
            progress.close()
            _show_instance_message(
                "Python IDE panel is still open.\n"
                "Close the panel before opening a window."
            )
            return

    def update_progress(value, message):
        progress.setValue(value)
        progress.setLabelText(message)
        app.processEvents()

    progress.setLabelText("Initializing UI...")
    progress.setValue(2)
    app.processEvents()

    window = EditorApp(progress_callback=update_progress)

    progress.setLabelText("Finalizing...")
    progress.setValue(6)
    app.processEvents()

    window.show()
    window.raise_()
    window.activateWindow()
    progress.close()

def _startup_launch_mode(settings):
    mode = settings.get("General", {}).get("startup_launch_mode", "Standalone Window")
    if not isinstance(mode, str):
        return "window"
    mode = mode.strip().lower()
    if "panel" in mode:
        return "panel"
    return "window"

def _try_add_panel_to_pane(panel):
    try:
        import nuke
    except Exception:
        return False

    target_pane = None
    for pane_name in ("Properties.1", "DAG.1", "Viewer.1"):
        try:
            target_pane = nuke.getPaneFor(pane_name)
            if target_pane:
                break
        except Exception:
            continue

    if not target_pane:
        return False

    if not hasattr(panel, "addToPane"):
        return False

    try:
        panel.addToPane(target_pane)
        return True
    except Exception:
        return False

def _schedule_panel_dock(panel, remaining_attempts=20, delay_ms=250):
    if remaining_attempts <= 0:
        return

    def _attempt():
        if _try_add_panel_to_pane(panel):
            return
        _schedule_panel_dock(panel, remaining_attempts=remaining_attempts - 1, delay_ms=delay_ms)

    QTimer.singleShot(delay_ms, _attempt)

def ide_start_panel():
    """
    Start the IDE as a dockable Nuke panel (best-effort).
    """
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        import nuke  # noqa: F401
        import nukescripts.panels as panels
    except Exception:
        panel_widget = create_panel()
        if panel_widget:
            try:
                panel_widget.show()
                panel_widget.raise_()
                panel_widget.activateWindow()
            except Exception:
                pass
        return

    panel = None
    try:
        panel = panels.restorePanel(PANEL_ID)
    except Exception:
        panel = None

    if not panel:
        try:
            panel = panels.registerWidgetAsPanel(
                "init_ide.create_panel",
                "Python IDE",
                PANEL_ID,
                True,
            )
        except TypeError:
            try:
                panel = panels.registerWidgetAsPanel(
                    "init_ide.create_panel",
                    "Python IDE",
                    PANEL_ID,
                )
            except Exception:
                panel = None
        except Exception:
            panel = None

    if not panel:
        panel_widget = create_panel()
        if panel_widget:
            try:
                panel_widget.show()
                panel_widget.raise_()
                panel_widget.activateWindow()
            except Exception:
                pass
        return

    if not _try_add_panel_to_pane(panel):
        _schedule_panel_dock(panel)

def check_startup_settings():
    """
    Check if startup_checkbox in settings.json is true and start IDE if enabled.
    """
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r") as file:
                settings = json.load(file)
            if settings.get("General", {}).get("startup_checkbox", False):
                print("Startup check is true")
                if _startup_launch_mode(settings) == "panel":
                    QTimer.singleShot(0, ide_start_panel)
                else:
                    ide_start_reload()
            else:
                print("Startup check is disabled")
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON file: {e}")
        except Exception as e:
            print(f"Error loading settings: {e}")
    else:
        print(f"Settings file not found at: {settings_path}")

def add_menu_command():
    """
    Add Python IDE command to Nuke menu.
    (Deprecated - menu.py now handles menu creation)
    """
    import nuke
    my_tools_menu = nuke.menu("Nuke").addMenu("Python")
    my_tools_menu.addCommand("Python IDE", ide_start_reload)

def create_panel():
    """
    Create Python IDE as a dockable panel in Nuke.
    Returns the panel widget.
    """
    from editor import editor_window
    import importlib
    importlib.reload(editor_window)

    
    app = QApplication.instance() or QApplication(sys.argv)

    existing = _find_editor_instance(app, editor_window.EditorApp)
    if existing:
        if not getattr(existing, "as_panel", False):
            _show_instance_message(
                "Python IDE is already open as a window.\n"
                "Close the window before opening a panel."
            )
            return None
        return existing

    progress = _create_progress(app)
    progress.setLabelText("Loading editor modules...")
    progress.setValue(1)
    app.processEvents()

    def update_progress(value, message):
        progress.setValue(value)
        progress.setLabelText(message)
        app.processEvents()

    progress.setLabelText("Initializing UI...")
    progress.setValue(2)
    app.processEvents()

    panel = editor_window.EditorApp(as_panel=True, progress_callback=update_progress)
    progress.setLabelText("Finalizing...")
    progress.setValue(6)
    app.processEvents()
    progress.close()
    return panel

def add_panel_to_pane():
    """
    Register and add Python IDE as a panel to Nuke's pane menu.
    This allows users to dock the IDE into Nuke's interface.
    """
    import nuke  # noqa: F401
    import nukescripts.panels as panels

    
    try:
        
        panels.registerWidgetAsPanel(
            'init_ide.create_panel',  
            'Python IDE',
            PANEL_ID
        )
        print("Python IDE registered as dockable panel")
    except Exception as e:
        print(f"Panel registration error: {e}")
