# BeatRoot

BeatRoot is a local-first, modular security assessment copilot for authorized environments. It helps with reconnaissance and enumeration workflows by combining pluggable LLM guidance, tool wrappers, parsers, session memory, and an interactive CLI.

This implementation is intentionally safety-bounded:

- It supports reconnaissance and enumeration tooling.
- It stores findings, prior commands, and reasoning context.
- It does not autonomously perform exploitation, brute forcing, persistence, or destructive actions.
- It always surfaces commands before execution and can require confirmation.

## Features

- Local-first LLM support with `ollama` as the default provider
- Optional OpenAI-compatible and Claude-compatible API clients
- Modular tool wrappers for `nmap`, `ffuf`, `gobuster`, and guarded generic commands
- Structured parsing for open ports, services, and web enumeration findings
- Persistent JSON session memory
- Interactive CLI loop with reasoning, next-step suggestions, and action logging
- Plugin-ready tool registry architecture

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

Start from the example file:

```bash
cp config.example.yaml config.yaml
```

Default configuration uses a PentestGPT-style `model` block and points to Ollama via its OpenAI-compatible API endpoint:

```yaml
model:
  provider: ollama
  api_base: http://localhost:11434/v1
  model: deepseek-coder
  api_key: null
```

## Usage

```bash
beatroot --target 192.168.1.10
beatroot --target 192.168.1.10 --config config.yaml --wordlist /usr/share/wordlists/dirb/common.txt
beatroot --target scanme.nmap.org --non-interactive --max-steps 3
```

## Project Layout

```text
beatroot/
  agent/
  cli/
  config/
  core/
  interface/
  llm/
  memory/
  parser/
  prompts/
  tools/
```

## Notes

- BeatRoot is intended for authorized testing, training labs, and defensive validation.
- Tool wrappers fail gracefully when binaries are missing.
- When no LLM is reachable, BeatRoot falls back to a deterministic heuristic planner.
