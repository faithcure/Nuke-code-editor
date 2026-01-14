import os
import importlib
from PySide2.QtWidgets import QToolButton, QAction, QToolBar, QWidget, QSizePolicy, QMenu
from PySide2.QtCore import QSize, Qt
from PySide2.QtGui import QIcon
import editor.core
import editor.nlink
import editor.settings.settings_ux as settings_ux
import editor.nodes.crtNode
importlib.reload(editor.nodes.crtNode)
importlib.reload(editor.core)
importlib.reload(editor.nlink)
importlib.reload(settings_ux)
from editor.nlink import update_nuke_functions
from editor.core import PathFromOS, CodeEditorSettings
from editor.nodes.crtNode import createNodesCode

pathFromOS = PathFromOS()
settings = CodeEditorSettings()

class MainToolbar:
    """
    MainToolbar is responsible for creating and managing the toolbar in the main application window.
    It provides a set of actions such as running code, saving files, searching within code, updating functions,
    and more.
    """

    @staticmethod
    def create_toolbar(parent):
        """
        Creates the main toolbar and adds necessary buttons and actions to it.
        Args:
            parent: The parent widget to which the toolbar is attached.
        """
        
        toolbar = parent.addToolBar("MAIN TOOLBAR")
        parent.addToolBar(settings.setToolbar_area, toolbar)  

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  

        
        toolbar.setIconSize(settings.toolbar_icon_size)
        toolbar.setStyleSheet("QToolBar { spacing: 4px; }")
        toolbar.setMovable(True)
        parent.addToolBar(Qt.TopToolBarArea, toolbar)

        def add_group_separator():
            separator = QWidget()
            separator.setFixedWidth(10)
            toolbar.addWidget(separator)

        
        new_file_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'new_file.png')), '', parent)
        new_file_action.setToolTip("New File")
        new_file_action.triggered.connect(parent.create_new_file_dialog)
        toolbar.addAction(new_file_action)

        open_file_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'directory.svg')), '', parent)
        open_file_action.setToolTip("Open File")
        open_file_action.triggered.connect(parent.open_file)
        toolbar.addAction(open_file_action)

        save_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'save.svg')), '', parent)
        save_action.setToolTip("Save Current File")
        save_action.triggered.connect(parent.save_file)
        toolbar.addAction(save_action)

        add_group_separator()

        run_selection_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'run_selection.svg')), '', parent)
        run_selection_action.setToolTip("Run Selection")
        run_selection_action.triggered.connect(parent.run_selected_code)
        toolbar.addAction(run_selection_action)

        run_all_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'play.svg')), '', parent)
        run_all_action.setToolTip("Run All Code")
        run_all_action.triggered.connect(parent.run_all_code)
        toolbar.addAction(run_all_action)

        stop_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'close_01.svg')), '', parent)
        stop_action.setToolTip("Stop Execution")
        stop_action.triggered.connect(parent.stop_code)
        toolbar.addAction(stop_action)

        add_group_separator()

        search_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'search.svg')), '', parent)
        search_action.setToolTip("Search in Code")
        search_action.triggered.connect(parent.show_search_dialog)
        toolbar.addAction(search_action)

        go_to_line_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'goto_line.svg')), '', parent)
        go_to_line_action.setToolTip("Go To Line")
        go_to_line_action.triggered.connect(parent.show_go_to_line_dialog)
        toolbar.addAction(go_to_line_action)

        add_group_separator()

        
        update_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'update.svg')), '', parent)
        update_action.setToolTip("Update Nuke Functions List (NLink!)")
        update_action.triggered.connect(update_nuke_functions)
        toolbar.addAction(update_action)

        
        
        parent._create_nodes_instance = createNodesCode()

        
        create_node_action = QAction(QIcon(os.path.join(pathFromOS.icons_path, 'crt_node.svg')), '', parent)
        create_node_action.setToolTip("Create Node Wizard")
        create_node_action.triggered.connect(parent._create_nodes_instance.createNodeMenu)
        toolbar.addAction(create_node_action)

        add_group_separator()
        
        
        
        
        

        toolbar.addSeparator()

        
        toolbar.addWidget(spacer)

        
        def create_expand_menu():
            """
            Creates a dropdown menu for switching UI modes.
            Returns:
                QMenu: The constructed menu with UI mode options.
            """
            mode_menu = QMenu(parent)
            for mode_name, function in settings_ux.ui_modes.items():  
                action = mode_menu.addAction(mode_name)
                action.triggered.connect(lambda checked=False, func=function: func(parent))
            return mode_menu

        
        ui_menu = create_expand_menu()

        ui_button = QToolButton(toolbar)
        ui_button.setIcon(QIcon(os.path.join(pathFromOS.icons_path, 'ux_design.svg')))
        ui_button.setToolTip("Switch UI Modes")
        ui_button.setPopupMode(QToolButton.InstantPopup)
        ui_button.setMenu(ui_menu)
        toolbar.addWidget(ui_button)

        
        def adjust_expand_layout(orientation):
            """
            Adjusts the layout and icon of the UI button based on toolbar orientation.
            Args:
                orientation (Qt.Orientation): The orientation of the toolbar.
            """
            if orientation == Qt.Vertical:
                ui_button.setIcon(QIcon(os.path.join(PathFromOS().icons_path, 'ux_design.svg')))
            else:
                ui_button.setIcon(QIcon(os.path.join(PathFromOS().icons_path, 'ux_design.svg')))

        
        toolbar.orientationChanged.connect(adjust_expand_layout)

        
        clear_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'clear.svg')), '', parent)
        clear_action.setToolTip("Clear Output")
        clear_action.triggered.connect(parent.clear_output)
        toolbar.addAction(clear_action)

        
        settings_action = QAction(QIcon(os.path.join(PathFromOS().icons_path, 'settings.png')), '', parent)
        settings_action.setToolTip("Settings")
        settings_action.triggered.connect(parent.open_settings)
        toolbar.addAction(settings_action)



        
        toolbar.orientationChanged.connect(lambda orientation: parent.update_toolbar_spacer(orientation, spacer))
