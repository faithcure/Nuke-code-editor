from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox, QHBoxLayout
from PySide2.QtCore import QUrl
from PySide2.QtGui import QDesktopServices


def build_license_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout()

    licence_info = QLabel(
        "This project uses a supportware model: it's free to use, and donations fund ongoing development."
    )
    licence_info.setWordWrap(True)
    layout.addWidget(licence_info)

    licence_status_group = QGroupBox("Current Status")
    licence_status_layout = QVBoxLayout()
    licence_status = QLabel("")
    licence_status.setWordWrap(True)
    licence_status_layout.addWidget(licence_status)
    licence_status_group.setLayout(licence_status_layout)
    layout.addWidget(licence_status_group)

    donation_group = QGroupBox("Donation")
    donation_layout = QVBoxLayout()

    donation_info = QLabel(
        "If this tool helps your workflow, consider supporting its development.\n\n"
        "Your donation directly funds long‑term maintenance, bug fixes, and new features. "
        "With steady support, I can keep improving the IDE and expand into more VFX-focused plugins "
        "and workflow enhancements. Without it, it becomes hard to sustain ongoing development."
    )
    donation_info.setWordWrap(True)
    donation_layout.addWidget(donation_info)

    donation_url_row = QHBoxLayout()
    donation_url_input = QLineEdit()
    donation_url_input.setObjectName("donation_url")
    donation_url_input.setPlaceholderText("Donation page URL (e.g. https://github.com/sponsors/<name>)")
    donation_url_row.addWidget(donation_url_input, 1)

    donate_button = QPushButton("Open Donate Page")
    donation_url_row.addWidget(donate_button, 0)
    donation_layout.addLayout(donation_url_row)

    donation_note = QLabel("Tip: Set your donation URL here to enable the button.")
    donation_note.setStyleSheet("color: grey;")
    donation_note.setWordWrap(True)
    donation_layout.addWidget(donation_note)

    def _update_donate_button_state():
        url = donation_url_input.text().strip()
        donate_button.setEnabled(bool(url))

    def _open_donation_url():
        url = donation_url_input.text().strip()
        if not url:
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        QDesktopServices.openUrl(QUrl(url))

    donation_url_input.textChanged.connect(_update_donate_button_state)
    donate_button.clicked.connect(_open_donation_url)
    _update_donate_button_state()

    donation_group.setLayout(donation_layout)
    layout.addWidget(donation_group)

    def _update_status_text():
        licence_status.setText(
            "Community License (Supportware): Free to use\n"
            "If you'd like long-term updates and new VFX tools, consider donating to support ongoing development."
        )

    _update_status_text()

    layout.addStretch()
    panel.setLayout(layout)
    settings_window.licence_panel = panel
    return panel
