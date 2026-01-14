import os
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QPushButton,
    QFileDialog,
)
from PySide2.QtCore import Qt


def build_environment_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout()

    filter_group = QGroupBox("Environment Variables")
    filter_layout = QVBoxLayout()

    filter_row = QHBoxLayout()
    filter_label = QLabel("Filter:")
    filter_input = QLineEdit()
    filter_input.setPlaceholderText("Type to filter variables...")
    only_nuke_checkbox = QCheckBox("Only Nuke variables")
    only_nuke_checkbox.setChecked(False)
    filter_row.addWidget(filter_label)
    filter_row.addWidget(filter_input, 1)
    filter_row.addWidget(only_nuke_checkbox)
    filter_layout.addLayout(filter_row)

    env_table = QTableWidget()
    env_table.setColumnCount(2)
    env_table.setHorizontalHeaderLabels(["Variable", "Value"])
    env_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    env_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    env_table.setSortingEnabled(True)

    filter_layout.addWidget(env_table)

    actions_row = QHBoxLayout()
    copy_selected = QPushButton("Copy Selected")
    export_button = QPushButton("Export .env")
    actions_row.addWidget(copy_selected)
    actions_row.addWidget(export_button)
    actions_row.addStretch()
    filter_layout.addLayout(actions_row)
    filter_group.setLayout(filter_layout)
    layout.addWidget(filter_group)

    explanation_label = QLabel(
        "All variables are read-only. Use the filter to locate specific values."
    )
    explanation_label.setWordWrap(True)
    explanation_label.setStyleSheet("color: gray; font-style: italic;")
    layout.addWidget(explanation_label)

    def populate_table():
        filter_text = filter_input.text().strip().lower()
        only_nuke = only_nuke_checkbox.isChecked()
        items = []
        for key, value in os.environ.items():
            if only_nuke and "NUKE" not in key.upper():
                continue
            if filter_text and filter_text not in key.lower() and filter_text not in value.lower():
                continue
            items.append((key, value))

        items.sort(key=lambda x: x[0].lower())
        env_table.setRowCount(len(items))
        for row, (key, value) in enumerate(items):
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem(value)
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            env_table.setItem(row, 0, key_item)
            env_table.setItem(row, 1, value_item)
        return items

    def selected_rows():
        rows = set()
        for item in env_table.selectedItems():
            rows.add(item.row())
        return sorted(rows)

    def copy_selected_rows():
        rows = selected_rows()
        if not rows:
            return
        lines = []
        for row in rows:
            key_item = env_table.item(row, 0)
            value_item = env_table.item(row, 1)
            if key_item and value_item:
                lines.append(f"{key_item.text()}={value_item.text()}")
        if lines:
            _copy_to_clipboard("\n".join(lines))

    def export_env():
        path, _ = QFileDialog.getSaveFileName(
            panel,
            "Export Environment",
            os.path.join(os.path.expanduser("~"), "nuke_env.env"),
            "Env Files (*.env)"
        )
        if not path:
            return
        lines = []
        for row in range(env_table.rowCount()):
            key_item = env_table.item(row, 0)
            value_item = env_table.item(row, 1)
            if key_item and value_item:
                lines.append(f"{key_item.text()}={value_item.text()}")
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write("\n".join(lines) + "\n")
        except Exception:
            pass

    copy_selected.clicked.connect(copy_selected_rows)
    export_button.clicked.connect(export_env)

    filter_input.textChanged.connect(populate_table)
    only_nuke_checkbox.stateChanged.connect(lambda _state: populate_table())
    populate_table()

    panel.setLayout(layout)
    return panel
