# beat_helper_dialog.py - BeatHelper UI Dialog
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QProgressBar, QTextEdit,
    QGroupBox, QMessageBox, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from utils.beat_helper import BeatHelper, ManualSearchThread, ManualDownloadThread
import os


class ManualResultItem(QFrame):
    """Custom widget for displaying manual search results"""
    download_requested = pyqtSignal(dict)
    view_requested = pyqtSignal(str)
    pdf_view_requested = pyqtSignal(str)
    
    def __init__(self, manual_data):
        super().__init__()
        self.manual_data = manual_data
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #101c2d;
                border: 1px solid #2f4666;
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }
            QFrame:hover {
                background-color: #142338;
                border: 1px solid #4f77a9;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(self.manual_data['title'])
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            QLabel {
                color: #d6e4f7;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        layout.addWidget(title_label)
        
        # Info row
        info_layout = QHBoxLayout()
        
        source_label = QLabel(f"Source: {self.manual_data['source']}")
        source_label.setStyleSheet("""
            QLabel {
                color: #75a3de;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        pages_label = QLabel(f"Pages: {self.manual_data['pages']}")
        pages_label.setStyleSheet("""
            QLabel {
                color: #90a6c6;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        type_label = QLabel(f"Type: {self.manual_data['type']}")
        type_label.setStyleSheet("""
            QLabel {
                color: #90a6c6;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        info_layout.addWidget(source_label)
        info_layout.addWidget(pages_label)
        info_layout.addWidget(type_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Determine if this is a downloadable file or just a search page
        result_type = self.manual_data.get('type', '')
        result_url = self.manual_data['url'].lower()
        result_pages = self.manual_data.get('pages', '')
        
        # Check if this is a search page fallback
        is_search_page = 'Click to Search' in result_pages or 'Search' in result_type or 'Manual Database' in result_type
        
        # Check if this is a PDF or downloadable manual
        is_pdf = '.pdf' in result_url or 'PDF' in result_type
        is_download_link = '/download/' in result_url or 'Download' in result_type
        is_manual_page = '/manual/' in result_url and not is_search_page
        
        # Show appropriate buttons based on content type
        can_download = (is_pdf or is_download_link or is_manual_page) and not is_search_page
        
        # Only show "View in App" for actual PDF files
        if is_pdf and not is_search_page:
            view_app_btn = QPushButton("View in App")
            view_app_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22456f;
                    color: #dbe8fa;
                    border: 1px solid #4f77a9;
                    border-radius: 5px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2a5588;
                    border: 1px solid #6e9ad3;
                }
            """)
            view_app_btn.clicked.connect(lambda: self.pdf_view_requested.emit(self.manual_data['url']))
            button_layout.addWidget(view_app_btn)
        
        view_btn = QPushButton("View Online")
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #17253b;
                color: #d0dced;
                border: 1px solid #2f4666;
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #213550;
                border: 1px solid #4f77a9;
            }
        """)
        view_btn.clicked.connect(lambda: self.view_requested.emit(self.manual_data['url']))
        button_layout.addWidget(view_btn)
        
        # Only show download button for actual manuals/PDFs, not search pages
        if can_download:
            download_btn = QPushButton("Download")
            download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17253b;
                    color: #d0dced;
                    border: 1px solid #2f4666;
                    border-radius: 5px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #213550;
                    border: 1px solid #4f77a9;
                }
            """)
            download_btn.clicked.connect(lambda: self.download_requested.emit(self.manual_data))
            button_layout.addWidget(download_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)


class BeatHelperDialog(QDialog):
    """Main BeatHelper dialog for searching and downloading manuals"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BeatHelper - Manual Finder")
        self.setMinimumSize(800, 700)
        self.resize(900, 750)
        
        self.search_thread = None
        self.download_thread = None
        self.current_results = []
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title_label = QLabel("BeatHelper - Manual Finder")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        
        subtitle_label = QLabel("Search and download product manuals from the web")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont("Consolas", 10))
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        main_layout.addLayout(header_layout)
        
        # Search section
        search_group = QGroupBox("Search for Manual")
        search_layout = QVBoxLayout(search_group)
        search_layout.setSpacing(10)
        
        search_input_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter product name or model (e.g., 'PS5', 'iPhone 14', 'Samsung TV')...")
        self.search_input.setMinimumHeight(40)
        self.search_input.returnPressed.connect(self.start_search)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedWidth(120)
        self.search_btn.setMinimumHeight(40)
        self.search_btn.clicked.connect(self.start_search)
        
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # Status label
        self.status_label = QLabel("Enter a product name to search for manuals")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(30)
        
        search_layout.addWidget(self.status_label)
        
        main_layout.addWidget(search_group)
        
        # Results section
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        # Scroll area for results
        from PyQt6.QtWidgets import QScrollArea, QWidget
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(350)
        
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(5, 5, 5, 5)
        self.results_layout.setSpacing(8)
        self.results_layout.addStretch()
        
        scroll_area.setWidget(self.results_container)
        results_layout.addWidget(scroll_area)
        
        main_layout.addWidget(results_group)
        
        # Download progress section
        self.progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(self.progress_group)
        
        self.progress_label = QLabel("No download in progress")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_group.setVisible(False)
        main_layout.addWidget(self.progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        help_btn = QPushButton("Help")
        help_btn.setFixedWidth(100)
        help_btn.clicked.connect(self.show_help)
        
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(help_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1a2b;
                color: #d0dced;
            }
            QGroupBox {
                color: #78a9e8;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #2f4666;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #111f33;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                background-color: #111f33;
            }
            QLineEdit {
                background-color: #12233a;
                color: #d0dced;
                border: 1px solid #2f4666;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #4f77a9;
                background-color: #162a45;
            }
            QPushButton {
                background-color: #17253b;
                color: #d0dced;
                border: 1px solid #2f4666;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #213550;
                border: 1px solid #4f77a9;
            }
            QPushButton:pressed {
                background-color: #192d45;
            }
            QLabel {
                color: #d0dced;
                background: transparent;
            }
            QProgressBar {
                border: 1px solid #2f4666;
                border-radius: 5px;
                text-align: center;
                background-color: #12233a;
                color: #d0dced;
            }
            QProgressBar::chunk {
                background-color: #2a5b94;
                border-radius: 4px;
            }
            QScrollArea {
                border: 1px solid #2f4666;
                border-radius: 6px;
                background-color: #0f1a2b;
            }
        """)
    
    def start_search(self):
        query = self.search_input.text().strip()
        
        # Validate query
        valid, message = BeatHelper.validate_query(query)
        if not valid:
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: #ff6b6b;")
            return
        
        # Clear previous results
        self.clear_results()
        
        # Update UI
        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        self.status_label.setText("Searching for manuals...")
        self.status_label.setStyleSheet("color: #78a9e8;")
        
        # Start search thread
        self.search_thread = ManualSearchThread(query)
        self.search_thread.search_complete.connect(self.on_search_complete)
        self.search_thread.search_error.connect(self.on_search_error)
        self.search_thread.progress_update.connect(self.on_progress_update)
        self.search_thread.start()
    
    def on_search_complete(self, results):
        self.current_results = results
        
        # Re-enable search
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        
        if results:
            self.status_label.setText(f"Found {len(results)} manual(s)")
            self.status_label.setStyleSheet("color: #76c893;")
            
            # Display results
            for manual_data in results:
                result_item = ManualResultItem(manual_data)
                result_item.download_requested.connect(self.start_download)
                result_item.view_requested.connect(self.view_online)
                result_item.pdf_view_requested.connect(self.view_pdf_in_app)
                
                # Insert before stretch
                self.results_layout.insertWidget(self.results_layout.count() - 1, result_item)
        else:
            self.status_label.setText("No manuals found")
            self.status_label.setStyleSheet("color: #ff6b6b;")
    
    def on_search_error(self, error_msg):
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.status_label.setText(f"Error: {error_msg}")
        self.status_label.setStyleSheet("color: #ff6b6b;")
    
    def on_progress_update(self, message):
        self.status_label.setText(message)
    
    def clear_results(self):
        """Clear all result items"""
        while self.results_layout.count() > 1:  # Keep the stretch
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def start_download(self, manual_data):
        """Start downloading a manual"""
        # Ask user where to save
        default_filename = BeatHelper.get_safe_filename(manual_data['title'], manual_data['url'])
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Manual As",
            default_filename,
            "All Files (*.*)"
        )
        
        if not save_path:
            return

        # Attempt to resolve the URL to a direct PDF first
        download_url = manual_data['url']
        if not download_url.lower().endswith('.pdf'):
            resolved = BeatHelper.resolve_pdf_url(download_url)
            if resolved:
                download_url = resolved
                # Inform user we found a direct PDF link
                QMessageBox.information(
                    self,
                    "PDF Resolved",
                    f"A direct PDF link was found and will be downloaded:\n{download_url}"
                )
            else:
                # Warn that the URL is a page and will be downloaded as-is
                QMessageBox.information(
                    self,
                    "Downloading Page",
                    "The selected link appears to be a page rather than a direct PDF.\n"
                    "The downloader will try to save the page contents.\n"
                    "If a PDF exists on the page, try 'View Online' and open the page in your browser."
                )

        # Show progress UI
        self.progress_group.setVisible(True)
        self.progress_label.setText(f"Downloading: {manual_data['title']}")
        self.progress_bar.setValue(0)

        # Start download thread (use resolved or original URL)
        self.download_thread = ManualDownloadThread(download_url, save_path)
        self.download_thread.download_complete.connect(self.on_download_complete)
        self.download_thread.download_error.connect(self.on_download_error)
        self.download_thread.download_progress.connect(self.on_download_progress)
        self.download_thread.status_update.connect(self.on_download_status)
        self.download_thread.start()
    
    def on_download_complete(self, file_path):
        self.progress_label.setText(f"Download complete!")
        self.progress_label.setStyleSheet("color: #76c893;")
        
        # Hide progress
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.progress_group.setVisible(False))
        
        # Check if it's a PDF file
        is_pdf = file_path.lower().endswith('.pdf')
        
        if is_pdf:
            # Ask user if they want to open the PDF
            reply = QMessageBox.question(
                self,
                "Download Complete",
                f"Manual downloaded successfully!\n\nSaved to:\n{file_path}\n\nWould you like to open the PDF in the viewer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.view_pdf_in_app(file_path)
        else:
            # For non-PDF files, just show confirmation
            QMessageBox.information(
                self,
                "Download Complete",
                f"Manual downloaded successfully!\n\nSaved to:\n{file_path}"
            )
    
    def on_download_error(self, error_msg):
        self.progress_label.setText(f"Error: {error_msg}")
        self.progress_label.setStyleSheet("color: #ff6b6b;")
        
        QMessageBox.warning(self, "Download Failed", error_msg)
    
    def on_download_progress(self, progress):
        self.progress_bar.setValue(progress)
    
    def on_download_status(self, status):
        self.progress_label.setText(status)
        self.progress_label.setStyleSheet("color: #78a9e8;")
    
    def view_online(self, url):
        """Open manual URL in browser"""
        BeatHelper.open_manual_in_browser(url)
        
        QMessageBox.information(
            self,
            "Opening in Browser",
            f"Manual page opened in your default browser:\n\n{url}"
        )
    
    def view_pdf_in_app(self, url):
        """Open PDF viewer dialog to view PDF in-app"""
        from ui.pdf_viewer_dialog import PDFViewerDialog

        # If URL is not a PDF try to resolve to a PDF link first
        pdf_url = url
        if not pdf_url.lower().endswith('.pdf'):
            resolved = BeatHelper.resolve_pdf_url(pdf_url)
            if resolved:
                pdf_url = resolved
            else:
                # No direct PDF found — open page in default browser and inform user
                QMessageBox.information(
                    self,
                    "No PDF Found",
                    "No direct PDF link could be found on the page.\n"
                    "Opening the manual page in your default browser instead."
                )
                BeatHelper.open_manual_in_browser(url)
                return

        # Create and show PDF viewer
        pdf_viewer = PDFViewerDialog(pdf_url, self)
        pdf_viewer.exec()
    
    def show_help(self):
        """Show help dialog"""
        help_text = """
        <h2>BeatHelper - Manual Finder</h2>
        <p><b>How to use:</b></p>
        <ol>
            <li><b>Enter Product Name:</b> Type the product name or model number (e.g., "PS5", "iPhone 14", "Samsung TV")</li>
            <li><b>Search:</b> Click the Search button or press Enter</li>
            <li><b>Browse Results:</b> View the list of found manuals</li>
            <li><b>View in App:</b> Click to open PDF manuals directly in BeatRooter (requires PyMuPDF)</li>
            <li><b>View Online:</b> Click to open the manual in your browser</li>
            <li><b>Download:</b> Click to download the manual to your computer</li>
        </ol>
        
        <p><b>Search Sources:</b></p>
        <ul>
            <li>ManualsLib - Large manual repository</li>
            <li>DuckDuckGo - PDF manuals from web</li>
            <li>Google Search - Additional manual sources</li>
            <li>Manufacturer Websites - Official support pages</li>
        </ul>
        
        <p><b>Tips:</b></p>
        <ul>
            <li>Be specific with model numbers for better results</li>
            <li>Include brand name for more accurate matches</li>
            <li>Try variations if first search doesn't find results</li>
            <li>Use "View in App" for PDF files to view them without leaving BeatRooter</li>
        </ul>
        
        <p><b>Note:</b> PDF viewing in-app requires PyMuPDF library (pip install PyMuPDF).</p>
        """
        
        QMessageBox.about(self, "BeatHelper Help", help_text)
