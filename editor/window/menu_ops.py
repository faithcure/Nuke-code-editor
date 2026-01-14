import os
from PySide2.QtGui import QKeySequence, QIcon
from PySide2.QtWidgets import QAction, QMenu, QMessageBox, QStyle
import nuke
from editor.core import PathFromOS
from editor.settings.github_utils import commit_changes, push_to_github, pull_from_github, get_status
from editor.dependencies import check_dependencies
from editor.settings.settings_ui import SettingsWindow
from editor.ui.dialogs.goToLineDialogs import GoToLineDialog
from editor.ui.dialogs.searchDialogs import SearchDialog
from editor.code_editor import CodeEditor


class MenuOpsMixin:
    def create_menu(self):
        """Genişletilmiş ve yeniden düzenlenmiş menü çubuğunu oluşturur."""
        def icon(filename=None, fallback=None):
            if filename:
                icon_path = os.path.join(PathFromOS().icons_path, filename)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
            if fallback is not None:
                try:
                    return self.style().standardIcon(fallback)
                except Exception:
                    pass
            return QIcon()

        menubar = self.menuBar()
        menubar.setStyleSheet("QMenuBar { padding: 4px 4px; font-size: 8pt; }")  # Menü çubuğu boyutu

        # 1. File Menüsü
        file_menu = menubar.addMenu('File')
        self.new_project_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'new_project.png')),
                                          'New Project', self)
        self.new_project_action.setShortcut(QKeySequence(self.settings.get_shortcut("New Project")))

        # New Project alt menüleri (Nuke ve Custom projeler)
        new_project_menu = QMenu('New Project', self)
        nuke_project_action = QAction(icon('welcome_new_nuke.svg', QStyle.SP_FileIcon),
                                      'Nuke Project (.nuke)', self)
        custom_project_action = QAction(icon('welcome_new_project.svg', QStyle.SP_FileIcon),
                                        'Custom Project', self)

        custom_project_action.triggered.connect(self.new_project_dialog)
        nuke_project_action.triggered.connect(self.open_nuke_project_dialog)
        new_project_menu.addAction(nuke_project_action)
        new_project_menu.addAction(custom_project_action)

        # File menüsü diğer aksiyonlar
        open_project_action = QAction(icon('welcome_open_project.svg', QStyle.SP_DirOpenIcon), 'Open Project',
                                      self)
        new_file_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'new_file.png')), 'New File', self)
        new_file_action.setShortcut(QKeySequence(self.settings.get_shortcut("New File")))
        open_action = QAction(icon(None, QStyle.SP_DialogOpenButton), 'Open File', self)
        open_action.setShortcut(QKeySequence(self.settings.get_shortcut("Open File")))

        save_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'save.svg')), 'Save', self)
        save_action.setShortcut(QKeySequence(self.settings.get_shortcut("Save")))
        save_as_action = QAction(icon(None, QStyle.SP_DialogSaveButton), 'Save As', self)
        save_as_action.setShortcut(QKeySequence(self.settings.get_shortcut("Save As")))
        save_all_action = QAction(icon('save.svg', QStyle.SP_DialogSaveButton), 'Save All', self)
        save_all_action.setShortcut(QKeySequence('Ctrl+K, S'))

        close_tab_action = QAction(icon('close_01.svg', QStyle.SP_DockWidgetCloseButton), 'Close Tab', self)
        close_tab_action.setShortcut(QKeySequence(self.settings.get_shortcut("Close Tab")))
        close_all_action = QAction(icon('close_01.svg', QStyle.SP_DockWidgetCloseButton), 'Close All Tabs', self)
        close_all_action.setShortcut(QKeySequence('Ctrl+Shift+W'))
        close_other_action = QAction(icon('close_01.svg', QStyle.SP_DockWidgetCloseButton), 'Close Other Tabs', self)

        copy_path_action = QAction(icon('output_copy.svg', QStyle.SP_DialogOpenButton), 'Copy File Path', self)
        copy_path_action.setShortcut(QKeySequence('Ctrl+Shift+C'))
        show_explorer_action = QAction(icon('folder_tree.svg', QStyle.SP_DirOpenIcon), 'Show in Explorer', self)

        exit_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'exit.png')), 'Exit', self)
        exit_action.setShortcut(QKeySequence(self.settings.get_shortcut("Exit")))

        # Preferences öğesi
        preferences_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'settings.png')), 'Preferences', self)

        # Connect actions
        save_all_action.triggered.connect(self.save_all_files)
        close_all_action.triggered.connect(self.close_all_tabs)
        close_other_action.triggered.connect(self.close_other_tabs)
        copy_path_action.triggered.connect(self.copy_file_path)
        show_explorer_action.triggered.connect(self.show_in_explorer)

        # File menüsüne eklemeler
        file_menu.addMenu(new_project_menu)
        file_menu.addAction(open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(new_file_action)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addAction(save_all_action)
        file_menu.addSeparator()
        file_menu.addAction(close_tab_action)
        file_menu.addAction(close_all_action)
        file_menu.addAction(close_other_action)
        file_menu.addSeparator()
        file_menu.addAction(copy_path_action)
        file_menu.addAction(show_explorer_action)
        file_menu.addSeparator()
        file_menu.addAction(preferences_action)
        file_menu.addSeparator()
        self.recent_projects = file_menu.addMenu('Recent Projects')
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # 2. Edit Menüsü
        edit_menu = menubar.addMenu('Edit')
        undo_action = QAction(icon(None, QStyle.SP_ArrowBack), 'Undo', self)
        undo_action.setShortcut(QKeySequence(self.settings.get_shortcut("Undo")))
        redo_action = QAction(icon(None, QStyle.SP_ArrowForward), 'Redo', self)
        redo_action.setShortcut(QKeySequence(self.settings.get_shortcut("Redo")))

        # Go To Line öğesi
        go_to_line_action = QAction(icon('goto_line.svg', QStyle.SP_FileDialogDetailedView), 'Go To Line', self)
        go_to_line_action.setShortcut(QKeySequence(self.settings.get_shortcut("Go to Line")))

        find_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'search.svg')), 'Search && Replace', self)
        find_action.setShortcut(QKeySequence(self.settings.get_shortcut("Find")))
        clear_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'clear.svg')), 'Clear Output', self)

        cut_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'cut.png')), 'Cut', self)
        cut_action.setShortcut(QKeySequence(self.settings.get_shortcut("Cut")))
        copy_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'copy.png')), 'Copy', self)
        copy_action.setShortcut(QKeySequence(self.settings.get_shortcut("Copy")))
        paste_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'paste.png')), 'Paste', self)
        paste_action.setShortcut(QKeySequence(self.settings.get_shortcut("Paste")))
        select_all_action = QAction('Select All', self)
        select_all_action.setShortcut(QKeySequence(self.settings.get_shortcut("Select All")))

        # Edit menüsüne eklemeler
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(cut_action)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        edit_menu.addAction(select_all_action)
        edit_menu.addSeparator()
        edit_menu.addAction(go_to_line_action)  # Go To Line eklenmesi
        edit_menu.addAction(find_action)
        edit_menu.addSeparator()
        edit_menu.addAction(clear_action)

        # 3. View Menüsü
        view_menu = menubar.addMenu('View')

        # Zoom işlemleri
        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.setShortcut(QKeySequence(self.settings.get_shortcut("Zoom In")))
        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.setShortcut(QKeySequence(self.settings.get_shortcut("Zoom Out")))
        reset_zoom_action = QAction('Reset Zoom', self)  # Reset Zoom eklendi
        reset_zoom_action.setShortcut(QKeySequence(self.settings.get_shortcut("Reset Zoom")))

        # View menüsüne eklemeler
        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(reset_zoom_action)  # Reset Zoom menüye eklendi
        view_menu.addSeparator()

        # UI Modes submenu
        import editor.settings.settings_ux as settings_ux
        ui_modes_menu = view_menu.addMenu(QIcon(os.path.join(PathFromOS().icons_path, 'ux_design.svg')), 'UI Modes')

        default_mode_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'mode_default.svg')), 'Default Mode', self)
        default_mode_action.triggered.connect(lambda: settings_ux.set_default_mode(self))
        ui_modes_menu.addAction(default_mode_action)

        expanded_mode_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'mode_expanded.svg')), 'Expanded Mode', self)
        expanded_mode_action.triggered.connect(lambda: settings_ux.set_expanded_mode(self))
        ui_modes_menu.addAction(expanded_mode_action)

        focus_mode_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'mode_focus.svg')), 'Focus Mode', self)
        focus_mode_action.triggered.connect(lambda: settings_ux.set_focus_mode(self))
        ui_modes_menu.addAction(focus_mode_action)

        compact_mode_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'mode_compact.svg')), 'Compact Mode', self)
        compact_mode_action.triggered.connect(lambda: settings_ux.set_compact_mode(self))
        ui_modes_menu.addAction(compact_mode_action)

        saitama_mode_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'mode_focus.svg')), 'Saitama', self)
        saitama_mode_action.triggered.connect(lambda: settings_ux.set_saitama_mode(self))
        ui_modes_menu.addAction(saitama_mode_action)

        view_menu.addSeparator()

        # Reset ve Varsayılan UI aksiyonları
        reset_ui_action = QAction('Reset UI', self)
        set_default_ui_action = QAction('Set Default UI', self)
        view_menu.addAction(reset_ui_action)
        view_menu.addAction(set_default_ui_action)

        # Zoom işlevlerini bağlama
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_out_action.triggered.connect(self.zoom_out)
        reset_zoom_action.triggered.connect(self.reset_zoom)  # Reset Zoom işlevine bağlama

        # 4. Run Menüsü
        run_menu = menubar.addMenu('Run')

        # Main run actions (match keyboard shortcuts)
        self.run_code_action = QAction(
            QIcon(os.path.join(PathFromOS().icons_path, 'run-icon.svg')),
            'Run (Selection/All)',
            self,
        )
        self.run_code_action.setShortcut(QKeySequence(self.settings.get_shortcut("Run Code")))

        self.run_all_code_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'run_all.svg')), 'Run All Code', self)
        self.run_all_code_action.setShortcut(QKeySequence(self.settings.get_shortcut("Execute All Code")))

        self.execute_current_line_action = QAction(
            QIcon(os.path.join(PathFromOS().icons_path, 'run_current.svg')),
            'Execute Current Line',
            self,
        )
        self.execute_current_line_action.setShortcut(QKeySequence(self.settings.get_shortcut("Execute Current Line")))

        self.stop_execution_action = QAction(
            QIcon(os.path.join(PathFromOS().icons_path, 'close_01.svg')),
            'Stop Execution',
            self,
        )

        run_menu.addAction(self.run_code_action)
        run_menu.addAction(self.run_all_code_action)
        run_menu.addAction(self.execute_current_line_action)
        run_menu.addSeparator()
        run_menu.addAction(self.stop_execution_action)

        # 5. Tools Menüsü
        tools_menu = menubar.addMenu('Tools')

        # Import createNodesCode for node creation tools
        from editor.nodes.crtNode import createNodesCode
        # Store as instance attribute to prevent garbage collection
        self._create_nodes_instance = createNodesCode()

        # Add Create Nodes items directly to Tools menu (only working items)
        create_node_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'crt_node.svg')), 'Create Node Wizard', self)
        create_node_action.triggered.connect(self._create_nodes_instance.createNodeMenu)
        tools_menu.addAction(create_node_action)

        tools_menu.addSeparator()

        live_connection_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'pycharm.png')), 'LCV PyCharm', self)
        live_connection_action.setEnabled(False)
        tools_menu.addAction(live_connection_action)

        tools_menu.addSeparator()

        # GitHub alt menüsü
        github_menu = tools_menu.addMenu(QIcon(os.path.join(PathFromOS().icons_path, 'github.svg')), 'GitHub')
        git_commit_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'commit.png')), 'Commit', self)
        git_push_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'push.png')), 'Push', self)
        git_pull_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'pull.png')), 'Pull', self)
        git_status_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'status.png')), 'Status', self)

        github_menu.addAction(git_commit_action)
        github_menu.addAction(git_push_action)
        github_menu.addAction(git_pull_action)
        github_menu.addAction(git_status_action)

        # Menü eylemleri için fonksiyon bağlama
        git_commit_action.triggered.connect(lambda: commit_changes(self))
        git_push_action.triggered.connect(lambda: push_to_github(self))
        git_pull_action.triggered.connect(lambda: pull_from_github(self))
        git_status_action.triggered.connect(lambda: get_status(self))

        # 6. Help Menüsü
        help_menu = menubar.addMenu('Help')
        documentation_action = QAction(
            QIcon(os.path.join(PathFromOS().icons_path, 'documentation.png')),
            'Documentation',
            self,
        )
        licence_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'licence.png')), 'Licence', self)
        about_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'about.png')), 'About', self)
        update_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'update.png')), 'Update', self)

        help_menu.addAction(documentation_action)
        help_menu.addAction(licence_action)
        help_menu.addAction(about_action)
        help_menu.addSeparator()
        help_menu.addAction(update_action)

        # İşlevleri Fonksiyonlara Bağlama
        self.new_project_action.triggered.connect(self.new_project_dialog)
        self.new_project_action.triggered.connect(self.new_project)
        open_project_action.triggered.connect(self.open_project)
        new_file_action.triggered.connect(self.create_new_file_dialog)
        open_action.triggered.connect(self.open_file)
        save_action.triggered.connect(self.save_file)
        save_as_action.triggered.connect(self.save_file_as)
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        exit_action.triggered.connect(self.file_exit)
        find_action.triggered.connect(lambda _=False: self.show_search_dialog())
        cut_action.triggered.connect(self.cut_text)
        copy_action.triggered.connect(self.copy_text)
        paste_action.triggered.connect(self.paste_text)
        select_all_action.triggered.connect(self.select_all_text)
        self.run_code_action.triggered.connect(self.run_code)
        self.run_all_code_action.triggered.connect(self.run_all_code)
        self.execute_current_line_action.triggered.connect(self.execute_current_line_in_active_editor)
        self.stop_execution_action.triggered.connect(self.stop_code)
        reset_ui_action.triggered.connect(self.reset_ui)
        set_default_ui_action.triggered.connect(self.set_default_ui)
        preferences_action.triggered.connect(self.open_settings)
        update_action.triggered.connect(self.run_update)

        # Go To Line işlevini bağlama
        go_to_line_action.triggered.connect(self.show_go_to_line_dialog)

    def execute_current_line_in_active_editor(self):
        editor = None
        try:
            editor = self._current_tab_widget().currentWidget()
        except Exception:
            editor = None

        if editor is not None and hasattr(editor, "execute_current_line"):
            try:
                editor.execute_current_line()
            except Exception:
                pass

    def show_search_dialog(self, initial_text=None, show_replace=True):
        """
        Opens a modal search dialog and allows the user to search within the current document.
        """
        if isinstance(initial_text, bool):
            initial_text = None

        if initial_text is None:
            try:
                editor = self._current_editor() if hasattr(self, "_current_editor") else None
                if editor and editor.textCursor().hasSelection():
                    initial_text = editor.textCursor().selectedText().replace("\u2029", "\n")
            except Exception:
                initial_text = None

        dialog = SearchDialog(self, show_replace=show_replace)
        if initial_text:
            try:
                dialog.search_input.setText(str(initial_text))
                dialog.search_input.selectAll()
            except Exception:
                pass
        dialog.exec_()

    def zoom_in(self):
        """Yazı boyutunu büyütür."""
        self.settings.main_font_size += 1
        self.apply_font_size()

    def zoom_out(self):
        """YDecreases the font size."""
        if self.settings.main_font_size > 1:  # En küçük yazı boyutu kontrolü
            self.settings.main_font_size -= 1
        self.apply_font_size()

    def reset_zoom(self):
        """Yazı boyutunu varsayılan değere sıfırlar."""
        self.settings.main_font_size = 11  # Varsayılan font boyutunu ayarla
        self.apply_font_size()

    def apply_font_size(self):
        """Kod editöründeki yazı boyutunu günceller ve status barda gösterir."""
        for index in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(index)
            if isinstance(editor, CodeEditor):
                font = editor.font()
                font.setPointSize(self.settings.main_font_size)
                editor.setFont(font)

        # Durum çubuğundaki yazı boyutu bilgisini güncelle
        self.font_size_label.setText(f"Font Size: {self.settings.main_font_size}")

    def show_go_to_line_dialog(self):
        """Go To Line diyalogunu gösterir."""
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            dialog = GoToLineDialog(current_editor)
            dialog.exec_()

    def stop_code(self):
        # Kodun çalışmasını durdurmak için işlemleri buraya yazın
        print("Execution stopped FUNC.")

    def open_settings(self):
        """Preferences menüsüne tıklanınca settings_ui.py'yi açar."""
        try:
            import editor.settings.settings_ui as settings_ui_module
            import importlib
            importlib.reload(settings_ui_module)

            settings_ui_module.launch_settings()

        except Exception as e:
            import traceback
            error_msg = f"Error while opening settings UI:\n{str(e)}\n\n{traceback.format_exc()}"
            print("="*60)
            print("SETTINGS ERROR:")
            print(error_msg)
            print("="*60)
            nuke.message(error_msg)

    def run_update(self):
        """Run the bundled module updater."""
        status = self.refresh_dependency_status()
        if status and status.get("ok"):
            QMessageBox.information(self, "Update", "Everything is up to date.")
            return

        message_lines = ["Updates are needed."]
        if status:
            if status["missing"]:
                message_lines.append(f"Missing: {', '.join(status['missing'])}")
            if status["path_missing"]:
                message_lines.append("Modules path not set in sys.path.")
        QMessageBox.warning(self, "Update", "\n".join(message_lines))

        updater = SettingsWindow(editor_window=self)
        updater.show()

    def refresh_dependency_status(self):
        status = check_dependencies()
        tooltip_lines = []
        if status["missing"]:
            tooltip_lines.append(f"Missing: {', '.join(status['missing'])}")
        if status["path_missing"]:
            tooltip_lines.append("Modules path not set in sys.path.")
        if not tooltip_lines:
            tooltip_lines.append("All required modules are available.")

        if status["ok"]:
            self.dependency_status_label.setText("Deps: OK")
            self.dependency_status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
            self.dependency_status_dot.setStyleSheet("background-color: #5cb85c; border-radius: 5px;")
        else:
            if status["path_missing"]:
                self.dependency_status_label.setText("Deps: Fix path")
            else:
                self.dependency_status_label.setText("Deps: Update needed")
            self.dependency_status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
            self.dependency_status_dot.setStyleSheet("background-color: #d9534f; border-radius: 5px;")

        tooltip_text = "\n".join(tooltip_lines)
        self.dependency_status_label.setToolTip(tooltip_text)
        self.dependency_status_dot.setToolTip(tooltip_text)
        return status
