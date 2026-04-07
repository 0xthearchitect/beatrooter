#!/bin/bash
# ------------------------------------
# RevShellGen Installer Script
# ------------------------------------

TOOL_NAME="RevShellGen"

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
    echo -e "${BLUE}[*] A transferir RevShellGen do GitHub...${NC}"

    if [ -d "/opt/revshellgen" ]; then
        echo -e "${YELLOW}[~] A remover versão anterior...${NC}"
        sudo rm -rf /opt/revshellgen
    fi

    sudo git clone https://github.com/t0thkr1s/revshellgen.git /opt/revshellgen || exit 1

    echo -e "${BLUE}[*] A criar comando global...${NC}"
    
    # Criar wrapper script
    echo '#!/bin/bash
python3 /opt/revshellgen/revshellgen.py "$@"' | sudo tee /usr/local/bin/revshellgen >/dev/null

    sudo chmod +x /usr/local/bin/revshellgen
    sudo chmod +x /opt/revshellgen/revshellgen.py

    echo ""
    echo -e "${GREEN}[✓] RevShellGen instalado com sucesso!${NC}"
    echo -e "${GREEN}[✓] Localização: /opt/revshellgen${NC}"
    echo -e "${GREEN}[✓] Use: revshellgen${NC}"
}

# ------------------------------------
# Remover
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover $TOOL_NAME...${NC}"

    if [ -d "/opt/revshellgen" ]; then
        sudo rm -rf /opt/revshellgen
    fi

    if [ -f "/usr/local/bin/revshellgen" ]; then
        sudo rm -f /usr/local/bin/revshellgen
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
