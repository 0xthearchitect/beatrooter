from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class LLMConfig:
    provider: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    model: str = "mistral"
    api_key: str | None = None
    timeout: int = 60


@dataclass(slots=True)
class AgentConfig:
    max_steps: int = 6
    show_reasoning: bool = True
    auto_approve_safe_tools: bool = False
    allow_llm_planning: bool = True


@dataclass(slots=True)
class SafetyConfig:
    authorized_use_only: bool = True
    allow_generic_command_execution: bool = False
    require_confirmation_for: list[str] = field(
        default_factory=lambda: ["nmap", "gobuster", "ffuf", "generic_command"]
    )
    blocked_keywords: list[str] = field(
        default_factory=lambda: [
            "rm",
            "mkfs",
            "dd",
            "hydra",
            "metasploit",
            "msfconsole",
            "sqlmap",
            "crackmapexec",
        ]
    )
    allowed_command_prefixes: list[str] = field(
        default_factory=lambda: ["echo", "host", "dig", "curl", "nmap", "gobuster", "ffuf"]
    )


@dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    directory: str = ".beatroot/logs"


@dataclass(slots=True)
class MemoryConfig:
    directory: str = ".beatroot/sessions"


@dataclass(slots=True)
class ToolDefaultsConfig:
    nmap_top_ports: int = 1000
    web_wordlist: str | None = None


@dataclass(slots=True)
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    tool_defaults: ToolDefaultsConfig = field(default_factory=ToolDefaultsConfig)

    @classmethod
    def from_dict(cls, raw: dict) -> "AppConfig":
        llm_raw = raw.get("llm", raw.get("model", {}))
        if "api_base" in llm_raw and "base_url" not in llm_raw:
            llm_raw = {**llm_raw, "base_url": llm_raw["api_base"]}
        if "api_base" in llm_raw:
            llm_raw = {key: value for key, value in llm_raw.items() if key != "api_base"}
        return cls(
            llm=LLMConfig(**llm_raw),
            agent=AgentConfig(**raw.get("agent", {})),
            safety=SafetyConfig(**raw.get("safety", {})),
            logging=LoggingConfig(**raw.get("logging", {})),
            memory=MemoryConfig(**raw.get("memory", {})),
            tool_defaults=ToolDefaultsConfig(**raw.get("tool_defaults", {})),
        )
