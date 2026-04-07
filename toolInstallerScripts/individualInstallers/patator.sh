#!/bin/bash
# ------------------------------------
# Patator Installer Script
# ------------------------------------

TOOL_NAME="Patator"

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
echo "2) Instalar via GitHub (última versão)"
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
            echo -e "${GREEN}[+] Detectado APT (Debian/Ubuntu)${NC}"
            sudo apt update
            sudo apt install -y patator
            ;;
        dnf)
            echo -e "${RED}[!] Patator NÃO está nos repos oficiais Fedora.${NC}"
            echo -e "${YELLOW}Use a opção 2 para instalar via GitHub.${NC}"
            exit 1
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            
            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo ""
                echo "1) Instalar via GitHub (recomendado)"
                echo "2) yay (AUR)"
                read -p "Método [1-2]: " method
                
                if [ "$method" == "2" ]; then
                    yay -Sy --noconfirm patator
                else
                    install_github
                    exit 0
                fi
            else
                echo -e "${YELLOW}[!] Instale via GitHub (opção 2)${NC}"
                exit 1
            fi
            ;;
        zypper)
            echo -e "${RED}[!] Patator NÃO está nos repos oficiais OpenSUSE.${NC}"
            echo -e "${YELLOW}Use a opção 2 para instalar via GitHub.${NC}"
            exit 1
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME instalado com sucesso!${NC}"
}

# ------------------------------------
# Instalar via GitHub
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A instalar dependências...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git python3 python3-pip
            ;;
        dnf)
            sudo dnf install -y git python3 python3-pip
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git python python-pip
            ;;
        zypper)
            sudo zypper install -y git python3 python3-pip
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac

    echo -e "${BLUE}[*] A transferir Patator do GitHub...${NC}"

    if [ -d "/opt/patator" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/patator
    fi

    sudo git clone https://github.com/lanjelot/patator.git /opt/patator || exit 1

    cd /opt/patator || exit 1

    echo -e "${BLUE}[*] A instalar via pip...${NC}"
    sudo pip3 install -r requirements.txt --break-system-packages 2>/dev/null || sudo pip3 install -r requirements.txt

    echo -e "${BLUE}[*] A criar link simbólico...${NC}"
    sudo chmod +x /opt/patator/patator.py
    sudo ln -sf /opt/patator/patator.py /usr/local/bin/patator

    echo ""
    echo -e "${GREEN}[✓] Patator instalado via GitHub!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    case $PM in
        apt)
            sudo apt remove -y patator
            sudo apt autoremove -y
            ;;
        pacman)
            sudo pacman -R --noconfirm patator 2>/dev/null
            ;;
    esac

    # Remover instalação via GitHub
    if [ -d "/opt/patator" ]; then
        sudo rm -rf /opt/patator
    fi

    if [ -f "/usr/local/bin/patator" ]; then
        sudo rm -f /usr/local/bin/patator
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
        install_github
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
