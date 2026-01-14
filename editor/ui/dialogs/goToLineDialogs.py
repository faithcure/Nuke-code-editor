from PySide2.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
)
from PySide2.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide2.QtGui import QTextCursor


class GoToLineDialog(QDialog):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

        self.setWindowTitle("Go to Line and Column")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label = QLabel("Enter target position:")
        layout.addWidget(label)

        input_row = QHBoxLayout()

        line_label = QLabel("Line")
        self.line_input = QLineEdit(self)
        self.line_input.setPlaceholderText("e.g. 42")
        self.line_input.setMaximumWidth(120)

        column_label = QLabel("Column")
        self.column_input = QLineEdit(self)
        self.column_input.setPlaceholderText("e.g. 1")
        self.column_input.setMaximumWidth(120)

        input_row.addWidget(line_label)
        input_row.addWidget(self.line_input)
        input_row.addSpacing(12)
        input_row.addWidget(column_label)
        input_row.addWidget(self.column_input)
        input_row.addStretch(1)
        layout.addLayout(input_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.on_ok_button_clicked)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._set_defaults_from_cursor()

        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(200)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_in_animation.start()

    def _set_defaults_from_cursor(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.line_input.setText(str(line))
        self.column_input.setText(str(column))
        self.line_input.selectAll()
        self.line_input.setFocus()

    def on_ok_button_clicked(self):
        line_text = self.line_input.text().strip()
        column_text = self.column_input.text().strip()

        if not line_text.isdigit() or not column_text.isdigit():
            QMessageBox.warning(self, "Invalid input", "Line and column must be positive integers.")
            return

        line_number = int(line_text)
        column_number = int(column_text)

        max_lines = self.editor.document().blockCount()
        if line_number < 1 or line_number > max_lines:
            QMessageBox.warning(self, "Out of range", f"Line must be between 1 and {max_lines}.")
            return

        self.go_to_line_column(line_number, column_number)
        self.accept()

    def go_to_line_column(self, line_number, column_number):
        editor = self.editor
        if not editor:
            return
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_number - 1)

        line_length = len(cursor.block().text())
        safe_column = max(1, min(column_number, line_length + 1))
        cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, safe_column - 1)

        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()
