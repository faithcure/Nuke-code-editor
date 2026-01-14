import ast
import json
import os
import re
import nuke
from PySide2.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QListWidget,
    QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem, QMessageBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QApplication, QTextEdit, QSplitter, QTreeWidget,
    QTreeWidgetItem, QCompleter, QMenu, QAction, QWidget
)
from PySide2.QtCore import Qt, QEvent, QTimer
from PySide2.QtGui import QKeySequence, QIcon, QFont
from editor.core import PathFromOS


class NukeNodeCreatorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuke Node Creator Pro")
        self.resize(800, 600)

        self.favorite_nodes = set()
        self.node_data = []

        
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(300)  
        self.update_timer.timeout.connect(self.generate_node_code)

        self.setup_ui()
        self.setup_connections()
        self.load_node_classes()

    def setup_ui(self):
        
        main_layout = QVBoxLayout()

        
        main_splitter = QSplitter(Qt.Horizontal)

        
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        
        search_layout = QVBoxLayout()
        search_row_top = QHBoxLayout()
        search_row_bottom = QHBoxLayout()

        self.node_search_input = QLineEdit()
        self.node_search_input.setPlaceholderText("Search nodes...")

        self.refresh_button = QPushButton("Refresh")

        search_row_top.addWidget(self.node_search_input)
        search_row_top.addWidget(self.refresh_button)

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "All", "Transform", "Color", "Merge", "Filter",
            "Channel", "Keyer", "Draw", "Time", "Other"
        ])

        self.source_combo = QComboBox()
        self.source_combo.addItems(["All Sources", "Built-in", "Plugin/Gizmo"])

        self.favorites_only_check = QCheckBox("Favorites only")

        search_row_bottom.addWidget(self.category_combo)
        search_row_bottom.addWidget(self.source_combo)
        search_row_bottom.addWidget(self.favorites_only_check)

        search_layout.addLayout(search_row_top)
        search_layout.addLayout(search_row_bottom)

        
        self.node_tree = QTreeWidget()
        self.node_tree.setHeaderLabels(["Node", "Category", "Source"])
        self.node_tree.setColumnWidth(0, 160)
        self.node_tree.setColumnWidth(1, 90)
        self.node_tree.setColumnWidth(2, 80)
        self.node_tree.setContextMenuPolicy(Qt.CustomContextMenu)

        left_layout.addLayout(search_layout)
        left_layout.addWidget(self.node_tree)
        left_panel.setLayout(left_layout)
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(360)

        
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        
        config_code_splitter = QSplitter(Qt.Vertical)

        
        node_details_group = QGroupBox("Node Configuration")
        node_details_layout = QVBoxLayout()

        
        var_name_layout = QHBoxLayout()
        var_name_layout.addWidget(QLabel("Node Variable:"))
        self.node_var_input = QLineEdit()
        self.node_var_input.setPlaceholderText("Enter node variable name")
        var_name_layout.addWidget(self.node_var_input)
        node_details_layout.addLayout(var_name_layout)

        
        self.is_function_check = QCheckBox("Wrap in Function")
        self.function_name_input = QLineEdit()
        self.function_name_input.setPlaceholderText("Function name")
        self.function_name_input.setVisible(False)

        node_details_layout.addWidget(self.is_function_check)
        node_details_layout.addWidget(self.function_name_input)

        
        self.knob_table = QTableWidget()
        self.knob_table.setColumnCount(4)
        self.knob_table.setHorizontalHeaderLabels([
            "Knob Name", "New Value", "Type", "Default Value"
        ])
        node_details_layout.addWidget(self.knob_table)

        node_details_group.setLayout(node_details_layout)

        
        code_preview_group = QGroupBox("Code Preview")
        code_preview_layout = QVBoxLayout()
        self.code_preview = QTextEdit()
        self.code_preview.setReadOnly(True)  
        
        code_font = QFont("Consolas", 10)
        self.code_preview.setFont(code_font)
        code_preview_layout.addWidget(self.code_preview)
        code_preview_group.setLayout(code_preview_layout)

        
        config_code_splitter.addWidget(node_details_group)
        config_code_splitter.addWidget(code_preview_group)

        
        right_layout.addWidget(config_code_splitter)

        
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate Code")
        self.copy_button = QPushButton("Copy Code")
        self.close_button = QPushButton("Close")

        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.close_button)
        right_layout.addLayout(button_layout)

        right_panel.setLayout(right_layout)

        
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setSizes([320, 880])

        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)


    def setup_connections(self):
        
        self.node_search_input.textChanged.connect(self.filter_nodes)
        self.category_combo.currentTextChanged.connect(self.filter_nodes)
        self.source_combo.currentTextChanged.connect(self.filter_nodes)
        self.favorites_only_check.stateChanged.connect(self.filter_nodes)
        self.refresh_button.clicked.connect(self.load_node_classes)
        self.node_tree.itemSelectionChanged.connect(self.on_node_selected)
        self.node_tree.customContextMenuRequested.connect(self.show_context_menu)

        
        self.node_var_input.textChanged.connect(self.update_code_preview)
        self.is_function_check.stateChanged.connect(self.on_function_check_changed)
        self.function_name_input.textChanged.connect(self.update_code_preview)

        
        self.knob_table.itemChanged.connect(self.update_code_preview)

        
        self.generate_button.clicked.connect(self.generate_node_code)
        self.copy_button.clicked.connect(self.copy_code_to_clipboard)
        self.close_button.clicked.connect(self.reject)

    def on_function_check_changed(self, state):
        self.function_name_input.setVisible(state)
        self.update_code_preview()

    def update_code_preview(self):
        
        self.update_timer.start()

    def load_node_classes(self):
        self.favorite_nodes = self._load_favorites()
        self.node_data = self._collect_nodes()
        self._populate_node_tree()
        self._update_search_completer()
        self._write_node_list_cache()

    def _favorites_path(self):
        return os.path.join(PathFromOS().settings_db, "node_creator_favorites.json")

    def _load_favorites(self):
        path = self._favorites_path()
        if not os.path.exists(path):
            return set()
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return set(data.get("favorites", []))
        except Exception:
            return set()

    def _save_favorites(self):
        path = self._favorites_path()
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump({"favorites": sorted(self.favorite_nodes)}, file, indent=2)
        except Exception:
            pass

    def _collect_nodes(self):
        extensions = ('gizmo', 'dll', 'dylib', 'so')
        excluded_nodes = ["A_RestoreEdgePremult"]
        excluded_prefixes = ["NST_"]

        category_map = {
            "Transform": ["transform", "move", "position", "crop"],
            "Color": ["color", "grade", "exposure", "saturation"],
            "Merge": ["merge", "combine", "blend"],
            "Filter": ["blur", "sharpen", "denoise", "filter"],
            "Channel": ["channel", "shuffle", "copy"],
            "Keyer": ["keyer", "key", "chroma"],
            "Draw": ["draw", "paint", "roto"],
            "Time": ["time", "frame", "retiming"]
        }

        def categorize(name):
            lowered = name.lower()
            for cat, keywords in category_map.items():
                if any(keyword in lowered for keyword in keywords):
                    return cat
            return "Other"

        nodes = []

        for name in self._list_builtin_nodes():
            nodes.append({
                "name": name,
                "category": categorize(name),
                "source": "Built-in",
            })

        for directory in nuke.pluginPath():
            if not os.path.exists(directory):
                continue
            for filename in os.listdir(directory):
                if (filename.endswith(extensions) and
                        filename not in excluded_nodes and
                        not any(filename.startswith(prefix) for prefix in excluded_prefixes)):
                    node_name = os.path.splitext(filename)[0]
                    nodes.append({
                        "name": node_name,
                        "category": categorize(node_name),
                        "source": "Plugin/Gizmo",
                    })

        unique = {}
        for node in nodes:
            unique[node["name"]] = node
        return sorted(unique.values(), key=lambda item: item["name"].lower())

    def _list_builtin_nodes(self):
        node_names = set()
        for name in dir(nuke.nodes):
            if name.startswith("_"):
                continue
            obj = getattr(nuke.nodes, name, None)
            if callable(obj):
                node_names.add(name)
        return node_names

    def _populate_node_tree(self):
        self.node_tree.clear()
        categories = [
            "Favorites",
            "Transform",
            "Color",
            "Merge",
            "Filter",
            "Channel",
            "Keyer",
            "Draw",
            "Time",
            "Other",
        ]
        category_items = {}
        for category in categories:
            category_item = QTreeWidgetItem(self.node_tree, [category, "", ""])
            category_item.setFlags(category_item.flags() & ~Qt.ItemIsSelectable)
            category_items[category] = category_item

        for node in self.node_data:
            node_name = node["name"]
            category = node["category"]
            source = node["source"]

            node_item = QTreeWidgetItem(category_items[category],
                                        [node_name, category, source])
            node_item.setData(0, Qt.UserRole, node_name)
            node_item.setData(0, Qt.UserRole + 1, category)
            node_item.setData(0, Qt.UserRole + 2, source)

            if node_name in self.favorite_nodes:
                fav_item = QTreeWidgetItem(category_items["Favorites"],
                                           [node_name, category, source])
                fav_item.setData(0, Qt.UserRole, node_name)
                fav_item.setData(0, Qt.UserRole + 1, category)
                fav_item.setData(0, Qt.UserRole + 2, source)

        self.node_tree.sortItems(0, Qt.AscendingOrder)

    def _update_search_completer(self):
        all_nodes = [node["name"] for node in self.node_data]
        completer = QCompleter(all_nodes)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.node_search_input.setCompleter(completer)

    def _write_node_list_cache(self):
        try:
            json_path = os.path.join(PathFromOS().json_dynamic_path, "nodeList.json")
            payload = [{"name": node["name"], "category": node["category"]} for node in self.node_data]
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
        except Exception:
            pass

    def filter_nodes(self):
        search_text = self.node_search_input.text().lower()
        selected_category = self.category_combo.currentText()
        selected_source = self.source_combo.currentText()
        favorites_only = self.favorites_only_check.isChecked()

        for i in range(self.node_tree.topLevelItemCount()):
            category_item = self.node_tree.topLevelItem(i)
            category_visible = False

            for j in range(category_item.childCount()):
                node_item = category_item.child(j)

                
                node_name = node_item.data(0, Qt.UserRole) or node_item.text(0)
                node_category = node_item.data(0, Qt.UserRole + 1) or node_item.text(1)
                node_source = node_item.data(0, Qt.UserRole + 2) or node_item.text(2)

                category_match = (selected_category == "All" or
                                  selected_category == node_category)

                
                name_match = (not search_text or
                              search_text in node_name.lower())

                source_match = (selected_source == "All Sources" or
                                selected_source == node_source)

                favorites_match = (not favorites_only or node_name in self.favorite_nodes)

                node_visible = category_match and name_match and source_match and favorites_match
                node_item.setHidden(not node_visible)

                if node_visible:
                    category_visible = True

            category_item.setHidden(not category_visible)

    def on_node_selected(self):
        selected_items = self.node_tree.selectedItems()
        if not selected_items or selected_items[0].parent() is None:
            return

        selected_node = selected_items[0].data(0, Qt.UserRole) or selected_items[0].text(0)
        self.populate_knob_table(selected_node)

        
        suggested_var = re.sub(r'\W+', '_', selected_node.lower())
        self.node_var_input.setText(suggested_var)

    def populate_knob_table(self, node_name):
        self.knob_table.setRowCount(0)

        temp_node = None
        try:
            temp_node = nuke.createNode(node_name, inpanel=False)

            for knob_name, knob in temp_node.knobs().items():
                row = self.knob_table.rowCount()
                self.knob_table.insertRow(row)

                
                name_item = QTableWidgetItem(knob_name)
                name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
                self.knob_table.setItem(row, 0, name_item)

                
                knob_class = knob.Class() if hasattr(knob, "Class") else type(knob).__name__
                value_type = self._normalize_value_type(knob_class, knob)
                type_item = QTableWidgetItem(knob_class)
                type_item.setFlags(type_item.flags() ^ Qt.ItemIsEditable)
                type_item.setData(Qt.UserRole, value_type)
                self.knob_table.setItem(row, 2, type_item)

                
                default_item = QTableWidgetItem(str(knob.value()))
                default_item.setFlags(default_item.flags() ^ Qt.ItemIsEditable)
                self.knob_table.setItem(row, 3, default_item)

                
                if value_type == "float":
                    spin_box = QDoubleSpinBox()
                    spin_box.setRange(-999999.0, 999999.0)
                    spin_box.setValue(float(knob.value()))
                    spin_box.valueChanged.connect(
                        lambda val, r=row: self.knob_table.setItem(r, 1, QTableWidgetItem(str(val)))
                    )
                    self.knob_table.setCellWidget(row, 1, spin_box)
                elif value_type == "int":
                    spin_box = QSpinBox()
                    spin_box.setRange(-999999, 999999)
                    spin_box.setValue(int(knob.value()))
                    spin_box.valueChanged.connect(
                        lambda val, r=row: self.knob_table.setItem(r, 1, QTableWidgetItem(str(val)))
                    )
                    self.knob_table.setCellWidget(row, 1, spin_box)
                elif value_type == "bool":
                    combo_box = QComboBox()
                    combo_box.addItems(["True", "False"])
                    combo_box.setCurrentText(str(knob.value()))
                    combo_box.currentTextChanged.connect(
                        lambda val, r=row: self.knob_table.setItem(r, 1, QTableWidgetItem(val))
                    )
                    self.knob_table.setCellWidget(row, 1, combo_box)
                elif value_type == "enum":
                    combo_box = QComboBox()
                    values = knob.values() if hasattr(knob, "values") else []
                    combo_box.addItems(values)
                    combo_box.setCurrentText(str(knob.value()))
                    combo_box.currentTextChanged.connect(
                        lambda val, r=row: self.knob_table.setItem(r, 1, QTableWidgetItem(val))
                    )
                    self.knob_table.setCellWidget(row, 1, combo_box)
                else:
                    line_edit = QLineEdit(str(knob.value()))
                    line_edit.textChanged.connect(
                        lambda val, r=row: self.knob_table.setItem(r, 1, QTableWidgetItem(val))
                    )
                    self.knob_table.setCellWidget(row, 1, line_edit)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating node: {e}")
        finally:
            
            if temp_node:
                nuke.delete(temp_node)

    def generate_node_code(self):
        
        if not self.node_tree.selectedItems():
            return

        selected_node = self.node_tree.selectedItems()[0].data(0, Qt.UserRole) or self.node_tree.selectedItems()[0].text(0)
        node_var = self.node_var_input.text().strip()

        if not node_var:
            return

        
        code_lines = []
        invalid_knobs = []  

        
        if self.is_function_check.isChecked():
            func_name = self.function_name_input.text().strip()
            if not func_name:
                return
            code_lines.append(f"def {func_name}():")
            indent = "    "
        else:
            indent = ""

        
        code_lines.append(f"{indent}{node_var} = nuke.createNode('{selected_node}')")

        
        for row in range(self.knob_table.rowCount()):
            knob_name_item = self.knob_table.item(row, 0)
            new_value_item = self.knob_table.item(row, 1)
            type_item = self.knob_table.item(row, 2)

            if (not knob_name_item or not new_value_item or
                    not type_item or not new_value_item.text()):
                continue

            knob_name = knob_name_item.text()
            new_value = new_value_item.text()
            value_type = type_item.data(Qt.UserRole) or type_item.text()

            
            try:
                if value_type == "int":
                    converted_value = int(float(new_value))
                elif value_type == "float":
                    converted_value = float(new_value)
                elif value_type == "bool":
                    converted_value = new_value.lower() == "true"
                elif value_type == "list":
                    converted_value = self._parse_sequence(new_value)
                elif value_type == "enum":
                    converted_value = new_value
                else:
                    converted_value = new_value

                
                code_lines.append(
                    f"{indent}{node_var}['{knob_name}'].setValue({repr(converted_value)})"
                )
            except ValueError:
                
                invalid_knobs.append(f"{knob_name} (expected {value_type}, got '{new_value}')")
                continue

        
        if self.is_function_check.isChecked():
            code_lines.append(f"{indent}return {node_var}")

        
        if invalid_knobs:
            code_lines.insert(0, f"# Warning: Skipped invalid knobs: {', '.join(invalid_knobs)}")

        
        full_code = "\n".join(code_lines)

        
        if self.code_preview.toPlainText() != full_code:
            self.code_preview.setPlainText(full_code)

        return full_code

    def copy_code_to_clipboard(self):
        code = self.code_preview.toPlainText()
        if not code:
            QMessageBox.warning(self, "Copy Error", "No code to copy.")
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        QMessageBox.information(self, "Code Copied", "Node creation code copied to clipboard.")

    def show_context_menu(self, pos):
        item = self.node_tree.itemAt(pos)
        if not item or item.parent() is None:
            return
        node_name = item.data(0, Qt.UserRole) or item.text(0)

        menu = QMenu(self)
        if node_name in self.favorite_nodes:
            action = QAction("Remove from Favorites", self)
            action.triggered.connect(lambda: self._remove_favorite(node_name))
        else:
            action = QAction("Add to Favorites", self)
            action.triggered.connect(lambda: self._add_favorite(node_name))
        menu.addAction(action)
        menu.exec_(self.node_tree.viewport().mapToGlobal(pos))

    def _add_favorite(self, node_name):
        self.favorite_nodes.add(node_name)
        self._save_favorites()
        self._populate_node_tree()
        self.filter_nodes()

    def _remove_favorite(self, node_name):
        if node_name in self.favorite_nodes:
            self.favorite_nodes.remove(node_name)
            self._save_favorites()
            self._populate_node_tree()
            self.filter_nodes()

    def _normalize_value_type(self, knob_class, knob):
        knob_class = knob_class or ""
        if knob_class in ("Double_Knob", "Float_Knob"):
            return "float"
        if knob_class in ("Int_Knob", "Int"):
            return "int"
        if knob_class in ("Boolean_Knob", "Bool_Knob"):
            return "bool"
        if knob_class in ("Enumeration_Knob", "Enumeration"):
            return "enum"
        if knob_class in ("XY_Knob", "XYZ_Knob", "WH_Knob", "Color_Knob", "Array_Knob"):
            return "list"
        value = knob.value()
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, (list, tuple)):
            return "list"
        return "string"

    def _parse_sequence(self, text):
        try:
            value = ast.literal_eval(text)
            if isinstance(value, (list, tuple)):
                return list(value)
        except Exception:
            pass
        parts = [part.strip() for part in text.split(",") if part.strip()]
        if not parts:
            return []
        values = []
        for part in parts:
            try:
                values.append(float(part))
            except ValueError:
                values.append(part)
        return values


def show_nuke_node_creator():
    """
    Convenience function to show the Nuke Node Creator dialog.
    Can be called directly from Nuke's script editor or menu.
    """
    dialog = NukeNodeCreatorDialog()
    dialog.exec_()
