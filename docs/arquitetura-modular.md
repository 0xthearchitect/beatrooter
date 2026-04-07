# Arquitetura modular proposta

## Objetivo

Separar o projeto em blocos por feature/produto para reduzir acoplamento, melhorar a documentação e permitir manutenção independente de cada parte:

- BeatRooter Canvas
- BeatNote
- Sandbox
- Tools e integrações
- Código partilhado

## Estado atual

Hoje o código está organizado por camada técnica dentro de uma única árvore:

- ui/
- core/
- models/
- integrations/
- tools/
- agent/

Isto funciona, mas mistura responsabilidades de features diferentes no mesmo espaço. O resultado é:

- imports muito espalhados
- risco de dependências circulares
- documentação pouco clara sobre o que pertence a cada feature
- refactors grandes quando uma feature muda

## Estrutura alvo

A proposta é separar cada feature em subpastas próprias, mantendo um pacote partilhado para tipos e utilitários comuns.

```text
BeatRooter/
├── BeatRooter/
│   ├── features/
│   │   ├── beatroot_canvas/
│   │   │   ├── core/
│   │   │   ├── ui/
│   │   │   ├── models/
│   │   │   └── integrations/
│   │   ├── beatnote/
│   │   │   ├── core/
│   │   │   ├── ui/
│   │   │   └── models/
│   │   ├── sandbox/
│   │   │   ├── core/
│   │   │   ├── ui/
│   │   │   └── models/
│   │   └── tools/
│   │       ├── core/
│   │       ├── parsers/
│   │       ├── docker/
│   │       └── ui/
│   ├── shared/
│   │   ├── models/
│   │   ├── ui/
│   │   ├── utils/
│   │   └── integrations/
│   ├── assets/
│   └── main.py
├── docs/
└── tests/
```

## Regras de organização

### 1) Cada feature vive num namespace próprio

Exemplos:

- BeatNote: `features/beatnote/`
- Sandbox: `features/sandbox/`
- Canvas principal: `features/beatroot_canvas/`
- Ferramentas: `features/tools/`

### 2) `shared/` só pode conter código reutilizável e neutro

Aqui entram:

- modelos de domínio comuns
- helpers de caminho, imagem e tema
- interfaces e contratos genéricos
- integrações sem lógica específica de feature

Não deve conter regras de negócio de uma feature concreta.

### 3) UI, core e models ficam juntos por feature

Cada feature deve poder ser entendida sem abrir metade do projeto.

Exemplo de BeatNote:

- `features/beatnote/core/beatnote_service.py`
- `features/beatnote/core/beatnote_model.py`
- `features/beatnote/ui/beatnote_panel.py`
- `features/beatnote/ui/beatnote_dialog.py`

### 4) Imports devem seguir uma direção clara

Regra prática:

- feature A pode importar de `shared/`
- feature A pode importar do seu próprio pacote
- feature A não deve importar diretamente de internals de feature B
- se houver necessidade real de partilha, mover o contrato para `shared/`

### 5) O entrypoint fica fino

O `main.py` deve apenas:

- configurar a app
- escolher a feature inicial
- abrir a janela principal
- delegar a lógica para as features

Não deve concentrar regras de negócio.

## Mapeamento sugerido do código atual

### BeatRooter Canvas

Mover gradualmente para a feature do canvas:

- `ui/main_window.py`
- `ui/canvas_widget.py`
- `ui/detail_panel.py`
- `ui/node_widget.py`
- `ui/dynamic_edge.py`
- `ui/toolbox.py`
- `core/graph_manager.py`
- `core/storage_manager.py`
- `core/theme_manager.py`
- `core/node_factory.py`
- `models/node.py`
- `models/edge.py`
- `models/graph_data.py`

### BeatNote

- `core/beatnote_model.py`
- `core/beatnote_service.py`
- `ui/beatnote_main_window.py`
- `ui/beatnote_panel.py`
- `ui/beatnote_dialog.py`

### Sandbox

- `core/sandbox/`
- `ui/sandbox/`
- `models/object_model.py`

### Tools

- `tools/`
- `downloaded_tools/`
- `agent/`

## Fases de migração recomendadas

### Fase 1 — documentação e contratos

- documentar estrutura alvo
- definir dependências permitidas
- criar aliases temporários de importação
- garantir testes antes da mudança estrutural

### Fase 2 — BeatNote

- mover BeatNote para a sua feature própria
- manter API pública estável
- atualizar imports e testes

### Fase 3 — Canvas principal

- separar UI pesada do core
- reduzir dependências diretas no `main.py`
- estabilizar os modelos partilhados

### Fase 4 — limpeza final

- remover imports antigos
- atualizar README e docs
- reorganizar testes por feature

## Estado atual da migração

Concluído nesta fase:

- BeatNote já está em `features/beatnote/`
- Tools já estão em `features/tools/`
- Sandbox já está em `features/sandbox/` e os entrypoints principais já importam dessa feature
- `main.py` já consome o Canvas por `features.beatroot_canvas.ui.main_window`
- Canvas migrado fisicamente para `features/beatroot_canvas/` (`ui`, `core`, `models`)
- Wrappers temporários legados de Canvas em `ui/`, `core/` e `models/` removidos
- Testes do BeatNote reorganizados para `tests/projects/beatnote/`
- Scenario Copilot removido (código e documentação)

Pendente:

- reorganizar os restantes testes por feature em `tests/projects/...`

## Critérios de sucesso

- cada feature abre sem depender de internals de outra feature
- os imports ficam previsíveis e curtos
- os testes passam sem adaptações especiais
- a documentação passa a refletir o layout real
- o `main.py` deixa de ser o centro lógico da aplicação

## Recomendação prática

Não mover tudo de uma vez.

A ordem mais segura é:

1. BeatNote
2. Tools
3. Sandbox
4. Canvas principal

Isto reduz o risco de quebrar a aplicação enquanto a estrutura evolui.
