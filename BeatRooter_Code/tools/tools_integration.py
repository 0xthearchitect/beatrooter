from PyQt6.QtWidgets import QDockWidget, QMenu, QMessageBox
from PyQt6.QtCore import Qt
from tools.tools_manager import ToolsManager
from tools.tools_downloader import ToolsDownloadManager

class ToolsIntegration:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tools_manager = None
        self.tools_dock = None
        self.download_manager = ToolsDownloadManager(main_window)

    def setup_tools_integration(self):
        self.tools_manager = ToolsManager(self.main_window)
        
        self.tools_dock = QDockWidget("External Tools", self.main_window)
        self.tools_dock.setWidget(self.tools_manager)

        self.tools_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tools_dock)


    def install_missing_tools(self):
        self.download_manager.request_installation()
        if self.tools_manager:
            self.tools_manager.check_available_tools()

    def check_tool_availability(self):
        missing_tools = self.download_manager.check_missing_tools()
        
        if not missing_tools:
            QMessageBox.information(
                self.main_window,
                "Ferramentas Disponíveis",
                "Todas as ferramentas estão disponíveis e prontas para uso!"
            )
        else:
            QMessageBox.warning(
                self.main_window,
                "Ferramentas em Falta",
                f"As seguintes ferramentas não estão disponíveis:\n\n{', '.join(missing_tools)}\n\n"
                "Use 'Install Missing Tools' para instalá-las automaticamente."
            )

    def toggle_tools_panel(self):
        if self.tools_dock.isVisible():
            self.tools_dock.hide()
        else:
            self.tools_dock.show()

    def quick_launch_tool(self, tool_name):
        if self.tools_dock.isHidden():
            self.tools_dock.show()
        
        self.tools_manager.select_tool(tool_name)