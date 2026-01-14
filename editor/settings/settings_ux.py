from PySide2.QtCore import Qt
from PySide2.QtWidgets import QToolBar

dock_names = [
    'workplace_dock',
    'outliner_dock',
    'header_dock',
    'nuke_ai_dock',
    'output_dock'
]

dock_default_positions = {
    'workplace_dock': Qt.RightDockWidgetArea,
    'outliner_dock': Qt.LeftDockWidgetArea,
    'header_dock': Qt.LeftDockWidgetArea,
    'nuke_ai_dock': Qt.BottomDockWidgetArea,
    'output_dock': Qt.BottomDockWidgetArea
}

def _set_chrome_visible(main_window, visible):
    status_bar = main_window.statusBar() if hasattr(main_window, "statusBar") else None
    if status_bar:
        status_bar.setVisible(visible)
    for toolbar in main_window.findChildren(QToolBar):
        toolbar.setVisible(visible)

def set_default_mode(main_window):
    """
    Default Mode:
    - Makes all dock widgets visible.
    - Places all dock widgets in their default positions.
    - Tabs the 'nuke_ai_dock' and 'output_dock' widgets at the bottom.
    """
    
    _set_chrome_visible(main_window, True)
    for dock_name, position in dock_default_positions.items():
        if hasattr(main_window, dock_name):
            dock_widget = getattr(main_window, dock_name)
            main_window.addDockWidget(position, dock_widget)
            dock_widget.setVisible(True)

    
    if hasattr(main_window, 'output_dock'):
        main_window.output_dock.raise_()


def set_expanded_mode(main_window):
    """
    Expanded Mode:
    - Makes all dock widgets visible.
    - Places Outliner and Header in the top-left corner, side by side.
    - Positions Workplace on the right side with full screen height.
    - Displays Console and Output at the bottom without tabs, separately.
    """

    
    _set_chrome_visible(main_window, True)
    for dock_name in dock_names:
        if hasattr(main_window, dock_name):
            dock_widget = getattr(main_window, dock_name)
            dock_widget.setVisible(True)
            dock_widget.setFloating(False)  

    
    if hasattr(main_window, 'outliner_dock') and hasattr(main_window, 'header_dock'):
        main_window.addDockWidget(Qt.LeftDockWidgetArea, main_window.outliner_dock)
        main_window.addDockWidget(Qt.LeftDockWidgetArea, main_window.header_dock)
        main_window.splitDockWidget(main_window.outliner_dock, main_window.header_dock, Qt.Horizontal)

    
    if hasattr(main_window, 'workplace_dock'):
        main_window.addDockWidget(Qt.RightDockWidgetArea, main_window.workplace_dock)

    
    if hasattr(main_window, 'output_dock'):
        main_window.addDockWidget(Qt.BottomDockWidgetArea, main_window.output_dock)

    
    main_window.output_dock.raise_()


def set_focus_mode(main_window):
    _set_chrome_visible(main_window, True)
    if hasattr(main_window, 'workplace_dock'):
        main_window.workplace_dock.setVisible(False)
        main_window.outliner_dock.setVisible(False)
        main_window.header_dock.setVisible(False)
        main_window.nuke_ai_dock.setVisible(False)
        main_window.output_dock.setVisible(False)
    else:
        return


def set_compact_mode(main_window):
    """
    Compact Mode:
    - Moves all widgets to the bottom as tabs.
    - Makes any hidden widgets visible.
    """

    
    _set_chrome_visible(main_window, True)
    base_dock = None

    for dock_name in dock_names:
        if hasattr(main_window, dock_name):
            dock_widget = getattr(main_window, dock_name)

            
            dock_widget.setVisible(True)

            if base_dock is None:
                
                base_dock = dock_widget
                main_window.addDockWidget(Qt.BottomDockWidgetArea, base_dock)
            else:
                
                main_window.tabifyDockWidget(base_dock, dock_widget)

    
    if base_dock:
        base_dock.raise_()

def set_saitama_mode(main_window):
    _set_chrome_visible(main_window, False)
    for dock_name in dock_names:
        if hasattr(main_window, dock_name):
            dock_widget = getattr(main_window, dock_name)
            dock_widget.setVisible(False)


ui_modes = {
    "Default Mode": set_default_mode,
    "Expanded Mode": set_expanded_mode,
    "Focus Mode": set_focus_mode,
    "Compact Mode": set_compact_mode,
    "Saitama": set_saitama_mode,
}
root_modes = {
    "Mumen Rider (Professional)": set_default_mode,
    "Saitama (immersive)": set_focus_mode,

}
