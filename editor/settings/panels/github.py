import os

from PySide2.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QGroupBox, QSpacerItem, QSizePolicy, QHBoxLayout


def build_github_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout()

    warning_group = QGroupBox("Use at Your Own Risk")
    warning_group.setFlat(True)
    warning_layout = QVBoxLayout()
    warning_layout.setContentsMargins(8, 6, 8, 6)
    warning_layout.setSpacing(6)
    warning_label = QLabel(
        "Git operations can modify or overwrite files. Make sure your project is under version control and backed up.\n"
        "Note: Shortcuts and actions may conflict with Nuke’s own hotkeys depending on focus."
    )
    warning_label.setWordWrap(True)
    warning_label.setStyleSheet("color: #ffb74d;")
    warning_layout.addWidget(warning_label)
    warning_group.setLayout(warning_layout)
    layout.addWidget(warning_group)

    credentials_group = QGroupBox("GitHub Credentials")
    credentials_layout = QFormLayout()

    username_input = QLineEdit()
    username_input.setObjectName("github_username")
    credentials_layout.addRow("Username:", username_input)

    token_input = QLineEdit()
    token_input.setObjectName("github_token")
    token_input.setEchoMode(QLineEdit.Password)
    show_token = QCheckBox("Show token")
    show_token.stateChanged.connect(
        lambda state: token_input.setEchoMode(QLineEdit.Normal if state else QLineEdit.Password)
    )
    token_row = QWidget()
    token_row_layout = QHBoxLayout(token_row)
    token_row_layout.setContentsMargins(0, 0, 0, 0)
    token_row_layout.setSpacing(8)
    token_row_layout.addWidget(token_input, 1)
    token_row_layout.addWidget(show_token, 0)
    credentials_layout.addRow("Token:", token_row)

    repo_url_input = QLineEdit()
    repo_url_input.setObjectName("github_repo_url")
    repo_url_input.setPlaceholderText("https://github.com/username/repository.git")
    credentials_layout.addRow("Repository URL:", repo_url_input)

    validate_button = QPushButton("Test Connection")
    validate_button.clicked.connect(lambda: settings_window.validate_credentials(username_input, token_input))
    credentials_layout.addRow(validate_button)

    settings_window.status_label = QLabel("Not validated")
    settings_window.status_label.setStyleSheet("color: #ff6f61; font-weight: bold;")
    credentials_layout.addRow(settings_window.status_label)

    token_description = QLabel(
        "Use a personal access token with repo scope for Git operations."
    )
    token_description.setWordWrap(True)
    credentials_layout.addRow(token_description)

    documentation_label = QLabel(
        "<a href='https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token' "
        "style='color:white;'>How to create a personal access token</a>"
    )
    documentation_label.setOpenExternalLinks(True)
    credentials_layout.addRow(documentation_label)

    credentials_group.setLayout(credentials_layout)
    layout.addWidget(credentials_group)

    layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

    environment_group = QGroupBox("Environment Check")
    environment_layout = QVBoxLayout()

    modules_message = QLabel()
    modules_message.setWordWrap(True)

    install_path = settings_window.modules_path
    required_modules = ["gitdb", "GitPython"]
    installed_modules = settings_window.check_github_modules(install_path, required_modules)
    normalized_install_path = os.path.normpath(install_path)
    path_in_sys_path = any(os.path.normpath(path) == normalized_install_path for path in settings_window.current_sys_path)

    if installed_modules and path_in_sys_path:
        modules_message.setText(
            "GitHub modules are installed and the modules path is available."
        )
        modules_message.setStyleSheet("color: palegreen;")
    elif installed_modules and not path_in_sys_path:
        modules_message.setText(
            "Modules are installed, but the modules path is not in sys.path."
        )
        modules_message.setStyleSheet("color: lightcoral;")

        fix_path_button = QPushButton("Fix Path")
        fix_path_button.setStyleSheet("background-color: lightcoral; color: white;")
        fix_path_button.clicked.connect(lambda: settings_window.show_fix_instructions(install_path))
        environment_layout.addWidget(fix_path_button)
    else:
        modules_message.setText("GitHub modules are missing.")
        modules_message.setStyleSheet("color: lightcoral;")

    environment_layout.addWidget(modules_message)

    install_button = QPushButton("Install GitHub Modules")
    install_button.setEnabled(False)
    install_button.clicked.connect(settings_window.install_github_modules)
    environment_layout.addWidget(install_button)

    update_button = QPushButton("Update GitHub Modules")
    update_button.setEnabled(False)
    update_button.clicked.connect(lambda: settings_window.update_github_modules(install_path, required_modules))
    environment_layout.addWidget(update_button)

    explanation_label = QLabel(
        "Module installation/updates are disabled in this build to avoid breaking Nuke's embedded Python."
    )
    explanation_label.setWordWrap(True)
    environment_layout.addWidget(explanation_label)

    environment_group.setLayout(environment_layout)
    layout.addWidget(environment_group)

    doc_link = QLabel("<a href='https://docs.github.com/en' style='color:white;'>GitHub Documentation</a>")
    doc_link.setOpenExternalLinks(True)
    layout.addWidget(doc_link)

    panel.setLayout(layout)
    return panel
