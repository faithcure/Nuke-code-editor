from PySide2.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QCheckBox,
    QStyle,
)
from PySide2.QtGui import QColor, QTextCursor, QTextCharFormat, QTextDocument
from PySide2.QtCore import Qt, QEasingCurve, QPropertyAnimation, QTimer, QRegularExpression
from PySide2.QtWidgets import QTextEdit


class SearchDialog(QDialog):
    def __init__(self, main_window=None, show_replace=True):
        super().__init__(main_window)
        self.main_window = main_window
        self.matches = []
        self.match_selections = []
        self.current_match_index = -1
        self.show_replace = show_replace

        self.setWindowTitle("Find and Replace")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        label = QLabel("Find:")
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search in current file")
        self.search_input.textChanged.connect(self.on_search_text_changed)

        self.result_count_label = QLabel("0 matches")
        self.result_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        close_button = QToolButton(self)
        close_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close_button.setToolTip("Close")
        close_button.clicked.connect(self.reject)

        top_row.addWidget(label)
        top_row.addWidget(self.search_input, 1)
        top_row.addWidget(self.result_count_label)
        top_row.addWidget(close_button)
        layout.addLayout(top_row)

        replace_row = QHBoxLayout()
        replace_label = QLabel("Replace:")
        self.replace_input = QLineEdit(self)
        self.replace_input.setPlaceholderText("Replace with")
        self.replace_input.textChanged.connect(self.on_replace_text_changed)

        self.replace_button = QToolButton(self)
        self.replace_button.setText("Replace")
        self.replace_button.clicked.connect(self.replace_current)

        self.replace_all_button = QToolButton(self)
        self.replace_all_button.setText("Replace All")
        self.replace_all_button.clicked.connect(self.replace_all)

        replace_row.addWidget(replace_label)
        replace_row.addWidget(self.replace_input, 1)
        replace_row.addWidget(self.replace_button)
        replace_row.addWidget(self.replace_all_button)
        if self.show_replace:
            layout.addLayout(replace_row)
        else:
            self.replace_input.hide()
            self.replace_button.hide()
            self.replace_all_button.hide()

        options_row = QHBoxLayout()
        self.case_sensitive_check = QCheckBox("Case sensitive")
        self.whole_word_check = QCheckBox("Whole word")
        self.regex_check = QCheckBox("Regex")

        self.case_sensitive_check.stateChanged.connect(self.on_search_text_changed)
        self.whole_word_check.stateChanged.connect(self.on_search_text_changed)
        self.regex_check.stateChanged.connect(self.on_search_text_changed)

        prev_button = QToolButton(self)
        next_button = QToolButton(self)
        prev_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        next_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        prev_button.setToolTip("Previous match")
        next_button.setToolTip("Next match")
        prev_button.clicked.connect(lambda: self.navigate_matches(direction=-1))
        next_button.clicked.connect(lambda: self.navigate_matches(direction=1))

        options_row.addWidget(self.case_sensitive_check)
        options_row.addWidget(self.whole_word_check)
        options_row.addWidget(self.regex_check)
        options_row.addStretch(1)
        options_row.addWidget(prev_button)
        options_row.addWidget(next_button)
        layout.addLayout(options_row)

        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(250)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_in_animation.start()

        self.move_below_cursor()
        self._update_replace_buttons()

    def move_below_cursor(self):
        """Shows the search dialog just below the cursor line."""
        current_editor = None
        if self.main_window and hasattr(self.main_window, "_current_editor"):
            current_editor = self.main_window._current_editor()
        if current_editor:
            cursor_rect = current_editor.cursorRect()
            editor_global_pos = current_editor.mapToGlobal(cursor_rect.bottomLeft())
            self.move(editor_global_pos.x(), editor_global_pos.y())

    def on_search_text_changed(self):
        """Update the match count as the search text changes."""
        search_term = self.search_input.text().strip()
        match_count = self.find_and_highlight(search_term) if search_term else 0
        label = "match" if match_count == 1 else "matches"
        self.result_count_label.setText(f"{match_count} {label}")
        self._update_replace_buttons()

    def on_replace_text_changed(self):
        self._update_replace_buttons()

    def find_and_highlight(self, search_term):
        """Highlight matches in the editor and return the match count."""
        current_editor = None
        if self.main_window and hasattr(self.main_window, "_current_editor"):
            current_editor = self.main_window._current_editor()
        if current_editor is None:
            return 0

        cursor = current_editor.textCursor()
        document = current_editor.document()
        current_editor.setExtraSelections([])

        self.matches = []
        self.match_selections = []
        extra_selections = []
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)

        find_flags = QTextDocument.FindFlags()
        if self.case_sensitive_check.isChecked():
            find_flags |= QTextDocument.FindCaseSensitively
        if self.whole_word_check.isChecked():
            find_flags |= QTextDocument.FindWholeWords

        find_source = self._build_find_source(search_term)
        if find_source is None:
            cursor.endEditBlock()
            return 0

        match_count = 0
        while not cursor.isNull() and not cursor.atEnd():
            cursor = document.find(find_source, cursor, find_flags)
            if not cursor.isNull():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format = self.get_transparent_highlight()
                extra_selections.append(selection)
                self.match_selections.append(selection)
                self.matches.append((cursor.selectionStart(), cursor.selectionEnd()))
                match_count += 1

        cursor.endEditBlock()
        current_editor.setExtraSelections(extra_selections)
        return match_count

    def get_transparent_highlight(self):
        """Transparent pastel highlight format."""
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(255, 180, 100, 80))
        return highlight_format

    def navigate_matches(self, direction=1):
        """Navigate matches up/down and highlight the current match."""
        if not self.matches:
            return

        if direction < 0:
            self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        else:
            self.current_match_index = (self.current_match_index + 1) % len(self.matches)

        editor = None
        if self.main_window and hasattr(self.main_window, "_current_editor"):
            editor = self.main_window._current_editor()
        if not editor:
            return

        start, end = self.matches[self.current_match_index]
        cursor = editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)
        if hasattr(editor, "ensureCursorVisible"):
            editor.ensureCursorVisible()
        self.flash_current_line(editor)

    def flash_current_line(self, editor):
        """Temporarily highlight the current line."""
        extra_selection = QTextEdit.ExtraSelection()
        extra_selection.format.setBackground(QColor(255, 230, 100, 150))
        extra_selection.cursor = editor.textCursor()
        editor.setExtraSelections(self.match_selections + [extra_selection])

        QTimer.singleShot(300, lambda: self.dim_highlight(editor))

    def dim_highlight(self, editor):
        """Reduce the highlight intensity."""
        editor.setExtraSelections(self.match_selections)

    def _update_replace_buttons(self):
        has_search = bool(self.search_input.text().strip())
        has_replace = bool(self.replace_input.text().strip())
        enabled = has_search and has_replace
        self.replace_button.setEnabled(enabled)
        self.replace_all_button.setEnabled(enabled)

    def _get_current_editor(self):
        if self.main_window and hasattr(self.main_window, "_current_editor"):
            return self.main_window._current_editor()
        return None

    def replace_current(self):
        editor = self._get_current_editor()
        if not editor:
            return

        search_term = self.search_input.text().strip()
        replace_text = self.replace_input.text()
        if not search_term or not replace_text:
            return

        find_flags = self._build_find_flags()
        find_source = self._build_find_source(search_term)
        if find_source is None:
            return

        cursor = editor.textCursor()
        if not self._selection_matches(cursor, search_term):
            cursor = self._find_next_match(editor, cursor, find_source, find_flags)
            if cursor is None:
                return
        if cursor.selectionStart() == cursor.selectionEnd():
            cursor.setPosition(min(cursor.position() + 1, editor.document().characterCount() - 1))
            cursor = self._find_next_match(editor, cursor, find_source, find_flags)
            if cursor is None:
                return

        cursor.beginEditBlock()
        cursor.insertText(replace_text)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)

        self.on_search_text_changed()
        next_cursor = self._find_next_match(editor, cursor, find_source, find_flags)
        if next_cursor:
            editor.setTextCursor(next_cursor)
            self._sync_current_match_index(editor)

    def replace_all(self):
        editor = self._get_current_editor()
        if not editor:
            return

        search_term = self.search_input.text().strip()
        replace_text = self.replace_input.text()
        if not search_term or not replace_text:
            return

        document = editor.document()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)

        find_flags = self._build_find_flags()
        find_source = self._build_find_source(search_term)
        if find_source is None:
            cursor.endEditBlock()
            return

        while True:
            cursor = document.find(find_source, cursor, find_flags)
            if cursor.isNull():
                break
            if cursor.selectionStart() == cursor.selectionEnd():
                cursor.setPosition(min(cursor.position() + 1, document.characterCount() - 1))
                continue
            cursor.insertText(replace_text)

        cursor.endEditBlock()
        self.on_search_text_changed()

    def _build_find_flags(self):
        flags = QTextDocument.FindFlags()
        if self.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.whole_word_check.isChecked():
            flags |= QTextDocument.FindWholeWords
        return flags

    def _build_find_source(self, search_term):
        if self.regex_check.isChecked():
            options = QRegularExpression.NoPatternOption
            if not self.case_sensitive_check.isChecked():
                options |= QRegularExpression.CaseInsensitiveOption
            pattern = QRegularExpression(search_term, options)
            if not pattern.isValid():
                return None
            return pattern
        return search_term

    def _selection_matches(self, cursor, search_term):
        if not cursor.hasSelection():
            return False
        selection = cursor.selectedText()
        if self.regex_check.isChecked():
            pattern = self._build_find_source(search_term)
            if pattern is None:
                return False
            match = pattern.match(selection)
            return match.hasMatch() and match.capturedLength(0) == len(selection)
        if self.case_sensitive_check.isChecked():
            return selection == search_term
        return selection.lower() == search_term.lower()

    def _find_next_match(self, editor, cursor, find_source, find_flags):
        start_cursor = QTextCursor(cursor)
        if start_cursor.hasSelection():
            start_cursor.setPosition(start_cursor.selectionEnd())

        next_cursor = editor.document().find(find_source, start_cursor, find_flags)
        if next_cursor.isNull():
            next_cursor = editor.document().find(find_source, QTextCursor(editor.document()), find_flags)
            if next_cursor.isNull():
                return None
        return next_cursor

    def _sync_current_match_index(self, editor):
        if not self.matches:
            self.current_match_index = -1
            return
        cursor = editor.textCursor()
        start = cursor.selectionStart()
        for i, (match_start, _match_end) in enumerate(self.matches):
            if match_start == start:
                self.current_match_index = i
                return
