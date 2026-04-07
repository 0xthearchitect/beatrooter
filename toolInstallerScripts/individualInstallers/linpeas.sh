#!/bin/bash
# ------------------------------------
# LinPEAS Installer Script
# ------------------------------------

TOOL_NAME="LinPEAS"

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
echo "1) Instalar via download oficial (peass-ng)"
echo "2) Instalar via GitHub (clone completo)"
echo "3) Remover"
echo "0) Sair"
echo ""
read -p "Escolha uma opção: " opcao


# ------------------------------------
# Instalação via Download Oficial
# ------------------------------------
install_direct() {
    echo -e "${BLUE}[*] A instalar LinPEAS via download oficial...${NC}"

    sudo mkdir -p /opt/linpeas
    sudo rm -f /opt/linpeas/linpeas.sh

    sudo wget -q https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh -O /opt/linpeas/linpeas.sh

    sudo chmod +x /opt/linpeas/linpeas.sh
    sudo ln -sf /opt/linpeas/linpeas.sh /usr/local/bin/linpeas

    echo -e "${GREEN}[✓] LinPEAS instalado com sucesso!${NC}"
}

# ------------------------------------
# Instalar via GitHub Clone
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A instalar LinPEAS via GitHub...${NC}"

    if [ -d "/opt/peass-ng" ]; then
        echo -e "${YELLOW}[~] Versão antiga encontrada. A remover...${NC}"
        sudo rm -rf /opt/peass-ng
    fi

    sudo git clone https://github.com/peass-ng/PEASS-ng.git /opt/peass-ng || exit 1

    sudo chmod +x /opt/peass-ng/linPEAS/linpeas.sh
    sudo ln -sf /opt/peass-ng/linPEAS/linpeas.sh /usr/local/bin/linpeas

    echo -e "${GREEN}[✓] LinPEAS instalado via GitHub!${NC}"
}

# ------------------------------------
# Remover ferramenta
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    # Remover ícone/link
    if [ -f "/usr/local/bin/linpeas" ]; then
        sudo rm -f /usr/local/bin/linpeas
    fi

    # Remover instalação directa
    if [ -d "/opt/linpeas" ]; then
        sudo rm -rf /opt/linpeas
    fi

    # Remover instalação via github
    if [ -d "/opt/peass-ng" ]; then
        sudo rm -rf /opt/peass-ng
    fi

    echo -e "${GREEN}[✓] $TOOL_NAME removido com sucesso!${NC}"
}

# ------------------------------------
# Menu
# ------------------------------------
case $opcao in
    1)
        install_direct
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
