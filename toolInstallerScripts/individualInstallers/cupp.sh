#!/bin/bash
# ------------------------------------
# CUPP Installer Script
# ------------------------------------

TOOL_NAME="CUPP"

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
echo "1) Instalar via GitHub"
echo "2) Remover"
echo "0) Sair"
echo ""
read -p "Escolha uma opção: " opcao

# ------------------------------------
# Instalar via GitHub
# ------------------------------------
install_github() {
    echo -e "${BLUE}[*] A transferir CUPP do GitHub...${NC}"

    if [ -d "/opt/cupp" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/cupp
    fi

    sudo git clone https://github.com/Mebus/cupp.git /opt/cupp || exit 1

    echo -e "${BLUE}[*] A criar comando global...${NC}"
    
    # Criar wrapper script
    echo '#!/bin/bash
python3 /opt/cupp/cupp.py "$@"' | sudo tee /usr/local/bin/cupp >/dev/null

    sudo chmod +x /usr/local/bin/cupp
    sudo chmod +x /opt/cupp/cupp.py

    echo ""
    echo -e "${GREEN}[✓] CUPP instalado com sucesso!${NC}"
    echo -e "${GREEN}[✓] Localização: /opt/cupp${NC}"
    echo -e "${GREEN}[✓] Use: cupp -i (modo interativo)${NC}"
    echo -e "${GREEN}[✓] Use: cupp -w <wordlist.txt> (wordlist download)${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    if [ -d "/opt/cupp" ]; then
        sudo rm -rf /opt/cupp
    fi

    if [ -f "/usr/local/bin/cupp" ]; then
        sudo rm -f /usr/local/bin/cupp
    fi

    echo -e "${GREEN}[✓] $TOOL_NAME removido!${NC}"
}

# ------------------------------------
# Executar opção
# ------------------------------------
case $opcao in
    1)
        install_github
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
