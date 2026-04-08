import copy

from PyQt6.QtCore import QPointF

from features.beatroot_canvas.models.edge import Edge
from features.beatroot_canvas.models.graph_data import GraphData
from features.beatroot_canvas.models.node import Node

class GraphManager:
    def __init__(self):
        self.graph_data = GraphData()
        self.node_counter = 0
        self.edge_counter = 0
        self.history = []
        self.history_position = -1
        self.max_history_size = 30

    def reset_history(self, description="Initial state"):
        self.history = []
        self.history_position = -1
        self.save_state(description)

    def load_snapshot(
        self,
        graph_data: GraphData,
        node_counter: int | None = None,
        edge_counter: int | None = None,
        history=None,
        history_position: int | None = None,
        description="Loaded state",
    ):
        if history:
            self.history = copy.deepcopy(history)
            self.history_position = max(
                0,
                min(
                    history_position if history_position is not None else len(self.history) - 1,
                    len(self.history) - 1,
                ),
            )
            self.restore_state(self.history[self.history_position])
            return

        self.graph_data = copy.deepcopy(graph_data)
        self.node_counter = int(node_counter if node_counter is not None else self._infer_node_counter())
        self.edge_counter = int(edge_counter if edge_counter is not None else self._infer_edge_counter())
        self.reset_history(description)

    def get_current_history_description(self):
        if 0 <= self.history_position < len(self.history):
            return self.history[self.history_position].get("description", "")
        return ""
    
    def save_state(self, description=""):
        if self.history_position < len(self.history) - 1:
            self.history = self.history[:self.history_position + 1]
        
        state = {
            'graph_data': copy.deepcopy(self.graph_data),
            'node_counter': self.node_counter,
            'edge_counter': self.edge_counter,
            'description': description
        }
        
        self.history.append(state)
        self.history_position = len(self.history) - 1

        if len(self.history) > self.max_history_size:
            self.history.pop(0)
            self.history_position -= 1
    
    def undo(self):
        if self.history_position > 0:
            self.history_position -= 1
            self.restore_state(self.history[self.history_position])
            return True
        return False
    
    def redo(self):
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            self.restore_state(self.history[self.history_position])
            return True
        return False
    
    def restore_state(self, state):
        self.graph_data = copy.deepcopy(state['graph_data'])
        self.node_counter = state['node_counter']
        self.edge_counter = state['edge_counter']
    
    def can_undo(self):
        return self.history_position > 0
    
    def can_redo(self):
        return self.history_position < len(self.history) - 1

    def _infer_node_counter(self) -> int:
        try:
            return max(
                [
                    int(str(node_id).split("_")[-1])
                    for node_id in self.graph_data.nodes.keys()
                    if str(node_id).startswith("node_") and str(node_id).split("_")[-1].isdigit()
                ]
                + [-1]
            ) + 1
        except ValueError:
            return len(self.graph_data.nodes)

    def _infer_edge_counter(self) -> int:
        try:
            return max(
                [
                    int(str(edge_id).split("_")[-1])
                    for edge_id in self.graph_data.edges.keys()
                    if str(edge_id).startswith("edge_") and str(edge_id).split("_")[-1].isdigit()
                ]
                + [-1]
            ) + 1
        except ValueError:
            return len(self.graph_data.edges)

    def add_node(self, node_type: str, position: QPointF, data: dict = None, save_state: bool = True) -> Node:
        node_id = f"node_{self.node_counter}"
        node = Node(node_id, node_type, position, data)
        self.graph_data.nodes[node_id] = node
        self.node_counter += 1
        if save_state:
            self.save_state(f"Add {node_type} node")
        return node

    def _remove_edge_without_history(self, edge_id: str):
        if edge_id not in self.graph_data.edges:
            return

        edge = self.graph_data.edges[edge_id]
        if edge.source_id in self.graph_data.nodes:
            self.graph_data.nodes[edge.source_id].remove_connection(edge_id)
        if edge.target_id in self.graph_data.nodes:
            self.graph_data.nodes[edge.target_id].remove_connection(edge_id)

        del self.graph_data.edges[edge_id]

    def remove_node(self, node_id: str, save_state: bool = True):
        if node_id in self.graph_data.nodes:
            node = self.graph_data.nodes[node_id]
            edges_to_remove = []
            for edge_id, edge in self.graph_data.edges.items():
                if edge.source_id == node_id or edge.target_id == node_id:
                    edges_to_remove.append(edge_id)
            
            for edge_id in edges_to_remove:
                self._remove_edge_without_history(edge_id)
            
            del self.graph_data.nodes[node_id]
            if save_state:
                self.save_state(f"Remove {node.type} node")
    
    def connect_nodes(self, source_id: str, target_id: str, label: str = "", 
                     edge_type: str = "connection", save_state: bool = True) -> Edge:
        if source_id not in self.graph_data.nodes or target_id not in self.graph_data.nodes:
            raise ValueError("Source or target node not found")

        edge_id = f"edge_{self.edge_counter}"
        edge = Edge(edge_id, source_id, target_id, label, edge_type)
        self.graph_data.edges[edge_id] = edge
        
        self.graph_data.nodes[source_id].add_connection(edge_id)
        self.graph_data.nodes[target_id].add_connection(edge_id)
        
        self.edge_counter += 1
        if save_state:
            self.save_state("Connect nodes")
        return edge
    
    def update_edge(self, edge_id: str, save_state: bool = True, **kwargs):
        if edge_id in self.graph_data.edges:
            edge = self.graph_data.edges[edge_id]
            old_data = {key: getattr(edge, key) for key in kwargs.keys() if hasattr(edge, key)}
            
            for key, value in kwargs.items():
                if hasattr(edge, key):
                    setattr(edge, key, value)
            
            if save_state and any(old_data[key] != kwargs[key] for key in old_data.keys()):
                self.save_state("Update edge")
            
            return edge
        return None
    
    def remove_edge(self, edge_id: str, save_state: bool = True):
        if edge_id in self.graph_data.edges:
            self._remove_edge_without_history(edge_id)
            if save_state:
                self.save_state("Remove edge")
    
    def get_node(self, node_id: str) -> Node:
        return self.graph_data.nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Edge:
        return self.graph_data.edges.get(edge_id)
    
    def get_connected_nodes(self, node_id: str) -> list:
        connected = []
        if node_id in self.graph_data.nodes:
            node = self.graph_data.nodes[node_id]
            for edge_id in node.connections:
                edge = self.graph_data.edges[edge_id]
                other_id = edge.target_id if edge.source_id == node_id else edge.source_id
                if other_id in self.graph_data.nodes:
                    connected.append(self.graph_data.nodes[other_id])
        return connected
    
    def clear_graph(self, save_state: bool = True):
        self.graph_data.clear()
        self.node_counter = 0
        self.edge_counter = 0
        if save_state:
            self.save_state("Clear graph")
