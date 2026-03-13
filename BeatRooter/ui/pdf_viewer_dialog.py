from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QWidget, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QByteArray
from PyQt6.QtGui import QPixmap, QImage, QPainter
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class PDFDownloadThread(QThread):
    """Thread for downloading PDF without blocking UI"""
    download_complete = pyqtSignal(str)  # File path
    download_error = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, url, temp_path):
        super().__init__()
        self.url = url
        self.temp_path = temp_path
    
    def run(self):
        try:
            self.progress_update.emit("Downloading PDF...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(self.url, headers=headers, timeout=30, stream=True)

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()

                # If already a PDF, save stream to temp file
                if 'application/pdf' in content_type or self.url.lower().endswith('.pdf') or response.url.lower().endswith('.pdf'):
                    with open(self.temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    self.download_complete.emit(self.temp_path)
                    return

                # If HTML/page, try to find a PDF link on the page
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    pdf_candidate = None
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if '.pdf' in href.lower():
                            pdf_candidate = urljoin(response.url, href)
                            break

                    if pdf_candidate:
                        # Attempt to download the discovered PDF
                        resp2 = requests.get(pdf_candidate, headers=headers, timeout=30, stream=True)
                        if resp2.status_code == 200 and 'application/pdf' in resp2.headers.get('content-type', '').lower():
                            with open(self.temp_path, 'wb') as f:
                                for chunk in resp2.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)

                            self.download_complete.emit(self.temp_path)
                            return
                except Exception:
                    pass

                # Fallback: save received content (likely HTML) and return — viewer will handle errors
                with open(self.temp_path, 'wb') as f:
                    f.write(response.content)

                self.download_complete.emit(self.temp_path)
                return
            else:
                self.download_error.emit(f"Failed to download: HTTP {response.status_code}")
        except Exception as e:
            self.download_error.emit(f"Download error: {str(e)}")


class PDFViewerDialog(QDialog):
    """Dialog for viewing PDF files using PyMuPDF (fitz)"""
    
    def __init__(self, pdf_source, parent=None):
        super().__init__(parent)
        self.pdf_source = pdf_source  # Can be URL or file path
        self.pdf_path = None
        self.pdf_doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.download_thread = None
        
        self.setWindowTitle("PDF Viewer - BeatHelper")
        self.setMinimumSize(900, 700)
        self.resize(1000, 800)
        
        self.setup_ui()
        self.apply_styles()
        self.load_pdf()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.status_label = QLabel("Loading PDF...")
        self.status_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        
        self.page_label = QLabel("Page: 0 / 0")
        self.page_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 12px;")
        
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.setFixedWidth(100)
        self.prev_btn.clicked.connect(self.previous_page)
        self.prev_btn.setEnabled(False)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setFixedWidth(100)
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        
        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_in_btn.setFixedWidth(60)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_in_btn.setEnabled(False)
        
        self.zoom_out_btn = QPushButton("Zoom Out")
        self.zoom_out_btn.setFixedWidth(60)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_out_btn.setEnabled(False)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(80)
        self.save_btn.clicked.connect(self.save_pdf)
        self.save_btn.setEnabled(False)
        
        toolbar.addWidget(self.status_label)
        toolbar.addStretch()
        toolbar.addWidget(self.page_label)
        toolbar.addWidget(self.prev_btn)
        toolbar.addWidget(self.next_btn)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.save_btn)
        
        layout.addLayout(toolbar)
        
        # PDF Display Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pdf_container = QWidget()
        self.pdf_layout = QVBoxLayout(self.pdf_container)
        self.pdf_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pdf_label = QLabel("Loading PDF...")
        self.pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_label.setStyleSheet("background-color: #4a4a4a; padding: 20px;")
        
        self.pdf_layout.addWidget(self.pdf_label)
        scroll_area.setWidget(self.pdf_container)
        
        layout.addWidget(scroll_area)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2e2e2e;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #a855f7;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #c084fc;
            }
            QPushButton:pressed {
                background-color: #9333ea;
            }
            QPushButton:disabled {
                background-color: #5a5a5a;
                color: #888888;
            }
            QScrollArea {
                border: 1px solid #5a5a5a;
                background-color: #3e3e3e;
            }
        """)
    
    def load_pdf(self):
        """Load PDF from URL or file path"""
        # Check if PyMuPDF is available
        try:
            import fitz  # PyMuPDF
        except ImportError:
            self.status_label.setText("Error: PyMuPDF not installed")
            self.pdf_label.setText(
                "PDF viewing requires PyMuPDF library.\n\n"
                "Install with: pip install PyMuPDF\n\n"
                "Opening in external browser instead..."
            )
            QMessageBox.warning(
                self,
                "Library Missing",
                "PyMuPDF is required for PDF viewing.\n\n"
                "Install it with: pip install PyMuPDF\n\n"
                "Opening PDF in external browser instead."
            )
            # Open in browser as fallback
            import webbrowser
            webbrowser.open(self.pdf_source)
            self.accept()
            return
        
        # Check if source is URL or file
        if self.pdf_source.startswith('http://') or self.pdf_source.startswith('https://'):
            # Download PDF first
            import tempfile
            self.pdf_path = os.path.join(tempfile.gettempdir(), 'beathelper_temp.pdf')
            
            self.download_thread = PDFDownloadThread(self.pdf_source, self.pdf_path)
            self.download_thread.download_complete.connect(self.on_download_complete)
            self.download_thread.download_error.connect(self.on_download_error)
            self.download_thread.progress_update.connect(self.on_progress_update)
            self.download_thread.start()
        else:
            # Local file
            self.pdf_path = self.pdf_source
            self.open_pdf_document()
    
    def on_download_complete(self, file_path):
        self.status_label.setText("Download complete")
        self.open_pdf_document()
    
    def on_download_error(self, error_msg):
        self.status_label.setText(f"Error: {error_msg}")
        self.pdf_label.setText(f"Failed to download PDF:\n{error_msg}")
        QMessageBox.warning(self, "Download Failed", error_msg)
    
    def on_progress_update(self, message):
        self.status_label.setText(message)
    
    def open_pdf_document(self):
        """Open and display the PDF document"""
        try:
            import fitz  # PyMuPDF
            
            if not os.path.exists(self.pdf_path):
                raise FileNotFoundError("PDF file not found")
            
            self.pdf_doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_doc)
            self.current_page = 0
            
            self.status_label.setText(f"PDF loaded: {self.total_pages} pages")
            
            # Enable controls
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)
            self.zoom_in_btn.setEnabled(True)
            self.zoom_out_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            
            # Display first page
            self.display_page()
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.pdf_label.setText(f"Failed to open PDF:\n{str(e)}")
            QMessageBox.critical(self, "PDF Error", f"Failed to open PDF:\n{str(e)}")
    
    def display_page(self):
        """Render and display the current page"""
        try:
            import fitz
            
            if not self.pdf_doc:
                return
            
            page = self.pdf_doc[self.current_page]
            
            # Render page to pixmap with zoom
            mat = fitz.Matrix(self.zoom_level * 2, self.zoom_level * 2)  # 2x for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to QImage
            img_data = pix.samples
            qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            
            # Display in label
            pixmap = QPixmap.fromImage(qimg)
            self.pdf_label.setPixmap(pixmap)
            self.pdf_label.setStyleSheet("")
            
            # Update page label
            self.page_label.setText(f"Page: {self.current_page + 1} / {self.total_pages}")
            
            # Update button states
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < self.total_pages - 1)
            
        except Exception as e:
            self.status_label.setText(f"Render error: {str(e)}")
            QMessageBox.warning(self, "Render Error", f"Failed to render page:\n{str(e)}")
    
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_page()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_page()
    
    def zoom_in(self):
        """Increase zoom level"""
        if self.zoom_level < 3.0:
            self.zoom_level += 0.2
            self.display_page()
    
    def zoom_out(self):
        """Decrease zoom level"""
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.2
            self.display_page()
    
    def save_pdf(self):
        """Save PDF to user-selected location"""
        if not self.pdf_path:
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            "manual.pdf",
            "PDF Files (*.pdf)"
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy(self.pdf_path, save_path)
                QMessageBox.information(
                    self,
                    "Saved",
                    f"PDF saved successfully to:\n{save_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    f"Failed to save PDF:\n{str(e)}"
                )
    
    def closeEvent(self, event):
        """Clean up when closing"""
        if self.pdf_doc:
            self.pdf_doc.close()
        
        # Clean up temp file if it was downloaded
        if self.pdf_path and 'beathelper_temp' in self.pdf_path:
            try:
                if os.path.exists(self.pdf_path):
                    os.remove(self.pdf_path)
            except:
                pass
        
        event.accept()