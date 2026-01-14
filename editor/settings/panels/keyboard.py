from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QKeySequenceEdit
from PySide2.QtCore import Qt
import os


DEFAULT_SHORTCUTS = {
    "File": [
        ("New Project", "Ctrl+N", "Create a new project"),
        ("New File", "Ctrl+Shift+N", "Create a new file"),
        ("Open File", "Ctrl+O", "Open an existing file"),
        ("Save", "Ctrl+S", "Save current file"),
        ("Save As", "Ctrl+Shift+S", "Save file with a new name"),
        ("Close Tab", "Ctrl+W", "Close current tab"),
        ("Exit", "Ctrl+Q", "Exit application"),
    ],
    "Edit": [
        ("Undo", "Ctrl+Z", "Undo last action"),
        ("Redo", "Ctrl+Y", "Redo last undone action"),
        ("Cut", "Ctrl+X", "Cut selected text"),
        ("Copy", "Ctrl+C", "Copy selected text"),
        ("Paste", "Ctrl+V", "Paste from clipboard"),
        ("Select All", "Ctrl+A", "Select all text"),
        ("Find", "Ctrl+F", "Find text in file"),
        ("Replace", "Ctrl+Shift+R", "Find and replace text"),
        ("Go to Line", "Ctrl+G", "Jump to a specific line"),
        ("Comment Toggle", "Ctrl+/", "Toggle line comment"),
        ("Duplicate Line", "Ctrl+D", "Duplicate current line or selection"),
        ("Delete Line", "Ctrl+Shift+K", "Delete current line"),
        ("Move Line Up", "Alt+Up", "Move line up"),
        ("Move Line Down", "Alt+Down", "Move line down"),
        ("Smart Home", "Home", "Jump to line start or first non-whitespace"),
        ("Smart End", "End", "Jump to end of line"),
    ],
    "View": [
        ("Zoom In", "Ctrl++", "Increase font size"),
        ("Zoom Out", "Ctrl+-", "Decrease font size"),
        ("Reset Zoom", "Ctrl+0", "Reset font size to default"),
        ("Show Whitespace", "Ctrl+Shift+W", "Toggle whitespace visibility"),
    ],
    "Execute": [
        ("Run Code", "F5", "Run all code in editor"),
        ("Execute Selected or All", "Ctrl+Enter", "Execute selected code or all code if nothing selected"),
        ("Execute All Code", "Ctrl+Shift+Enter", "Always execute all code"),
        ("Execute Current Line", "Ctrl+Alt+Enter", "Execute the current line"),
    ],
}


def build_keyboard_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout(panel)

    title = QLabel("Keyboard Shortcuts")
    title.setStyleSheet("font-size: 14pt; font-weight: bold;")
    layout.addWidget(title)

    description = QLabel(
        "Customize keyboard shortcuts for IDE commands. Click a Shortcut field and press your keys."
    )
    description.setStyleSheet("color: grey;")
    description.setWordWrap(True)
    layout.addWidget(description)

    restart_warning = QLabel(
        "Restart the IDE after changing shortcuts to apply them."
    )
    restart_warning.setStyleSheet("color: #ff9900; font-weight: bold; background-color: rgba(255, 153, 0, 0.1); padding: 8px; border-radius: 4px;")
    restart_warning.setWordWrap(True)
    layout.addWidget(restart_warning)

    platform_info = QLabel(
        "Shortcuts adapt to your OS (Ctrl on Windows/Linux, Cmd on macOS). "
        "Note: Some shortcuts may conflict with Nuke's own shortcuts."
    )
    platform_info.setStyleSheet("color: #4a9eff; font-size: 9pt; font-style: italic; padding: 4px;")
    platform_info.setWordWrap(True)
    layout.addWidget(platform_info)

    settings_window.default_shortcuts = DEFAULT_SHORTCUTS
    settings_window.shortcuts_table = QTableWidget()
    settings_window.shortcuts_table.setColumnCount(4)
    settings_window.shortcuts_table.setHorizontalHeaderLabels(["Command", "Category", "Shortcut", "Description"])

    row = 0
    settings_window.shortcut_editors = {}

    for category, commands in DEFAULT_SHORTCUTS.items():
        for cmd_name, default_shortcut, cmd_description in commands:
            settings_window.shortcuts_table.insertRow(row)

            cmd_item = QTableWidgetItem(cmd_name)
            cmd_item.setFlags(cmd_item.flags() & ~Qt.ItemIsEditable)
            settings_window.shortcuts_table.setItem(row, 0, cmd_item)

            cat_item = QTableWidgetItem(category)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
            settings_window.shortcuts_table.setItem(row, 1, cat_item)

            shortcut_edit = QKeySequenceEdit(default_shortcut)
            shortcut_edit.setObjectName(f"shortcut_{cmd_name}")
            shortcut_edit.keySequenceChanged.connect(settings_window.on_shortcut_changed)
            settings_window.shortcuts_table.setCellWidget(row, 2, shortcut_edit)
            settings_window.shortcut_editors[cmd_name] = shortcut_edit

            desc_item = QTableWidgetItem(cmd_description)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            settings_window.shortcuts_table.setItem(row, 3, desc_item)

            row += 1

    settings_window.shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    settings_window.shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    settings_window.shortcuts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    settings_window.shortcuts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    settings_window.shortcuts_table.setAlternatingRowColors(True)

    layout.addWidget(settings_window.shortcuts_table)

    buttons_layout = QHBoxLayout()
    restore_button = QPushButton("Restore Defaults")
    restore_button.clicked.connect(settings_window.restore_default_shortcuts)
    restore_button.setToolTip("Reset all shortcuts to default values")
    buttons_layout.addWidget(restore_button)

    export_button = QPushButton("Export to .ini")
    export_button.clicked.connect(settings_window.export_shortcuts_to_ini)
    export_button.setToolTip("Save current shortcuts to an .ini file")
    buttons_layout.addWidget(export_button)

    import_button = QPushButton("Import from .ini")
    import_button.clicked.connect(settings_window.import_shortcuts_from_ini)
    import_button.setToolTip("Load shortcuts from an .ini file")
    buttons_layout.addWidget(import_button)

    buttons_layout.addStretch()
    layout.addLayout(buttons_layout)

    settings_window.conflict_label = QLabel("")
    settings_window.conflict_label.setStyleSheet("color: #ff6f61; font-weight: bold;")
    settings_window.conflict_label.setWordWrap(True)
    layout.addWidget(settings_window.conflict_label)

    settings_window.check_shortcut_conflicts()
    return panel
