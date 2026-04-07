#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
    GESTOR DE FERRAMENTAS DE SEGURANÇA
============================================
Sistema modular que executa scripts individuais
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Cores ANSI
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"

# Diretório dos scripts
SCRIPTS_DIR = Path(__file__).parent / "individualInstallers"

# Configuração das ferramentas (carregada de tools.json)
TOOLS = {}


def load_config():
    """Carrega configuração das ferramentas"""
    global TOOLS
    config_file = Path(__file__).parent / "tools.json"
    
    if not config_file.exists():
        print(f"{RED}[✗] Ficheiro tools.json não encontrado!{RESET}")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        TOOLS = json.load(f)


def clear_screen():
    """Limpa o ecrã"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header(title):
    """Imprime cabeçalho formatado"""
    print(f"\n{CYAN}{'=' * 50}")
    print(f"{title:^50}")
    print(f"{'=' * 50}{RESET}\n")


def is_tool_installed(tool_key):
    """Verifica se uma ferramenta está instalada"""
    tool = TOOLS[tool_key]
    check_cmd = tool.get('check_command', tool_key)
    
    # Verificações especiais
    if isinstance(check_cmd, list):
        for cmd in check_cmd:
            if subprocess.run(['which', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                return True
        return False
    
    # Verificar path especial
    special_path = tool.get('special_path')
    if special_path and os.path.exists(special_path):
        return True
    
    return subprocess.run(['which', check_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0


def run_installer_script(tool_key, action):
    """Executa o script instalador de uma ferramenta
    
    Args:
        tool_key: chave da ferramenta no dicionário
        action: 'install' ou 'remove'
    """
    tool = TOOLS[tool_key]
    script_name = tool['script']
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        print(f"{RED}[✗] Script {script_name} não encontrado!{RESET}")
        return False
    
    print(f"{BLUE}[*] A executar {script_name}...{RESET}\n")
    
    # Preparar o comando baseado na ação
    if action == 'install':
        # Passa opção "1" ou "2" dependendo se existe repo option
        option = tool.get('install_option', '1')
    elif action == 'remove':
        option = tool.get('remove_option', '3')
    else:
        print(f"{RED}[✗] Ação inválida: {action}{RESET}")
        return False
    
    # Executar o script com a opção automaticamente
    try:
        # Usar echo para passar a opção automaticamente
        process = subprocess.Popen(
            f"echo '{option}' | bash {script_path}",
            shell=True,
            executable='/bin/bash'
        )
        process.wait()
        
        if process.returncode == 0:
            return True
        else:
            print(f"{RED}[✗] Erro ao executar script.{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}[✗] Erro: {e}{RESET}")
        return False


def install_tool(tool_key):
    """Instala uma ferramenta"""
    tool = TOOLS[tool_key]
    print(f"{BLUE}[*] A instalar {tool['name']}...{RESET}\n")
    
    success = run_installer_script(tool_key, 'install')
    
    if success:
        print(f"\n{GREEN}[✓] {tool['name']} instalado!{RESET}")
    else:
        print(f"\n{RED}[✗] Erro ao instalar {tool['name']}.{RESET}")
    
    return success


def remove_tool(tool_key):
    """Remove uma ferramenta"""
    tool = TOOLS[tool_key]
    print(f"{BLUE}[*] A remover {tool['name']}...{RESET}\n")
    
    success = run_installer_script(tool_key, 'remove')
    
    if success:
        print(f"\n{GREEN}[✓] {tool['name']} removido!{RESET}")
    else:
        print(f"\n{RED}[✗] Erro ao remover {tool['name']}.{RESET}")
    
    return success


def install_all_tools():
    """Instala todas as ferramentas"""
    print_header("INSTALAR TODAS AS FERRAMENTAS")
    
    for tool_key in TOOLS:
        if is_tool_installed(tool_key):
            print(f"{YELLOW}[~] {TOOLS[tool_key]['name']} já está instalado. A saltar...{RESET}\n")
        else:
            install_tool(tool_key)
        print()
    
    input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


def remove_all_tools():
    """Remove todas as ferramentas"""
    print_header("REMOVER TODAS AS FERRAMENTAS")
    
    confirm = input(f"{RED}Tem a certeza que deseja remover TODAS as ferramentas? [S/N]: {RESET}").lower()
    
    if confirm != 's':
        print(f"{YELLOW}[!] Operação cancelada.{RESET}")
        input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")
        return
    
    for tool_key in TOOLS:
        if is_tool_installed(tool_key):
            remove_tool(tool_key)
        else:
            print(f"{YELLOW}[~] {TOOLS[tool_key]['name']} não está instalado. A saltar...{RESET}\n")
        print()
    
    input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


def install_individual_menu():
    """Menu para instalar ferramentas individualmente"""
    while True:
        clear_screen()
        print_header("INSTALAR FERRAMENTA INDIVIDUAL")
        
        tool_list = list(TOOLS.keys())
        
        for i, tool_key in enumerate(tool_list, 1):
            status = f"{GREEN}[INSTALADO]{RESET}" if is_tool_installed(tool_key) else f"{RED}[NÃO INSTALADO]{RESET}"
            print(f"{i}) {TOOLS[tool_key]['name']:30} {status}")
        
        print(f"\n0) Voltar ao menu principal")
        
        choice = input(f"\n{YELLOW}Escolha uma opção: {RESET}")
        
        if choice == '0':
            break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tool_list):
                tool_key = tool_list[idx]
                if is_tool_installed(tool_key):
                    print(f"\n{YELLOW}[!] {TOOLS[tool_key]['name']} já está instalado!{RESET}")
                else:
                    print()
                    install_tool(tool_key)
                
                input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")
        except ValueError:
            print(f"{RED}[!] Opção inválida!{RESET}")
            input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


def remove_individual_menu():
    """Menu para remover ferramentas individualmente"""
    while True:
        clear_screen()
        print_header("REMOVER FERRAMENTA INDIVIDUAL")
        
        tool_list = list(TOOLS.keys())
        
        for i, tool_key in enumerate(tool_list, 1):
            status = f"{GREEN}[INSTALADO]{RESET}" if is_tool_installed(tool_key) else f"{RED}[NÃO INSTALADO]{RESET}"
            print(f"{i}) {TOOLS[tool_key]['name']:30} {status}")
        
        print(f"\n0) Voltar ao menu principal")
        
        choice = input(f"\n{YELLOW}Escolha uma opção: {RESET}")
        
        if choice == '0':
            break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tool_list):
                tool_key = tool_list[idx]
                if not is_tool_installed(tool_key):
                    print(f"\n{YELLOW}[!] {TOOLS[tool_key]['name']} não está instalado!{RESET}")
                else:
                    print()
                    remove_tool(tool_key)
                
                input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")
        except ValueError:
            print(f"{RED}[!] Opção inválida!{RESET}")
            input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


def remove_all_installed_tools():
    """Remove apenas as ferramentas que estão instaladas"""
    print_header("REMOVER TODAS AS FERRAMENTAS INSTALADAS")
    
    # Contar ferramentas instaladas
    installed = [key for key in TOOLS if is_tool_installed(key)]
    
    if not installed:
        print(f"{YELLOW}[!] Nenhuma ferramenta está instalada.{RESET}")
        input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")
        return
    
    print(f"{CYAN}Ferramentas instaladas encontradas: {GREEN}{len(installed)}{RESET}\n")
    for key in installed:
        print(f"  • {TOOLS[key]['name']}")
    
    print()
    confirm = input(f"{RED}Tem a certeza que deseja remover TODAS as {len(installed)} ferramentas instaladas? [s/N]: {RESET}").lower()
    
    if confirm != 's':
        print(f"{YELLOW}[!] Operação cancelada.{RESET}")
        input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")
        return
    
    print()
    for tool_key in installed:
        remove_tool(tool_key)
        print()
    
    print(f"\n{GREEN}[✓] Remoção concluída!{RESET}")
    input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


def show_tool_status():
    """Mostra o estado de instalação de todas as ferramentas"""
    clear_screen()
    print_header("ESTADO DAS FERRAMENTAS")
    
    for tool_key in TOOLS:
        status = f"{GREEN}✓ INSTALADO{RESET}" if is_tool_installed(tool_key) else f"{RED}✗ NÃO INSTALADO{RESET}"
        print(f"{TOOLS[tool_key]['name']:30} {status}")
    
    input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


def main_menu():
    """Menu principal"""
    # Carregar configuração
    load_config()
    
    # Verificar se diretório de scripts existe
    if not SCRIPTS_DIR.exists():
        print(f"{RED}[✗] Diretório 'individualInstallers' não encontrado!{RESET}")
        print(f"{YELLOW}Crie o diretório e coloque os scripts .sh lá dentro.{RESET}")
        sys.exit(1)
    
    while True:
        clear_screen()
        print_header("INSTALADOR DE FERRAMENTAS BEATROOTER")
        
        print(f"{CYAN}Total de ferramentas: {GREEN}{len(TOOLS)}{RESET}\n")
        
        print("1) Instalar todas as ferramentas")
        print("2) Remover todas as ferramentas")
        print("3) Instalar ferramenta individual")
        print("4) Remover ferramenta individual")
        print("5) Ver estado das ferramentas")
        print("\n0) Sair")
        
        choice = input(f"\n{YELLOW}Escolha uma opção: {RESET}")
        
        if choice == '1':
            install_all_tools()
        elif choice == '2':
            remove_all_tools()
        elif choice == '3':
            install_individual_menu()
        elif choice == '4':
            remove_individual_menu()
        elif choice == '5':
            show_tool_status()
        elif choice == '6':
            remove_all_installed_tools()
        elif choice == '0':
            print(f"\n{GREEN}A sair... Até breve!{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}[!] Opção inválida!{RESET}")
            input(f"\n{CYAN}Pressione ENTER para continuar...{RESET}")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Interrompido pelo utilizador.{RESET}")
        sys.exit(0)
