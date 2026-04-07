#!/bin/bash
# ------------------------------------
# SQLmap Installer Script
# ------------------------------------

TOOL_NAME="SQLmap"

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
            sudo apt install -y sqlmap
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y sqlmap
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"

            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo ""
                echo "1) pacman (repositório oficial)"
                echo "2) yay (AUR – versão mais recente)"
                read -p "Método [1-2]: " method

                if [ "$method" == "2" ]; then
                    yay -Sy --noconfirm sqlmap-git
                else
                    sudo pacman -Sy --noconfirm sqlmap
                fi
            else
                sudo pacman -Sy --noconfirm sqlmap
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y sqlmap
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

    echo -e "${BLUE}[*] A transferir SQLmap do GitHub...${NC}"

    if [ -d "/opt/sqlmap" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/sqlmap
    fi

    sudo git clone https://github.com/sqlmapproject/sqlmap.git /opt/sqlmap || exit 1

    sudo chmod +x /opt/sqlmap/sqlmap.py
    sudo ln -sf /opt/sqlmap/sqlmap.py /usr/bin/sqlmap

    echo ""
    echo -e "${GREEN}[✓] SQLmap instalado via GitHub!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt remove -y sqlmap
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y sqlmap
            ;;
        pacman)
            sudo pacman -R --noconfirm sqlmap
            ;;
        zypper)
            sudo zypper remove -y sqlmap
            ;;
    esac

    # Também remover instalação manual via GitHub
    if [ -d "/opt/sqlmap" ]; then
        sudo rm -rf /opt/sqlmap
    fi

    if [ -f "/usr/bin/sqlmap" ]; then
        sudo rm -f /usr/bin/sqlmap
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
