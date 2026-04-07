#!/bin/bash
# ------------------------------------
# Sublist3r Installer Script
# ------------------------------------

TOOL_NAME="Sublist3r"

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
            sudo apt install -y sublist3r
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            
            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo -e "${YELLOW}[!] Sublist3r NÃO existe no repositório oficial do Arch.${NC}"
                echo ""
                echo "1) Instalar via yay (AUR)"
                echo "2) Instalar manualmente via GitHub"
                read -p "Método [1-2]: " method
                
                if [ "$method" == "1" ]; then
                    yay -Sy --noconfirm sublist3r
                else
                    install_manual
                    exit 0
                fi
            else
                echo -e "${RED}[!] Sublist3r NÃO existe no repositório oficial Arch.${NC}"
                echo -e "${YELLOW}Instale o yay ou use a opção 2.${NC}"
                exit 1
            fi
            ;;
        dnf|zypper)
            echo -e "${RED}[!] Sublist3r NÃO existe no repositório $PM.${NC}"
            echo -e "${YELLOW}Use a opção 2 para instalar manualmente.${NC}"
            exit 1
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não reconhecido!${NC}"
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
    echo -e "${BLUE}[*] A instalar dependências (Python3, pip, git)...${NC}"
    
    case $PM in
        apt)
            sudo apt update
            sudo apt install -y python3 python3-pip git
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip git
            ;;
        pacman)
            sudo pacman -Sy --noconfirm python python-pip git
            ;;
        zypper)
            sudo zypper install -y python3 python3-pip git
            ;;
        *)
            echo -e "${RED}[!] Não consegui instalar dependências.${NC}"
            exit 1
            ;;
    esac
    
    INSTALL_DIR="/opt/Sublist3r"
    
    echo ""
    echo -e "${BLUE}[*] A transferir Sublist3r do GitHub...${NC}"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${BLUE}[*] A remover instalação anterior...${NC}"
        sudo rm -rf "$INSTALL_DIR"
    fi
    
    if [ -L "/usr/local/bin/sublist3r" ]; then
        sudo rm -f /usr/local/bin/sublist3r
    fi
    
    git clone https://github.com/aboul3la/Sublist3r /tmp/Sublist3r || exit 1
    
    echo -e "${BLUE}[*] A mover para $INSTALL_DIR...${NC}"
    sudo mv /tmp/Sublist3r "$INSTALL_DIR"
    
    cd "$INSTALL_DIR" || exit
    
    echo -e "${BLUE}[*] A instalar requisitos Python...${NC}"
    pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt
    
    echo -e "${BLUE}[*] A criar link simbólico...${NC}"
    sudo chmod +x "$INSTALL_DIR/sublist3r.py"
    sudo ln -sf "$INSTALL_DIR/sublist3r.py" /usr/local/bin/sublist3r
    
    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME instalado manualmente!${NC}"
    echo -e "${GREEN}[✓] Localização: $INSTALL_DIR${NC}"
    echo -e "${GREEN}[✓] Use: sublist3r -d dominio.com${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    
    # Remover instalação manual
    if [ -d "/opt/Sublist3r" ]; then
        echo -e "${BLUE}[*] A remover instalação manual...${NC}"
        sudo rm -rf /opt/Sublist3r
        sudo rm -f /usr/local/bin/sublist3r
    fi
    
    # Remover via gestor de pacotes
    case $PM in
        apt)
            sudo apt remove -y sublist3r
            sudo apt autoremove -y
            ;;
        pacman)
            sudo pacman -R --noconfirm sublist3r 2>/dev/null
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