#!/usr/bin/env python3

GREEN = "\033[92m"
PURPLE = "\033[95m"
RESET = "\033[0m"
CYAN = "\033[96m"
GRAY = "\033[90m"
BOLD = "\033[1m"

ASCII = r"""              __
             /  \     __
             |   |   /  |
              \  \  /   /
               \  \/   /
               /  |   |
               |  |   |
                \ |  /
                 !| !
       ___  ___  !|/  ___
      /   |/   \/   \/   \
      |                   \
      |   |    |    |     |
      |   |    |    |     |
      |   |    |    |     |
      |___|    |    |     |\
          |____|____|_____| \
                |           |
                |__________/"""

INTRO = f"""
{GRAY}[+] Initializing BeatConsole...{RESET}

{BOLD}{CYAN}Welcome to BeatConsole{RESET}

{GRAY}----------------------------------------{RESET}

{CYAN}> Tools:{RESET}           Run your tools
{CYAN}> Nodes:{RESET}           Build custom nodes
{CYAN}> Challenges:{RESET}      Test your skills

{GRAY}----------------------------------------{RESET}

This is cybersecurity in its raw form.
No UI. No guidance. No safety nets.

{GRAY}BeatRooter was just the beginning...{RESET}

{BOLD}> Are you ready?{RESET}
"""

def main():
    lines = ASCII.splitlines()

    for i, line in enumerate(lines):
        # Linha especial onde queres mistura de cores
        if "___  ___  !|/  ___" in line:
            # pinta só os ___ de roxo
            parts = line.split("___")
            colored_line = ""

            for j, part in enumerate(parts):
                colored_line += GREEN + part
                if j < len(parts) - 1:
                    colored_line += PURPLE + "___"

            print(colored_line + RESET)

        # Parte de cima (verde)
        elif i < 9:
            print(GREEN + line + RESET)

        # Resto (roxo)
        else:
            print(PURPLE + line + RESET)

    print()
    print(INTRO)


if __name__ == "__main__":
    main()
