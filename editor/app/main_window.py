import ast
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from functools import partial
from PySide2.QtCore import QPropertyAnimation, QEasingCurve
from PySide2.QtCore import QStringListModel
from PySide2.QtGui import QIcon, QKeySequence
from PySide2.QtGui import QPixmap, QPainter, QPainterPath, QBrush
from PySide2.QtGui import QTextCursor, QGuiApplication
from PySide2.QtWidgets import *
from PySide2.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QGraphicsDropShadowEffect, QFrame
import editor.code_editor
import editor.core
import editor.output
import editor.ui.dialogs.new_nuke_project
import editor.ui.dialogs.searchDialogs
import editor.settings.github_utils
import editor.ui.toolbars.main_toolbar
from editor.core import PathFromOS, CodeEditorSettings, write_python_file
from editor.code_editor import CodeEditor
from PySide2.QtWidgets import QTextEdit, QMainWindow, QPushButton, QHBoxLayout, QWidget, QApplication
from PySide2.QtCore import Qt, QRect, QSize, QTimer
from PySide2.QtGui import QColor, QTextCharFormat, QFont
import traceback
import platform
import socket
import nuke
from editor.ui.dialogs.new_nuke_project import NewNukeProjectDialog
# from init_ide import settings_path
from editor.window.file_ops import FileOpsMixin
from editor.window.run_ops import RunOpsMixin
from editor.window.tab_ops import TabOpsMixin
from editor.window.layout_ops import LayoutOpsMixin
from editor.window.menu_ops import MenuOpsMixin
from editor.window.workspace_ops import WorkspaceOpsMixin
importlib.reload(editor.core)
importlib.reload(editor.code_editor)
importlib.reload(editor.output)
importlib.reload(editor.ui.dialogs.new_nuke_project)
importlib.reload(editor.ui.dialogs.searchDialogs)
importlib.reload(editor.settings.github_utils)
importlib.reload(editor.ui.toolbars.main_toolbar)
from editor.code_editor import PygmentsHighlighter
from editor.ui.toolbars.main_toolbar import MainToolbar

class EditorApp(QMainWindow, FileOpsMixin, RunOpsMixin, TabOpsMixin, LayoutOpsMixin, MenuOpsMixin, WorkspaceOpsMixin):
    """
    Main application window for the Nuke Code Editor.

    Features:
    - Provides a custom integrated development environment for Python and Nuke scripting.
    - Includes toolbar, status bar, dock widgets, and tab-based editor functionalities.
    - Supports creating, opening, editing, and saving Python and Nuke script files.
    - Includes additional features such as a workspace explorer, outliner, and customizable UI components.
    """

    def __init__(self, parent=None, as_panel=False, progress_callback=None):
        super().__init__(parent)

        self.setProperty("codeeditor_v02_instance", True)

        # Store panel mode flag
        self.as_panel = as_panel
        self._progress_callback = progress_callback
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        # Initialize the main toolbar
        self._update_startup_progress(3, "Loading toolbar...")
        MainToolbar.create_toolbar(self)

        # Load settings
        self._update_startup_progress(4, "Loading settings...")
        self.settings = CodeEditorSettings()
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # Window title and initial properties
        self.empty_project_win_title = "Nuke Code Editor (Beta): "  # Default title for an empty project
        self.setWindowTitle("Nuke Code Editor (Beta): Empty Project**")  # Title will change with Open and New projects

        # Only set geometry and center if running as standalone window
        if not as_panel:
            self.setGeometry(100, 100, 1200, 800)

            # Center the window on the screen
            try:
                qr = self.frameGeometry()
                screen = QGuiApplication.primaryScreen()
                cp = screen.availableGeometry().center()
                qr.moveCenter(cp)
                self.move(qr.topLeft())
            except:
                # If centering fails (e.g., in panel mode), just continue
                pass

        # Variables for new project and file operations
        self.project_dir = None # Current project directory
        self.current_file_path = None  # Current file

        # Create and configure the status bar
        self.status_bar = self.statusBar()  # Status bar oluşturma
        self.status_bar.showMessage("Ready")  # İlk mesajı göster
        self.font_size_label = QLabel(f"Font Size: {self.settings.main_font_size} | ", self)
        self.status_bar.addPermanentWidget(self.font_size_label)
        self.status_bar = self.statusBar()

        # Add a label for replace operations on the right side
        self.replace_status_label = QLabel()
        self.status_bar.addPermanentWidget(self.replace_status_label)  # Add to the right corner
        self.replace_status_label.setText("Status")  # Initial message

        # Dependency status indicator
        self.dependency_status_dot = QLabel()
        self.dependency_status_dot.setFixedSize(10, 10)
        self.dependency_status_dot.setStyleSheet("background-color: #999999; border-radius: 5px;")
        self.dependency_status_label = QLabel("Deps: ...")
        self.status_bar.addPermanentWidget(self.dependency_status_dot)
        self.status_bar.addPermanentWidget(self.dependency_status_label)
        self.refresh_dependency_status()

        # Project settings paths and other configurations
        self.item_colors = {} # Dictionary to manage item-specific colors
        self.color_settings_path = os.path.join(PathFromOS().assets_path, "item_colors.json")
        self.settings_path = os.path.join(PathFromOS().settings_db, "settings.json")

        # Create a tabbed editor (Custom Tab Widget with enhanced features)
        self._tab_widgets = []
        self._tab_splitter = None
        self.python_icon = QIcon(os.path.join(PathFromOS().icons_path, 'python_tab.svg'))
        self.tab_widget = self._create_tab_widget()

        # Close button and icon settings
        self.close_icon = os.path.join(PathFromOS().icons_path, 'new_file.png')  # Ensure the path is correct
        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                
            }}

            QTabBar::tab {{
                background-color: #2B2B2B;
                color: #B0B0B0;
                padding: 5px 10px;
                border: none;
                font-size: 10pt;
                min-width: 150px;  /* Genişlik ayarı */
                min-height: 15px;  /* Yükseklik ayarı */
            }}

            QTabBar::tab:selected {{
                background-color: #3C3C3C;
                color: #FFFFFF;
                border-bottom: 2px solid #3C88E3;
            }}
            
            QTabBar::tab:!selected {{
                background-color: #323232;
            }}
            QTabBar::tab:hover {{
                background-color: #3C3C3C;
                color: #E0E0E0;
            }}
            
        """)

        self.setCentralWidget(self.tab_widget)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        # Create the top menu
        self._update_startup_progress(5, "Building menus and docks...")
        self.create_menu()

        # Dockable lists
        self.create_docks()

        # Load colors at startup
        self.load_colors_from_file()

        # Recent projects are stored as a JSON list
        self.recent_projects_list = []
        # self.recent_projects_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "./",  "assets", "recent_projects.json")
        self.recent_projects_path = os.path.join(PathFromOS().json_path, "recent_projects.json")
        # Load colors and recent projects
        self.load_recent_projects()
        last_project_loaded = self.load_last_project()

        # If we can't (or shouldn't) resume a project, start with no editor tabs.
        # CustomTabWidget will show its welcome screen instead.
        if last_project_loaded:
            self.add_new_tab("untitled.py", initial_content=CodeEditorSettings().temp_codes)
        else:
            try:
                if hasattr(self.tab_widget, "check_and_show_welcome"):
                    self.tab_widget.check_and_show_welcome()
            except Exception:
                pass
        self.create_bottom_tabs() # Conolse / Output Widgets
        # Define dynamic shortcuts from settings
        run_shortcut = QShortcut(QKeySequence(self.settings.get_shortcut("Execute Selected or All")), self)
        run_shortcut.activated.connect(self.run_code)
        # Replace shortcut
        self.replace_shortcut = QShortcut(QKeySequence(self.settings.get_shortcut("Replace")), self)
        self.replace_shortcut.activated.connect(lambda: self.show_search_dialog(show_replace=True))

        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._on_autosave_timeout)
        self.apply_runtime_settings()

    def _open_project_default_file(self, project_dir):
        if not project_dir:
            return

        candidates = (
            os.path.join(project_dir, "__init__.py"),
            os.path.join(project_dir, "init.py"),
            os.path.join(project_dir, "menu.py"),
        )
        for path in candidates:
            try:
                if os.path.exists(path):
                    self.add_new_tab(path)
                    return
            except Exception:
                continue

    def _update_startup_progress(self, value, message):
        if self._progress_callback:
            try:
                self._progress_callback(value, message)
            except Exception as exc:
                print(f"[Startup] Progress callback failed: {exc}", file=sys.stderr)

    def apply_runtime_settings(self):
        self.settings = CodeEditorSettings()
        self._apply_editor_runtime_settings()
        self._configure_autosave_timer()

    def _apply_editor_runtime_settings(self):
        try:
            tab_widgets = self._all_tab_widgets()
        except Exception:
            tab_widgets = []

        for tab_widget in tab_widgets:
            try:
                for i in range(tab_widget.count()):
                    editor = tab_widget.widget(i)
                    if not isinstance(editor, CodeEditor):
                        continue
                    editor.settings = CodeEditorSettings()
                    editor.ctrl_wheel_enabled = editor.settings.ctrlWheel
                    editor.setFont(QFont(editor.settings.main_default_font, editor.settings.main_font_size))
                    editor.apply_tab_settings()
                    editor.set_line_spacing(editor.settings.line_spacing_size)
            except Exception:
                continue

    def _configure_autosave_timer(self):
        enable = bool(getattr(self.settings, "enable_autosave", False))
        minutes = getattr(self.settings, "autosave_interval", 5)
        try:
            minutes = int(minutes)
        except Exception:
            minutes = 5
        minutes = max(1, min(60, minutes))
        self._autosave_timer.stop()
        if enable:
            self._autosave_timer.start(minutes * 60 * 1000)

    def _on_autosave_timeout(self):
        try:
            self.settings = CodeEditorSettings()
            self._configure_autosave_timer()
        except Exception:
            pass
        try:
            self.autosave_all_modified_files()
        except Exception:
            pass

    def keyPressEvent(self, event):
        """
        Captures key press events and handles specific shortcuts.

        Args:
            event (QKeyEvent): The key event triggered by the user.
        """
        if event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier:
            self.run_code()
        else:
            super().keyPressEvent(event)
        super().keyPressEvent(event)

    def mark_as_modified(self, dock, file_path):
        """
        Marks a file as modified by appending '*' to the title.

        Args:
            dock (QDockWidget): The dock widget containing the file.
            file_path (str): Path to the file being modified.
        """
        if dock.windowTitle()[-1] != '*':
            dock.setWindowTitle(f"{os.path.basename(file_path)}*")

    def browse_directory(self, line_edit_widget):
        """Open directory browser and set selected path to the given QLineEdit"""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if directory:
            # Normalize path for cross-platform compatibility
            normalized_path = os.path.normpath(directory)
            line_edit_widget.setText(normalized_path)

    def new_project_dialog(self):
        """Yeni proje oluşturmak için diyalog kutusu."""
        self.allowed_pattern = r'^[a-zA-Z0-9_ ]+$'
        bg_image_path = os.path.join(PathFromOS().icons_path, 'nuke_logo_bg_01.png')
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setModal(True)
        new_project_dialog_size = QSize(500, 300)  # Yüksekliği artırıldı
        dialog.resize(new_project_dialog_size)

        # Gölge efekti
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(40)
        shadow_effect.setOffset(0, 12)  # Gölge aşağı kaydırıldı
        shadow_effect.setColor(QColor(0, 0, 0, 100))
        dialog.setGraphicsEffect(shadow_effect)

        # Ana layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        # Arka plan çerçevesi
        background_frame = QFrame(dialog)
        background_frame.setStyleSheet("""
            QFrame {
                background-color: rgb(50, 50, 50);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 9px;
            }
        """)

        # İçerik yerleşimi
        inner_layout = QVBoxLayout(background_frame)
        inner_layout.setContentsMargins(30, 30, 30, 20)
        layout.addWidget(background_frame)

        # İmajı yükle ve yuvarlak köşeli bir pixmap oluştur
        pixmap = QPixmap(bg_image_path)
        rounded_pixmap = QPixmap(pixmap.size())
        rounded_pixmap.fill(Qt.transparent)

        # Yuvarlak köşe maskesi uygulama
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRect(0, 0, pixmap.width(), pixmap.height()), 9, 9)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        # Yuvarlatılmış pixmap'i image_label içinde göster
        image_label = QLabel(background_frame)
        image_label.setPixmap(rounded_pixmap)
        image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        image_label.setFixedSize(dialog.size())

        # Başlık
        title_label = QLabel("Create New Project", background_frame)
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setStyleSheet("""
            color: #CFCFCF;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Myriad';
            border: none;
            background-color: transparent;
        """)
        inner_layout.addWidget(title_label)

        # Başlık altındaki boşluk
        inner_layout.addSpacing(20)

        # Proje ismi giriş alanı
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Enter Project Name")
        self.project_name_input.setMaxLength(20)  # Maksimum 20 karakter
        self.project_name_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: #E0E0E0;
                padding: 10px;
                padding-right: 40px;  /* Sağ tarafta karakter sayacı için boşluk */
                border: 1px solid #5A5A5A;
                border-radius: 8px;
            }
        """)
        inner_layout.addWidget(self.project_name_input)

        # Giriş doğrulama işlevi
        def validate_project_name():
            # İzin verilen karakterler

            if re.match(self.allowed_pattern, self.project_name_input.text()) and self.project_name_input.text() != "":
                # Geçerli giriş olduğunda orijinal stile dön
                self.project_name_input.setStyleSheet("""
                    QLineEdit {
                        background-color: rgba(255, 255, 255, 0.08);
                        color: #E0E0E0;
                        padding: 10px;
                        padding-right: 40px;
                        border: 1px solid #5A5A5A;
                        border-radius: 8px;
                    }
                """)
                self.project_desc.setText("Please ensure the correct information!")
            else:
                # Geçersiz giriş olduğunda kırmızı çerçeve
                self.project_name_input.setStyleSheet("""
                    QLineEdit {
                        background-color: rgba(255, 100, 100, 0.08);
                        color: #ff9991;
                        padding: 10px;
                        padding-right: 40px;
                        border: 1px solid red;
                        border-radius: 8px;
                    }
                """)
                self.project_desc.setText("Incorrect file name!")

        self.project_name_input.textChanged.connect(validate_project_name)

        # Character counter
        char_count_label = QLabel("0/20", self.project_name_input)
        if self.project_name_input.text() == "":
            char_count_label.setText("")
        char_count_label.setStyleSheet("""
            color: rgba(160, 160, 160, 0.6);  /* %60 opaklık */
            font-size: 12px;
            border: none;
            background: transparent;
        """)
        char_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        char_count_label.setFixedSize(60, 30)

        # Function that updates character counter
        def update_char_count():
            current_length = str(len(self.project_name_input.text()))
            current_length_count = current_length + "/20"

            char_count_label.setText(current_length_count)
            char_count_label.move(self.project_name_input.width() - 75,
                                  (self.project_name_input.height() - char_count_label.height()) // 2)

        # Counter update with `textChanged` signal
        self.project_name_input.textChanged.connect(update_char_count)

        # QLineEdit'ler arasında ve title ile boşluk bırak
        inner_layout.addSpacing(20)

        # Project directory entry field and "Browse" button
        self.project_dir_input = QLineEdit()
        self.project_dir_input.setPlaceholderText("Select Project Directory")
        self.project_dir_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: #E0E0E0;
                padding: 10px;  /* Orijinal kalınlık */
                border: 1px solid #5A5A5A;
                border-radius: 8px;
            }
        """)

        def validate_project_directory(): # Directory validation function
            if not self.project_dir_input.text():
                # Red frame if no directory is selected
                self.project_dir_input.setStyleSheet("""
                    QLineEdit {
                        background-color: rgba(255, 255, 255, 0.08);
                        color: #E0E0E0;
                        padding: 10px;
                        border: 1px solid red;
                        border-radius: 8px;
                    }
                """)
            else:
                # Return to original style when valid input
                self.project_dir_input.setStyleSheet("""
                    QLineEdit {
                        background-color: rgba(255, 255, 255, 0.08);
                        color: #E0E0E0;
                        padding: 10px;
                        border: 1px solid #5A5A5A;
                        border-radius: 8px;
                    }
                """)

        # Dir selection layout
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.project_dir_input)

        # Browse Button
        project_dir_button = QPushButton("Browse")
        project_dir_button.setFixedHeight(self.project_dir_input.sizeHint().height())  # QLineEdit ile aynı yükseklik
        project_dir_button.setStyleSheet("""
            QPushButton {
                background-color: #4E4E4E;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #6E6E6E;
            }
        """)
        dir_layout.addWidget(project_dir_button)
        inner_layout.addLayout(dir_layout)

        # Information Buttons
        self.project_desc = QLabel("Please ensure the correct information!")
        self.project_desc.setStyleSheet("""
            color: #A0A0A0;
            font-size: 11px;
            border: none;
            text-align: left;
            margin-top: 10px;
        """)
        inner_layout.addWidget(self.project_desc)

        # OK / Cancel Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # OK Button
        ok_button = QPushButton("OK")
        ok_button.setFixedSize(80, 30)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #808080; /* Gri renk */
                color: #FFFFFF;
                font-family: 'Myriad';
                border-radius: 10px;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #A9A9A9; /* Daha açık gri */
            }
        """)
        button_layout.addWidget(ok_button)

        # Cancel Button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedSize(80, 30)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #808080; /* Gri renk */
                color: #FFFFFF;
                font-family: 'Myriad';
                border-radius: 10px;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #A9A9A9; /* Daha açık gri */
            }
        """)
        button_layout.addWidget(cancel_button)

        # Label ile butonlar arasında boşluk ekleyin
        inner_layout.addSpacing(20)  # Label ile buton grubu arasında boşluk
        inner_layout.addLayout(button_layout)

        # Proje dizini seçiminde "Browse" butonuna tıklama işlemi
        project_dir_button.clicked.connect(lambda: self.browse_directory(self.project_dir_input))

        # OK butonuna tıklandığında proje oluşturma işlemi
        ok_button.clicked.connect(
            lambda: self.create_new_project(self.project_name_input.text(), self.project_dir_input.text(), dialog))

        # Cancel butonuna tıklanınca dialogu kapatma işlemi
        cancel_button.clicked.connect(dialog.close)
        dialog.exec_()

    def create_new_project(self, project_name, project_directory, dialog):
        """Create a new project directory and set project_dir to the new path."""
        # Validate project name
        project_name = project_name.strip()
        if not project_name:
            self.project_desc.setText("Please enter a project name!")
            self.project_name_input.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(255, 100, 100, 0.08);
                    color: #ff9991;
                    padding: 10px;
                    padding-right: 40px;
                    border: 1px solid red;
                    border-radius: 8px;
                }
            """)
            return

        # Validate project name format
        if not re.match(self.allowed_pattern, project_name):
            self.project_desc.setText("Invalid project name! Use only letters, numbers, spaces, and underscores.")
            self.project_name_input.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(255, 100, 100, 0.08);
                    color: #ff9991;
                    padding: 10px;
                    padding-right: 40px;
                    border: 1px solid red;
                    border-radius: 8px;
                }
            """)
            return

        # Validate directory
        project_directory = project_directory.strip()
        if not project_directory:
            self.project_desc.setText("Please select a project directory!")
            self.project_dir_input.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(255, 100, 100, 0.08);
                    color: #ff9991;
                    padding: 10px;
                    border: 1px solid red;
                    border-radius: 8px;
                }
            """)
            return

        # Check if directory exists
        if not os.path.exists(project_directory):
            self.project_desc.setText("Selected directory does not exist!")
            return

        # Normalize path for cross-platform compatibility
        project_path = os.path.normpath(os.path.join(project_directory, project_name))

        # Check if project already exists
        if os.path.exists(project_path):
            self.project_desc.setText("Project directory already exists!")
            QMessageBox.warning(dialog, "Project Exists", f"A project named '{project_name}' already exists in this directory.")
            return

        # Create project directory with error handling
        try:
            os.makedirs(project_path)

            # Create a basic __init__.py file
            init_file = os.path.join(project_path, "__init__.py")
            from datetime import datetime
            init_content = (
                f"# Project: {project_name}\n"
                f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"# Python Code Editor - Custom Project\n"
                "# from love import StopWars\n"
            )
            write_python_file(init_file, init_content, mode="w", encoding="utf-8")

        except PermissionError:
            self.project_desc.setText("Permission denied!")
            QMessageBox.critical(dialog, "Permission Error", "You don't have permission to create a project in this directory.")
            return
        except Exception as e:
            self.project_desc.setText(f"Error: {str(e)}")
            QMessageBox.critical(dialog, "Error", f"Failed to create project:\n{str(e)}")
            return

        # Set self.project_dir to the newly created project directory
        self.project_dir = project_path
        self.populate_workplace(self.project_dir)
        self.setWindowTitle(self.empty_project_win_title + os.path.basename(self.project_dir))

        # Add to recent projects
        self.add_to_recent_projects(self.project_dir)

        # Show success message
        QMessageBox.information(dialog, "Success", f"Project '{project_name}' created successfully!")

        # Open the bootstrap file in a new editor tab
        self._open_project_default_file(self.project_dir)

        # Close the dialog
        dialog.close()

    def open_nuke_project_dialog(self):
        # Returns the workplace after generating a project specific to Nuke
        dialog = NewNukeProjectDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint) # Make dialog Z +1
        if dialog.exec_():
            project_name = dialog.project_name_input.text().strip()
            project_dir = dialog.project_dir_input.text().strip()
            self.project_dir = os.path.join(project_dir, project_name)
            if os.path.exists(self.project_dir):
                self.populate_workplace(self.project_dir)
                self.setWindowTitle(self.empty_project_win_title + os.path.basename(self.project_dir))
                self.add_to_recent_projects(self.project_dir)
                self._open_project_default_file(self.project_dir)
            else:
                QMessageBox.warning(self, "Nuke Project", "Project folder was not created.")


    def reset_ui(self):
        """Resets the UI layout."""
        QMessageBox.information(self, "Reset UI", "UI has been reset.")

    def set_default_ui(self):
        """Sets the default UI layout."""
        QMessageBox.information(self, "Set Default UI", "UI has been set to default.")

    def cut_text(self):
        """Cuts the selected text from the active editor."""
        current_editor = self.tab_widget.currentWidget()
        if isinstance(current_editor, CodeEditor):
            current_editor.cut()

    def copy_text(self):
        """Copies the selected text from the active editor."""
        current_editor = self.tab_widget.currentWidget()
        if isinstance(current_editor, CodeEditor):
            current_editor.copy()

    def paste_text(self):
        """Pastes the text from the clipboard into the active editor."""
        current_editor = self.tab_widget.currentWidget()
        if isinstance(current_editor, CodeEditor):
            current_editor.paste()

    def select_all_text(self):
        """Selects all text in the active editor."""
        current_editor = self.tab_widget.currentWidget()
        if isinstance(current_editor, CodeEditor):
            current_editor.selectAll()

    def update_recent_projects_menu(self):
        """Recent Projects menüsünü günceller."""
        self.recent_projects.clear()
        # Her proje için menüye bir eylem ekleyelim
        for project_path in self.recent_projects_list:
            # Normalize path for display
            normalized_path = os.path.normpath(project_path)
            # Show only last 2 directories for cleaner menu
            display_name = os.path.sep.join(normalized_path.split(os.path.sep)[-2:])
            action = QAction(display_name, self)
            action.setToolTip(normalized_path)  # Full path in tooltip
            # 'checked' argümanını ekleyin ve path'i lambda'ya gönderin
            action.triggered.connect(partial(self.open_project_from_path, normalized_path))
            self.recent_projects.addAction(action)

    def load_last_project(self):
        """Load recent_paths[0] if 'resume_last_project' is enabled. Returns True if loaded."""
        resume_last_project = False
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as settings_file:
                    settings_data = json.load(settings_file) or {}
                general = settings_data.get("General", {}) if isinstance(settings_data, dict) else {}
                resume_last_project = bool(general.get("resume_last_project", False))
            except Exception:
                resume_last_project = False

        if not resume_last_project:
            return False

        if not os.path.exists(self.recent_projects_path):
            return False

        try:
            with open(self.recent_projects_path, 'r') as file:
                data = json.load(file) or {}
            recent_paths = data.get("recent_paths", []) if isinstance(data, dict) else []
        except Exception:
            return False

        if not recent_paths:
            return False

        last_project = recent_paths[0]
        if not last_project or not os.path.exists(last_project):
            return False

        self.project_dir = last_project
        self.populate_workplace(self.project_dir)
        self.setWindowTitle(self.empty_project_win_title + os.path.basename(self.project_dir))
        return True

    def open_project_from_path(self, project_path):
        """
        Opens a project from the given file path, updates the recent projects list,
        and dynamically refreshes the menu.
        """
        if os.path.exists(project_path):
            # Proje yolunu aç
            self.project_dir = project_path
            self.populate_workplace(project_path)
            self.setWindowTitle(self.empty_project_win_title + os.path.basename(project_path))

            # Use centralized add_to_recent_projects method
            self.add_to_recent_projects(project_path)
        else:
            QMessageBox.warning(self, "Error", f"Project directory {project_path} does not exist.")

    def new_project(self):
        """Yeni bir proje dizini seçer ve doğrudan dosya sistemine yansıtır."""
        # self.project_dir = QFileDialog.getExistingDirectory(self, "Proje Dizini Seç")
        if self.project_dir:
            self.populate_workplace(self.project_dir)

    def on_modification_changed(self, editor, modified):
        """Update tab title with * when file is modified"""
        target_tabs = None
        for tab_widget in self._all_tab_widgets():
            if tab_widget.indexOf(editor) != -1:
                target_tabs = tab_widget
                break

        if not target_tabs:
            return

        index = target_tabs.indexOf(editor)
        tab_title = target_tabs.tabText(index).replace("*", "")

        if modified:
            target_tabs.setTabText(index, "*" + tab_title)
        else:
            target_tabs.setTabText(index, tab_title)

    def mark_as_modified(self, editor):
        """Legacy method - kept for compatibility"""
        pass


    def open_project(self):
        """Open an existing project and set self.project_dir to the selected directory."""
        project_path = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if project_path:
            self.project_dir = project_path
            self.populate_workplace(project_path)
            self.setWindowTitle(self.empty_project_win_title + os.path.basename(project_path))

            # Projeyi recent_projects_list'e ekleyelim
            self.add_to_recent_projects(self.project_dir)

    def add_to_recent_projects(self, project_path):
        """Projeyi recent projects listesine ekler."""
        # Eğer proje zaten listede varsa çıkaralım
        if project_path in self.recent_projects_list:
            self.recent_projects_list.remove(project_path)

        # En başa ekleyelim
        self.recent_projects_list.insert(0, project_path)

        # Eğer 7'den fazla proje varsa, en son projeyi çıkaralım
        if len(self.recent_projects_list) > 7:
            self.recent_projects_list.pop()

        # Listeyi güncelle ve dosyaya kaydet
        self.save_recent_projects()
        self.update_recent_projects_menu()


    def save_recent_projects(self):
        """Recent Projects listesini JSON dosyasına düzenli bir formatta kaydeder ve tekrar eden yolları kaldırır."""
        try:
            # Platform bağımsız yollar için normalize et ve tekrar edenleri kaldır
            # dict.fromkeys() sırayı korur, bu yüzden ilk eklenen (en son) üstte kalır
            normalized_paths = list(dict.fromkeys(
                [os.path.normpath(path) for path in self.recent_projects_list]
            ))

            # JSON dosyasına recent_paths anahtarı altında kaydet
            with open(self.recent_projects_path, 'w') as file:
                json.dump({"recent_paths": normalized_paths}, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving recent projects: {e}")

    def load_recent_projects(self):
        """Recent Projects listesini JSON dosyasından yükler."""
        if os.path.exists(self.recent_projects_path):
            try:
                with open(self.recent_projects_path, 'r') as file:
                    data = json.load(file)
                    self.recent_projects_list = data.get("recent_paths", [])
            except Exception as e:
                print(f"Error loading recent projects: {e}")
                self.recent_projects_list = []  # Hata durumunda boş listeye geç

        # Menüde göstermek için listeyi güncelle
        self.update_recent_projects_menu()

    def closeEvent(self, event):
        """Uygulamayı kapatmadan önce kaydedilmemiş değişiklikleri kontrol eder."""
        response = self.prompt_save_changes()

        # Eğer kaydedilmemiş dosya yoksa, mesaj gösterilmez ve direkt kapatılır
        if response is None:
            event.accept()
            if event.isAccepted():
                self.deleteLater()
            return

        # Kaydedilmemiş dosyalar varsa soruları soralım
        if response == QMessageBox.Save:
            self.save_all_files()
            event.accept()
        elif response == QMessageBox.Discard:
            event.accept()  # Exit without saving
        elif response == QMessageBox.Cancel:
            event.ignore()  # Çıkışı iptal et
        if event.isAccepted():
            self.deleteLater()

    def file_exit(self):
        """File > Exit tıklandığında kaydedilmemiş dosyaları kontrol eder ve işlemi kapatır."""
        response = self.prompt_save_changes()

        # Eğer kaydedilmemiş dosya yoksa, uygulamayı kapat
        if response is None:
            self.close()
            return

        # Kaydedilmemiş dosyalar varsa kullanıcıya soralım
        if response == QMessageBox.Save:
            self.save_all_files()
            self.close()
        elif response == QMessageBox.Discard:
            self.close()  # Kaydetmeden çık
        elif response == QMessageBox.Cancel:
            pass  # İptal edildi, hiçbir şey yapma

    def close_app(self):
        """Programı kapatır."""
        reply = QMessageBox.question(self, 'Çıkış',
                                     "There are unsaved changes. Do you still want to quit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()
