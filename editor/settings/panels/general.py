import os
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QFrame,
    QSizePolicy,
    QSpacerItem,
    QPushButton,
    QTextEdit,
)
from PySide2.QtCore import Qt
from editor.settings import settings_ux
from editor.core import PathFromOS


def build_general_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout()

    lang_theme_group = QGroupBox("Language and Theme")
    lang_theme_layout = QVBoxLayout()
    lang_theme_inner_layout = QHBoxLayout()

    language_combobox = QComboBox()
    language_combobox.setObjectName("default_language")
    language_combobox.addItem("English")
    language_combobox.setEnabled(False)

    theme_combobox = QComboBox()
    theme_combobox.setObjectName("default_theme")
    theme_combobox.addItem("Nuke Default")
    theme_combobox.setEnabled(False)

    separator = QFrame()
    separator.setFrameShape(QFrame.VLine)
    separator.setFrameShadow(QFrame.Sunken)
    separator.setStyleSheet("color: lightgrey;")

    lang_theme_inner_layout.addWidget(QLabel("Language:"))
    lang_theme_inner_layout.addWidget(language_combobox)
    lang_theme_inner_layout.addWidget(separator)
    lang_theme_inner_layout.addWidget(QLabel("Theme:"))
    lang_theme_inner_layout.addWidget(theme_combobox)
    lang_theme_inner_layout.addStretch()

    lang_theme_layout.addLayout(lang_theme_inner_layout)
    settings_note = QLabel("Some settings are fixed because the IDE runs inside Nuke.")
    settings_note.setStyleSheet("color: Grey;")
    settings_note.setWordWrap(True)
    lang_theme_layout.addWidget(settings_note)

    lang_theme_group.setLayout(lang_theme_layout)
    lang_theme_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(lang_theme_group)

    start_group = QGroupBox("Startup")
    start_layout = QVBoxLayout()
    startup_checkbox = QCheckBox("Start IDE on Nuke launch")
    startup_checkbox.setObjectName("startup_checkbox")
    start_description = QLabel("Automatically open the IDE when Nuke starts.")
    start_description.setStyleSheet("color: Grey;")
    start_description.setWordWrap(True)
    start_layout.addWidget(startup_checkbox)
    start_layout.addWidget(start_description)

    startup_mode_row = QHBoxLayout()
    startup_mode_label = QLabel("Launch as:")
    startup_mode_combobox = QComboBox()
    startup_mode_combobox.setObjectName("startup_launch_mode")
    startup_mode_combobox.addItems(["Standalone Window", "Dockable Panel"])
    startup_mode_combobox.setToolTip("Choose how the IDE starts when Nuke launches.")
    startup_mode_row.addWidget(startup_mode_label)
    startup_mode_row.addWidget(startup_mode_combobox, 1)
    start_layout.addLayout(startup_mode_row)

    def _sync_startup_mode_enabled(checked):
        startup_mode_combobox.setEnabled(bool(checked))

    startup_checkbox.toggled.connect(_sync_startup_mode_enabled)
    _sync_startup_mode_enabled(startup_checkbox.isChecked())
    start_group.setLayout(start_layout)
    start_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(start_group)

    ui_settings_group = QGroupBox("Interface")
    ui_settings_layout = QVBoxLayout()
    interface_mode_combobox = QComboBox()
    interface_mode_combobox.setObjectName("default_interface_mode")
    interface_mode_combobox.addItems(settings_ux.root_modes.keys())
    interface_mode_combobox.setToolTip("Default interface mode on startup.")
    ui_settings_layout.addWidget(QLabel("Default Interface Mode:"))
    ui_settings_layout.addWidget(interface_mode_combobox)
    ui_note = QLabel("You can change the interface mode later from the main menu.")
    ui_note.setStyleSheet("color: Grey;")
    ui_note.setWordWrap(True)
    ui_settings_layout.addWidget(ui_note)
    ui_settings_group.setLayout(ui_settings_layout)
    ui_settings_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(ui_settings_group)

    last_project_group = QGroupBox("Project Session")
    last_project_layout = QVBoxLayout()
    last_project_checkbox = QCheckBox("Resume last project")
    last_project_checkbox.setObjectName("resume_last_project")
    last_project_note = QLabel("If disabled, the IDE starts with an empty session.")
    last_project_note.setStyleSheet("color: Grey;")
    last_project_note.setWordWrap(True)
    last_project_layout.addWidget(last_project_checkbox)
    last_project_layout.addWidget(last_project_note)
    last_project_group.setLayout(last_project_layout)
    last_project_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(last_project_group)

    syntax_color_group = QGroupBox("Syntax Highlighting")
    syntax_color_layout = QVBoxLayout()
    manage_syntax_layout = QHBoxLayout()

    pygments_module_path = os.path.join(PathFromOS().project_root, "third_party")
    pygments_available = os.path.exists(os.path.join(pygments_module_path, "pygments"))

    manage_syntax_button = QPushButton("Install Pygments")
    manage_syntax_button.clicked.connect(settings_window.install_pygement_module)
    manage_syntax_button.setObjectName("install_color_module")
    manage_syntax_button.setEnabled(not pygments_available)
    manage_syntax_button.setFixedWidth(140)
    manage_syntax_layout.addWidget(manage_syntax_button)

    syntax_style_dropdown = QComboBox()
    syntax_style_dropdown.setObjectName("syntax_style_dropdown")
    supported_styles = [
        "monokai",
        "lightbulb",
        "github-dark",
        "rrt",
        "zenburn",
        "material",
        "one-dark",
        "dracula",
        "nord-darker",
        "gruvbox-dark",
        "stata-dark",
        "native",
        "fruity",
    ]
    syntax_style_dropdown.addItems(sorted(supported_styles))
    syntax_style_dropdown.setCurrentText("monokai")
    syntax_style_dropdown.setToolTip("Select a syntax highlighting style.")
    syntax_style_dropdown.setEnabled(pygments_available)
    syntax_style_dropdown.setFixedWidth(200)
    manage_syntax_layout.addWidget(syntax_style_dropdown)
    manage_syntax_layout.addStretch()

    syntax_color_layout.addLayout(manage_syntax_layout)
    syntax_color_note = QLabel("Use Pygments styles for syntax highlighting.")
    syntax_color_note.setStyleSheet("color: Grey;")
    syntax_color_note.setWordWrap(True)
    syntax_color_layout.addWidget(syntax_color_note)

    preview_group = QGroupBox("Syntax Preview")
    preview_layout = QVBoxLayout()

    settings_window.preview_editor = QTextEdit()
    settings_window.preview_editor.setReadOnly(True)
    settings_window.preview_editor.setMinimumHeight(200)

    sample_code = """# Nuke Python Script Example
import nuke

def apply_effect(node):
    \"\"\"Apply color grading effect to node\"\"\"
    node.setInput(0, 'Image')
    node.knob('color').setValue(0.5)

    for i in range(10):
        fade_value = i * 0.1
        node.knob('fade').setValue(fade_value)

    return node
"""

    def apply_syntax_highlighting():
        try:
            from pygments import highlight
            from pygments.lexers import PythonLexer
            from pygments.formatters import HtmlFormatter

            current_style = settings_window.settings.get("General", {}).get("syntax_style_dropdown", "monokai")
            if syntax_style_dropdown.currentText():
                current_style = syntax_style_dropdown.currentText()
            formatter = HtmlFormatter(style=current_style, noclasses=True, nobackground=False)
            highlighted = highlight(sample_code, PythonLexer(), formatter)
            settings_window.preview_editor.setHtml(highlighted)
        except Exception:
            settings_window.preview_editor.setPlainText(sample_code)

    settings_window.apply_syntax_preview = apply_syntax_highlighting
    apply_syntax_highlighting()
    preview_layout.addWidget(settings_window.preview_editor)

    preview_info = QLabel("Preview updates as you change font or syntax settings.")
    preview_info.setStyleSheet("color: Grey; font-style: italic;")
    preview_layout.addWidget(preview_info)
    preview_group.setLayout(preview_layout)
    syntax_color_layout.addWidget(preview_group)

    syntax_style_dropdown.currentTextChanged.connect(lambda: apply_syntax_highlighting())

    syntax_color_group.setLayout(syntax_color_layout)
    syntax_color_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(syntax_color_group)

    layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    panel.setLayout(layout)
    settings_window.syntax_style_dropdown = syntax_style_dropdown
    settings_window.general_panel = panel
    return panel
