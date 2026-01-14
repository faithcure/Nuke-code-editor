import inspect
import re
from PySide2.QtGui import QColor, QPainter, QTextCursor, QFont
from PySide2.QtWidgets import QPlainTextEdit
from PySide2.QtCore import Qt, QTimer
import importlib
import editor.core
import os

try:
    import nuke
except ImportError:
    nuke = None

importlib.reload(editor.core)
from editor.core import CodeEditorSettings, PathFromOS


class InlineGhosting(QPlainTextEdit):
    """
    A custom text editor widget with inline ghost text and intelligent code suggestions.

    This widget displays predictive text suggestions as users type and allows them to accept
    suggestions using specific key combinations. It also integrates with `nuke` and `nukescripts`
    to provide function suggestions and parameters.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.suggestions, self.nuke_suggestions, self.nukescripts_suggestions, self.suggestion_priority = self.load_suggestions_from_modules()
        self.usage_count = {key: 0 for key in self.suggestions}  
        self.ghost_text = ""
        self.current_suggestion = None
        self.accepting_suggestion = False
        self._suppress_cursor_clear = False
        self.textChanged.connect(self.update_ghost_text)
        self.cursorPositionChanged.connect(self._on_cursor_position_changed)

    def _on_cursor_position_changed(self):
        if self._suppress_cursor_clear:
            return
        self.clear_ghost_text()

    def clear_ghost_text(self):
        if not self.ghost_text and not self.current_suggestion:
            return
        self.ghost_text = ""
        self.current_suggestion = None
        self.viewport().update()

    def _cursor_in_string_or_comment(self):
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()

        in_single = False
        in_double = False
        in_triple_single = False
        in_triple_double = False
        escaped = False

        def scan_triple_state_from_previous_blocks(limit_blocks: int = 200):
            block = cursor.block().previous()
            state = None  # "'''" or '"""'
            remaining = limit_blocks
            while block.isValid() and remaining > 0:
                remaining -= 1
                text = block.text()
                positions = []
                for delim in ("'''", '"""'):
                    start = 0
                    while True:
                        idx = text.find(delim, start)
                        if idx == -1:
                            break
                        positions.append((idx, delim))
                        start = idx + 3
                positions.sort(reverse=True)
                for _idx, delim in positions:
                    if state is None:
                        state = delim
                    elif state == delim:
                        state = None
                block = block.previous()
            return state

        prev_triple = scan_triple_state_from_previous_blocks()
        if prev_triple == "'''":
            in_triple_single = True
        elif prev_triple == '"""':
            in_triple_double = True

        i = 0
        while i < pos:
            if not (in_single or in_double or in_triple_single or in_triple_double):
                if block_text.startswith("'''", i):
                    in_triple_single = True
                    i += 3
                    continue
                if block_text.startswith('"""', i):
                    in_triple_double = True
                    i += 3
                    continue
                ch = block_text[i]
                if ch == "'":
                    in_single = True
                    i += 1
                    continue
                if ch == '"':
                    in_double = True
                    i += 1
                    continue
                if ch == "#":
                    return True, False
            else:
                if in_triple_single and block_text.startswith("'''", i):
                    in_triple_single = False
                    i += 3
                    continue
                if in_triple_double and block_text.startswith('"""', i):
                    in_triple_double = False
                    i += 3
                    continue

                ch = block_text[i]
                if in_single:
                    if not escaped and ch == "'":
                        in_single = False
                    escaped = (ch == "\\") and not escaped
                elif in_double:
                    if not escaped and ch == '"':
                        in_double = False
                    escaped = (ch == "\\") and not escaped
                else:
                    escaped = False

            i += 1

        in_string = in_single or in_double or in_triple_single or in_triple_double
        return False, in_string

    def load_suggestions_from_modules(self):
        """
        Loads function suggestions from the `nuke` and `nukescripts` modules.

        Returns:
            tuple: Suggestions, Nuke-only suggestions, nukescripts-only suggestions, and priority map.
        """
        suggestions = {}
        nuke_suggestions = {}
        nukescripts_suggestions = {}
        suggestion_priority = {}

        if nuke:
            for attr in dir(nuke):
                if not attr.startswith("_"):
                    completion_text = self.get_completion_text(nuke, attr)
                    suggestions[attr] = completion_text
                    nuke_suggestions[attr] = completion_text
                    suggestion_priority[attr] = 2

        try:
            import nukescripts
            for attr in dir(nukescripts):
                if not attr.startswith("_"):
                    completion_text = self.get_completion_text(nukescripts, attr)
                    suggestions[attr] = completion_text
                    nukescripts_suggestions[attr] = completion_text
                    suggestion_priority.setdefault(attr, 1)
        except ImportError:
            pass

        return suggestions, nuke_suggestions, nukescripts_suggestions, suggestion_priority

    def get_prefix_and_context(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            return "", None

        in_comment, in_string = self._cursor_in_string_or_comment()
        if in_comment or in_string:
            return "", None

        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()
        before_cursor = block_text[:pos_in_block]
        module_match = re.search(r"(nuke|nukescripts)\.(\w*)$", before_cursor)
        if module_match:
            return module_match.group(2), module_match.group(1)

        word_cursor = QTextCursor(cursor)
        word_cursor.select(QTextCursor.WordUnderCursor)
        word = word_cursor.selectedText()
        if not word:
            return "", None
        if cursor.position() != word_cursor.selectionEnd():
            return "", None
        prefix_len = max(0, cursor.position() - word_cursor.selectionStart())
        return word[:prefix_len], None

    def get_sorted_suggestions(self, module_context):
        if module_context == "nuke":
            candidates = self.nuke_suggestions.items()
        elif module_context == "nukescripts":
            candidates = self.nukescripts_suggestions.items()
        else:
            candidates = self.suggestions.items()

        return sorted(
            candidates,
            key=lambda item: (
                -self.suggestion_priority.get(item[0], 0),
                -self.usage_count.get(item[0], 0),
                item[0],
            ),
        )

    def get_completion_text(self, module, attr):
        """
        Retrieves the completion text for a given attribute in a module.

        Args:
            module: The module to inspect.
            attr: The attribute name.

        Returns:
            str: Completion text based on the function's signature or docstring.
        """
        item = getattr(module, attr)
        if inspect.isfunction(item) or inspect.ismethod(item):
            try:
                params = inspect.signature(item).parameters
                param_list = ", ".join(param.name for param in params.values())
                return f"{attr}({param_list})"
            except (ValueError, TypeError):
                
                docstring = getattr(item, "__doc__", "")
                if docstring:
                    first_line = docstring.splitlines()[0]
                    return f"{attr}({first_line})"
                else:
                    return f"{attr}()"
        elif isinstance(item, str):
            return f"{attr}('')"
        elif isinstance(item, (int, float)):
            return f"{attr}"
        else:
            return f"{attr}()"

    def update_ghost_text(self):
        """
        Updates the ghost text based on the current word under the cursor.
        """
        if not CodeEditorSettings().ENABLE_INLINE_GHOSTING:
            self.clear_ghost_text()
            return

        if self.accepting_suggestion:
            self.clear_ghost_text()
            return

        prefix, module_context = self.get_prefix_and_context()
        if not prefix:
            self.clear_ghost_text()
            return

        if module_context is None and len(prefix) < 2:
            self.clear_ghost_text()
            return

        sorted_suggestions = self.get_sorted_suggestions(module_context)
        suggestion = self.find_suggestion(prefix, sorted_suggestions)
        if suggestion:
            suggestion_key, completion_text = suggestion
            self.current_suggestion = suggestion_key
            if completion_text.startswith(prefix):
                self.ghost_text = completion_text[len(prefix):]
            else:
                self.ghost_text = completion_text
        else:
            self.clear_ghost_text()

        self.viewport().update()

    def find_suggestion(self, prefix, sorted_suggestions):
        """
        Finds a relevant suggestion based on the typed word, including partial matches.

        Args:
            word (str): The current word under the cursor.
            sorted_suggestions (dict): Dictionary of sorted suggestions.

        Returns:
            str: The completion text for the suggestion.
        """
        for suggestion, completion_text in sorted_suggestions:
            if suggestion.startswith(prefix):
                if suggestion == prefix and completion_text == suggestion:
                    continue
                return suggestion, completion_text
        return ""

    def accept_ghost_text(self, cursor=None):
        if not self.ghost_text:
            return False
        if cursor is None:
            cursor = self.textCursor()
        self.accepting_suggestion = True
        cursor.insertText(self.ghost_text)
        if self.current_suggestion:
            self.usage_count[self.current_suggestion] = self.usage_count.get(self.current_suggestion, 0) + 1
        self.ghost_text = ""
        self.current_suggestion = None
        self.accepting_suggestion = False
        self.viewport().update()
        return True

    def keyPressEvent(self, event):
        """
        Handles key press events to accept suggestions or trigger special behaviors.

        Args:
            event: The key press event.
        """
        if event.text() or event.key() in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Return, Qt.Key_Enter):
            self._suppress_cursor_clear = True
            QTimer.singleShot(0, lambda: setattr(self, "_suppress_cursor_clear", False))

        if event.key() == Qt.Key_Return and event.modifiers() == Qt.AltModifier and self.ghost_text:
            self.accepting_suggestion = True
            self.accept_ghost_text()
            self.accepting_suggestion = False
            return

        elif event.key() == Qt.Key_ParenRight:
            cursor = self.textCursor()
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText()

            if word in self.suggestions and callable(getattr(nuke, word, None)):
                cursor.movePosition(QTextCursor.EndOfWord)
                cursor.insertText("()")
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
                return

        super().keyPressEvent(event)

    def paintEvent(self, event):
        """
        Custom paint event to render the ghost text.

        Args:
            event: The paint event.
        """
        super().paintEvent(event)
        if self.ghost_text:
            painter = QPainter(self.viewport())
            painter.setPen(CodeEditorSettings().GHOSTING_COLOR)

            cursor_rect = self.cursorRect(self.textCursor())
            x_offset, y_offset = cursor_rect.x(), cursor_rect.y() + self.fontMetrics().ascent()
            painter.drawText(x_offset, y_offset, self.ghost_text)
            painter.end()
