import os
from models.object_model import SandboxObject, ObjectType
from PyQt6.QtCore import QPointF

class SystemAnalysisFilter:
    
    @staticmethod
    def filter_essential_components(all_objects, max_objects=50):
        if len(all_objects) <= max_objects:
            return all_objects
        
        scored_objects = []
        for obj in all_objects:
            score = SystemAnalysisFilter.calculate_importance_score(obj)
            scored_objects.append((score, obj))

        scored_objects.sort(key=lambda x: x[0], reverse=True)
        
        return SystemAnalysisFilter.balance_categories(scored_objects, max_objects)

    @staticmethod
    def balance_categories(scored_objects, max_objects):
        categorized = {
            'system': [],
            'network': [],
            'security': [],
            'services': [],
            'processes': [],
            'users': []
        }

        for score, obj in scored_objects:
            obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
            
            if obj_type in ['SYSTEM_INFO']:
                categorized['system'].append((score, obj))
            elif any(net_key in obj_type.lower() for net_key in ['network', 'interface', 'port']):
                categorized['network'].append((score, obj))
            elif any(sec_key in obj_type.lower() for sec_key in ['security', 'firewall', 'policy']):
                categorized['security'].append((score, obj))
            elif obj_type in ['RUNNING_SERVICE']:
                categorized['services'].append((score, obj))
            elif obj_type in ['PROCESS']:
                categorized['processes'].append((score, obj))
            elif obj_type in ['USER_ACCOUNT']:
                categorized['users'].append((score, obj))
            else:
                categorized['system'].append((score, obj))
        
        target_per_category = max(3, max_objects // 6)
        result = []
        
        for category, objects in categorized.items():
            if objects:
                objects.sort(key=lambda x: x[0], reverse=True)
                taken = min(target_per_category, len(objects))
                result.extend([obj for score, obj in objects[:taken]])
        
        if len(result) < max_objects:
            remaining = max_objects - len(result)
            all_included = set(result)
            additional = []
            for score, obj in scored_objects:
                if obj not in all_included:
                    additional.append((score, obj))
            
            additional.sort(key=lambda x: x[0], reverse=True)
            result.extend([obj for score, obj in additional[:remaining]])
        
        return result

    @staticmethod
    def calculate_importance_score(obj):
        score = 0
        
        type_weights = {
            'SYSTEM_INFO': 100,
            'NETWORK_INTERFACE': 85,
            'OPEN_PORT': 80,
            'RUNNING_SERVICE': 75,
            'SECURITY_POLICY': 70,
            'USER_ACCOUNT': 65,
            'INSTALLED_SOFTWARE': 60,
            'PROCESS': 55
        }
        
        obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
        score += type_weights.get(obj_type, 50)
        
        props = obj.properties if hasattr(obj, 'properties') else {}
        
        if props.get('status') == 'running':
            score += 15
        
        if any(net_key in str(props).lower() for net_key in ['network', 'interface', 'port']):
            score += 10
        
        if any(sec_key in str(props).lower() for sec_key in ['security', 'firewall', 'policy']):
            score += 12
        
        name = obj.name.lower() if hasattr(obj, 'name') else str(obj).lower()
        
        critical_keywords = [
            'system', 'windows', 'linux', 'network', 'security',
            'ssh', 'http', 'https', 'dns', 'dhcp', 'firewall'
        ]
        
        for keyword in critical_keywords:
            if keyword in name:
                score += 8
        
        return score

    @staticmethod
    def group_similar_objects(objects):
        grouped = {}
        
        for obj in objects:
            obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)

            if obj_type in ['PROCESS', 'SERVICE']:
                status = obj.properties.get('status', 'unknown') if hasattr(obj, 'properties') else 'unknown'
                group_key = f"{obj_type}_{status}"
            elif obj_type in ['FILE', 'LOG']:
                name = obj.name.lower() if hasattr(obj, 'name') else str(obj).lower()
                if '.' in name:
                    ext = name.split('.')[-1]
                    group_key = f"{obj_type}_{ext}"
                else:
                    group_key = f"{obj_type}_other"
            else:
                group_key = obj_type
            
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(obj)

        result = []
        for group_key, group_objects in grouped.items():
            if len(group_objects) <= 5:
                result.extend(group_objects)
            else:
                scored = [(SystemAnalysisFilter.calculate_importance_score(obj), obj) for obj in group_objects]
                scored.sort(key=lambda x: x[0], reverse=True)
                result.extend([obj for score, obj in scored[:3]])
        
        return result