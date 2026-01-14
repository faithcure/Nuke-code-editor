import importlib
import json
import os
import re
from PySide2.QtCore import QRect, QPoint
from PySide2.QtCore import QRegExp
from PySide2.QtCore import QSize
from PySide2.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QPen
from PySide2.QtGui import QFont, QPalette, QTextOption
from PySide2.QtGui import QPainter, QTextFormat, QFontDatabase, QTextBlockFormat, QFontMetrics
from PySide2.QtWidgets import *
import editor.completer
import editor.inline_ghosting
from editor.core import CodeEditorSettings
import editor.settings.settings_ui
from editor.completer import Completer
from PySide2.QtCore import Qt
from PySide2.QtGui import QTextCursor
from editor.inline_ghosting import InlineGhosting
from init_ide import settings_path

importlib.reload(editor.completer)
importlib.reload(editor.inline_ghosting)
importlib.reload(editor.settings.settings_ui)

from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Number, Operator, Text, Generic, Literal, Punctuation
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

class CodeEditor(InlineGhosting):
    def __init__(self, editor_window=None, *args):
        super().__init__(*args)
        self.editor_window = editor_window  
        self.font_size = CodeEditorSettings().main_font_size  
        self.ctrl_wheel_enabled = CodeEditorSettings().ctrlWheel  
        self.show_whitespace = False  
        self.extra_cursors = []  
        self.settings = CodeEditorSettings()  
        self.folded_blocks = set()  
        self.setup_fonts()
        self.set_background_color()
        self.completer = Completer(self)  
        self.setWordWrapMode(QTextOption.NoWrap)
        self.set_line_spacing(CodeEditorSettings().line_spacing_size)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(self.highlight_current_word)
        self.cursorPositionChanged.connect(self.highlight_matching_brackets)
        self.cursorPositionChanged.connect(self.update_cursor_position)
        self.blockCountChanged.connect(self.update_line_and_character_count)
        self.textChanged.connect(self.update_line_and_character_count)
        self.cursorPositionChanged.connect(self.update_line_and_character_count)
        self.textChanged.connect(self.handle_text_change)
        self.update_line_number_area_width(0)
        self.highlighter = PygmentsHighlighter(self.document())  
        self._line_selection = None
        self._clicked_line_selection = None
        self._word_selections = []
        self._bracket_selections = []

    def matches_shortcut(self, event, shortcut_str):
        """
        Check if a QKeyEvent matches a shortcut string.

        Args:
            event: QKeyEvent to check
            shortcut_str: Shortcut string like "Ctrl+D", "Alt+Up", "Ctrl+Shift+Enter"

        Returns:
            bool: True if event matches the shortcut
        """
        if not shortcut_str:
            return False

        
        parts = shortcut_str.split('+')
        expected_modifiers = Qt.NoModifier
        expected_key = None

        for part in parts:
            part = part.strip()
            if part == "Ctrl":
                expected_modifiers |= Qt.ControlModifier
            elif part == "Shift":
                expected_modifiers |= Qt.ShiftModifier
            elif part == "Alt":
                expected_modifiers |= Qt.AltModifier
            elif part == "Meta":
                expected_modifiers |= Qt.MetaModifier
            else:
                
                key_map = {
                    "Enter": Qt.Key_Return,
                    "Return": Qt.Key_Return,
                    "Up": Qt.Key_Up,
                    "Down": Qt.Key_Down,
                    "Left": Qt.Key_Left,
                    "Right": Qt.Key_Right,
                    "Home": Qt.Key_Home,
                    "End": Qt.Key_End,
                    "Tab": Qt.Key_Tab,
                    "Backspace": Qt.Key_Backspace,
                    "Delete": Qt.Key_Delete,
                    "Escape": Qt.Key_Escape,
                    "Space": Qt.Key_Space,
                    "/": Qt.Key_Slash,
                    "+": Qt.Key_Plus,
                    "-": Qt.Key_Minus,
                    "*": Qt.Key_Asterisk,
                    "0": Qt.Key_0,
                    "F5": Qt.Key_F5,
                }

                if part in key_map:
                    expected_key = key_map[part]
                elif len(part) == 1:
                    
                    expected_key = ord(part.upper())

        if expected_key is None:
            return False

        
        return event.key() == expected_key and event.modifiers() == expected_modifiers

    def _indent_unit(self):
        settings = CodeEditorSettings()
        if settings.use_spaces_for_tabs:
            return " " * int(settings.tab_size)
        return "\t"

    def _remove_indent_from_line(self, cursor):
        settings = CodeEditorSettings()
        cursor.movePosition(QTextCursor.StartOfBlock)
        if not settings.use_spaces_for_tabs:
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
            if cursor.selectedText() == "\t":
                cursor.removeSelectedText()
                return
            cursor.clearSelection()
        line_text = cursor.block().text()
        leading_spaces = len(line_text) - len(line_text.lstrip(" "))
        if leading_spaces > 0:
            spaces_to_remove = min(int(settings.tab_size), leading_spaces)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, spaces_to_remove)
            cursor.removeSelectedText()

    def handle_text_change(self):
        """Trigger completion on each text change while typing."""
        self.completer.update_completions()

        
        if CodeEditorSettings().ENABLE_INLINE_GHOSTING:
            self.update_ghost_text()  
        else:
            self.ghost_text = ""  
            self.viewport().update()  

    def set_background_color(self):
        """Set the editor background color."""
        
        palette = self.palette()
        
        palette.setColor(QPalette.Base, CodeEditorSettings().code_background_color)
        
        self.setPalette(palette)

    def setup_fonts(self):
        

        default_font = CodeEditorSettings().main_default_font  
        default_font_size = CodeEditorSettings().main_font_size  

        self.setFont(QFont(default_font, default_font_size))  
        self.apply_tab_settings()

    def apply_tab_settings(self):
        settings = CodeEditorSettings()
        tab_size = max(1, int(settings.tab_size))
        metrics = QFontMetrics(self.font())
        self.setTabStopDistance(metrics.horizontalAdvance(" ") * tab_size)


    def wheelEvent(self, event):
        """Adjust font size with CTRL + Wheel"""
        if self.ctrl_wheel_enabled and event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.font_size += 1
            elif event.angleDelta().y() < 0 and self.font_size > 1:
                self.font_size -= 1

            
            font = self.font()
            font.setPointSize(self.font_size)
            self.setFont(font)
            self.apply_tab_settings()

            
            if self.editor_window:
                self.editor_window.font_size_label.setText(f"Font Size: {self.font_size} | ")

            event.accept()
        else:
            
            super().wheelEvent(event)

    def set_line_spacing(self, line_spacing_factor):
        line_spacing_factor = max(0.8, float(line_spacing_factor))
        original_cursor = self.textCursor()
        original_position = original_cursor.position()
        original_anchor = original_cursor.anchor()

        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.Document)
        block_format = QTextBlockFormat()
        block_format.setLineHeight(line_spacing_factor * 100, QTextBlockFormat.ProportionalHeight)
        cursor.mergeBlockFormat(block_format)

        restored = self.textCursor()
        restored.setPosition(original_anchor)
        restored.setPosition(original_position, QTextCursor.KeepAnchor)
        self.setTextCursor(restored)

    def keyPressEvent(self, event):
        cursor = self.textCursor()

        
        if self.completer.completion_popup.popup().isVisible():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                try:
                    if self.completer.accept_current():
                        return
                except Exception:
                    pass
            if event.key() in (Qt.Key_Escape, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
                self.completer.completion_popup.popup().hide()
                super().keyPressEvent(event)
                return
            if event.modifiers() in (Qt.ControlModifier, Qt.AltModifier, Qt.ControlModifier | Qt.ShiftModifier):
                self.completer.completion_popup.popup().hide()

        
        
        if self.matches_shortcut(event, self.settings.get_shortcut("Execute Selected or All")):
            self.execute_selected_or_all_code()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Execute All Code")):
            self.run_all_code()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Execute Current Line")):
            self.execute_current_line()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Comment Toggle")):
            self.toggle_comment()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Duplicate Line")):
            self.duplicate_line()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Delete Line")):
            self.delete_line()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Move Line Up")):
            self.move_line_up()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Move Line Down")):
            self.move_line_down()
            event.accept()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Smart Home")):
            self.smart_home()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Smart End")):
            self.smart_end()
            return

        
        elif self.matches_shortcut(event, self.settings.get_shortcut("Show Whitespace")):
            self.toggle_show_whitespace()
            return

        
        elif event.key() == Qt.Key_Backspace and self.extra_cursors:
            super().keyPressEvent(event)
            self.apply_backspace_to_extra_cursors()
            return

        
        elif event.key() == Qt.Key_Delete and self.extra_cursors:
            super().keyPressEvent(event)
            self.apply_delete_to_extra_cursors()
            return

        
        if self.completer.completion_popup.popup().isVisible():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                try:
                    if self.completer.accept_current():
                        return
                except Exception:
                    pass
                return

            elif event.key() in (Qt.Key_Up, Qt.Key_Down):
                
                self.completer.completion_popup.popup().keyPressEvent(event)
                return  

        
        if event.key() in (Qt.Key_ParenLeft, Qt.Key_BraceLeft, Qt.Key_BracketLeft,
                           Qt.Key_QuoteDbl, Qt.Key_Apostrophe):
            pairs = {
                Qt.Key_ParenLeft: ('(', ')'),
                Qt.Key_BraceLeft: ('{', '}'),
                Qt.Key_BracketLeft: ('[', ']'),
                Qt.Key_QuoteDbl: ('"', '"'),
                Qt.Key_Apostrophe: ("'", "'"),
            }
            opening, closing = pairs[event.key()]
            cursor.insertText(opening + closing)
            cursor.movePosition(QTextCursor.Left)
            self.setTextCursor(cursor)

        
        elif event.key() in (Qt.Key_ParenRight, Qt.Key_BraceRight, Qt.Key_BracketRight,
                             Qt.Key_QuoteDbl, Qt.Key_Apostrophe):
            current_char = self.document().characterAt(cursor.position())
            closing_chars = {
                Qt.Key_ParenRight: ')',
                Qt.Key_BraceRight: '}',
                Qt.Key_BracketRight: ']',
                Qt.Key_QuoteDbl: '"',
                Qt.Key_Apostrophe: "'",
            }
            if current_char == closing_chars[event.key()]:
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
            else:
                super().keyPressEvent(event)

        
        elif event.key() == Qt.Key_Tab:
            if self.completer.completion_popup.popup().isVisible():
                self.completer.hide_popup()
            
            if CodeEditorSettings().ENABLE_INLINE_GHOSTING and hasattr(self, 'ghost_text') and self.ghost_text:
                
                if hasattr(self, "accept_ghost_text"):
                    self.accept_ghost_text(cursor)
                else:
                    cursor.insertText(self.ghost_text)
                    self.ghost_text = ""
                    self.viewport().update()
            else:
                cursor.insertText(self._indent_unit())

        
        elif event.key() == Qt.Key_Backtab:
            cursor.beginEditBlock()

            
            if cursor.hasSelection():
                
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()

                
                cursor.setPosition(start_pos)
                start_block = cursor.block()

                cursor.setPosition(end_pos)
                end_block = cursor.block()

                block = start_block
                while block.isValid():
                    cursor.setPosition(block.position())
                    self._remove_indent_from_line(cursor)

                    
                    if block == end_block:
                        break

                    block = block.next()
            else:
                
                block = cursor.block()
                self._remove_indent_from_line(cursor)

            cursor.endEditBlock()

        elif event.key() == Qt.Key_Return:
            block = cursor.block()
            text = block.text()
            indentation = text[:len(text) - len(text.lstrip())]

            if text.strip().endswith(':'):
                indentation += self._indent_unit()
            super().keyPressEvent(event)
            cursor.insertText(indentation)

            
            if self.extra_cursors:
                self.apply_to_extra_cursors('\n' + indentation)

        else:
            
            if self.extra_cursors and len(event.text()) == 1 and event.text().isprintable():
                
                super().keyPressEvent(event)
                
                self.apply_to_extra_cursors(event.text())
            else:
                super().keyPressEvent(event)

    def update_line_and_character_count(self):
        """Update the total number of characters in the status bar, along with cursor position."""
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        total_characters = len(self.toPlainText())

        main_window = self.get_main_window()
        if main_window:
            main_window.status_bar.showMessage(f"{line}:{column} | Characters: {total_characters}")

    def execute_selected_or_all_code(self):
        """
        Execute selected code if any, otherwise execute all code.
        Called when user presses Ctrl+Enter.
        """
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'run_code'):
            main_window.run_code()
        else:
            return

    def run_all_code(self):
        """
        Execute all code in the editor.
        Called from context menu "Run All Code".
        """
        
        cursor = self.textCursor()
        had_selection = cursor.hasSelection()
        if had_selection:
            start = cursor.selectionStart()
            end = cursor.selectionEnd()

        
        cursor.clearSelection()
        self.setTextCursor(cursor)

        
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'run_code'):
            main_window.run_code()

        
        if had_selection:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)

    def execute_current_line(self):
        """
        Execute only the current line where the cursor is positioned.
        Leading whitespace is automatically stripped to prevent Python indentation errors.
        Called when user presses Ctrl+Alt+Enter.
        """
        cursor = self.textCursor()
        block = cursor.block()
        line_text = block.text()
        stripped_line = line_text.lstrip()

        if not stripped_line:
            main_window = self.get_main_window()
            if main_window:
                main_window.status_bar.showMessage("Current line is empty", 2000)
            return

        
        original_cursor = QTextCursor(cursor)
        line_cursor = QTextCursor(cursor)
        line_cursor.movePosition(QTextCursor.StartOfBlock)
        line_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        self.setTextCursor(line_cursor)

        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'run_code'):
            main_window.run_code()

        self.setTextCursor(original_cursor)

    def toggle_comment(self):
        """
        Toggle comment on selected lines or current line.
        Ctrl+/ shortcut.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        
        cursor.setPosition(start)
        start_block = cursor.blockNumber()

        
        cursor.setPosition(end)
        end_block = cursor.blockNumber()

        
        cursor.setPosition(start)
        for block_num in range(start_block, end_block + 1):
            cursor.movePosition(QTextCursor.StartOfBlock)
            line_text = cursor.block().text()

            
            stripped = line_text.lstrip()
            if stripped.startswith('#'):
                
                indent = len(line_text) - len(stripped)
                cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, indent)
                cursor.deleteChar()  
                
                if cursor.block().text()[indent:indent+1] == ' ':
                    cursor.deleteChar()
            else:
                
                cursor.insertText('# ')

            
            cursor.movePosition(QTextCursor.NextBlock)

        cursor.endEditBlock()

    def duplicate_line(self):
        """
        Duplicate current line or selection.
        Ctrl+D shortcut.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        if cursor.hasSelection():
            
            selected_text = cursor.selectedText()
            cursor.setPosition(cursor.selectionEnd())
            cursor.insertText(selected_text)
        else:
            
            current_position = cursor.position()
            block = cursor.block()

            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            line_text = cursor.selectedText()
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.insertText('\n' + line_text)

            
            cursor.setPosition(current_position)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def delete_line(self):
        """
        Delete current line.
        Ctrl+Shift+K shortcut.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)

        
        if not cursor.atEnd():
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)

        cursor.removeSelectedText()
        cursor.endEditBlock()

    def move_line_up(self):
        """
        Move current line up.
        Alt+Up shortcut.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        
        if cursor.blockNumber() == 0:
            cursor.endEditBlock()
            return

        
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_line = cursor.selectedText()
        cursor.removeSelectedText()

        
        if not cursor.atEnd():
            cursor.deleteChar()

        
        cursor.movePosition(QTextCursor.PreviousBlock)
        cursor.movePosition(QTextCursor.StartOfBlock)

        
        cursor.insertText(current_line + '\n')

        
        cursor.movePosition(QTextCursor.PreviousBlock)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def move_line_down(self):
        """
        Move current line down.
        Alt+Down shortcut.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_line = cursor.selectedText()

        
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.EndOfBlock)
        if cursor.atEnd():
            cursor.endEditBlock()
            return

        
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)  
        cursor.removeSelectedText()

        
        cursor.movePosition(QTextCursor.EndOfBlock)

        
        cursor.insertText('\n' + current_line)

        
        cursor.movePosition(QTextCursor.StartOfBlock)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def smart_home(self):
        """
        Smart Home key: First press goes to first non-whitespace character,
        second press goes to line start.
        Home key shortcut.
        """
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()

        
        first_non_ws = len(text) - len(text.lstrip())
        current_col = cursor.columnNumber()

        
        if current_col == first_non_ws or current_col < first_non_ws:
            cursor.movePosition(QTextCursor.StartOfBlock)
        else:
            
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, first_non_ws)

        self.setTextCursor(cursor)

    def smart_end(self):
        """
        Smart End key: Go to line end.
        End key shortcut.
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.EndOfBlock)
        self.setTextCursor(cursor)

    def toggle_show_whitespace(self):
        """
        Toggle visibility of whitespace characters (spaces and tabs).
        Ctrl+Shift+W shortcut.
        """
        self.show_whitespace = not self.show_whitespace
        self.viewport().update()  

        
        main_window = self.get_main_window()
        if main_window:
            status = "ON" if self.show_whitespace else "OFF"
            main_window.status_bar.showMessage(f"Show Whitespace: {status}", 2000)

    def apply_to_extra_cursors(self, text):
        """
        Apply text input to all extra cursors in multi-cursor mode.
        """
        if not self.extra_cursors:
            return

        
        sorted_positions = sorted(self.extra_cursors, reverse=True)
        new_positions = []

        for pos in sorted_positions:
            cursor = QTextCursor(self.document())
            cursor.setPosition(pos)
            cursor.insertText(text)
            
            new_positions.append(pos + len(text))

        
        self.extra_cursors = new_positions
        self.viewport().update()

    def apply_backspace_to_extra_cursors(self):
        """
        Apply backspace to all extra cursors in multi-cursor mode.
        """
        if not self.extra_cursors:
            return

        
        sorted_positions = sorted(self.extra_cursors, reverse=True)
        new_positions = []

        for pos in sorted_positions:
            if pos > 0:  
                cursor = QTextCursor(self.document())
                cursor.setPosition(pos)
                cursor.deletePreviousChar()
                new_positions.append(pos - 1)
            else:
                new_positions.append(pos)

        
        self.extra_cursors = new_positions
        self.viewport().update()

    def apply_delete_to_extra_cursors(self):
        """
        Apply delete to all extra cursors in multi-cursor mode.
        """
        if not self.extra_cursors:
            return

        
        sorted_positions = sorted(self.extra_cursors, reverse=True)
        new_positions = []

        for pos in sorted_positions:
            cursor = QTextCursor(self.document())
            cursor.setPosition(pos)
            if not cursor.atEnd():  
                cursor.deleteChar()
            new_positions.append(pos)

        
        self.extra_cursors = new_positions
        self.viewport().update()

    def get_main_window(self):
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent

    def contextMenuEvent(self, event):
        
        menu = self.createStandardContextMenu()

        
        menu.addSeparator()

        
        main_window = self.get_main_window()

        
        run_selected_action = QAction("Run Selected Code", self)
        run_selected_action.setShortcut(self.settings.get_shortcut("Execute Selected or All"))
        if self.textCursor().hasSelection():
            run_selected_action.triggered.connect(lambda: main_window.run_code() if main_window else None)
        else:
            run_selected_action.setEnabled(False)  
        menu.addAction(run_selected_action)

        
        run_all_action = QAction("Run All Code", self)
        run_all_action.setShortcut(self.settings.get_shortcut("Execute All Code"))
        run_all_action.triggered.connect(lambda: self.run_all_code())
        menu.addAction(run_all_action)

        
        execute_line_action = QAction("Execute Current Line", self)
        execute_line_action.setShortcut(self.settings.get_shortcut("Execute Current Line"))
        execute_line_action.triggered.connect(lambda: self.execute_current_line())
        menu.addAction(execute_line_action)

        
        menu.addSeparator()

        
        # Use '&&' so the menu shows a literal '&' (no mnemonic)
        search_action = QAction("Search && Replace", self)
        search_action.setShortcut(self.settings.get_shortcut("Find"))

        if main_window:
            selected = self.textCursor().selectedText()
            selected = selected.replace("\u2029", "\n") if selected else ""
            selected = selected if selected.strip() else None
            search_action.triggered.connect(
                lambda _=False, text=selected: main_window.show_search_dialog(initial_text=text, show_replace=True)
            )
        menu.addAction(search_action)

        
        menu.exec_(event.globalPos())

    def get_main_window(self):
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent

    def highlight_current_word(self):
        extra_selections = []
        selected_text = self.textCursor().selectedText()

        if selected_text and len(selected_text) >= 2:
            document = self.document()
            cursor = QTextCursor(document)
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor(125, 81, 0))

            while not cursor.isNull() and not cursor.atEnd():
                cursor = document.find(selected_text, cursor)
                if not cursor.isNull():
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = cursor
                    selection.format = highlight_format
                    extra_selections.append(selection)
        else:
            self._word_selections = []
            self._refresh_extra_selections()
            return

        self._word_selections = extra_selections
        self._refresh_extra_selections()

    def highlight_matching_brackets(self):
        """
        Highlight matching brackets/braces/parentheses/quotes.
        """
        cursor = self.textCursor()
        pos = cursor.position()

        
        brackets = {
            '(': ')', ')': '(',
            '[': ']', ']': '[',
            '{': '}', '}': '{',
        }

        
        char_at = self.document().characterAt(pos)
        char_before = self.document().characterAt(pos - 1) if pos > 0 else ''

        
        if char_at in brackets:
            bracket = char_at
            search_pos = pos
        elif char_before in brackets:
            bracket = char_before
            search_pos = pos - 1
        else:
            
            self._bracket_selections = []
            self._refresh_extra_selections()
            return

        
        match_pos = self.find_matching_bracket(search_pos, bracket, brackets)

        if match_pos != -1:
            
            extra_selections = []

            
            selection1 = QTextEdit.ExtraSelection()
            cursor1 = QTextCursor(self.document())
            cursor1.setPosition(search_pos)
            cursor1.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            selection1.cursor = cursor1
            selection1.format.setBackground(QColor(80, 120, 80))  
            selection1.format.setForeground(QColor(255, 255, 255))  
            extra_selections.append(selection1)

            
            selection2 = QTextEdit.ExtraSelection()
            cursor2 = QTextCursor(self.document())
            cursor2.setPosition(match_pos)
            cursor2.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            selection2.cursor = cursor2
            selection2.format.setBackground(QColor(80, 120, 80))  
            selection2.format.setForeground(QColor(255, 255, 255))  
            extra_selections.append(selection2)

            self._bracket_selections = extra_selections
            self._refresh_extra_selections()
        else:
            self._bracket_selections = []
            self._refresh_extra_selections()

    def find_matching_bracket(self, pos, bracket, brackets):
        """
        Find the position of matching bracket.
        """
        doc = self.document()
        text = doc.toPlainText()

        
        if pos < 0 or pos >= len(text):
            return -1

        is_opening = bracket in '([{'
        match_bracket = brackets[bracket]

        if is_opening:
            
            count = 1
            for i in range(pos + 1, len(text)):
                if i >= len(text):  
                    break
                if text[i] == bracket:
                    count += 1
                elif text[i] == match_bracket:
                    count -= 1
                    if count == 0:
                        return i
        else:
            
            count = 1
            for i in range(pos - 1, -1, -1):
                if i < 0 or i >= len(text):  
                    break
                if text[i] == bracket:
                    count += 1
                elif text[i] == match_bracket:
                    count -= 1
                    if count == 0:
                        return i

        return -1  

    def update_cursor_position(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1

        main_window = self.get_main_window()
        if main_window:
            main_window.status_bar.showMessage(f"{line}:{column}")

    def _refresh_extra_selections(self):
        selections = []
        if self._line_selection:
            selections.append(self._line_selection)
        if self._clicked_line_selection:
            selections.append(self._clicked_line_selection)
        selections.extend(self._word_selections)
        selections.extend(self._bracket_selections)
        self.setExtraSelections(selections)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())

        
        pen = QPen(QColor(CodeEditorSettings().intender_color))
        pen.setWidth(CodeEditorSettings().intender_width)
        painter.setPen(pen)

        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                text = block.text()
                indentation_level = len(text) - len(text.lstrip())
                indent_size = int(CodeEditorSettings().tab_size)
                font_metrics = self.fontMetrics()
                char_width = font_metrics.horizontalAdvance(' ')

                for i in range(1, (indentation_level // indent_size) + 1):
                    x = i * indent_size * char_width
                    painter.drawLine(x, top, x, bottom)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

        
        if self.show_whitespace:
            pen = QPen(QColor(100, 100, 100))  
            painter.setPen(pen)

            block = self.firstVisibleBlock()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()

            font_metrics = self.fontMetrics()
            char_width = font_metrics.horizontalAdvance(' ')
            char_height = font_metrics.height()

            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    text = block.text()
                    x_offset = self.contentOffset().x()

                    for i, char in enumerate(text):
                        x = i * char_width + x_offset
                        y = top + char_height / 2

                        if char == ' ':
                            
                            painter.drawEllipse(int(x + char_width / 2 - 1), int(y - 1), 2, 2)
                        elif char == '\t':
                            
                            arrow_y = int(y)
                            arrow_start_x = int(x + 2)
                            arrow_end_x = int(x + char_width * int(CodeEditorSettings().tab_size) - 2)
                            painter.drawLine(arrow_start_x, arrow_y, arrow_end_x, arrow_y)
                            
                            painter.drawLine(arrow_end_x, arrow_y, arrow_end_x - 3, arrow_y - 2)
                            painter.drawLine(arrow_end_x, arrow_y, arrow_end_x - 3, arrow_y + 2)

                block = block.next()
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()

        
        if self.extra_cursors:
            pen = QPen(QColor(255, 255, 255))  
            pen.setWidth(2)
            painter.setPen(pen)

            for pos in self.extra_cursors:
                cursor = QTextCursor(self.document())
                cursor.setPosition(pos)
                rect = self.cursorRect(cursor)

                
                painter.drawLine(rect.topLeft(), rect.bottomLeft())

        painter.end()

    def line_number_area_width(self):
        digits = len(str(self.blockCount()))
        space = 20 + self.fontMetrics().horizontalAdvance('9') * digits +10
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        if self.isReadOnly():
            self._line_selection = None
            self._refresh_extra_selections()
            return

        selection = QTextEdit.ExtraSelection()
        lineColor = QColor(77, 77, 77)
        selection.format.setBackground(lineColor)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self._line_selection = selection
        self._refresh_extra_selections()

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), CodeEditorSettings().line_number_background_color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        font = painter.font()
        font.setBold(CodeEditorSettings().line_number_weight)
        font.setPointSize(CodeEditorSettings().main_font_size)
        painter.setFont(font)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                text = block.text().strip()

                
                folding_enabled = CodeEditorSettings().ENABLE_CODE_FOLDING
                is_foldable = folding_enabled and self.is_foldable_line(block_number)
                is_folded = folding_enabled and block_number in self.folded_blocks

                
                if folding_enabled and is_foldable:
                    icon_size = 8  
                    icon_x = 3  
                    icon_y = int(top + (self.fontMetrics().height() - icon_size) / 2)

                    
                    icon_color = QColor(120, 120, 120)
                    painter.setPen(QPen(icon_color))
                    painter.setBrush(icon_color)

                    if is_folded:
                        
                        triangle = [
                            QPoint(icon_x, icon_y),
                            QPoint(icon_x, icon_y + icon_size),
                            QPoint(icon_x + icon_size, icon_y + icon_size // 2)
                        ]
                        painter.drawPolygon(triangle)
                    else:
                        
                        triangle = [
                            QPoint(icon_x, icon_y),
                            QPoint(icon_x + icon_size, icon_y),
                            QPoint(icon_x + icon_size // 2, icon_y + icon_size)
                        ]
                        painter.drawPolygon(triangle)

                
                painter.setPen(CodeEditorSettings().line_number_color)
                line_number_x = 15  
                painter.drawText(line_number_x, top, self.line_number_area.width() - line_number_x - 5,
                                self.fontMetrics().height(), Qt.AlignLeft, number)

                
                if folding_enabled and is_folded:
                    end_line = self.find_block_end(block_number)
                    hidden_lines = end_line - block_number
                    if hidden_lines > 0:
                        
                        painter.setPen(QColor(100, 100, 100))
                        indicator_text = f"  ... ({hidden_lines} lines)"
                        text_width = self.fontMetrics().horizontalAdvance(block.text())
                        painter.drawText(self.line_number_area.width() + text_width + 10, top,
                                       500, self.fontMetrics().height(),
                                       Qt.AlignLeft, indicator_text)

            
            block_number += 1
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

        painter.setPen(CodeEditorSettings().line_number_draw_line)
        painter.drawLine(self.line_number_area.width() - 1, event.rect().top(), self.line_number_area.width() - 1,
                         event.rect().bottom())

    def mousePressEvent(self, event):
        """Handle mouse press for multi-cursor support and line highlighting"""
        if getattr(self, "completer", None):
            try:
                self.completer.hide_popup()
            except Exception:
                pass
        
        if event.modifiers() == Qt.ControlModifier and event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()

            
            if position in self.extra_cursors:
                
                self.extra_cursors.remove(position)
            else:
                
                self.extra_cursors.append(position)

            self.viewport().update()  
            return

        
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.NoModifier:
            self.extra_cursors.clear()

        super().mousePressEvent(event)  
        self.highlight_clicked_line()

    def highlight_clicked_line(self):
        """Highlight the clicked line with a translucent background."""
        cursor = self.textCursor()
        selection = QTextEdit.ExtraSelection()
        line_color = CodeEditorSettings().clicked_line_color
        selection.format.setBackground(line_color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = cursor
        selection.cursor.clearSelection()
        self._clicked_line_selection = selection
        self._refresh_extra_selections()

    def get_indentation_level(self, text):
        """Get the indentation level of a line"""
        return len(text) - len(text.lstrip())

    def find_block_end(self, start_line):
        """Find the end line of a code block starting at start_line"""
        block = self.document().findBlockByNumber(start_line)
        if not block.isValid():
            return start_line

        start_text = block.text()
        start_indent = self.get_indentation_level(start_text)

        
        block = block.next()
        current_line = start_line + 1

        while block.isValid():
            text = block.text().strip()

            
            if not text or text.startswith('#'):
                block = block.next()
                current_line += 1
                continue

            
            current_indent = self.get_indentation_level(block.text())

            
            if current_indent <= start_indent:
                return current_line - 1

            block = block.next()
            current_line += 1

        
        return current_line - 1

    def is_foldable_line(self, line_number):
        """Check if a line can be folded (starts with def, class, if, for, while, etc.)"""
        block = self.document().findBlockByNumber(line_number)
        if not block.isValid():
            return False

        text = block.text().strip()

        
        foldable_keywords = ['def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'with ', 'match ', 'case ']

        for keyword in foldable_keywords:
            if text.startswith(keyword):
                
                if text.endswith(':'):
                    
                    end_line = self.find_block_end(line_number)
                    return end_line > line_number

        return False

    def toggle_fold(self, line_number):
        """Toggle folding for a block starting at line_number"""
        if not CodeEditorSettings().ENABLE_CODE_FOLDING:
            return
        if not self.is_foldable_line(line_number):
            return

        if line_number in self.folded_blocks:
            
            self.folded_blocks.remove(line_number)
        else:
            
            self.folded_blocks.add(line_number)

        
        self.update_folded_blocks()
        self.viewport().update()
        self.line_number_area.update()

    def is_line_folded(self, line_number):
        """Check if a line is inside a folded block"""
        for folded_line in self.folded_blocks:
            if folded_line < line_number <= self.find_block_end(folded_line):
                return True
        return False

    def update_folded_blocks(self):
        """Update the visibility of folded blocks"""
        if not CodeEditorSettings().ENABLE_CODE_FOLDING:
            self.folded_blocks.clear()
            return
        block = self.document().firstBlock()
        line_number = 0

        while block.isValid():
            
            should_hide = self.is_line_folded(line_number)

            
            block.setVisible(not should_hide)

            block = block.next()
            line_number += 1

        
        self.updateGeometry()
        self.viewport().update()
        self.update()

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event):
        """Handle mouse clicks on line number area for folding"""
        if not CodeEditorSettings().ENABLE_CODE_FOLDING:
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            
            viewport_pos = event.pos()
            viewport_pos.setX(0)  

            
            cursor = self.code_editor.cursorForPosition(viewport_pos)
            line_number = cursor.blockNumber()

            
            if self.code_editor.is_foldable_line(line_number):
                self.code_editor.toggle_fold(line_number)
                event.accept()
                return

        super().mousePressEvent(event)


class PyCharmDarkStyle(Style):
    """
    PyCharm Dark theme adapted for Pygments.
    """
    default_style = ""
    background_color = "#1e1f22"  
    highlight_color = "#26282e"  

    styles = {
        
        Text: '#bcbec4',  
        Text.Whitespace: '#6f737a',  
        Text.Highlight: 'bg:#26282e',  
        Error: 'bold bg:#ff5640',  

        
        Comment: 'italic #7a7e85',  
        Comment.Multiline: 'italic #7a7e85',  
        Comment.Preproc: 'italic #7a7e85',  
        Comment.Special: 'italic bold #6f737a',  

        
        Keyword: 'bold #cf8e6d',  
        Keyword.Constant: 'bold #cf8e6d',  
        Keyword.Declaration: 'bold #cf8e6d',  
        Keyword.Namespace: 'bold #cf8e6d',  
        Keyword.Pseudo: 'italic #cf8e6d',  

        
        Name: '#bcbec4',  
        Name.Builtin: '#c77dbb',  
        Name.Function: '#57aaf7',  
        Name.Class: 'bold #bcbec4',  
        Name.Decorator: '#fa7db1',  
        Name.Exception: 'bold #ff5640',  
        Name.Variable: '#bcbec4',  
        Name.Variable.Global: 'italic #bcbec4',  
        Name.Variable.Instance: 'italic #bcbec4',  
        Name.Attribute: '#A9B7C6',  
        Name.Tag: 'bold #d5b778',  

        
        String: '#A9B7C6',  
        String.Interpol: '#A9B7C6',  
        String.Escape: '#c77dbb',  
        String.Doc: 'italic #6A8759',  

        
        Number: '#2aacb8',  
        Operator: '#bcbec4',  
        Operator.Word: 'bold #cf8e6d',  
        Punctuation: '#bcbec4',  

        
        Generic.Deleted: 'bg:#402929',  
        Generic.Inserted: 'bg:#3d7a49',  
        Generic.Heading: 'bold #bcbec4',  
        Generic.Subheading: 'bold #bcbec4',  
        Generic.Error: 'bg:#fa6675 #FFFFFF',  
        Generic.Emph: 'italic',  
        Generic.Strong: 'bold',  
        Generic.Prompt: '#bcbec4',  
        Generic.Output: '#bcbec4',  
        Generic.Traceback: '#f75464',  

        
        Name.Tag: 'bold #d5b778',  
        Name.Attribute: '#A9B7C6',  
        String.Double: '#A9B7C6',  
        String.Single: '#A9B7C6',  
        String.Symbol: '#A9B7C6',  

        
        Name.Property: '#fa7db1',  
        Name.Label: '#d5b778',  
        Name.Constant: '#c77dbb',  
        String.Regex: '#57aaf7',  
        Keyword.Type: 'italic #c77dbb',  
    }


class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        
        style = "monokai"  
        
        try:
            with open(settings_path, "r") as settings_file:
                settings = json.load(settings_file)
                style = settings.get("General", {}).get("syntax_style_dropdown", style)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            pass
        super().__init__(document)

        
        self.formatter = HtmlFormatter(style=style)
        self.lexer = PythonLexer()
        self.token_styles = self._generate_token_styles()
        self._triple_string_format = self.token_styles.get(String, QTextCharFormat())
        self._resolved_format_cache = {}
        self._default_text_format = self.token_styles.get(Text, QTextCharFormat())
        self._text_fg = self._format_for_token(Text)
        self._op_fg = self._format_for_token(Operator)
        self._attr_fg = self._format_for_token(Name.Attribute)
        self._self_fg = self._pick_self_format()

    def _generate_token_styles(self):
        """Convert Pygments token styles to PyQt formats."""
        token_styles = {}
        for token, style in self.formatter.style:
            text_format = QTextCharFormat()

            if style['color']:
                text_format.setForeground(QColor(f"#{style['color']}"))
            if style['bold']:
                text_format.setFontWeight(QFont.Bold)
            if style['italic']:
                text_format.setFontItalic(True)

            token_styles[token] = text_format
        return token_styles

    def _format_for_token(self, token_type):
        """
        Resolve a QTextCharFormat for a token using Pygments' parent-token fallback.
        Many styles only define `Name` but the lexer emits `Name.Attribute`, etc.
        """
        if token_type in self._resolved_format_cache:
            return self._resolved_format_cache[token_type]

        resolved = None
        current = token_type
        # Walk up the token hierarchy until we find a styled token.
        while current is not None and current not in self.token_styles and current.parent is not current:
            if current.parent is None:
                break
            current = current.parent

        if current in self.token_styles:
            resolved = self.token_styles[current]

        # If punctuation has no explicit style, borrow Operator/Text so brackets/braces get color.
        if resolved is None and token_type in (Punctuation,):
            resolved = self.token_styles.get(Operator, self._default_text_format)

        if resolved is None:
            resolved = self._default_text_format

        self._resolved_format_cache[token_type] = resolved
        return resolved

    def _has_foreground(self, fmt: QTextCharFormat) -> bool:
        try:
            return fmt.hasProperty(QTextCharFormat.ForegroundBrush)
        except Exception:
            return False

    def _foreground_color(self, fmt: QTextCharFormat):
        try:
            if not self._has_foreground(fmt):
                return None
            return fmt.foreground().color()
        except Exception:
            return None

    def _pick_distinct(self, preferred: QTextCharFormat, fallback: QTextCharFormat, against: QTextCharFormat):
        """
        Prefer `preferred` if it has a foreground and differs from `against` (when possible),
        otherwise fall back.
        """
        p = self._foreground_color(preferred)
        a = self._foreground_color(against)
        if p is not None and (a is None or p != a):
            return preferred
        f = self._foreground_color(fallback)
        if f is not None:
            return fallback
        return preferred

    def _pick_self_format(self):
        # Use Name.Builtin.Pseudo if the theme defines it, otherwise pick something distinct.
        pseudo = self._format_for_token(Name.Builtin.Pseudo)
        builtin = self._format_for_token(Name.Builtin)
        text = self._format_for_token(Text)
        chosen = self._pick_distinct(pseudo, builtin, against=text)
        # As a last resort, use attribute color (usually distinct in many themes).
        chosen = self._pick_distinct(chosen, self._format_for_token(Name.Attribute), against=text)
        return chosen

    def highlightBlock(self, text):
        """
        Split text into tokens and apply styles.

        Note: QSyntaxHighlighter runs per-block; Pygments lexers are not stateful per line.
        We special-case triple-quoted strings so multi-line docstrings highlight correctly.
        """
        self.setCurrentBlockState(0)

        def apply_pygments(segment: str, offset: int):
            if not segment:
                return
            tokens = self.lexer.get_tokens(segment)
            local_index = 0
            for token_type, token_value in tokens:
                if local_index >= len(segment):
                    break
                if not token_value:
                    continue
                length = len(token_value)
                fmt = self._format_for_token(token_type)
                safe_length = max(0, min(length, len(segment) - local_index))
                if safe_length:
                    self.setFormat(offset + local_index, safe_length, fmt)
                local_index += length

        prev_state = self.previousBlockState()
        in_delim = None
        in_state = 0
        if prev_state == 1:
            in_delim = "'''"
            in_state = 1
        elif prev_state == 2:
            in_delim = '"""'
            in_state = 2

        start = 0

        if in_delim:
            end = text.find(in_delim)
            if end == -1:
                self.setFormat(0, len(text), self._triple_string_format)
                self.setCurrentBlockState(in_state)
                return
            self.setFormat(0, min(len(text), end + 3), self._triple_string_format)
            start = end + 3

        while start < len(text):
            next_single = text.find("'''", start)
            next_double = text.find('"""', start)
            next_positions = [p for p in (next_single, next_double) if p != -1]

            if not next_positions:
                apply_pygments(text[start:], start)
                break

            next_pos = min(next_positions)
            apply_pygments(text[start:next_pos], start)

            delim = "'''" if next_pos == next_single else '"""'
            state = 1 if delim == "'''" else 2
            end = text.find(delim, next_pos + 3)
            if end == -1:
                self.setFormat(next_pos, len(text) - next_pos, self._triple_string_format)
                self.setCurrentBlockState(state)
                break

            self.setFormat(next_pos, min(len(text) - next_pos, (end + 3) - next_pos), self._triple_string_format)
            start = end + 3

        # Extra semantic-style overlays (theme-derived) for a more IDE-like feel.
        self._apply_parameter_name_highlight(text)
        self._apply_self_highlight(text)
        self._apply_bracket_highlight(text)

    def _apply_parameter_name_highlight(self, text: str):
        # Highlight parameter names in `def func(a, b=1, *, c=None, **kw):`
        m = re.match(r"^\\s*def\\s+[_A-Za-z][_A-Za-z0-9]*\\s*\\((.*)\\)\\s*:", text)
        if not m:
            return
        params = m.group(1)
        if not params:
            return

        # Find the absolute offset where params start in the line.
        start_idx = text.find("(")
        if start_idx == -1:
            return
        start_idx += 1

        # Match identifiers that look like parameter names; skip common syntax tokens.
        for match in re.finditer(r"\\b[_A-Za-z][_A-Za-z0-9]*\\b", params):
            name = match.group(0)
            if name in {"def", "return", "lambda"}:
                continue
            abs_pos = start_idx + match.start()
            self.setFormat(abs_pos, len(name), self._attr_fg)

    def _apply_self_highlight(self, text: str):
        for match in re.finditer(r"\\bself\\b", text):
            self.setFormat(match.start(), 4, self._self_fg)

    def _apply_bracket_highlight(self, text: str):
        # Color brackets/braces/parentheses and dots so `{}`, `[]`, `self.` become visible.
        # Use operator color when it is distinct, otherwise keep text color.
        fmt = self._pick_distinct(self._op_fg, self._attr_fg, against=self._text_fg)
        for match in re.finditer(r"[\\[\\]\\{\\}\\(\\)\\.]", text):
            self.setFormat(match.start(), 1, fmt)
