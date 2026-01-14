import os
import re
import zipfile
import importlib
import editor.core
importlib.reload(editor.core)
from PySide2.QtGui import QFont, QColor, QPainter, QTextFormat
from PySide2.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QHBoxLayout, QFileDialog,\
    QCheckBox, QPlainTextEdit, QTextEdit
from PySide2.QtCore import Qt, QSize, QRect, QRegExp
from PySide2.QtWidgets import QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
from PySide2.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextCursor


class LineNumberedTextEdit(QPlainTextEdit):
    """
       A custom text editor widget with line numbers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def lineNumberAreaWidth(self):
        """
        Calculate the required width for the line number area.
        """
        digits = 1
        max_number = max(1, self.blockCount())
        while max_number >= 10:
            max_number //= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        """
        Update the width of the line number area based on the current content.
        """
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        """
        Update the line number area during scrolling or when the content changes.
        """
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        """
        Adjust the geometry of the line number area when the widget is resized.
        """
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        """
        Highlight the currently active line in the editor.
        """
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(75, 75, 74, 150)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        """
        Paint the line numbers in the line number area.
        """
        painter = QPainter(self.lineNumberArea)
        
        painter.fillRect(event.rect(), QColor(40, 40, 40))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(0, top, self.lineNumberArea.width() - 3, self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

class LineNumberArea(QFrame):
    """
    A widget that displays line numbers for the associated editor.
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class SyntaxHighlighter(QSyntaxHighlighter):
    """
    A syntax highlighter for coloring specific keywords in the text.
    """
    def __init__(self, document):
        super().__init__(document)
        self.highlightingRules = []

        
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#ff79c6"))  
        keywordFormat.setFontWeight(QFont.Bold)

        nukeFormat = QTextCharFormat()
        nukeFormat.setForeground(QColor("#ffb86c"))  

        menuFormat = QTextCharFormat()
        menuFormat.setForeground(QColor("#ffb86c"))  

        commandFormat = QTextCharFormat()
        commandFormat.setForeground(QColor("#bbbbbb"))  
        commandFormat.setFontWeight(QFont.Bold)

        
        keywords = ["import", "nuke", "command", "menu", "addCommand"]

        for word in keywords:
            if word == "nuke":
                pattern = QRegExp(r'\bnuke\b')
                self.highlightingRules.append((pattern, nukeFormat))
            elif word == "menu":
                pattern = QRegExp(r'\bmenu\b')
                self.highlightingRules.append((pattern, menuFormat))
            elif word in ["addCommand", "command"]:
                pattern = QRegExp(r'\b' + word + r'\b')
                self.highlightingRules.append((pattern, commandFormat))
            else:
                pattern = QRegExp(r'\b' + word + r'\b')
                self.highlightingRules.append((pattern, keywordFormat))

    def highlightBlock(self, text):
        """
        Apply syntax highlighting to the given block of text.
        """
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

class NewNukeProjectDialog(QDialog):
    """
    A dialog for creating a new Nuke project with features such as input validation, syntax highlighting,
    and optional backups of the `.nuke` environment.
    """
    def __init__(self, editp_window, parent=None, jet_fonts=None):
        """
        Initialize the dialog for creating a new Nuke project.
        """
        super().__init__(parent)
        self.editor_window = editp_window  
        self.allowed_pattern = r'^[a-zA-Z0-9_ ]+$'  
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)  
        self.setAttribute(Qt.WA_TranslucentBackground)  
        self.setModal(True)
        dialog_size = QSize(500, 500)
        self.resize(dialog_size)

        
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(40)
        shadow_effect.setOffset(0, 12)
        shadow_effect.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow_effect)

        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        
        background_frame = QFrame(self)
        background_frame.setStyleSheet(
            """QFrame {background-color: rgb(50, 50, 50);border: 1px solid rgba(255, 255, 255, 0.1);border-radius: 9px;}""")
        self.inner_layout = QVBoxLayout(background_frame)
        self.inner_layout.setContentsMargins(30, 30, 30, 20)
        self.main_layout.addWidget(background_frame)

        
        title_label = QLabel("Create New Nuke Project", background_frame)
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setStyleSheet(
            """color: #CFCFCF; font-size: 18px; font-weight: bold; font-family: 'Myriad';border: none;background-color: transparent;""")
        self.inner_layout.addWidget(title_label)
        self.inner_layout.addSpacing(35)

        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: rgba(255, 255, 255, 0.2);")
        self.inner_layout.addWidget(line)

        
        self.project_name_input = QLineEdit()
        self.project_name_input.textChanged.connect(self.update_init_py_text)
        self.project_name_input.setPlaceholderText("Enter Project Name")
        self.project_name_input.setMaxLength(25)
        self.project_name_input.setStyleSheet(
            """QLineEdit {background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0; padding: 10px; padding-right: 40px; border: 1px solid #5A5A5A; border-radius: 8px;}""")
        self.inner_layout.addWidget(self.project_name_input)

        
        self.character_count_label = QLabel("0/25")
        self.character_count_label.setStyleSheet("color: #CFCFCF; font-size: 12px; border: 0px;")
        char_layout = QHBoxLayout()
        char_layout.addWidget(self.project_name_input)
        char_layout.addWidget(self.character_count_label)
        self.inner_layout.addLayout(char_layout)

        
        self.project_name_input.textChanged.connect(self.validate_project_name)

        
        self.project_dir_input = QLineEdit()
        self.project_dir_input.setPlaceholderText("Select Project Directory")
        self.project_dir_input.setText(self.get_default_nuke_directory())
        self.project_dir_input.setStyleSheet(
            """QLineEdit {background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0; padding: 10px; border: 1px solid #5A5A5A; border-radius: 8px;}""")
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.project_dir_input)
        browse_button = QPushButton("Browse")
        browse_button.setFixedHeight(37)
        browse_button.setStyleSheet(
            """QPushButton {background-color: #4E4E4E; color: #FFFFFF; border-radius: 8px; padding: 6px 12px; font-size: 12px;} QPushButton:hover {background-color: #6E6E6E;}""")
        browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(browse_button)
        self.inner_layout.addLayout(dir_layout)

        
        def add_separator():
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setStyleSheet("color: rgba(255, 255, 255, 0.2);")
            self.inner_layout.addWidget(line)

        add_separator()
        
        self.create_menu_py_checkbox = QCheckBox("Create Menu.py")
        self.create_menu_py_checkbox.setStyleSheet("color: #CFCFCF;")
        self.create_menu_py_checkbox.stateChanged.connect(self.toggle_menu_py_textbox)
        self.inner_layout.addWidget(self.create_menu_py_checkbox)

        self.menu_py_textbox = LineNumberedTextEdit()
        self.menu_py_textbox.setStyleSheet(
            f"""background-color: rgba(255, 255, 255, 0.08);color: #CFCFCF;font-size: 12px;""")
        self.menu_py_textbox.setFont(QFont("Consolas"))
        self.inner_layout.addWidget(self.menu_py_textbox)
        self.menu_py_textbox.hide()  

        
        self.highlighter_menu = SyntaxHighlighter(self.menu_py_textbox.document())  
        
        self.create_init_py_checkbox = QCheckBox("Create init.py")
        self.create_init_py_checkbox.setStyleSheet("color: #CFCFCF;")
        self.create_init_py_checkbox.stateChanged.connect(self.toggle_init_py_textbox)
        self.inner_layout.addWidget(self.create_init_py_checkbox)

        
        self.init_py_textbox = LineNumberedTextEdit()
        self.init_py_textbox.setFont(QFont("Consolas"))
        self.init_py_textbox.setStyleSheet(
            f"""background-color: rgba(255, 255, 255, 0.08);color: #CFCFCF;font-size: 12px;""")
        self.inner_layout.addWidget(self.init_py_textbox)
        self.init_py_textbox.hide()  
        
        self.highlighter_init = SyntaxHighlighter(self.init_py_textbox.document())  


        add_separator()

        
        self.create_backup_folder_checkbox = QCheckBox("Make backup .nuke folder (be safe)")
        self.create_backup_folder_checkbox.setStyleSheet("color: #CFCFCF;")
        self.create_backup_folder_checkbox.stateChanged.connect(self.toggle_backup_location)
        self.inner_layout.addWidget(self.create_backup_folder_checkbox)

        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setPlaceholderText("Select Backup Location")
        self.backup_dir_input.setStyleSheet(
            """QLineEdit {background-color: rgba(255, 255, 255, 0.08);color: #E0E0E0;padding: 10px;border: 1px solid #5A5A5A;border-radius: 8px;}""")


        
        backup_dir_layout = QHBoxLayout()
        backup_dir_layout.addWidget(self.backup_dir_input)
        self.browse_backup_button = QPushButton("Backup Location")
        self.browse_backup_button.setFixedHeight(37)
        self.browse_backup_button.setFixedWidth(150)
        self.browse_backup_button.setStyleSheet(
            """QPushButton {background-color: #4E4E4E;color: #FFFFFF;border-radius: 8px;padding: 6px 12px;font-size: 12px;} QPushButton:hover {background-color: #6E6E6E;}""")
        self.browse_backup_button.clicked.connect(self.browse_backup_directory)
        backup_dir_layout.addWidget(self.browse_backup_button)
        self.inner_layout.addLayout(backup_dir_layout)

        
        self.backup_explanation = QLabel(
            "If you have an existing .nuke environment, backing it up \nwill make your work easier.")
        self.backup_explanation.setStyleSheet("color: #CFCFCF; font-size: 12px; stroke: none; border: none;")
        self.inner_layout.addWidget(self.backup_explanation)
        self.backup_explanation.hide()
        self.backup_dir_input.hide()
        self.browse_backup_button.hide()
        vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.inner_layout.addItem(vertical_spacer)
        add_separator()

        
        warning_layout = QHBoxLayout()
        warning_icon = QLabel("ℹ ")
        warning_icon.setStyleSheet(" font-size: 40px; font-weight: bold; border: none;")
        warning_layout.addWidget(warning_icon)

        warning_message = QLabel(
            "For creating projects outside '.nuke', please use 'New Project > Custom Project'. \n"
            "We disclaim liability for any damage to files in the selected directory. \n"
            "To avoid disrupting the '.nuke' directory, please consider creating a backup.\n"
            "Failure to select this option may result in data loss, for which we accept no liability.")
        warning_message.setStyleSheet(
            "color: #FFFFFF; background-color: rgba(255, 0, 0, 0.1); padding: 5px; border-radius: 5px; font-size: 11px;")
        warning_layout.addWidget(warning_message)
        self.inner_layout.addLayout(warning_layout)

        
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.setFixedSize(80, 30)
        ok_button.setStyleSheet(
            """QPushButton {background-color: #808080;color: #FFFFFF;border-radius: 10px;font-size: 14px;padding: 5px;} QPushButton:hover {background-color: #A9A9A9;}""")
        button_layout.addWidget(ok_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedSize(80, 30)
        cancel_button.setStyleSheet(
            """QPushButton {background-color: #808080;color: #FFFFFF;border-radius: 10px;font-size: 14px;padding: 5px;} QPushButton:hover {background-color: #A9A9A9;}""")
        button_layout.addWidget(cancel_button)

        self.inner_layout.addSpacing(20)
        self.inner_layout.addLayout(button_layout)

        ok_button.clicked.connect(self.create_project)
        cancel_button.clicked.connect(self.reject)

    def validate_project_name(self):
        """
        Validate the project name input to ensure it follows Python variable naming conventions
        and has a maximum length of 25 characters.
        """
        text = self.project_name_input.text()

        
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", text):
            text = re.sub(r"[^A-Za-z0-9_]", "", text)
            text = re.sub(r"^[^A-Za-z_]+", "", text)
            self.project_name_input.setText(text)

        
        if len(text) > 25:
            text = text[:25]
            self.project_name_input.setText(text)

        
        self.character_count_label.setText(f"{len(text)}/25")

    def update_init_py_text(self):
        """
        Update the content of `init.py` in the text box with the current project name.
        Highlights the project name in orange.
        """
        project_name = self.project_name_input.text() or "your_plugin_path"
        formatted_text = f"import nuke\nimport os\nnuke.pluginAddPath('{project_name}')"

        self.init_py_textbox.clear()
        cursor = QTextCursor(self.init_py_textbox.document())
        cursor.insertText(formatted_text)

        
        format = QTextCharFormat()
        format.setForeground(QColor("#ffb86c"))  
        self.highlight_text(cursor, project_name, format)

    def highlight_text(self, cursor, text, format):
        """
        Highlight specific text in the document with the given format.
        """
        cursor.beginEditBlock()
        document = self.init_py_textbox.document()
        pattern = QRegExp(rf"\b{text}\b")

        pos = 0
        index = pattern.indexIn(document.toPlainText(), pos)

        while index >= 0:
            cursor.setPosition(index)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(text))
            cursor.mergeCharFormat(format)
            pos = index + len(text)
            index = pattern.indexIn(document.toPlainText(), pos)

        cursor.endEditBlock()

    def toggle_menu_py_textbox(self, state):
        """
        Toggles the visibility of the `menu.py` editor textbox.
        Displays a pre-filled template if checked.
        """
        if state == Qt.Checked:
            self.menu_py_textbox.show()
            self.menu_py_textbox.setPlainText("import nuke\ntoolbar = nuke.menu(\'Nodes\')\ni = toolbar.addMenu('Studio')")
        else:
            self.menu_py_textbox.hide()
            self.menu_py_textbox.clear()

    def toggle_init_py_textbox(self, state):
        """
        Toggles the visibility of the `init.py` editor textbox.
        Displays a pre-filled template if checked.
        """
        if state == Qt.Checked:
            self.init_py_textbox.show()
            self.init_py_textbox.setPlainText("import nuke\nimport os\nnuke.pluginAddPath('your_plugin_path')")
        else:
            self.init_py_textbox.hide()
            self.init_py_textbox.clear()

    def toggle_backup_location(self, state):
        """
        Toggles the visibility of the backup location input fields and explanation.
        """
        if state == Qt.Checked:
            self.backup_dir_input.show()
            self.browse_backup_button.show()
            self.backup_explanation.show()  
            self.backup_dir_input.setText("")
        else:
            self.backup_dir_input.hide()
            self.browse_backup_button.hide()
            self.backup_explanation.hide()  

    def get_default_nuke_directory(self):
        """
        Returns the default `.nuke` directory path based on the operating system.
        """
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, ".nuke")

    def browse_directory(self):
        """
        Opens a file dialog for selecting the project directory and sets the input field.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if directory:
            self.project_dir_input.setText(directory)

    def browse_backup_directory(self):
        """
        Opens a file dialog for selecting the backup directory and sets the input field.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if directory:
            self.backup_dir_input.setText(directory)

    def create_project(self):
        """
        Creates the new Nuke project based on user input.
        Validates the project name and directory, creates directories, and optionally
        backs up the `.nuke` environment.
        """
        import datetime
        from PySide2.QtWidgets import QProgressDialog, QMessageBox

        project_name = self.project_name_input.text().strip()
        project_dir = self.project_dir_input.text().strip()

        
        if not project_dir or not os.path.exists(project_dir):
            self.project_dir_input.setStyleSheet(
                """QLineEdit {background-color: rgba(255, 150, 150, 0.08); color: #E0E0E0;
                padding: 10px; border: 1px solid red; border-radius: 8px;}"""
            )
            self.project_dir_input.setPlaceholderText("Wrong 'Directory' or 'Path'")
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid project directory.")
            return
        else:
            self.project_dir_input.setStyleSheet(
                """QLineEdit {background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0;
                padding: 10px; border: 1px solid #5A5A5A; border-radius: 8px;}"""
            )

        
        if not project_name:
            self.project_name_input.setStyleSheet(
                """QLineEdit {background-color: rgba(255, 150, 150, 0.08); color: #E0E0E0;
                padding: 10px; padding-right: 40px; border: 1px solid red; border-radius: 8px;}"""
            )
            QMessageBox.warning(self, "Invalid Project Name", "Please enter a valid project name.")
            return
        else:
            self.project_name_input.setStyleSheet(
                """QLineEdit {background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0;
                padding: 10px; padding-right: 40px; border: 1px solid #5A5A5A; border-radius: 8px;}"""
            )

        try:
            
            project_last_path = os.path.join(project_dir, project_name)
            os.makedirs(project_last_path, exist_ok=True)

            
            current_date = datetime.datetime.now().strftime("%Y_%m_%d")
            main_init_file = os.path.join(project_last_path, "__init__.py")
            main_init_content = (
                "# This directory is part of the main script. //With opened Python Code Editor.\n"
                f"# Created on: {current_date}\n"
                "# from love import StopWars\n"
            )
            editor.core.write_python_file(main_init_file, main_init_content, mode="w", encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Creating Project",
                f"Failed to create project directory:\n{str(e)}"
            )
            return

        
        if self.create_backup_folder_checkbox.isChecked():
            backup_dir = self.backup_dir_input.text().strip()
            if not backup_dir or not os.path.exists(backup_dir):
                self.backup_dir_input.setStyleSheet(
                    """QLineEdit {background-color: rgba(255, 150, 150, 0.08); color: #E0E0E0;
                    padding: 10px; border: 1px solid red; border-radius: 8px;}"""
                )
                self.backup_dir_input.setPlaceholderText("Invalid backup directory")
                QMessageBox.warning(self, "Invalid Backup Directory", "Please select a valid backup directory.")
                return
            else:
                self.backup_dir_input.setStyleSheet(
                    """QLineEdit {background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0;
                    padding: 10px; border: 1px solid #5A5A5A; border-radius: 8px;}"""
                )

            try:
                
                nuke_dir = self.get_default_nuke_directory()
                backup_zip = os.path.join(backup_dir, f"doth_nuke_backup_{current_date}.zip")
                file_count = sum(len(files) for _, _, files in os.walk(nuke_dir))
                progress = QProgressDialog("Backing up files...", "Cancel", 0, file_count, self)
                progress.setWindowTitle("Backup Progress")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                current_progress = 0

                with zipfile.ZipFile(backup_zip, 'w') as zf:
                    for root, dirs, files in os.walk(nuke_dir):
                        for file in files:
                            if progress.wasCanceled():
                                QMessageBox.information(self, "Backup Canceled", "Backup operation was canceled by user.")
                                return
                            zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), nuke_dir))
                            current_progress += 1
                            progress.setValue(current_progress)
                progress.close()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Backup Error",
                    f"Failed to create backup:\n{str(e)}"
                )
                return

        try:
            
            if self.create_menu_py_checkbox.isChecked():
                menu_py_content = self.menu_py_textbox.toPlainText()
                menu_py_path = os.path.join(project_dir, "menu.py")
                editor.core.write_python_file(menu_py_path, menu_py_content, mode="w", encoding="utf-8")

            
            if self.create_init_py_checkbox.isChecked():
                init_py_content = self.init_py_textbox.toPlainText()
                init_py_path = os.path.join(project_dir, "init.py")
                editor.core.write_python_file(init_py_path, init_py_content, mode="w", encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(
                self,
                "File Creation Error",
                f"Failed to create init.py or menu.py:\n{str(e)}"
            )
            return

        
        QMessageBox.information(
            self,
            "Project Created",
            f"Project '{project_name}' has been created successfully!\n\n"
            f"Location: {project_last_path}"
        )

        
        if self.editor_window and hasattr(self.editor_window, 'open_file'):
            try:
                self.editor_window.open_file(main_init_file)
            except Exception as e:
                pass

        
        self.accept()
