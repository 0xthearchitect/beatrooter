#!/bin/bash
# ------------------------------------
# John the Ripper Installer Script
# ------------------------------------

TOOL_NAME="John the Ripper"

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
echo "2) Compilar manualmente via GitHub (Jumbo)"
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
            sudo apt install -y john
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y john
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            
            if command -v yay >/dev/null 2>&1; then
                echo -e "${GREEN}[+] AUR helper (yay) detectado!${NC}"
                echo ""
                echo "1) pacman (repositório oficial)"
                echo "2) yay (AUR - versão jumbo)"
                read -p "Método [1-2]: " method
                
                if [ "$method" == "2" ]; then
                    yay -Sy --noconfirm john
                else
                    sudo pacman -Sy --noconfirm john
                fi
            else
                sudo pacman -Sy --noconfirm john
            fi
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y john
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
# Compilar manualmente (Jumbo)
# ------------------------------------
compile_manual() {
    echo -e "${BLUE}[*] A instalar dependências de build...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git build-essential libssl-dev zlib1g-dev \
                yasm libgmp-dev libpcap-dev libbz2-dev
            ;;
        dnf)
            sudo dnf install -y git gcc gcc-c++ make openssl-devel \
                gmp-devel pcap-devel bzip2-devel zlib-devel yasm
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git base-devel openssl gmp \
                libpcap bzip2 zlib yasm
            ;;
        zypper)
            sudo zypper install -y git gcc gcc-c++ make libopenssl-devel \
                gmp-devel libpcap-devel libbz2-devel zlib-devel yasm
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${BLUE}[*] A clonar John the Ripper (Jumbo) do GitHub...${NC}"

    if [ -d "john" ]; then
        rm -rf john
    fi

    git clone https://github.com/openwall/john.git || exit 1
    cd john/src || exit 1

    echo -e "${BLUE}[*] A configurar...${NC}"
    ./configure || exit 1

    echo -e "${BLUE}[*] A compilar (pode demorar)...${NC}"
    make -s clean && make -sj$(nproc) || exit 1

    echo -e "${BLUE}[*] A instalar...${NC}"
    sudo make install || {
        # Se make install falhar, copiar manualmente
        sudo cp ../run/john /usr/local/bin/
        sudo chmod +x /usr/local/bin/john
    }

    cd ../..
    rm -rf john

    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME (Jumbo) compilado e instalado!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    PM=$(detect_pm)
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    case $PM in
        apt)
            sudo apt remove -y john
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y john
            ;;
        pacman)
            sudo pacman -R --noconfirm john
            ;;
        zypper)
            sudo zypper remove -y john
            ;;
    esac

    # Remover instalação manual
    if [ -f "/usr/local/bin/john" ]; then
        sudo rm -f /usr/local/bin/john
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
