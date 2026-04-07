#!/bin/bash
# ------------------------------------
# Searchsploit Installer Script
# ------------------------------------

TOOL_NAME="Searchsploit"

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
echo "2) Instalar via GitHub (ExploitDB completo)"
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
            sudo apt install -y exploitdb
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y exploitdb
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            sudo pacman -Sy --noconfirm exploitdb
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y exploitdb
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}[✓] Searchsploit instalado com sucesso!${NC}"
}

# ------------------------------------
# Instalar via GitHub (ExploitDB)
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A instalar Searchsploit via GitHub...${NC}"

    if [ -d "/opt/exploitdb" ]; then
        echo -e "${YELLOW}[~] Versão antiga encontrada. A remover...${NC}"
        sudo rm -rf /opt/exploitdb
    fi

    sudo git clone https://github.com/offensive-security/exploitdb.git /opt/exploitdb || exit 1

    sudo ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit

    echo -e "${GREEN}[✓] Searchsploit instalado via GitHub!${NC}"
}

# ------------------------------------
# Remover ferramenta
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt remove -y exploitdb
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y exploitdb
            ;;
        pacman)
            sudo pacman -R --noconfirm exploitdb
            ;;
        zypper)
            sudo zypper remove -y exploitdb
            ;;
    esac

    # Remover instalação via github
    if [ -d "/opt/exploitdb" ]; then
        sudo rm -rf /opt/exploitdb
    fi

    if [ -f "/usr/local/bin/searchsploit" ]; then
        sudo rm -f /usr/local/bin/searchsploit
    fi

    echo -e "${GREEN}[✓] $TOOL_NAME removido com sucesso!${NC}"
}

# ------------------------------------
# Execução da escolha
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
