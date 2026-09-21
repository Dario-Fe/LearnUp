# AGENTS.md — guida per chi mantiene questa skill

Questo file è per gli agenti AI che lavoreranno sul progetto in sessioni future (e per gli umani che
vogliono capire le decisioni prese). Contiene: architettura, invarianti, stato attuale, ricette operative,
trappole note, registro delle decisioni e backlog.

**Prima di modificare qualsiasi cosa, leggi le sezioni 2 (verifica), 5 (invarianti) e 6 (convenzioni).**

> **Nota per gli agenti che *usano* la skill (non la mantengono).**
> Questo file riguarda lo sviluppo e la manutenzione del progetto. Se stai conducendo una sessione di
> studio con l'utente, **ignoralo**: segui `SKILL.md` e le reference in `references/`. Leggi questo file
> solo se ti viene chiesto di modificare, estendere, correggere o pubblicare la skill.

---

## 1. Cos'è il progetto in dieci righe

`insegnante-virtuale` è una **skill per agenti** (standard Agent Skills: `SKILL.md` + cartelle di supporto)
che costruisce un insegnante virtuale rigoroso e divulgativo. La skill **non contiene la conoscenza degli
argomenti**: contiene la cornice di regole, il protocollo di sessione e un motore Python (`scripts/iv.py`)
che gestisce un **registro di sotto-skill** generate al bisogno e salvate su disco. All'avvio la skill
chiede cosa si vuole studiare, cerca nel registro e **riusa** la sotto-skill se esiste, altrimenti la
**genera, la valida e la registra**. Lo stato dell'allievo (sessioni, voti, lacune, ripetizione spaziata)
è separato dalla conoscenza e non viene mai rigenerato.

Il repository **è** la skill: `SKILL.md` sta nella radice.

---

## 2. Verifica obbligatoria (definition of done)

Qualunque modifica va chiusa con questi tre comandi, dalla radice del repository:

```bash
python -m unittest discover -s tests -t tests    # deve dire OK (39 test al 2026-09-21)
python scripts/iv.py validate --all              # nessuna sotto-skill rotta
python scripts/iv.py status                      # nessuna bozza pendente, nessun da_rigenerare inatteso
```

Se tocchi la cornice (`references/`), verifica anche il ciclo completo su un argomento di prova:

```bash
python scripts/iv.py find "argomento di prova" --json      # atteso: status none → genera_nuova
python scripts/iv.py create --title "Argomento di prova"   # crea lo scheletro
python scripts/iv.py validate argomento-di-prova           # atteso: exit 1 (bozza non compilata)
```

Se tocchi l'esportazione o i dati, verifica con un dataset vero:

```bash
python scripts/iv.py list --json
python scripts/iv.py stats --json
```

Non dichiarare completata una modifica al motore senza aver eseguito i test: `iv.py` è la parte che rompe
silenziosamente la persistenza dei progressi.

### Smoke test della skill (da fare a mano, prima di una release)

Da condurre in una **chat nuova** (il routing per descrizione avviene all'avvio della sessione) e osservando
che l'agente esegua davvero i comandi, non che risponda a memoria.

| # | Cosa dire all'agente | Esito atteso |
|---|---|---|
| 1 | *"Voglio studiare il metodo Feynman"* | `find` → `exact`, riuso della sotto-skill esistente, aggancio dal Modulo 1 senza rigenerare nulla |
| 2 | *"Voglio studiare il teorema di Bayes"* | `find` → `none`, `create`, compilazione, `validate` verde, `register`, inizio della lezione |
| 3 | *"Riprendiamo il metodo Feynman"* | `show` + ripresa dal progresso salvato ("riprendiamo da…"), non dall'inizio |
| 4 | *"Ripassiamo"* | `due` con i concetti in scadenza e 5 minuti di recupero attivo prima di contenuti nuovi |
| 5 | *"Com'è andato il mio studio?"* | `stats` con diario, lacune ricorrenti e argomenti che stanno raffreddando |
| 6 | Fine di una sessione qualsiasi | `log` eseguito e prossima data di ripasso comunicata all'utente |
| 7 | Dopo il test: `python scripts/iv.py status` | nessuna bozza pendente; `da_rigenerare` vuoto; `ripassi_oggi` coerente con i voti dati |

Per provare il percorso **come lo vivrebbe chi installa la skill da GitHub** (senza la junction locale),
copia il repository in una cartella temporanea, mettilo in `prova/.agents/skills/insegnante-virtuale/`
e apri lì una sessione: deve funzionare senza alcuna configurazione, e il primo comando deve ricostruire
`registry.json` dai `meta.json` presenti.

---

## 3. Mappa architetturale

| Percorso | Ruolo | Chi lo legge/scrive |
|---|---|---|
| `SKILL.md` | Orchestrazione: avvio obbligatorio, albero delle decisioni, generazione, insegnamento, chiusura, regole dure | L'agente all'avvio della skill |
| `references/costituzione.md` | **Invarianti pedagogiche**: rigore etichettato, chiarezza, esempi concreti, disponibilità non compiacente, verifica, carico cognitivo, prerequisiti, autonomia, persistenza | L'agente prima di insegnare |
| `references/protocollo-sessione.md` | Flusso operativo in 3 fasi (avvio, generazione, insegnamento, chiusura) con i comandi esatti | L'agente durante la sessione |
| `references/contratto-output.md` | Forma della lezione: 4 livelli, struttura a blocchi, etichette, divieti di forma | L'agente quando scrive |
| `references/modalita.md` | Autodidatta / esame / docenza e cosa cambia | L'agente all'avvio e al cambio modalità |
| `references/schema-sottoskill.md` | Specifica dei file di una sotto-skill, minimi di qualità, checklist, esempio buono/cattivo | L'agente quando genera |
| `scripts/iv.py` | **Motore**: registro, ricerca, creazione, validazione, alias/merge, progressi, SM-2, diario | L'agente, l'utente, i test |
| `assets/templates/topic/` | Scheletro di sotto-skill con placeholder `{{...}}` e commenti `ISTRUZIONI:` | `iv.py create` |
| `tests/test_iv.py` | 39 test del motore (caricamento via `importlib`, data dir temporanea) | Chi modifica `iv.py` |
| `data/topics/<slug>/` | **Le sotto-skill salvate** (8 file) | Generati dall'agente, letti dall'agente |
| `data/registry.json` | Indice: slug, titolo, chiave canonica, alias, stato, `base_version`, hash, revisione | `iv.py` (rigenerabile da disco) |
| `data/progress/<learner>/` | Stato allievo: sessioni, concetti (SM-2), lacune, log, `DIARIO.md` | `iv.py log/stats` |

### Funzioni chiave di `iv.py`

| Funzione | Responsabilità | Attenzione |
|---|---|---|
| `norm` / `tokens` / `stems` / `key_of` / `slugify` | Normalizzazione del linguaggio (accenti, stopword, steli) | Cambiarle altera **tutto** il matching storico: i registri esistenti possono non risolvere più |
| `similarity` | Punteggio 0..1 (Jaccard pesato sulla contenenza) | Le soglie `T_EXACT=0.93`, `T_VARIANT=0.68`, `T_CANDIDATE=0.42` decidono riuso vs nuova sotto-skill |
| `lookup` | Ricerca ibrida: alias → chiave → slug → similarità; restituisce `status` e `azione` | È il cuore della promessa "controlla se esiste già" |
| `sync_from_disk` | Aggiunge al registro i topic presenti su disco ma assenti dall'indice | Rende innocuo il fatto che `registry.json` sia in `.gitignore` |
| `cmd_create` | Copia il template, sostituisce i placeholder, scrive `meta.json`, inserisce la voce in stato `draft` | Rifiuta titoli che corrispondono a un argomento esistente |
| `validate_topic` | Tutti i controlli sullo schema e sui minimi | **Non verifica la verità dei contenuti**: vedi §10 |
| `cmd_register` | Attiva la sotto-skill: hash del contenuto, `base_version`, revisione, `quality.validated` | Rifiuta di attivare se la validazione fallisce (senza `--force`) |
| `sm2` | Ripetizione spaziata semplificata (intervalli 1 → 6 → round(intervallo × ease)) | Un elemento per concetto, non card multiple |
| `cmd_log` | Registra sessione, voti, lacune; aggiorna il piano di ripasso | `--concept` e `--grade` devono avere la stessa lunghezza |
| `cmd_stats` | Diario in Markdown (minuti, voto medio, lacune ricorrenti, argomenti raffreddati, suggerimenti) | Con `--write` produce `data/progress/<learner>/DIARIO.md` |
| `build_parser` / `main` | CLI argparse di 12 sottocomandi + `--data` / `--skill-dir` | `_utf8_stdout()` è necessario su Windows (console cp1252) |

---

## 4. Stato attuale (2026-09-21)

- **Versione della cornice**: `BASE_VERSION = "1.0.0"` in `scripts/iv.py`. Cambiarla è il meccanismo che
  segnala le sotto-skill da rigenerare (`iv.py status` → `da_rigenerare`).
- **Test**: 39, tutti verdi (`unittest`, nessuna dipendenza).
- **Sotto-skill presenti**: `data/topics/metodo-feynman/` (esempio di riferimento completo, validato,
  hash `20e669fba114`, revisione 1) e `data/topics/basi-di-machine-learning/` (creata il 2026-09-21 da
  **opencode**, non da Codebuff: è la prova di agnosticismo fra agenti, vedi §4.1). Entrambe modalità
  `autodidatta`, livello iniziale 1, prerequisiti nessuno, `validate --all` OK.
- **Progressi**: `data/progress/default/` contiene un ciclo completo su `basi-di-machine-learning`
  (9 sessioni, 140 minuti, 9 concetti in SM-2, `DIARIO.md` generato) prodotto dal test con opencode.
  Sono dati di prova, non versionati: cancellabili senza conseguenze.
- **Repository**: radice = skill; `README.md` (inglese) + `README.it.md` (italiano) + `LICENSE` MIT +
  `.gitignore` che esclude dati personali e indice. Non ancora inizializzato come repo git.
- **Installazione locale**: `.agents/skills/insegnante-virtuale` è una **junction** verso la radice
  (creata con PowerShell; `mklink` da Git Bash fallisce per l'escape dei percorsi). Serve solo al discovery
  da parte dell'agente: è in `.gitignore` e non fa parte della pubblicazione.
- **Cosa non è ancora stato fatto**: nessuna esportazione (`export`), nessuna interfaccia web,
  ricerca solo lessicale, cornice non internazionalizzata.

### 4.1 Compatibilità fra agenti (verificata il 2026-09-21)

Il sistema è stato usato per intero da **opencode** (agente diverso da quello di sviluppo) su un argomento
nuovo, "basi di machine learning", senza alcuna modifica alla skill. Esito: ciclo completo riuscito
(`find` → `create` → contenuti → `validate` → `register` → 9 `log` → `stats`/`DIARIO.md`), indice coerente,
nessun file estraneo lasciato nel repository.

Cosa questo dimostra e cosa no:

- **Funziona** perché tutta la logica sta in `SKILL.md` + `references/` + `iv.py`: nessuna istruzione
  dipende da un client specifico, e ogni comando ha output JSON stabile.
- **Tollerato**: campi extra nei `meta.json` sono ammessi (l'agente può aggiungerne), e `register` scrive
  il blocco `quality` da sé. Non aggiungere validazioni che rifiutino campi sconosciuti: romperebbero
  il funzionamento con agenti diversi.
- **Da sapere**: gli agenti dimenticano gli argomenti opzionali (`--mode`, `--level`). Per questo `iv.py
  log` eredita il livello dal `meta.json` quando non glielo si passa. Se aggiungi opzioni utili, prevedi
  un default sensato invece di un campo vuoto.
- **Non verificato** con altri client (Claude Code, Codex, Cursor): il presupposto comune è solo che il
  client sappia caricare una skill per `description` e eseguire comandi shell.

---

## 5. Invarianti da non rompere

1. **Il riuso viene prima della generazione.** Ogni sessione deve passare da `iv.py find` prima di creare
   qualcosa. Non introdurre scorciatoie che generino sotto-skill senza lookup.
2. **I progressi dell'allievo non si toccano mai.** `data/progress/` è separato da `data/topics/`:
   rigenerare una sotto-skill non deve mai riscrivere sessioni, voti o scadenze.
3. **Una sotto-skill `draft` non si usa.** `validate` + `register` sono il cancello di qualità.
4. **La validazione è un gate, non un consiglio.** Se aggiungi regole, aggiungile come errore bloccante
   (o come avviso solo se non incidono sulla qualità didattica).
5. **Le sotto-skill restano annidate** in `data/topics/`: non trasformarle in skill di primo livello
   (inquinerebbero il routing dell'agente con decine di descrizioni concorrenti).
6. **Le reference non contraddicono la costituzione.** In caso di conflitto vince `costituzione.md`;
   se cambi una regola, aggiorna entrambe e incrementa `BASE_VERSION`.
7. **Nessuna dipendenza esterna.** Solo libreria standard Python: il progetto deve girare con un
   `git clone` e Python installato, niente pip, niente venv.
8. **Nessun dato personale nel repository.** `data/progress/`, `data/_merged/`, `data/registry.json`
   restano fuori dal versionamento.
9. **Il motore non parla italiano "da terminale" e basta**: ogni comando deve avere output JSON stabile
   (`--json` dove esiste) perché è così che l'agente lo consuma.
10. **Rigore dichiarato, mai fonti inventate.** Vale per i contenuti generati e per la documentazione:
    se un'informazione non è verificata, va etichettata come tale (vedi `references/costituzione.md`).

---

## 6. Convenzioni

- **Lingua**: contenuti, documentazione, commenti e messaggi della CLI in **italiano** (il pubblico del
  progetto è italiano). `README.md` è in inglese come vetrina, `README.it.md` è la versione completa.
  Se aggiungi una funzione, aggiorna **entrambi** i README e la sezione Roadmap di pari passo.
- **Codice**: Python, solo standard library, type hints leggeri, docstring in italiano. Le funzioni del
  motore si chiamano `cmd_<verbo>` e delegano a funzioni pure testabili (`lookup`, `validate_topic`, `sm2`).
- **Slug**: minuscolo, accenti rimossi, spazi in `-` (`slugify`). **Chiave canonica**: parole di contenuto
  ordinate (`key_of`). Non cambiare la formula senza una migrazione.
- **Date e orari**: ISO 8601 (`YYYY-MM-DD`), salvati come stringhe nelle stesse forme attuali.
- **File di dati**: JSON indentato 2, `ensure_ascii=False`, sempre con newline finale.
- **Idempotenza**: i comandi di sola lettura non scrivono **contenuti** né progressi. L'unica scrittura
  ammessa è `data/registry.json`, e solo per allinearsi ai `meta.json` (creazione se assente, più i topic
  o gli alias mancanti). Se il registro è già allineato, il file non viene toccato: c'è un test che lo
  verifica confrontando l'`mtime`.
- **Compatibilità Windows**: aprire file con `encoding="utf-8"` esplicito e non rimuovere `_utf8_stdout()`.
- **Messaggi CLI**: campi JSON in italiano (`ok`, `azione`, `prossimi_passi`), perché l'agente li interpreta
  direttamente.

---

## 7. Ricette operative

### 7.1 Aggiungere o modificare una regola pedagogica (nuova versione della cornice)

1. Modifica `references/costituzione.md` (e/o `contratto-output.md`, `protocollo-sessione.md`).
2. Incrementa `BASE_VERSION` in `scripts/iv.py` (semantica: major = regole che invalidano i contenuti,
   minor = aggiunte compatibili).
3. Aggiorna `references/schema-sottoskill.md` se la regola tocca la struttura dei file.
4. `python scripts/iv.py status` → i topic vecchi devono comparire in `da_rigenerare`.
5. Verifica il ciclo: §2.
6. Aggiorna la Roadmap solo se cambia il perimetro del prodotto.

### 7.2 Aggiungere una modalità

1. Sezione in `references/modalita.md` (scopo, ritmo, cosa cambia in `verifica.md`, chiusura).
2. Aggiungi la stringa alla tupla `MODES` in `scripts/iv.py` (usata da `create --mode` e da `validate`).
3. Riga nella tabella "Come cambiano le sotto-skill per modalità".
4. Test: aggiungi un caso in `TestValidazione` che verifichi il rifiuto di una modalità sconosciuta.

### 7.3 Aggiungere un file a una sotto-skill (es. `flashcard.md`)

1. Crea il template in `assets/templates/topic/` (con `{{TITLE}}` dove serve e commenti `ISTRUZIONI:`).
2. Aggiungi il nome a `REQUIRED_FILES` in `iv.py` e, se serve, un controllo in `validate_topic`.
3. Aggiorna `references/schema-sottoskill.md` (tabella requisiti + qualità) e `SKILL.md` (elenco file).
4. I topic esistenti diventeranno non validi: è voluto; vanno completati con `validate` e `register`.
5. Aggiungi un test che verifichi l'errore quando il file manca.

### 7.4 Aggiungere un comando CLI

1. `cmd_<verbo>(args)` in `iv.py`, con output via `emit(...)` (JSON + eventuale `as_text` leggibile).
2. Sottoparser in `build_parser()` con `--json` e `--learner` se ha senso.
3. Documenta il comando in **tre** punti: `SKILL.md` (manutenzione rapida), `README.md`, `README.it.md`.
4. Test in `TestCLI` o nella classe tematica pertinente, usando la data dir temporanea di `setUp`.

### 7.5 Aggiungere un controllo di validazione

1. In `validate_topic()` usa `err()` per bloccare, `warn()` per avvisare.
2. Soglie e minimi vanno **allineati** in `references/schema-sottoskill.md`: la documentazione e il codice
   devono dire la stessa cosa.
3. Test positivo (sotto-skill conforme) e negativo (sotto-skill rotta) in `TestValidazione`.
4. Il riempimento di riferimento per i test è `fill_topic()` in `tests/test_iv.py`: aggiornalo insieme.

### 7.6 Creare un nuovo argomento (procedura che deve seguire l'agente)

1. `python scripts/iv.py find "<argomento>"` — mai saltare.
2. `create --title … --level N --mode … [--prereq …]`.
3. Compila in quest'ordine: `percorso.md` → `errori-tipici.md` → `glossario.md` → `esercizi.md` →
   `verifica.md` → `fonti.md` → `SKILL.md`.
4. `validate` finché non è verde, poi `register --self-check "…"`.
5. Registra la sessione con `log` a fine incontro.

Un argomento di esempio nuovo, se aggiunto al repository, deve passare il validatore: gli esempi incompleti
non entrano.

### 7.7 Rigenerare un argomento (cornice cambiata)

1. `python scripts/iv.py status` → elenco `da_rigenerare`.
2. Rileggi `costituzione.md` e `contratto-output.md`.
3. Correggi i file della sotto-skill dove contraddicono la cornice (spesso: etichette di affidabilità,
   struttura dei moduli, criteri di autovalutazione).
4. `validate` → `register --self-check "riallineata alla cornice vX"`.
5. **Non toccare `data/progress/`.**

---

## 8. Test

```bash
python -m unittest discover -s tests -t tests
```

Copertura attuale (39 test): normalizzazione e similarità, ciclo di riuso (`none`/`exact`/`variant`/
`draft_incompleto`), rifiuto dei duplicati, alias, merge con migrazione dei progressi, reindex,
validazione (bozza vs completo, `--all`, cornice vecchia → `da_rigenerare`), SM-2 (intervalli crescenti,
azzeramento dopo voto basso), log, `due`, profili allievo separati, `show`, `stats --write`, CLI esterna
via `subprocess` (JSON e codice di uscita).

Convenzioni dei test: nessun test tocca `data/` reale — `setUp` chiama `iv.set_data_dir(tempdir)`.
I comandi si eseguono con l'helper `run([...])`, che cattura stdout e codice di uscita. I contenuti di
riempimento stanno nelle costanti `VALID_*` in cima al file.

---

## 9. Trappole note

- **Windows e console cp1252**: senza `_utf8_stdout()` gli accenti rompono l'output. Non rimuoverla.
- **Junction e ricorsione**: `.agents/skills/insegnante-virtuale` punta alla radice del repository.
  `find`/`rg` non seguono i link per default, quindi non c'è ricorsione, ma **non aggiungere tool che
  percorrono gli alberi seguendo i symlink**.
- **`registry.json` è in `.gitignore`**: chi clona non lo trova. Va bene, perché `sync_from_disk()` lo
  ricostruisce dai `meta.json` **e lo salva** al primo comando. Verificato su una copia pulita del repo.
  Attenzione alla trappola storica: se il salvataggio lo togli, il file resta vuoto su disco (l'indice
  funziona in memoria ma mente a chi lo legge) finché non si esegue un comando che scrive. Se aggiungi
  campi al registro, assicurati che siano derivabili da `meta.json` (`REGISTRY_ENTRY_FIELDS`).
- **Il registro deve restare derivabile**: alias e unioni vanno scritti in `meta.json` (o la cartella va
  spostata, come fa `merge` in `data/_merged/`), altrimenti su un clone riappaiono duplicati. Verificato:
  dopo `alias` + `merge`, cancellando `registry.json` l'indice ricostruito è identico.
- **Il validatore non verifica la verità**: garantisce struttura e minimi. La qualità sostanziale è
  responsabilità dell'agente che genera, e si difende con le etichette di affidabilità e la sezione
  *Da verificare* in `fonti.md`.
- **Placeholder e `ISTRUZIONI:`**: il validatore li cerca come stringhe. Se cambi la sintassi dei template,
  aggiorna `PLACEHOLDERS` in `iv.py`.
- **`già`/`più` → `gia`/`piu`**: la normalizzazione rimuove gli accenti, quindi le stopword vanno scritte
  senza accenti in `STOPWORDS`.
- **Cambiare `tokens`/`stems` è una modifica di compatibilità**: può far smettere di risolvere alias
  registrati con la vecchia formula. Se succede, `iv.py reindex` non basta: serve un `alias --add`.
- **Il demo `metodo-feynman`** è il test di qualità a occhio: se il validatore passa ma il contenuto sembra
  fiacco, il problema sono le soglie minime, non l'esempio.

---

## 10. Registro delle decisioni (2026-09-21)

| # | Decisione | Motivazione |
|---|---|---|
| 1 | Quattro strati separati (cornice / sotto-skill / stato allievo / orchestrazione) | Hanno cicli di vita diversi: la conoscenza è rigenerabile, i progressi no |
| 2 | Dati dentro la skill (`data/`), non accanto al progetto | Autocontenimento e portabilità; `--data`/`IV_DATA` coprono il caso di installazione in sola lettura |
| 3 | Sotto-skill annidate, non skill di primo livello | Evita di inquinare il routing dell'agente con decine di descrizioni concorrenti; si caricano per percorso (progressive disclosure) |
| 4 | Matching ibrido: script deterministico + conferma dell'LLM | Il dedup puramente semantico degenera dopo molte decine di argomenti; quello puramente esatto non riconosce le varianti |
| 5 | Chiavi canoniche con stopword rimosse, steli e alias | "Roma antica" / "Impero romano" convergono senza duplicare; gli steli gestiscono singolare/plurale senza lemmatizzatore |
| 6 | `registry.json` derivabile da disco e non versionato | Elimina conflitti di merge e rende innocuo il primo comando su un clone pulito |
| 7 | Validazione bloccante prima dell'attivazione | Una sotto-skill incompleta è peggio di nessuna sotto-skill: l'agente la userebbe comunque |
| 8 | `BASE_VERSION` come meccanismo di rigenerazione | Permette di far evolvere le regole senza riscrivere a mano decine di argomenti |
| 9 | Progressi in file separati per allievo | Serve alla modalità docenza e protegge i dati da rigenerazioni |
| 10 | SM-2 semplificato, un elemento per concetto | Costo di implementazione minimo con beneficio reale; l'export Anki (v0.2) coprirà i casi avanzati |
| 11 | Rigore tramite etichette dichiarate invece di toni cautelativi | Mantiene lo stile divulgativo senza sacrificare l'onestà epistemica |
| 12 | Solo libreria standard Python | Installazione a costo zero: `git clone` e via, nessun ambiente virtuale |
| 13 | Repository = skill (radice con `SKILL.md`) | Standard per un repo mono-skill e compatibile con `npx skills add` |
| 14 | README bilingue, contenuti della skill in italiano | Vetrina internazionale su GitHub, pubblico reale italiano |
| 15 | Licenza MIT | Permissiva, standard di fatto per le skill |
| 16 | Installazione locale via junction | Mantiene una sola copia dei sorgenti (niente drift) pur restando scopribile dall'agente |
| 17 | `sync_from_disk` salva l'indice ricostruito, invece di ricostruirlo solo in memoria | Su un clone l'indice deve essere vero anche su disco; un file derivato vuoto è peggio di un file assente. Le scritture avvengono solo se il registro differisce dai `meta.json` |
| 18 | `iv.py log` eredita `--level` dal `meta.json` invece di lasciare `null` | Gli agenti omettono gli opzionali; un campo vuoto nei progressi costringe l'agente successivo a reinterpretare il metadato |
| 19 | Il repository si chiama `LearnUp`, la skill `insegnante-virtuale` | Nomi con destinatari diversi: il repository è il progetto da leggere su GitHub, la skill è il contratto con l'agente. Rinomare la skill invaliderebbe `npx skills add` e il caricamento per nome |

---

## 11. Backlog tecnico prioritizzato

### v0.2 — Esportazione (prossimo passo consigliato)

- [ ] `iv.py export --format md|json|csv|html --topic <slug> --learner <name> --output <file>`
      - **md**: report leggibile (sessione / argomento / periodo);
      - **json**: dump stabile e versionato dello schema (`schema_version` nel payload);
      - **csv**: formato Anki a 5 colonne (`front`, `back`, `tags`, `due`, `ease`), con **ID stabili**
        derivati da `key_of(concetto)` per non perdere lo storico dei ripassi al reimport;
      - **html**: pagina statica autonoma (nessuna dipendenza esterna) con diario, argomenti, ripassi.
      - *Criterio di accettazione*: esportazione di `metodo-feynman` con un log di prova produce file
        validi; test in `TestEsportazione`; comando documentato in `SKILL.md` + entrambi i README.
- [ ] `iv.py backup --out <archivio.zip>` e `--restore`, con esclusione di `__pycache__`.
      - *Criterio*: round-trip (backup → restore in data dir temporanea) verificato da un test.
- [ ] `--format pdf` con Pandoc se presente, fallback a Markdown con avviso.
- [ ] "Pagella" per argomento: livello raggiunto, lacune aperte, tempo investito, prossimi passi.

### v0.3 — Interfaccia web

- [ ] Fase 1: dashboard statica generata da `export --format html` (compatibile GitHub Pages).
- [ ] Fase 2: app locale (FastAPI + HTMX, oppure solo `http.server` per l'MVP) con quattro viste:
      sessione guidata, ripasso flashcard (aggiorna SM-2 con i pulsanti di voto), editor di sotto-skill con
      validazione live, diario con grafici.
      - *Vincoli*: local-first, nessun account, nessuna dipendenza frontend con build step;
      - *Criterio*: studiare un modulo e registrare un voto senza aprire il terminale.

### v0.4 — Argomenti più intelligenti

- [ ] Ricerca semantica opzionale (embedding locali) come secondo livello dopo quella lessicale, con
      fallback silenzioso se le dipendenze non ci sono (attenzione all'invariante "nessuna dipendenza":
      va proposto come extra opzionale, non obbligatorio).
- [ ] Import del programma d'esame da PDF/elenco capitoli → proposta di piano dei moduli con revisione umana.
- [ ] Proposta automatica di sotto-skill di prerequisito a partire dai campi *Serve prima* dei moduli.
- [ ] Analisi delle lacune trasversali fra argomenti diversi.

### v0.5 — Integrazioni

- [ ] Server MCP che espone i comandi principali come tool.
- [ ] Promemoria di ripasso via email/calendario (`.ics`).
- [ ] RAG sui materiali dell'utente come fonte preferita.
- [ ] GitHub Action `iv.py validate --all` sulle pull request.
- [ ] Import/export di singole sotto-skill fra utenti, con merge dei progressi locali.

### Debito tecnico noto

- [ ] `references/` è solo in italiano: valutare una cartella `references/en/` quando ci sarà pubblico non italiano.
- [ ] `validate_topic` non controlla la coerenza fra `meta.json` e il contenuto (es. livello dichiarato vs
      registro linguistico dei moduli): valutare un avviso euristico.
- [ ] Nessuna migrazione automatica del registro quando cambia la formula delle chiavi canoniche.

---

## 12. Pubblicazione

Repository pubblico: **https://github.com/Dario-Fe/LearnUp** (branch `main`, remote `origin`).
Attenzione ai due nomi diversi: il **repository** si chiama `LearnUp`, la **skill** `insegnante-virtuale`
(è quello che l'agente carica ed è quello che `--skill` si aspetta). Non "correggere" il nome della
skill per allinearlo al repository: romperebbe le installazioni esistenti e il caricamento per nome.

Versionare: `SKILL.md`, `README.md`, `README.it.md`, `AGENTS.md`, `LICENSE`, `.gitignore`, `references/`,
`scripts/`, `assets/`, `tests/`, `data/topics/` (esempio di riferimento).

Non versionare: `data/progress/`, `data/_merged/`, `data/registry.json`, `.agents/`, `__pycache__/`
(già in `.gitignore`).

```bash
git init && git add . && git status      # verificare che non compaia nulla di personale
git commit -m "Insegnante Virtuale: skill di studio rigenerante"
git branch -M main
git remote add origin https://github.com/Dario-Fe/LearnUp.git      # remoto di riferimento (già esistente)
git push -u origin main
# per un fork: gh repo create <utente>/LearnUp --public --source=. --push
```

Repository pubblico: **https://github.com/Dario-Fe/LearnUp**. Il nome del repository (`LearnUp`) e
quello della skill (`insegnante-virtuale`) sono deliberatamente diversi: la skill si chiama così perché
è quello che l'agente carica, il repository perché è il progetto. Verificare che
`npx skills add Dario-Fe/LearnUp --list` trovi la skill `insegnante-virtuale`.

Prima di pubblicare un fork: sostituire il titolare del copyright in `LICENSE` (già impostato a
`Dario-Fe` nel repository di riferimento).

---

## 13. Cosa NON fare

- Non committare `data/progress/` o `data/registry.json`: contengono dati personali e indice rigenerabile.
- Non usare una sotto-skill in stato `draft`, e non disattivare la validazione per "fare prima".
- Non toccare i progressi durante una rigenerazione.
- Non aggiungere dipendenze Python obbligatorie.
- Non trasformare le sotto-skill in skill di primo livello.
- Non far divergere `validate_topic()` da `references/schema-sottoskill.md`.
- Non aggiornare un solo README: `README.md` e `README.it.md` vanno tenuti allineati, insieme alla Roadmap.
- Non inventare fonti, citazioni o numeri in nessun contenuto, documentazione inclusa.
