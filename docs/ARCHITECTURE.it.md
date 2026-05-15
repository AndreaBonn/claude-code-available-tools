# Architettura

Documentazione tecnica degli internals di cctools. Per l'utilizzo, vedi il [README](../README.it.md).

## Panoramica del sistema

Cinque moduli con separazione netta delle responsabilita: dispatch CLI, discovery del filesystem, e tre backend di visualizzazione.

```mermaid
%%{init: {'theme': 'default'}}%%
graph LR
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff

    cli["cli.py<br/>Punto di ingresso"]:::core

    subgraph display["Backend di visualizzazione"]
        direction TB
        tui["tui.py<br/>TUI Textual"]:::core
        inline_mod["inline.py<br/>Report Rich"]:::core
    end

    terminal["terminal.py<br/>Rilevamento terminale"]:::ext
    ext_term(["Terminale esterno"]):::ext

    scanner["scanner.py<br/>Motore di discovery"]:::engine

    subgraph config["Sorgenti configurazione"]
        direction TB
        global_cfg["~/.claude/<br/>Config globale"]:::data
        project_cfg[".claude/<br/>Config progetto"]:::data
    end

    cli --> tui
    cli --> inline_mod
    cli --> terminal
    terminal -.-> ext_term

    tui --> scanner
    inline_mod --> scanner

    scanner --> global_cfg
    scanner --> project_cfg
```

| Colore | Significato |
|--------|------------|
| Blu | Moduli core (entry point, visualizzazione) |
| Verde | Motore di discovery |
| Ambra | Sorgenti dati di configurazione |
| Grigio | Esterni/dipendenti dalla piattaforma |

## Flusso di discovery dello scanner

`scanner.scan_all()` legge dalle directory di configurazione globale e di progetto, oltre a sorgenti extra (file legacy, variabili d'ambiente). Ogni sorgente produce istanze della dataclass `Resource`, unite in una singola lista ordinata.

```mermaid
%%{init: {'theme': 'default'}}%%
graph TD
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff

    scan_all["scan_all#40;#41;"]:::engine

    subgraph global_src["Globale ~/.claude/"]
        g_content["commands/*.md<br/>agents/*.md<br/>skills/SKILL.md<br/>settings.json"]:::data
    end

    subgraph project_src["Progetto .claude/"]
        p_content["commands/*.md<br/>agents/*.md<br/>skills/SKILL.md<br/>settings.json"]:::data
    end

    extra_src["Sorgenti extra"]:::ext
    extra_detail[".mcp.json<br/>.claude.json #40;legacy#41;<br/>CLAUDE_* / ANTHROPIC_* env"]:::ext

    output["list#91;Resource#93;"]:::core

    scan_all --> global_src
    scan_all --> project_src
    scan_all --> extra_src
    extra_src --- extra_detail

    g_content --> output
    p_content --> output
    extra_detail --> output
```

Da `settings.json`, lo scanner estrae tre tipi di risorse: server MCP (`mcpServers`), hook (`hooks`) e variabili d'ambiente. Il parser YAML frontmatter e integrato (nessuna dipendenza da PyYAML) e supporta scalari multilinea (`>`, `|`).

## Dispatch delle modalita CLI

`cli.py` instrada verso uno dei tre backend di visualizzazione in base al flag `--mode` o al rilevamento automatico. In modalita auto, la larghezza del terminale determina se avviare la TUI completa o ricadere sull'output testuale inline.

```mermaid
sequenceDiagram
    participant user as Utente
    participant cli as cli.py
    participant scanner as scanner.py
    participant tui as tui.py
    participant inline_mod as inline.py
    participant terminal as terminal.py

    user->>cli: cctools --mode X

    alt mode = auto
        cli->>cli: Controlla colonne terminale
        alt colonne >= 80
            cli->>tui: CtoolsApp.run()
        else colonne < 80
            cli->>inline_mod: inline.run()
        end
    else mode = tui
        cli->>tui: CtoolsApp.run()
    else mode = inline
        cli->>inline_mod: inline.run()
    else mode = external
        cli->>terminal: find_terminal_emulator()
        terminal-->>cli: argv prefix
        cli->>cli: subprocess.Popen cctools --mode tui
    end

    tui->>scanner: scan_all()
    scanner-->>tui: lista Resource
    Note over tui: Auto-refresh ogni 3s

    inline_mod->>scanner: scan_all()
    scanner-->>inline_mod: lista Resource
    inline_mod-->>user: Output Rich text
```

La TUI usa `set_interval(3)` di Textual per il refresh periodico. Ad ogni tick, confronta le fingerprint delle risorse (categoria, nome, scope, sorgente) e ricostruisce l'albero solo quando rileva cambiamenti.

## Pipeline CI

GitHub Actions esegue ad ogni push e PR su main, su una matrice di versioni Python.

```mermaid
%%{init: {'theme': 'default'}}%%
graph LR
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff

    trigger["Push / PR<br/>su main"]:::ext
    matrix["Matrice<br/>Python 3.10, 3.12, 3.13"]:::ext

    lint["Lint<br/>ruff check + format"]:::core
    test_step["Test<br/>pytest + coverage"]:::engine
    typecheck["Typecheck<br/>mypy"]:::core
    audit["Sicurezza<br/>pip-audit"]:::data
    badges["Badge<br/>solo main"]:::data

    trigger --> matrix
    matrix --> lint
    lint --> test_step
    test_step --> typecheck
    typecheck --> audit
    audit -->|"branch main"| badges
```

La generazione dei badge (conteggio test, percentuale copertura) avviene solo sul branch main e committa file JSON dei badge nel repository.
