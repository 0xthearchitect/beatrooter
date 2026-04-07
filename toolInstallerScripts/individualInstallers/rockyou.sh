#!/bin/bash
# ------------------------------------
# RockYou Wordlist Installer Script
# ------------------------------------

TOOL_NAME="RockYou Wordlist"

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
echo "1) Instalar via download (GitHub)"
echo "2) Remover"
echo "0) Sair"
echo ""
read -p "Escolha uma opção: " opcao


# ------------------------------------
# Instalar RockYou
# ------------------------------------
install_rockyou() {
    INSTALL_DIR="/usr/share/wordlists"
    
    echo -e "${BLUE}[*] A criar diretório $INSTALL_DIR...${NC}"
    sudo mkdir -p "$INSTALL_DIR"
    
    echo -e "${BLUE}[*] A transferir rockyou.txt do GitHub...${NC}"
    
    # Remover versão antiga se existir
    if [ -f "$INSTALL_DIR/rockyou.txt" ]; then
        echo -e "${YELLOW}[~] Removendo versão anterior...${NC}"
        sudo rm -f "$INSTALL_DIR/rockyou.txt"
    fi
    
    if [ -f "$INSTALL_DIR/rockyou.txt.gz" ]; then
        sudo rm -f "$INSTALL_DIR/rockyou.txt.gz"
    fi
    
    # Download do rockyou
    echo -e "${BLUE}[*] A descarregar (pode demorar ~130MB)...${NC}"
    sudo wget -q --show-progress \
        https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt \
        -O "$INSTALL_DIR/rockyou.txt" || {
        
        # Fallback: tentar versão comprimida
        echo -e "${YELLOW}[~] A tentar download alternativo (comprimido)...${NC}"
        sudo wget -q --show-progress \
            https://gitlab.com/kalilinux/packages/wordlists/-/raw/kali/master/rockyou.txt.gz \
            -O "$INSTALL_DIR/rockyou.txt.gz" || exit 1
        
        echo -e "${BLUE}[*] A descomprimir...${NC}"
        sudo gunzip "$INSTALL_DIR/rockyou.txt.gz"
    }
    
    # Criar link simbólico em /opt se não existir
    if [ ! -d "/opt/wordlists" ]; then
        sudo mkdir -p /opt/wordlists
    fi
    sudo ln -sf "$INSTALL_DIR/rockyou.txt" /opt/wordlists/rockyou.txt 2>/dev/null
    
    # Verificar tamanho
    SIZE=$(du -h "$INSTALL_DIR/rockyou.txt" 2>/dev/null | cut -f1)
    LINES=$(wc -l < "$INSTALL_DIR/rockyou.txt" 2>/dev/null)
    
    echo ""
    echo -e "${GREEN}[✓] RockYou instalado com sucesso!${NC}"
    echo -e "${GREEN}[✓] Localização: $INSTALL_DIR/rockyou.txt${NC}"
    echo -e "${GREEN}[✓] Tamanho: $SIZE${NC}"
    echo -e "${GREEN}[✓] Linhas: $(printf "%'d" $LINES)${NC}"
    echo ""
    echo -e "${CYAN}[i] Uso com John: john --wordlist=$INSTALL_DIR/rockyou.txt hash.txt${NC}"
    echo -e "${CYAN}[i] Uso com Hashcat: hashcat -m 0 -a 0 hash.txt $INSTALL_DIR/rockyou.txt${NC}"
}

# ------------------------------------
# Remover RockYou
# ------------------------------------
remove_rockyou() {
    echo -e "${BLUE}[*] A remover RockYou wordlist...${NC}"
    
    sudo rm -f /usr/share/wordlists/rockyou.txt
    sudo rm -f /usr/share/wordlists/rockyou.txt.gz
    sudo rm -f /opt/wordlists/rockyou.txt
    
    echo -e "${GREEN}[✓] RockYou removido!${NC}"
}

# ------------------------------------
# Executar opção
# ------------------------------------
case $opcao in
    1)
        install_rockyou
        ;;
    2)
        remove_rockyou
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
