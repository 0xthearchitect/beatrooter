import subprocess
import platform
import os
from PyQt6.QtWidgets import QMessageBox

class WSLHandler:
    @staticmethod
    def is_wsl_available():
        if platform.system() != "Windows":
            return False
            
        try:
            result = subprocess.run(
                ['wsl', 'echo', 'test'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'test' in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def execute_via_wsl(command_parts, working_dir=None):
        try:
            wsl_command = ['wsl'] + command_parts
            
            process = subprocess.Popen(
                wsl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                bufsize=1,
                universal_newlines=True
            )
            
            return process
        except Exception as e:
            raise Exception(f"WSL execution failed: {str(e)}")

    @staticmethod
    def check_tool_in_wsl(tool_name):
        try:
            result = subprocess.run(
                ['wsl', 'which', tool_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def suggest_wsl_installation():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("WSL Not Available")
        msg.setText(
            "Windows Subsystem for Linux (WSL) is not available on your system.\n\n"
            "Some tools may work better in WSL environment.\n"
            "Would you like to learn more about installing WSL?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            import webbrowser
            webbrowser.open('https://docs.microsoft.com/en-us/windows/wsl/install')
        
        return False
    
    @staticmethod
    def fix_gobuster_command(command_parts):
        try:
            has_wordlist = False
            wordlist_index = -1
            
            for i, part in enumerate(command_parts):
                if part == '-w' and i + 1 < len(command_parts):
                    wordlist_index = i + 1
                    wordlist_path = command_parts[wordlist_index]

                    check_cmd = ['wsl', 'test', '-f', wordlist_path, '&&', 'echo', 'EXISTS']
                    result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
                    if 'EXISTS' in result.stdout:
                        has_wordlist = True
                    break
            
            if not has_wordlist:
                possible_wordlists = [
                    '/usr/share/dirb/wordlists/common.txt',
                    '/usr/share/dirb/wordlists/big.txt',
                    '/usr/share/dirb/wordlists/small.txt',
                    '/usr/share/wordlists/dirb/common.txt',
                    '/usr/share/seclists/Discovery/Web-Content/common.txt'
                ]
                
                for wordlist in possible_wordlists:
                    check_cmd = ['wsl', 'test', '-f', wordlist, '&&', 'echo', 'EXISTS']
                    result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
                    if 'EXISTS' in result.stdout:
                        if wordlist_index != -1:
                            command_parts[wordlist_index] = wordlist
                        else:
                            command_parts.extend(['-w', wordlist])
                        has_wordlist = True
                        break

                if not has_wordlist:
                    default_wordlist = '/usr/share/dirb/wordlists/common.txt'
                    if wordlist_index != -1:
                        command_parts[wordlist_index] = default_wordlist
                    else:
                        command_parts.extend(['-w', default_wordlist])
            
            return command_parts
            
        except Exception as e:
            print(f"Error fixing gobuster command: {e}")
            if '-w' not in command_parts:
                command_parts.extend(['-w', '/usr/share/dirb/wordlists/common.txt'])
            return command_parts
        
    @staticmethod
    def check_wordlist_availability():
        wordlists = [
            '/usr/share/dirb/wordlists/common.txt',
            '/usr/share/dirb/wordlists/big.txt',
            '/usr/share/dirb/wordlists/small.txt',
            '/usr/share/wordlists/dirb/common.txt',
            '/usr/share/seclists/Discovery/Web-Content/common.txt'
        ]
        
        available = []
        for wordlist in wordlists:
            try:
                result = subprocess.run(
                    ['wsl', 'test', '-f', wordlist, '&&', 'echo', 'EXISTS'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if 'EXISTS' in result.stdout:
                    available.append(wordlist)
            except Exception:
                continue
        
        return available