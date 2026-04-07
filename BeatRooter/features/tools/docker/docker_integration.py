from PyQt6.QtWidgets import QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from features.tools.docker.docker_automation import DockerAutomationDialog

class DockerAutomationManager:
    def __init__(self, main_window):
        self.main_window = main_window
    
    def show_docker_automation(self):
        sandbox_data = self._get_current_sandbox_data()
        
        if not sandbox_data or not sandbox_data.get('objects'):
            QMessageBox.warning(self.main_window, "Aviso", 
                              "Nenhum sandbox carregado ou vazio.\n\n"
                              "Por favor, carregue um sandbox com uma aplicação web primeiro.")
            return
        
        print(f"Sandbox carregado com {len(sandbox_data.get('objects', []))} objetos")
        
        dialog = DockerAutomationDialog(sandbox_data, self.main_window)
        dialog.exec()
    
    def _get_current_sandbox_data(self):
        try:
            environment = self.main_window.sandbox_manager.environment

            sandbox_data = {
                'metadata': environment.metadata,
                'objects': []
            }
            
            for obj_id, obj in environment.objects.items():
                obj_dict = obj.to_dict()
                sandbox_data['objects'].append(obj_dict)
            
            return sandbox_data
            
        except Exception as e:
            print(f"Erro ao extrair dados do sandbox: {e}")
            return None