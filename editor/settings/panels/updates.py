import importlib.machinery
import importlib.util
import os
import sys
from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout

from editor.dependencies import check_dependencies, required_modules
from editor.core import PathFromOS


def build_update_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout(panel)

    title = QLabel("Dependencies and Updates")
    title.setStyleSheet("font-weight: bold; font-size: 14px;")
    layout.addWidget(title)

    status_label = QLabel()
    summary_label = QLabel()
    path_label = QLabel()
    sys_path_label = QLabel()
    details = QTextEdit()
    details.setReadOnly(True)
    details.setMinimumHeight(160)

    button_row = QHBoxLayout()
    check_button = QPushButton("Check Status")
    update_button = QPushButton("Update Bundled Packages")
    fix_path_button = QPushButton("Fix Modules Path")
    button_row.addWidget(check_button)
    button_row.addWidget(update_button)
    button_row.addWidget(fix_path_button)

    layout.addWidget(status_label)
    layout.addWidget(summary_label)
    layout.addWidget(path_label)
    layout.addWidget(sys_path_label)
    layout.addWidget(details)
    layout.addLayout(button_row)
    layout.addStretch()

    settings_window.dependency_status_label = status_label
    settings_window.dependency_details_box = details

    def _modules_path():
        if getattr(settings_window, "modules_path", None):
            return settings_window.modules_path
        return os.path.join(PathFromOS().project_root, "third_party")

    def _find_spec_in_path(module_name, path):
        try:
            return importlib.machinery.PathFinder.find_spec(module_name, [path])
        except Exception:
            return None

    def _iter_bundled_modules(path):
        modules = []
        if not path or not os.path.isdir(path):
            return modules
        for entry in sorted(os.listdir(path)):
            if entry.startswith(("_", ".")) or entry == "__pycache__":
                continue
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                if os.path.exists(os.path.join(full_path, "__init__.py")):
                    modules.append(entry)
            elif entry.endswith(".py"):
                modules.append(os.path.splitext(entry)[0])
        return modules

    def _module_source(module_name, modules_path):
        spec = importlib.util.find_spec(module_name)
        if not spec:
            if _find_spec_in_path(module_name, modules_path):
                return "bundled (path not in sys.path)"
            return "missing"
        origin = spec.origin or ""
        if origin and os.path.normpath(origin).startswith(os.path.normpath(modules_path)):
            return "bundled"
        return "system"

    def render_status():
        status = check_dependencies()
        modules_path = _modules_path()
        path_in_sys = modules_path in sys.path

        if status["ok"]:
            status_label.setText("Everything is up to date.")
            status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
        else:
            status_label.setText("Updates or path fixes are needed.")
            status_label.setStyleSheet("color: #d9534f; font-weight: bold;")

        missing = len(status["missing"])
        path_missing = len(status["path_missing"])
        summary_label.setText(f"Required modules: {missing} missing, {path_missing} need sys.path fix.")
        path_label.setText(f"Modules path: {modules_path}")
        sys_path_label.setText(f"Modules path in sys.path: {'Yes' if path_in_sys else 'No'}")

        lines = ["Required modules:"]
        for package in required_modules():
            if package in status["missing"]:
                lines.append(f"- {package}: MISSING")
            elif package in status["path_missing"]:
                lines.append(f"- {package}: PATH NOT SET")
            else:
                lines.append(f"- {package}: OK")

        lines.append("")
        lines.append("Resolved module sources:")
        for package in required_modules():
            module_name = package.lower() if package == "GitPython" else package
            source = _module_source(module_name, modules_path)
            lines.append(f"- {module_name}: {source}")

        bundled = _iter_bundled_modules(modules_path)
        lines.append("")
        lines.append("Bundled modules (third_party):")
        if bundled:
            for name in bundled:
                lines.append(f"- {name}")
        else:
            lines.append("- none found")

        details.setPlainText("\n".join(lines))
        return status

    def handle_fix_path():
        status = render_status()
        if status["path_missing"]:
            settings_window.show_fix_instructions(status["modules_path"])

    check_button.clicked.connect(render_status)
    update_button.clicked.connect(settings_window.update_vendor_modules)
    fix_path_button.clicked.connect(handle_fix_path)

    render_status()
    return panel
