#!/bin/bash
# ------------------------------------
# Steghide Installer Script
# ------------------------------------

TOOL_NAME="Steghide"

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
echo "1) Instalar via repositório oficial"
echo "2) Remover"
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
            echo -e "${GREEN}[+] Detectado APT (Debian/Ubuntu)${NC}"
            sudo apt update
            sudo apt install -y steghide
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y steghide
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
                    yay -Sy --noconfirm steghide
                else
                    sudo pacman -Sy --noconfirm steghide
                fi
            else
                sudo pacman -Sy --noconfirm steghide
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y steghide
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME instalado com sucesso!${NC}"
    echo -e "${GREEN}[✓] Esconder: steghide embed -cf image.jpg -ef secret.txt${NC}"
    echo -e "${GREEN}[✓] Extrair: steghide extract -sf image.jpg${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    case $PM in
        apt)
            sudo apt remove -y steghide
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y steghide
            ;;
        pacman)
            sudo pacman -R --noconfirm steghide
            ;;
        zypper)
            sudo zypper remove -y steghide
            ;;
    esac

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
