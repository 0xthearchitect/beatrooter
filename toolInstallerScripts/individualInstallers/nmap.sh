#!/bin/bash
# ------------------------------------
# Nmap Installer Script
# ------------------------------------

TOOL_NAME="Nmap"

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
echo "2) Compilar manualmente via GitHub"
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
            sudo apt install -y nmap
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y nmap
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
                    yay -Sy --noconfirm nmap
                else
                    sudo pacman -Sy --noconfirm nmap
                fi
            else
                sudo pacman -Sy --noconfirm nmap
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y nmap
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
# Compilar manualmente
# ------------------------------------
compile_manual() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A instalar dependências da compilação...${NC}"
    
    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git build-essential liblua5.3-dev libssl-dev
            ;;
        dnf)
            sudo dnf install -y git gcc gcc-c++ make openssl-devel lua-devel
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git base-devel openssl lua
            ;;
        zypper)
            sudo zypper install -y git gcc gcc-c++ make libopenssl-devel lua-devel
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${BLUE}[*] A transferir Nmap do GitHub...${NC}"
    
    if [ -d "nmap" ]; then
        echo -e "${BLUE}[*] A remover instalação anterior...${NC}"
        rm -rf nmap
    fi
    
    git clone https://github.com/nmap/nmap || exit 1
    cd nmap || exit
    
    echo -e "${BLUE}[*] A preparar build...${NC}"
    ./configure || exit 1
    
    echo -e "${BLUE}[*] A compilar (pode demorar)...${NC}"
    make || exit 1
    
    echo -e "${BLUE}[*] A instalar...${NC}"
    sudo make install || exit 1
    
    cd ..
    echo -e "${BLUE}[*] A limpar ficheiros temporários...${NC}"
    rm -rf nmap
    
    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME compilado e instalado!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    
    case $PM in
        apt)
            sudo apt remove -y nmap
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y nmap
            ;;
        pacman)
            sudo pacman -R --noconfirm nmap
            ;;
        zypper)
            sudo zypper remove -y nmap
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
        compile_manual
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