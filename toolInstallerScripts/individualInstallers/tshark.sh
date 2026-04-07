#!/bin/bash
# ------------------------------------
# TShark Installer Script
# ------------------------------------

TOOL_NAME="TShark"

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
echo "2) Instalar via GitHub (última versão do Wireshark/TShark)"
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
            sudo apt install -y tshark
            ;;
        dnf)
            echo -e "${GREEN}[+] Detectado DNF (Fedora/RHEL)${NC}"
            sudo dnf install -y wireshark-cli
            ;;
        pacman)
            echo -e "${GREEN}[+] Detectado Pacman (Arch/Manjaro)${NC}"
            sudo pacman -Sy --noconfirm wireshark-cli
            ;;
        zypper)
            echo -e "${GREEN}[+] Detectado Zypper (OpenSUSE)${NC}"
            sudo zypper install -y wireshark
            ;;
        *)
            echo -e "${RED}[!] Gestor de pacotes não suportado!${NC}"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}[✓] $TOOL_NAME instalado com sucesso!${NC}"

    # Permitir capturas sem root (APT)
    if [ $PM = "apt" ]; then
        sudo usermod -aG wireshark $USER
        echo -e "${YELLOW}[~] Para capturar pacotes sem root, reinicie a sessão.${NC}"
    fi
}

# ------------------------------------
# Instalar via GitHub (compilação do Wireshark)
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A instalar dependências...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt update
            sudo apt install -y git cmake make gcc g++ flex bison \
                libglib2.0-dev libpcap-dev qtbase5-dev libqt5svg5-dev \
                qtmultimedia5-dev python3 python3-pip
            ;;
        dnf)
            sudo dnf install -y git cmake make gcc gcc-c++ flex bison \
                glib2-devel libpcap-devel qt5-qtbase-devel qt5-qtsvg-devel python3
            ;;
        pacman)
            sudo pacman -Sy --noconfirm git cmake base-devel flex bison glib2 libpcap qt5
            ;;
        zypper)
            sudo zypper install -y git cmake gcc gcc-c++ flex bison glib2-devel libpcap-devel libqt5-qtbase-devel
            ;;
        *)
            echo -e "${RED}[!] Não foi possível instalar dependências.${NC}"
            exit 1
            ;;
    esac

    echo -e "${BLUE}[*] A transferir Wireshark/TShark do GitHub...${NC}"

    if [ -d "/opt/wireshark" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/wireshark
    fi

    sudo git clone https://github.com/wireshark/wireshark.git /opt/wireshark || exit 1

    cd /opt/wireshark
    sudo cmake .
    sudo make -j"$(nproc)"
    sudo make install

    echo -e "${GREEN}[✓] TShark instalado via GitHub (versão mais recente)!${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"
    PM=$(detect_pm)

    case $PM in
        apt)
            sudo apt remove -y tshark
            sudo apt autoremove -y
            ;;
        dnf)
            sudo dnf remove -y wireshark-cli
            ;;
        pacman)
            sudo pacman -R --noconfirm wireshark-cli
            ;;
        zypper)
            sudo zypper remove -y wireshark
            ;;
    esac

    # Remover instalação manual
    if [ -d "/opt/wireshark" ]; then
        sudo rm -rf /opt/wireshark
    fi

    echo -e "${GREEN}[✓] $TOOL_NAME removido!${NC}"
}

# ------------------------------------
# Execução
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
