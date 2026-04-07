#!/bin/bash
# ------------------------------------
# RPCClient Installer Script
# ------------------------------------

TOOL_NAME="RPCClient"

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
            echo -e "${BLUE}[*] RPCClient faz parte do pacote samba-common-bin${NC}"
            sudo apt update
            sudo apt install -y samba-common-bin
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y samba-common-tools
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
                    yay -Sy --noconfirm smbclient
                else
                    sudo pacman -Sy --noconfirm smbclient
                fi
            else
                sudo pacman -Sy --noconfirm smbclient
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y samba-client
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME instalado com sucesso!${NC}"
    echo -e "${GREEN}[✓] Use: rpcclient -U username //target${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    
    echo -e "${YELLOW}[!] AVISO: RPCClient faz parte de pacotes Samba.${NC}"
    echo -e "${YELLOW}[!] Remover pode afetar outras ferramentas Samba.${NC}"
    read -p "Deseja continuar? [s/N]: " confirm
    
    if [ "$confirm" != "s" ]; then
        echo -e "${YELLOW}[!] Operação cancelada.${NC}"
        exit 0
    fi
    
    case $PM in
        apt)
            sudo apt remove -y samba-common-bin
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y samba-common-tools
            ;;
        pacman)
            sudo pacman -R --noconfirm smbclient
            ;;
        zypper)
            sudo zypper remove -y samba-client
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
