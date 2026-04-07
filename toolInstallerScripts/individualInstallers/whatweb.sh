#!/bin/bash
# ------------------------------------
# WhatWeb Installer Script
# ------------------------------------

TOOL_NAME="WhatWeb"

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
            echo -e "${GREEN}[+] Detectado APT (Debian/Ubuntu/Kali)${NC}"
            sudo apt update
            sudo apt install -y whatweb
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y whatweb
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"

            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo ""
                echo "1) pacman (repositório oficial)"
                echo "2) yay (AUR – versão git)"
                read -p "Método [1-2]: " method

                if [ "$method" == "2" ]; then
                    yay -Sy --noconfirm whatweb-git
                else
                    sudo pacman -Sy --noconfirm whatweb
                fi
            else
                sudo pacman -Sy --noconfirm whatweb
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y whatweb
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
# Instalar via GitHub (última versão)
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A instalar dependências...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git ruby ruby-dev build-essential
            ;;
        dnf)
            sudo dnf install -y git ruby ruby-devel gcc make
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git ruby base-devel
            ;;
        zypper)
            sudo zypper install -y git ruby ruby-devel gcc make
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac

    echo -e "${BLUE}[*] A transferir WhatWeb do GitHub...${NC}"

    if [ -d "/opt/whatweb" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/whatweb
    fi

    sudo git clone https://github.com/urbanadventurer/WhatWeb /opt/whatweb || exit 1

    echo -e "${BLUE}[*] A instalar gems Ruby necessárias...${NC}"
    cd /opt/whatweb || exit 1
    sudo gem install bundler
    sudo bundle install || true

    sudo ln -sf /opt/whatweb/whatweb /usr/bin/whatweb

    echo ""
    echo -e "${GREEN}[✓] WhatWeb instalado via GitHub!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt remove -y whatweb
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y whatweb
            ;;
        pacman)
            sudo pacman -R --noconfirm whatweb
            ;;
        zypper)
            sudo zypper remove -y whatweb
            ;;
    esac

    # Remover instalação via GitHub
    if [ -d "/opt/whatweb" ]; then
        sudo rm -rf /opt/whatweb
    fi

    if [ -f "/usr/bin/whatweb" ]; then
        sudo rm -f /usr/bin/whatweb
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
