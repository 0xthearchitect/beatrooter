import json
import os
import copy
import tempfile
from datetime import datetime
from features.beatroot_canvas.models.graph_data import GraphData
from features.wordlists.core.wordlist_service import WordlistService
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRectF, QSize
from PyQt6.QtSvg import QSvgGenerator

class StorageManager:
    def __init__(self):
        self.current_file = None

    def estimate_graph_size_bytes(self, graph_data: GraphData, filename: str | None = None) -> int:
        try:
            target_filename = str(filename or "").strip()
            if not target_filename:
                target_filename = os.path.join(tempfile.gettempdir(), "beatrooter_estimate.brt")
            data = self._prepare_graph_data_for_save(graph_data, target_filename)
            serialized = json.dumps(data, ensure_ascii=False)
            return len(serialized.encode("utf-8"))
        except Exception:
            return 0
    
    def save_graph(self, graph_data: GraphData, filename: str) -> bool:
        try:
            graph_data.metadata['modified'] = datetime.now().isoformat()
            if not graph_data.metadata.get('created'):
                graph_data.metadata['created'] = datetime.now().isoformat()

            data = self._prepare_graph_data_for_save(graph_data, filename)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.current_file = filename
            return True
            
        except Exception as e:
            print(f"Error saving graph: {e}")
            return False
    
    def load_graph(self, filename: str) -> GraphData:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            graph_data = GraphData.from_dict(data)
            self._hydrate_graph_after_load(graph_data, filename)
            self.current_file = filename
            return graph_data
            
        except Exception as e:
            print(f"Error loading graph: {e}")
            return GraphData()

    def _prepare_graph_data_for_save(self, graph_data: GraphData, filename: str) -> dict:
        data = copy.deepcopy(graph_data.to_dict())
        for node_payload in data.get("nodes", []):
            if node_payload.get("type") != "wordlists":
                continue
            node_payload["data"] = WordlistService.prepare_node_data_for_save(
                node_payload.get("id", ""),
                node_payload.get("data", {}),
                filename,
            )
            node_payload["data"].pop("external_content_path", None)
        return data

    def _hydrate_graph_after_load(self, graph_data: GraphData, filename: str):
        for node in graph_data.nodes.values():
            if getattr(node, "type", "") != "wordlists":
                continue
            node.data = WordlistService.hydrate_node_data_after_load(node.data, filename)
    
    def export_png(self, graph_data: GraphData, filename: str, scene=None) -> bool:
        try:
            if scene is None:
                print("No scene provided for PNG export")
                return False
            
            if not filename.lower().endswith('.png'):
                filename += '.png'
            
            print(f"Starting PNG export to: {filename}")

            rect = scene.itemsBoundingRect()
            print(f"Scene bounding rect: {rect}")
            
            if rect.width() <= 0 or rect.height() <= 0:
                rect = QRectF(0, 0, 800, 600)
                print("Using default size for PNG export")
            
            margin = 50
            width = int(rect.width() + margin)
            height = int(rect.height() + margin)
            
            print(f"Creating PNG with size: {width}x{height}")

            pixmap = QPixmap(width, height)
            pixmap.fill(QColor(255, 255, 255))
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            try:
                painter.fillRect(0, 0, width, height, QColor(255, 255, 255))
                
                source_rect = rect
                target_rect = QRectF(margin/2, margin/2, rect.width(), rect.height())
                
                scene.render(painter, target_rect, source_rect)
                
                painter.end()
                
                success = pixmap.save(filename, "PNG", 90)
                
                if success:
                    print(f"PNG exported successfully: {filename}")
                    file_size = os.path.getsize(filename)
                    print(f"File size: {file_size} bytes")
                    return True
                else:
                    print(f"Failed to save PNG file: {filename}")
                    return False
                    
            except Exception as paint_error:
                print(f"Error during painting: {paint_error}")
                import traceback
                traceback.print_exc()
                painter.end()
                return False
                
        except Exception as e:
            print(f"Error exporting PNG: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_svg(self, graph_data: GraphData, filename: str, scene=None) -> bool:
        try:
            if scene is None:
                print("No scene provided for SVG export")
                return False
            
            if not filename.lower().endswith('.svg'):
                filename += '.svg'
            
            print(f"Starting SVG export to: {filename}")

            rect = scene.itemsBoundingRect()
            print(f"Scene bounding rect: {rect}")
            
            if rect.width() <= 0 or rect.height() <= 0:
                rect = QRectF(0, 0, 800, 600)
                print("Using default size for SVG export")

            margin = 50
            
            generator = QSvgGenerator()
            generator.setFileName(filename)
            generator.setSize(QSize(int(rect.width() + margin), int(rect.height() + margin)))
            generator.setViewBox(QRectF(rect.x() - margin/2, rect.y() - margin/2, 
                                      rect.width() + margin, rect.height() + margin))
            generator.setTitle("Digital Detective Board Export")
            generator.setDescription("Exported from BeatRooter")
            
            painter = QPainter(generator)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            try:
                painter.fillRect(int(rect.x() - margin/2), int(rect.y() - margin/2),
                               int(rect.width() + margin), int(rect.height() + margin),
                               QColor(255, 255, 255))

                scene.render(painter)
                painter.end()
                
                print(f"SVG exported successfully: {filename}")
                file_size = os.path.getsize(filename)
                print(f"File size: {file_size} bytes")
                return True
                
            except Exception as paint_error:
                print(f"Error during SVG painting: {paint_error}")
                import traceback
                traceback.print_exc()
                painter.end()
                return False
                
        except Exception as e:
            print(f"Error exporting SVG: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_json(self, graph_data: GraphData, filename: str) -> bool:
        try:
            if not filename.lower().endswith('.json'):
                filename += '.json'
            return self.save_graph(graph_data, filename)
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
        
    # Adicione estes métodos à classe StorageManager:

    def save_sandbox_environment(self, environment, filename: str) -> bool:
        try:
            import json
            from datetime import datetime
            
            environment.metadata['modified'] = datetime.now().isoformat()
            if not environment.metadata.get('created'):
                environment.metadata['created'] = datetime.now().isoformat()
            
            data = environment.to_dict()  # AGORA INCLUI CONEXÕES
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.current_file = filename
            return True
            
        except Exception as e:
            print(f"Error saving sandbox environment: {e}")
            return False

    def load_sandbox_environment(self, filename: str):
        try:
            import json
            
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            from models.object_model import SandboxEnvironment
            environment = SandboxEnvironment.from_dict(data)  # AGORA CARREGA CONEXÕES
            
            self.current_file = filename
            return environment
            
        except Exception as e:
            print(f"Error loading sandbox environment: {e}")
            return SandboxEnvironment()
