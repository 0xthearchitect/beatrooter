#!/bin/bash
# ------------------------------------
# GHIDRA Installer Script
# ------------------------------------

TOOL_NAME="Ghidra"

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
echo "1) Instalar via download oficial"
echo "2) Remover"
echo "0) Sair"
echo ""
read -p "Escolha uma opção: " opcao


# ------------------------------------
# Obter URL da última release
# ------------------------------------
get_latest_ghidra_url() {
    curl -s https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest \
    | grep browser_download_url \
    | grep zip\" \
    | cut -d '"' -f 4
}

# ------------------------------------
# Instalar Ghidra
# ------------------------------------
install_ghidra() {
    echo -e "${BLUE}[*] A obter URL da última versão...${NC}"
    GHIDRA_URL=$(get_latest_ghidra_url)

    if [[ -z "$GHIDRA_URL" ]]; then
        echo -e "${RED}[✗] Não foi possível obter a versão mais recente.${NC}"
        exit 1
    fi

    echo -e "${BLUE}[*] URL encontrada:${NC} $GHIDRA_URL"
    
    TMP_ZIP="/tmp/ghidra.zip"

    echo -e "${BLUE}[*] A descarregar Ghidra...${NC}"
    wget -q "$GHIDRA_URL" -O "$TMP_ZIP"

    echo -e "${BLUE}[*] A instalar em /opt/ghidra...${NC}"

    sudo rm -rf /opt/ghidra
    sudo mkdir -p /opt/ghidra
    sudo unzip -q "$TMP_ZIP" -d /opt/ghidra

    # Pasta real tem nome tipo: ghidra_10.3.4_PUBLIC
    GHIDRA_DIR=$(find /opt/ghidra -maxdepth 1 -type d -name "ghidra_*" | head -n 1)

    if [[ ! -d "$GHIDRA_DIR" ]]; then
        echo -e "${RED}[✗] Falha ao localizar diretório descomprimido.${NC}"
        exit 1
    fi

    # Criar comando global
    sudo rm -f /usr/local/bin/ghidra
    echo -e "#!/bin/bash\n$GHIDRA_DIR/ghidraRun \"\$@\"" | sudo tee /usr/local/bin/ghidra >/dev/null
    sudo chmod +x /usr/local/bin/ghidra

    echo -e "${GREEN}[✓] Ghidra instalado com sucesso!${NC}"
    echo -e "${GREEN}[✓] Execute usando: ghidra${NC}"
}

# ------------------------------------
# Remover Ghidra
# ------------------------------------
remove_tool() {
    echo -e "${BLUE}[*] A remover Ghidra...${NC}"

    sudo rm -rf /opt/ghidra
    sudo rm -f /usr/local/bin/ghidra

    echo -e "${GREEN}[✓] $TOOL_NAME removido com sucesso!${NC}"
}


# ------------------------------------
# Switch Case
# ------------------------------------
case $opcao in
    1)
        install_ghidra
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
