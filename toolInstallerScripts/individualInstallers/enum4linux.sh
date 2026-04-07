#!/bin/bash
# ------------------------------------
# Enum4linux Installer Script
# ------------------------------------

TOOL_NAME="Enum4linux"

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
echo "2) Clonar versão original via GitHub"
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
            echo -e "${GREEN}[+] A instalar enum4linux${NC}"
            sudo apt update
            sudo apt install -y enum4linux
            ;;
        dnf)
            echo -e "${GREEN}[+] A instalar via dnf${NC}"
            sudo dnf install -y enum4linux
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
                    yay -Sy --noconfirm enum4linux
                else
                    sudo pacman -Sy --noconfirm enum4linux
                fi
            else
                sudo pacman -Sy --noconfirm enum4linux
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] A instalar via zypper${NC}"
            sudo zypper install -y enum4linux
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}[✓] $TOOL_NAME instalado!${NC}"
}

# ------------------------------------
# Clonar versão manual (GitHub)
# ------------------------------------
install_git() {
    echo -e "${BLUE}[*] A clonar Enum4linux...${NC}"

    # Remover pasta antiga
    if [ -d "enum4linux" ]; then
        rm -rf enum4linux
    fi

    git clone https://github.com/CiscoCXSecurity/enum4linux.git || exit 1

    sudo cp enum4linux/enum4linux.pl /usr/local/bin/enum4linux
    sudo chmod +x /usr/local/bin/enum4linux

    rm -rf enum4linux

    echo -e "${GREEN}[✓] $TOOL_NAME instalado manualmente!${NC}"
}

# ------------------------------------
# Remover ferramenta
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    case $PM in
        apt)
            sudo apt remove -y enum4linux
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y enum4linux
            ;;
        pacman)
            sudo pacman -R --noconfirm enum4linux
            ;;
        zypper)
            sudo zypper remove -y enum4linux
            ;;
    esac

    # Também remove binário manual
    if [ -f /usr/local/bin/enum4linux ]; then
        sudo rm -f /usr/local/bin/enum4linux
    fi

    echo -e "${GREEN}[✓] $TOOL_NAME removido!${NC}"
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
