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
        normalized = relative_path.replace('\\', '/').lstrip('/')

        if hasattr(sys, '_MEIPASS'):
            base_dirs = [Path(sys._MEIPASS)]
            path_logger.info(f"Executável PyInstaller detectado. MEIPASS: {base_dirs[0]}")
            debug_prefix = "[DEBUG EXE]"
        else:
            base_dir = Path(__file__).resolve().parent.parent
            # Some development layouts keep assets one level above the package dir.
            base_dirs = [base_dir, base_dir.parent]
            path_logger.info(f"Modo desenvolvimento. Diretórios base: {base_dirs}")
            debug_prefix = "[DEBUG DEV]"

        possible_paths = []
        for base in base_dirs:
            possible_paths.append(base / normalized)
            possible_paths.append(base / resource_type / normalized)
            possible_paths.append(base / "assets" / normalized)

            if normalized.startswith("assets/"):
                possible_paths.append(base / normalized[7:])
            if normalized.startswith("animations/"):
                possible_paths.append(base / normalized[11:])
            if "/" in normalized:
                possible_paths.append(base / normalized.split("/")[-1])

        # Explicit fallbacks for common renamed branding assets.
        alias_map = {
            "icons/app_icon.png": ["beatrooter_logo.svg", "icons/app_icon.ico"],
            "small logo.png": ["beatrooter_logo.svg"],
        }
        for alias in alias_map.get(normalized, []):
            for base in base_dirs:
                possible_paths.append(base / "assets" / alias)
                possible_paths.append(base / alias)

        unique_paths = []
        seen = set()
        for path in possible_paths:
            path_str = str(path)
            if path_str in seen:
                continue
            seen.add(path_str)
            unique_paths.append(path)

        path_logger.debug(f"Tentando {len(unique_paths)} caminhos possíveis")
        for i, path in enumerate(unique_paths):
            path_logger.debug(f"  [{i}] {path}")
            if path.exists():
                path_logger.info(f"✓ Encontrado em: {path}")
                print(f"{debug_prefix} Encontrado: {path}")
                return str(path)

        path_logger.warning(f"Nenhum caminho funcionou para: {relative_path}")
        print(f"{debug_prefix} Nenhum caminho funcionou para: {relative_path}")
        if unique_paths:
            return str(unique_paths[0])
        return str(base_dirs[0] / resource_type / normalized)
                
    except Exception as e:
        error_msg = f"[ERROR] Falha ao obter caminho: {relative_path}, erro: {e}"
        print(error_msg)
        path_logger.error(error_msg)
        return relative_path
