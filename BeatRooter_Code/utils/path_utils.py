import os
import sys
from pathlib import Path
import logging
import traceback

def setup_path_logger():
    logger = logging.getLogger('path_utils')
    logger.setLevel(logging.WARNING)
    
    try:
        log_file = "path_utils_debug.log"
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    except:
        pass
    
    return logger

path_logger = setup_path_logger()

def get_resource_path(relative_path, resource_type='assets'):
    try:
        print(f"[DEBUG PATH] Procurando: '{relative_path}', tipo: '{resource_type}'")
        path_logger.debug(f"Procurando recurso: {relative_path}, tipo: {resource_type}")
        
        if hasattr(sys, '_MEIPASS'):
            base_path = Path(sys._MEIPASS)
            path_logger.info(f"Executável PyInstaller detectado. MEIPASS: {base_path}")

            try:
                if base_path.exists():
                    items = list(base_path.glob("*"))
                    path_logger.debug(f"Conteúdo do diretório base ({len(items)} itens):")
                    for item in items[:10]:
                        path_logger.debug(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
            except Exception as e:
                path_logger.debug(f"Não foi possível listar diretório base: {e}")
            
            possible_paths = []
            
            possible_paths.append(base_path / relative_path)

            possible_paths.append(base_path / resource_type / relative_path)
            
            if relative_path.startswith('assets/'):
                possible_paths.append(base_path / relative_path[7:])

            if relative_path.startswith('animations/'):
                possible_paths.append(base_path / relative_path[11:])

            if '/' in relative_path or '\\' in relative_path:
                parts = relative_path.replace('\\', '/').split('/')
                if len(parts) > 1:
                    possible_paths.append(base_path / parts[-1])
            
            path_logger.debug(f"Tentando {len(possible_paths)} caminhos possíveis")
            
            for i, path in enumerate(possible_paths):
                path_logger.debug(f"  [{i}] {path}")
                if path.exists():
                    path_logger.info(f"✓ Encontrado em: {path}")
                    print(f"[DEBUG EXE] Encontrado: {path}")
                    return str(path)
            
            path_logger.warning(f"Nenhum caminho funcionou para: {relative_path}")
            print(f"[DEBUG EXE] Nenhum caminho funcionou para: {relative_path}")
            
            return str(possible_paths[0] if possible_paths else base_path / relative_path)
            
        else:
            base_dir = Path(__file__).parent.parent
            path_logger.info(f"Modo desenvolvimento. Diretório base: {base_dir}")

            possible_paths = []
            
            possible_paths.append(base_dir / "assets" / relative_path)

            possible_paths.append(base_dir / relative_path)
            
            if relative_path.startswith('assets/'):
                possible_paths.append(base_dir / relative_path)
            
            possible_paths.append(base_dir / resource_type / relative_path)
            
            path_logger.debug(f"Tentando {len(possible_paths)} caminhos possíveis no dev")
            
            for i, path in enumerate(possible_paths):
                path_logger.debug(f"  [{i}] {path}")
                if path.exists():
                    path_logger.info(f"✓ Encontrado em: {path}")
                    print(f"[DEBUG DEV] Encontrado: {path}")
                    return str(path)
            
            path_logger.warning(f"Nenhum caminho funcionou no dev para: {relative_path}")
            print(f"[DEBUG DEV] Nenhum caminho funcionou para: {relative_path}")

            last_path = possible_paths[0] if possible_paths else base_dir / "assets" / relative_path
            last_path.parent.mkdir(parents=True, exist_ok=True)
            return str(last_path)
                
    except Exception as e:
        error_msg = f"[ERROR] Falha ao obter caminho: {relative_path}, erro: {e}"
        print(error_msg)
        path_logger.error(error_msg)
        return relative_path