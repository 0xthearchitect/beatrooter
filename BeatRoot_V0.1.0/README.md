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
- Scenario-only mode to answer from prebuilt environment evidence without running tools

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
beatroot --target internal-lab --scenario-file scenario.json --scenario-only
<<<<<<< codex/implement-beatroot-agent-interaction-logic
beatroot --target internal-lab --scenario-json '{"nodes":[{"id":"web1","services":[{"port":443,"name":"https"}]}]}' --scenario-only
cat scenario.json | beatroot --target internal-lab --scenario-stdin --scenario-only
```

### Scenario-only integration (BeatRooter nodes)

If you already have a scenario graph in BeatRooter and want BeatRoot to only reason over that data:

1. Export the node context (hosts, services, paths, notes, findings) to a JSON or text file.
2. Run BeatRoot with `--scenario-file <file>` and `--scenario-only`.
3. In this mode BeatRoot receives the scenario as evidence and blocks command execution (`nmap`, `ffuf`, `gobuster`, etc).
4. To allow mixed behavior, omit `--scenario-only` and keep `--scenario-file` so the model can still use the scenario as additional context.

You can also avoid files completely by sending JSON directly:

- CLI inline payload: `--scenario-json '{...}'`
- CLI pipe mode: `--scenario-stdin` (read from stdin)
- Programmatic integration from BeatRooter Python code:

```python
from beatroot.core import run_assessment

result = run_assessment(
    config=config,
    target="internal-lab",
    task="Analyze this in-scope environment graph.",
    model=config.llm.model,
    scenario_context=graph_json_dict,  # dict/list/string accepted
    scenario_only=True,
)
=======
>>>>>>> dev
```

### Scenario-only integration (BeatRooter nodes)

If you already have a scenario graph in BeatRooter and want BeatRoot to only reason over that data:

1. Export the node context (hosts, services, paths, notes, findings) to a JSON or text file.
2. Run BeatRoot with `--scenario-file <file>` and `--scenario-only`.
3. In this mode BeatRoot receives the scenario as evidence and blocks command execution (`nmap`, `ffuf`, `gobuster`, etc).
4. To allow mixed behavior, omit `--scenario-only` and keep `--scenario-file` so the model can still use the scenario as additional context.

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
