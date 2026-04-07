#!/bin/bash
# ------------------------------------
# DNS Utils Installer Script
# ------------------------------------

TOOL_NAME="DNS Utils (nslookup/dig)"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo "======================================"
echo "   INSTALAR/REMOVER $TOOL_NAME"
echo "======================================"
echo ""
echo "Este script instala as ferramentas:"
echo "  - nslookup"
echo "  - dig"
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
            echo -e "${BLUE}[*] A instalar dnsutils...${NC}"
            sudo apt update
            sudo apt install -y dnsutils
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            echo -e "${BLUE}[*] A instalar bind-utils...${NC}"
            sudo dnf install -y bind-utils
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            echo -e "${BLUE}[*] A instalar bind...${NC}"
            
            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo ""
                echo "1) pacman (repositório oficial)"
                echo "2) yay (AUR)"
                read -p "Método [1-2]: " method
                
                if [ "$method" == "2" ]; then
                    yay -Sy --noconfirm bind
                else
                    sudo pacman -Sy --noconfirm bind
                fi
            else
                sudo pacman -Sy --noconfirm bind
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            echo -e "${BLUE}[*] A instalar bind-utils...${NC}"
            sudo zypper install -y bind-utils
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}[✓] DNS Utils instalados com sucesso!${NC}"
    echo ""
    echo -e "${GREEN}[✓] Ferramentas disponíveis:${NC}"
    echo "    - nslookup dominio.com"
    echo "    - dig dominio.com"
    echo "    - dig @8.8.8.8 dominio.com"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover DNS Utils...${NC}"
    
    case $PM in
        apt)
            sudo apt remove -y dnsutils
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y bind-utils
            ;;
        pacman)
            sudo pacman -R --noconfirm bind
            ;;
        zypper)
            sudo zypper remove -y bind-utils
            ;;
    esac
    
    echo -e "${GREEN}[✓] DNS Utils removidos!${NC}"
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