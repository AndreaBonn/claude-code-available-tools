# ctools — Claude Code Tools Explorer

**Specifica tecnica e funzionale — v1.0**

> Documento autosufficiente pensato per essere passato direttamente a Claude Code (o a uno sviluppatore umano) per l'implementazione completa del progetto.

---

## 1. Executive summary

`ctools` è uno strumento che permette a un utente di Claude Code di **ispezionare in modo interattivo tutte le risorse configurate nel proprio ambiente**: slash commands, subagents, skills, server MCP, hook e variabili d'ambiente, sia a livello globale (`~/.claude/`) che a livello di progetto (`./.claude/`).

Il progetto è composto da **due artefatti distinti che cooperano**:

1. **`ctools`** — CLI Python standalone con interfaccia TUI (terminale full-screen) costruita con [Textual](https://textual.textualize.io/). Presenta una sidebar a sinistra con categorie espandibili, un pannello di dettaglio a destra, filtro di ricerca interattivo e auto-refresh ogni 3 secondi.
2. **`/tools`** — slash command globale installato in `~/.claude/commands/tools.md` che, dentro una sessione Claude Code, lancia `ctools` in tre modalità diverse (external, tui, inline).

**Obiettivo UX**: avere una "barra di navigazione sempre disponibile" sulle risorse Claude Code. Poiché Claude Code occupa l'intero terminale, la soluzione è aprire la TUI in una **finestra di terminale separata** (default `/tools external`), che l'utente può posizionare a fianco di Claude Code.

**Target**: Ubuntu Linux (utente primario), con supporto cross-distro Linux e macOS come bonus. Python 3.10+.

---

## 2. Ambito e requisiti

### 2.1 Requisiti funzionali

| ID | Requisito | Priorità |
|----|-----------|----------|
| F1 | Scansione automatica di tutte le risorse Claude Code in `~/.claude/` e in `./.claude/` del progetto corrente | MUST |
| F2 | Visualizzazione in TUI con sidebar sinistra espandibile per categoria | MUST |
| F3 | Pannello di dettaglio a destra con metadati completi della risorsa selezionata | MUST |
| F4 | Filtro interattivo per nome e descrizione (tasto `/`) | MUST |
| F5 | Distinzione visiva tra risorse global (`●` verde) e project (`◆` giallo) | MUST |
| F6 | Auto-refresh periodico della scansione (ogni 3 secondi) | MUST |
| F7 | Slash command `/tools` che lancia la TUI in terminale esterno | MUST |
| F8 | Modalità `/tools inline` che stampa un report testuale nella chat | MUST |
| F9 | Modalità `/tools tui` che lancia la TUI nel terminale corrente | SHOULD |
| F10 | Fallback automatico a inline se nessun terminale grafico è disponibile | MUST |
| F11 | Script di installazione one-shot | MUST |
| F12 | Il path del file sorgente di ogni risorsa è sempre visibile nel dettaglio | MUST |

### 2.2 Requisiti non funzionali

| ID | Requisito |
|----|-----------|
| NF1 | Il tempo di avvio della TUI deve essere < 500 ms su repo tipici |
| NF2 | Tutte le letture sono read-only: `ctools` non modifica mai nessun file di configurazione |
| NF3 | Nessuna dipendenza di sistema obbligatoria oltre Python 3.10 e `pip` |
| NF4 | Il parser di frontmatter YAML deve essere tollerante a file malformati (non deve crashare) |
| NF5 | La TUI deve funzionare correttamente con terminali di larghezza minima 80 colonne |
| NF6 | Il codice deve avere type hints completi e seguire PEP 8 |
| NF7 | Il pacchetto deve essere installabile via `pip install .` da sorgente |

### 2.3 Fuori ambito (v1.0)

- Editing delle risorse dalla TUI (solo lettura).
- Supporto Windows nativo (solo WSL2).
- Introspezione dello stato runtime di un server MCP (connesso/attivo/errore).
- Plugin system, marketplace, channels: non sono letti in v1.
- Memory files (`CLAUDE.md`, `CLAUDE.local.md`): non sono letti in v1.

---

## 3. Mappa delle risorse Claude Code da scansionare

Questa è la sorgente di verità per lo scanner. I path seguono la documentazione ufficiale Claude Code (ottobre 2025 e successive).

> **Nota sulla variabile d'ambiente `CLAUDE_CONFIG_DIR`**: se settata, sostituisce `~/.claude` ovunque. Lo scanner deve rispettarla.

### 3.1 Scope globale (user)

Base directory: `claude_home()` = `$CLAUDE_CONFIG_DIR` se definita, altrimenti `~/.claude`.

| Categoria | Path | Formato | Note |
|-----------|------|---------|------|
| Slash commands | `$HOME_CLAUDE/commands/**/*.md` | Markdown con frontmatter YAML opzionale | Il nome è il path relativo senza `.md`; subcartelle creano namespace (`cat:cmd`) |
| Subagents | `$HOME_CLAUDE/agents/**/*.md` | Markdown con frontmatter YAML | Formato ufficiale |
| Skills | `$HOME_CLAUDE/skills/<nome>/SKILL.md` | Markdown con frontmatter YAML | Ogni skill è una cartella |
| Settings (MCP + hooks + env) | `$HOME_CLAUDE/settings.json` | JSON | Chiavi rilevanti: `mcpServers`, `hooks`, `env` |
| Settings legacy | `~/.claude.json` | JSON | **Sempre in `~/.claude.json`, non in `CLAUDE_CONFIG_DIR`**. Contiene `mcpServers` user-level e `projects[<path>].mcpServers` per MCP per-progetto |
| Env vars runtime | Variabili `CLAUDE_*` e `ANTHROPIC_*` nel process env | — | Categoria `env`, scope `global`, origin `shell` |

### 3.2 Scope progetto

Il progetto viene rilevato risalendo l'albero da `cwd` fino a trovare una cartella `.claude/` o un file `.mcp.json`. Se non trovato, lo scope progetto è vuoto.

| Categoria | Path | Formato |
|-----------|------|---------|
| Slash commands | `<project>/.claude/commands/**/*.md` | Markdown con frontmatter |
| Subagents | `<project>/.claude/agents/**/*.md` | Markdown con frontmatter |
| Skills | `<project>/.claude/skills/<nome>/SKILL.md` | Markdown con frontmatter |
| Settings condivisi | `<project>/.claude/settings.json` | JSON (`mcpServers`, `hooks`, `env`) |
| Settings locali | `<project>/.claude/settings.local.json` | JSON (stessa struttura, gitignored) |
| MCP di progetto | `<project>/.mcp.json` | JSON con root `{mcpServers: {...}}` |

### 3.3 Formato dei file

#### 3.3.1 Slash command / subagent (markdown con frontmatter)

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
allowed-tools: Bash(git diff:*), Read
model: claude-sonnet-4-6
---

Quando ti viene chiesto di fare security review, analizza...
```

Regole di estrazione:
- Il frontmatter è delimitato da `---` all'inizio e `---` su una riga propria.
- Se `name` manca nel frontmatter, usare il path relativo senza estensione con separatori sostituiti da `:` (es. `git/commit.md` → `git:commit`).
- Se `description` manca, usare la prima riga non vuota del body (max 240 caratteri).
- Ogni altra chiave del frontmatter deve essere conservata in `extra`.

#### 3.3.2 Skill (`SKILL.md`)

Stesso formato markdown+frontmatter. Differenza: il file si chiama sempre `SKILL.md` e vive in una cartella il cui nome è il nome della skill.

```markdown
---
name: docx
description: Usare questa skill quando l'utente vuole creare...
---

# Istruzioni per la skill...
```

#### 3.3.3 `settings.json`

Estrarre **solo** queste chiavi top-level (il resto va ignorato):

- `mcpServers`: `dict[str, dict]` — ogni voce definisce un server MCP
- `hooks`: `dict[str, list[dict]]` — eventi → gruppi di hook
- `env`: `dict[str, str]` — variabili d'ambiente statiche

Un MCP server ha una di queste forme:

```json
{
  "mcpServers": {
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "remote-api": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

La descrizione mostrata deve essere `[<transport>] <command + args>` oppure `[<transport>] <url>`, troncata a 240 caratteri.

Un hook ha questa forma:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "~/.claude/hooks/log.sh"}
        ]
      }
    ]
  }
}
```

Per ogni hook definito, creare una `Resource` con:
- `name`: `<event>:<matcher>` (es. `PreToolUse:Bash`)
- `description`: `[<type>] <command>`
- `extra`: dict completo dell'hook

#### 3.3.4 `~/.claude.json` (legacy)

Oltre a `mcpServers` top-level, ha una struttura annidata:

```json
{
  "mcpServers": { "global-server": {...} },
  "projects": {
    "/home/user/project-a": {
      "mcpServers": { "project-specific-server": {...} }
    }
  }
}
```

Lo scanner deve estrarre **entrambi** (top-level E tutti i `projects[*].mcpServers`). Per quelli dentro `projects[...]`, il campo `extra["location"]` deve indicare il path del progetto.

#### 3.3.5 `.mcp.json` (project root)

Root del file:

```json
{
  "mcpServers": { "server-name": {...} }
}
```

### 3.4 Tabella di riepilogo categorie

| ID interno | Label UI | Icona | Sort order |
|------------|----------|-------|------------|
| `commands` | Slash Commands | ⌘ | 1 |
| `agents` | Subagents | ◈ | 2 |
| `skills` | Skills | ★ | 3 |
| `mcp` | MCP Servers | ⚡ | 4 |
| `hooks` | Hooks | ⎇ | 5 |
| `env` | Env Variables | $ | 6 |

Dentro ogni categoria, ordinare per: (scope `global` prima di `project`) poi alfabetico sul nome, case-insensitive.

---

## 4. Architettura

### 4.1 Struttura del pacchetto

```
ctools-project/
├── pyproject.toml
├── README.md
├── install.sh
├── src/
│   └── ctools/
│       ├── __init__.py
│       ├── __main__.py          # entry point: python -m ctools
│       ├── cli.py               # argparse + dispatch a tui/inline/external
│       ├── scanner.py           # logica di scansione (pura, testabile)
│       ├── inline.py            # rendering testo per /tools inline
│       ├── tui.py               # Textual app
│       └── terminal.py          # detection di terminali emulator disponibili
├── slash-command/
│   └── tools.md                 # da copiare in ~/.claude/commands/
└── tests/
    ├── test_scanner.py
    ├── test_inline.py
    └── fixtures/
        ├── home-claude/         # finto ~/.claude
        └── project-claude/      # finto progetto con .claude/
```

### 4.2 Flusso di esecuzione

```
Utente in Claude Code digita /tools
         │
         ▼
Claude Code legge ~/.claude/commands/tools.md
         │
         ▼
Il markdown istruisce Claude a eseguire "ctools --from-slash <mode>" via Bash
         │
         ▼
  ┌──────┴──────────────────────────┐
  │                                  │
  ▼ mode = external (default)        ▼ mode = inline
spawnea nuovo terminal emulator      stampa su stdout
con `ctools --mode tui`              report colorato
(la TUI gira isolata)                (torna al prompt di Claude)
         │
         ▼ mode = tui
esegue Textual app nel
terminale corrente
(Claude Code sospeso finché l'utente non chiude con q)
```

### 4.3 Modello dati

```python
# scanner.py
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Resource:
    category: str      # "commands" | "agents" | "skills" | "mcp" | "hooks" | "env"
    name: str          # nome univoco dentro la categoria
    scope: str         # "global" | "project"
    source: Path       # file che definisce la risorsa
    description: str = ""
    extra: dict = field(default_factory=dict)
```

Un'unica funzione pubblica espone l'API dello scanner:

```python
def scan_all(project_dir: Path | None = None) -> list[Resource]: ...
```

Helper di raggruppamento:

```python
def group_by_category(resources: list[Resource]) -> dict[str, list[Resource]]: ...
```

### 4.4 Dipendenze Python

In `pyproject.toml`:

```toml
[project]
name = "ctools"
version = "1.0.0"
description = "Interactive explorer for Claude Code tools and configuration"
requires-python = ">=3.10"
dependencies = [
    "textual>=0.80.0",
    "rich>=13.7.0",
]

[project.scripts]
ctools = "ctools.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov", "mypy", "ruff"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ctools"]
```

**Perché queste scelte**:
- `textual` è lo standard de facto per TUI Python moderne, ha async runtime integrato e ottimo support per bindings da tastiera.
- `rich` è transitivo di `textual` ma lo esponiamo esplicitamente per il rendering colorato del mode `inline`.
- Python 3.10+ per `X | None` syntax e dataclass features.

---

## 5. Specifica dettagliata dei moduli

### 5.1 `scanner.py`

Deve implementare tutte le funzioni descritte in sezione 3. Requisiti chiave:

- `claude_home()` → rispetta `CLAUDE_CONFIG_DIR`, default `~/.claude`
- `project_root(start: Path | None = None) -> Path | None` → risale l'albero cercando `.claude/` o `.mcp.json`
- `parse_frontmatter(text: str) -> tuple[dict, str]` → parser YAML minimale (key: value per riga, gestisce quote semplici/doppie, commenti `#`, righe vuote)
- Tutte le operazioni di I/O devono essere wrappate in `try/except OSError` e `try/except json.JSONDecodeError` e non devono mai propagare eccezioni a `scan_all()`
- Se `source` è un file inesistente o non leggibile, la risorsa semplicemente non viene inclusa nell'output

**Test unitari obbligatori** (in `tests/test_scanner.py`):

1. `test_parse_frontmatter_basic` — parsing standard
2. `test_parse_frontmatter_missing` — file senza frontmatter → `({}, text)`
3. `test_parse_frontmatter_malformed` — frontmatter rotto → non crasha, ritorna `({}, text)` o parziale
4. `test_scan_commands_with_fixtures` — usa `tests/fixtures/home-claude/commands/` con 3 file di esempio
5. `test_scan_skills_ignores_dir_without_SKILL_md` — cartella skill senza `SKILL.md` viene saltata
6. `test_scan_mcp_from_settings` — estrae server MCP stdio e http
7. `test_scan_hooks_expands_matcher_groups` — un matcher con 2 hook def produce 2 risorse
8. `test_scan_claude_json_projects` — estrae MCP anche da `projects[<path>].mcpServers`
9. `test_project_root_walks_up` — cwd = sottocartella, trova `.claude/` ancestrale
10. `test_claude_home_respects_env_var` — `CLAUDE_CONFIG_DIR` override

### 5.2 `inline.py`

Espone `render(filter_term: str = "", use_color: bool = True) -> str` e `main_inline() -> int`.

Comportamento:

- Legge le risorse via `scan_all()`
- Applica il filtro (substring case-insensitive su `name` e `description`)
- Raggruppa per categoria nell'ordine di sezione 3.4
- Stampa intestazione: `Claude Code — Available Tools`, path di `claude_home()` e project root
- Per ogni categoria: header con icona + label + count; sotto, le risorse con badge scope, nome, descrizione (truncata a 100 char) e source path
- Categorie vuote: mostrate con `(0)` in grigio
- Footer: `Total: N resources`
- Colori ANSI solo se `sys.stdout.isatty()` è True

CLI args accettati da `main_inline`:
- `-f FILTER` / `--filter FILTER` / `--filter=FILTER` / primo arg positional → imposta filtro
- Exit code 0 sempre (salvo errori fatali)

### 5.3 `tui.py`

Textual app con questo layout CSS:

```
Screen {
    layout: vertical;
}
#body {
    height: 1fr;
    layout: horizontal;
}
#sidebar {
    width: 42;
    border-right: solid $accent;
}
#detail {
    padding: 1 2;
    width: 1fr;
}
#filter-bar {
    dock: bottom;
    height: 3;
    display: none;
}
#filter-bar.visible { display: block; }
```

Widgets:
- `Header` standard Textual (mostra titolo app)
- `SidebarTree(Tree)`: albero collassabile, root nascosta, 6 nodi categoria; espande automaticamente se filtro attivo o se la categoria ha ≤ 8 elementi
- `DetailPanel(Static)`: usa markup Rich per formattare
- `Input(id="filter")`: appare sopra il footer quando si preme `/`, si nasconde con `Escape`
- `Footer` standard che mostra i key bindings

Key bindings:

| Tasto | Azione |
|-------|--------|
| `q` | Quit |
| `/` | Apre filter bar e focus sul campo |
| `Escape` | Chiude filter bar e pulisce filtro |
| `r` | Refresh manuale |
| `↑ ↓` | Naviga tree (comportamento nativo Tree) |
| `Enter` | Espande/collassa categoria oppure seleziona leaf |
| `Space` | Toggle espansione |

Comportamenti richiesti:

1. **Auto-refresh**: `set_interval(3.0, self._auto_refresh)` che ri-chiama `scan_all()` e, se il set di risorse è cambiato (confronto per `(category, name, scope, str(source))`), ricostruisce il tree preservando la selezione corrente per nome se possibile.
2. **Filtro live**: `on_input_changed` aggiorna immediatamente il tree, e se c'è filtro espande tutte le categorie per mostrare match.
3. **Selezione**: `on_tree_node_highlighted` aggiorna `DetailPanel` con i dati della risorsa corrispondente (via lookup in `_node_to_resource`).
4. **Scope badge inline**: `● verde` per global, `◆ giallo` per project, accanto al nome nella sidebar.
5. **Stato iniziale detail**: se nessuna risorsa è selezionata, mostra una legenda dei badge.

### 5.4 `terminal.py`

Una sola funzione pubblica:

```python
def find_terminal_emulator() -> tuple[list[str], str] | None:
    """
    Ritorna (argv_prefix, name) per lanciare un comando in un nuovo terminale,
    o None se nessun emulatore è disponibile.
    L'argv_prefix è pensato per essere esteso con ['ctools', '--mode', 'tui'].
    """
```

Ordine di ricerca:

1. `$TERMINAL` env var, se settata e l'eseguibile esiste in `PATH` → `[$TERMINAL, "-e"]`
2. `gnome-terminal` → `["gnome-terminal", "--", "bash", "-lc"]`
3. `konsole` → `["konsole", "-e"]`
4. `xfce4-terminal` → `["xfce4-terminal", "-x"]`
5. `x-terminal-emulator` → `["x-terminal-emulator", "-e"]`
6. `xterm` → `["xterm", "-e"]`
7. macOS: se `platform.system() == "Darwin"`, usa `osascript` per aprire Terminal.app
8. Nessuno trovato → `None`

La detection deve verificare con `shutil.which()` che l'eseguibile esista realmente.

### 5.5 `cli.py`

Argparse con subcommands / flags:

```
ctools [--mode {tui,inline,external,auto}] [--filter TERM] [--from-slash]
```

Comportamento:

- `--mode auto` (default): se stdout è TTY e la finestra è ≥ 80 colonne, usa `tui`; altrimenti `inline`
- `--mode tui`: lancia la Textual app in-process
- `--mode inline`: stampa il report di `inline.py`
- `--mode external`: trova un terminale via `terminal.py` e spawna `ctools --mode tui` lì dentro. Se `find_terminal_emulator()` torna None, stampa un warning e ricade su `inline`.
- `--filter TERM`: passato a inline o preimpostato nella TUI
- `--from-slash`: flag informativo che attiva un banner iniziale "Launched via /tools" nella TUI e, in inline, aggiunge un footer con suggerimento "Usa `/tools inline` o `/tools tui` per cambiare modalità"

Entry point:

```python
def main() -> int:
    args = _parse_args()
    if args.mode == "auto":
        args.mode = "tui" if _should_use_tui() else "inline"
    if args.mode == "inline":
        return inline.run(filter_term=args.filter, from_slash=args.from_slash)
    if args.mode == "tui":
        return tui.run(filter_term=args.filter, from_slash=args.from_slash)
    if args.mode == "external":
        return _launch_external(args)
    return 2
```

---

## 6. Slash command `/tools`

File: `slash-command/tools.md` → installato in `~/.claude/commands/tools.md`.

### 6.1 Contenuto del markdown

```markdown
---
name: tools
description: Open the Claude Code tools explorer (ctools). Shows all configured slash commands, subagents, skills, MCP servers, hooks, and env variables from ~/.claude and the current project.
argument-hint: [external|tui|inline] [filter_term]
allowed-tools: Bash(ctools:*)
---

Open the ctools explorer based on the argument provided.

The first argument (if present) selects the mode:
- `external` (default): open the TUI in a new terminal window, leaving this chat intact
- `tui`: open the TUI in the current terminal (Claude Code will be suspended until you quit with `q`)
- `inline`: print a static text report directly in this chat

The second argument (if present) is a filter term passed to ctools.

Arguments received: $ARGUMENTS

Execute:

```bash
MODE="${1:-external}"
FILTER="${2:-}"
if [ -n "$FILTER" ]; then
  ctools --mode "$MODE" --filter "$FILTER" --from-slash
else
  ctools --mode "$MODE" --from-slash
fi
```

If `ctools` is not found on PATH, tell the user to run the installer:
`bash <(curl ...)` or `cd ~/ctools-project && ./install.sh`.

If mode is `external` and the command reports "no terminal emulator found", suggest retrying with `/tools tui` or `/tools inline`.
```

### 6.2 Esempi d'uso

| Comando dell'utente | Risultato |
|---------------------|-----------|
| `/tools` | Apre TUI in finestra terminale separata |
| `/tools external` | Idem |
| `/tools tui` | Apre TUI nel terminale corrente |
| `/tools inline` | Stampa report testuale nella chat |
| `/tools inline git` | Stampa report filtrato per `git` |
| `/tools external mcp` | Apre TUI esterna, filtro preimpostato su `mcp` |

---

## 7. Installazione

### 7.1 `install.sh`

Script bash POSIX-compatible che:

1. Verifica `python3 --version >= 3.10`; se no, errore ed esci.
2. Verifica che `pip` sia disponibile; se no, errore ed esci.
3. Crea `~/.local/pipx/venvs/ctools` OPPURE usa `pipx install` se disponibile (preferenza per `pipx`). Fallback: `pip install --user .`.
4. Verifica che `~/.local/bin` sia in `PATH`; se no, stampa istruzioni per aggiungerlo a `.bashrc`/`.zshrc`.
5. Copia `slash-command/tools.md` in `~/.claude/commands/tools.md`, creando la directory se non esiste. Se il file esiste già, chiede conferma (o accetta flag `--force`).
6. Esegue `ctools --mode inline` come smoke test e mostra il numero di risorse trovate.
7. Stampa un recap finale con:
   - Path dell'eseguibile `ctools`
   - Path dello slash command installato
   - Esempio d'uso: `ctools` da terminale, `/tools` da Claude Code

### 7.2 Disinstallazione

Documentata nel README:

```bash
pipx uninstall ctools        # o: pip uninstall ctools
rm -f ~/.claude/commands/tools.md
```

---

## 8. Convenzioni di codice

- **Type hints**: obbligatorie su tutte le funzioni pubbliche e metodi di classe.
- **Docstring**: stile Google su tutte le funzioni pubbliche.
- **Linting**: `ruff check src/ tests/` deve passare pulito.
- **Formattazione**: `ruff format`.
- **Type checking**: `mypy --strict src/ctools/scanner.py src/ctools/inline.py` deve passare pulito; i moduli TUI possono rilassare a `--ignore-missing-imports` per Textual.
- **No I/O in costruttori**: le dataclass non devono leggere file; lo fa solo lo scanner.
- **No print() fuori da `inline.py` e `cli.py`**: usare `logging` se serve diagnostica.

---

## 9. Testing

### 9.1 Fixture di test

Creare in `tests/fixtures/` una struttura completa che simuli sia `~/.claude` che un progetto:

```
tests/fixtures/
├── home-claude/
│   ├── commands/
│   │   ├── simple.md              # senza frontmatter
│   │   ├── with-fm.md             # con frontmatter completo
│   │   └── namespace/
│   │       └── cmd.md
│   ├── agents/
│   │   └── reviewer.md
│   ├── skills/
│   │   ├── valid-skill/SKILL.md
│   │   └── empty-dir/             # no SKILL.md → ignorato
│   └── settings.json              # con mcpServers + hooks + env
└── project-claude/
    ├── .claude/
    │   ├── commands/local-cmd.md
    │   ├── settings.json
    │   └── settings.local.json
    └── .mcp.json
```

### 9.2 Suite minima

- ≥ 25 test unitari totali
- Coverage ≥ 85% su `scanner.py` e `inline.py`
- I test TUI sono opzionali (Textual ha `App.run_test()` ma richiedono setup); almeno un smoke test che costruisce la app e verifica che compose() produca i widget attesi.

### 9.3 Comando di verifica

```bash
pytest tests/ -v --cov=ctools --cov-report=term-missing
```

---

## 10. Roadmap post-v1 (non implementare ora, documentare nel README)

- Editing di risorse direttamente dalla TUI (apre `$EDITOR` sul file sorgente)
- Health check dei server MCP (prova a connettersi e mostra stato)
- Export del report in JSON/YAML
- Supporto per memory files (`CLAUDE.md` chain)
- Supporto per plugins e marketplace
- Integrazione con `fzf` in modalità inline per filtro interattivo senza TUI
- Watch mode che tiene aperta la TUI e notifica via OS notification quando compaiono nuove risorse

---

## 11. Criteri di accettazione (definition of done)

Il progetto è considerato completo quando tutti i seguenti punti sono verificati su Ubuntu 22.04 o 24.04:

1. ✅ `pip install .` dal repo clonato termina senza errori
2. ✅ `ctools --help` stampa l'help senza crash
3. ✅ `ctools --mode inline` mostra tutte le risorse di `~/.claude` con colori ANSI
4. ✅ `ctools --mode inline --filter xyz` filtra correttamente
5. ✅ `ctools` (auto mode) apre la TUI su un terminale ≥ 80 colonne
6. ✅ Nella TUI: `/` apre filtro, typing filtra live, `Escape` pulisce
7. ✅ Nella TUI: le 6 categorie appaiono sempre, anche se vuote
8. ✅ Nella TUI: aggiungendo un file `.md` in `~/.claude/commands/` mentre la TUI è aperta, il file appare entro 3-4 secondi senza intervento
9. ✅ `ctools --mode external` apre una nuova finestra gnome-terminal (o equivalente) con la TUI
10. ✅ Dopo installazione, `/tools` dentro Claude Code lancia la TUI in finestra esterna
11. ✅ `/tools inline` dentro Claude Code stampa il report nella chat
12. ✅ `pytest` passa pulito con ≥ 85% coverage sui moduli core
13. ✅ `ruff check` e `mypy --strict` sui moduli core passano senza errori
14. ✅ Lo scanner non crasha mai in presenza di JSON malformati, frontmatter rotti, permessi negati, o file binari in directory di markdown

---

## 12. Note per l'implementatore

- **Ordine di implementazione consigliato**: `scanner.py` + test → `inline.py` + test → `cli.py` (solo inline) → `terminal.py` → `tui.py` → `cli.py` (completo) → `install.sh` → slash command.
- **Non implementare tutto in un singolo file**: i moduli sono già disegnati per essere piccoli e testabili separatamente.
- **Testa prima `scanner.py` con fixture reali**: è il componente più complesso e tutto il resto ne dipende.
- **Se Textual ha breaking changes**: fissa la versione minima in `pyproject.toml` e documentalo.
- **Sicurezza**: lo scanner NON deve mai eseguire `command` fields letti da config file — solo leggerli e mostrarli.
- **Graceful degradation**: se `~/.claude` non esiste (primo run di Claude Code), scanner deve ritornare solo le risorse di progetto e process env, senza errori.

---

## 13. Riferimenti

- Claude Code settings: https://code.claude.com/docs/en/settings
- Subagents: https://code.claude.com/docs/en/sub-agents
- Slash commands: https://code.claude.com/docs/en/slash-commands
- Skills: https://code.claude.com/docs/en/skills
- Hooks: https://code.claude.com/docs/en/hooks
- MCP servers: https://code.claude.com/docs/en/mcp
- Textual docs: https://textual.textualize.io/
