[English](SECURITY.md) | **Italiano**

# Policy di Sicurezza

## Versioni supportate

| Versione | Supportata |
|----------|------------|
| 1.0.x    | Sì         |

## Segnalare una vulnerabilità

Per segnalare una vulnerabilità di sicurezza, usa GitHub Security Advisories:

[Segnala una vulnerabilità](https://github.com/AndreaBonn/claude-code-available-tools/security/advisories/new)

Non aprire una issue pubblica per segnalazioni di sicurezza.

### Cosa includere

- Descrizione della vulnerabilità
- Passi per riprodurla
- Versione/i interessate
- Valutazione dell'impatto (cosa potrebbe ottenere un attaccante)

### Tempi di risposta

- Conferma ricezione: entro 72 ore
- Fix critici: entro 30 giorni
- Disclosure pubblica coordinata dopo il rilascio del fix

## Misure di sicurezza implementate

Claude Code Available Tools by Bonn è un tool CLI locale che legge i file di configurazione Claude Code dal disco. Non espone servizi di rete, non gestisce autenticazione e non elabora input utente non fidato da fonti esterne.

Misure attuali:

- **Lockfile delle dipendenze**: `uv.lock` fissa tutte le dipendenze transitive a versioni esatte (`uv.lock`)
- **I/O su file sicuro**: tutte le letture da filesystem sono racchiuse in try/except con gestione errori esplicita, nessuna eccezione si propaga dallo scanner (`src/cctools/scanner.py:177-198`)
- **Nessuna superficie di shell injection**: il tool non passa stringhe fornite dall'utente a comandi shell; `subprocess.Popen` in `cli.py:80` usa argomenti in formato lista
- **No `eval`/`exec`/`pickle`**: nessuna esecuzione dinamica di codice sui contenuti dei file
- **Parsing JSON con type guard**: i dati JSON dai file di configurazione sono validati con controlli `isinstance` prima dell'uso (`src/cctools/scanner.py:186-198`)
- **Analisi statica**: linter ruff e type checker mypy configurati in `pyproject.toml`

## Best practice di sicurezza per gli utenti

- Mantieni Python e le dipendenze aggiornati
- Verifica il contenuto delle directory `~/.claude/` e `.claude/` di progetto, dato che cctools legge e visualizza il loro contenuto
- Se usi `CLAUDE_CONFIG_DIR` per indicare una directory di configurazione personalizzata, assicurati che abbia i permessi file appropriati

## Fuori ambito

I seguenti casi non sono considerati vulnerabilità in Claude Code Available Tools by Bonn:

- Visualizzazione di dati sensibili già presenti nei file di configurazione Claude Code (questa è la funzione prevista del tool)
- Escalation di privilegi locali che richiedono accesso preesistente all'account dell'utente
- Attacchi di social engineering
- Denial of service tramite file di configurazione eccessivamente grandi sul filesystem locale
- Vulnerabilità in dipendenze di terze parti già pubblicamente note (segnalale upstream)

## Riconoscimenti

I ricercatori di sicurezza che segnalano vulnerabilità valide saranno accreditati qui su richiesta.

---

[Torna al README](README.it.md)
