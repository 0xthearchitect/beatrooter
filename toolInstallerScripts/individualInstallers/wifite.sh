#!/bin/bash
# ------------------------------------
# Wifite Installer Script
# ------------------------------------

TOOL_NAME="Wifite"

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
            sudo apt install -y wifite aircrack-ng hcxdumptool hcxtools reaver bully
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y wifite aircrack-ng reaver
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            sudo pacman -Sy --noconfirm wifite aircrack-ng reaver bully
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y wifite aircrack-ng reaver
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
# Instalar via GitHub (Wifite2 – última versão)
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A instalar dependências...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git python3 python3-pip aircrack-ng hcxdumptool hcxtools reaver bully
            ;;
        dnf)
            sudo dnf install -y git python3 python3-pip aircrack-ng reaver bully
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git python aircrack-ng reaver bully
            ;;
        zypper)
            sudo zypper install -y git python3 python3-pip aircrack-ng reaver
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac

    echo -e "${BLUE}[*] A transferir Wifite (Wifite2) do GitHub...${NC}"

    if [ -d "/opt/wifite" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/wifite
    fi

    sudo git clone https://github.com/derv82/wifite2.git /opt/wifite || exit 1
    sudo chmod +x /opt/wifite/wifite.py

    echo -e "${BLUE}[*] A criar link simbólico...${NC}"
    sudo ln -sf /opt/wifite/wifite.py /usr/bin/wifite

    echo ""
    echo -e "${GREEN}[✓] Wifite instalado via GitHub!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt remove -y wifite
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y wifite
            ;;
        pacman)
            sudo pacman -R --noconfirm wifite
            ;;
        zypper)
            sudo zypper remove -y wifite
            ;;
    esac

    # Remover instalação via GitHub
    if [ -d "/opt/wifite" ]; then
        sudo rm -rf /opt/wifite
    fi

    if [ -f "/usr/bin/wifite" ]; then
        sudo rm -f /usr/bin/wifite
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
