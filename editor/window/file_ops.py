import os
import re
import sys
import subprocess
from PySide2.QtWidgets import QApplication, QFileDialog, QMessageBox, QInputDialog
from editor.code_editor import CodeEditor
from editor.core import write_python_file


class FileOpsMixin:
    def autosave_all_modified_files(self):
        """
        Auto-save all modified editors without prompting.

        Rules:
        - If a tab has an existing path, save there.
        - If it's an untitled tab and a project is open, save into the project.
        - Otherwise, skip (never opens dialogs).
        """
        if not hasattr(self, "_all_tab_widgets"):
            return 0

        saved_count = 0
        for tab_widget in self._all_tab_widgets():
            try:
                for index in range(tab_widget.count()):
                    editor = tab_widget.widget(index)
                    if not isinstance(editor, CodeEditor):
                        continue
                    if not editor.document().isModified():
                        continue
                    if self._autosave_editor_tab(tab_widget, index, editor):
                        saved_count += 1
            except Exception:
                continue
        return saved_count

    def _autosave_editor_tab(self, tab_widget, index, editor):
        tab_title = tab_widget.tabText(index).replace("*", "").strip()
        existing_file_path = tab_widget.tabToolTip(index)

        if existing_file_path:
            try:
                file_path = os.path.normpath(existing_file_path)
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(editor.toPlainText())
                editor.document().setModified(False)
                tab_widget.setTabText(index, os.path.basename(file_path))
                if hasattr(self, "statusBar"):
                    self.statusBar().showMessage(f"Auto-saved: {os.path.basename(file_path)}", 1500)
                return True
            except Exception:
                return False

        if tab_title.startswith("untitled") and getattr(self, "project_dir", None):
            base_name = "untitled"
            file_extension = ".py"
            counter = 1

            while True:
                if counter == 1:
                    file_name = f"{base_name}{file_extension}"
                else:
                    file_name = f"{base_name}_{counter}{file_extension}"
                file_path = os.path.join(self.project_dir, file_name)
                if not os.path.exists(file_path):
                    break
                counter += 1

            try:
                write_python_file(file_path, editor.toPlainText(), mode="w", encoding="utf-8")
                editor.document().setModified(False)
                tab_widget.setTabText(index, file_name)
                tab_widget.setTabToolTip(index, file_path)
                if hasattr(self, "update_header_tree"):
                    self.update_header_tree()
                if hasattr(self, "refresh_workspace"):
                    self.refresh_workspace()
                if hasattr(self, "statusBar"):
                    self.statusBar().showMessage(f"Auto-saved to project: {file_name}", 1500)
                return True
            except Exception:
                return False

        return False

    def open_file(self):
        """Dosya açma işlemi."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "Python Dosyaları (*.py);;Tüm Dosyalar (*)")

        if file_name:
            normalized_path = os.path.normpath(os.path.abspath(file_name))
            # Öncelikle aynı dosya yoluna sahip bir sekmenin açık olup olmadığını kontrol edelim
            for tab_widget in self._all_tab_widgets():
                for index in range(tab_widget.count()):
                    existing_editor = tab_widget.widget(index)
                    if not isinstance(existing_editor, CodeEditor):
                        continue
                    existing_path = getattr(existing_editor, '_file_path', None) or tab_widget.tabToolTip(index)
                    if existing_path and os.path.normpath(os.path.abspath(existing_path)) == normalized_path:
                        # Eğer aynı dosya açıksa, mevcut sekmeyi öne getir
                        tab_widget.setCurrentWidget(existing_editor)
                        return  # Yeni bir sekme açılmasını engelle ve çık

            # Aynı dosya açık değilse yeni bir sekme aç
            self.add_new_tab(file_name)
            print("add_new_tab 1625")

    def save_file(self):
        """Smart save: automatically save to project folder if project is open."""
        target_tabs = self._current_tab_widget()
        current_editor = target_tabs.currentWidget()
        if not current_editor or not isinstance(current_editor, CodeEditor):
            return False

        index = target_tabs.indexOf(current_editor)
        if index == -1:
            return False

        tab_title = target_tabs.tabText(index).replace("*", "").strip()

        # Get existing file path from tooltip
        existing_file_path = target_tabs.tabToolTip(index)

        # Scenario 1: File already has a path (previously saved)
        if existing_file_path and os.path.exists(existing_file_path):
            try:
                file_path = os.path.normpath(existing_file_path)
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(current_editor.toPlainText())
                current_editor.document().setModified(False)
                target_tabs.setTabText(index, os.path.basename(file_path))
                self.statusBar().showMessage(f"Saved: {os.path.basename(file_path)}", 2000)

                # Refresh workspace to show changes
                if self.project_dir:
                    self.refresh_workspace()
                return True
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
                return False

        # Scenario 2: Untitled file + Project is open → Auto-save to project
        if tab_title.startswith("untitled") and self.project_dir:
            # Generate unique filename in project directory
            base_name = "untitled"
            file_extension = ".py"
            counter = 1

            while True:
                if counter == 1:
                    file_name = f"{base_name}{file_extension}"
                else:
                    file_name = f"{base_name}_{counter}{file_extension}"

                file_path = os.path.join(self.project_dir, file_name)
                if not os.path.exists(file_path):
                    break
                counter += 1

            try:
                # Save file to project directory
                write_python_file(file_path, current_editor.toPlainText(), mode="w", encoding="utf-8")

                current_editor.document().setModified(False)

                # Update tab with new name
                target_tabs.setTabText(index, file_name)
                target_tabs.setTabToolTip(index, file_path)

                # Show success message
                self.statusBar().showMessage(f"Auto-saved to: {file_name}", 3000)

                # Update HEADER to show new filename
                self.update_header_tree()

                # Refresh workspace to show new file
                self.refresh_workspace()
                return True

            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to auto-save file:\n{str(e)}")
                return False

        # Scenario 3: No project or user wants to choose location → Save As
        return self.save_file_as()

    def save_file_as(self):
        """Dosyayı farklı bir yola kaydeder."""
        target_tabs = self._current_tab_widget()
        current_editor = target_tabs.currentWidget()
        if not current_editor or not isinstance(current_editor, CodeEditor):
            return False

        # Get current file name as default
        index = target_tabs.indexOf(current_editor)
        current_name = target_tabs.tabText(index).replace("*", "")

        # Determine default directory
        default_dir = self.project_dir if self.project_dir else os.path.expanduser("~")
        default_path = os.path.join(default_dir, current_name)

        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save File As", default_path,
            "Python Files (*.py);;All Files (*)"
        )

        if file_name:
            try:
                # Normalize path for cross-platform compatibility
                file_name = os.path.normpath(file_name)

                with open(file_name, 'w', encoding='utf-8') as file:
                    file.write(current_editor.toPlainText())

                current_editor.document().setModified(False)

                # Update tab name and tooltip
                target_tabs.setTabText(index, os.path.basename(file_name))
                target_tabs.setTabToolTip(index, file_name)

                # Add to recent files
                self.add_to_recent_files(file_name)

                # Show status message
                self.statusBar().showMessage(f"Saved as: {os.path.basename(file_name)}", 3000)

                # Update HEADER to show new filename
                self.update_header_tree()

                # Refresh workspace if file is within project directory
                if self.project_dir and file_name.startswith(self.project_dir):
                    self.refresh_workspace()
                return True

            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
                return False
        return False

    def copy_file_path(self):
        """Copy current file path to clipboard"""
        target_tabs = self._current_tab_widget()
        current_editor = target_tabs.currentWidget()
        if not current_editor or not isinstance(current_editor, CodeEditor):
            QMessageBox.information(self, "Copy Path", "No active editor tab.")
            return

        index = target_tabs.indexOf(current_editor)
        tab_title = target_tabs.tabText(index).replace("*", "").strip()

        # Get file path from tab data or construct from project_dir
        file_path = target_tabs.tabToolTip(index)

        if not file_path or tab_title.startswith("untitled"):
            QMessageBox.information(self, "Copy Path", "No file path available for unsaved file.")
            return

        # Normalize path for cross-platform compatibility
        file_path = os.path.normpath(file_path)
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
        self.statusBar().showMessage(f"Copied: {file_path}", 2000)

    def show_in_explorer(self):
        """Show current file in system file explorer"""
        target_tabs = self._current_tab_widget()
        current_editor = target_tabs.currentWidget()
        if not current_editor or not isinstance(current_editor, CodeEditor):
            QMessageBox.information(self, "Show in Explorer", "No active editor tab.")
            return

        index = target_tabs.indexOf(current_editor)
        tab_title = target_tabs.tabText(index).replace("*", "").strip()

        # Get file path from tab tooltip
        file_path = target_tabs.tabToolTip(index)

        if not file_path or tab_title.startswith("untitled"):
            QMessageBox.information(self, "Show in Explorer", "No file path available for unsaved file.")
            return

        # Normalize path
        file_path = os.path.normpath(file_path)

        if os.path.exists(file_path):
            directory = os.path.dirname(file_path)
            try:
                # Platform-specific file explorer opening
                if sys.platform == 'win32':
                    # Windows: open folder and select file
                    os.startfile(directory)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', '-R', file_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', directory])
            except Exception as e:
                QMessageBox.critical(self, "Show in Explorer", f"Failed to open explorer:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Show in Explorer", "File not found on disk.")

    def add_to_recent_files(self, file_path):
        """Add file to recent files list"""
        # TODO: Implement recent files tracking
        # Similar to recent_projects but for individual files
        pass

    def rename_tab(self, index, tab_widget=None):
        """Rename current tab file on disk and update workspace."""
        target_tabs = tab_widget or self._current_tab_widget()
        editor = target_tabs.widget(index)
        if not editor or not isinstance(editor, CodeEditor):
            QMessageBox.information(self, "Rename", "No active editor tab.")
            return

        old_path = target_tabs.tabToolTip(index)
        old_name = target_tabs.tabText(index).replace("*", "").strip()

        if not old_path or old_name.startswith("untitled"):
            QMessageBox.information(self, "Rename", "Please save the file before renaming.")
            return

        base_name, ext = os.path.splitext(old_name)
        if not ext:
            ext = ".py"

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Tab",
            "New file name:",
            text=base_name
        )
        if not ok:
            return

        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "Rename", "File name cannot be empty.")
            return

        new_name = new_name.replace(" ", "_")
        if not new_name.isascii():
            QMessageBox.warning(self, "Rename", "File name must be ASCII (no Turkish characters).")
            return

        if any(ch in new_name for ch in "çğıöşüÇĞİÖŞÜ"):
            QMessageBox.warning(self, "Rename", "Turkish characters are not allowed in file names.")
            return

        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', new_name):
            QMessageBox.warning(
                self,
                "Rename",
                "File name must start with a letter or '_' and contain only letters, numbers, or '_'."
            )
            return

        dir_path = os.path.dirname(os.path.normpath(old_path))
        candidate = f"{new_name}{ext}"
        new_path = os.path.join(dir_path, candidate)
        counter = 1
        while os.path.exists(new_path):
            candidate = f"{new_name}_{counter}{ext}"
            new_path = os.path.join(dir_path, candidate)
            counter += 1

        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(self, "Rename Error", f"Failed to rename file:\n{str(e)}")
            return

        target_tabs.setTabText(index, os.path.basename(new_path))
        target_tabs.setTabToolTip(index, new_path)
        editor._file_path = new_path

        self.update_header_tree()
        if self.project_dir:
            self.refresh_workspace()
