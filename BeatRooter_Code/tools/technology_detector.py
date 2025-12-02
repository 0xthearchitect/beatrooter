import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class TechnologyDetector:
    def __init__(self, sandbox_data: Dict[str, Any]):
        self.sandbox_data = sandbox_data
        self.detected_tech = {}
    
    def detect_technologies(self) -> Dict[str, Any]:
        self.detected_tech = {
            'backend': self._detect_backend(),
            'database': self._detect_database(),
            'frontend': self._detect_frontend(),
            'dependencies': self._detect_dependencies(),
            'ports': self._detect_ports(),
            'file_structure': self._analyze_file_structure()
        }
        return self.detected_tech
    
    def _detect_backend(self) -> Dict[str, Any]:
        backend_info = {
            'type': None,
            'framework': None,
            'language': None,
            'entry_point': None,
            'dependencies': []
        }
        
        for obj in self.sandbox_data.get('objects', []):
            obj_type = obj.get('type')

            if obj_type in ['flask', 'django']:
                backend_info.update({
                    'type': 'python',
                    'framework': obj_type,
                    'language': 'python'
                })
            elif obj_type in ['nodejs', 'express', 'nestjs']:
                backend_info.update({
                    'type': 'nodejs',
                    'framework': obj_type,
                    'language': 'javascript'
                })

            if obj_type == 'code_file' and obj.get('code_content'):
                code_content = obj['code_content']
                filename = obj.get('name', '').lower()
                
                if filename == 'package.json':
                    backend_info['type'] = 'nodejs'
                    backend_info['framework'] = 'nodejs'
                elif filename == 'requirements.txt':
                    backend_info['type'] = 'python'
                elif filename == 'app.py' or filename == 'server.py':
                    backend_info['entry_point'] = filename
                
                if code_content.get('language'):
                    lang = code_content['language'].lower()
                    if 'python' in lang:
                        backend_info.update({'type': 'python', 'language': 'python'})
                    elif 'javascript' in lang or 'node' in lang:
                        backend_info.update({'type': 'nodejs', 'language': 'javascript'})
        
        return backend_info
    
    def _detect_database(self) -> Dict[str, Any]:
        db_info = {
            'type': None,
            'version': None,
            'port': None,
            'credentials': {}
        }
        
        for obj in self.sandbox_data.get('objects', []):
            obj_type = obj.get('type')
            
            if obj_type in ['postgresql', 'mysql', 'mongodb', 'database']:
                db_info['type'] = obj_type
                db_info['version'] = obj.get('properties', {}).get('version')

                if obj.get('login_credentials'):
                    creds = obj['login_credentials']
                    db_info['credentials'] = {
                        'username': creds.get('username'),
                        'password': creds.get('password'),
                        'database': creds.get('database'),
                        'port': creds.get('port')
                    }
                    db_info['port'] = creds.get('port')
        
        return db_info
    
    def _detect_frontend(self) -> Dict[str, Any]:
        frontend_info = {
            'framework': None,
            'build_tool': None,
            'static_files': []
        }
        
        for obj in self.sandbox_data.get('objects', []):
            obj_type = obj.get('type')
            
            if obj_type in ['react', 'angular', 'vue']:
                frontend_info['framework'] = obj_type
            elif obj_type in ['html', 'css', 'javascript']:
                frontend_info['static_files'].append(obj_type)
        
        return frontend_info
    
    def _detect_dependencies(self) -> List[str]:
        dependencies = []
        
        for obj in self.sandbox_data.get('objects', []):
            if obj.get('type') == 'code_file' and obj.get('code_content'):
                code_content = obj['code_content']
                
                if obj.get('name', '').lower() == 'package.json':
                    try:
                        import json
                        package_content = code_content.get('source_code', '{}')
                        package_data = json.loads(package_content)
                        deps = package_data.get('dependencies', {})
                        dev_deps = package_data.get('devDependencies', {})
                        
                        dependencies.extend(list(deps.keys()))
                        dependencies.extend(list(dev_deps.keys()))
                    except:
                        pass
                
                elif obj.get('name', '').lower() == 'requirements.txt':
                    req_content = code_content.get('source_code', '')
                    for line in req_content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dependencies.append(line.split('==')[0].split('>=')[0])
                
                elif code_content.get('dependencies'):
                    dependencies.extend(code_content['dependencies'])
        
        return list(set(dependencies))
    
    def _detect_ports(self) -> Dict[str, int]:
        ports = {
            'app': 5000,
            'database': 5432,
            'frontend': 3000
        }
        
        for obj in self.sandbox_data.get('objects', []):
            if obj.get('login_credentials'):
                port = obj['login_credentials'].get('port')
                if port and port > 0:
                    if obj.get('type') in ['postgresql', 'mysql', 'mongodb', 'database']:
                        ports['database'] = port
                    else:
                        ports['app'] = port
        
        return ports
    
    def _analyze_file_structure(self) -> Dict[str, Any]:
        structure = {
            'has_static': False,
            'has_templates': False,
            'has_package_json': False,
            'has_requirements': False,
            'entry_points': []
        }
        
        for obj in self.sandbox_data.get('objects', []):
            name = obj.get('name', '').lower()
            obj_type = obj.get('type')
            
            if obj_type == 'web_folder':
                folder_name = name.lower()
                if 'static' in folder_name or 'public' in folder_name:
                    structure['has_static'] = True
                if 'templates' in folder_name or 'views' in folder_name:
                    structure['has_templates'] = True
            
            elif obj_type == 'code_file':
                if name == 'package.json':
                    structure['has_package_json'] = True
                elif name == 'requirements.txt':
                    structure['has_requirements'] = True
                elif any(ep in name for ep in ['app.', 'server.', 'index.', 'main.']):
                    structure['entry_points'].append(name)
        
        return structure