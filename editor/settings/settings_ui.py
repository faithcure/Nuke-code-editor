import subprocess
import json
import sys
from functools import partial

from pygments.styles import get_all_styles

try:
    import psutil
except Exception:
    psutil = None

try:
    import requests
except Exception:
    requests = None
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QListWidget, QStackedWidget, QWidget,
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QHBoxLayout, QFormLayout, QDialogButtonBox, QGroupBox, QTextEdit, QFrame, QFontComboBox, QFileDialog, QSpacerItem,
    QSizePolicy, QMessageBox, QProgressBar, QProgressDialog, QTableWidget, QTableWidgetItem, QHeaderView, QKeySequenceEdit,
    QScrollArea
)
from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtGui import QFontDatabase, QFont
import os
import time
import re
import importlib
import editor.settings.settings_ux
from editor.settings import settings_ux
from editor.core import PathFromOS, write_python_file
from editor.settings.panels import (
    build_general_panel,
    build_keyboard_panel,
    build_code_editor_panel,
    build_environment_panel,
    build_license_panel,
    build_github_panel,
    build_update_panel,
)
importlib.reload(editor.settings.settings_ux)


class ProcessManager(QThread):
    """Handles process execution with memory and timeout constraints."""
    process_error = Signal(str)
    process_completed = Signal(str)

    def __init__(self, memory_limit, timeout_limit, command):
        super().__init__()
        self.memory_limit = memory_limit  
        self.timeout_limit = timeout_limit  
        self.command = command  
        self._is_running = True

    def run(self):
        """Run the process and monitor its memory and timeout constraints."""
        try:
            process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            start_time = time.time()

            while self._is_running:
                
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout_limit:
                    process.terminate()
                    self.process_error.emit(f"Process timed out after {self.timeout_limit} seconds.")
                    return

                
                if psutil is None:
                    self.process_error.emit("psutil is required for process monitoring but is not installed.")
                    process.terminate()
                    return
                proc = psutil.Process(process.pid)
                memory_usage = proc.memory_info().rss / (1024 * 1024)
                if memory_usage > self.memory_limit:
                    process.terminate()
                    self.process_error.emit(f"Memory limit exceeded: {memory_usage:.2f} MB (limit: {self.memory_limit} MB)")
                    return

                
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    self.process_completed.emit(stdout.decode('utf-8') if stdout else stderr.decode('utf-8'))
                    return

                time.sleep(0.5)  
        except Exception as e:
            self.process_error.emit(f"Unexpected error: {str(e)}")

    def stop(self):
        """Stop the running process."""
        self._is_running = False

class ModuleInstallerThread(QThread):
    progress_updated = Signal(int, str)  
    download_info = Signal(str)  
    completed = Signal()  
    error_occurred = Signal(str)  

    def __init__(self, install_path, required_modules, python_path, upgrade=False):
        super().__init__()
        self.install_path = install_path
        self.required_modules = required_modules
        self.python_path = python_path
        self.upgrade = upgrade

    def run(self):
        try:
            for i, module in enumerate(self.required_modules):
                self.progress_updated.emit(i, f"Installing {module}...")

                
                command = [
                    self.python_path,
                    "-m",
                    "pip",
                    "install",
                    module,
                    "--target",
                    self.install_path,
                    "--progress-bar",
                    "off",
                ]
                if self.upgrade:
                    command.append("--upgrade")

                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                
                for line in process.stdout:
                    match = re.search(r"(\d+\.?\d*)\s?([kMG]B)\s?/?\s?(\d+\.?\d*)?\s?([kMG]B)?", line)
                    if match:
                        downloaded = match.group(1) + " " + match.group(2)
                        total = match.group(3) + " " + match.group(4) if match.group(3) else "unknown"
                        self.download_info.emit(f"Downloading {module}: {downloaded} of {total}")
                    if "Installing collected packages" in line:
                        self.download_info.emit(f"Installing package files for {module}...")

                
                process.wait()

                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args)

                time.sleep(0.5)  

            self.completed.emit()
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Error while installing {module}:\n{str(e)}")
        except Exception as ex:
            self.error_occurred.emit(f"Unexpected error:\n{str(ex)}")

class SettingsWindow(QMainWindow):
    SETTINGS_FILE = PathFromOS().settings_path

    def __init__(self, editor_window=None):
        super().__init__()
        self.editor_window = editor_window
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.status_label = None
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(
            """
            QLabel { color: white; }
            QSpinBox, QDoubleSpinBox {
                min-height: 30px;
                padding: 2px 6px;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 18px;
            }
            """
        )
        self.modules_path = os.path.join(PathFromOS().project_root, "third_party")
        self.current_sys_path = list(sys.path)
        self.__init_ui__()

    @staticmethod
    def find_python_executable():
        """Find system Python executable across all platforms"""
        if "PYTHON_HOME" in os.environ:
            python_path = os.path.join(os.environ["PYTHON_HOME"], "python.exe")
            if os.path.exists(python_path):
                return python_path

        user_home = os.path.expanduser("~")
        possible_paths = [
            
            os.path.join(user_home, "AppData", "Local", "Programs", "Python", "Python311", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Programs", "Python", "Python310", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Programs", "Python", "Python39", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Programs", "Python", "Python38", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Programs", "Python", "Python37", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Microsoft", "WindowsApps", "python.exe"),
            os.path.join(user_home, "anaconda3", "python.exe"),
            os.path.join(user_home, "miniconda3", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Continuum", "anaconda3", "python.exe"),
            os.path.join(user_home, "AppData", "Local", "Continuum", "miniconda3", "python.exe"),
            
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
            r"C:\Python39\python.exe",
            r"C:\Python38\python.exe",
            r"C:\Python37\python.exe",
            r"C:\Python36\python.exe",
            r"C:\Program Files\Python311\python.exe",
            r"C:\Program Files\Python310\python.exe",
            r"C:\Program Files\Python39\python.exe",
            r"C:\Program Files\Python38\python.exe",
            r"C:\Program Files (x86)\Python37\python.exe",
            r"C:\Program Files (x86)\Python36\python.exe",
            
            "/usr/bin/python3.11",
            "/usr/bin/python3.10",
            "/usr/bin/python3.9",
            "/usr/bin/python3.8",
            "/usr/bin/python3.7",
            "/usr/bin/python3.6",
            "/usr/bin/python3",
            "/usr/bin/python",
            "/usr/local/bin/python3.11",
            "/usr/local/bin/python3.10",
            "/usr/local/bin/python3.9",
            "/usr/local/bin/python3.8",
            "/usr/local/bin/python3.7",
            "/usr/local/bin/python3",
            "/usr/local/bin/python",
            "/opt/python3.11/bin/python3",
            "/opt/python3.10/bin/python3",
            "/opt/python3.9/bin/python3",
            "/opt/python3.8/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.9/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.8/bin/python3",
            
            os.path.join(os.environ.get("VIRTUAL_ENV", ""), "bin", "python"),
            os.path.join(os.environ.get("CONDA_PREFIX", ""), "bin", "python"),
            
            os.path.join(user_home, ".pyenv", "shims", "python"),
            os.path.join(user_home, ".pyenv", "versions", "3.11.0", "bin", "python"),
            os.path.join(user_home, ".pyenv", "versions", "3.10.0", "bin", "python"),
            os.path.join(user_home, ".pyenv", "versions", "3.9.0", "bin", "python"),
            os.path.join(user_home, ".pyenv", "versions", "3.8.0", "bin", "python"),
            os.path.join(user_home, ".pyenv", "versions", "3.7.0", "bin", "python"),
            
            r"D:\Python311\python.exe",
            r"D:\Python310\python.exe",
            r"D:\Python39\python.exe"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def __init_ui__(self):
        """Initialize UI components"""
        
        self.settings = self.load_settings()
        self.current_sys_path = list(sys.path)

        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search in settings...")
        self.search_box.textChanged.connect(self.filter_settings)

        
        self.category_list = QListWidget()
        self.category_list.addItems([
            "General",
            "Code Editor",
            "Environment",
            "Updates",
            "Keyboard",
            "License / Donation",
            "GitHub",
        ])
        self.category_list.setMinimumWidth(180)
        self.category_list.currentRowChanged.connect(self.display_category)

        
        self.settings_panels = QStackedWidget()
        self.settings_panels.addWidget(build_general_panel(self))
        self.settings_panels.addWidget(build_code_editor_panel(self))
        self.settings_panels.addWidget(build_environment_panel(self))
        self.settings_panels.addWidget(build_update_panel(self))
        self.settings_panels.addWidget(build_keyboard_panel(self))
        self.settings_panels.addWidget(build_license_panel(self))
        self.settings_panels.addWidget(build_github_panel(self))

        
        button_box = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        button_box.button(QDialogButtonBox.Ok).clicked.connect(self.save_and_close)
        button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_settings)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)

        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.search_box)  
        main_content_layout = QHBoxLayout()
        main_content_layout.addWidget(self.category_list, 1)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QFrame.NoFrame)
        self.settings_scroll.setWidget(self.settings_panels)
        main_content_layout.addWidget(self.settings_scroll, 3)
        main_layout.addLayout(main_content_layout)
        restart_note = QLabel("Note: Many settings take effect after restarting the IDE (close and reopen).")
        restart_note.setStyleSheet("color: #ff9900; font-size: 9pt;")
        restart_note.setWordWrap(True)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(restart_note, 1)
        bottom_row.addWidget(button_box, 0)
        main_layout.addLayout(bottom_row)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        
        self.apply_settings_to_widgets()
        self.refresh_dependency_status()
        self.category_list.setCurrentRow(0)
        self._wire_dirty_state()

    def refresh_dependency_status(self):
        try:
            from editor.dependencies import check_dependencies, required_modules
        except Exception:
            return None

        status = check_dependencies()
        if hasattr(self, "dependency_status_label") and self.dependency_status_label:
            if status["ok"]:
                self.dependency_status_label.setText("Everything is up to date.")
                self.dependency_status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
            else:
                self.dependency_status_label.setText("Updates or path fixes are needed.")
                self.dependency_status_label.setStyleSheet("color: #d9534f; font-weight: bold;")

        if hasattr(self, "dependency_details_box") and self.dependency_details_box:
            lines = []
            for package in required_modules():
                if package in status["missing"]:
                    lines.append(f"{package}: MISSING")
                elif package in status["path_missing"]:
                    lines.append(f"{package}: PATH NOT SET")
                else:
                    lines.append(f"{package}: OK")
            self.dependency_details_box.setPlainText("\n".join(lines))

        return status

    def filter_settings(self, search_text):
        """Highlights matching widgets based on the search text or resets styles when empty."""
        search_text = search_text.lower()

        DEFAULT_STYLE = "background-color: none; "  
        HIGHLIGHT_STYLE = "background-color: rgba(247, 153, 42, 0.5); "  

        for category_index in range(self.settings_panels.count()):
            panel = self.settings_panels.widget(category_index)
            found = False  

            for widget_type in [QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox]:
                for widget in panel.findChildren(widget_type):
                    widget_name = widget.objectName().lower() if widget.objectName() else ""
                    widget_text = widget.text().lower() if hasattr(widget, "text") else ""

                    if search_text:  
                        if search_text in widget_name or search_text in widget_text:
                            widget.setStyleSheet(HIGHLIGHT_STYLE)
                            found = True
                        else:
                            widget.setStyleSheet(DEFAULT_STYLE)
                    else:  
                        widget.setStyleSheet(DEFAULT_STYLE)

            if search_text:
                self.category_list.item(category_index).setHidden(not found)
            else:
                self.category_list.item(category_index).setHidden(False)

    def load_settings(self):
        """Loads settings from a JSON file if it exists, otherwise returns default settings."""
        if os.path.exists(self.SETTINGS_FILE):
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        else:
            return {}

    def save_settings(self):
        """Saves current widget states to a JSON file."""
        self.to_json()

    def general_settings(self):
        return build_general_panel(self)

    def keyboard_settings(self):
        return build_keyboard_panel(self)

    def on_shortcut_changed(self):
        """Called whenever a shortcut is changed via QKeySequenceEdit"""
        self.check_shortcut_conflicts()

    def restore_default_shortcuts(self):
        """Restore all shortcuts to their default values"""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore all keyboard shortcuts to their factory defaults?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for cmd_name, shortcut_edit in self.shortcut_editors.items():
                
                for category, commands in self.default_shortcuts.items():
                    for name, default_shortcut, description in commands:
                        if name == cmd_name:
                            shortcut_edit.setKeySequence(default_shortcut)
                            break

            self.conflict_label.setText("")
            QMessageBox.information(self, "Success", "All shortcuts have been restored to factory defaults.")

    def export_shortcuts_to_ini(self):
        """Export current shortcuts to .ini file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Shortcuts",
            os.path.join(os.path.expanduser("~"), ".nuke", "keyboard_shortcuts.ini"),
            "INI Files (*.ini)"
        )

        if file_path:
            try:
                import configparser
                config = configparser.ConfigParser()

                
                for row in range(self.shortcuts_table.rowCount()):
                    cmd_name = self.shortcuts_table.item(row, 0).text()
                    category = self.shortcuts_table.item(row, 1).text()
                    shortcut_edit = self.shortcuts_table.cellWidget(row, 2)
                    shortcut = shortcut_edit.keySequence().toString() if shortcut_edit else ""

                    if category not in config:
                        config[category] = {}

                    config[category][cmd_name] = shortcut

                with open(file_path, 'w') as configfile:
                    config.write(configfile)

                QMessageBox.information(self, "Success", f"Shortcuts exported to:\n{file_path}")

            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export shortcuts:\n{str(e)}")

    def import_shortcuts_from_ini(self):
        """Import shortcuts from .ini file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Shortcuts",
            os.path.join(os.path.expanduser("~"), ".nuke"),
            "INI Files (*.ini)"
        )

        if file_path:
            try:
                import configparser
                config = configparser.ConfigParser()
                config.read(file_path)

                
                for row in range(self.shortcuts_table.rowCount()):
                    cmd_name = self.shortcuts_table.item(row, 0).text()
                    category = self.shortcuts_table.item(row, 1).text()

                    if category in config and cmd_name in config[category]:
                        shortcut = config[category][cmd_name]
                        shortcut_edit = self.shortcuts_table.cellWidget(row, 2)
                        if shortcut_edit:
                            shortcut_edit.setKeySequence(shortcut)

                QMessageBox.information(self, "Success", f"Shortcuts imported from:\n{file_path}")
                self.check_shortcut_conflicts()

            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import shortcuts:\n{str(e)}")

    def check_shortcut_conflicts(self):
        """Check for duplicate shortcuts and warn user"""
        shortcuts_dict = {}
        conflicts = []

        for row in range(self.shortcuts_table.rowCount()):
            cmd_name = self.shortcuts_table.item(row, 0).text()
            shortcut_edit = self.shortcuts_table.cellWidget(row, 2)

            if shortcut_edit:
                shortcut = shortcut_edit.keySequence().toString()

                if shortcut and shortcut.strip():  
                    if shortcut in shortcuts_dict:
                        conflicts.append((shortcut, shortcuts_dict[shortcut], cmd_name))
                    else:
                        shortcuts_dict[shortcut] = cmd_name

        if conflicts:
            conflict_text = "⚠️ Shortcut conflicts detected:\n"
            for shortcut, cmd1, cmd2 in conflicts:
                conflict_text += f"  • {shortcut}: '{cmd1}' and '{cmd2}'\n"
            self.conflict_label.setText(conflict_text)
        else:
            self.conflict_label.setText("")

    def install_pygement_module(self):
        QMessageBox.information(
            self,
            "Install Disabled",
            "Online installation is disabled in this build to avoid breaking Nuke's embedded Python.\n\n"
            "Use the bundled dependencies in `CodeEditor_v02/third_party` or update the plugin package."
        )
        return

        install_path = os.path.join(PathFromOS().project_root, "third_party")
        required_modules = ["Pygments"]

        user_home = os.path.expanduser("~")
        nuke_dir = os.path.join(user_home, ".nuke")
        init_path = os.path.join(nuke_dir, "init.py")
        if not os.path.exists(install_path):
            os.makedirs(install_path)

        
        python_path = self.find_python_executable()

        if not python_path:
            QMessageBox.critical(
                self,
                "Python Not Found",
                "System Python could not be located. Please install Python or specify its path using the PYTHON_HOME environment variable."
            )
            return
        
        progress = QProgressDialog("Installing Pygments modules...", "Cancel", 0, len(required_modules))
        progress.setWindowTitle("Installation Progress")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        
        thread = ModuleInstallerThread(install_path, required_modules, python_path, upgrade=True)
        thread.progress_updated.connect(lambda value, text: (
            progress.setValue(value),
            progress.setLabelText(text)
        ))
        thread.download_info.connect(lambda info: progress.setLabelText(info))

        def on_completed():
            try:
                ide_init_path = os.path.join(os.path.dirname(init_path), "init_ide.py")  

                
                if not os.path.exists(ide_init_path):
                    ide_init_content = (
                        "# Added modules path\n"
                        "import sys\n"
                        f"sys.path.append({repr(install_path)})\n"
                    )
                    write_python_file(ide_init_path, ide_init_content, mode="w", encoding="utf-8", ensure_dir=True)

                
                if os.path.exists(init_path):
                    with open(init_path, "r+") as init_file:
                        content = init_file.read()
                        import_statement = "exec(open(os.path.join(os.path.dirname(__file__), 'init_ide.py')).read())"
                        if import_statement not in content:
                            init_file.write(f"\n# Import init_ide.py\n")
                            init_file.write(f"import os\n")
                            init_file.write(f"{import_statement}\n")

                QMessageBox.information(
                    self,
                    "Success",
                    "Modules installed and linked successfully."
                )

            except Exception:
                QMessageBox.warning(
                    self,
                    "Error",
                    "An error occurred during the installation process."
                )

            progress.setValue(len(required_modules))
            self.prompt_restart_nuke()

        thread.completed.connect(on_completed)
        thread.error_occurred.connect(lambda error: QMessageBox.critical(self, "Installation Error", error))
        progress.canceled.connect(lambda: thread.terminate())
        thread.start()

    def code_editor_settings(self):
        return build_code_editor_panel(self)

    def environment_settings(self):
        return build_environment_panel(self)

    def licence_settings(self):
        return build_license_panel(self)

    def github_settings(self):
        return build_github_panel(self)

    def validate_credentials(self, username_input, token_input):
        """
        Validates the GitHub username and token from the user.
        """
        username = username_input.text().strip()
        token = token_input.text().strip()

        if not username or not token:
            QMessageBox.warning(self, "Validation Failed", "Username or token cannot be empty.")
            return

        if self.check_github_credentials(username, token):
            
            self.status_label.setText("Validated successfully")
            self.status_label.setStyleSheet("color: #8bc34a; font-weight: bold;")  
            
        else:
            
            self.status_label.setText("Validation failed")
            self.status_label.setStyleSheet("color: #ff6f61; font-weight: bold;")  
            QMessageBox.critical(self, "Validation Failed", "Invalid GitHub credentials. Please try again.")

    def check_github_credentials(self, username, token):
        """
        Checks the GitHub username and token.
        """
        if not username or not token:
            QMessageBox.critical(
                self,
                "Validation Error",
                "Please enter both username and token."
            )
            return False

        try:
            if requests is None:
                QMessageBox.critical(
                    self,
                    "Dependency Missing",
                    "The 'requests' package is required for GitHub validation."
                )
                return False
            url = "https://api.github.com/user"
            response = requests.get(url, auth=(username, token))

            if response.status_code == 200:
                
                api_username = response.json().get('login', '')

                
                if username == api_username:
                    QMessageBox.information(
                        self,
                        "Validation Successful",
                        f"Welcome, {api_username}!, The GitHub credentials are valid."
                    )
                    return True
                else:
                    QMessageBox.critical(
                        self,
                        "Username Mismatch",
                        f"Provided username does not match the token owner.\n"
                        f"Expected: {api_username}\nProvided: {username}"
                    )
                    return False
            elif response.status_code == 401:
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    "Authentication failed. Please check your username and token."
                )
                return False
            else:
                QMessageBox.critical(
                    self,
                    "Authentication Error",
                    f"Unexpected error: {response.json().get('message', 'Unknown error')}."
                )
                return False
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Network Error", f"An error occurred: {e}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"An error occurred: {e}")
            return False

    def show_fix_instructions(self, install_path):
        """
        Provide a clear explanation and option to automatically add the modules path.
        Ensures compatibility across all platforms (Windows, macOS, Linux).
        """
        confirmation = QMessageBox.question(
            self,
            "Fix Path Confirmation",
            f"The required modules path is not in sys.path. It may be corrupted.\n\n"
            f"We can correct the following files:\n\n"
            f"{install_path}\n\n"
            "Would you like to proceed with this change?\n\n"
            "You will need to restart Nuke to apply the changes.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            QMessageBox.information(
                self,
                "Fix Path Instructions",
                "This build does not write to your Nuke user scripts automatically.\n\n"
                "To fix the modules path safely:\n"
                "1) Ensure the plugin is loaded via your Nuke user `init.py`:\n"
                "   `nuke.pluginAddPath('./CodeEditor_v02')`\n"
                "2) Restart Nuke.\n\n"
                f"Expected bundled modules path:\n{install_path}"
            )
        else:
            QMessageBox.information(
                self,
                "Action Canceled",
                "The path was not added. If you change your mind, you can use the Fix Path option again."
            )

    def install_github_modules(self):
        """
        Install GitHub modules to the 'modules' directory using a background thread and show detailed progress.
        After installation, add the 'modules' path to sys.path in the .nuke/init.py file and ask the user to restart Nuke.
        """
        
        QMessageBox.information(
            self,
            "Install Disabled",
            "Online installation is disabled in this build to avoid breaking Nuke's embedded Python.\n\n"
            "Use the bundled dependencies in `CodeEditor_v02/third_party` or update the plugin package."
        )
        return

        
        user_home = os.path.expanduser("~")
        nuke_dir = os.path.join(user_home, ".nuke")
        init_path = os.path.join(nuke_dir, "init.py")

        
        if not os.path.exists(install_path):
            os.makedirs(install_path)

        
        python_path = self.find_python_executable()
        if not python_path:
            QMessageBox.critical(
                self,
                "Python Not Found",
                "System Python could not be located. Please install Python or specify its path using the PYTHON_HOME environment variable."
            )
            return

        
        progress = QProgressDialog("Installing GitHub modules...", "Cancel", 0, len(required_modules))
        progress.setWindowTitle("Installation Progress")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        
        thread = ModuleInstallerThread(install_path, required_modules, python_path)
        thread.progress_updated.connect(lambda value, text: (
            progress.setValue(value),
            progress.setLabelText(text)
        ))
        thread.download_info.connect(lambda info: progress.setLabelText(info))

        def on_completed():
            try:
                ide_init_path = os.path.join(os.path.dirname(init_path), "init_ide.py")  

                
                if not os.path.exists(ide_init_path):
                    ide_init_content = (
                        "# Added modules path\n"
                        "import sys\n"
                        f"sys.path.append({repr(install_path)})\n"
                    )
                    write_python_file(ide_init_path, ide_init_content, mode="w", encoding="utf-8", ensure_dir=True)

                
                if os.path.exists(init_path):
                    with open(init_path, "r+") as init_file:
                        content = init_file.read()
                        import_statement = "exec(open(os.path.join(os.path.dirname(__file__), 'init_ide.py')).read())"
                        if import_statement not in content:
                            init_file.write(f"\n# Import init_ide.py\n")
                            init_file.write(f"import os\n")
                            init_file.write(f"{import_statement}\n")

                QMessageBox.information(
                    self,
                    "Success",
                    "Modules installed and linked successfully."
                )

            except Exception:
                QMessageBox.warning(
                    self,
                    "Error",
                    "An error occurred during the installation process."
                )

            progress.setValue(len(required_modules))
            self.prompt_restart_nuke()

        thread.completed.connect(on_completed)
        thread.error_occurred.connect(lambda error: QMessageBox.critical(self, "Installation Error", error))
        progress.canceled.connect(lambda: thread.terminate())
        thread.start()

    def update_github_modules(self, install_path, required_modules):
        """
        Update the specified GitHub modules in the 'modules' directory.
        Args:
            install_path (str): Path to the folder where modules are installed.
            required_modules (list): List of required module names to update.
        """
        QMessageBox.information(
            self,
            "Update Disabled",
            "Automatic updates via pip are disabled because they can install incompatible binary wheels "
            "and break Nuke's embedded Python.\n\n"
            "To update dependencies safely, update the plugin package (replace `CodeEditor_v02/third_party`) "
            "with a known-good release that matches your Nuke/Python version."
        )
        return
        
        python_path = self.find_python_executable()
        if not python_path:
            QMessageBox.critical(
                self,
                "Python Not Found",
                "System Python could not be located. Please install Python or specify its path using the PYTHON_HOME environment variable."
            )
            return

        
        progress = QProgressDialog("Updating GitHub modules...", "Cancel", 0, len(required_modules))
        progress.setWindowTitle("Update Progress")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        
        thread = ModuleInstallerThread(install_path, required_modules, python_path)

        def on_completed():
            progress.setValue(len(required_modules))
            QMessageBox.information(
                self,
                "Update Complete",
                "GitHub modules have been successfully updated."
            )

        def on_error(error):
            progress.close()
            QMessageBox.critical(self, "Update Error", error)

        thread.progress_updated.connect(lambda value, text: (
            progress.setValue(value),
            progress.setLabelText(text)
        ))

        def on_cancel():
            if thread.isRunning():
                thread.terminate()
            progress.close()

        thread.download_info.connect(lambda info: progress.setLabelText(info))
        thread.completed.connect(on_completed)
        thread.error_occurred.connect(on_error)
        progress.canceled.connect(lambda: thread.terminate())
        progress.canceled.connect(on_cancel)
        thread.start()

    def update_vendor_modules(self):
        """Update bundled third-party modules used by the editor."""
        QMessageBox.information(
            self,
            "Update Disabled",
            "Automatic updates via pip are disabled because they can install incompatible binary wheels "
            "and break Nuke's embedded Python.\n\n"
            "To update dependencies safely, update the plugin package (replace `CodeEditor_v02/third_party`) "
            "with a known-good release that matches your Nuke/Python version."
        )
        return


    def prompt_restart_nuke(self):
        """
        Prompt the user to restart Nuke after module installation, explaining why it is necessary.
        """
        QMessageBox.information(
            self,
            "Restart Nuke",
            "Please restart Nuke manually to apply changes.\n\n"
            "Automatic restart is disabled to avoid data loss."
        )

    def restart_nuke(self):
        """
        Restart Nuke by terminating the current process and starting a new instance.
        """
        QMessageBox.information(
            self,
            "Restart Nuke",
            "Automatic restart is disabled. Please close and reopen Nuke manually."
        )

    def check_github_modules(self, install_path, required_modules):
        """
        Check if required modules are present in the specified folder.
        Args:
            install_path (str): Path to the target folder where modules are installed.
            required_modules (list): List of required module names.
        Returns:
            bool: True if all required modules are found, False otherwise.
        """
        if not os.path.exists(install_path):
            return False

        installed_modules = os.listdir(install_path)  
        for module in required_modules:
            if not any(module.lower() in item.lower() for item in installed_modules):
                return False
        return True

    def other_apps_settings(self):
        return None

    def load_licence_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load License File", "", "License Files (*.lic)")
        if file_name:
            QMessageBox.information(self, "License", "License management is not enabled in this build.")

    
    def apply_settings(self):
        self.save_settings()
        self._apply_runtime_settings()
        self._dirty = False

    def _apply_runtime_settings(self):
        if self.editor_window and hasattr(self.editor_window, "apply_runtime_settings"):
            self.editor_window.apply_runtime_settings()

    def reset_settings(self):
        """Reset all settings to default values"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?\n\n"
            "This will:\n"
            "• Reset all editor preferences\n"
            "• Reset all keyboard shortcuts\n"
            "• Clear GitHub credentials\n"
            "• Remove all customizations\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            
            if os.path.exists(self.SETTINGS_FILE):
                os.remove(self.SETTINGS_FILE)

            
            self.settings = {}

            
            self.apply_settings_to_widgets()

            
            if hasattr(self, 'restore_default_shortcuts'):
                self.restore_default_shortcuts()

            QMessageBox.information(
                self,
                "Settings Reset",
                "All settings have been reset to default values.\n\n"
                "Please restart the application for all changes to take effect."
            )
            self._dirty = False

    def save_and_close(self):
        self.save_settings()
        self._dirty = False
        self.close()

    def display_category(self, index):
        self.settings_panels.setCurrentIndex(index)

    def closeEvent(self, event):
        if getattr(self, "_dirty", False):
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to apply them before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.apply_settings()
                event.accept()
                return
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
        event.accept()

    def _mark_dirty(self, *_args):
        self._dirty = True

    def _wire_dirty_state(self):
        self._dirty = False
        for panel_index in range(self.settings_panels.count()):
            panel = self.settings_panels.widget(panel_index)
            for widget in panel.findChildren(QLineEdit):
                widget.textChanged.connect(self._mark_dirty)
            for widget in panel.findChildren(QCheckBox):
                widget.stateChanged.connect(self._mark_dirty)
            for widget in panel.findChildren(QComboBox):
                widget.currentIndexChanged.connect(self._mark_dirty)
            for widget in panel.findChildren(QSpinBox):
                widget.valueChanged.connect(self._mark_dirty)
            for widget in panel.findChildren(QDoubleSpinBox):
                widget.valueChanged.connect(self._mark_dirty)
            for widget in panel.findChildren(QFontComboBox):
                widget.currentFontChanged.connect(self._mark_dirty)
            for widget in panel.findChildren(QKeySequenceEdit):
                widget.keySequenceChanged.connect(self._mark_dirty)

    def apply_settings_to_widgets(self):
        """
        Applies settings from the loaded JSON file to the widgets in the settings panels.

        This function maps each widget's objectName to the corresponding setting key in the JSON data.
        The settings panels are indexed in the following order:
        - 0: General
        - 1: Keyboard
        - 2: Code Editor
        - 3: Environment
        - 4: Licence
        - 5: GitHub
        - 6: GitHub
        """

        
        general_panel = self.settings_panels.widget(0)
        general_data = self.settings.get("General", {})
        for widget in general_panel.findChildren(QCheckBox):
            if widget.objectName() and widget.objectName() in general_data:
                widget.setChecked(general_data[widget.objectName()])
        for widget in general_panel.findChildren(QComboBox):
            if widget.objectName() and widget.objectName() in general_data:
                index = widget.findText(general_data[widget.objectName()])
                if index != -1:  
                    widget.setCurrentIndex(index)

        
        keyboard_data = self.settings.get("Keyboard", {})
        if hasattr(self, 'shortcut_editors') and keyboard_data:
            for cmd_name, shortcut_value in keyboard_data.items():
                if cmd_name in self.shortcut_editors:
                    self.shortcut_editors[cmd_name].setKeySequence(shortcut_value)

        
        code_editor_panel = self.settings_panels.widget(1)  
        code_editor_data = self.settings.get("Code Editor", {})
        for widget in code_editor_panel.findChildren(QFontComboBox):
            font_family = code_editor_data.get(widget.objectName(), "Consolas")  
            widget.setCurrentFont(QFont(font_family))  
        for widget in code_editor_panel.findChildren(QSpinBox):
            widget.setValue(code_editor_data.get(widget.objectName(), widget.value()))
        for widget in code_editor_panel.findChildren(QDoubleSpinBox):
            widget.setValue(float(code_editor_data.get(widget.objectName(), widget.value())))
        inverted_code_editor_flags = {
            "disable_smart_compilation",
            "disable_completion_popup",
            "disable_suggestion",
            "disable_fuzzy_compilation",
            "disable_node_completer",
        }
        for widget in code_editor_panel.findChildren(QCheckBox):
            if not widget.objectName():
                continue
            if widget.objectName() in inverted_code_editor_flags:
                if widget.objectName() in code_editor_data:
                    widget.setChecked(not code_editor_data.get(widget.objectName(), False))
            else:
                widget.setChecked(code_editor_data.get(widget.objectName(), widget.isChecked()))

        
        environment_panel = self.settings_panels.widget(2)  
        environment_data = self.settings.get("Environment", {})
        for widget in environment_panel.findChildren(QSpinBox):
            widget.setValue(environment_data.get(widget.objectName(), widget.value()))
        for widget in environment_panel.findChildren(QLineEdit):
            widget.setText(environment_data.get(widget.objectName(), widget.text()))

        
        licence_panel = self.settings_panels.widget(5)  
        licence_data = self.settings.get("Licence", {})
        for widget in licence_panel.findChildren(QLineEdit):
            widget.setText(licence_data.get(widget.objectName(), widget.text()))

        
        github_panel = self.settings_panels.widget(6)  
        github_data = self.settings.get("Github", {})
        for widget in github_panel.findChildren(QLineEdit):
            widget.setText(github_data.get(widget.objectName(), widget.text()))

        
        # Other Apps panel removed.

    def to_json(self):
        """Saves the current state of all widgets to the settings file."""
        settings_data = {}

        
        general_data = {}
        general_panel = self.settings_panels.widget(0)  
        for widget in general_panel.findChildren(QCheckBox):
            if widget.objectName():
                general_data[widget.objectName()] = widget.isChecked()
        for widget in general_panel.findChildren(QComboBox):  
            if widget.objectName():
                general_data[widget.objectName()] = widget.currentText()  
        settings_data["General"] = general_data

        
        keyboard_data = {}
        if hasattr(self, 'shortcuts_table'):
            for row in range(self.shortcuts_table.rowCount()):
                cmd_name = self.shortcuts_table.item(row, 0).text()
                shortcut_edit = self.shortcuts_table.cellWidget(row, 2)
                if shortcut_edit:
                    shortcut = shortcut_edit.keySequence().toString()
                    keyboard_data[cmd_name] = shortcut
        settings_data["Keyboard"] = keyboard_data

        
        code_editor_data = {}
        code_editor_panel = self.settings_panels.widget(1)  
        for widget in code_editor_panel.findChildren(QFontComboBox):
            if widget.objectName():
                code_editor_data[widget.objectName()] = widget.currentFont().family()
        for widget in code_editor_panel.findChildren(QSpinBox):
            if widget.objectName():
                code_editor_data[widget.objectName()] = widget.value()
        for widget in code_editor_panel.findChildren(QDoubleSpinBox):
            if widget.objectName():
                code_editor_data[widget.objectName()] = float(widget.value())
        inverted_code_editor_flags = {
            "disable_smart_compilation",
            "disable_completion_popup",
            "disable_suggestion",
            "disable_fuzzy_compilation",
            "disable_node_completer",
        }
        for widget in code_editor_panel.findChildren(QCheckBox):
            if not widget.objectName():
                continue
            if widget.objectName() in inverted_code_editor_flags:
                code_editor_data[widget.objectName()] = not widget.isChecked()
            else:
                code_editor_data[widget.objectName()] = widget.isChecked()
        settings_data["Code Editor"] = code_editor_data

        
        environment_data = {}
        environment_panel = self.settings_panels.widget(2)  
        for widget in environment_panel.findChildren(QSpinBox):
            if widget.objectName():
                environment_data[widget.objectName()] = widget.value()
        for widget in environment_panel.findChildren(QLineEdit):
            if widget.objectName():
                environment_data[widget.objectName()] = widget.text()
        settings_data["Environment"] = environment_data

        
        licence_data = {}
        licence_panel = self.settings_panels.widget(5)  
        for widget in licence_panel.findChildren(QLineEdit):
            if widget.objectName():
                licence_data[widget.objectName()] = widget.text()
        settings_data["Licence"] = licence_data

        
        github_data = {}
        github_panel = self.settings_panels.widget(6)  
        for widget in github_panel.findChildren(QLineEdit):
            if widget.objectName():
                github_data[widget.objectName()] = widget.text()
        settings_data["Github"] = github_data

        
        # Other Apps panel removed.

        
        with open(self.SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(settings_data, file, indent=4, ensure_ascii=False)



def launch_settings(editor_window=None):
    """Launch settings window in Nuke environment."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    
    for widget in app.topLevelWidgets():
        if isinstance(widget, SettingsWindow):
            widget.editor_window = editor_window
            widget.raise_()
            widget.activateWindow()
            return widget

    
    settings_window = SettingsWindow(editor_window=editor_window)
    settings_window.show()
    settings_window.raise_()
    settings_window.activateWindow()

    
    return settings_window
