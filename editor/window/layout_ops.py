import os
from PySide2.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide2.QtGui import QIcon, QPixmap, QFont
from PySide2.QtWidgets import (
    QDockWidget,
    QTreeWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QSizePolicy,
    QLineEdit,
)
from editor.console import ConsoleWidget
from editor.core import PathFromOS
from editor.nlink import load_nuke_functions
from editor.window.workspace_ops import WorkplaceTreeWidget


class LayoutOpsMixin:
    def create_bottom_tabs(self):
        """
        Creates and configures bottom dock widgets for Output and Terminal.
        """
        # Output Dock Widget (Console)
        self.output_dock = QDockWidget("CONSOLE", self)
        self.output_widget = ConsoleWidget()
        self.output_dock.setWidget(self.output_widget)
        self.output_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.output_dock.setFloating(False)
        output_icon = QIcon(os.path.join(PathFromOS().icons_path, "play_orange.svg"))
        self.set_custom_dock_title(self.output_dock, "CONSOLE", output_icon)
        self.addDockWidget(self.settings.OUTPUT_DOCK_POS, self.output_dock)
        self.output_dock.setVisible(self.settings.OUTPUT_VISIBLE)

        # Console tab is the only bottom dock now
        self.output_dock.raise_()

    def set_custom_dock_title(self, dock_widget, title, icon):
        """
        Sets a custom style and icon for the title bar of a dock widget.
        """
        # Create a custom title bar widget
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)  # Remove inner margins
        title_layout.setAlignment(Qt.AlignLeft)  # Align content to the left

        # Add the icon
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))  # Set the icon size to 16x16
        title_layout.addWidget(icon_label)

        # Add the title text
        title_label = QLabel(title.upper())  # Convert the title text to uppercase
        title_font = QFont("Arial", 10)
        title_font.setBold(True)  # Make the font bold
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        # Add stretchable space to align the content properly
        title_layout.addStretch()

        # Set the custom title bar widget for the dock widget
        dock_widget.setTitleBarWidget(title_bar)

    def update_toolbar_spacer(self, orientation: Qt.Orientation, spacer: QWidget):
        """
        Adjusts the spacer's size policy based on the toolbar's orientation.
        """
        if orientation == Qt.Horizontal:
            # Expand width for horizontal orientation
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        else:
            # Expand height for vertical orientation
            spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def create_docks(self):
        """Sol tarafa dockable listeleri ekler."""
        # Workplace dock widget
        self.workplace_dock = QDockWidget("WORKPLACE", self)
        expand_icon_path = os.path.join(PathFromOS().icons_path, 'expand_icon.svg')
        collapse_icon_path = os.path.join(PathFromOS().icons_path, 'collapse_icon.svg')

        self.workplace_tree = WorkplaceTreeWidget(self, main_window=self)
        self.workplace_tree.setHeaderHidden(True)
        self.workplace_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.workplace_tree.customContextMenuRequested.connect(self.context_menu)
        self.workplace_tree.itemDoubleClicked.connect(self.on_workplace_item_double_clicked)
        self.workplace_dock.setWidget(self.workplace_tree)
        self.addDockWidget(self.settings.WORKPLACE_DOCK_POS, self.workplace_dock)
        self.workplace_dock.setVisible(self.settings.WORKPLACE_VISIBLE)
        self.workplace_tree.setAlternatingRowColors(True)

        # Başlık oluşturmaOUTPUT_DOCK_POS
        self.create_dock_title("WORKSPACE", self.workplace_dock, expand_icon_path, collapse_icon_path)

        # OUTLINER ve HEADER widget'larını oluşturma
        self.create_outliner_dock(expand_icon_path, collapse_icon_path)
        self.create_header_dock(expand_icon_path, collapse_icon_path)

    def create_dock_title(self, title, dock_widget, expand_icon_path, collapse_icon_path):
        """Dock widget başlığını özelleştirme ve collapse/expand işlevi ekleme."""
        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 5, 5, 5)

        # İkon ve toggle işlemi için QLabel
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap(expand_icon_path).scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.mousePressEvent = lambda event: self.toggle_dock_widget(dock_widget, icon_label, expand_icon_path,
                                                                           collapse_icon_path)

        # Title text
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignVCenter)
        font = QFont("Arial", 10, QFont.Bold)
        title_label.setFont(font)

        # Layout ekleme
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_widget.setLayout(title_layout)

        dock_widget.setTitleBarWidget(title_widget)

    def toggle_dock_widget(self, dock_widget, icon_label, expand_icon_path, collapse_icon_path):
        """Dock widget'ı collapse/expand yapma fonksiyonu."""
        is_collapsed = dock_widget.maximumHeight() == 30
        if is_collapsed:
            dock_widget.setMinimumHeight(200)
            dock_widget.setMaximumHeight(16777215)
            icon_label.setPixmap(
                QPixmap(collapse_icon_path).scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            dock_widget.setMinimumHeight(30)
            dock_widget.setMaximumHeight(30)
            icon_label.setPixmap(QPixmap(expand_icon_path).scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def create_outliner_dock(self, expand_icon_path, collapse_icon_path):
        """OUTLINER dock widget'ını oluşturur ve başlığı özelleştirir."""
        self.outliner_dock = QDockWidget("OUTLINER", self)
        outliner_widget = QWidget()
        outliner_layout = QVBoxLayout(outliner_widget)
        outliner_layout.setContentsMargins(0, 0, 0, 0)  # Tüm kenarlardan sıfır boşluk
        outliner_layout.setSpacing(0)  # Öğeler arasında boşluk yok

        # PathFromOS sınıfının bir örneğini oluşturuyoruz
        path_from_os = PathFromOS()

        # İkon yolunu alıyoruz
        expand_icon = os.path.join(path_from_os.icons_path, 'expand_icon.svg')
        collapse_icon = os.path.join(path_from_os.icons_path, 'collapse_icon.svg')

        # OUTLINER QTreeWidget tanımla
        self.outliner_list = QTreeWidget()
        self.outliner_list.setHeaderHidden(True)  # Başlığı gizle
        self.outliner_list.setAlternatingRowColors(False)
        self.outliner_list.setStyleSheet("""
            QTreeWidget {
                background-color: #2B2B2B;
                border: none;
                font-size: 9pt;  /* Yazı boyutu */
            }
            
        """)

        self.outliner_list.setRootIsDecorated(False)  # Klasör simgeleri ve bağlantı çizgilerini gizler
        self.outliner_list.setStyleSheet(
            "QTreeWidget::branch { background-color: transparent; }")  # Dikey çizgileri kaldırır

        # Arama çubuğu için bir widget ve layout oluştur
        self.search_widget = QWidget()
        search_layout = QHBoxLayout(self.search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_widget.setFixedHeight(25)  # Arama çubuğu yüksekliği
        self.search_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(60, 60, 60, 0.8); /* Yarı saydam arka plan */
                border-radius: 8px;
            }
        """)
        self.search_widget.setVisible(False)  # It will be hidden initially

        # Add SearchBar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(60, 60, 60, 0.8); 
                border: none;
                color: #FFFFFF;
                padding-left: 5px;
                height: 20px;  
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
        """)

        self.search_bar.textChanged.connect(self.filter_outliner)
        search_layout.addWidget(self.search_bar)

        # OUTLINER widget'ını layout'a ekleyin
        outliner_layout.addWidget(self.outliner_list)
        outliner_layout.addWidget(self.search_widget)  # Arama çubuğu alta ekleniyor

        # OUTLINER widget'ını Outliner dock'a bağla
        self.outliner_dock.setWidget(outliner_widget)
        self.addDockWidget(self.settings.OUTLINER_DOCK_POS, self.outliner_dock)
        self.outliner_dock.setVisible(self.settings.OUTLINER_VISIBLE)

        self.populate_outliner_with_functions()
        # Sağ tıklama menüsü ekle (Context Menu)
        self.outliner_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.outliner_list.customContextMenuRequested.connect(self.context_menu_outliner)
        # OUTLINER başlık stilini oluştur ve arama ikonunu ekle
        self.create_custom_dock_title("OUTLINER", self.outliner_dock, expand_icon_path, collapse_icon_path)

        # Arama çubuğunu gösterme ve gizleme için animasyonlar
        self.search_animation_show = QPropertyAnimation(self.search_widget, b"maximumHeight")
        self.search_animation_hide = QPropertyAnimation(self.search_widget, b"maximumHeight")

        # Animasyon durumu kontrolü için bayrak
        self.search_bar_visible = False  # Çubuğun görünürlüğünü kontrol eden bayrak
        # Nuke fonksiyonlarını JSON'dan yükle ve OUTLINER'a ekle
        self.nuke_functions = load_nuke_functions()  # JSON'dan Nuke fonksiyonlarını yükle
        if self.nuke_functions:
            self.add_nuke_functions_to_outliner(self.nuke_functions)  # Eğer fonksiyonlar doluysa OUTLINER'a ekle

    def create_custom_dock_title(self, title, dock_widget, expand_icon_path, collapse_icon_path):
        """OUTLINER başlığını özelleştirir, simge ve arama ikonunu ekler."""
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        # Sol tarafa ikonu ekleyelim
        expand_icon_label = QLabel()
        expand_icon_label.setPixmap(QPixmap(expand_icon_path).scaled(25, 25, Qt.KeepAspectRatio,
                                                                     Qt.SmoothTransformation))  # İkonu 25x25 olarak büyüttük
        expand_icon_label.mousePressEvent = lambda event: self.toggle_dock_widget(dock_widget, expand_icon_label,
                                                                                  expand_icon_path, collapse_icon_path)
        title_layout.addSpacing(5)  # İkonu sağa kaydırıyoruz
        title_layout.addWidget(expand_icon_label)

        # OUTLINER başlık yazısı
        # Başlık metni
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignVCenter)
        font = QFont("Arial", 10, QFont.Bold)
        title_label.setFont(font)
        title_layout.addWidget(title_label)

        title_layout.addStretch(1)  # Başlığı sola yaslamak için araya boşluk ekle

        # Sağ tarafa arama ikonunu ekleyelim
        search_icon_label = QLabel()
        search_icon_label.setPixmap(
            QPixmap(os.path.join(PathFromOS().icons_path, "find.svg")).scaled(20, 20, Qt.KeepAspectRatio,
                                                                              Qt.SmoothTransformation))  # Arama simgesini de 20x20 olarak büyüttük
        search_icon_label.setStyleSheet("QLabel { padding: 5px; cursor: pointer; }")
        search_icon_label.mousePressEvent = self.toggle_search_bar  # İkona tıklandığında arama çubuğunu aç/kapa
        title_layout.addWidget(search_icon_label)

        # Özel başlık widget'ını dock'un başlığı olarak ayarla
        title_bar.setLayout(title_layout)
        dock_widget.setTitleBarWidget(title_bar)

    def toggle_search_bar(self, event):
        """Arama çubuğunu aç/kapa."""
        if not self.search_bar_visible:
            self.show_search_bar(event)
        else:
            self.hide_search_bar(event)

    def show_search_bar(self, event):
        """Arama çubuğunu kayarak göster."""
        if not self.search_bar_visible:
            # Arama çubuğunun açılması için animasyon ayarları
            self.search_animation_show.setDuration(300)
            self.search_animation_show.setStartValue(0)  # Gizli başlıyor
            self.search_animation_show.setEndValue(25)  # Arama çubuğunun tam yüksekliği
            self.search_animation_show.setEasingCurve(QEasingCurve.OutQuad)
            self.search_widget.setVisible(True)  # Arama widget'ını görünür yap
            self.search_animation_show.start()

            # Çubuğun şu an görünür olduğunu işaretleyelim
            self.search_bar_visible = True

    def hide_search_bar(self, event):
        """Arama çubuğunu kayarak gizle."""
        if self.search_bar_visible:
            # Arama çubuğunun kapanması için animasyon ayarları
            self.search_animation_hide.setDuration(300)
            self.search_animation_hide.setStartValue(25)  # Tam yükseklikten başlıyor
            self.search_animation_hide.setEndValue(0)  # Gizli sonlanıyor
            self.search_animation_hide.setEasingCurve(QEasingCurve.InQuad)
            self.search_animation_hide.start()
            self.search_animation_hide.finished.connect(
                lambda: self.search_widget.setVisible(False))  # Animasyon bitince gizle

            # Çubuğun şu an gizlendiğini işaretleyelim
            self.search_bar_visible = False

    def create_header_dock(self, expand_icon_path, collapse_icon_path):
        """HEADER dock widget'ını oluşturur."""
        self.header_dock = QDockWidget("HEADER", self)
        self.header_tree = QTreeWidget()

        # Set up columns
        self.header_tree.setColumnCount(2)
        self.header_tree.setHeaderLabels(["Structure", "Line"])

        # Customize header appearance
        header = self.header_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(40)  # Minimum width for line numbers

        # Style the header
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: rgb(45, 45, 45);
                color: rgb(150, 150, 150);
                padding: 4px;
                border: none;
                border-bottom: 1px solid rgb(60, 60, 60);
                font-size: 8pt;
                font-weight: bold;
            }
        """)

        # Enhanced tree widget styling
        self.header_tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                font-size: 9pt;
                background-color: rgb(40, 40, 40);
                alternate-background-color: rgb(45, 45, 45);
                selection-background-color: rgb(70, 100, 130);
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px;
                border: none;
            }
            QTreeWidget::item:hover {
                background-color: rgb(60, 60, 60);
            }
            QTreeWidget::item:selected {
                background-color: rgb(70, 100, 130);
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(none);
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(none);
            }
        """)

        # Enable alternating row colors for better readability
        self.header_tree.setAlternatingRowColors(True)
        self.header_tree.setIndentation(15)
        self.header_tree.setWordWrap(False)  # Prevent text wrapping
        # Don't elide text - let it display fully
        self.header_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.header_dock.setWidget(self.header_tree)
        self.addDockWidget(self.settings.HEADER_DOCK_POS, self.header_dock)
        self.header_dock.setVisible(self.settings.HEADER_VISIBLE)

        # Connect signals
        self.header_tree.itemClicked.connect(self.go_to_line_from_header)
        self.header_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header_tree.customContextMenuRequested.connect(self.context_menu_header)

        # HEADER başlığı için özel widget
        self.create_dock_title("HEADER", self.header_dock, expand_icon_path, collapse_icon_path)
