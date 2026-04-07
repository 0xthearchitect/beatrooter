#!/bin/bash
# ------------------------------------
# Hashcat Installer Script
# ------------------------------------

TOOL_NAME="Hashcat"

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
# Detectar package manager
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
            sudo apt update
            sudo apt install -y hashcat
            ;;
        dnf)
            sudo dnf install -y hashcat
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
                    yay -Sy --noconfirm hashcat
                else
                    sudo pacman -Sy --noconfirm hashcat
                fi
            else
                sudo pacman -Sy --noconfirm hashcat
            fi
            ;;
        zypper)
            sudo zypper install -y hashcat
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}[✓] Hashcat instalado com sucesso!${NC}"
}

# ------------------------------------
# Compilar manualmente via GitHub
# ------------------------------------
compile_manual() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A instalar dependências necessárias...${NC}"

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git build-essential cmake pkg-config \
                libssl-dev libtool
            ;;
        dnf)
            sudo dnf install -y git make automake gcc gcc-c++ cmake openssl-devel
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git base-devel cmake openssl
            ;;
        zypper)
            sudo zypper install -y git gcc gcc-c++ make cmake libopenssl-devel
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac

    echo -e "${BLUE}[*] A clonar repositório do Hashcat...${NC}"
    rm -rf hashcat 2>/dev/null
    git clone https://github.com/hashcat/hashcat.git || exit 1
    cd hashcat || exit 1

    echo -e "${BLUE}[*] A compilar (isto pode demorar)...${NC}"
    make -j"$(nproc)" || exit 1

    echo -e "${BLUE}[*] A instalar...${NC}"
    sudo make install || exit 1

    cd ..
    rm -rf hashcat

    echo -e "${GREEN}[✓] Hashcat compilado e instalado!${NC}"
}

# ------------------------------------
# Remover Hashcat
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover Hashcat...${NC}"

    case $PM in
        apt)
            sudo apt remove -y hashcat
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y hashcat
            ;;
        pacman)
            sudo pacman -Rns --noconfirm hashcat
            ;;
        zypper)
            sudo zypper remove -y hashcat
            ;;
    esac

    # Se tiver sido instalado via GitHub
    if command -v hashcat >/dev/null 2>&1; then
        sudo rm -f "$(command -v hashcat)"
    fi

    echo -e "${GREEN}[✓] Hashcat removido!${NC}"
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
