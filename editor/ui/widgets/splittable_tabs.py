

"""
Splittable Tab Widget - VS Code style split tabs
Allows dragging tabs to split vertically/horizontally or float as separate window
"""

from PySide2.QtWidgets import (
    QTabWidget, QTabBar, QSplitter, QWidget, QVBoxLayout,
    QApplication, QMainWindow, QLabel
)
from PySide2.QtCore import Qt, QPoint, QRect, Signal, QMimeData
from PySide2.QtGui import QPainter, QColor, QDrag, QPen


class DraggableTabBar(QTabBar):
    """Custom TabBar with drag-drop support"""

    tab_detach_requested = Signal(int, QPoint)  
    tab_move_requested = Signal(int, int)  

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setElideMode(Qt.ElideRight)
        self.setSelectionBehaviorOnRemove(QTabBar.SelectLeftTab)
        self.setMovable(True)
        self.setTabsClosable(True)

        self.drag_start_pos = QPoint()
        self.drag_initiated = False

    def mousePressEvent(self, event):
        """Start tracking drag"""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.drag_initiated = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Initiate drag when threshold exceeded"""
        if not (event.buttons() & Qt.LeftButton):
            return

        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        
        tab_index = self.tabAt(self.drag_start_pos)
        if tab_index == -1:
            return

        
        self.drag_initiated = True
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(tab_index))
        drag.setMimeData(mime_data)

        
        

        drop_action = drag.exec_(Qt.MoveAction)

        
        if drop_action == Qt.IgnoreAction:
            global_pos = self.mapToGlobal(event.pos())
            self.tab_detach_requested.emit(tab_index, global_pos)

    def dragEnterEvent(self, event):
        """Accept drag from same or other tab bars"""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle drop - reorder or merge tabs"""
        event.acceptProposedAction()


class SplittableTabWidget(QTabWidget):
    """
    TabWidget with split and float capabilities
    - Drag tabs to edges to split vertically/horizontally
    - Drag tabs outside to float
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        
        self.draggable_bar = DraggableTabBar(self)
        self.setTabBar(self.draggable_bar)

        
        self.draggable_bar.tab_detach_requested.connect(self.detach_tab)
        self.tabCloseRequested.connect(self.close_tab)

        
        self.split_indicator_rect = None
        self.split_direction = None  

        
        self.parent_splitter = None

    def close_tab(self, index):
        """Close tab at index"""
        widget = self.widget(index)
        if widget:
            self.removeTab(index)
            

    def detach_tab(self, index, position):
        """Detach tab and create floating window"""
        
        tab_text = self.tabText(index)
        tab_widget = self.widget(index)
        tab_tooltip = self.tabToolTip(index)

        if not tab_widget:
            return

        
        self.removeTab(index)

        
        floating_window = FloatingTabWindow(tab_text, tab_widget, position, self)
        floating_window.tab_reattach_requested.connect(self.reattach_tab)
        floating_window.show()

    def reattach_tab(self, window):
        """Reattach tab from floating window"""
        widget = window.main_widget
        title = window.windowTitle()

        
        index = self.addTab(widget, title)
        self.setCurrentIndex(index)

        
        window.close()

    def paintEvent(self, event):
        """Draw split indicators during drag"""
        super().paintEvent(event)

        if self.split_indicator_rect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            
            color = QColor(100, 150, 255, 80)
            painter.fillRect(self.split_indicator_rect, color)

            
            pen = QPen(QColor(100, 150, 255, 200), 2)
            painter.setPen(pen)
            painter.drawRect(self.split_indicator_rect)

            painter.end()


class FloatingTabWindow(QMainWindow):
    """Floating window for detached tabs"""

    tab_reattach_requested = Signal(object)  

    def __init__(self, title, widget, position, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        self.move(position)

        
        self.main_widget = widget

        
        self.setCentralWidget(widget)

        
        self.setWindowFlags(Qt.Window)

    def closeEvent(self, event):
        """Handle window close - reattach tab"""
        self.tab_reattach_requested.emit(self)
        event.accept()


class SplitTabContainer(QWidget):
    """
    Container for managing split tab widgets with QSplitter
    Handles vertical and horizontal splits
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        
        self.root_splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(self.root_splitter)

        
        self.initial_tab_widget = SplittableTabWidget(self)
        self.root_splitter.addWidget(self.initial_tab_widget)

        
        self.tab_widgets = [self.initial_tab_widget]

    def get_main_tab_widget(self):
        """Get the main (initial) tab widget"""
        return self.initial_tab_widget

    def split_tab_widget(self, tab_widget, direction):
        """
        Split a tab widget in given direction
        direction: 'horizontal' or 'vertical'
        """
        
        new_tab_widget = SplittableTabWidget(self)

        
        parent_splitter = tab_widget.parent()

        if direction == 'horizontal':
            
            if isinstance(parent_splitter, QSplitter) and parent_splitter.orientation() == Qt.Horizontal:
                splitter = parent_splitter
            else:
                splitter = QSplitter(Qt.Horizontal, self)
                index = parent_splitter.indexOf(tab_widget)
                parent_splitter.insertWidget(index, splitter)
                parent_splitter.widget(index + 1).setParent(splitter)
                splitter.addWidget(tab_widget)

            splitter.addWidget(new_tab_widget)

        elif direction == 'vertical':
            
            if isinstance(parent_splitter, QSplitter) and parent_splitter.orientation() == Qt.Vertical:
                splitter = parent_splitter
            else:
                splitter = QSplitter(Qt.Vertical, self)
                index = parent_splitter.indexOf(tab_widget)
                parent_splitter.insertWidget(index, splitter)
                parent_splitter.widget(index + 1).setParent(splitter)
                splitter.addWidget(tab_widget)

            splitter.addWidget(new_tab_widget)

        
        self.tab_widgets.append(new_tab_widget)

        return new_tab_widget
