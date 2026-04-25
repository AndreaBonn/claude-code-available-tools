[English](README.md) | **Italiano**

# Claude Code Available Tools by Bonn

Explorer interattivo per i tool e la configurazione di Claude Code. Scansiona e visualizza slash command, subagent, skill, server MCP, hook e variabili d'ambiente dalle configurazioni globali (`~/.claude/`) e di progetto (`.claude/`).

[![CI](https://github.com/AndreaBonn/claude-code-available-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/claude-code-available-tools/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/claude-code-available-tools/main/badges/test-badge.json)](https://github.com/AndreaBonn/claude-code-available-tools/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/claude-code-available-tools/main/badges/coverage-badge.json)](https://github.com/AndreaBonn/claude-code-available-tools/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blueviolet.svg)](SECURITY.it.md)

## Funzionalità

- Tre modalità di visualizzazione: TUI a schermo intero (Textual), report testuale inline (Rich), finestra terminale esterna
- Scansione delle configurazioni Claude Code globali e a livello di progetto
- Indicatori visivi di scope: verde per risorse globali, giallo per risorse di progetto
- Filtro in tempo reale e auto-refresh (intervallo 3s) in modalità TUI
- Parser YAML frontmatter minimale senza dipendenze YAML esterne
- Cross-platform: Linux, macOS, Windows
- Si integra come slash command `/tools` nelle sessioni Claude Code

## Installazione

Richiede Python 3.10+ e uno tra: pipx, uv o pip.

```bash
# Clona il repository
git clone https://github.com/AndreaBonn/claude-code-available-tools.git
cd claude-code-available-tools

# Esegui l'installer universale (rileva automaticamente il sistema operativo)
./install.sh

# Oppure usa gli installer specifici per piattaforma
./installers/install_linux.sh       # Linux
./installers/install_macos.sh       # macOS
.\install.bat                       # Windows
```

L'installer esegue quattro operazioni:

1. Verifica la presenza di Python 3.10+
2. Installa il pacchetto `cctools` (tramite pipx, uv o pip)
3. Copia lo slash command `/tools` in `~/.claude/commands/tools.md`
4. Esegue un test di verifica

Installazione manuale:

```bash
pip install .
# oppure
pipx install .
# oppure
uv tool install .
```

### Supporto piattaforme

| OS | TUI | Inline | External | Installer |
|----|-----|--------|----------|-----------|
| Linux | Sì | Sì | gnome-terminal, konsole, xfce4-terminal, xterm | `install_linux.sh` |
| macOS | Sì | Sì | Terminal.app via osascript | `install_macos.sh` |
| Windows | Sì | Sì | Non disponibile | `install_windows.ps1` |

## Utilizzo

```bash
# Modalità automatica (TUI se terminale >= 80 colonne, altrimenti inline)
cctools

# Modalità esplicite
cctools --mode tui
cctools --mode inline
cctools --mode external

# Filtra risorse per nome o descrizione
cctools --mode inline --filter mcp
```

Dall'interno di una sessione Claude Code:

```
/tools                  # Apre la TUI in un terminale esterno
/tools inline           # Stampa il report nella chat
/tools tui              # Apre la TUI nel terminale corrente
/tools inline mcp       # Report inline filtrato
```

### Scorciatoie da tastiera TUI

| Tasto | Azione |
|-------|--------|
| `/` | Apre la barra di filtro |
| `Escape` | Chiude il filtro, cancella il testo |
| `r` | Refresh manuale |
| `q` | Esci |

## Configurazione

`cctools` legge i file di configurazione Claude Code esistenti. Non è richiesta configurazione aggiuntiva.

L'unica variabile d'ambiente opzionale è `CLAUDE_CONFIG_DIR`, che sovrascrive la directory di configurazione predefinita `~/.claude/`. Lo scanner rileva anche le variabili `CLAUDE_*` e `ANTHROPIC_*` dall'ambiente shell.

### Descrizioni custom per gli hook

Gli hook di Claude Code non includono nativamente una descrizione leggibile. È possibile aggiungere un campo opzionale `description` a qualsiasi definizione di hook, e `cctools` lo utilizzerà come testo di visualizzazione al posto del comando grezzo:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "./scripts/validate.sh",
        "description": "Valida l'input prima dell'esecuzione Bash"
      }]
    }]
  }
}
```

Senza `description`, cctools mostra `[command] ./scripts/validate.sh`. Con il campo presente, viene visualizzato il testo leggibile.

## Test

```bash
uv sync --dev
uv run pytest tests/ -v --cov=cctools
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Contribuire

I contributi sono benvenuti tramite pull request. Prima di inviare:

1. Esegui i test e verifica che passino
2. Esegui `ruff check` e `ruff format`
3. Esegui `mypy` per il type checking
4. Mantieni i commit focalizzati e descrittivi

## Sicurezza

Per segnalare vulnerabilità, consulta la [policy di sicurezza](SECURITY.it.md).

## Licenza

Rilasciato sotto la licenza Apache 2.0 -- vedi [LICENSE](LICENSE).

## Autore

Andrea Bonacci -- [@AndreaBonn](https://github.com/AndreaBonn)

---

Se questo progetto ti è utile, una stella su GitHub è apprezzata.
