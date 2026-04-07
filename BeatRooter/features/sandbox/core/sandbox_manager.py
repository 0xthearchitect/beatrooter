from models.object_model import SandboxEnvironment, SandboxObject, ObjectType
from features.sandbox.core.sandbox_object_factory import SandboxObjectFactory
import copy

class SandboxManager:
    def __init__(self):
        self.environment = SandboxEnvironment()
        self.history = []
        self.history_position = -1
        self.max_history_size = 50
    
    def add_connection(self, source_id: str, target_id: str, connection_type: str = "network") -> str:

        if (source_id in self.environment.objects and 
            target_id in self.environment.objects):
            
            self.save_state("Add connection between objects")
            
            import time
            connection_id = f"conn_{int(time.time() * 1000)}"
        
            
            from models.object_model import SandboxConnection
            connection = SandboxConnection(
                id=connection_id,
                source_id=source_id,
                target_id=target_id,
                connection_type=connection_type
            )
            
            self.environment.connections[connection_id] = connection
            
            self.environment.objects[source_id].add_connection(connection_id)
            self.environment.objects[target_id].add_connection(connection_id)
            
            return connection_id

        return None

    def remove_connection(self, connection_id: str):
        if connection_id in self.environment.connections:
            self.save_state("Remove connection")
            self.environment.remove_connection(connection_id)
    
    def _remove_object_connections(self, obj_id: str):
        connections_to_remove = []
        
        for connection_id, connection in self.environment.connections.items():
            if connection.source_id == obj_id or connection.target_id == obj_id:
                connections_to_remove.append(connection_id)
        
        for connection_id in connections_to_remove:
            self.remove_connection(connection_id)
    
    def save_state(self, description=""):
        if self.history_position < len(self.history) - 1:
            self.history = self.history[:self.history_position + 1]
        
        state = {
            'environment': copy.deepcopy(self.environment),
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
        self.environment = copy.deepcopy(state['environment'])
    
    def can_undo(self):
        return self.history_position > 0
    
    def can_redo(self):
        return self.history_position < len(self.history) - 1
    
    def add_object(self, obj_type: ObjectType, position, name: str = None, 
                  properties: dict = None, parent_id: str = None) -> SandboxObject:
        self.save_state(f"Add {obj_type.value} object")
        
        obj = SandboxObjectFactory.create_object(obj_type, position, name, properties)
        self.environment.add_object(obj)
        
        if parent_id and parent_id in self.environment.objects:
            parent = self.environment.objects[parent_id]
            if obj_type in SandboxObjectFactory.get_allowed_children(parent.object_type):
                parent.add_child(obj.id)
                obj.parent_id = parent_id
        
        return obj
    
    def remove_object(self, obj_id: str):
        if obj_id in self.environment.objects:
            obj = self.environment.objects[obj_id]
            self.save_state(f"Remove {obj.object_type.value} object")
            
            self._remove_object_connections(obj_id)
            
            if obj.parent_id and obj.parent_id in self.environment.objects:
                self.environment.objects[obj.parent_id].remove_child(obj_id)
            
            self.environment.remove_object(obj_id)
    
    def _remove_object_connections(self, obj_id: str):
        connections_to_remove = []
        
        for other_obj_id, other_obj in self.environment.objects.items():
            for connection_id in list(other_obj.connections):
                if obj_id in connection_id:
                    connections_to_remove.append((other_obj_id, connection_id))
        
        for other_obj_id, connection_id in connections_to_remove:
            self.environment.objects[other_obj_id].remove_connection(connection_id)
    
    def set_parent(self, child_id: str, parent_id: str):
        if (child_id in self.environment.objects and 
            parent_id in self.environment.objects):
            
            child = self.environment.objects[child_id]
            parent = self.environment.objects[parent_id]
            
            if child.object_type not in SandboxObjectFactory.get_allowed_children(parent.object_type):
                raise ValueError(f"Cannot add {child.object_type.value} as child of {parent.object_type.value}")
            
            self.save_state(f"Set parent for {child.object_type.value}")
            
            if child.parent_id and child.parent_id in self.environment.objects:
                self.environment.objects[child.parent_id].remove_child(child_id)

            parent.add_child(child_id)
            child.parent_id = parent_id
    
    def update_object_properties(self, obj_id: str, properties: dict):
        if obj_id in self.environment.objects:
            obj = self.environment.objects[obj_id]
            old_properties = obj.properties.copy()
            
            obj.properties.update(properties)
            
            if old_properties != obj.properties:
                self.save_state(f"Update {obj.object_type.value} properties")
    
    def clear_environment(self):
        self.save_state("Clear environment")
        self.environment = SandboxEnvironment()
    
    def get_object_tree(self, root_id: str = None) -> list:
        if not root_id:
            root_objects = [obj for obj in self.environment.objects.values() if not obj.parent_id]
            return root_objects
        
        if root_id not in self.environment.objects:
            return []
        
        root = self.environment.objects[root_id]
        tree = [root]
        
        for child_id in root.children:
            tree.extend(self.get_object_tree(child_id))
        
        return tree