#!/bin/bash
# ------------------------------------
# Hydra Installer Script
# ------------------------------------

TOOL_NAME="Hydra"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo "======================================"
echo "     INSTALAR/REMOVER $TOOL_NAME"
echo "======================================"
echo ""
echo "1) Instalar via repositório"
echo "2) Compilar manualmente (GitHub - THC Hydra)"
echo "3) Remover"
echo "0) Sair"
echo ""
read -p "Escolha uma opção: " opcao

# ------------------------------------
# Detectar gestor de pacotes
# ------------------------------------
detect_pm() {
    if command -v apt >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v pacman >/dev/null 2>&1; then
        echo "pacman"
    elif command -v zypper >/dev/null 2>&1; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

# ------------------------------------
# Instalar via repositório
# ------------------------------------
install_repo() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A detectar gestor de pacotes: $PM${NC}"

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y hydra
            ;;
        dnf)
            sudo dnf install -y hydra
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            
            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo ""
                echo "1) pacman (repositório oficial)"
                echo "2) yay (AUR)"
                read -p "Método [1-2]: " method
                
                if [ "$method" == "2" ]; then
                    yay -Sy --noconfirm hydra
                else
                    sudo pacman -Sy --noconfirm hydra
                fi
            else
                sudo pacman -Sy --noconfirm hydra
            fi
            ;;
        zypper)
            sudo zypper install -y hydra
            ;;
        *)
            echo -e "${RED}[!] Nenhum gestor suportado detectado.${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}[✓] Hydra instalado com sucesso!${NC}"
}

# ------------------------------------
# Compilar Hydra manualmente
# ------------------------------------
install_git() {
    echo -e "${BLUE}[*] A clonar repositório THC Hydra...${NC}"

    # Apagar diretório anterior
    rm -rf hydra 2>/dev/null

    git clone https://github.com/vanhauser-thc/thc-hydra.git hydra || {
        echo -e "${RED}[✗] Falha ao clonar repositório.${NC}"
        exit 1
    }

    cd hydra || exit 1

    echo -e "${BLUE}[*] A compilar...${NC}"
    ./configure
    make
    sudo make install

    cd ..
    rm -rf hydra

    echo -e "${GREEN}[✓] Hydra compilado e instalado!${NC}"
}

# ------------------------------------
# Remover Hydra
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover Hydra...${NC}"

    case $PM in
        apt)
            sudo apt remove -y hydra && sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y hydra
            ;;
        pacman)
            sudo pacman -R --noconfirm hydra
            ;;
        zypper)
            sudo zypper remove -y hydra
            ;;
    esac

    # Remover binários compilados manualmente
    if command -v hydra >/dev/null 2>&1; then
        sudo rm -f "$(command -v hydra)"
    fi

    echo -e "${GREEN}[✓] Hydra removido!${NC}"
}

# ------------------------------------
# Executar opção
# ------------------------------------
case $opcao in
    1)
        install_repo
        ;;
    2)
        install_git
        ;;
    3)
        remove_tool
        ;;
    0)
        echo "A sair..."
        exit 0
        ;;
    *)
        echo -e "${RED}Opção inválida.${NC}"
        exit 1
        ;;
esac
