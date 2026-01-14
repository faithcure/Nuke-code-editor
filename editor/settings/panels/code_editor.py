from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QGroupBox, QFontComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QHBoxLayout
from PySide2.QtGui import QFontDatabase


def build_code_editor_panel(settings_window):
    panel = QWidget()
    layout = QVBoxLayout()

    font_group = QGroupBox("Font")
    font_layout = QFormLayout()

    font_selector = QFontComboBox()
    font_selector.setObjectName("default_selected_font")
    font_selector.setCurrentFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
    font_layout.addRow("Font:", font_selector)

    font_size_spinbox = QSpinBox()
    font_size_spinbox.setMinimumWidth(100)
    font_size_spinbox.setMinimumHeight(30)
    font_size_spinbox.setObjectName("default_font_size")
    font_size_spinbox.setRange(8, 48)
    font_size_spinbox.setValue(14)

    zoom_checkbox = QCheckBox("Zoom with Mouse Wheel")
    zoom_checkbox.setObjectName("is_wheel_zoom")
    font_size_layout = QHBoxLayout()
    font_size_layout.addWidget(font_size_spinbox)
    font_size_layout.addWidget(zoom_checkbox)
    font_layout.addRow("Font Size:", font_size_layout)

    zoom_explanation = QLabel("Use Ctrl+Mouse Wheel for quick zoom. The default size is 14.")
    zoom_explanation.setStyleSheet("color: grey;")
    zoom_explanation.setWordWrap(True)
    font_layout.addRow(zoom_explanation)

    font_group.setLayout(font_layout)
    layout.addWidget(font_group)

    extra_settings_group = QGroupBox("Completion & Suggestions")
    extra_layout = QFormLayout()

    smart_completion_checkbox = QCheckBox("Enable Smart Completion")
    smart_completion_checkbox.setChecked(True)
    smart_completion_checkbox.setObjectName("disable_smart_compilation")
    extra_layout.addRow(smart_completion_checkbox)

    smart_completion_note = QLabel("Show contextual suggestions while typing.")
    smart_completion_note.setStyleSheet("color: grey;")
    smart_completion_note.setWordWrap(True)
    extra_layout.addRow(smart_completion_note)

    completion_popup_checkbox = QCheckBox("Enable Completion Popup")
    completion_popup_checkbox.setChecked(True)
    completion_popup_checkbox.setObjectName("disable_completion_popup")
    extra_layout.addRow(completion_popup_checkbox)

    completion_popup_note = QLabel("Show the popup completion list while typing.")
    completion_popup_note.setStyleSheet("color: grey;")
    completion_popup_note.setWordWrap(True)
    extra_layout.addRow(completion_popup_note)

    inline_suggestion_checkbox = QCheckBox("Inline Ghosting Suggestions")
    inline_suggestion_checkbox.setChecked(True)
    inline_suggestion_checkbox.setObjectName("disable_suggestion")
    extra_layout.addRow(inline_suggestion_checkbox)

    inline_suggestion_note = QLabel("Preview a completion inline; accept with Alt+Enter. Requires Smart Completion.")
    inline_suggestion_note.setStyleSheet("color: grey;")
    inline_suggestion_note.setWordWrap(True)
    extra_layout.addRow(inline_suggestion_note)

    fuzzy_completion_checkbox = QCheckBox("Fuzzy Matching")
    fuzzy_completion_checkbox.setChecked(True)
    fuzzy_completion_checkbox.setObjectName("disable_fuzzy_compilation")
    extra_layout.addRow(fuzzy_completion_checkbox)

    fuzzy_completion_note = QLabel("Offer close matches when an exact match is missing. Requires Smart Completion.")
    fuzzy_completion_note.setStyleSheet("color: grey;")
    fuzzy_completion_note.setWordWrap(True)
    extra_layout.addRow(fuzzy_completion_note)

    node_completer_checkbox = QCheckBox("Node Auto-Completer")
    node_completer_checkbox.setChecked(True)
    node_completer_checkbox.setObjectName("disable_node_completer")
    extra_layout.addRow(node_completer_checkbox)

    node_completer_note = QLabel("Suggest nodes and node names during creation. Requires Smart Completion.")
    node_completer_note.setStyleSheet("color: grey;")
    node_completer_note.setWordWrap(True)
    extra_layout.addRow(node_completer_note)

    def toggle_dependent_checkboxes(enabled):
        completion_popup_checkbox.setEnabled(enabled)
        inline_suggestion_checkbox.setEnabled(enabled)
        fuzzy_completion_checkbox.setEnabled(enabled)
        node_completer_checkbox.setEnabled(enabled)

    smart_completion_checkbox.stateChanged.connect(
        lambda state: toggle_dependent_checkboxes(state == 2)
    )
    toggle_dependent_checkboxes(smart_completion_checkbox.isChecked())

    extra_settings_group.setLayout(extra_layout)
    layout.addWidget(extra_settings_group)

    folding_group = QGroupBox("Code Folding")
    folding_layout = QFormLayout()
    enable_folding_checkbox = QCheckBox("Enable code folding")
    enable_folding_checkbox.setChecked(True)
    enable_folding_checkbox.setObjectName("enable_code_folding")
    enable_folding_checkbox.setToolTip("Show fold/unfold icons for code blocks.")
    folding_layout.addRow(enable_folding_checkbox)
    folding_note = QLabel("Collapse code blocks for better readability.")
    folding_note.setStyleSheet("color: grey;")
    folding_note.setWordWrap(True)
    folding_layout.addRow(folding_note)
    folding_group.setLayout(folding_layout)
    layout.addWidget(folding_group)

    spacing_group = QGroupBox("Line Spacing")
    spacing_layout = QFormLayout()
    line_spacing_spinbox = QDoubleSpinBox()
    line_spacing_spinbox.setMinimumHeight(30)
    line_spacing_spinbox.setObjectName("line_spacing_size")
    line_spacing_spinbox.setRange(0.8, 3.0)
    line_spacing_spinbox.setSingleStep(0.1)
    line_spacing_spinbox.setValue(1.2)
    line_spacing_spinbox.setSuffix("x")
    line_spacing_spinbox.setToolTip("Adjust the line height multiplier")
    spacing_layout.addRow("Line Spacing:", line_spacing_spinbox)
    spacing_note = QLabel("Adjust line height. Default is 1.2x.")
    spacing_note.setStyleSheet("color: grey;")
    spacing_note.setWordWrap(True)
    spacing_layout.addRow(spacing_note)
    spacing_group.setLayout(spacing_layout)
    layout.addWidget(spacing_group)

    autosave_group = QGroupBox("Auto-save")
    autosave_layout = QFormLayout()
    enable_autosave_checkbox = QCheckBox("Enable auto-save")
    enable_autosave_checkbox.setObjectName("enable_autosave")
    enable_autosave_checkbox.setChecked(False)
    autosave_layout.addRow(enable_autosave_checkbox)

    autosave_interval_spinbox = QSpinBox()
    autosave_interval_spinbox.setMinimumHeight(30)
    autosave_interval_spinbox.setObjectName("autosave_interval")
    autosave_interval_spinbox.setRange(1, 60)
    autosave_interval_spinbox.setValue(5)
    autosave_interval_spinbox.setSuffix(" minutes")
    autosave_interval_spinbox.setEnabled(False)
    autosave_layout.addRow("Auto-save interval:", autosave_interval_spinbox)

    enable_autosave_checkbox.stateChanged.connect(
        lambda state: autosave_interval_spinbox.setEnabled(state == 2)
    )

    autosave_note = QLabel("Automatically save your work at regular intervals.")
    autosave_note.setStyleSheet("color: grey;")
    autosave_note.setWordWrap(True)
    autosave_layout.addRow(autosave_note)
    autosave_group.setLayout(autosave_layout)
    layout.addWidget(autosave_group)

    indent_group = QGroupBox("Indentation")
    indent_layout = QFormLayout()
    tab_size_spinbox = QSpinBox()
    tab_size_spinbox.setMinimumHeight(30)
    tab_size_spinbox.setObjectName("tab_size")
    tab_size_spinbox.setRange(2, 8)
    tab_size_spinbox.setValue(4)
    tab_size_spinbox.setSuffix(" spaces")
    indent_layout.addRow("Tab size:", tab_size_spinbox)

    use_spaces_checkbox = QCheckBox("Use spaces instead of tabs")
    use_spaces_checkbox.setObjectName("use_spaces_for_tabs")
    use_spaces_checkbox.setChecked(True)
    indent_layout.addRow(use_spaces_checkbox)

    indent_note = QLabel("Python standard is 4 spaces.")
    indent_note.setStyleSheet("color: grey;")
    indent_note.setWordWrap(True)
    indent_layout.addRow(indent_note)
    indent_group.setLayout(indent_layout)
    layout.addWidget(indent_group)

    def update_preview_font(font):
        preview_editor = getattr(settings_window, "preview_editor", None)
        if not preview_editor:
            return
        preview_editor.setFontFamily(font.family())
        apply_preview = getattr(settings_window, "apply_syntax_preview", None)
        if apply_preview:
            apply_preview()

    def update_preview_font_size(size):
        preview_editor = getattr(settings_window, "preview_editor", None)
        if not preview_editor:
            return
        preview_editor.setFontPointSize(size)
        apply_preview = getattr(settings_window, "apply_syntax_preview", None)
        if apply_preview:
            apply_preview()

    font_selector.currentFontChanged.connect(update_preview_font)
    font_size_spinbox.valueChanged.connect(update_preview_font_size)

    panel.setLayout(layout)
    return panel
