#!/bin/bash
# ------------------------------------
# ExifTool Installer Script
# ------------------------------------

TOOL_NAME="ExifTool"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo "======================================"
echo "     INSTALAR/REMOVER $TOOL_NAME"
echo "======================================"
echo ""
echo "1) Instalar via repositório oficial"
echo "2) Instalar manualmente via GitHub"
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
            sudo apt install -y libimage-exiftool-perl
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y perl-Image-ExifTool
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
                    yay -Sy --noconfirm exiftool
                else
                    sudo pacman -Sy --noconfirm exiftool
                fi
            else
                sudo pacman -Sy --noconfirm exiftool
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y exiftool
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
# Instalar manualmente
# ------------------------------------
install_manual() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A instalar dependências (Perl)...${NC}"
    
    case $PM in
        apt)
            sudo apt update
            sudo apt install -y perl wget unzip
            ;;
        dnf)
            sudo dnf install -y perl wget unzip
            ;;
        pacman)
            sudo pacman -Sy --noconfirm perl wget unzip
            ;;
        zypper)
            sudo zypper install -y perl wget unzip
            ;;
        *)
            echo -e "${RED}[!] Não consegui instalar dependências.${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${BLUE}[*] A transferir ExifTool do GitHub...${NC}"
    wget https://github.com/exiftool/exiftool/archive/refs/heads/master.zip -O exiftool.zip || exit 1
    
    echo -e "${BLUE}[*] A extrair...${NC}"
    unzip -q exiftool.zip || exit 1
    
    cd exiftool-master || exit
    
    echo -e "${BLUE}[*] A instalar...${NC}"
    sudo mkdir -p /usr/local/exiftool/
    sudo cp -r ./* /usr/local/exiftool/
    sudo chmod +x /usr/local/exiftool/exiftool
    sudo ln -sf /usr/local/exiftool/exiftool /usr/local/bin/exiftool
    
    cd ..
    rm -rf exiftool-master exiftool.zip
    
    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME instalado manualmente!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    
    # Remover instalação manual
    if [ -d "/usr/local/exiftool" ]; then
        echo -e "${BLUE}[*] A remover instalação manual...${NC}"
        sudo rm -rf /usr/local/exiftool
        sudo rm -f /usr/local/bin/exiftool
    fi
    
    # Remover via gestor de pacotes
    case $PM in
        apt)
            sudo apt remove -y libimage-exiftool-perl
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y perl-Image-ExifTool
            ;;
        pacman)
            sudo pacman -R --noconfirm exiftool 2>/dev/null
            ;;
        zypper)
            sudo zypper remove -y exiftool
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
        install_manual
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