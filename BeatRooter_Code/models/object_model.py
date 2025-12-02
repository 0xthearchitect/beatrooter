from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QPointF
from enum import Enum

class ObjectCategory(Enum):
    OPERATING_SYSTEM = "operating_system"
    NETWORK = "network"
    WEB = "web"
    ORGANIZATION = "organization"

class ObjectType(Enum):
    # Operating Systems
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    
    WINDOWS_10 = "windows_10"
    WINDOWS_11 = "windows_11"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    ARCH = "arch"
    CENTOS = "centos"
    KALI = "kali"
    
    SERVICE = "service"
    PROCESS = "process"
    SCHEDULED_TASK = "scheduled_task"
    
    FOLDER = "folder"
    FILE = "file"
    REGISTRY_KEY = "registry_key"
    CONFIG_FILE = "config_file"

    NETWORK_INTERFACE = "network_interface"
    OPEN_PORT = "open_port"
    RUNNING_SERVICE = "running_service"
    INSTALLED_SOFTWARE = "installed_software"
    USER_ACCOUNT = "user_account"
    SECURITY_POLICY = "security_policy"
    SYSTEM_INFO = "system_info"
    
    # Network Devices
    COMPUTER = "computer"
    SERVER = "server"
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    ACCESS_POINT = "access_point"
    MODEM = "modem"
    CONTAINER = "container"
    
    # Web Technologies
    APACHE = "apache"
    NGINX = "nginx"
    IIS = "iis"
    TOMCAT = "tomcat"
    
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    REDIS = "redis"
    DATABASE = "database"
    
    DJANGO = "django"
    FLASK = "flask"
    NODEJS = "nodejs"
    SPRING = "spring"
    EXPRESS = "express"
    NESTJS = "nestjs"
    RAILS = "rails"

    REACT = "react"
    ANGULAR = "angular"
    VUE = "vue"
    
    WEB_FOLDER = "web_folder"
    WEB_APP = "web_app"
    CODE_FILE = "code_file"
    API_ENDPOINT = "api_endpoint"

    OAUTH = "oauth"
    JWT = "jwt"
    SAML = "saml"
    
    PROJECT = "project"
    TEAM = "team"
    USER = "user"
    GROUP = "group"

@dataclass
class SandboxConnection:
    id: str
    source_id: str
    target_id: str
    connection_type: str = "network"
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'connection_type': self.connection_type,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            id=data['id'],
            source_id=data['source_id'],
            target_id=data['target_id'],
            connection_type=data.get('connection_type', 'network'),
            properties=data.get('properties', {})
        )
    
@dataclass
class CodeContent:
    language: str
    source_code: str
    dependencies: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    build_commands: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'language': self.language,
            'source_code': self.source_code,
            'dependencies': self.dependencies,
            'environment_vars': self.environment_vars,
            'build_commands': self.build_commands
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            language=data.get('language', ''),
            source_code=data.get('source_code', ''),
            dependencies=data.get('dependencies', []),
            environment_vars=data.get('environment_vars', {}),
            build_commands=data.get('build_commands', [])
        )

@dataclass
class LoginCredentials:
    username: str
    password: str = ""
    url: str = ""
    port: int = 0
    database: str = ""
    additional_fields: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'password': self.password,
            'url': self.url,
            'port': self.port,
            'database': self.database,
            'additional_fields': self.additional_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            username=data.get('username', ''),
            password=data.get('password', ''),
            url=data.get('url', ''),
            port=data.get('port', 0),
            database=data.get('database', ''),
            additional_fields=data.get('additional_fields', {})
        )

@dataclass
class SandboxObject:
    id: str
    object_type: ObjectType
    category: ObjectCategory
    position: QPointF
    name: str
    properties: Dict[str, Any]
    children: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    connections: List[str] = field(default_factory=list)
    code_content: Optional[CodeContent] = None
    login_credentials: Optional[LoginCredentials] = None
    
    def __init__(self, obj_id: str, obj_type: ObjectType, category: ObjectCategory, position: QPointF, 
                 name: str, properties: Dict[str, Any] = None):
        self.id = obj_id
        self.object_type = obj_type
        self.category = category
        self.position = position
        self.name = name
        self.properties = properties or {}
        self.children = []
        self.parent_id = None
        self.connections = []
        self.code_content = None
        self.login_credentials = None
    
    def add_child(self, child_id: str):
        if child_id not in self.children:
            self.children.append(child_id)
    
    def remove_child(self, child_id: str):
        if child_id in self.children:
            self.children.remove(child_id)
    
    def add_connection(self, connection_id: str):
        if connection_id not in self.connections:
            self.connections.append(connection_id)
    
    def remove_connection(self, connection_id: str):
        if connection_id in self.connections:
            self.connections.remove(connection_id)
    
    def set_code_content(self, language: str, source_code: str, dependencies: List[str] = None,
                        environment_vars: Dict[str, str] = None, build_commands: List[str] = None):
        self.code_content = CodeContent(
            language=language,
            source_code=source_code,
            dependencies=dependencies or [],
            environment_vars=environment_vars or {},
            build_commands=build_commands or []
        )
    
    def set_login_credentials(self, username: str, password: str = "", url: str = "", 
                             port: int = 0, database: str = "", additional_fields: Dict[str, str] = None):
        self.login_credentials = LoginCredentials(
            username=username,
            password=password,
            url=url,
            port=port,
            database=database,
            additional_fields=additional_fields or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            'id': self.id,
            'type': self.object_type.value,
            'category': self.category.value,
            'position': {
                'x': self.position.x(),
                'y': self.position.y()
            },
            'name': self.name,
            'properties': self.properties,
            'children': self.children,
            'parent_id': self.parent_id,
            'connections': self.connections
        }
        
        if self.code_content:
            data['code_content'] = self.code_content.to_dict()
        
        if self.login_credentials:
            data['login_credentials'] = self.login_credentials.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        position = QPointF(data['position']['x'], data['position']['y'])
        obj = cls(
            data['id'],
            ObjectType(data['type']),
            ObjectCategory(data['category']),
            position,
            data['name'],
            data['properties']
        )
        obj.children = data.get('children', [])
        obj.parent_id = data.get('parent_id')
        obj.connections = data.get('connections', [])
        
        if 'code_content' in data:
            obj.code_content = CodeContent.from_dict(data['code_content'])
        
        if 'login_credentials' in data:
            obj.login_credentials = LoginCredentials.from_dict(data['login_credentials'])
        
        return obj

@dataclass
class SandboxEnvironment:
    objects: Dict[str, SandboxObject] = field(default_factory=dict)
    connections: Dict[str, SandboxConnection] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self):
        self.objects = {}
        self.connections = {}
        self.metadata = {
            'title': 'Untitled Sandbox',
            'created': '',
            'environment_type': 'network_topology',
            'version': '1.0'
        }
    
    def add_connection(self, connection: SandboxConnection):
        self.connections[connection.id] = connection
        print(f"DEBUG: Connection added to environment - ID: {connection.id}")
    
    def remove_connection(self, connection_id: str):
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            if connection.source_id in self.objects:
                self.objects[connection.source_id].remove_connection(connection_id)
            if connection.target_id in self.objects:
                self.objects[connection.target_id].remove_connection(connection_id)
            
            del self.connections[connection_id]

    
    def add_object(self, obj: SandboxObject):
        self.objects[obj.id] = obj
    
    def remove_object(self, obj_id: str):
        if obj_id in self.objects:
            obj = self.objects[obj_id]
            if obj.parent_id and obj.parent_id in self.objects:
                self.objects[obj.parent_id].remove_child(obj_id)
            
            for child_id in obj.children[:]:
                self.remove_object(child_id)
            
            del self.objects[obj_id]
    
    def get_object(self, obj_id: str) -> Optional[SandboxObject]:
        return self.objects.get(obj_id)
    
    def get_children(self, parent_id: str) -> List[SandboxObject]:
        parent = self.get_object(parent_id)
        if not parent:
            return []
        return [self.objects[child_id] for child_id in parent.children if child_id in self.objects]
    
    def to_dict(self) -> Dict[str, Any]:
        print(f"DEBUG: Saving environment - Objects: {len(self.objects)}, Connections: {len(self.connections)}")
        
        data = {
            'metadata': self.metadata,
            'objects': [obj.to_dict() for obj in self.objects.values()],
            'connections': [conn.to_dict() for conn in self.connections.values()]
        }
        
        print(f"DEBUG: Connections to save: {[conn.id for conn in self.connections.values()]}")
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        print(f"DEBUG: Loading environment - Objects in file: {len(data.get('objects', []))}, Connections in file: {len(data.get('connections', []))}")
        
        env = cls()
        env.metadata = data.get('metadata', {})
        
        for obj_data in data.get('objects', []):
            obj = SandboxObject.from_dict(obj_data)
            env.objects[obj.id] = obj
        
        for conn_data in data.get('connections', []):
            print(f"DEBUG: Loading connection: {conn_data}")
            connection = SandboxConnection.from_dict(conn_data)
            env.connections[connection.id] = connection
            
            if connection.source_id in env.objects:
                env.objects[connection.source_id].add_connection(connection.id)
            if connection.target_id in env.objects:
                env.objects[connection.target_id].add_connection(connection.id)
        
        print(f"DEBUG: After loading - Objects: {len(env.objects)}, Connections: {len(env.connections)}")
        return env