import os
from PySide2.QtCore import Qt, QEvent
from PySide2.QtWidgets import QApplication, QMessageBox, QSplitter
from PySide2.QtCore import QSize
from editor.code_editor import CodeEditor
from editor.ui.widgets.custom_tab_widget import CustomTabWidget
from editor.core import CodeEditorSettings


class TabOpsMixin:
    def _create_tab_widget(self):
        tab_widget = CustomTabWidget(self)
        tab_widget.setIconSize(QSize(15, 15))
        tab_widget.setTabsClosable(True)
        tab_widget.tabCloseRequested.connect(lambda index, tw=tab_widget: self.close_tab(index, tw))
        tab_widget.currentChanged.connect(self.ensure_tab)
        tab_widget.currentChanged.connect(lambda _=None, tw=tab_widget: self._set_active_tab_widget(tw))
        self._tab_widgets.append(tab_widget)
        return tab_widget

    def _all_tab_widgets(self):
        return list(self._tab_widgets) if self._tab_widgets else [self.tab_widget]

    def _real_tab_count(self, tab_widget):
        count = tab_widget.count()
        if hasattr(tab_widget, "welcome_widget"):
            if tab_widget.indexOf(tab_widget.welcome_widget) >= 0:
                count -= 1
        return max(0, count)

    def _find_parent_tab_widget(self, widget):
        while widget is not None:
            if isinstance(widget, CustomTabWidget):
                return widget
            widget = widget.parent()
        return None

    def _set_active_tab_widget(self, tab_widget):
        if tab_widget:
            self.tab_widget = tab_widget

    def _current_tab_widget(self):
        focus_widget = QApplication.focusWidget()
        active = self._find_parent_tab_widget(focus_widget) if focus_widget else None
        if active:
            self._set_active_tab_widget(active)
            return active
        return self.tab_widget

    def _cleanup_split_layout(self, tab_widget):
        if not self._tab_splitter:
            return
        if len(self._tab_widgets) <= 1:
            return
        if not tab_widget or self._real_tab_count(tab_widget) > 0:
            return

        parent = tab_widget.parent()
        tab_widget.setParent(None)
        if tab_widget in self._tab_widgets:
            self._tab_widgets.remove(tab_widget)

        self._collapse_splitter(parent)

    def _collapse_splitter(self, splitter):
        if not isinstance(splitter, QSplitter):
            return

        if splitter.count() == 1:
            remaining = splitter.widget(0)
            parent = splitter.parent()
            splitter.setParent(None)

            if isinstance(parent, QSplitter):
                index = parent.indexOf(splitter)
                parent.insertWidget(index, remaining)
                self._collapse_splitter(parent)
            else:
                self.setCentralWidget(remaining)
                self._tab_splitter = remaining if isinstance(remaining, QSplitter) else None
            return

        if splitter.count() == 0:
            parent = splitter.parent()
            splitter.setParent(None)
            self._collapse_splitter(parent)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            tab_widget = self._find_parent_tab_widget(obj)
            if tab_widget:
                self._set_active_tab_widget(tab_widget)
        return super().eventFilter(obj, event)

    def add_new_tab(self, file_path, initial_content=""):
        """Yeni bir sekme oluşturur ve dosyayı yükler."""
        target_tabs = self._current_tab_widget()
        editor = CodeEditor()  # QPlainTextEdit yerine CodeEditor kullanıyoruz
        editor.textChanged.connect(self.update_header_tree)  # Direkt editor widget'ine bağlama yaptık

        # Store file path in editor for accurate duplicate detection
        if os.path.exists(file_path):
            editor._file_path = os.path.abspath(file_path)
        else:
            editor._file_path = file_path  # untitled files

        # Dosya içeriği eğer mevcutsa yüklüyoruz, yoksa varsayılan içerik ile açıyoruz
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                editor.setPlainText(content)
                editor.document().setModified(False)  # Mark as not modified after loading
        else:
            editor.setPlainText(initial_content)
            # For new untitled files, mark as modified so user knows to save
            if initial_content:
                editor.document().setModified(True)

        # Connect modification tracking
        editor.document().modificationChanged.connect(
            lambda modified: self.on_modification_changed(editor, modified)
        )

        # Add tab with file name
        tab_index = target_tabs.addTab(editor, self.python_icon, os.path.basename(file_path))
        target_tabs.setCurrentWidget(editor)

        # Set tooltip with full file path for existing files
        if os.path.exists(file_path):
            target_tabs.setTabToolTip(tab_index, os.path.normpath(os.path.abspath(file_path)))

        # Completer popup'ını kontrol etmeden önce niteliklerin var olup olmadığını kontrol ediyoruz
        if hasattr(editor, 'completer') and hasattr(editor.completer, 'completion_popup'):
            editor.completer.completion_popup.popup().hide()

    def close_tab(self, index, tab_widget=None):
        """Bir sekmeyi kapatmadan önce kontrol eder."""
        target_tabs = tab_widget or self.tab_widget
        widget = target_tabs.widget(index)
        if not widget:
            return True

        # Skip welcome widget
        if not isinstance(widget, CodeEditor):
            target_tabs.removeTab(index)
            self._cleanup_split_layout(target_tabs)
            return True

        print("istemci kapatildi")
        if widget.document().isModified():
            # Eğer sekmede kaydedilmemiş değişiklikler varsa kullanıcıya soralım
            response = self.prompt_save_changes(widget)
            if response == QMessageBox.Save:
                target_tabs.setCurrentIndex(index)
                self._set_active_tab_widget(target_tabs)
                if self.save_file():
                    target_tabs.removeTab(index)  # Dosya kaydedildiyse tabı kapat
                else:
                    return False
            elif response == QMessageBox.Discard:
                target_tabs.removeTab(index)  # Kaydetmeden kapat
            elif response == QMessageBox.Cancel:
                return False  # İptal edildiğinde hiçbir işlem yapma

        else:
            target_tabs.removeTab(index)  # Değişiklik yoksa doğrudan kapat

        self._cleanup_split_layout(target_tabs)
        return True

    def split_editor_tab(self, index, direction, side=None, tab_widget=None):
        """
        Split tab in given direction
        Note: Full split implementation requires QSplitter integration
        For now, showing notification
        """
        target_tabs = tab_widget or self.tab_widget
        if not target_tabs or index < 0:
            return

        tab_widget_to_move = target_tabs.widget(index)
        if not tab_widget_to_move or tab_widget_to_move == target_tabs.welcome_widget:
            return

        new_tab_widget = self._create_tab_widget()

        tab_text = target_tabs.tabText(index)
        tab_icon = target_tabs.tabIcon(index)
        tab_tooltip = target_tabs.tabToolTip(index)

        target_tabs.removeTab(index)
        new_index = new_tab_widget.addTab(tab_widget_to_move, tab_icon, tab_text)
        if tab_tooltip:
            new_tab_widget.setTabToolTip(new_index, tab_tooltip)
        new_tab_widget.setCurrentIndex(new_index)

        orientation = Qt.Horizontal if direction == "horizontal" else Qt.Vertical
        side = side or ("right" if direction == "horizontal" else "bottom")

        parent_splitter = target_tabs.parent()
        if isinstance(parent_splitter, QSplitter):
            if parent_splitter.orientation() == orientation:
                insert_index = parent_splitter.indexOf(target_tabs)
                if side in ("left", "top"):
                    parent_splitter.insertWidget(insert_index, new_tab_widget)
                else:
                    parent_splitter.insertWidget(insert_index + 1, new_tab_widget)
            else:
                new_splitter = QSplitter(orientation, parent_splitter)
                insert_index = parent_splitter.indexOf(target_tabs)
                parent_splitter.insertWidget(insert_index, new_splitter)
                target_tabs.setParent(None)
                if side in ("left", "top"):
                    new_splitter.addWidget(new_tab_widget)
                    new_splitter.addWidget(target_tabs)
                else:
                    new_splitter.addWidget(target_tabs)
                    new_splitter.addWidget(new_tab_widget)
        else:
            splitter = QSplitter(orientation, self)
            if side in ("left", "top"):
                splitter.addWidget(new_tab_widget)
                splitter.addWidget(target_tabs)
            else:
                splitter.addWidget(target_tabs)
                splitter.addWidget(new_tab_widget)
            self.setCentralWidget(splitter)
            self._tab_splitter = splitter

        self._set_active_tab_widget(new_tab_widget)

    def prompt_save_changes(self, editor=None):
        """Kaydedilmemiş değişiklikler için bir uyarı gösterir ve kullanıcıdan giriş alır."""
        unsaved_files = []

        # Eğer belirli bir editördeki kaydedilmemiş değişiklik kontrol ediliyorsa, onun adını ekle
        if editor:
            if isinstance(editor, CodeEditor) and editor.document().isModified():
                for tab_widget in self._all_tab_widgets():
                    index = tab_widget.indexOf(editor)
                    if index != -1:
                        unsaved_files.append(tab_widget.tabText(index))
                        break
        else:
            # Tüm kaydedilmemiş dosyaların listesini alalım
            for tab_widget in self._all_tab_widgets():
                for i in range(tab_widget.count()):
                    widget = tab_widget.widget(i)
                    # Skip welcome widget - only check CodeEditor instances
                    if isinstance(widget, CodeEditor):
                        if widget.document().isModified():
                            tab_title = tab_widget.tabText(i)
                            unsaved_files.append(tab_title)

        # Eğer kaydedilmemiş dosya yoksa None döndür ve mesaj göstermeden devam et
        if not unsaved_files:
            return None

        # Kaydedilmemiş dosyalar varsa mesajı oluştur
        message = "You did not save the last changes made.\nUnsaved files:\n"
        message += "\n".join(f"- {file}" for file in unsaved_files)

        # Kaydetme, kaydetmeden çıkma ve iptal seçeneklerini sunalım
        response = QMessageBox.question(
            self,
            "Unsaved changes",
            message,
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        return response

    def save_all_files(self):
        """Tüm açık sekmelerdeki dosyaları kaydeder."""
        active_tabs = self._current_tab_widget()
        for tab_widget in self._all_tab_widgets():
            current_index = tab_widget.currentIndex()

            for i in range(tab_widget.count()):
                widget = tab_widget.widget(i)
                # Skip welcome widget - only save CodeEditor instances
                if isinstance(widget, CodeEditor) and widget.document().isModified():
                    # Switch to this tab and save
                    tab_widget.setCurrentIndex(i)
                    self._set_active_tab_widget(tab_widget)
                    self.save_file()

            # Restore original tab
            if current_index >= 0 and current_index < tab_widget.count():
                tab_widget.setCurrentIndex(current_index)

        self._set_active_tab_widget(active_tabs)

    def close_all_tabs(self):
        """Close all tabs with save prompts"""
        for tab_widget in self._all_tab_widgets():
            while tab_widget.count() > 0:
                if not self.close_tab(0, tab_widget):
                    return

    def close_other_tabs(self):
        """Close all tabs except the current one"""
        target_tabs = self._current_tab_widget()
        current_index = target_tabs.currentIndex()
        if current_index == -1:
            return

        # Close tabs after current (in reverse to maintain indices)
        for i in range(target_tabs.count() - 1, current_index, -1):
            if not self.close_tab(i, target_tabs):
                return

        # Close tabs before current (in reverse)
        for i in range(current_index - 1, -1, -1):
            if not self.close_tab(i, target_tabs):
                return

    def ensure_tab(self):
        """Ensure at least one tab is open and update HEADER panel"""
        # CustomTabWidget automatically shows welcome screen when count == 0
        # Update header tree when tab changes
        self.update_header_tree()

    def add_new_untitled_tab(self):
        """Add a new untitled tab with auto-incrementing number"""
        untitled_name = self.tab_widget.get_next_untitled_name()
        self.add_new_tab(untitled_name, initial_content=CodeEditorSettings().temp_codes)

        # Hide completer popup
        current_editor = self.tab_widget.currentWidget()
        if isinstance(current_editor, CodeEditor):
            if hasattr(current_editor, 'completer') and hasattr(current_editor.completer, 'completion_popup'):
                current_editor.completer.completion_popup.popup().hide()
