import nuke
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import os
from editor.core import PathFromOS


class MacroPanelBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.icon_path = PathFromOS().icons_path  
        self.setWindowTitle("Nuke Panel Builder")
        self.resize(1400, 800)

        
        self.canvas_widgets = []  
        self.selected_widget = None  
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.selected_knobs = []

        
        self.installEventFilter(self)

        self.create_tool_bar()

        self.content_splitter = QSplitter(Qt.Horizontal)
        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()
        self.main_layout.addWidget(self.content_splitter)
        self.create_status_bar()

    def create_tool_bar(self):
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        
        generate_icon_path = os.path.join(self.icon_path, "run-icon.svg")
        generate_action = toolbar.addAction(QIcon(generate_icon_path), "Generate Python Code")
        generate_action.triggered.connect(self.generate_code)

        
        clear_icon_path = os.path.join(self.icon_path, "clear-codes-icon.svg")
        clear_action = toolbar.addAction(QIcon(clear_icon_path), "Clear Codes")
        clear_action.triggered.connect(self.clear_codes)

    def create_left_panel(self):
        left_dock = QDockWidget("Widget Box", self)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        
        self.tab_widget = QTabWidget()

        
        knobs_tab = QWidget()
        knobs_layout = QVBoxLayout(knobs_tab)

        
        self.knobs_tree = QTreeWidget()
        self.knobs_tree.setHeaderHidden(True)
        self.knobs_tree.setIconSize(QSize(16, 16))
        self.populate_knobs_tree(self.knobs_tree)
        knobs_layout.addWidget(self.knobs_tree)

        
        layouts_tab = QWidget()
        layouts_layout = QVBoxLayout(layouts_tab)

        
        self.layouts_tree = QTreeWidget()
        self.layouts_tree.setHeaderHidden(True)
        self.layouts_tree.setIconSize(QSize(16, 16))
        self.populate_layouts_tree()
        layouts_layout.addWidget(self.layouts_tree)

        
        self.tab_widget.addTab(knobs_tab, "Knobs")
        self.tab_widget.addTab(layouts_tab, "Layouts")

        left_layout.addWidget(self.tab_widget)

        
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)

        filter_top_layout = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by name...")
        filter_top_layout.addWidget(self.filter_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Types", "Input", "Color", "Transform", "File", "Container", "Custom"])
        filter_top_layout.addWidget(self.type_combo)
        filter_layout.addLayout(filter_top_layout)

        
        self.knob_preview_group = QGroupBox()
        self.knob_preview_layout = QVBoxLayout()

        self.knob_preview_label = QLabel()
        self.knob_preview_label.setAlignment(Qt.AlignCenter)
        self.knob_preview_layout.addWidget(self.knob_preview_label)

        self.knob_preview_name_label = QLabel()
        self.knob_preview_name_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.knob_preview_layout.addWidget(self.knob_preview_name_label)

        self.knob_preview_type_label = QLabel()
        self.knob_preview_layout.addWidget(self.knob_preview_type_label)

        self.knob_preview_group.setLayout(self.knob_preview_layout)
        filter_layout.addWidget(self.knob_preview_group)

        
        self.filter_edit.textChanged.connect(self.apply_filters)
        self.type_combo.currentTextChanged.connect(self.apply_filters)

        left_layout.addWidget(filter_widget)

        left_widget.setLayout(left_layout)
        left_dock.setWidget(left_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)

    def create_center_panel(self):
        self.center_widget = QWidget()
        self.center_layout = QVBoxLayout(self.center_widget)

        
        self.drop_frame = QFrame()
        self.drop_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.drop_frame.setMinimumSize(400, 500)
        self.drop_frame.setAcceptDrops(True)

        
        class GridFrame(QFrame):
            def paintEvent(self, event):
                super().paintEvent(event)
                painter = QPainter(self)
                painter.setPen(QPen(QColor(100, 100, 100, 50), 1, Qt.DashLine))

                
                for x in range(0, self.width(), 20):
                    painter.drawLine(x, 0, x, self.height())

                
                for y in range(0, self.height(), 20):
                    painter.drawLine(0, y, self.width(), y)

        self.drop_frame = GridFrame()
        self.drop_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #444;
            }
        """)

        
        def dragEnterEvent(event):
            if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
                event.accept()
            else:
                event.ignore()

        def dropEvent(event):
            pos = event.pos()
            data = event.mimeData()
            item_data = self.get_layout_data_from_mime(data)
            if item_data:
                
                if "class" in item_data:
                    
                    self.create_layout_widget(item_data, pos)
                else:
                    
                    self.create_knob_widget(item_data, pos)
            event.accept()

        self.drop_frame.dragEnterEvent = dragEnterEvent
        self.drop_frame.dropEvent = dropEvent

        self.center_layout.addWidget(self.drop_frame)
        self.content_splitter.addWidget(self.center_widget)

    def get_layout_data_from_mime(self, mime_data):
        
        encoded_data = mime_data.data("application/x-qabstractitemmodeldatalist")
        stream = QDataStream(encoded_data, QIODevice.ReadOnly)
        while not stream.atEnd():
            row = stream.readInt32()
            col = stream.readInt32()
            item_data = {}
            for role in range(stream.readInt32()):
                key = stream.readInt32()
                value = stream.readQVariant()
                if key == Qt.UserRole:
                    return value
        return None

    def create_right_panel(self):
        right_dock = QDockWidget("Properties & Code", self)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(2)

        
        self.right_tabs = QTabWidget()

        
        properties_tab = QWidget()
        properties_layout = QVBoxLayout(properties_tab)

        
        self.property_table = QTableWidget()
        self.property_table.setColumnCount(2)
        self.property_table.setHorizontalHeaderLabels(["Property", "Value"])

        
        self.property_table.setShowGrid(False)  
        self.property_table.setAlternatingRowColors(True)  
        self.property_table.horizontalHeader().setStretchLastSection(True)
        self.property_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.property_table.horizontalHeader().setDefaultSectionSize(140)
        self.property_table.verticalHeader().setVisible(False)
        self.property_table.setSelectionBehavior(QTableWidget.SelectRows)

        
        self.property_table.setStyleSheet("""
            QTableWidget {
                background-color: #282828;
                alternate-background-color: #2e2e2e;
                color: #d8d8d8;
                border: none;
                font-size: 11px;
                gridline-color: transparent;
            }

            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #383838;
            }

            QTableWidget::item:selected {
                background-color: #4b5052;
                color: #ffffff;
            }

            QHeaderView::section {
                background-color: #333333;
                color: #d8d8d8;
                padding: 4px;
                border: none;
                border-bottom: 2px solid #444444;
                font-weight: bold;
            }

            QScrollBar:vertical {
                background-color: #282828;
                width: 12px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background-color: #444444;
                min-height: 20px;
                border-radius: 2px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #555555;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        properties_layout.addWidget(self.property_table)

        
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)

        self.code_preview = QTextEdit()
        self.code_preview.setReadOnly(True)
        self.code_preview.setFont(QFont("Consolas", 10))
        self.code_preview.setPlaceholderText("Generated Python code will appear here...")
        self.code_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                font-family: Consolas, monospace;
            }
        """)
        code_layout.addWidget(self.code_preview)

        
        self.right_tabs.addTab(properties_tab, "Properties")
        self.right_tabs.addTab(code_tab, "Code Preview")

        right_layout.addWidget(self.right_tabs)
        right_widget.setLayout(right_layout)
        right_dock.setWidget(right_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)

    def update_property_editor(self, knob_data):
        """Updates the property editor based on the selected knob."""
        if not knob_data:
            self.property_table.setRowCount(0)
            return

        
        properties = self.get_knob_properties(knob_data["type"])
        self.property_table.setRowCount(len(properties))

        for row, (prop_name, prop_data) in enumerate(properties.items()):
            
            name_item = QTableWidgetItem(prop_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  
            self.property_table.setItem(row, 0, name_item)

            
            value_widget = self.create_property_widget(prop_data)
            if value_widget:
                self.property_table.setCellWidget(row, 1, value_widget)

    def create_property_widget(self, prop_data):
        """Create the appropriate widget for a property type."""
        prop_type = prop_data["type"]
        default_value = prop_data["default"]

        if prop_type == "string":
            widget = QLineEdit()
            widget.setText(str(default_value))
            widget.textChanged.connect(lambda: self.on_property_changed(widget))
            return widget

        elif prop_type == "bool":
            widget = QWidget()
            layout = QHBoxLayout(widget)
            checkbox = QCheckBox()
            checkbox.setChecked(default_value)
            checkbox.stateChanged.connect(lambda: self.on_property_changed(checkbox))
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            return widget

        elif prop_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(-1e6, 1e6)
            widget.setValue(default_value)
            widget.valueChanged.connect(lambda: self.on_property_changed(widget))
            return widget

        elif prop_type == "color":
            widget = QPushButton()
            widget.setStyleSheet(f"background-color: {default_value};")
            widget.clicked.connect(lambda: self.show_color_dialog(widget))
            return widget

        elif prop_type == "file":
            widget = QWidget()
            layout = QHBoxLayout(widget)
            line_edit = QLineEdit(default_value)
            browse_btn = QPushButton("...")
            browse_btn.clicked.connect(lambda: self.show_file_dialog(line_edit))
            layout.addWidget(line_edit)
            layout.addWidget(browse_btn)
            return widget

        return None

    def on_property_changed(self, widget):
        """Called when a property value changes."""
        try:
            
            if isinstance(widget, QLineEdit):
                value = widget.text()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()
            else:
                return

            
            self.update_knob_property(widget, value)
        except Exception as e:
            pass

    def update_knob_property(self, widget, value):
        """Updates the property of the selected widget"""
        if not self.selected_widget:
            return

        
        for widget_data in self.canvas_widgets:
            if widget_data.get("widget") == self.selected_widget:
                
                if "properties" not in widget_data:
                    widget_data["properties"] = {}

                
                for row in range(self.property_table.rowCount()):
                    cell_widget = self.property_table.cellWidget(row, 1)
                    if cell_widget == widget or (hasattr(cell_widget, 'layout') and
                                                  cell_widget.layout() and
                                                  cell_widget.layout().itemAt(0) and
                                                  cell_widget.layout().itemAt(0).widget() == widget):
                        property_name = self.property_table.item(row, 0).text()
                        widget_data["properties"][property_name] = value
                        break
                break

    def show_color_dialog(self, button):
        """Show the color picker dialog."""
        color = QColorDialog.getColor()
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()};")
            self.update_knob_property(button, color.name())

    def show_file_dialog(self, line_edit):
        """Show the file picker dialog."""
        file_path, _ = QFileDialog.getOpenFileName()
        if file_path:
            line_edit.setText(file_path)
            self.update_knob_property(line_edit, file_path)

    def get_knob_properties(self, knob_type):
        """Return available properties for the knob type."""
        common_properties = {
            "Name": {"type": "string", "default": ""},
            "Label": {"type": "string", "default": ""},
            "Tooltip": {"type": "string", "default": ""},
            "Hidden": {"type": "bool", "default": False},
        }

        type_specific_properties = {
            "string_knob": {
                "Default Value": {"type": "string", "default": ""},
                "Multiline": {"type": "bool", "default": False},
            },
            "number_knob": {
                "Default Value": {"type": "float", "default": 0.0},
                "Min": {"type": "float", "default": -1e6},
                "Max": {"type": "float", "default": 1e6},
                "Step": {"type": "float", "default": 1.0},
            },
            "color_knob": {
                "Default Color": {"type": "color", "default": "#000000"},
                "Alpha": {"type": "bool", "default": False},
            },
            "button_knob": {
                "Command": {"type": "string", "default": ""},
                "Icon": {"type": "file", "default": ""},
            },
        }

        
        properties = common_properties.copy()
        if knob_type in type_specific_properties:
            properties.update(type_specific_properties[knob_type])

        return properties

    def apply_filters(self):
        filter_text = self.filter_edit.text().lower()
        type_filter = self.type_combo.currentText()

        root = self.knobs_tree.invisibleRootItem()
        for i in range(root.childCount()):
            category_item = root.child(i)
            category_visible = False

            if type_filter == "All Types" or category_item.text(0) == type_filter:
                for j in range(category_item.childCount()):
                    knob_item = category_item.child(j)
                    knob_visible = filter_text in knob_item.text(0).lower()
                    knob_item.setHidden(not knob_visible)
                    if knob_visible:
                        category_visible = True

            category_item.setHidden(not category_visible)

    def create_status_bar(self):
        status_bar = self.statusBar()
        status_bar.showMessage("Ready")

    def populate_knobs_tree(self, tree):
        right_arrow = os.path.join(self.icon_path, "right-arrow.svg").replace("\\", "/")
        down_arrow = os.path.join(self.icon_path, "down-arrow.svg").replace("\\", "/")

        try:
            import nuke
            all_knob_types = nuke.knobTypes()
        except:
            all_knob_types = {
                "Basic Input": {
                    "icon": "basic_input",
                    "knobs": [
                        ("String_Knob", "string_knob"),
                        ("Int_Knob", "number_knob"),
                        ("Double_Knob", "number_knob"),
                        ("Boolean_Knob", "button_knob"),
                        ("Password_Knob", "string_knob"),
                        ("Text_Knob", "string_knob"),
                        ("Multiline_Eval_String_Knob", "string_knob")
                    ]
                },
                "Color & Transform": {
                    "icon": "color_transform",
                    "knobs": [
                        ("Color_Knob", "color_knob"),
                        ("AColor_Knob", "color_knob"),
                        ("XY_Knob", "transform_knob"),
                        ("XYZ_Knob", "transform_knob"),
                        ("UV_Knob", "transform_knob"),
                        ("WH_Knob", "transform_knob"),
                        ("Box3_Knob", "transform_knob"),
                        ("Scale_Knob", "transform_knob"),
                        ("Format_Knob", "transform_knob")
                    ]
                },
                "Array & Vector": {
                    "icon": "array_vector",
                    "knobs": [
                        ("Array_Knob", "array_vector"),
                        ("BBox_Knob", "array_vector"),
                        ("ColorChip_Knob", "color_knob"),
                        ("Channel_Knob", "array_vector"),
                        ("ChannelMask_Knob", "array_vector"),
                        ("Link_Knob", "array_vector")
                    ]
                },
                "Button & Menu": {
                    "icon": "button_knob",
                    "knobs": [
                        ("PyScript_Knob", "button_knob"),
                        ("PyCustom_Knob", "button_knob"),
                        ("Enumeration_Knob", "button_knob"),
                        ("Pulldown_Knob", "button_knob"),
                        ("Radio_Knob", "button_knob"),
                        ("Button_Knob", "button_knob")
                    ]
                }
            }

        tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: #2d2d2d;
                border: none;
                color: #e0e0e0;
            }}
            QTreeWidget::item {{
                padding: 4px;
                border: none;
            }}
            QTreeWidget::item:hover {{
                background-color: #3d3d3d;
            }}
            QTreeWidget::item:selected {{
                background-color: #4b4b4b;
            }}
            QTreeView::branch {{
                background: transparent;
                border: none;
            }}
            QTreeView::branch:has-siblings {{
                border-image: none;
                background: transparent;
            }}
            QTreeView::branch:has-siblings:adjoins-item {{
                border-image: none;
                background: transparent;
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url({right_arrow});
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                border-image: none;
                image: url({down_arrow});
            }}
        """)

        tree.setRootIsDecorated(True)
        tree.setExpandsOnDoubleClick(True)

        for category, data in all_knob_types.items():
            category_item = QTreeWidgetItem(tree)
            category_item.setText(0, category)
            category_icon_path = self.get_icon_path(data["icon"])
            category_item.setIcon(0, QIcon(category_icon_path))

            for knob_name, icon_key in data["knobs"]:
                knob_item = QTreeWidgetItem(category_item)

                if knob_name == "String_Knob":
                    knob_item.setText(0, "Text Field")
                elif knob_name == "Int_Knob":
                    knob_item.setText(0, "Integer Field")
                elif knob_name == "Double_Knob":
                    knob_item.setText(0, "Float Field")
                elif knob_name == "Boolean_Knob":
                    knob_item.setText(0, "Checkbox")
                elif knob_name == "Password_Knob":
                    knob_item.setText(0, "Password Field")
                elif knob_name == "Text_Knob":
                    knob_item.setText(0, "Multiline Text")
                elif knob_name == "Multiline_Eval_String_Knob":
                    knob_item.setText(0, "Multiline Expression")
                elif knob_name == "Color_Knob":
                    knob_item.setText(0, "Color Picker")
                elif knob_name == "AColor_Knob":
                    knob_item.setText(0, "Advanced Color Picker")
                elif knob_name == "XY_Knob":
                    knob_item.setText(0, "XY Coordinate")
                elif knob_name == "XYZ_Knob":
                    knob_item.setText(0, "XYZ Coordinate")
                elif knob_name == "UV_Knob":
                    knob_item.setText(0, "UV Coordinate")
                elif knob_name == "WH_Knob":
                    knob_item.setText(0, "Width/Height")
                elif knob_name == "Box3_Knob":
                    knob_item.setText(0, "3D Bounding Box")
                elif knob_name == "Scale_Knob":
                    knob_item.setText(0, "Scale")
                elif knob_name == "Format_Knob":
                    knob_item.setText(0, "Format")
                elif knob_name == "Array_Knob":
                    knob_item.setText(0, "Array")
                elif knob_name == "BBox_Knob":
                    knob_item.setText(0, "Bounding Box")
                elif knob_name == "ColorChip_Knob":
                    knob_item.setText(0, "Color Chip")
                elif knob_name == "Channel_Knob":
                    knob_item.setText(0, "Channel")
                elif knob_name == "ChannelMask_Knob":
                    knob_item.setText(0, "Channel Mask")
                elif knob_name == "Link_Knob":
                    knob_item.setText(0, "Link")
                elif knob_name == "PyScript_Knob":
                    knob_item.setText(0, "Python Script")
                elif knob_name == "PyCustom_Knob":
                    knob_item.setText(0, "Python Custom")
                elif knob_name == "Enumeration_Knob":
                    knob_item.setText(0, "Dropdown")
                elif knob_name == "Pulldown_Knob":
                    knob_item.setText(0, "Pulldown")
                elif knob_name == "Radio_Knob":
                    knob_item.setText(0, "Radio Button")
                elif knob_name == "Button_Knob":
                    knob_item.setText(0, "Button")
                else:
                    knob_item.setText(0, knob_name)

                knob_icon_path = self.get_icon_path(icon_key)
                knob_item.setIcon(0, QIcon(knob_icon_path))
                knob_item.setData(1, Qt.UserRole, {
                    "name": knob_item.text(0),
                    "type": icon_key,
                    "nuke_class": knob_name,
                    "icon_path": os.path.join(self.icon_path, f"{icon_key}.svg")
                })

        
        self.knobs_tree.setDragEnabled(True)
        self.knobs_tree.setDragDropMode(QAbstractItemView.DragOnly)

        
        self.knobs_tree.currentItemChanged.connect(self.update_knob_preview)
        self.knobs_tree.itemDoubleClicked.connect(self.add_knob_to_center)

    def populate_layouts_tree(self):
        
        self.layouts_tree.setStyleSheet(self.knobs_tree.styleSheet())

        layouts = {
            "Containers": {
                "icon": "container_icon.svg",
                "items": [
                    ("Tab Layout", "tab_layout_icon.svg"),
                    ("Group Box", "group_box_icon.svg"),
                    ("Collapsible Frame", "collapsible_frame_icon.svg")
                ]
            },
            "Basic Layouts": {
                "icon": "basic_layout_icon.svg",
                "items": [
                    ("Vertical Layout", "vertical_layout_icon.svg"),
                    ("Horizontal Layout", "horizontal_layout_icon.svg"),
                    ("Grid Layout", "grid_layout_icon.svg")
                ]
            }
        }

        for category, data in layouts.items():
            category_item = QTreeWidgetItem(self.layouts_tree)
            category_item.setText(0, category)
            category_icon = QIcon(os.path.join(self.icon_path, data["icon"]))
            category_item.setIcon(0, category_icon)

            for item_name, icon_file in data["items"]:
                layout_item = QTreeWidgetItem(category_item)
                layout_item.setText(0, item_name)
                layout_icon = QIcon(os.path.join(self.icon_path, icon_file))
                layout_item.setIcon(0, layout_icon)
                layout_item.setData(1, Qt.UserRole, {
                    "name": item_name,
                    "type": item_name.lower().replace(" ", "_"),
                    "class": self.get_layout_class(item_name)
                })

        
        self.layouts_tree.setDragEnabled(True)
        self.layouts_tree.setDragDropMode(QAbstractItemView.DragOnly)

        
        self.layouts_tree.itemDoubleClicked.connect(self.add_layout_to_center)

    def get_layout_class(self, layout_type):
        """Return the appropriate class for the layout type."""
        
        layout_classes = {
            "tab_layout": QTabWidget,
            "group_box": QGroupBox,
            "collapsible_frame": QFrame,
            "vertical_layout": QVBoxLayout,
            "horizontal_layout": QHBoxLayout,
            "grid_layout": QGridLayout,
            "form_layout": QFormLayout
        }

        
        normalized_type = layout_type.lower().replace(" ", "_")
        return layout_classes.get(normalized_type, QVBoxLayout)  

    def add_knob_to_center(self, item):
        """Double-click to add knob to center"""
        if not item or not item.parent():  
            return

        knob_data = item.data(1, Qt.UserRole)
        if knob_data and "nuke_class" in knob_data:
            
            widget = self.create_knob_widget(knob_data)
            if widget:
                
                drop_frame_rect = self.drop_frame.rect()
                widget_rect = widget.rect()
                center_pos = QPoint(
                    (drop_frame_rect.width() - widget_rect.width()) // 2,
                    (drop_frame_rect.height() - widget_rect.height()) // 2
                )
                widget.move(center_pos)

    def add_layout_to_center(self, item):
        """Add a layout via double-click."""
        if not item or not item.parent():  
            return

        layout_data = item.data(1, Qt.UserRole)
        if layout_data:
            
            widget = self.create_layout_widget(layout_data)
            if widget:
                
                drop_frame_rect = self.drop_frame.rect()
                widget_rect = widget.rect()
                center_pos = QPoint(
                    (drop_frame_rect.width() - widget_rect.width()) // 2,
                    (drop_frame_rect.height() - widget_rect.height()) // 2
                )
                widget.move(center_pos)

    def create_knob_widget(self, knob_data, pos=None):
        """Creates a REAL visual widget for the knob on canvas"""
        if not knob_data:
            pass
            return None

        try:
            knob_name = knob_data.get("name", "Knob")
            knob_type = knob_data.get("type", "string_knob")
            nuke_class = knob_data.get("nuke_class", "String_Knob")

            
            container = QWidget(self.drop_frame)
            container.setMinimumSize(300, 60)
            container.setStyleSheet("""
                QWidget {
                    background-color: rgba(50, 50, 50, 230);
                    border: 2px solid #555;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)

            
            layout = QHBoxLayout(container)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(10)

            
            label = QLabel(knob_name + ":")
            label.setStyleSheet("color: #ddd; font-weight: bold; min-width: 80px;")
            layout.addWidget(label)

            
            actual_widget = None

            if nuke_class == "String_Knob" or nuke_class == "Password_Knob":
                actual_widget = QLineEdit()
                actual_widget.setPlaceholderText("Enter text...")
                if nuke_class == "Password_Knob":
                    actual_widget.setEchoMode(QLineEdit.Password)
                actual_widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                        border-radius: 3px;
                    }
                """)

            elif nuke_class == "Int_Knob":
                actual_widget = QSpinBox()
                actual_widget.setRange(-999999, 999999)
                actual_widget.setValue(0)
                actual_widget.setStyleSheet("""
                    QSpinBox {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                    }
                """)

            elif nuke_class == "Double_Knob":
                actual_widget = QDoubleSpinBox()
                actual_widget.setRange(-999999.0, 999999.0)
                actual_widget.setValue(0.0)
                actual_widget.setDecimals(3)
                actual_widget.setStyleSheet("""
                    QDoubleSpinBox {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                    }
                """)

            elif nuke_class == "Boolean_Knob":
                actual_widget = QCheckBox("Enabled")
                actual_widget.setStyleSheet("""
                    QCheckBox {
                        color: white;
                        spacing: 5px;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                    }
                """)

            elif nuke_class == "Text_Knob" or nuke_class == "Multiline_Eval_String_Knob":
                actual_widget = QTextEdit()
                actual_widget.setMaximumHeight(80)
                actual_widget.setPlaceholderText("Enter multiline text...")
                actual_widget.setStyleSheet("""
                    QTextEdit {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                    }
                """)

            elif nuke_class == "Color_Knob" or nuke_class == "AColor_Knob":
                actual_widget = QPushButton()
                actual_widget.setText("Pick Color")
                actual_widget.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6666;
                        border: 2px solid #555;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #ff8888;
                    }
                """)
                actual_widget.clicked.connect(lambda: self.pick_color_for_widget(actual_widget))

            elif nuke_class == "Button_Knob" or nuke_class == "PyScript_Knob":
                actual_widget = QPushButton(knob_name)
                actual_widget.setStyleSheet("""
                    QPushButton {
                        background-color: #4a7ba7;
                        border: none;
                        color: white;
                        padding: 6px 20px;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #5a8bc7;
                    }
                """)

            elif nuke_class == "Enumeration_Knob" or nuke_class == "Pulldown_Knob":
                actual_widget = QComboBox()
                actual_widget.addItems(["Option 1", "Option 2", "Option 3"])
                actual_widget.setStyleSheet("""
                    QComboBox {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                    }
                """)

            elif nuke_class == "File_Knob":
                file_widget = QWidget()
                file_layout = QHBoxLayout(file_widget)
                file_layout.setContentsMargins(0, 0, 0, 0)
                file_line = QLineEdit()
                file_line.setPlaceholderText("Select file...")
                file_line.setStyleSheet("""
                    QLineEdit {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                    }
                """)
                file_btn = QPushButton("...")
                file_btn.setMaximumWidth(30)
                file_layout.addWidget(file_line)
                file_layout.addWidget(file_btn)
                actual_widget = file_widget

            else:
                
                actual_widget = QLineEdit()
                actual_widget.setPlaceholderText(f"{nuke_class}")
                actual_widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #3a3a3a;
                        color: white;
                        border: 1px solid #555;
                        padding: 4px;
                    }
                """)

            layout.addWidget(actual_widget)
            layout.setStretch(1, 1)

            
            container.mousePressEvent = lambda e: self.select_canvas_widget(container)

            
            if pos:
                container.move(pos)
            else:
                
                y_offset = len(self.canvas_widgets) * 70
                container.move(20, 20 + y_offset)

            container.show()

            
            widget_data = {
                "widget": container,
                "actual_widget": actual_widget,
                "label": label,
                "type": knob_type,
                "nuke_class": nuke_class,
                "properties": {
                    "Name": knob_name.lower().replace(" ", "_"),
                    "Label": knob_name,
                    "Tooltip": "",
                    "Hidden": False,
                    "Default Value": ""
                }
            }
            self.canvas_widgets.append(widget_data)

            return container

        except Exception as e:
            pass
            import traceback
            traceback.print_exc()
            return None

    def pick_color_for_widget(self, button):
        """Color picker for color knob widgets"""
        color = QColorDialog.getColor()
        if color.isValid():
            button.setStyleSheet(button.styleSheet().replace(
                "background-color: #ff6666;",
                f"background-color: {color.name()};"
            ).replace(
                "background-color: #ff8888;",
                f"background-color: {color.lighter(110).name()};"
            ))

    def select_canvas_widget(self, widget):
        """Select a widget on the canvas"""
        self.selected_widget = widget

        
        for widget_data in self.canvas_widgets:
            if widget_data.get("widget") == widget:
                
                self.update_property_editor(widget_data)
                break

        
        for w in self.canvas_widgets:
            w_widget = w.get("widget")
            if w_widget == widget:
                
                w_widget.setStyleSheet("""
                    QWidget {
                        background-color: rgba(50, 50, 50, 230);
                        border: 3px solid #ffd700;
                        border-radius: 6px;
                        padding: 8px;
                    }
                """)
            else:
                
                w_widget.setStyleSheet("""
                    QWidget {
                        background-color: rgba(50, 50, 50, 230);
                        border: 2px solid #555;
                        border-radius: 6px;
                        padding: 8px;
                    }
                """)

    def create_layout_widget(self, layout_data, pos=None):
        """Create and configure the layout widget."""
        if not layout_data:
            pass
            return None

        try:
            layout_type = layout_data.get("type", "")
            layout_name = layout_data.get("name", "Unnamed Layout")

            
            container = QWidget(self.drop_frame)
            container.setMinimumSize(100, 100)
            container.setStyleSheet("""
                QWidget {
                    background-color: rgba(60, 60, 60, 150);
                    border: 1px solid #555;
                }
            """)

            
            if layout_type == "tab_layout":
                tab_widget = QTabWidget(container)
                tab_widget.addTab(QWidget(), "Tab 1")
                tab_widget.addTab(QWidget(), "Tab 2")
                QVBoxLayout(container).addWidget(tab_widget)

            elif layout_type == "group_box":
                group_box = QGroupBox(layout_name, container)
                group_box.setLayout(QVBoxLayout())
                QVBoxLayout(container).addWidget(group_box)

            elif layout_type == "collapsible_frame":
                frame = QFrame(container)
                frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
                frame.setLayout(QVBoxLayout())
                QVBoxLayout(container).addWidget(frame)

            else:
                
                layout_class = self.get_layout_class(layout_type)
                container.setLayout(layout_class())

            
            if pos:
                container.move(pos)

            container.show()

            
            widget_data = {
                "widget": container,
                "type": layout_type,
                "is_layout": True,
                "properties": {
                    "Name": layout_name
                }
            }
            self.canvas_widgets.append(widget_data)

            return container

        except Exception as e:
            pass
            return None



    def update_knob_preview(self, current, previous):
        """Update the preview panel for the selected knob."""

        
        def clear_preview():
            self.knob_preview_label.clear()
            self.knob_preview_name_label.clear()
            self.knob_preview_type_label.clear()

        knob_data = current.data(1, Qt.UserRole) if current and current.parent() else None
        self.update_property_editor(knob_data)

        
        if not current or not current.parent():
            clear_preview()
            return

        
        knob_data = current.data(1, Qt.UserRole)
        if not knob_data:
            clear_preview()
            return

        try:
            
            icon_path = knob_data.get("icon_path", "")
            if icon_path and os.path.exists(icon_path):
                knob_icon = QPixmap(icon_path)
                self.knob_preview_label.setPixmap(
                    knob_icon.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.knob_preview_label.clear()

            
            self.knob_preview_name_label.setText(knob_data.get("name", ""))
            self.knob_preview_type_label.setText(knob_data.get("type", ""))

        except Exception as e:
            pass
            clear_preview()

    def generate_code(self):
        """Generate Python code from canvas widgets with real values"""
        if not self.canvas_widgets:
            self.code_preview.setPlainText("# No widgets added to canvas yet!")
            return

        code_lines = []
        code_lines.append("import nuke")
        code_lines.append("")
        code_lines.append("def create_custom_panel():")
        code_lines.append('    """Auto-generated Nuke panel UI"""')
        code_lines.append('    panel = nuke.Panel("Custom Panel")')
        code_lines.append("")

        
        sorted_widgets = sorted(
            [w for w in self.canvas_widgets if not w.get("is_layout")],
            key=lambda w: (w["widget"].pos().y(), w["widget"].pos().x())
        )

        
        for widget_data in sorted_widgets:
            nuke_class = widget_data.get("nuke_class", "String_Knob")
            properties = widget_data.get("properties", {})
            actual_widget = widget_data.get("actual_widget")

            knob_name = properties.get("Name", "knob")
            label = widget_data.get("label").text().replace(":", "").strip()
            tooltip = properties.get("Tooltip", "")

            
            default_value = ""
            if isinstance(actual_widget, QLineEdit):
                default_value = actual_widget.text()
            elif isinstance(actual_widget, (QSpinBox, QDoubleSpinBox)):
                default_value = str(actual_widget.value())
            elif isinstance(actual_widget, QCheckBox):
                default_value = str(actual_widget.isChecked())
            elif isinstance(actual_widget, QTextEdit):
                default_value = actual_widget.toPlainText()
            elif isinstance(actual_widget, QComboBox):
                default_value = actual_widget.currentText()

            
            if nuke_class == "String_Knob":
                code_lines.append(f'    panel.addSingleLineInput("{knob_name}", "{label}")')
                if default_value:
                    code_lines.append(f'    panel.value("{knob_name}", "{default_value}")')

            elif nuke_class == "Password_Knob":
                code_lines.append(f'    panel.addPasswordInput("{knob_name}", "{label}")')
                if default_value:
                    code_lines.append(f'    panel.value("{knob_name}", "{default_value}")')

            elif nuke_class == "Int_Knob":
                val = default_value if default_value else "0"
                code_lines.append(f'    panel.addScriptCommand("{knob_name}", "{label}", "{val}")')

            elif nuke_class == "Double_Knob":
                val = default_value if default_value else "0.0"
                code_lines.append(f'    panel.addScriptCommand("{knob_name}", "{label}", "{val}")')

            elif nuke_class == "Boolean_Knob":
                val = default_value.lower() if default_value else "False"
                code_lines.append(f'    panel.addBooleanCheckBox("{knob_name}", "{label}", {val})')

            elif nuke_class in ["Text_Knob", "Multiline_Eval_String_Knob"]:
                code_lines.append(f'    panel.addMultilineTextInput("{knob_name}", "{label}")')
                if default_value:
                    escaped_value = default_value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                    code_lines.append(f'    panel.value("{knob_name}", "{escaped_value}")')

            elif nuke_class in ["Color_Knob", "AColor_Knob"]:
                
                code_lines.append(f'    panel.addColorChip("{knob_name}", [1.0, 0.5, 0.5])')

            elif nuke_class in ["Button_Knob", "PyScript_Knob"]:
                code_lines.append(f'    panel.addButton("{label}")')

            elif nuke_class in ["Enumeration_Knob", "Pulldown_Knob"]:
                if isinstance(actual_widget, QComboBox):
                    options = [actual_widget.itemText(i) for i in range(actual_widget.count())]
                    options_str = " ".join(options)
                    code_lines.append(f'    panel.addEnumerationPulldown("{knob_name}", "{options_str}")')
                    if default_value:
                        code_lines.append(f'    panel.value("{knob_name}", "{default_value}")')

            elif nuke_class == "File_Knob":
                code_lines.append(f'    panel.addFilenameSearch("{knob_name}", "{label}")')
                if default_value:
                    code_lines.append(f'    panel.value("{knob_name}", "{default_value}")')

            else:
                
                code_lines.append(f'    # {nuke_class}: {label}')
                code_lines.append(f'    panel.addSingleLineInput("{knob_name}", "{label}")')

            if tooltip:
                code_lines.append(f'    # Tooltip: {tooltip}')

            code_lines.append("")

        
        code_lines.append("    # Show panel and get values")
        code_lines.append("    if panel.show():")
        for widget_data in sorted_widgets:
            properties = widget_data.get("properties", {})
            knob_name = properties.get("Name", "knob")
            if widget_data.get("nuke_class") not in ["Button_Knob", "PyScript_Knob"]:
                code_lines.append(f'        {knob_name}_value = panel.value("{knob_name}")')
                code_lines.append(f'        print(f"{knob_name}: {{{knob_name}_value}}")')

        code_lines.append("")
        code_lines.append("        # Process values here")
        code_lines.append("        return True")
        code_lines.append("    else:")
        code_lines.append("        print('Panel cancelled')")
        code_lines.append("        return False")
        code_lines.append("")
        code_lines.append("# Run the function")
        code_lines.append("create_custom_panel()")

        
        generated_code = "\n".join(code_lines)
        self.code_preview.setPlainText(generated_code)

        
        self.right_tabs.setCurrentIndex(1)

        
        self.statusBar().showMessage(f"✓ Generated code for {len(sorted_widgets)} widgets", 3000)

    def clear_codes(self):
        """Clear all widgets from canvas and reset"""
        if not self.canvas_widgets:
            return

        
        reply = QMessageBox.question(
            self,
            "Clear Canvas",
            "Are you sure you want to remove all widgets from the canvas?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            
            for widget_data in self.canvas_widgets:
                widget = widget_data.get("widget")
                if widget:
                    widget.deleteLater()

            
            self.canvas_widgets.clear()
            self.selected_widget = None

            
            self.property_table.setRowCount(0)

            
            self.code_preview.clear()

            
            self.statusBar().showMessage("Canvas cleared", 2000)

    def delete_selected_widget(self):
        """Delete the currently selected widget"""
        if not self.selected_widget:
            return

        
        for i, widget_data in enumerate(self.canvas_widgets):
            if widget_data.get("widget") == self.selected_widget:
                
                self.selected_widget.deleteLater()
                self.canvas_widgets.pop(i)
                self.selected_widget = None

                
                self.property_table.setRowCount(0)

                
                self.statusBar().showMessage("Widget deleted", 2000)
                break

    def eventFilter(self, obj, event):
        """Handle keyboard shortcuts"""
        if event.type() == QEvent.KeyPress:
            
            if event.key() == Qt.Key_Delete:
                self.delete_selected_widget()
                return True

        return super().eventFilter(obj, event)

    def get_icon_path(self, icon_name):
        icon_paths = {
            "basic_input": os.path.join(self.icon_path, "basic-input-icon.svg"),
            "color_transform": os.path.join(self.icon_path, "color-transform-icon.svg"),
            "array_vector": os.path.join(self.icon_path, "array-vector-icon.svg"),
            "string_knob": os.path.join(self.icon_path, "string-knob-icon.svg"),
            "number_knob": os.path.join(self.icon_path, "number-knob-icon.svg"),
            "color_knob": os.path.join(self.icon_path, "color-knob-icon.svg"),
            "transform_knob": os.path.join(self.icon_path, "transform-knob-icon.svg"),
            "file_knob": os.path.join(self.icon_path, "file-knob-icon.svg"),
            "button_knob": os.path.join(self.icon_path, "button-knob-icon.svg")
        }
        default_icon = os.path.join(self.icon_path, "default-icon.svg")
        icon_path = icon_paths.get(icon_name, default_icon)

        if not os.path.exists(icon_path):
            pass
            return ""
        return icon_path


_panel_builder_instance = None

def show_panel_builder():
    """Show the Panel Builder dialog"""
    global _panel_builder_instance

    
    if _panel_builder_instance is None or not _panel_builder_instance.isVisible():
        _panel_builder_instance = MacroPanelBuilder()
        _panel_builder_instance.show()
    else:
        
        _panel_builder_instance.raise_()
        _panel_builder_instance.activateWindow()
