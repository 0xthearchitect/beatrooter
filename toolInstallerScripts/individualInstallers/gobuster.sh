#!/bin/bash
# ------------------------------------
# GoBuster Installer Script
# ------------------------------------

TOOL_NAME="GoBuster"

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
            sudo apt install -y gobuster
            ;;
        dnf)
            echo -e "${RED}[!] GoBuster NÃO está nos repos oficiais Fedora/DNF.${NC}"
            echo -e "${YELLOW}Use a opção 2 para compilar manualmente.${NC}"
            exit 1
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
                    yay -Sy --noconfirm gobuster
                else
                    sudo pacman -Sy --noconfirm gobuster
                fi
            else
                sudo pacman -Sy --noconfirm gobuster
            fi
            ;;
        zypper)
            echo -e "${RED}[!] GoBuster NÃO está nos repos oficiais OpenSUSE.${NC}"
            echo -e "${YELLOW}Use a opção 2 para compilar manualmente.${NC}"
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
# Compilar manualmente
# ------------------------------------
compile_manual() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A instalar dependências (Git, Go)...${NC}"
    
    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git golang
            ;;
        dnf)
            sudo dnf install -y git golang
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git go
            ;;
        zypper)
            sudo zypper install -y git go
            ;;
        *)
            echo -e "${RED}[!] Não consegui instalar Go automaticamente.${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${BLUE}[*] A transferir GoBuster do GitHub...${NC}"
    
    if [ -d "gobuster" ]; then
        echo -e "${BLUE}[*] A remover instalação anterior...${NC}"
        rm -rf gobuster
    fi
    
    git clone https://github.com/OJ/gobuster || exit 1
    cd gobuster || exit
    
    echo -e "${BLUE}[*] A compilar GoBuster...${NC}"
    go build || exit 1
    
    echo -e "${BLUE}[*] A mover binário para /usr/local/bin...${NC}"
    sudo mv gobuster /usr/local/bin/gobuster
    sudo chmod +x /usr/local/bin/gobuster
    
    cd ..
    rm -rf gobuster
    
    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME compilado e instalado!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    
    # Remover binário manual
    if [ -f "/usr/local/bin/gobuster" ]; then
        echo -e "${BLUE}[*] A remover instalação manual...${NC}"
        sudo rm -f /usr/local/bin/gobuster
    fi
    
    # Remover via gestor de pacotes
    case $PM in
        apt)
            sudo apt remove -y gobuster
            sudo apt autoremove -y
            ;;
        pacman)
            sudo pacman -R --noconfirm gobuster 2>/dev/null
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