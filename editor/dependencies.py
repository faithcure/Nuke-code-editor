import importlib.machinery
import importlib.util
import os
import sys

from editor.core import PathFromOS

IMPORT_NAME_MAP = {
    "GitPython": "git",
}


def _modules_path():
    return os.path.join(PathFromOS().project_root, "third_party")


def _find_spec_in_path(module_name, path):
    try:
        return importlib.machinery.PathFinder.find_spec(module_name, [path])
    except Exception:
        return None


def required_modules():
    modules = ["gitdb", "GitPython", "psutil", "requests", "pygments"]
    return modules


def check_dependencies():
    modules_path = _modules_path()
    missing = []
    path_missing = []
    for package in required_modules():
        import_name = IMPORT_NAME_MAP.get(package, package)
        if importlib.util.find_spec(import_name):
            continue
        if _find_spec_in_path(import_name, modules_path):
            path_missing.append(package)
            continue
        missing.append(package)

    ok = not missing and not path_missing
    return {
        "ok": ok,
        "missing": missing,
        "path_missing": path_missing,
        "modules_path": modules_path,
    }
