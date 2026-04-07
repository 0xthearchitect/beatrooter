from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from PyQt6.QtCore import QPointF

@dataclass
class Node:
    id: str
    type: str
    position: QPointF
    data: Dict[str, Any]
    connections: List[str]
    
    def __init__(self, node_id: str, node_type: str, position: QPointF, data: Dict[str, Any] = None):
        self.id = node_id
        self.type = node_type
        self.position = position
        self.data = data or {}
        self.connections = []
    
    def add_connection(self, edge_id: str):
        if edge_id not in self.connections:
            self.connections.append(edge_id)
    
    def remove_connection(self, edge_id: str):
        if edge_id in self.connections:
            self.connections.remove(edge_id)
    
    def update_data(self, key: str, value: Any):
        self.data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'position': {
                'x': self.position.x(),
                'y': self.position.y()
            },
            'data': self.data,
            'connections': self.connections
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        position = QPointF(data['position']['x'], data['position']['y'])
        node = cls(data['id'], data['type'], position, data['data'])
        node.connections = data.get('connections', [])
        return node