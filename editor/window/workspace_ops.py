import ast
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from PySide2.QtCore import Qt, QSize, QTimer, QStringListModel
from PySide2.QtGui import (
    QIcon,
    QPixmap,
    QPainterPath,
    QPainter,
    QFont,
    QColor,
    QBrush,
    QTextCursor,
)
from PySide2.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QMenu,
    QAction,
    QApplication,
    QInputDialog,
    QColorDialog,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QAbstractItemView,
)
from editor.core import (
    PathFromOS,
    CodeEditorSettings,
    ensure_py_extension,
    write_python_file,
    get_unique_python_path,
)
from editor.code_editor import CodeEditor


class WorkplaceTreeWidget(QTreeWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.source() is self and self.main_window and self.main_window.project_dir:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.source() is self and self.main_window and self.main_window.project_dir:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        if event.source() is not self or not self.main_window or not self.main_window.project_dir:
            event.ignore()
            return

        target_item = self.itemAt(event.pos())
        target_dir = self.main_window.project_dir
        if target_item:
            target_path = target_item.data(0, Qt.UserRole)
            if target_path:
                if os.path.isdir(target_path):
                    target_dir = target_path
                else:
                    target_dir = os.path.dirname(target_path)

        moved_any = False
        for item in self.selectedItems():
            src_path = item.data(0, Qt.UserRole)
            if not src_path or not os.path.exists(src_path):
                continue
            if os.path.isdir(src_path):
                continue
            dest_path = os.path.join(target_dir, os.path.basename(src_path))
            if os.path.normpath(src_path) == os.path.normpath(dest_path):
                continue
            if os.path.exists(dest_path):
                QMessageBox.warning(self, "Move File", f"'{os.path.basename(dest_path)}' already exists.")
                continue
            try:
                shutil.move(src_path, dest_path)
                self.main_window.update_open_tabs_path(src_path, dest_path)
                moved_any = True
            except Exception as e:
                QMessageBox.critical(self, "Move File", f"Failed to move file:\n{str(e)}")

        if moved_any:
            self.main_window.refresh_workspace()
        event.acceptProposedAction()


class WorkspaceOpsMixin:
    def populate_workplace(self, directory):
        """Workplace'ı proje dizini ile doldurur."""
        try:
            if not os.path.exists(directory):
                QMessageBox.warning(self, "Error", f"Directory does not exist: {directory}")
                return

            if not os.path.isdir(directory):
                QMessageBox.warning(self, "Error", f"Path is not a directory: {directory}")
                return

            self.workplace_tree.clear()  # Önceki dizini temizle
            root_item = QTreeWidgetItem(self.workplace_tree)
            root_item.setText(0, os.path.basename(directory))
            root_item.setData(0, Qt.UserRole, directory)
            root_item.setFlags(root_item.flags() | Qt.ItemIsDropEnabled)
            self.add_items_to_tree(root_item, directory)
            self.workplace_tree.expandAll()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to populate workplace:\n{str(e)}")
            print(f"Error populating workplace: {e}")

    def add_items_to_tree(self, parent_item, directory):
        """Add all files and folders to tree with icons and metadata"""
        try:
            items = os.listdir(directory)
        except PermissionError:
            return  # Skip directories we can't read

        # Sort: folders first, then files
        folders = []
        files = []
        for item in items:
            # Skip hidden files except important ones
            if item.startswith('.') and item not in ['.gitignore', '.env', '.nuke', '.git']:
                continue

            path = os.path.join(directory, item)
            if os.path.isdir(path):
                folders.append(item)
            else:
                files.append(item)

        folders.sort(key=str.lower)
        files.sort(key=str.lower)

        # Add folders
        for folder_name in folders:
            folder_path = os.path.join(directory, folder_name)
            folder_item = QTreeWidgetItem(parent_item)
            folder_item.setText(0, folder_name)
            folder_item.setData(0, Qt.UserRole, folder_path)
            folder_item.setFlags(folder_item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

            # Folder icon with fallback
            folder_icon = self.get_file_icon('folder')
            if folder_icon:
                folder_item.setIcon(0, folder_icon)

            # Recursively add subfolder contents
            self.add_items_to_tree(folder_item, folder_path)

        # Add files
        for file_name in files:
            file_path = os.path.join(directory, file_name)
            file_item = QTreeWidgetItem(parent_item)
            file_item.setText(0, file_name)
            file_item.setData(0, Qt.UserRole, file_path)
            file_item.setFlags(file_item.flags() | Qt.ItemIsDragEnabled)

            # Get file extension
            _, extension = os.path.splitext(file_name)

            # Get icon with fallback
            icon = self.get_file_icon(extension.lower())
            if icon:
                file_item.setIcon(0, icon)

    def get_file_icon(self, file_type):
        """Get icon for file type with fallback"""
        icons_path = PathFromOS().icons_path

        # Icon mapping with fallback
        icon_map = {
            'folder': 'folder_tree.svg',
            '.py': 'python_tab.svg',
            '.txt': 'text_icon.svg',
            '.md': 'text_icon.svg',
            '.json': 'text_icon.svg',
            '.xml': 'text_icon.svg',
            '.yml': 'text_icon.svg',
            '.yaml': 'text_icon.svg',
            '.sh': 'shell_icon.svg',
            '.bat': 'shell_icon.svg',
            '.cpp': 'cpp_icon.svg',
            '.c': 'cpp_icon.svg',
            '.h': 'cpp_icon.svg',
            '.hpp': 'cpp_icon.svg',
            '.js': 'text_icon.svg',
            '.jsx': 'text_icon.svg',
            '.ts': 'text_icon.svg',
            '.tsx': 'text_icon.svg',
            '.html': 'text_icon.svg',
            '.css': 'text_icon.svg',
            '.scss': 'text_icon.svg',
            '.png': 'image_icon.svg',
            '.jpg': 'image_icon.svg',
            '.jpeg': 'image_icon.svg',
            '.gif': 'image_icon.svg',
            '.svg': 'image_icon.svg',
            '.bmp': 'image_icon.svg',
        }

        icon_file = icon_map.get(file_type, 'text_icon.svg')
        icon_path = os.path.join(icons_path, icon_file)

        # Check if icon exists, if not use fallback
        if os.path.exists(icon_path):
            return QIcon(icon_path)

        # Try fallback to text_icon.svg
        fallback_path = os.path.join(icons_path, 'text_icon.svg')
        if os.path.exists(fallback_path):
            return QIcon(fallback_path)

        # Return empty icon if no fallback available
        return None

    def on_workplace_item_double_clicked(self, item, column):
        """Workplace'deki bir dosya çift tıklanınca dosyayı aç."""
        file_path = item.data(0, Qt.UserRole)

        if not file_path or os.path.isdir(file_path):
            return  # Skip folders

        # Check if file is already open (by comparing full paths)
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            if isinstance(widget, CodeEditor):
                # Store file path in editor widget for accurate tracking
                existing_path = getattr(widget, '_file_path', None)
                if existing_path and os.path.normpath(existing_path) == os.path.normpath(file_path):
                    # File already open, switch to it
                    self.tab_widget.setCurrentIndex(index)
                    return

        # Open file in new tab
        self.add_new_tab(file_path)

    def context_menu(self, position):
        """Enhanced context menu with new features"""
        menu = QMenu()
        if self.workplace_tree.topLevelItemCount() == 0:
            return None

        item = self.workplace_tree.itemAt(position)

        # New File/Folder
        new_file_action = QAction('New File', self)
        new_file_action.triggered.connect(lambda: self.workspace_new_file(item))
        menu.addAction(new_file_action)

        new_folder_action = QAction('New Folder', self)
        new_folder_action.triggered.connect(lambda: self.workspace_new_folder(item))
        menu.addAction(new_folder_action)

        menu.addSeparator()

        # Open/Explore
        open_file_action = QAction('Open File', self)
        open_file_action.triggered.connect(lambda: self.open_file_item(item))
        menu.addAction(open_file_action)

        explore_file_action = QAction('Show in Explorer', self)
        explore_file_action.triggered.connect(lambda: self.explore_file(item))
        menu.addAction(explore_file_action)

        menu.addSeparator()

        # Rename
        rename_action = QAction('Rename', self)
        rename_action.setShortcut('F2')
        rename_action.triggered.connect(lambda: self.workspace_rename_item(item))
        menu.addAction(rename_action)

        # Copy/Paste/Delete
        copy_action = QAction('Copy', self)
        copy_action.triggered.connect(lambda: self.copy_item(item))
        menu.addAction(copy_action)

        paste_action = QAction('Paste', self)
        paste_action.triggered.connect(self.paste_item)
        menu.addAction(paste_action)

        delete_action = QAction('Delete', self)
        delete_action.setShortcut('Delete')
        delete_action.triggered.connect(lambda: self.delete_file_item(item))
        menu.addAction(delete_action)

        menu.addSeparator()

        # Set Color
        set_color_action = QAction('Set Color', self)
        set_color_action.triggered.connect(lambda: self.set_item_color(item))
        menu.addAction(set_color_action)

        menu.addSeparator()

        # Refresh
        refresh_action = QAction('Refresh', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_workspace)
        menu.addAction(refresh_action)

        # Expand/Collapse All
        expand_all_action = QAction('Expand All', self)
        expand_all_action.triggered.connect(self.expand_all_items)
        menu.addAction(expand_all_action)

        collapse_all_action = QAction('Collapse All', self)
        collapse_all_action.triggered.connect(self.collapse_all_items)
        menu.addAction(collapse_all_action)

        menu.exec_(self.workplace_tree.viewport().mapToGlobal(position))

    def refresh_workspace(self):
        """Refresh workspace to show file system changes"""
        if self.project_dir:
            self.populate_workplace(self.project_dir)
            self.statusBar().showMessage("Workspace refreshed", 2000)

    def workspace_new_file(self, item):
        """Create new file in workspace"""
        if not self.project_dir:
            QMessageBox.warning(self, "New File", "No project directory set.")
            return

        # Get target directory
        if item:
            file_path = item.data(0, Qt.UserRole)
            if os.path.isdir(file_path):
                target_dir = file_path
            else:
                target_dir = os.path.dirname(file_path)
        else:
            target_dir = self.project_dir

        # Ask for filename
        filename, ok = QInputDialog.getText(self, "New File", "Enter filename:")
        if ok and filename:
            requested_path = ensure_py_extension(os.path.join(target_dir, filename))
            base_name = os.path.splitext(os.path.basename(requested_path))[0]
            if not self.is_valid_python_identifier(base_name):
                QMessageBox.warning(self, "Invalid File Name", "The file name must follow Python naming conventions!")
                return
            try:
                new_file_path = get_unique_python_path(requested_path)
                write_python_file(new_file_path, "# New Python file\n", mode="w", encoding="utf-8")
                self.refresh_workspace()
                self.add_new_tab(new_file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create file:\n{str(e)}")

    def workspace_new_folder(self, item):
        """Create new folder in workspace"""
        if not self.project_dir:
            QMessageBox.warning(self, "New Folder", "No project directory set.")
            return

        # Get target directory
        if item:
            file_path = item.data(0, Qt.UserRole)
            if os.path.isdir(file_path):
                target_dir = file_path
            else:
                target_dir = os.path.dirname(file_path)
        else:
            target_dir = self.project_dir

        # Ask for folder name
        foldername, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and foldername:
            new_folder_path = os.path.join(target_dir, foldername)
            try:
                os.makedirs(new_folder_path, exist_ok=True)
                self.refresh_workspace()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create folder:\n{str(e)}")

    def workspace_rename_item(self, item):
        """Rename file or folder"""
        if not item:
            return

        old_path = item.data(0, Qt.UserRole)
        if not old_path or not os.path.exists(old_path):
            return

        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)

        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                self.refresh_workspace()

                # Update open tabs if file is renamed
                for tab_widget in self._all_tab_widgets():
                    for index in range(tab_widget.count()):
                        widget = tab_widget.widget(index)
                        if isinstance(widget, CodeEditor):
                            if getattr(widget, '_file_path', None) == old_path:
                                widget._file_path = new_path
                                tab_widget.setTabText(index, new_name)
                                tab_widget.setTabToolTip(index, new_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename:\n{str(e)}")

    def expand_all_items(self):
        """Expands all items in Workplace."""
        self.workplace_tree.expandAll()

    def collapse_all_items(self):
        """Collapses all items in Workplace."""
        self.workplace_tree.collapseAll()

    def explore_file(self, item):
        """Open file location in system file explorer - cross-platform"""
        file_path = item.data(0, Qt.UserRole)

        if not file_path:
            QMessageBox.warning(self, "Error", "Please select a file or folder.")
            return

        # Get directory path
        if os.path.isfile(file_path):
            dir_path = os.path.dirname(file_path)
        else:
            dir_path = file_path

        if not os.path.exists(dir_path):
            QMessageBox.warning(self, "Error", "Path does not exist.")
            return

        # Platform-specific file explorer opening
        try:
            if sys.platform == 'win32':
                os.startfile(dir_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', dir_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', dir_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file explorer:\n{str(e)}")

    def open_file_item(self, item):
        """Open file from context menu"""
        if not item:
            return

        file_path = item.data(0, Qt.UserRole)

        if not file_path or not os.path.exists(file_path) or os.path.isdir(file_path):
            QMessageBox.warning(self, "Open File", "Please select a valid file.")
            return

        # Check if file is already open (by comparing full paths)
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            if isinstance(widget, CodeEditor):
                existing_path = getattr(widget, '_file_path', None)
                if existing_path and os.path.normpath(existing_path) == os.path.normpath(file_path):
                    # File already open, switch to it
                    self.tab_widget.setCurrentIndex(index)
                    return

        # Open file in new tab
        self.add_new_tab(file_path)

    def copy_item(self, item):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.exists(file_path):
            clipboard = QApplication.clipboard()
            clipboard.setText(file_path)
        else:
            QMessageBox.warning(self, "Hata", "Kopyalanacak dosya mevcut değil.")

    def paste_item(self):
        clipboard = QApplication.clipboard()
        file_path = clipboard.text()
        if os.path.exists(file_path):
            dest_dir = self.project_dir  # Yapıştırma dizinini burada belirtin
            dest_file = os.path.join(dest_dir, os.path.basename(file_path))
            try:
                shutil.copy(file_path, dest_file)
                self.populate_workplace(self.project_dir)  # Yüklemeyi yenile
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Dosya yapıştırılamadı: {str(e)}")
        else:
            QMessageBox.warning(self, "Hata", "Yapıştırılacak dosya mevcut değil.")

    def delete_file_item(self, item):
        if not item:
            return

        file_path = item.data(0, Qt.UserRole)
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Hata", "Silinecek dosya mevcut değil.")
            return

        confirm = QMessageBox.question(
            self,
            "Sil",
            f"Dosya '{os.path.basename(file_path)}' silinsin mi?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        target_root = os.path.normpath(file_path)
        is_dir = os.path.isdir(file_path)

        def is_under_target(path):
            try:
                return os.path.commonpath([target_root, os.path.normpath(path)]) == target_root
            except ValueError:
                return False

        # If any open tabs under this path have unsaved changes, prompt first.
        for tab_widget in self._all_tab_widgets():
            for index in range(tab_widget.count()):
                widget = tab_widget.widget(index)
                if not isinstance(widget, CodeEditor):
                    continue
                tab_path = getattr(widget, '_file_path', None)
                if not tab_path:
                    continue
                if (is_dir and is_under_target(tab_path)) or (not is_dir and os.path.normpath(tab_path) == target_root):
                    if widget.document().isModified():
                        response = self.prompt_save_changes(widget)
                        if response == QMessageBox.Cancel:
                            return
                        if response == QMessageBox.Save:
                            tab_widget.setCurrentIndex(index)
                            self._set_active_tab_widget(tab_widget)
                            if not self.save_file():
                                return

        try:
            if is_dir:
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Dosya silinemedi: {str(e)}")
            return

        # Close any tabs that point to deleted paths without re-prompting.
        for tab_widget in self._all_tab_widgets():
            for index in range(tab_widget.count() - 1, -1, -1):
                widget = tab_widget.widget(index)
                if not isinstance(widget, CodeEditor):
                    continue
                tab_path = getattr(widget, '_file_path', None)
                if not tab_path:
                    continue
                if (is_dir and is_under_target(tab_path)) or (not is_dir and os.path.normpath(tab_path) == target_root):
                    tab_widget.removeTab(index)
            self._cleanup_split_layout(tab_widget)

        self.populate_workplace(self.project_dir)  # Workspace'i güncelle

    def update_open_tabs_path(self, old_path, new_path):
        for tab_widget in self._all_tab_widgets():
            for index in range(tab_widget.count()):
                widget = tab_widget.widget(index)
                if isinstance(widget, CodeEditor):
                    if getattr(widget, '_file_path', None) == old_path:
                        widget._file_path = new_path
                        tab_widget.setTabText(index, os.path.basename(new_path))
                        tab_widget.setTabToolTip(index, new_path)

    def set_item_color(self, item):
        color = QColorDialog.getColor()
        if color.isValid():
            self.update_item_color(item, color)  # Bu satırı kullanarak rengi güncelle ve kaydet

    def save_colors_to_file(self):
        """Renkleri JSON dosyasına kaydet."""
        try:
            with open(self.color_settings_path, 'w') as file:
                json.dump(self.item_colors, file)
        except Exception as e:
            print(f"Error saving colors: {e}")

    def load_colors_from_file(self):
        """Item renklerini JSON dosyasından yükler."""
        if os.path.exists(self.color_settings_path):
            with open(self.color_settings_path, 'r') as file:
                self.item_colors = json.load(file)

            # Ağaçtaki renkleri geri yüklemek için
            def apply_color_to_item(item):
                file_path = item.data(0, Qt.UserRole)
                if file_path in self.item_colors:
                    color = QColor(self.item_colors[file_path])
                    item.setBackground(0, QBrush(color))

            # Tüm öğeleri dolaşarak renkleri uygula
            def iterate_tree_items(item):
                apply_color_to_item(item)
                for i in range(item.childCount()):
                    iterate_tree_items(item.child(i))

            iterate_tree_items(self.workplace_tree.invisibleRootItem())

    def update_item_color(self, item, color):
        file_path = item.data(0, Qt.UserRole)  # Dosya yolunu al
        if file_path:  # Eğer dosya yolu geçerliyse
            # Rengi kaydet
            self.item_colors[file_path] = color.name()  # Renk bilgisini kaydet (örn. '#RRGGBB')
            # Öğenin arka plan rengini değiştir
            item.setBackground(0, QBrush(color))
            # Değişiklikleri hemen kaydet
            self.save_colors_to_file()

    def new_file(self):
        """Yeni Python dosyası oluşturur."""
        print("new_file 1310")
        if not self.project_dir:
            QMessageBox.warning(self, "Save Error", "Project directory is not set.")
            return
        self.add_new_tab("untitled.py")

    def load_suggestions(self):
        # suggestions.json'dan önerileri yükler
        with open(PathFromOS().json_path + "/suggestions.json", "r") as file:
            data = json.load(file)
        return data.get("suggestions", [])
        print(PathFromOS().json_path + "/suggestions.json")

    def create_new_file_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setModal(True)
        dialog.resize(500, 80)

        # Pencereyi ortalamak
        qr = dialog.frameGeometry()
        qr.moveCenter(self.frameGeometry().center())
        dialog.move(qr.topLeft())

        # Gölge efekti
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(30)
        shadow_effect.setOffset(0, 8)
        shadow_effect.setColor(QColor(0, 0, 0, 150))
        dialog.setGraphicsEffect(shadow_effect)

        # Ana layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        # Ana pencere çerçevesine (input_frame) sadece stroke ekliyoruz
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(48, 48, 48, 230); /* Saydam koyu arka plan */
                border: 1px solid rgba(80, 80, 80, 200); /* Kenarlık sadece çerçevede */
                border-radius: 10px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(input_frame)

        # Python logosu (Kenarlık olmadan, saydamlık ile)
        icon_label = QLabel()
        python_icon_path = os.path.join(PathFromOS().icons_path, "python_logo.png")
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)
        python_icon = QPixmap(python_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(python_icon)
        icon_label.setGraphicsEffect(opacity_effect)
        icon_label.setFixedSize(30, 30)
        icon_label.setStyleSheet("""
            QLabel {
                padding-left: 5px;
            }
        """)
        input_layout.addWidget(icon_label)

        # Giriş alanı (QLineEdit)
        file_name_input = QLineEdit()
        file_name_input.setPlaceholderText("Type a name to create a new file...")
        file_name_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                font-size: 14px;
            }
            QLineEdit::placeholder {
                color: rgba(200, 200, 200, 0.6);
            }
        """)
        input_layout.addWidget(file_name_input)

        # Create button
        create_button = QLabel("CREATE")
        create_button.setStyleSheet("""
            QLabel {
                color: rgba(255, 165, 0, 0.8);
                font-size: 12px;
                padding-right: 10px;
            }
        """)
        input_layout.addWidget(create_button)

        # File name validation
        def handle_create():
            file_name = file_name_input.text().strip()
            if file_name:
                self.create_file(file_name, dialog)
            else:
                QMessageBox.warning(self, "Invalid Name", "Please enter a valid file name.")

        file_name_input.returnPressed.connect(handle_create)
        create_button.mousePressEvent = lambda event: handle_create()

        dialog.exec_()

    def create_file(self, file_name, dialog):
        # Proje dizini kontrolü
        if not self.project_dir:
            QMessageBox.warning(self, "No Project Directory", "Please open or create a project before saving files.")
            return

        # Dosya adı Python kurallarına uygun mu kontrol etme
        requested_path = ensure_py_extension(os.path.join(self.project_dir, file_name))
        base_name = os.path.splitext(os.path.basename(requested_path))[0]
        if not self.is_valid_python_identifier(base_name):
            QMessageBox.warning(self, "Invalid File Name", "The file name must follow Python naming conventions!")
            return

        full_path = get_unique_python_path(requested_path)
        write_python_file(full_path, "# New Python file\n", mode="w", encoding="utf-8")

        self.add_new_tab(full_path)  # Yeni dosya ile bir sekme aç
        print("add_new_tab 1500")
        self.populate_workplace(self.project_dir)  # "Workplace" görünümünü güncelle
        dialog.close()

    def populate_outliner_with_functions(self):
        """
        Populates the OUTLINER with classes and functions from specific files,
        excluding the headers from `nuke.py` and `nukescripts.py`.
        """
        # Define paths to the Nuke and Nukescripts files
        nuke_file_path = PathFromOS().nuke_ref_path
        nukescripts_file_path = PathFromOS().nukescripts_ref_path

        # Extract classes and functions from the files
        nuke_classes = self.list_classes_from_file(nuke_file_path)
        nukescripts_classes = self.list_classes_from_file(nukescripts_file_path)

        # Add parsed definitions directly to the OUTLINER
        self.add_classes_and_functions_to_tree(nuke_classes)
        self.add_classes_and_functions_to_tree(nukescripts_classes)

    def add_nuke_functions_to_outliner(self, nuke_functions):
        """
        Adds Nuke-specific functions to the existing OUTLINER without altering other entries.
        """
        if nuke_functions:
            # Search for "Nuke Functions" header in OUTLINER
            parent_item = None
            for i in range(self.outliner_list.topLevelItemCount()):
                item = self.outliner_list.topLevelItem(i)
                if item.text(0) == "Nuke Functions":
                    parent_item = item
                    break

            if not parent_item:
                # Create "Nuke Functions" header if not present
                parent_item = QTreeWidgetItem(self.outliner_list)
                parent_item.setText(0, "Nuke Functions")
                parent_item.setIcon(0, QIcon(os.path.join(PathFromOS().icons_path, 'folder_tree.svg')))  # Folder Icon

            # Add each function under "Nuke Functions"
            for func in nuke_functions:
                func_item = QTreeWidgetItem(parent_item)
                func_item.setText(0, func["name"])  # Extract function name
                func_item.setIcon(0, QIcon(
                    os.path.join(PathFromOS().icons_path, 'M_red.svg')))  # Set the function icon

            # Expand only the "Nuke Functions" category
            self.outliner_list.expandItem(parent_item)

    def add_classes_and_functions_to_tree(self, classes):
        """
        Adds classes and their methods directly to the OUTLINER.
        """
        for class_name, methods in classes:
            # Add class to OUTLINER
            class_item = QTreeWidgetItem(self.outliner_list)
            class_item.setText(0, class_name)
            class_item.setIcon(0, QIcon(os.path.join(PathFromOS().icons_path, 'C_logo.svg')))  # Assign class icon

            # Add methods for the class
            for method in methods:
                method_item = QTreeWidgetItem(class_item)
                method_item.setText(0, method)
                method_item.setIcon(0, QIcon(os.path.join(PathFromOS().icons_path, 'M_logo.svg')))  # Assign method icon

        # Expand all items in the OUTLINER for better visibility
        self.outliner_list.expandAll()

    def list_classes_from_file(self, file_path):
        """Verilen dosyadaki sınıfları ve metotları bulur, özel metotları filtreler."""
        if not os.path.exists(file_path):
            print(f"Error: {file_path} dosyası bulunamadı!")
            return []

        # Dosya içeriğini okuyor ve AST'ye dönüştürüyoruz
        with open(file_path, 'r') as file:
            file_content = file.read()
        tree = ast.parse(file_content)
        classes = []

        # AST üzerinde gezinerek sınıf ve metodları buluyoruz
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                # Sınıf içinde, __init__ gibi özel metodları filtreliyoruz
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('__')]
                classes.append((class_name, methods))

        return classes

    def update_header_tree(self):
        """QPlainTextEdit içindeki metni analiz edip sınıf ve fonksiyonları HEADER'a ekler."""
        # Debounce: Cancel previous timer if exists
        if hasattr(self, '_header_update_timer'):
            self._header_update_timer.stop()

        self._header_update_timer = QTimer()
        self._header_update_timer.setSingleShot(True)
        self._header_update_timer.timeout.connect(self._do_update_header_tree)
        self._header_update_timer.start(300)  # 300ms debounce

    def _do_update_header_tree(self):
        """Actual implementation of header tree update."""
        self.header_tree.clear()

        current_editor = self.tab_widget.currentWidget()
        if current_editor is None:
            return

        if not hasattr(current_editor, 'toPlainText'):
            return

        code = current_editor.toPlainText()

        try:
            tree = ast.parse(code)
        except (SyntaxError, IndentationError) as e:
            # Show syntax error in header
            error_item = QTreeWidgetItem(self.header_tree)
            error_item.setText(0, f"⚠ Syntax Error (line {getattr(e, 'lineno', '?')})")
            error_item.setForeground(0, QColor(255, 100, 100))
            error_item.setData(0, Qt.UserRole, getattr(e, 'lineno', None))
            return

        # Icon paths
        class_icon_path = os.path.join(PathFromOS().icons_path, "C_logo.svg")
        def_icon_path = os.path.join(PathFromOS().icons_path, "def.svg")
        project_icon_path = os.path.join(PathFromOS().icons_path, "python.svg")

        # Current file name header
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            file_name = self.tab_widget.tabText(current_index).replace("*", "").strip()
            file_path = self.tab_widget.tabToolTip(current_index)

            file_item = QTreeWidgetItem(self.header_tree)
            # Use simple bullet point instead of emoji to save space
            file_item.setText(0, f"● {file_name}")
            file_item.setForeground(0, QColor(150, 200, 255))
            file_item.setFont(0, self._make_bold_font())
            file_item.setSizeHint(0, QSize(300, 28))  # Increased width
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsSelectable)

            # Add full path as tooltip if available
            if file_path and os.path.exists(file_path):
                file_item.setToolTip(0, file_path)
            else:
                # If no path, still show filename in tooltip
                file_item.setToolTip(0, file_name)

        # Parse top-level nodes only (more efficient than ast.walk)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self._add_class_item(node, class_icon_path, def_icon_path)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_function_item(node, def_icon_path, is_top_level=True)

        # Expand all by default
        self.header_tree.expandAll()

    def _make_bold_font(self):
        """Create bold font for headers."""
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        return font

    def _get_function_signature(self, node):
        """Extract function signature with parameters."""
        params = []
        for arg in node.args.args:
            param_str = arg.arg
            # Add type annotation if present
            if arg.annotation:
                param_str += f": {ast.unparse(arg.annotation)}"
            params.append(param_str)

        # Add *args if present
        if node.args.vararg:
            vararg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg_str += f": {ast.unparse(node.args.vararg.annotation)}"
            params.append(vararg_str)

        # Add **kwargs if present
        if node.args.kwarg:
            kwarg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg_str += f": {ast.unparse(node.args.kwarg.annotation)}"
            params.append(kwarg_str)

        return f"({', '.join(params)})"

    def _get_decorators(self, node):
        """Get list of decorator names."""
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
        return decorators

    def _get_docstring(self, node):
        """Extract docstring from node."""
        return ast.get_docstring(node) or ""

    def _add_class_item(self, node, class_icon_path, def_icon_path):
        """Add a class item to the header tree."""
        class_item = QTreeWidgetItem(self.header_tree)

        # Build class display name with decorators
        decorators = self._get_decorators(node)
        class_name = node.name
        if decorators:
            class_name = f"@{', @'.join(decorators)} {class_name}"

        # Check for base classes
        if node.bases:
            bases = [ast.unparse(base) for base in node.bases]
            class_name += f"({', '.join(bases)})"

        class_item.setText(0, class_name)
        class_item.setIcon(0, QIcon(class_icon_path))
        class_item.setData(0, Qt.UserRole, node.lineno)
        class_item.setData(0, Qt.UserRole + 1, "class")
        class_item.setForeground(0, QColor(100, 200, 255))
        class_item.setFont(0, self._make_bold_font())
        class_item.setSizeHint(0, QSize(200, 26))

        # Add docstring as tooltip
        docstring = self._get_docstring(node)
        if docstring:
            class_item.setToolTip(0, docstring[:200] + "..." if len(docstring) > 200 else docstring)

        # Add line number indicator
        class_item.setText(1, f":{node.lineno}")
        class_item.setForeground(1, QColor(120, 120, 120))

        # Add methods
        for sub_node in node.body:
            if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_method_item(sub_node, class_item, def_icon_path)

    def _add_method_item(self, node, parent_item, def_icon_path):
        """Add a method item under a class."""
        method_item = QTreeWidgetItem(parent_item)

        # Get decorators
        decorators = self._get_decorators(node)

        # Determine method type and color
        is_async = isinstance(node, ast.AsyncFunctionDef)
        is_static = 'staticmethod' in decorators
        is_classmethod = 'classmethod' in decorators
        is_property = 'property' in decorators

        # Build display name
        prefix = ""
        color = QColor(200, 200, 150)

        if is_async:
            prefix = "async "
            color = QColor(255, 180, 100)
        if is_static:
            prefix = "static "
            color = QColor(150, 150, 200)
        elif is_classmethod:
            prefix = "class "
            color = QColor(150, 200, 150)
        elif is_property:
            prefix = "@property "
            color = QColor(200, 150, 200)

        signature = self._get_function_signature(node)
        method_name = f"{prefix}{node.name}{signature}"

        method_item.setText(0, method_name)
        method_item.setIcon(0, QIcon(def_icon_path))
        method_item.setData(0, Qt.UserRole, node.lineno)
        method_item.setData(0, Qt.UserRole + 1, "method")
        method_item.setForeground(0, color)
        method_item.setSizeHint(0, QSize(200, 24))

        # Add docstring as tooltip
        docstring = self._get_docstring(node)
        if docstring:
            method_item.setToolTip(0, docstring[:200] + "..." if len(docstring) > 200 else docstring)

        # Add line number
        method_item.setText(1, f":{node.lineno}")
        method_item.setForeground(1, QColor(100, 100, 100))

    def _add_function_item(self, node, def_icon_path, is_top_level=True):
        """Add a function item to the header tree."""
        func_item = QTreeWidgetItem(self.header_tree)

        # Determine if async
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Build display name
        prefix = "async " if is_async else ""
        signature = self._get_function_signature(node)
        func_name = f"{prefix}{node.name}{signature}"

        func_item.setText(0, func_name)
        func_item.setIcon(0, QIcon(def_icon_path))
        func_item.setData(0, Qt.UserRole, node.lineno)
        func_item.setData(0, Qt.UserRole + 1, "function")
        func_item.setForeground(0, QColor(255, 200, 100) if is_async else QColor(180, 220, 180))
        func_item.setSizeHint(0, QSize(200, 24))

        # Add docstring as tooltip
        docstring = self._get_docstring(node)
        if docstring:
            func_item.setToolTip(0, docstring[:200] + "..." if len(docstring) > 200 else docstring)

        # Add line number
        func_item.setText(1, f":{node.lineno}")
        func_item.setForeground(1, QColor(120, 120, 120))

    def go_to_line_from_header(self, item, column):
        """HEADER'da bir öğeye tıklandığında ilgili satıra gitme işlemi."""
        line_number = item.data(0, Qt.UserRole)  # Satır numarası verisini alıyoruz
        if line_number is not None:
            current_editor = self.tab_widget.currentWidget()
            # WelcomeWidget veya CodeEditor olmayan widget'ları kontrol et
            if not hasattr(current_editor, 'textCursor'):
                return  # textCursor metodu yoksa çık

            cursor = current_editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_number - 1)  # Satıra gitme
            current_editor.setTextCursor(cursor)
            current_editor.setFocus()

    def context_menu_header(self, position):
        """HEADER için context menu."""
        item = self.header_tree.itemAt(position)

        menu = QMenu()

        # "Go to Line" action
        if item and item.data(0, Qt.UserRole) is not None:
            go_to_action = QAction("Go to Line", self)
            go_to_action.triggered.connect(lambda: self.go_to_line_from_header(item, 0))
            menu.addAction(go_to_action)

            # "Copy Name" action
            copy_name_action = QAction("Copy Name", self)
            copy_name_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text(0).split('(')[0].strip()))
            menu.addAction(copy_name_action)

            # "Copy Signature" action (for functions/methods)
            item_type = item.data(0, Qt.UserRole + 1)
            if item_type in ["function", "method"]:
                copy_sig_action = QAction("Copy Full Signature", self)
                copy_sig_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text(0)))
                menu.addAction(copy_sig_action)

            menu.addSeparator()

        # "Expand All" action
        expand_all_action = QAction("Expand All", self)
        expand_all_action.triggered.connect(self.header_tree.expandAll)
        menu.addAction(expand_all_action)

        # "Collapse All" action
        collapse_all_action = QAction("Collapse All", self)
        collapse_all_action.triggered.connect(self.header_tree.collapseAll)
        menu.addAction(collapse_all_action)

        menu.addSeparator()

        # "Refresh" action
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._do_update_header_tree)
        menu.addAction(refresh_action)

        # Show menu
        menu.exec_(self.header_tree.viewport().mapToGlobal(position))

    def insert_into_editor(self, item, column):
        """OUTLINER'da çift tıklanan öğeyi aktif metin düzenleyiciye ekler."""
        # Seçilen sınıf ya da fonksiyon adını al
        selected_text = item.text(0)

        # Aktif düzenleyiciye eriş
        current_editor = self.tab_widget.currentWidget()

        # WelcomeWidget veya CodeEditor olmayan widget'ları kontrol et
        if current_editor and hasattr(current_editor, 'textCursor'):
            cursor = current_editor.textCursor()  # Düzenleyicinin imlecini al

            # Metni imlecin olduğu yere ekleyelim ve bir boşluk ekleyelim
            cursor.insertText(selected_text + ' ')  # Metni ekledikten sonra bir boşluk ekler

            # İmleci güncelle
            current_editor.setTextCursor(cursor)

    def context_menu_outliner(self, position):
        """OUTLINER'da sağ tıklama menüsü oluşturur."""
        item = self.outliner_list.itemAt(position)
        if item is None:
            return

        menu = QMenu()

        # "Insert the Code" seçeneği
        insert_action = QAction("Insert the Code", self)
        insert_action.triggered.connect(lambda: self.insert_into_editor(item, 0))

        # "Go to Information" seçeneği
        go_to_info_action = QAction("Search API Reference", self)
        go_to_info_action.triggered.connect(lambda: self.go_to_information(item))

        # Menü öğelerini ekleyin
        menu.addAction(insert_action)
        menu.addAction(go_to_info_action)

        # Ayraç ekleyin
        menu.addSeparator()

        # "Expand All" seçeneği
        expand_all_action = QAction("Expand All", self)
        expand_all_action.triggered.connect(self.expand_all_outliner_items)
        menu.addAction(expand_all_action)

        # "Collapse All" seçeneği
        collapse_all_action = QAction("Collapse All", self)
        collapse_all_action.triggered.connect(self.collapse_all_outliner_items)
        menu.addAction(collapse_all_action)

        # Ayraç ekleyin
        menu.addSeparator()

        # "Search QLineEdit'i Aç" seçeneği
        search_action = QAction("Open Search Bar", self)
        search_action.triggered.connect(self.toggle_search_bar)  # Daha önceki toggle_search_bar işlevine bağlandı
        menu.addAction(search_action)

        # Sağ tıklama menüsünü göster
        menu.exec_(self.outliner_list.viewport().mapToGlobal(position))

    def expand_all_outliner_items(self):
        """OUTLINER'daki tüm öğeleri genişletir."""
        self.outliner_list.expandAll()

    def collapse_all_outliner_items(self):
        """OUTLINER'daki tüm öğeleri kapatır."""
        self.outliner_list.collapseAll()

    def go_to_information(self, item):
        """Seçilen öğeyi geliştirici kılavuzunda arar."""
        selected_text = item.text(0)  # Seçilen öğe

        # URL şablonu
        base_url = "https://learn.foundry.com/nuke/developers/15.0/pythondevguide/search.html"

        # Arama sorgusunu oluştur
        search_url = f"{base_url}?q={selected_text}&check_keywords=yes&area=default"

        # Tarayıcıda aç
        webbrowser.open(search_url)

    def custom_outliner_action(self, item):
        """OUTLINER'da özel bir işlem gerçekleştirir."""
        selected_text = item.text(0)
        QMessageBox.information(self, "Custom Action", f"You selected: {selected_text}")

    def filter_outliner(self, text):
        """Filters items in OUTLINER based on text in the search bar"""
        root = self.outliner_list.invisibleRootItem()  # OUTLINER'ın kök öğesi

        # Filtre metni boşsa tüm öğeleri göster
        if not text:
            for i in range(root.childCount()):
                item = root.child(i)
                item.setHidden(False)
                for j in range(item.childCount()):
                    sub_item = item.child(j)
                    sub_item.setHidden(False)
            return

        # Filter classes and methods based on search text
        for i in range(root.childCount()):  # Ana öğeler (sınıflar)
            item = root.child(i)
            match_found = False  # Ana öğeyi gösterip göstermeme durumu

            # Ana öğe metniyle arama metni eşleşiyor mu?
            if text.lower() in item.text(0).lower():
                item.setHidden(False)
                match_found = True
            else:
                item.setHidden(True)

            # Alt öğeleri kontrol et (metotlar)
            for j in range(item.childCount()):
                sub_item = item.child(j)

                if text.lower() in sub_item.text(0).lower():  # Arama metni alt öğeyle eşleşiyor mu?
                    sub_item.setHidden(False)
                    match_found = True  # Eğer bir alt öğe eşleşiyorsa ana öğeyi de göster
                else:
                    sub_item.setHidden(True)

            # Eğer alt öğelerden biri eşleştiyse ana öğeyi göster
            if match_found:
                item.setHidden(False)

    def update_completer_from_outliner(self):
        """OUTLINER'daki sınıf ve fonksiyon isimlerini QCompleter'e ekler."""
        outliner_items = []
        root = self.outliner_list.invisibleRootItem()  # OUTLINER'ın kök öğesi

        # OUTLINER'daki tüm öğeleri dolaşarak listeye ekle
        for i in range(root.childCount()):  # Ana öğeler (class'lar)
            item = root.child(i)
            outliner_items.append(item.text(0))  # Class ismini ekle

            for j in range(item.childCount()):  # Alt öğeler (methods'ler)
                sub_item = item.child(j)
                outliner_items.append(sub_item.text(0))  # Method ismini ekle

        # Tamamlama önerileri için QStringListModel kullanarak model oluşturuyoruz
        model = QStringListModel(outliner_items, self.completer)
        self.completer.setModel(model)

    def is_valid_python_identifier(self, name):
        """Python değişken adı kurallarına uygunluk kontrolü"""
        if not name.isidentifier():
            return False
        return True

    def show_python_naming_info(self):
        QMessageBox.information(self, "Python Naming Info",
                                "Python file names must:\n- Start with a letter or underscore\n- Contain only letters, numbers, or underscores\n- Not be a reserved keyword")
