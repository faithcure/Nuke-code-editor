import sys
import traceback
import io
import os
import re
import builtins
from datetime import datetime
from PySide2.QtWidgets import (QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLineEdit, QComboBox, QLabel, QToolBar, QAction, QFileDialog, QApplication)
from PySide2.QtGui import (QFont, QTextCursor, QTextCharFormat,
                            QColor, QTextDocument, QIcon, QKeySequence)
from PySide2.QtCore import Qt, Signal, QRegExp, QSize, QObject, QThread
from editor.core import PathFromOS
import logging

try:
    import nuke
    import nukescripts
except ImportError:
    nuke = None

class DebugLogger:
    def __init__(self, log_file="debug_log.txt"):
        self.logger = logging.getLogger("DebugLogger")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, message, level="info"):
        if level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)

def validate_code(code):
    try:
        compile(code, "<string>", "exec")
        return None
    except SyntaxError as e:
        return str(e)

class SysOutputRedirector:
    def __init__(self, output_widget):
        self.output_widget = output_widget

    def write(self, message):
        if message.strip():
            self.output_widget.append_output(message)

    def flush(self):
        pass


class PythonExecutionWorker(QObject):
    output = Signal(str, str)
    finished = Signal()

    def __init__(self, code):
        super().__init__()
        self.code = code
        self._stop_requested = False
        self._stdout_proxy = None

    def stop(self):
        self._stop_requested = True

    def _make_stream_proxy(self, level):
        worker = self

        class _StreamProxy:
            def write(self, message):
                if message:
                    worker.output.emit(message, level)

            def flush(self):
                pass

        return _StreamProxy()

    def _trace(self, frame, event, arg):
        if self._stop_requested:
            raise KeyboardInterrupt("Execution stopped")
        return self._trace

    def run(self):
        validation_error = validate_code(self.code)
        if validation_error:
            self.output.emit(f"Syntax Error: {validation_error}", "ERROR")
            self.finished.emit()
            return

        def _print(*args, **kwargs):
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            message = sep.join(str(arg) for arg in args) + end
            if message.strip():
                self.output.emit(message, "OUTPUT")

        try:
            sys.settrace(self._trace)
            safe_builtins = dict(builtins.__dict__)
            safe_builtins["print"] = _print
            exec(self.code, {"__builtins__": safe_builtins}, {})
            self.output.emit("Code executed successfully", "SUCCESS")
        except KeyboardInterrupt:
            self.output.emit("Execution stopped by user.", "WARNING")
        except Exception:
            error_message = traceback.format_exc()
            self.output.emit(error_message, "ERROR")
        finally:
            sys.settrace(None)
            self.finished.emit()

def execute_python_code(code, output_widget, debug_mode=False):
    validation_error = validate_code(code)
    if validation_error:
        output_widget.append_output(f"Syntax Error: {validation_error}", "ERROR")
        return

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        exec(code, {'__builtins__': __builtins__}, {})
        output = sys.stdout.getvalue()
        if output.strip():
            output_widget.append_output(output, "OUTPUT")
    except Exception as e:
        error_message = traceback.format_exc()
        output_widget.append_output(error_message, "ERROR")
    finally:
        sys.stdout = old_stdout

def execute_nuke_code(code, output_widget):
    """
    Executes the given Nuke code and directs the result to the output_widget.
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = SysOutputRedirector(output_widget)
    sys.stderr = SysOutputRedirector(output_widget)

    try:
        
        result = nuke.executeInMainThreadWithResult(lambda: exec(code))
        if result is not None:
            pass
    except Exception as e:
        
        error_message = traceback.format_exc()
        output_widget.append_output(error_message, "ERROR")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class OutputTextEdit(QTextEdit):
    """Enhanced QTextEdit with professional output features"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.load_custom_font()
        self.setup_style()

        
        self.color_scheme = {
            "ERROR": "#ff6b6b",      
            "WARNING": "#ffcc00",    
            "INFO": "#4a9eff",       
            "SUCCESS": "#51cf66",    
            "DEBUG": "#868e96",      
            "OUTPUT": "#e0e0e0",     
            "TIMESTAMP": "#6c757d",  
        }

    def load_custom_font(self):
        """Load a system monospace font"""
        self.setFont(QFont("Consolas", 10))

    def setup_style(self):
        """Setup text edit styling"""
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: none;
                padding: 4px;
            }
        """)

    def append_with_format(self, message, color, bold=False, italic=False):
        """Append text with specific formatting"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        format = QTextCharFormat()
        format.setForeground(QColor(color))
        if bold:
            format.setFontWeight(QFont.Bold)
        if italic:
            format.setFontItalic(italic)

        cursor.insertText(message, format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class OutputWidget(QWidget):
    """Professional Output Console with advanced features"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auto_scroll = True
        self.show_timestamps = False
        self.show_level_tags = False
        self.filter_level = "ALL"  
        self.message_count = {"ERROR": 0, "WARNING": 0, "INFO": 0, "OUTPUT": 0}

        
        self.all_messages = []  

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI with toolbar and text area"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        
        self.text_edit = OutputTextEdit()
        layout.addWidget(self.text_edit)

        
        self.status_layout = QHBoxLayout()
        self.status_layout.setContentsMargins(4, 2, 4, 2)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #868e96; font-size: 9pt;")
        self.status_layout.addWidget(self.status_label)

        self.stats_label = QLabel("Errors: 0 | Warnings: 0 | Info: 0")
        self.stats_label.setStyleSheet("color: #868e96; font-size: 9pt;")
        self.status_layout.addWidget(self.stats_label)
        self.status_layout.addStretch()

        layout.addLayout(self.status_layout)

    def create_toolbar(self):
        """Create PyCharm-style toolbar with icon-only buttons on left, filter/search on right"""
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3e3e3e;
            }
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: none;
                padding: 4px;
                font-size: 14pt;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
                border-radius: 2px;
            }
            QPushButton:checked {
                background-color: #4e4e4e;
                border-radius: 2px;
            }
            QComboBox {
                background-color: #3e3e3e;
                color: #e0e0e0;
                border: 1px solid #4e4e4e;
                border-radius: 2px;
                padding: 3px 6px;
                font-size: 9pt;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 4px;
            }
            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            QLineEdit {
                background-color: #3e3e3e;
                color: #e0e0e0;
                border: 1px solid #4e4e4e;
                border-radius: 2px;
                padding: 3px 6px;
                font-size: 9pt;
            }
            QLabel {
                color: #868e96;
                font-size: 9pt;
            }
        """)

        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.setSpacing(2)

        
        icons_path = PathFromOS().icons_path

        
        clear_icon = QIcon(os.path.join(icons_path, "output_clear.svg"))
        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(clear_icon)
        self.clear_btn.setIconSize(QSize(16, 16))
        self.clear_btn.setToolTip("Clear all output (Ctrl+L)")
        self.clear_btn.setFixedSize(QSize(24, 24))
        self.clear_btn.clicked.connect(self.clear_output)
        toolbar_layout.addWidget(self.clear_btn)

        
        copy_icon = QIcon(os.path.join(icons_path, "output_copy.svg"))
        self.copy_btn = QPushButton()
        self.copy_btn.setIcon(copy_icon)
        self.copy_btn.setIconSize(QSize(16, 16))
        self.copy_btn.setToolTip("Copy all output to clipboard")
        self.copy_btn.setFixedSize(QSize(24, 24))
        self.copy_btn.clicked.connect(self.copy_all)
        toolbar_layout.addWidget(self.copy_btn)

        
        export_icon = QIcon(os.path.join(icons_path, "output_export.svg"))
        self.export_btn = QPushButton()
        self.export_btn.setIcon(export_icon)
        self.export_btn.setIconSize(QSize(16, 16))
        self.export_btn.setToolTip("Export output to file")
        self.export_btn.setFixedSize(QSize(24, 24))
        self.export_btn.clicked.connect(self.export_to_file)
        toolbar_layout.addWidget(self.export_btn)

        
        separator1 = QLabel("│")
        separator1.setStyleSheet("color: #4e4e4e; font-size: 14pt; padding: 0px 4px;")
        toolbar_layout.addWidget(separator1)

        
        scroll_icon = QIcon(os.path.join(icons_path, "output_scroll.svg"))
        self.auto_scroll_btn = QPushButton()
        self.auto_scroll_btn.setIcon(scroll_icon)
        self.auto_scroll_btn.setIconSize(QSize(16, 16))
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.setToolTip("Toggle auto-scroll (ON)")
        self.auto_scroll_btn.setFixedSize(QSize(24, 24))
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        toolbar_layout.addWidget(self.auto_scroll_btn)

        
        timestamp_icon = QIcon(os.path.join(icons_path, "output_timestamp.svg"))
        self.timestamp_btn = QPushButton()
        self.timestamp_btn.setIcon(timestamp_icon)
        self.timestamp_btn.setIconSize(QSize(16, 16))
        self.timestamp_btn.setCheckable(True)
        self.timestamp_btn.setChecked(False)
        self.timestamp_btn.setToolTip("Toggle timestamps (OFF)")
        self.timestamp_btn.setFixedSize(QSize(24, 24))
        self.timestamp_btn.clicked.connect(self.toggle_timestamps)
        toolbar_layout.addWidget(self.timestamp_btn)

        
        self.prefix_btn = QPushButton("[]")
        self.prefix_btn.setCheckable(True)
        self.prefix_btn.setChecked(False)
        self.prefix_btn.setToolTip("Toggle level tags (OFF)")
        self.prefix_btn.setFixedSize(QSize(24, 24))
        self.prefix_btn.clicked.connect(self.toggle_level_tags)
        toolbar_layout.addWidget(self.prefix_btn)

        
        toolbar_layout.addStretch()

        

        
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: #868e96; font-size: 9pt; padding-right: 4px;")
        toolbar_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["ALL", "ERROR", "WARNING", "INFO", "OUTPUT"])
        self.filter_combo.setToolTip("Filter messages by type")
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        toolbar_layout.addWidget(self.filter_combo)

        
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #868e96; font-size: 9pt; padding-left: 8px; padding-right: 4px;")
        toolbar_layout.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Find in output...")
        self.search_box.setFixedWidth(180)
        self.search_box.setToolTip("Search in output (real-time)")
        self.search_box.textChanged.connect(self.search_output)
        toolbar_layout.addWidget(self.search_box)

        return toolbar_widget

    def clear_output(self):
        """Clear all output"""
        self.text_edit.clear()
        self.all_messages = []  
        self.message_count = {"ERROR": 0, "WARNING": 0, "INFO": 0, "OUTPUT": 0}
        self.update_stats()
        self.update_status("Output cleared")

    def copy_all(self):
        """Copy all output to clipboard"""
        text = self.text_edit.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.update_status("Output copied to clipboard")

    def export_to_file(self):
        """Export output to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Output",
            f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                self.update_status(f"Output exported to {file_path}")
            except Exception as e:
                self.append_output(f"Failed to export: {str(e)}", "ERROR")

    def toggle_auto_scroll(self, checked):
        """Toggle auto-scroll feature"""
        self.auto_scroll = checked
        self.auto_scroll_btn.setToolTip(f"Toggle auto-scroll ({'ON' if checked else 'OFF'})")

    def toggle_timestamps(self, checked):
        """Toggle timestamp display"""
        self.show_timestamps = checked
        self.timestamp_btn.setToolTip(f"Toggle timestamps ({'ON' if checked else 'OFF'})")
        
        self.render_messages()

    def toggle_level_tags(self, checked):
        """Toggle level tag display (e.g., [INFO])"""
        self.show_level_tags = checked
        self.prefix_btn.setToolTip(f"Toggle level tags ({'ON' if checked else 'OFF'})")
        self.render_messages()

    def apply_filter(self, filter_level):
        """Apply message filter - re-render messages based on selected level"""
        self.filter_level = filter_level
        self.render_messages()

        
        if filter_level == "ALL":
            self.update_status(f"Filter: ALL ({len(self.all_messages)} messages)")
        else:
            filtered_count = sum(1 for msg in self.all_messages if msg["level"] == filter_level)
            self.update_status(f"Filter: {filter_level} ({filtered_count} messages)")

    def render_messages(self):
        """Re-render all messages based on current filter"""
        
        scrollbar = self.text_edit.verticalScrollBar()
        old_value = scrollbar.value()
        was_at_bottom = old_value >= scrollbar.maximum() - 10

        
        self.text_edit.clear()

        
        for msg_data in self.all_messages:
            
            if self.filter_level != "ALL" and msg_data["level"] != self.filter_level:
                continue

            
            self._render_single_message(msg_data)

        
        if self.auto_scroll or was_at_bottom:
            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()
        else:
            scrollbar.setValue(old_value)

    def _render_single_message(self, msg_data):
        """Render a single message to the text edit"""
        level = msg_data["level"]
        message = msg_data["message"]
        timestamp = msg_data["timestamp"]

        
        if self.show_timestamps and timestamp:
            self.text_edit.append_with_format(timestamp, self.text_edit.color_scheme["TIMESTAMP"])

        
        if self.show_level_tags:
            level_badge = f"[{level}] "
            color = self.text_edit.color_scheme.get(level, self.text_edit.color_scheme["OUTPUT"])
            self.text_edit.append_with_format(level_badge, color, bold=True)

        
        self.append_colorized_message(message, level)

        
        self.text_edit.append_with_format("\n", "#ffffff")

    def search_output(self, text):
        """Search in output"""
        if not text:
            
            cursor = self.text_edit.textCursor()
            cursor.clearSelection()
            self.text_edit.setTextCursor(cursor)
            return

        
        self.text_edit.moveCursor(QTextCursor.Start)
        format = QTextCharFormat()
        format.setBackground(QColor("#3d5a80"))

        
        while self.text_edit.find(text):
            cursor = self.text_edit.textCursor()
            cursor.mergeCharFormat(format)

    def update_status(self, message):
        """Update status label"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(f"[{timestamp}] {message}")

    def update_stats(self):
        """Update statistics label"""
        self.stats_label.setText(
            f"Errors: {self.message_count['ERROR']} | "
            f"Warnings: {self.message_count['WARNING']} | "
            f"Info: {self.message_count['INFO']} | "
            f"Output: {self.message_count['OUTPUT']}"
        )

    def append_output(self, message, level="OUTPUT"):
        """
        Append output with color-coded level

        Args:
            message (str): Message to append
            level (str): Message level - ERROR, WARNING, INFO, SUCCESS, DEBUG, OUTPUT
        """
        if not message.strip():
            return

        
        if level in self.message_count:
            self.message_count[level] += 1
            self.update_stats()

        
        timestamp = ""
        if self.show_timestamps:
            timestamp = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "

        
        msg_data = {
            "level": level,
            "message": message,
            "timestamp": timestamp
        }
        self.all_messages.append(msg_data)

        
        if self.filter_level == "ALL" or self.filter_level == level:
            self._render_single_message(msg_data)

            
            if self.auto_scroll:
                self.text_edit.moveCursor(QTextCursor.End)
                self.text_edit.ensureCursorVisible()

    def append_colorized_message(self, message, level):
        """Colorize message based on content (stack traces, file paths, etc.)"""
        color = self.text_edit.color_scheme.get(level, self.text_edit.color_scheme["OUTPUT"])

        
        if level == "ERROR" and ("Traceback" in message or "File " in message):
            self.append_stack_trace(message)
        else:
            
            self.text_edit.append_with_format(message, color)

    def append_stack_trace(self, trace):
        """Parse and colorize Python stack trace"""
        lines = trace.split('\n')

        for line in lines:
            if not line.strip():
                continue

            
            if line.strip().startswith('File '):
                match = re.match(r'(\s*File ")([^"]+)(",\s+line\s+)(\d+)(,\s+in\s+)(.+)', line)
                if match:
                    self.text_edit.append_with_format(match.group(1), "#868e96")  
                    self.text_edit.append_with_format(match.group(2), "#4a9eff", bold=True)  
                    self.text_edit.append_with_format(match.group(3), "#868e96")  
                    self.text_edit.append_with_format(match.group(4), "#ffcc00", bold=True)  
                    self.text_edit.append_with_format(match.group(5), "#868e96")  
                    self.text_edit.append_with_format(match.group(6), "#51cf66")  
                    self.text_edit.append_with_format("\n", "#ffffff")
                else:
                    self.text_edit.append_with_format(line + "\n", "#ff6b6b")

            
            elif "Traceback" in line:
                self.text_edit.append_with_format(line + "\n", "#ff6b6b", bold=True)

            
            elif ':' in line and any(exc in line for exc in ['Error', 'Exception', 'Warning']):
                parts = line.split(':', 1)
                self.text_edit.append_with_format(parts[0], "#ff6b6b", bold=True)  
                if len(parts) > 1:
                    self.text_edit.append_with_format(': ' + parts[1] + "\n", "#ff6b6b")

            
            else:
                self.text_edit.append_with_format("    " + line.strip() + "\n", "#e0e0e0")

    def append_error_output(self, message):
        """Compatibility method - append error message"""
        self.append_output(message, "ERROR")

    def append_info_output(self, message):
        """Compatibility method - append info message"""
        self.append_output(message, "INFO")

    def append_warning_output(self, message):
        """Append warning message"""
        self.append_output(message, "WARNING")

    def append_success_output(self, message):
        """Append success message"""
        self.append_output(message, "SUCCESS")

    
    def clear(self):
        """Compatibility method - clear output"""
        self.clear_output()

    def append(self, message):
        """Compatibility method - append message as HTML"""
        
        import re
        clean_text = re.sub('<[^<]+?>', '', message)

        
        if 'color: grey' in message.lower() or 'color: gray' in message.lower():
            level = "INFO"
        elif 'color: red' in message.lower() or '#fe8c86' in message.lower():
            level = "ERROR"
        else:
            level = "OUTPUT"

        self.append_output(clean_text, level)

    def setReadOnly(self, readonly):
        """Compatibility method - text_edit is already read-only"""
        self.text_edit.setReadOnly(readonly)

    def setFont(self, font):
        """Compatibility method - set font on text_edit"""
        self.text_edit.setFont(font)
