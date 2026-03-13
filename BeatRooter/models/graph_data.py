from typing import Dict, List
from models.node import Node
from models.edge import Edge

class GraphData:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.metadata: Dict[str, any] = {
            'title': 'Untitled Investigation',
            'created': '',
            'version': '1.0',
            'custom_node_templates': {},
            'node_template_settings': {},
        }
    
    def clear(self):
        self.nodes.clear()
        self.edges.clear()
    
    def to_dict(self) -> Dict[str, any]:
        return {
            'metadata': self.metadata,
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [edge.to_dict() for edge in self.edges.values()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]):
        graph = cls()
        graph.metadata = data.get('metadata', {})
        
        # Load nodes
        for node_data in data.get('nodes', []):
            node = Node.from_dict(node_data)
            graph.nodes[node.id] = node
        
        # Load edges
        for edge_data in data.get('edges', []):
            edge = Edge.from_dict(edge_data)
            graph.edges[edge.id] = edge
        
        return graph
