from PySide2.QtWidgets import (
    QAction,
    QApplication,
    QBoxLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedLayout,
    QStyle,
    QTabBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide2.QtCore import Qt, Signal, QSize, QPoint, QRect, QMimeData
from PySide2.QtGui import QIcon, QPainter, QColor, QFont, QPixmap, QDrag, QPen, QCursor
from PySide2.QtSvg import QSvgWidget
import os
from editor.core import PathFromOS


class CustomTabBar(QTabBar):
    """Custom tab bar with drag-drop reordering and right-click menu support"""

    new_tab_requested = Signal()
    tab_detach_requested = Signal(int, QPoint)  
    tab_drop_requested = Signal(int, QPoint)  

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setElideMode(Qt.ElideRight)
        self.setSelectionBehaviorOnRemove(QTabBar.SelectLeftTab)
        self.setMovable(True)  
        self.setDrawBase(False)

        
        self.drag_start_pos = QPoint()
        self.drag_initiated = False

        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        """Show context menu on right-click"""
        menu = QMenu(self)

        
        new_tab_action = QAction("New Tab", self)
        new_tab_action.triggered.connect(self.new_tab_requested.emit)

        close_tab_action = QAction("Close Tab", self)
        close_other_tabs_action = QAction("Close Other Tabs", self)
        close_all_tabs_action = QAction("Close All Tabs", self)

        rename_tab_action = QAction("Rename Tab", self)

        
        detach_tab_action = QAction("Detach Tab (Float)", self)
        split_horizontal_action = QAction("Split Right", self)
        split_vertical_action = QAction("Split Below", self)

        
        tab_index = self.tabAt(position)

        if tab_index >= 0:
            tab_widget = self.parent()
            editor_app = tab_widget._get_editor_app() if hasattr(tab_widget, '_get_editor_app') else None
            if editor_app:
                close_tab_action.triggered.connect(lambda: editor_app.close_tab(tab_index, tab_widget))
                rename_tab_action.triggered.connect(lambda: editor_app.rename_tab(tab_index, tab_widget))
            close_other_tabs_action.triggered.connect(lambda: self.close_other_tabs(tab_index))
            close_all_tabs_action.triggered.connect(self.close_all_tabs)

            
            detach_tab_action.triggered.connect(lambda: self.detach_tab_at_index(tab_index))
            split_horizontal_action.triggered.connect(lambda: self.split_tab_at_index(tab_index, 'horizontal', 'right'))
            split_vertical_action.triggered.connect(lambda: self.split_tab_at_index(tab_index, 'vertical', 'bottom'))

            menu.addAction(new_tab_action)
            menu.addSeparator()
            menu.addAction(detach_tab_action)
            menu.addAction(split_horizontal_action)
            menu.addAction(split_vertical_action)
            menu.addSeparator()
            menu.addAction(rename_tab_action)
            menu.addAction(close_tab_action)
            menu.addAction(close_other_tabs_action)
            menu.addAction(close_all_tabs_action)
        else:
            
            menu.addAction(new_tab_action)

        menu.exec_(self.mapToGlobal(position))

    def mousePressEvent(self, event):
        """Start tracking drag"""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.drag_initiated = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Initiate drag to split or float when cursor leaves tab bar"""
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return

        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        if self.drag_initiated:
            return

        
        if self.rect().contains(event.pos()):
            super().mouseMoveEvent(event)
            return

        tab_index = self.tabAt(self.drag_start_pos)
        if tab_index == -1:
            super().mouseMoveEvent(event)
            return

        self.drag_initiated = True
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(tab_index))
        drag.setMimeData(mime_data)

        drop_action = drag.exec_(Qt.MoveAction)
        if drop_action == Qt.IgnoreAction:
            self.tab_drop_requested.emit(tab_index, QCursor.pos())

    def mouseReleaseEvent(self, event):
        self.drag_initiated = False
        super().mouseReleaseEvent(event)

    def detach_tab_at_index(self, index):
        """Request detach from parent widget"""
        global_pos = self.mapToGlobal(self.tabRect(index).center())
        self.tab_detach_requested.emit(index, global_pos)

    def split_tab_at_index(self, index, direction, side=None):
        """Request split from parent widget"""
        tab_widget = self.parent()
        if hasattr(tab_widget, 'split_tab'):
            tab_widget.split_tab(index, direction, side)

    def close_other_tabs(self, keep_index):
        """Close all tabs except the specified one"""
        tab_widget = self.parent()
        editor_app = tab_widget._get_editor_app() if hasattr(tab_widget, '_get_editor_app') else None
        if not editor_app:
            return
        
        for i in range(tab_widget.count() - 1, -1, -1):
            if i != keep_index:
                editor_app.close_tab(i, tab_widget)

    def close_all_tabs(self):
        """Close all tabs"""
        tab_widget = self.parent()
        editor_app = tab_widget._get_editor_app() if hasattr(tab_widget, '_get_editor_app') else None
        if not editor_app:
            return
        for i in range(tab_widget.count() - 1, -1, -1):
            editor_app.close_tab(i, tab_widget)


class WelcomeWidget(QWidget):
    """Welcome screen shown when no editor tabs are open."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons_layout_mode = None  # "horizontal" | "vertical"
        self.setup_ui()

    def _get_editor_app(self):
        win = self.window()
        if win and hasattr(win, "property") and win.property("codeeditor_v02_instance"):
            return win
        return win

    def setup_ui(self):
        """Setup the welcome screen UI."""
        stacked_layout = QStackedLayout(self)
        stacked_layout.setStackingMode(QStackedLayout.StackAll)

        center_layer = QWidget(self)
        bottom_layer = QWidget(self)
        center_layer.setAttribute(Qt.WA_TranslucentBackground, True)
        bottom_layer.setAttribute(Qt.WA_TranslucentBackground, True)
        # The centered logo layer should not block clicks/hover for the bottom actions.
        center_layer.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._bottom_layer = bottom_layer
        stacked_layout.addWidget(center_layer)
        stacked_layout.addWidget(bottom_layer)

        center_layout = QVBoxLayout(center_layer)
        center_layout.setContentsMargins(24, 24, 24, 24)
        center_layout.setSpacing(0)
        center_layout.addStretch(1)

        
        svg_path = os.path.join(PathFromOS().icons_path, "welcome_logo.svg")

        if os.path.exists(svg_path):
            
            
            svg_widget = QSvgWidget(svg_path)
            svg_widget.setFixedSize(350, 160)
            svg_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            center_layout.addWidget(svg_widget, 0, Qt.AlignCenter)
        else:
            
            fallback_label = QLabel("Python IDE")
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setStyleSheet("color: #FFA500; font-size: 24pt;")
            fallback_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            center_layout.addWidget(fallback_label, 0, Qt.AlignCenter)

        center_layout.addStretch(1)

        bottom_layout = QVBoxLayout(bottom_layer)
        bottom_layout.setContentsMargins(24, 24, 24, 24)
        bottom_layout.setSpacing(0)
        bottom_layout.addStretch(1)

        self.new_nuke_project_btn = QToolButton(bottom_layer)
        self.new_project_btn = QToolButton(bottom_layer)
        self.open_project_btn = QToolButton(bottom_layer)

        self.new_nuke_project_btn.setText("New Nuke Project")
        self.new_project_btn.setText("New Project")
        self.open_project_btn.setText("Open Project")

        project_icon_path = os.path.join(PathFromOS().icons_path, "new_project.png")
        new_project_icon_path = os.path.join(PathFromOS().icons_path, "welcome_new_project.svg")
        new_nuke_icon_path = os.path.join(PathFromOS().icons_path, "welcome_new_nuke.svg")
        open_project_icon_path = os.path.join(PathFromOS().icons_path, "welcome_open_project.svg")

        self.new_nuke_project_btn.setIcon(
            QIcon(new_nuke_icon_path)
            if os.path.exists(new_nuke_icon_path)
            else (QIcon(project_icon_path) if os.path.exists(project_icon_path) else self.style().standardIcon(QStyle.SP_FileIcon))
        )
        self.new_project_btn.setIcon(
            QIcon(new_project_icon_path)
            if os.path.exists(new_project_icon_path)
            else (QIcon(project_icon_path) if os.path.exists(project_icon_path) else self.style().standardIcon(QStyle.SP_FileIcon))
        )
        self.open_project_btn.setIcon(
            QIcon(open_project_icon_path)
            if os.path.exists(open_project_icon_path)
            else self.style().standardIcon(QStyle.SP_DirOpenIcon)
        )

        for btn in (self.new_nuke_project_btn, self.new_project_btn, self.open_project_btn):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setFixedHeight(34)
            btn.setIconSize(QSize(16, 16))

            # Side-by-side buttons fit better on typical window widths
            btn.setMinimumWidth(170)
            btn.setMaximumWidth(220)

        # Primary action
        self.open_project_btn.setProperty("primary", True)

        self._button_row = QBoxLayout(QBoxLayout.LeftToRight)
        self._button_row.setContentsMargins(0, 0, 0, 0)
        self._button_row.setSpacing(10)
        bottom_layout.addLayout(self._button_row)
        bottom_layout.addSpacing(14)

        self.new_nuke_project_btn.clicked.connect(self._on_new_nuke_project)
        self.new_project_btn.clicked.connect(self._on_new_project)
        self.open_project_btn.clicked.connect(self._on_open_project)

        self._update_button_layout()

        
        self.setStyleSheet("""
            WelcomeWidget {
                background-color: #1e1e1e;
            }

            WelcomeWidget QLabel {
                color: #cfd3d6;
                font-size: 10pt;
            }

            WelcomeWidget QToolButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #e7e7e7;
                border: none;
                border-radius: 8px;
                padding: 7px 14px;
            }

            WelcomeWidget QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }

            WelcomeWidget QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.03);
            }

            WelcomeWidget QToolButton[primary="true"] {
                background-color: rgba(255, 140, 0, 0.16);
            }

            WelcomeWidget QToolButton[primary="true"]:hover {
                background-color: rgba(255, 140, 0, 0.22);
            }

            WelcomeWidget QToolButton[primary="true"]:pressed {
                background-color: rgba(255, 140, 0, 0.12);
            }
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_button_layout()

    def _buttons_fit_horizontally(self):
        if not hasattr(self, "_bottom_layer") or not hasattr(self, "_button_row"):
            return True

        layout = self._bottom_layer.layout()
        if not layout:
            available_width = self._bottom_layer.width()
        else:
            margins = layout.contentsMargins()
            available_width = self._bottom_layer.width() - margins.left() - margins.right()

        required_width = (
            sum(
                max(btn.minimumWidth(), btn.minimumSizeHint().width())
                for btn in (self.new_nuke_project_btn, self.new_project_btn, self.open_project_btn)
            )
            + self._button_row.spacing() * 2
        )
        return available_width >= required_width

    def _rebuild_button_row(self, mode):
        while self._button_row.count():
            self._button_row.takeAt(0)

        if mode == "horizontal":
            self._button_row.setDirection(QBoxLayout.LeftToRight)
            self._button_row.addStretch(1)
            self._button_row.addWidget(self.new_nuke_project_btn)
            self._button_row.addWidget(self.new_project_btn)
            self._button_row.addWidget(self.open_project_btn)
            self._button_row.addStretch(1)
            return

        self._button_row.setDirection(QBoxLayout.TopToBottom)
        self._button_row.addWidget(self.new_nuke_project_btn, 0, Qt.AlignHCenter)
        self._button_row.addWidget(self.new_project_btn, 0, Qt.AlignHCenter)
        self._button_row.addWidget(self.open_project_btn, 0, Qt.AlignHCenter)

    def _update_button_layout(self):
        mode = "horizontal" if self._buttons_fit_horizontally() else "vertical"
        if mode == self._buttons_layout_mode:
            return
        self._buttons_layout_mode = mode
        self._rebuild_button_row(mode)

    def _on_new_nuke_project(self):
        editor_app = self._get_editor_app()
        if editor_app and hasattr(editor_app, "open_nuke_project_dialog"):
            editor_app.open_nuke_project_dialog()

    def _on_new_project(self):
        editor_app = self._get_editor_app()
        if editor_app and hasattr(editor_app, "new_project_dialog"):
            editor_app.new_project_dialog()

    def _on_open_project(self):
        editor_app = self._get_editor_app()
        if editor_app and hasattr(editor_app, "open_project"):
            editor_app.open_project()


class FloatingTabWindow(QMainWindow):
    """Floating window for detached tabs"""

    tab_reattach_requested = Signal(object, object)  
    window_closed = Signal(object)

    def __init__(self, title, widget, position, original_tab_widget, tab_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 700)
        self.move(position)

        
        self.main_widget = widget
        self.original_tab_widget = original_tab_widget
        self.tab_data = tab_data  

        
        if widget:
            widget.setParent(self)
            
            self.setCentralWidget(widget)
            
            widget.show()

        
        self.setWindowFlags(Qt.Window)

    def closeEvent(self, event):
        """Handle window close - reattach tab"""
        self.tab_reattach_requested.emit(self, self.main_widget)
        self.window_closed.emit(self)
        event.accept()


class CustomTabWidget(QTabWidget):
    """Enhanced tab widget with + button, drag-drop, split, float, and welcome screen"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor_app = parent if hasattr(parent, 'add_new_untitled_tab') else None
        self._floating_windows = []

        
        self.custom_tab_bar = CustomTabBar(self)
        self.setTabBar(self.custom_tab_bar)

        
        self.custom_tab_bar.new_tab_requested.connect(self.request_new_tab)

        
        self.custom_tab_bar.tab_detach_requested.connect(self.detach_tab)
        self.custom_tab_bar.tab_drop_requested.connect(self.handle_tab_drop)

        
        self.new_tab_button = QPushButton("+", self)
        self.new_tab_button.setFixedSize(22, 22)
        self.new_tab_button.setCursor(Qt.PointingHandCursor)
        self.new_tab_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #868e96;
                border: none;
                font-size: 14pt;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #FFA500;
            }
            QPushButton:pressed {
                color: #FF8C00;
            }
        """)
        self.new_tab_button.clicked.connect(self.request_new_tab)

        
        self.welcome_widget = WelcomeWidget()

        
        self.untitled_counter = 1

        
        self._updating_welcome = False

        
        self.tabCloseRequested.connect(self.on_tab_closed)
        self.currentChanged.connect(self.on_current_changed)
        self.currentChanged.connect(self.update_new_tab_button)

    def _get_editor_app(self):
        if self.editor_app:
            return self.editor_app

        window = self.window()
        if hasattr(window, 'add_new_untitled_tab'):
            self.editor_app = window
            return window

        return None

    def request_new_tab(self):
        """Request new tab from parent (EditorApp)"""
        editor_app = self._get_editor_app()
        if editor_app:
            editor_app.add_new_untitled_tab()

    def request_open_file(self):
        """Request open file from parent (EditorApp)"""
        editor_app = self._get_editor_app()
        if editor_app:
            editor_app.open_file()

    def on_tab_closed(self, index):
        """Handle tab close"""
        self.check_and_show_welcome()

    def on_current_changed(self, index):
        """Handle tab change"""
        self.check_and_show_welcome()

    def check_and_show_welcome(self):
        """Show welcome widget if no tabs are open"""
        
        if self._updating_welcome:
            return

        self._updating_welcome = True
        try:
            if self.count() == 0:
                
                if self.welcome_widget.parent() != self:
                    
                    self.blockSignals(True)
                    super().addTab(self.welcome_widget, "")
                    self.tabBar().setTabButton(0, QTabBar.RightSide, None)  
                    self.tabBar().setTabButton(0, QTabBar.LeftSide, None)
                    
                    self.tabBar().hide()
                    self.blockSignals(False)
            else:
                
                welcome_index = self.indexOf(self.welcome_widget)
                if welcome_index >= 0:
                    
                    self.blockSignals(True)
                    super().removeTab(welcome_index)
                    self.blockSignals(False)
                
                self.tabBar().show()
        finally:
            self._updating_welcome = False

    def get_next_untitled_name(self):
        """Generate next untitled_x name"""
        name = f"untitled_{self.untitled_counter}.py"
        self.untitled_counter += 1
        return name

    def addTab(self, widget, *args):
        """Override addTab to handle welcome widget"""
        
        if widget != self.welcome_widget:
            welcome_index = self.indexOf(self.welcome_widget)
            if welcome_index >= 0:
                
                self.blockSignals(True)
                super().removeTab(welcome_index)
                self.blockSignals(False)
            self.tabBar().show()

        result = super().addTab(widget, *args)
        self.update_new_tab_button()
        return result

    def removeTab(self, index):
        """Override removeTab to update button visibility"""
        super().removeTab(index)
        self.update_new_tab_button()

    def update_new_tab_button(self):
        """Update + button position (always visible)"""
        tab_bar = self.tabBar()

        
        self.new_tab_button.show()

        
        real_tab_count = self.count()
        if real_tab_count > 0 and self.indexOf(self.welcome_widget) >= 0:
            real_tab_count -= 1

        if real_tab_count == 0:
            
            x = 8
            y = 4
            self.new_tab_button.move(x, y)
        else:
            
            last_tab_index = self.count() - 1
            last_tab_rect = tab_bar.tabRect(last_tab_index)
            x = last_tab_rect.right() + 4
            y = last_tab_rect.top() + (last_tab_rect.height() - self.new_tab_button.height()) // 2
            self.new_tab_button.move(x, y)

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.update_new_tab_button()

    def showEvent(self, event):
        """Handle show events"""
        super().showEvent(event)
        self.update_new_tab_button()

    def handle_tab_drop(self, index, global_pos):
        """Handle drag-drop for split or floating tabs"""
        if self.widget(index) == self.welcome_widget:
            return

        editor_app = self._get_editor_app()
        if editor_app and hasattr(editor_app, 'handle_tab_drop'):
            editor_app.handle_tab_drop(self, index, global_pos)
            return

        local_pos = self.mapFromGlobal(global_pos)
        if not self.rect().contains(local_pos):
            self.detach_tab(index, global_pos)
            return

        edge = self._get_split_edge(local_pos)
        if not edge:
            return

        direction = 'horizontal' if edge in ("left", "right") else 'vertical'
        self.split_tab(index, direction, edge)

    def _get_split_edge(self, local_pos):
        """Determine which edge the drop is near for splitting"""
        tab_bar_rect = self.tabBar().geometry()
        if tab_bar_rect.contains(local_pos):
            return None

        edge_margin = 80
        rect = self.rect()
        if local_pos.x() <= rect.left() + edge_margin:
            return "left"
        if local_pos.x() >= rect.right() - edge_margin:
            return "right"
        if local_pos.y() <= rect.top() + edge_margin:
            return "top"
        if local_pos.y() >= rect.bottom() - edge_margin:
            return "bottom"

        return None

    def get_split_edge_for_global(self, global_pos):
        """Expose split edge detection for global cursor positions"""
        local_pos = self.mapFromGlobal(global_pos)
        return self._get_split_edge(local_pos)

    def detach_tab(self, index, position):
        """Detach tab and create floating window"""
        
        tab_text = self.tabText(index)
        tab_widget = self.widget(index)
        tab_tooltip = self.tabToolTip(index)
        tab_icon = self.tabIcon(index)  

        if not tab_widget or tab_widget == self.welcome_widget:
            return

        
        tab_data = {
            'text': tab_text,
            'tooltip': tab_tooltip,
            'icon': tab_icon,
            'widget': tab_widget
        }

        
        self.removeTab(index)

        
        floating_window = FloatingTabWindow(tab_text, tab_widget, position, self, tab_data)
        floating_window.tab_reattach_requested.connect(self.reattach_tab)
        floating_window.window_closed.connect(self._on_floating_window_closed)
        floating_window.show()
        self._floating_windows.append(floating_window)

    def reattach_tab(self, window, widget):
        """Reattach tab from floating window"""
        
        tab_data = window.tab_data

        
        index = self.addTab(widget, tab_data.get('icon'), tab_data.get('text'))

        
        tooltip = tab_data.get('tooltip', '')
        if tooltip:
            self.setTabToolTip(index, tooltip)

        self.setCurrentIndex(index)

        
        if window in self._floating_windows:
            self._floating_windows.remove(window)

    def _on_floating_window_closed(self, window):
        if window in self._floating_windows:
            self._floating_windows.remove(window)

    def split_tab(self, index, direction, side=None):
        """Split tab in given direction (horizontal/vertical)"""
        
        
        editor_app = self._get_editor_app()
        if editor_app:
            editor_app.split_editor_tab(index, direction, side, self)
        else:
            return
