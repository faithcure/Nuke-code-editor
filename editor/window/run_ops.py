import platform
import socket
import traceback
from datetime import datetime
from PySide2.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide2.QtWidgets import QPlainTextEdit
from PySide2.QtCore import QThread
import nuke
from editor.output import PythonExecutionWorker, execute_python_code, execute_nuke_code


class RunOpsMixin:
    def _clear_python_worker(self):
        self._python_execution_thread = None
        self._python_execution_worker = None

    def stop_code(self):
        worker = getattr(self, "_python_execution_worker", None)
        thread = getattr(self, "_python_execution_thread", None)
        if worker is not None:
            worker.stop()
        if thread is not None and thread.isRunning():
            thread.quit()

    def _start_python_code_async(self, code):
        self.stop_code()

        thread = QThread(self)
        worker = PythonExecutionWorker(code)
        worker.moveToThread(thread)

        def _append(message, level):
            try:
                self.output_widget.append_output(message, level)
            except Exception:
                pass

        worker.output.connect(_append)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_python_worker)
        thread.started.connect(worker.run)

        self._python_execution_thread = thread
        self._python_execution_worker = worker
        thread.start()

    def clear_output(self):
        """
        Clears all content from the output panel.

        This resets the display area of the output widget, removing any text or messages.
        """
        self.output_widget.clear_output()

    def run_code(self):
        """
        Executes the code in the current active tab and displays the results or errors in the output panel.

        - Clears the output panel before execution.
        - Displays environment info like Python version, Nuke version, computer name, and timestamp.
        - Executes the selected or full content of the active editor tab.
        - Handles both Python and Nuke-specific code execution.
        - Outputs success or error messages back to the output panel.
        """
        # Clear the Output Widget
        self.output_widget.clear_output()

        python_version = platform.python_version()  # Get Python version
        nuke_version = nuke.env['NukeVersionString']  # Get Nuke version
        computer_name = socket.gethostname()  # Get the computer name

        # Get the current date and time
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        target_tabs = self._current_tab_widget()

        # Get the name of the active tab
        active_tab_name = target_tabs.tabText(target_tabs.currentIndex())

        # Display system and environment info in the output
        info_message = (
            f'Python: {python_version} | Nuke: {nuke_version} | '
            f'File: {active_tab_name} | Computer: {computer_name} | {formatted_time}'
        )
        self.output_widget.append_output(info_message, "INFO")

        # Execute the code from the active editor
        current_editor = target_tabs.currentWidget()

        if isinstance(current_editor, QPlainTextEdit):
            cursor = current_editor.textCursor()
            code = cursor.selectedText().strip() or current_editor.toPlainText()

            if not code.strip():
                self.output_widget.append_output("No code to execute", "WARNING")
                return

            try:
                if "nuke." in code or "nukescripts." in code:
                    # Execute Nuke-specific code
                    self.output_widget.append_output("Executing Nuke code...", "INFO")
                    execute_nuke_code(code, self.output_widget)
                    self.output_widget.append_output("Code executed successfully", "SUCCESS")
                else:
                    # Execute standard Python code
                    self.output_widget.append_output("Executing Python code...", "INFO")
                    self._start_python_code_async(code)

            except Exception:
                # Handle and display errors
                error_message = traceback.format_exc()
                self.output_widget.append_output(error_message, "ERROR")

    def run_selected_code(self):
        """Execute only the selected code in the active editor."""
        current_editor = self._current_tab_widget().currentWidget()
        if not isinstance(current_editor, QPlainTextEdit):
            self.output_widget.append_output("No editable code is active", "WARNING")
            return

        cursor = current_editor.textCursor()
        if not cursor.hasSelection():
            self.output_widget.append_output("No selection to execute", "WARNING")
            return

        self.output_widget.clear_output()
        code = cursor.selectedText().strip()
        if not code:
            self.output_widget.append_output("No selection to execute", "WARNING")
            return

        try:
            if "nuke." in code or "nukescripts." in code:
                self.output_widget.append_output("Executing Nuke code...", "INFO")
                execute_nuke_code(code, self.output_widget)
                self.output_widget.append_output("Code executed successfully", "SUCCESS")
            else:
                self.output_widget.append_output("Executing Python code...", "INFO")
                self._start_python_code_async(code)
        except Exception:
            error_message = traceback.format_exc()
            self.output_widget.append_output(error_message, "ERROR")

    def run_all_code(self):
        """Execute all code in the active editor."""
        current_editor = self._current_tab_widget().currentWidget()
        if not isinstance(current_editor, QPlainTextEdit):
            self.output_widget.append_output("No editable code is active", "WARNING")
            return

        self.output_widget.clear_output()
        code = current_editor.toPlainText().strip()
        if not code:
            self.output_widget.append_output("No code to execute", "WARNING")
            return

        try:
            if "nuke." in code or "nukescripts." in code:
                self.output_widget.append_output("Executing Nuke code...", "INFO")
                execute_nuke_code(code, self.output_widget)
                self.output_widget.append_output("Code executed successfully", "SUCCESS")
            else:
                self.output_widget.append_output("Executing Python code...", "INFO")
                self._start_python_code_async(code)
        except Exception:
            error_message = traceback.format_exc()
            self.output_widget.append_output(error_message, "ERROR")

    def find_and_highlight(self, search_term):
        """
        Highlights occurrences of a given search term in the active code editor.

        Args:
            search_term (str): The term to search and highlight in the editor.

        Behavior:
            - Searches for all occurrences of the `search_term` in the current editor.
            - Applies a yellow background to highlight matching terms.
            - If no editor is open, displays an error message in the output widget.
        """
        current_editor = self._current_tab_widget().currentWidget()
        if current_editor is None:
            self.output_widget.append_error_output("Please open an active tab for coding...")
            return

        cursor = current_editor.textCursor()  # Get the editor's cursor
        document = current_editor.document()  # Get the text document

        # Clear existing highlights
        current_editor.setExtraSelections([])

        # Store results for highlighting
        extra_selections = []

        # Begin bulk changes to the cursor
        cursor.beginEditBlock()

        # Move cursor to the start of the document
        cursor.movePosition(QTextCursor.Start)

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))  # Set highlight color to yellow

        # Search for all matches of the term
        while not cursor.isNull() and not cursor.atEnd():
            cursor = document.find(search_term, cursor)
            if not cursor.isNull():
                # Create a selection for the found term
                selection = QPlainTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format = highlight_format
                extra_selections.append(selection)

        # End bulk changes
        cursor.endEditBlock()

        # Apply highlights to the editor
        current_editor.setExtraSelections(extra_selections)
