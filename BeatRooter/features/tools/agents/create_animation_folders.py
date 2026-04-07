import os
import shutil

def create_animation_structure():
    base_folders = [
        "assets/animations/nabia_intro",
        "assets/animations/nabia_ready", 
        "assets/animations/nabia_complete"
    ]
    
    for folder in base_folders:
        os.makedirs(folder, exist_ok=True)
        print(f"Pasta criada: {folder}")

    example_images = [
        "ola1.png", "ola2.png", "ola3.png", "ola4.png", "ola5.png", "ola6.png", "ola7.png", "ola8.png",
        "nabia_destruidora.png", "10.png"
    ]
    
    for img in example_images:
        open(f"assets/animations/placeholder_{img}", 'w').close()
    
    print("\nEstrutura criada! Agora substitua os arquivos placeholder pelas suas imagens:")
    print("- nabia_intro/: Coloque os frames da animação (múltiplas imagens)")
    print("- nabia_ready/: Coloque 1 imagem estática")
    print("- nabia_complete/: Coloque 1 imagem estática")

if __name__ == "__main__":
    create_animation_structure()