# file_icon_manager.py - ATUALIZADO PARA ÍCONES GRANDES
import os
import sys
import winreg
import ctypes
import subprocess
from pathlib import Path

class FileIconManager:
    def __init__(self):
        self.app_name = "BeatRooter"
        
    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def register_file_associations(self):
        """Registra as associações de arquivo quando a aplicação inicia"""
        if not self.is_admin():
            print("Aviso: Execute como administrador para registrar ícones")
            return False
        
        try:
            # Usar diretório raiz do projeto
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent
            
            app_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            
            print(f"Base directory: {base_dir}")
            
            # Caminho para ícones
            icons_dir = base_dir / "assets" / "icons"
            brs_icon = icons_dir / "brs_file.ico"
            brt_icon = icons_dir / "brt_file.ico"
            
            print(f"BRS icon: {brs_icon} (exists: {brs_icon.exists()})")
            print(f"BRT icon: {brt_icon} (exists: {brt_icon.exists()})")
            
            # Se ícones não existem, criar ícones profissionais
            if not brs_icon.exists() or not brt_icon.exists():
                print("Criando ícones profissionais...")
                self._create_professional_icons(icons_dir)
            
            # Registrar extensões
            self._register_extension(".brs", "SandboxFile", 
                                   "BeatRooter Sandbox File",
                                   str(brs_icon),
                                   f'"{app_path}" "%1"')
            
            self._register_extension(".brt", "InvestigationFile",
                                   "BeatRooter Investigation File", 
                                   str(brt_icon),
                                   f'"{app_path}" "%1"')
            
            # Forçar atualização
            self._force_icon_refresh()
            
            print("✅ Ícones registrados com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_professional_icons(self, icons_dir):
        """Cria ícones profissionais com múltiplos tamanhos"""
        try:
            from PIL import Image, ImageDraw
            
            icons_dir.mkdir(parents=True, exist_ok=True)
            
            def create_icon_sizes(text, bg_color, filename):
                sizes = [16, 32, 48, 64, 128, 256]
                images = []
                
                for size in sizes:
                    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    
                    # Fundo arredondado
                    margin = max(2, size // 16)
                    draw.rounded_rectangle(
                        [margin, margin, size-margin, size-margin],
                        radius=size//8,
                        fill=bg_color,
                        outline=(255, 255, 255),
                        width=max(1, size//64)
                    )
                    
                    # Texto
                    font_size = max(6, size // 3)
                    try:
                        from PIL import ImageFont
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (size - text_width) // 2
                    y = (size - text_height) // 2
                    
                    # Sombra do texto
                    shadow_offset = max(1, size // 64)
                    draw.text((x+shadow_offset, y+shadow_offset), text, 
                             font=font, fill=(0, 0, 0, 128))
                    # Texto principal
                    draw.text((x, y), text, font=font, fill=(255, 255, 255))
                    
                    images.append(img)
                
                # Salvar como ICO com múltiplos tamanhos
                if images:
                    images[0].save(
                        filename,
                        format='ICO',
                        sizes=[(img.width, img.height) for img in images],
                        append_images=images[1:]
                    )
                    print(f"Ícone criado: {filename}")
            
            # Criar ícones
            create_icon_sizes("BRS", (33, 150, 243), icons_dir / "brs_file.ico")
            create_icon_sizes("BRT", (244, 67, 54), icons_dir / "brt_file.ico")
            create_icon_sizes("BR", (76, 175, 80), icons_dir / "app_icon.ico")
            
        except Exception as e:
            print(f"Erro ao criar ícones: {e}")
            # Fallback para ícones simples
            self._create_fallback_icons(icons_dir)
    
    def _create_fallback_icons(self, icons_dir):
        """Fallback para ícones básicos"""
        try:
            from PIL import Image, ImageDraw
            
            icons_dir.mkdir(parents=True, exist_ok=True)
            
            def create_simple_icon(text, bg_color, filename):
                # Apenas tamanho 32x32 para fallback
                img = Image.new('RGB', (32, 32), bg_color)
                draw = ImageDraw.Draw(img)
                
                bbox = draw.textbbox((0, 0), text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (32 - text_width) // 2
                y = (32 - text_height) // 2
                
                draw.text((x, y), text, fill='white')
                img.save(filename, format='ICO')
            
            create_simple_icon("BRS", (33, 150, 243), icons_dir / "brs_file.ico")
            create_simple_icon("BRT", (244, 67, 54), icons_dir / "brt_file.ico")
            
        except Exception as e:
            print(f"Erro no fallback: {e}")
    
    def _register_extension(self, extension, file_type, description, icon_path, app_command):
        """Registra uma extensão específica"""
        try:
            prog_id = f"{self.app_name}.{file_type}"
            
            print(f"Registrando {extension}...")
            
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, prog_id)
            
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, prog_id) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, description)
                
                with winreg.CreateKey(key, "DefaultIcon") as icon_key:
                    winreg.SetValueEx(icon_key, "", 0, winreg.REG_SZ, icon_path)
                
                with winreg.CreateKey(key, "shell\\open\\command") as cmd_key:
                    winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, app_command)
            
            print(f"✅ {extension} registrado")
                    
        except Exception as e:
            print(f"❌ Erro em {extension}: {e}")
            raise
    
    def _force_icon_refresh(self):
        """Força atualização completa dos ícones"""
        try:
            print("Atualizando ícones...")
            
            # Limpar cache de ícones
            subprocess.run('ie4uinit.exe -ClearIconCache', shell=True, capture_output=True)
            
            # Recarregar Explorer
            subprocess.run('taskkill /f /im explorer.exe', shell=True, capture_output=True)
            subprocess.run('start explorer.exe', shell=True, capture_output=True)
            
            print("✅ Sistema atualizado")
            
        except Exception as e:
            print(f"⚠️ Aviso: {e}")