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
python -m unittest discover -s tests -t tests    # deve dire OK (175 test al 2026-09-22)
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
| 8 | Chiedi una spiegazione lunga e poi: `python scripts/iv.py style <slug>` | tutti i file entro l'obiettivo di leggibilità del livello (`percorso.md` per primo) |
| 9 | `python scripts/iv.py learner list` | un solo profilo per persona (o gli alias dichiarati): nessun progresso orfano |
| 10 | *"Studiamo X anche per Marco Rossi"* | il profilo `Marco Rossi` nasce al primo `log`, con diario proprio, e la sotto-skill **non** viene rigenerata |
| 11 | *"Ho scritto male il cognome di Marco, correggilo"* | `learner rename`: il profilo si sposta, resta un alias, nessuna sessione persa |
| 12 | *"Cancella il profilo di Marco"* | mostra l'anteprima (sessioni, minuti, cosa verrebbe perso) e attende conferma: senza `--yes` non cancella |

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
| `references/contratto-output.md` | Forma della lezione: 4 livelli, **registro** (standard/scolastico/bambino), esempio nella lingua del corso, temi delicati, struttura a blocchi, etichette, divieti di forma | L'agente quando scrive e prima di consegnare un modulo |
| `references/modalita.md` | Autodidatta / esame / docenza e cosa cambia | L'agente all'avvio e al cambio modalità |
| `references/schema-sottoskill.md` | Specifica dei file di una sotto-skill, minimi di qualità, checklist, esempio buono/cattivo | L'agente quando genera |
| `scripts/iv.py` | **Motore**: registro, ricerca, creazione, validazione, alias/merge, progressi, SM-2, diario | L'agente, l'utente, i test |
| `assets/templates/topic/` | Scheletro di sotto-skill con placeholder `{{...}}` e commenti `ISTRUZIONI:` | `iv.py create` |
| `assets/templates/lezione/` | Scheletro della lezione per il docente (sezioni che il motore verifica) | `iv.py lezione` |
| `tests/test_iv.py` | 85 test del motore (caricamento via `importlib`, data dir temporanea) | Chi modifica `iv.py` |
| `data/topics/<slug>/` | **Le sotto-skill salvate** (8 file) | Generati dall'agente, letti dall'agente |
| `data/materiali/<slug>/` | **Materiali dell'utente** (appunti, programma, prove passate) + `materiali.json` + `INDICE.md` derivato + le trascrizioni `<nome>.estratto.md` | `iv.py materiali`, e le letture dell'agente |
| `data/lezioni/<slug>/` | **Lezioni per una classe**: artefatti del docente, non conoscenza condivisa | `iv.py lezione` crea e verifica |
| `data/registry.json` | Indice: slug, titolo, chiave canonica, alias, stato, `base_version`, hash, revisione | `iv.py` (rigenerabile da disco) |
| `data/progress/<learner>/` | Stato allievo: sessioni, concetti (SM-2), lacune, log, `DIARIO.md`, e `_persona.json` (persona dichiarata: banda d'età, tempi, scadenza) | `iv.py log/stats` e `iv.py learner persona` |

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
| `cmd_log` | Registra sessione, voti, lacune; aggiorna il piano di ripasso e riscrive il diario | `--concept` e `--grade` devono avere la stessa lunghezza; `session_marker()` rifiuta le etichette di sessione |
| `session_marker` | Riconosce «fine sessione», «avvio percorso» e simili come non-concetti | Non allargarlo troppo: «il modulo 3: somma pesata» è un concetto valido (c'è un test) |
| `learner_dir` / `other_profiles` | Risolvono il profilo allievo (alias, maiuscole/spazi) e dichiarano i profili con progressi | Confronto case-insensitive: non usare `PROGRESS_DIR / learner` direttamente |
| `topic_files` | I file di progresso di un profilo: esclude `_persona.json`, che non è un argomento | Unico punto di verità: usarlo al posto di `glob("*.json")` su una cartella profilo. Senza, la persona viene contata come argomento e `merge` la unisce come una storia di studio |
| `read_persona` / `write_persona` | Leggono e scrivono la persona dichiarata del profilo (`_persona.json`) | La banda d'età è **dichiarata e non verificata**: è un input per proporre livello e registro, mai un fatto accertato. I campi sconosciuti si conservano (gli agenti possono aggiungerne) |
| `registro_effettivo` / `livello_suggerito` | Precedenza del tono (sessione > persona > banda d'età > `standard`) e livello da cui partire per un argomento nuovo | Il **livello** resta una proprietà dell'argomento, il registro una proprietà di chi parla: non scrivere il registro nei `meta.json` o si rompe il riuso |
| `clean_profile_name` | Valida il nome del profilo: spazi e accenti sì, separatori di percorso e metacaratteri no | Senza il controllo, `--learner ../x` scrive fuori da `data/progress/` |
| `build_diary` / `write_diary` | Compongono e salvano il diario; li usano `stats` e `log` | Il diario è derivato: non aggiungere stato che vive solo lì |
| `cmd_stats` | Diario in Markdown (minuti, voto medio, lacune ricorrenti, argomenti raffreddati, suggerimenti) | Con `--write` produce `data/progress/<learner>/DIARIO.md` |
| `ProseLint` | Avvisi di scrittura: caratteri non latini, righe duplicate o troncate, markdown rotto, forestierismi | Sono **avvisi**, mai errori: non deve bloccare il riuso di una sotto-skill utile |
| `frame_state` / `version_major` | Confrontano la cornice di un topic con `BASE_VERSION`: `da_rigenerare` (major) vs `aggiornabile` (minor) | Prima confrontava la stringa intera: qualunque ritocco marcava tutto come da rigenerare |
| `prova_dichiarata` / `giorni_alla_prova` | La prova dichiarata nella persona, normalizzata (`data`, `obiettivo`, `argomento`) | Una data illeggibile non deve diventare un piano inventato: `giorni_alla_prova` restituisce `None` |
| `piano_di_studio` / `passo_dalla_scadenza` | Stima se il materiale che resta ci sta con il budget dichiarato, e in `status` la mette davanti a tutto | È una **stima**, non una promessa: minuti per modulo dalle sessioni passate, e conta solo gli argomenti avviati (più quello della scadenza). Non presentarla come un piano garantito |
| `lezione_problemi` / `cmd_lezione` | L'artefatto del docente: creazione e verifica (sezioni, righe di scaletta, voci minime, leggibilità) | Verifica la forma, non la verità, come `validate_topic`. `--check` esce `1` su uno scheletro: non indebolirlo, è ciò che rende l'artefatto verificabile |
| `read_materiali` / `cmd_materiali` | Materiali dell'utente: li copia nei dati e ne rigenera l'indice (`INDICE.md`, con la sezione **Trascrizioni**: sorgente → copia, pagine, mezzo) | Sono la **fonte da privilegiare**, e non si versionano. Una voce il cui file non esiste più non sopravvive: l'indice non deve mentire |
| `collega_testo` / `testi_di` | Copia accanto al materiale la sua trascrizione in testo (`<origine>.estratto.md`) e la registra in `materiali.json` | Il motore **non estrae** il testo: l'estrazione resta all'agente (vista, OCR, copia). Qui si controllano i limiti: sotto `MIN_TESTO_CARATTERI` rifiuta, sopra `MAX_TESTO_CARATTERI` rifiuta senza `--force`. Il nome della copia viene dal **file di origine**, non dal materiale: due estratti dello stesso documento convivono, lo stesso nome è un aggiornamento (`sostituito`). Non tornare a derivarlo dal materiale: era la perdita silenziosa descritta in §9 |
| `comando_esiste` / `modulo_esiste` / `strumenti_disponibili` / `metodo_estrazione` / `cmd_strumenti` | Sonda sulla **macchina in cui gira l'agente**: quali estrattori di PDF ci sono (`pdftotext`, `pypdf`, `pymupdf`), e cosa consigliare di conseguenza (`copia_meccanica`, `mezzo_da_dichiarare`, `controllo_a_campione`, `metodo_alternativo` + `quando_cambiare`) | Il motore **rileva e non esegue mai**: nessun `subprocess`, nessun import dell'opzionale (solo `shutil.which` e `find_spec`). Il giorno in cui la sonda esegue un comando, la skill ha una dipendenza di fatto. Funzione pura `metodo_estrazione` per i test; `status` ne espone il riassunto |
| `testo_utf8` | Legge il testo da collegare **solo se è UTF-8**, altrimenti rifiuta dicendo cosa fare | `pdftotext` senza `-enc UTF-8` scrive Latin-1 (visto sul campo): un file che sembra a posto e che il motore non sa leggere. Il rifiuto è un cancello: nessun non-UTF-8 entra in `data/materiali/` |
| `pagine_dichiarate` + il controllo `caratteri_per_pagina` | Dalle pagine dichiarate (`"40"`, `"1-40"`) ricava il rapporto caratteri/pagina: sotto `CARATTERI_PER_PAGINA[0]` (250) **rifiuta** (copia troncata o riassunta), sopra il massimo (6000) avvisa che le pagine sono sbagliate | È l'unico controllo sulla **fedeltà** possibile senza leggere il documento: aritmetica, non fiducia. `--mezzo` e `--campione` sono invece dichiarazioni dell'agente, non verifiche: non presentarli come garanzia. Il controllo dipende da `--pagine`: senza, il motore lo dice nel payload invece di tacere |
| `chunk_di_testo` / `punteggio_query` / `cerca_nei_materiali` | Ricerca lessicale **dentro** i testi trascritti: blocchi (paragrafi; un titolo markdown resta attaccato al blocco che apre) con riga, punteggio = quota di parole della query presente. La dimensione è `CHUNK_CARATTERI` (600) | È il "RAG" dichiarato: lessicale, locale, senza dipendenze, mai semantico. Restituisce sempre `materiali_senza_testo`, perché il silenzio della ricerca non è una prova. Non trasformarlo in un motore a embedding senza rivedere l'invariante #10 |
| `cmd_learner` | `list`, `merge`, `rename`, `delete`, `persona` dei profili allievo | Il profilo assorbito/rinominato resta come alias: non reintrodurre `PROGRESS_DIR / learner` a mano. `delete` senza `--yes` è un'anteprima che esce 1 senza toccare nulla. `merge` e `rename` devono portarsi dietro anche la persona, e `merge` non deve lasciare una cartella con il solo `_persona.json` |
| `rewrite_profile_aliases` | Dopo una rinomina: chi puntava al vecchio nome segue il nuovo, e il vecchio diventa un alias | Senza questo, il nome vecchio ricrea un profilo vuoto e le sessioni finiscono nel posto sbagliato |
| `style_target` / `style_problems` | Obiettivo effettivo di leggibilità: il più severo fra livello e registro | Il registro **stringe e non allenta**: non introdurre una regola che faccia vincere il registro lasco, o le due cose si contraddicono |
| `style_metrics` | Leggibilità misurabile: Gulpease, parole per frase, virgole per frase, frasi oltre 30 parole | I parametri per livello sono in `STYLE_TARGETS`, quelli per registro in `STYLE_TARGETS_REGISTRO`: cambiarli cambia cosa il validatore avvisa |
| `cmd_style` | Misura una sotto-skill (`style <slug>`) o una bozza di spiegazione (`--text`) | Esce `1` quando è fuori obiettivo: è un avviso, non un guasto |
| `build_parser` / `main` | CLI argparse di **18** sottocomandi (`find`, `create`, `validate`, `register`, `alias`, `merge`, `reindex`, `log`, `due`, `stats`, `list`, `show`, `status`, `style`, `learner`, `strumenti`, `materiali`, `lezione`) + `--data` / `--skill-dir` | `_utf8_stdout()` è necessario su Windows (console cp1252) |

---

## 4. Stato attuale (2026-09-21)

- **Versione della cornice**: `BASE_VERSION = "1.7.0"` in `scripts/iv.py`. La 1.7.0 ha aggiunto il
  **nome della trascrizione dal file di origine** (due estratti dello stesso documento convivono,
  decisione #39) e il fatto che **`-layout` non è sempre giusto**: la sonda riporta entrambi i comandi e
  il protocollo impone di guardare i primi righi dell'estratto (decisione #40). La 1.6.0 ha aggiunto la
  **sonda degli strumenti** (`iv.py strumenti`, decisione #38): il motore dice cosa sa fare la macchina su
  cui gira, così si sa se il testo si copia o si legge. La 1.5.0 ha aggiunto il
  **controllo di plausibilità della trascrizione** (caratteri per pagina, decisione #37), la dichiarazione
  di `--mezzo` e `--campione`, e il passo di **controllo a campione** obbligatorio nel protocollo. La 1.4.0 ha aggiunto la
  **ricerca dentro i materiali** (`materiali testo` + `materiali search`, decisione #36) con i limiti di
  trascrizione come contratto. La 1.3.0 ha reso operative tre
  promesse che le reference facevano già: **piano dalla scadenza** e budget (decisione #33), **materiali
  dell'utente** come fonte privilegiata (#35, nuova FASE 1.0 del protocollo), **lezione del docente** come
  artefatto verificabile (#34). La 1.2.0 aveva aggiunto il **registro** (a chi si parla:
  `standard`/`scolastico`/`bambino`) e la **persona** dichiarata del profilo (`_persona.json`). Sono tutte
  minor: nessun topic diventa `da_rigenerare` e i vecchi restano usabili (compaiono in
  `cornice_aggiornabile` per l'arricchimento opzionale).
  La 1.1.0 aveva aggiunto la regola
  sugli esempi verificati **nella lingua del corso** (trappola in §9, decisione #30): è una minor, quindi i
  topic scritti con la 1.0.0 restano usabili e compaiono in `cornice_aggiornabile` — nessuno diventa
  `da_rigenerare`. Il confronto è per **major**
  (`frame_state`): major diversa → `da_rigenerare` (i contenuti vanno rigenerati); stessa major ma versione
  più vecchia → `cornice_aggiornabile` (arricchimento opzionale, la sotto-skill resta usabile). Versione
  assente o illeggibile → da rigenerare, per prudenza (vedi decisione #27).
- **Test**: 175, tutti verdi (`unittest`, nessuna dipendenza).
- **Capacità aggiunte il 2026-09-22** (dopo il registro): **piano dalla scadenza** (data e budget dichiarati
  nella persona, `status` stima se il materiale ci sta, `due` anticipa i ripassi oltre la prova),
  **materiali dell'utente** come fonte privilegiata (`data/materiali/`, non versionati), **lezione del
  docente** come artefatto verificabile (`data/lezioni/`, `iv.py lezione --check`), **ricerca lessicale
  dentro i materiali** (`materiali testo` / `materiali search`: file, pagina, riga, senza dipendenze),
  **sonda degli strumenti** (`iv.py strumenti`: la macchina decide se si copia o si legge).
- **Sotto-skill presenti** (tutte `validate --all` OK, nessun avviso), ma **una sola è pubblicata**:
  - `data/topics/metodo-feynman/` — esempio di riferimento, scritto a mano (hash `20e669fba114`, rev. 1);
    **è l'unico argomento versionato** (vedi §12);
  - `data/topics/basi-di-machine-learning/` — creata da **opencode** (modalità `autodidatta`, livello 1),
    esclusa dal repository da `.git/info/exclude`;
  - `data/topics/funzionamento-degli-llm-dalle-fondamenta-ai-dettagli/` — creata da **Pi + modello locale**
    (modalità `docenza`, livello 2, prerequisiti «programmazione di base» e «concetti di base dell'AI»),
    poi revisionata a mano: rev. 2. **Materiale di lavoro dell'utente** (corsi): resta sulla sua macchina,
    escluso dal repository da `.git/info/exclude`. È stata pubblicata per errore nel commit `c5bdbb2` e
    rimossa dal versionamento subito dopo.
- **Cosa è pubblico e cosa è privato** — distinzione da non confondere: il repository pubblica la
  **cornice** (`SKILL.md`, `references/`, `scripts/`, `tests/`, documentazione) più **un solo esempio** di
  sotto-skill (`metodo-feynman`). Gli argomenti che l'utente crea studiando restano locali: non vanno
  versionati in automatico solo perché `validate` li promuove. Prima di aggiungere un `data/topics/<slug>/`
  al repository, chiedere.
- **Progressi**: un solo profilo, `data/progress/Dario/` (14 sessioni, 235 minuti, 12 concetti): i due
  profili separati (`default` da opencode, `Dario` da Pi) sono stati uniti con
  `iv.py learner merge default --into Dario` e `.profiles.json` registra l'alias, così un agente che omette
  `--learner` continua a scrivere in `Dario`. Dati locali, non versionati.
- **Leggibilità misurata** (2026-09-21, `iv.py style`): mediana dei file 72.9 Gulpease, minimo 59.4, massimo
  86.7, frase più lunga 35 parole. I tre argomenti hanno leggibilità simile — il topic di opencode+Muse è
  stato il **più** leggibile (70.0 su `percorso.md`), quello di Pi+modello locale il più denso (60.3).
  Misurare è servito a smentire l'ipotesi "il modello X scrive più complicato": la differenza percepita
  stava nella lezione in chat, che nulla registra (vedi debito tecnico in §11).
- **Repository**: radice = skill; `README.md` (inglese) + `README.it.md` (italiano) + `LICENSE` MIT +
  `.gitignore` che esclude dati personali e indice. Repository git inizializzato su `main`, con `origin`
  puntato a https://github.com/Dario-Fe/LearnUp (vedi §12).
- **Installazione locale**: `.agents/skills/insegnante-virtuale` è una **junction** verso la radice
  (creata con PowerShell; `mklink` da Git Bash fallisce per l'escape dei percorsi). Serve solo al discovery
  da parte dell'agente: è in `.gitignore` e non fa parte della pubblicazione.
- **Cosa non è ancora stato fatto**: nessuna esportazione (`export`), nessuna interfaccia web,
  ricerca solo lessicale, cornice non internazionalizzata.

### 4.1 Compatibilità fra agenti (verificata il 2026-09-21)

Il sistema è stato usato per intero da due agenti diversi da quello di sviluppo, su argomenti nuovi e senza
alcuna modifica alla skill:

1. **opencode** → "basi di machine learning" (autodidatta). Ciclo completo riuscito (`find` → `create` →
   contenuti → `validate` → `register` → 9 `log` → `stats`/`DIARIO.md`), indice coerente, nessun file
   estraneo nel repository.
2. **Pi + modello locale (onith1.5)** → "funzionamento degli LLM" (docenza). Ciclo completo riuscito, e il
   test ha fatto emergere tre classi di problemi reali, ora chiuse nel motore (decisioni #20-#23):
   `modalita: null` nei log, concetti-marcatore di sessione registrati in SM-2, profilo allievo scritto con
   un nome diverso da quello di lettura. La **qualità della scrittura** è invece risultata il punto debole
   del modello piccolo (refusi, inglese rimasto in prosa, righe duplicate, una frase di corsi) e ha
   motivato il lint di prosa e il passo di rilettura obbligatorio (§9, decisione #23).

Cosa questo dimostra e cosa no:

- **Funziona** perché tutta la logica sta in `SKILL.md` + `references/` + `iv.py`: nessuna istruzione
  dipende da un client specifico, e ogni comando ha output JSON stabile.
- **Tollerato**: campi extra nei `meta.json` sono ammessi (l'agente può aggiungerne), e `register` scrive
  il blocco `quality` da sé. Non aggiungere validazioni che rifiutino campi sconosciuti: romperebbero
  il funzionamento con agenti diversi.
- **Da sapere**: gli agenti dimenticano gli argomenti opzionali (`--mode`, `--level`, `--learner`). Per
  questo `iv.py log` eredita livello e modalità dal `meta.json`, e `status`/`list` segnalano quando i
  progressi stanno sotto un altro profilo allievo. Se aggiungi opzioni utili, prevedi un default sensato
  invece di un campo vuoto.
- **Agenti diversi sbagliano le stesse cose**: le tre classi di errore del test con Pi erano già state
  commesse da opencode (progressi su un profilo diverso) o sono strutturali (marcatori di sessione
  scambiati per concetti). Quando un problema si ripete su due agenti, la correzione non è un'istruzione
  in più nella documentazione ma un **controllo nel motore** che lo rende impossibile.
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
6. **I file derivati si rigenerano da soli.** `registry.json` si riallinea dai `meta.json` e `DIARIO.md`
   dai progressi (`log` lo riscrive). Non aggiungere stato che vive solo in un file derivato: su un clone,
   o dopo un agente distratto, diventa una bugia.
7. **`--concept` è un contenuto, non una tappa.** Il motore rifiuta i marcatori di sessione («fine
   sessione», «avvio percorso»): inquinano lacune, voto medio e ripetizione spaziata. I contenuti verificati
   vanno in `--concept`, la narrazione della sessione in `--summary`/`--module`/`--next`.
8. **Un profilo allievo per persona.** `--learner` va passato con lo stesso identificativo a ogni comando
   (il confronto ignora maiuscole e spazi, ma non due nomi diversi). Chi legge i progressi deve vedere dove
   sono: `list` e `status` lo dichiarano, e nessun comando deve dedurre il profilo dal nome del computer.
   Il nome si chiede **una volta**, al primo avvio, dicendo dove finisce (`data/progress/`, non versionato),
   e si riusa senza richiederlo quando un profilo esiste già: mai dedurlo da email, cartella utente o
   hostname, e mai insistere con chi preferisce restare anonimo.
9. **Le reference non contraddicono la costituzione.** In caso di conflitto vince `costituzione.md`;
   se cambi una regola, aggiorna entrambe e incrementa `BASE_VERSION`.
10. **Nessuna dipendenza esterna.** Solo libreria standard Python: il progetto deve girare con un
   `git clone` e Python installato, niente pip, niente venv.
11. **Nessun dato personale nel repository.** `data/progress/`, `data/_merged/`, `data/registry.json`
   restano fuori dal versionamento.
12. **La semplicità ha obiettivi numerici.** Il livello dichiarato fissa Gulpease, parole per frase e quota
   di frasi lunghe (`STYLE_TARGETS`): cambiarli cambia un contratto, non una preferenza. Non trasformare
   l'avviso di leggibilità in errore bloccante finché il corpus non sta tutto sopra soglia con margine.
13. **I profili allievo si uniscono, non si duplicano.** Due nomi per la stessa persona si risolvono con
   `iv.py learner merge`, che unisce i progressi e lascia un alias: senza alias la divisione si ricrea.
14. **Il motore non parla italiano "da terminale" e basta**: ogni comando deve avere output JSON stabile
   (`--json` dove esiste) perché è così che l'agente lo consuma.
15. **Rigore dichiarato, mai fonti inventate.** Vale per i contenuti generati e per la documentazione:
    se un'informazione non è verificata, va etichettata come tale (vedi `references/costituzione.md`).

---

## 6. Convenzioni

- **Lingua**: contenuti, documentazione, commenti e messaggi della CLI in **italiano** (il pubblico del
  progetto è italiano). `README.md` è in inglese come vetrina, `README.it.md` è la versione completa.
  Se aggiungi una funzione, aggiorna **entrambi** i README e la sezione Roadmap di pari passo: oltre ai
  comandi, i README riportano la **struttura del repository** (quindi anche le cartelle di dati e i
  template nuovi) e il **numero di test** (`tests/test_iv.py  # N test del motore`), che è andato fuori
  sincrono una volta: è un dato derivato, e nessun controllo lo verifica.
- **Codice**: Python, solo standard library, type hints leggeri, docstring in italiano. Le funzioni del
  motore si chiamano `cmd_<verbo>` e delegano a funzioni pure testabili (`lookup`, `validate_topic`, `sm2`).
- **Slug**: minuscolo, accenti rimossi, spazi in `-` (`slugify`). **Chiave canonica**: parole di contenuto
  ordinate (`key_of`). Non cambiare la formula senza una migrazione.
- **Date e orari**: ISO 8601 (`YYYY-MM-DD`), salvati come stringhe nelle stesse forme attuali.
- **File di dati**: JSON indentato 2, `ensure_ascii=False`, sempre con newline finale.
- **Idempotenza**: i comandi di sola lettura non scrivono **contenuti** né progressi. Le uniche scritture
  ammesse sono i file **derivati**: `data/registry.json` (allineamento ai `meta.json`, toccato solo se
  differisce: c'è un test sull'`mtime`) e `data/progress/<learner>/DIARIO.md` (riscritto da `log` e da
  `stats --write`). A questi si aggiunge `data/materiali/<slug>/INDICE.md`, rigenerato da `materiali list` e
  da ogni `materiali add`. `materiali search` è invece di sola **lettura**: non riscrive l'indice né il
  registro. Un comando di lettura non deve mai modificare `data/topics/`.
- **Compatibilità Windows**: aprire file con `encoding="utf-8"` esplicito e non rimuovere `_utf8_stdout()`.
- **Messaggi CLI**: campi JSON in italiano (`ok`, `azione`, `prossimi_passi`), perché l'agente li interpreta
  direttamente.

---

## 7. Ricette operative

### 7.1 Aggiungere o modificare una regola pedagogica (nuova versione della cornice)

1. Modifica `references/costituzione.md` (e/o `contratto-output.md`, `protocollo-sessione.md`).
2. Incrementa `BASE_VERSION` in `scripts/iv.py`: **major** = regole che invalidano i contenuti generati
   (tutti i topic diventano `da_rigenerare`), **minor** = aggiunte compatibili (i topic restano usabili e
   compaiono in `cornice_aggiornabile`). Il codice confronta solo la major (`frame_state`).
3. Aggiorna `references/schema-sottoskill.md` se la regola tocca la struttura dei file.
4. `python scripts/iv.py status` → con una major nuova i topic vecchi compaiono in `da_rigenerare`; con una
   minor nuova in `cornice_aggiornabile` (c'è un test per entrambi i casi).
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

Copertura attuale (175 test): normalizzazione e similarità, ciclo di riuso (`none`/`exact`/`variant`/
`draft_incompleto`), rifiuto dei duplicati, alias, merge con migrazione dei progressi, reindex,
validazione (bozza vs completo, `--all`, cornice vecchia → `da_rigenerare`), SM-2 (intervalli crescenti,
azzeramento dopo voto basso), log, `due`, profili allievo separati, `show`, `stats --write`, CLI esterna
via `subprocess` (JSON e codice di uscita, più la guardia che nessun sottocomando ridefinisca `--data` o
`--skill-dir`: vedi le trappole), più le classi nate dai test con altri agenti:

- `TestGaranzieSuiDatiRegistrati` — eredità di `--mode`, rifiuto dei marcatori di sessione (e non-rifiuto
  dei concetti veri che nominano un modulo), profilo allievo insensibile a maiuscole, visibilità dei
  progressi di altri profili in `list`/`status`, diario riscritto da `log`, prereq multipli separati.
- `TestLintDiProsa` — caratteri non latini, righe duplicate, markdown sbilanciato: **avvisi, non errori**
  (c'è un test esplicito che una sotto-skill con refusi resta valida e riusabile).
- `TestProfiliAllievo` — creazione di un secondo allievo al primo `log` (cartella e diario propri),
  progressi che non si mescolano, nome con maiuscole diverse che resta un solo profilo, unione di due
  profili con alias, scheda SM-2 più avanzata conservata, rifiuto dei nomi con separatori di percorso
  e del nome vuoto (che resta anonimo), rinomina semplice, rinomina di sole maiuscole (su Windows passa da
  un nome temporaneo), rifiuto della rinomina verso un profilo già usato, anteprima di cancellazione che non
  tocca niente, cancellazione che rimuove anche gli alias e non lascia profili zombie.
- `TestStileMisurabile` — Gulpease e conteggi, righe di elenco come frasi, asticella del livello che sale e scende, comando `style`, avviso di leggibilità nel validatore e silenzio sui file troppo corti.
- `TestPianoDiStudio` — senza persona il piano è vuoto e il passo tecnico non cambia; i moduli visti si ricavano da etichette libere (`2`, `Modulo 3`, `modulo 1: somma`); la stima usa i minuti reali per modulo; con scadenza e budget dice se ci sta e in quel caso guida `prossimo_passo`; senza budget invita a dichiararlo; una prova passata si segnala senza bloccare; l'argomento della prova entra nella stima anche se non è mai stato iniziato; `due` elenca in `prova.da_anticipare` i concetti che cadrebbero dopo la prova.
- `TestLezioneDelDocente` — lo scheletro nasce in `data/lezioni/` e non nei progressi né nei topic; senza compilazione `--check` esce 1 (ISTRUZIONI, placeholder, scaletta corta, meno di tre domande probabili); una lezione compilata passa; il registro dichiarato alza l'asticella; non riscrive in silenzio una lezione esistente (`--force`); data non ISO rifiutata; `log --lesson` registra la lezione consegnata e rifiuta un file inesistente.
- `TestMaterialiDellUtente` — `materiali add` copia (non collega) e scrive l'indice; rifiuta argomenti e file inesistenti e non sovrascrive senza `--force`; una voce il cui file sparisce non sopravvive all'indice; `list` mostra gli argomenti con materiali; la lista degli argomenti dichiara quanti materiali ha ciascuno; i materiali non finiscono nei topic né nei progressi.
- `TestRegistroDellaPersona` — precedenza sessione > persona > banda d'età > `standard`; il registro stringe gli obiettivi del livello e non li allenta mai; `style --registro` misura la bozza con l'asticella giusta; il periodare fitto di virgole si segnala solo col registro; la persona espone `registro_effettivo` e `livello_suggerito`.
- `TestPersonaDichiarata` — la persona dichiarata (`_persona.json`) non è un argomento: non entra nei conteggi di `learner list`, né in `stats`, né in `due`; `merge` la adotta, la tiene o non la perde, e non lascia cartelle con soli metadati; `rename` la segue e riallinea il campo `learner`; dati sbagliati rifiutati (data non ISO, budget non positivo, obiettivo senza scadenza) senza creare profili a metà; i campi aggiunti da un agente sopravvivono alla riscrittura; `--reset` azzera la persona e non i progressi.
- `TestRicercaNeiMateriali` — **due estratti dello stesso materiale convivono** e si cercano entrambi (nome dal file di origine); rifare l'estratto dello stesso file è un aggiornamento (`sostituito: true`) e il payload lo dice; i blocchi sono abbastanza fini da essere una citazione (un paragrafo lungo si spezza in più blocchi); un materiale senza testo non è cercabile ma **non è vuoto** (il payload elenca `materiali_senza_testo`); il testo collegato rende il materiale cercabile con pagina e riga; la ricerca è lessicale e lo dichiara (un sinonimo non trova nulla); il blocco che contiene tutta la query viene prima; si cerca un argomento per volta; rifiuto del testo troppo corto e di quello oltre il limite (accettato con `--force`, con avviso su `fonti.md`); il testo si aggancia solo a un materiale registrato; un `.estratto.md` cancellato riporta il materiale a "non cercabile"; indice e lista dichiarano cosa è cercabile.
  Sulla fedeltà dichiarata: una copia di tre pagine passa il rapporto caratteri/pagina, una da 500 caratteri dichiarata come 12 pagine **no** (e `--force` la accetta con un avviso); pagine non numeriche non impediscono il collegamento ma il payload dice che il controllo non è stato fatto; pagine sottostimate avvisano senza bloccare; `--mezzo`/`--campione` finiscono nel registro, nell'indice, nella lista e **in ogni risultato di ricerca**, dove l'assenza di controllo si legge come *non verificata*;  `--mezzo` sconosciuto rifiutato sia dalla CLI sia dalla funzione; un estratto **non UTF-8** rifiutato con la causa e il comando che lo risolve.
- `TestStrumentiDiEstrazione` — la sonda risponde per la macchina su cui gira: senza estrattori si legge a vista (`--mezzo vista`, controllo a campione **obbligatorio**), con `pdftotext` o `pypdf` la copia è meccanica (controllo consigliato); `pdfinfo` conta le pagine e **non** rende la copia meccanica; il comando consigliato per `pdftotext` contiene `-enc UTF-8` (senza, l'estratto è Latin-1); con `pdftotext` la sonda riporta anche l'**alternativa** senza `-layout` e la regola per scegliere; senza estrattore non c'è alternativa da proporre; rilevamento impossibile = assente, non errore; la CLI dichiara di non eseguire gli strumenti; `status` espone il riassunto.

- `TestDocumentazioneAllineata` — guardia sulla **deriva della documentazione**: i sottocomandi elencati in `AGENTS.md` §3 devono essere esattamente quelli di `build_parser()`, e il numero di test dichiarato nei due README deve corrispondere alle `def test_` di questo file. Salta se `AGENTS.md` o i README non fanno parte della copia. Nasce da due derive reali: §3 dichiarava **14** sottocomandi quando erano 18, e i README hanno riportato 54, 158, 168 e 173 test in momenti diversi.

Quando aggiungi un controllo al `ProseLint`, aggiungi anche il test che lo attiva e il test che verifica
che una sotto-skill pulita non produca avvisi: le euristiche di lingua sono le più facili da far
"sparare a vuoto".

Quando aggiungi un **test**, i due README e questo file vanno riallineati al conteggio nuovo: non è
buona volontà, lo pretende `TestDocumentazioneAllineata` se il numero dichiarato non torna.

### Controllo globale (quando si tocca molto)

Dopo una sessione di modifiche larghe (come quelle sui materiali) vale la pena questo giro, che non ha
dipendenze e non entra nel repository:

```bash
python -m compileall -q scripts tests      # sintassi di tutto
python -m unittest discover -s tests -t tests
python scripts/iv.py validate --all
python scripts/iv.py status
for s in find create validate register alias merge reindex log due stats list show \
         status style learner strumenti materiali lezione; do
    python scripts/iv.py $s --help >/dev/null || echo "ROTTO: $s"
done
```

Nessun linter esterno è installato di proposito (invariante #10). Il 2026-09-22 la stessa verifica è stata
fatta con uno script monouso in `/tmp` (non nel repository) che cerca: import inutilizzati, **definizioni
duplicate allo stesso livello** (rischio reale quando si fanno molte sostituzioni di testo), `except:`
nudo, funzioni definite e mai usate, tabelle markdown con il numero di colonne sbagliato, spazi a fine
riga, caratteri `U+FFFD` e righe oltre 110 caratteri. Due risultati utili: nessuna definizione duplicata e
nessuna tabella rotta, ma una riga con spazio finale (corretta) e una deriva nei conteggi (§3 e README).

Convenzioni dei test: nessun test tocca `data/` reale — `setUp` chiama `iv.set_data_dir(tempdir)`.
I comandi si eseguono con l'helper `run([...])`, che cattura stdout e codice di uscita. I contenuti di
riempimento stanno nelle costanti `VALID_*` in cima al file.

---

## 9. Trappole note

- **`--data` è un'opzione globale**: un sottocomando che la ridefinisce (è stato il caso di
  `lezione --data` per indicare il giorno) la **azzera**, perché argparse sovrascrive il valore con il default
  locale: il comando ignora la data dir e lavora in silenzio su quella reale. Gli unit test non possono
  vederlo, perché chiamano le funzioni con la data dir già fissata dal `setUp`: la difesa è
  `TestCLI.test_nessun_sottocomando_ridefinisce_le_opzioni_globali` più uno smoke via `subprocess`. Se
  aggiungi un'opzione a un sottocomando, controlla prima che il nome non esista sul parser principale
  (l'opzione giusta era `--giorno`).
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
- **Il lint di prosa non è un correttore di bozze**: intercetta caratteri non latini, righe duplicate o
  troncate, markdown rotto, parole straniere residue. Non vede refusi come «soma» per «somma», «ordem» per
  «ordine», «unallievo» per «un allievo»: per quelli serve la rilettura (FASE 1.4-bis del protocollo).
  Misura presa sul campo, sul corso sugli LLM scritto da un piccolo modello locale: il lint ha prodotto 7
  avvisi (tutti difetti meccanici reali), mentre la rilettura a mano ha corretto una trentina fra refusi e
  frasi rotte che il lint non vede — due insiemi quasi disgiunti.
- **Trappola del profilo allievo**: gli agenti inventano un nome per l'allievo (`Dario`) e poi leggono con
  il default. `list` mostrava «0 sessioni, mai» su un argomento con 5 sessioni. Ora `list` e `status`
  dichiarano gli altri profili con progressi; il confronto dei nomi ignora maiuscole e spazi. Restano
  possibili due profili *diversi* per la stessa persona: è una scelta dell'agente, non un bug del motore —
  chiedi prima di unire (`iv.py learner merge`), perché l'unione è irreversibile sul nome assorbito.
- **Alias e cancellazione sono legati**: cancellare un profilo rimuove anche gli alias che puntavano a lui
  (chiave *o* destinazione). Se non li togli, il vecchio nome risolve su un profilo inesistente e il primo
  comando lo ricrea vuoto: un profilo zombie, vuoto ma credibile.
- **Nome profilo = nome di cartella**: spazi e accenti sono ammessi (`Marco Rossi`), separatori di percorso
  no. Il payload dei comandi riporta il profilo **risolto** (`learner_dir(...).name`), non quello richiesto:
  così "ho scritto in `default` mentre credevo `Dario`" si vede subito invece di restare nascosto.
- **Leggibilità ≠ qualità**: `style` misura frasi e parole, non la verità, la profondità o la bontà
  dell'esempio. Un testo può passare tutti gli obiettivi numerici e spiegare male. Non usare il numero come
  alibi, e non riscrivere frasi buone solo per spostare un indice di 0,5 punti.
- **Placeholder e `ISTRUZIONI:`**: il validatore li cerca come stringhe. Se cambi la sintassi dei template,
  aggiorna `PLACEHOLDERS` in `iv.py`.
- **`già`/`più` → `gia`/`piu`**: la normalizzazione rimuove gli accenti, quindi le stopword vanno scritte
  senza accenti in `STOPWORDS`.
- **Cambiare `tokens`/`stems` è una modifica di compatibilità**: può far smettere di risolvere alias
  registrati con la vecchia formula. Se succede, `iv.py reindex` non basta: serve un `alias --add`.
- **Il demo `metodo-feynman`** è il test di qualità a occhio: se il validatore passa ma il contenuto sembra
  fiacco, il problema sono le soglie minime, non l'esempio.
- **La ricerca nei materiali non vede i sinonimi, e il vuoto non è una prova**: `materiali search` confronta
  parole e steli. Un agente che riceve zero risultati e risponde «nel tuo programma non c'è» commette
  l'errore che questa funzione esiste per evitare. Prima di concludere vanno guardati
  `materiali_senza_testo` (materiali mai trascritti) e le pagine dichiarate in `--pagine` (per un manuale
  grande si trascrive un capitolo per volta). È il motivo per cui il payload li restituisce a ogni ricerca.
- **`pdftotext` senza `-enc UTF-8` scrive Latin-1** (trovato provando il ciclo completo su un PDF vero, non
  dai test: negli unit test l'estratto lo scrivevo io, in UTF-8). Il file sembra a posto, gli accenti sono
  byte spuri, e il motore — che legge sempre UTF-8 — o non lo legge o lo legge male. Il comando consigliato
  dalla sonda include `-enc UTF-8`, `testo_utf8` rifiuta il file non-UTF-8 dicendo quale comando lo risolve,
  e c'è un test che lo tiene fermo. Vale per ogni estrattore, non solo per quello: **l'encoding di uscita
  di uno strumento esterno è un'assunzione, non un dato.**
- **Il file derivato non deve cancellarne un altro in silenzio** (trovato sul campo): la trascrizione prendeva il nome dal **materiale**, quindi la seconda estrazione dello stesso documento sovrascriveva la prima senza errore né avviso. Un file derivato che sovrascrive un altro file derivato è una perdita invisibile: nessun test lo vede se i test usano un solo estratto per materiale. La regola che ne è nata: **il nome deriva dalla sorgente**, e quando qualcosa viene comunque sostituito il payload lo dichiara (`sostituito`). Vale per ogni comando che scrive accanto a dati dell'utente: prima di riusare un nome, chiedersi *quante cose diverse possono produrre quel nome*.
- **`-layout` non è sempre giusto, e il motore non può dirlo** (visto su un PDF vero: un riquadro centrato dentro un periodo): l'impaginazione conserva tabelle ed elenchi ma intreccia gli elementi centrati con le frasi; l'ordine di flusso le legge intere ma fonde gli elenchi in una riga e allarga i blocchi. La differenza si vede **guardando l'estratto**, non ragionando sul comando, e i due difetti sono opposti: non esiste un flag "giusto" da fissare nella documentazione. Per questo la sonda li riporta entrambi con la regola per scegliere, il protocollo impone il passo "guarda i primi righi", e le due copie convivono. Attenzione a non "semplificare" tornando a un solo comando consigliato: riaprirebbe il guasto.
- **La sonda rileva e non esegue, e deve restare così**: niente `subprocess`, niente import dell'opzionale
  (solo `shutil.which` e `find_spec`, che non ha effetti). Se un giorno la sonda esegue un comando per
  "verificare meglio", la skill ha una dipendenza di fatto e l'invariante #10 è rotto senza che nessun test
  se ne accorga. L'estrazione resta a chi conduce la sessione.
- **`--mezzo` e `--campione` sono dichiarazioni, non garanzie**: il motore li registra e li mostra, ma
  nessun codice ha verificato niente. Non presentarli mai come una prova di fedeltà, e non togliere il
  controllo caratteri/pagina pensando che li sostituisca: quello è aritmetica, gli altri due sono la parola
  di chi ha trascritto. Attenzione anche al fatto che il controllo dipende da `--pagine`: se manca, il
  motore lo dichiara in `avvisi` e **nessuno** ha controllato la completezza — un payload senza avvisi non
  significa "copia verificata".
- **Il testo trascritto è una fonte citabile, quindi si trascrive e non si riassume**: il motore non può
  distinguere una trascrizione da una parafrasi. Una parafrasi collegata come `--file` diventa una fonte
  citabile con riga e pagina, cioè esattamente il tipo di bugia che l'invariante #15 vieta. La difesa è la
  regola in `protocollo-sessione.md` FASE 1.1-ter più `fonti.md`, non il codice: il codice controlla solo
  lunghezza e forma.
- **Calchi linguistici negli esempi (visto sul campo)**: la sotto-skill sugli LLM spiegava l'ambiguità con
  «la banca era alluvionata perché il fiume era in piena» — ambiguità inglese (*bank* = istituto / riva) che
  in italiano non esiste: *banca* non significa "riva", e la riva è *riva, sponda, argine* (Treccani dà
  "banca" come istituto di credito, come "banca dati", come antica "panca", e come termine tecnico per i
  terrapieni a ridosso degli argini). L'allievo ha risposto in modo plausibile e la verifica l'ha bocciato
  su una domanda che non esisteva: **l'errore era nel materiale, non nella risposta**. Il `ProseLint` non
  può vederlo (non è un refuso, è un senso sbagliato), quindi la difesa è la regola in
  `references/contratto-output.md`: sostituire l'alternativa nella frase e verificare che l'ambiguità
  sopravviva in italiano.

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
| 20 | `log` eredita anche `--mode` dal `meta.json` e rifiuta i concetti-marcatore di sessione | Le stesse omissioni degli agenti che avevano già motivato l'eredità di `--level`; i marcatori («fine sessione: moduli 1-3») creavano lacune finte, voci in `weak_spots` e suggerimenti sbagliati nel diario |
| 21 | Il profilo allievo è normalizzato (maiuscole/spazi) e `list`/`status` dichiarano i profili con progressi | Un agent (Pi) ha scritto in `Dario`, un altro (opencode) in `default`: la tabella diceva «mai» su argomenti studiati. Il motore non unifica profili diversi — sarebbe una scelta sui dati dell'utente — ma non li nasconde |
| 22 | `DIARIO.md` si riscrive da `log` (oltre a `stats --write`) | È un file derivato come il registro: se dipende da un passo che l'agente può saltare, resta indietro. Stesso principio della decisione #17 |
| 23 | Lint di prosa come **avviso** in `validate` + passo di rilettura obbligatorio nel protocollo | Il validatore garantiva lo schema ma non la scrittura: un modello locale ha prodotto refusi, inglese rimasto in prosa, righe duplicate e un modulo con una frase duplicata. Gli avvisi rendono visibile la deriva senza bloccare il riuso (una sotto-skill utile non deve diventare inutilizzabile per una virgola) |
| 24 | Obiettivi di leggibilità numerici per livello (`iv.py style`, `STYLE_TARGETS`) | "Spiega semplice" era solo una richiesta in prosa: dipendeva interamente dal modello. Con Gulpease, parole per frase e quota di frasi lunghe diventa un contratto verificabile — e la risposta operativa è sempre la stessa: **spezza le frasi**. Soglie tarate sul corpus esistente (mediana 72.9, minimo 59.4) |
| 25 | `iv.py learner merge` unisce due profili allievo e registra l'alias in `.profiles.json` | La divisione dei progressi non è un caso isolato: l'hanno prodotta due agenti indipendenti. Un comando determinista evita la chirurgia sui file, e l'alias impedisce che il profilo assorbito rinasca al primo comando senza `--learner` |
| 26 | Il nome dell'allievo si chiede **al primo avvio** (solo se non esiste nessun profilo) e si dichiara che resta in locale | Chiude alla radice la divisione dei profili: il nome non è più una variabile che l'agente inventa o deduce, ed è il momento naturale per dire dove finiscono i dati. La condizione "solo se non ci sono profili" tiene la personalizzazione senza aggiungere attrito a ogni sessione: chi ha già studiato non vede nessuna domanda in più. Il rifiuto resta legittimo (`default`) |
| 27 | `da_rigenerare` scatta solo al cambio di **major**; una minor più vecchia diventa `cornice_aggiornabile` | Il codice confrontava la stringa intera, mentre la documentazione prometteva "minor = aggiunte compatibili": conseguenza, ogni ritocco alle regole avrebbe marcato come da rigenerare anche i topic perfettamente validi, con lavoro inutile e un allarme che perde significato. Ora il codice dice quello che le reference promettevano. Una versione assente o illeggibile resta `da_rigenerare`: provenienza ignota = ricontrollare |
| 28 | Il nome del profilo è validato (spazi sì, separatori di percorso no) e i comandi riportano il profilo **risolto** | Un secondo studente deve nascere dichiarandolo, e i nomi reali hanno spazi ("Marco Rossi"): bloccare gli spazi sarebbe stato ostile, lasciar passare `../x` avrebbe scritto fuori da `data/progress/`. Riportare il nome risolto chiude la classe di bug in cui l'output dichiara un profilo e il file ne dimostra un altro (già visto con `log`, che rispondeva `default` senza dirlo mentre l'agente credeva di aver scritto altrove) |
| 29 | `learner rename` separato da `learner merge`, e `learner delete` con anteprima obbligatoria (`--yes`) | Sono tre operazioni diverse e vanno confuse il meno possibile: correggere un nome (rename, senza toccare i contenuti), fondere due storie (merge), distruggere una storia (delete). `rename` verso un profilo con progressi si rifiuta e rimanda a `merge`; `delete` senza `--yes` non modifica niente ed espone cosa verrebbe perso |
| 30 | Una verifica costruita su un esempio difettoso si **annulla**, non si corregge: la scheda esce dai progressi e il concetto si rivaluta con un esempio valido | Un voto basso su una domanda sbagliata è un dato falso, e nella ripetizione spaziata costa due volte: programma un ripasso che non serve e abbassa l'ease di un concetto mai verificato. Corollario sul materiale: l'esempio va verificato **nella lingua del corso** (vedi trappole e `contratto-output.md`), perché il calco dall'inglese è invisibile al lint |
| 31 | La **persona dichiarata** (banda d'età, tempi, scadenza) vive in `data/progress/<learner>/_persona.json`, e i file di progresso si leggono con un unico `topic_files()` | Chi studia non è l'argomento: la stessa sotto-skill serve un bambino e un adulto, quindi la banda d'età non può stare nel `meta.json` senza rompere il riuso. Dentro la cartella del profilo, la persona resta **portabile con i suoi progressi** (backup, export, import fra utenti); il prezzo è che i sei punti che contavano i JSON come argomenti andavano riuniti in un helper, e il test di `merge` ha confermato che senza quell'helper il file della persona veniva fuso come una storia di studio. Nessun cambio di `BASE_VERSION`: non sono regole pedagogiche ma collocazione di dati |
| 32 | Il **registro** (`standard`/`scolastico`/`bambino`) stringe gli obiettivi del livello e non li allenta; la precedenza è sessione > persona > banda d'età > `standard`, e il registro si misura con `style --registro` **prima** di consegnare un modulo | "Spiega come a un bambino" era, come "spiega semplice" prima della decisione #24, una richiesta in prosa che dipendeva interamente dal modello. Il registro non poteva essere un asse parallelo al livello: due assi che si contraddicono (livello 3 + banda bambino) vanno risolti da una regola, non da un caso, e la regola "il registro stringe" risolve senza arbitrati. La precedenza mette la sessione in cima perché è l'unica che sa cosa sta succedendo adesso; l'**argomento non entra nella scala** perché le sotto-skill sono di chiunque le studi. Il registro si applica quando si parla, non quando si scrive il corso: per questo nessun `meta.json` lo contiene e nessun topic va rigenerato (minor, `BASE_VERSION` 1.2.0) |
| 33 | Scadenza e budget dichiarati nella persona **producono un piano** (`piano_di_studio` in `status`, `prova.da_anticipare` in `due`) | `esame` prometteva il "piano a ritroso dalla data" e `modalita.md` lo diceva da sempre, ma il motore non conosceva la data: l'utente rispondeva a una domanda e nessuno la usava. Un campo dichiarato e mai usato è peggio di un campo assente, perché sembra che il sistema abbia capito. La stima è dichiarata tale (minuti per modulo dalle sessioni passate) e non promette un voto |
| 34 | La lezione per una classe è un **artefatto verificabile** (`iv.py lezione`, `data/lezioni/`), con `--check` che rifiuta gli scheletri | In docenza il valore non è la spiegazione in chat, che sparisce, ma il materiale che si porta in aula. "Il sistema produce anche materiale per il docente" era una promessa senza artefatto; ora la lezione ha sezioni obbligatorie, minimi di sostanza e leggibilità verificata — e vive fuori dalle sotto-skill perché è di una classe, non di tutti |
| 35 | I materiali dell'utente si **copiano** in `data/materiali/<slug>/` e diventano la fonte da privilegiare; l'indice è derivato e non sopravvive a un file cancellato | `modalita.md` prometteva l'allineamento a programma e prove passate, e la decisione #11 promette "niente fonti inventate": senza un posto dove metterli, i materiali restavano nella chat e sparivano. La copia invece del collegamento evita che il corso si rompa quando l'utente sposta l'originale; l'estrazione del testo la fa l'agente (sa leggere i PDF), così l'invariante "nessuna dipendenza" resta intatta |
| 36 | La ricerca dentro i materiali è **lessicale e limitata dalla trascrizione**: `materiali testo` collega la trascrizione (rifiutata sotto ~400 caratteri e sopra ~400.000, cioè ~250 pagine), `materiali search` risponde con file, pagina e riga, e il payload dichiara sempre cosa non era cercabile | Il "RAG" che si poteva fare senza dipendenze e senza mentire è questo: le funzioni di normalizzazione e steli c'erano già, i materiali no. Due limiti sono deliberati, non tecnici. Il tetto sulla trascrizione rende **eseguibile** la regola "non dichiarare letto ciò che non potevi leggere": sopra quella soglia si estrae un capitolo per volta e si dichiara in `fonti.md` cosa manca. Il pavimento evita che un frammento diventi una "fonte". Il motore non può distinguere una trascrizione da una parafrasi — resta un debito dichiarato, difeso dalla regola "trascrivi, non riassumere" e dalla citazione verificabile (riga e pagina) |
| 37 | La fedeltà di una trascrizione si controlla **per aritmetica**: i caratteri per pagina dichiarata (`CARATTERI_PER_PAGINA`, rifiuto sotto 250, avviso sopra 6000), più `--mezzo` e `--campione` come **dichiarazioni** visibili in indice, lista e risultati di ricerca | Delle due domande dell'utente — «la copia è davvero il documento?» e «viene letta quando serve?» — la prima non ha risposta certa: il motore non legge il PDF e nessun codice distingue una trascrizione da una parafrasi. Invece di una promessa, si fa l'unica verifica che non chiede fiducia: se dichiari 50 pagine e il testo ha 8.000 caratteri, la copia è troncata o riassunta, e si vede. Il rapporto becca il troncamento e il riassunto grosso, **non la parafrasi della stessa lunghezza** — limite dichiarato. Sul secondo punto: nessun controllo obbliga l'agente a cercare, quindi la difesa è il protocollo (controllo a campione di tre citazioni prima di citare) e il fatto che `search` restituisce sempre `materiali_senza_testo` e la provenienza: il vuoto non è una prova, e chi legge sa quanto ci si sta fidando |
| 38 | Il motore **sonda la macchina** (`iv.py strumenti`: `pdftotext`, `pdfinfo`, `pypdf`, `pymupdf`) e ne ricava il metodo di trascrizione: copia meccanica (`--mezzo testo`, controllo a campione consigliato) oppure lettura (`--mezzo vista`, controllo **obbligatorio**). `status` lo dichiara a ogni avvio | La domanda "gli strumenti ci sono?" non ha una risposta valida in generale: cambia da macchina a macchina, ed è per questo che va chiesta a runtime e non promessa nella documentazione. Gli attrezzi restano **opzionali** (invariante #10): il motore li rileva con `shutil.which`/`find_spec` e **non li esegue mai**, così la skill continua a girare con il solo Python. Un PDF copiato meccanicamente non è una lettura, e il codice lo sa per la prima volta: da lì dipende quanto controllo serve. Corollario trovato sul campo: `pdftotext` senza `-enc UTF-8` scrive Latin-1, quindi il comando consigliato include il flag e `testo_utf8` rifiuta un estratto non-UTF-8 invece di lasciarlo entrare |
| 39 | Il nome della trascrizione deriva dal **file di origine** (`<origine>.estratto.md`), non dal materiale: due estratti dello stesso documento convivono e si cercano entrambi, mentre lo stesso nome è un **aggiornamento** dichiarato (`sostituito: true`) | Con il nome derivato dal materiale, il secondo estratto **cancellava il primo in silenzio**: nessun errore, nessun avviso, nessun `--force`. La conseguenza era che il flusso centrale della regola "sopra ~250 pagine si trascrive un capitolo per volta" era **impossibile**: il capitolo 2 cancellava il capitolo 1. Trovato provando il ciclo su un PDF vero, non dai test — i test usavano una sola trascrizione per materiale. Ora il nome dice da quale file viene, e l'origine resta scritta in `materiali.json` (`sorgente`) e in `INDICE.md` |
| 40 | La sonda riporta **entrambi** i comandi di `pdftotext` (`-layout` e non) e il protocollo impone di **guardare i primi righi** dell'estratto prima di scegliere: la scelta dipende dal documento, non dalla preferenza | Un PDF di prova (Word 2019, colonna singola, nessuna scansione, 3 pagine: un documento normale, non un caso estremo) ha mostrato che `-layout` **sposta un riquadro centrato in mezzo a una frase**, facendo dire al periodo una cosa che nel documento non esiste: le parole ci sono tutte, l'ordine no. (Il documento era privato dell'utente e non è nel repository: i test riproducono il **modello** del guasto con testi sintetici.) Senza `-layout` le frasi sono intere ma gli elenchi si fondono in una riga e i blocchi diventano enormi. Il codice **non può** decidere: distingue una copia fedele da una infedele solo chi legge. Quindi si dichiara il dubbio invece di nasconderlo ("il flag giusto dipende dal documento"), si sceglie guardando, e se servono entrambe le estrazioni convivono grazie alla decisione #39. Corollario: `CHUNK_CARATTERI` sceso da 1200 a 600, perché in modalità flusso un blocco da 868 caratteri rendeva la citazione inutile ("riga 1" per un'intera pagina) |

| 41 | I limiti del "RAG" si **dichiarano come contratto** nella sezione *Limiti da conoscere* di entrambi i README: tre limiti puntuali (cerca solo il trascritto, ricerca lessicale, fedeltà non garantita — parafrasi e ordine delle frasi invisibili), più la formula che li riassume: **verificabile, non infallibile** | L'utente ha chiesto esplicitamente di metterlo per iscritto prima di far sedimentare le modifiche, ed è la sintesi onesta di ciò che il progetto può promettere. La ricerca locale funziona, ma un utente che la legge come "la skill ha letto i miei documenti" costruisce fiducia su una base falsa: l'errore non si vede nella demo, si vede il giorno in cui cita una fonte che non esiste. Un limite scritto nelle reference non basta (l'utente legge il README, non `protocollo-sessione.md`), e diffuso in venti punti non basta nemmeno: serve **un posto** dove chi valuta il progetto trova i tre limiti insieme, e `SKILL.md` ha la regola operativa corrispondente ("mai vendere la ricerca come se avesse guardato tutto") |

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
- [~] Import del programma d'esame da PDF/elenco capitoli → proposta di piano dei moduli con revisione
      umana. **Avviato**: `materiali add --tipo programma` copia il programma e lo rende la fonte da
      rispettare; manca la proposta automatica di piano dei moduli.
- [ ] Proposta automatica di sotto-skill di prerequisito a partire dai campi *Serve prima* dei moduli.
- [ ] Analisi delle lacune trasversali fra argomenti diversi.

### v0.5 — Integrazioni

- [ ] Server MCP che espone i comandi principali come tool.
- [ ] Promemoria di ripasso via email/calendario (`.ics`).
- [~] RAG sui materiali dell'utente come fonte preferita. **Ricerca lessicale fatta** (`materiali testo`
      + `materiali search`: blocchi con file/pagina/riga, limiti di trascrizione come contratto),
      **controllo aritmetico della fedeltà fatto** (caratteri per pagina: becca troncamento e riassunto
      grosso), **flusso "un capitolo per volta" tecnicamente possibile** (il nome della trascrizione
      viene dalla sorgente: gli estratti convivono). Mancano: una rilevanza che vada oltre la
      sovrapposizione di parole; un controllo sulla **parafrasi della stessa lunghezza** (il motore non
      può distinguerla da una trascrizione: solo la regola e `fonti.md` lo dichiarano); e un **controllo
      della leggibilità** dell'estratto (l'intreccio di un riquadro centrato in una frase passa ogni
      controllo automatico: lo vede solo chi legge i primi righi — vedi il passo nel protocollo).
- [ ] GitHub Action `iv.py validate --all` sulle pull request.
- [ ] Import/export di singole sotto-skill fra utenti, con merge dei progressi locali.

### Debito tecnico noto

- [ ] `references/` è solo in italiano: valutare una cartella `references/en/` quando ci sarà pubblico non italiano.
- [ ] `validate_topic` non controlla la coerenza fra `meta.json` e il contenuto (es. livello dichiarato vs
      registro linguistico dei moduli): valutare un avviso euristico.
- [ ] Il `ProseLint` non ha un dizionario: refusi come «soma»/«somma» o «ordem»/«ordine» passano. Idea:
      confrontare il vocabolario del topic con quello del `glossario.md` (distanza di edit 1 tra un termine
      del glossario e una parola dei moduli) per intercettare la **deriva terminologica**.
- [ ] Lo stile si misura sui **file** generati, non sulla lezione che l'agente scrive in chat: la deriva di
      stile durante l'insegnamento resta non verificabile a posteriori. Idea minima: `log --explanation "…"`
      che sorveglia le ultime frasi consegnate, o un `style --text` obbligatorio prima di ogni modulo nuovo.
- [ ] `style` misura la *scrittura*: non vede la densità concettuale (quanti concetti nuovi per riga) né se
      il livello di astrazione è adatto. Un `--concetti-per-100-parole` euristico è il prossimo passo naturale.
- [ ] Nessuna migrazione automatica del registro quando cambia la formula delle chiavi canoniche.

---

## 12. Pubblicazione

Repository pubblico: **https://github.com/Dario-Fe/LearnUp** (branch `main`, remote `origin`).
Attenzione ai due nomi diversi: il **repository** si chiama `LearnUp`, la **skill** `insegnante-virtuale`
(è quello che l'agente carica ed è quello che `--skill` si aspetta). Non "correggere" il nome della
skill per allinearlo al repository: romperebbe le installazioni esistenti e il caricamento per nome.

Versionare: `SKILL.md`, `README.md`, `README.it.md`, `AGENTS.md`, `LICENSE`, `.gitignore`, `references/`,
`scripts/`, `assets/`, `tests/`, e **`data/topics/` limitatamente all'esempio di riferimento**
(`data/topics/metodo-feynman/`).

Non versionare: `data/progress/`, `data/_merged/`, `data/registry.json`, `.agents/`, `__pycache__/`
(già in `.gitignore`).

Non versionare `data/lezioni/` (lezioni preparate per una classe) e `data/materiali/` (materiali forniti
  dall'utente, anche protetti da copyright): sono in `.gitignore`, come `data/progress/`.

Non versionare gli argomenti creati studiando (sono materiale dell'utente): restano sulla sua macchina ed esclusi da `.git/info/exclude`, che è **locale e non versionato** — lo stesso meccanismo di
`data/progress/`. Oggi elenca `data/topics/basi-di-machine-learning/` e
`data/topics/funzionamento-degli-llm-dalle-fondamenta-ai-dettagli/`. Serve a due cose insieme: non
finiscono nel repository e non sporcano `git status`, così un argomento locale non viene aggiunto per
sbaglio con un `git add -A`.

Il repository di riferimento è già inizializzato e pubblicato: non serve `git init` né `git remote add`.
Per un **fork** o una copia nuova:

```bash
git init && git add . && git status      # verificare che non compaia nulla di personale
git commit -m "Insegnante Virtuale: skill di studio rigenerante"
git branch -M main
gh repo create <utente>/LearnUp --public --source=. --push
```

Verificare che `npx skills add <utente>/LearnUp --list` trovi la skill `insegnante-virtuale`.
Prima di pubblicare un fork: sostituire il titolare del copyright in `LICENSE` (già impostato a
`Dario-Fe` nel repository di riferimento).

---

## 13. Cosa NON fare

- Non committare `data/progress/` o `data/registry.json`: contengono dati personali e indice rigenerabile.
- Non committare gli argomenti creati studiando (`data/topics/<slug>/` diverso da `metodo-feynman`):
  sono materiale dell'utente, non parte della skill.
- Non usare una sotto-skill in stato `draft`, e non disattivare la validazione per "fare prima".
- Non toccare i progressi durante una rigenerazione.
- Non aggiungere dipendenze Python obbligatorie.
- Non trasformare le sotto-skill in skill di primo livello.
- Non far divergere `validate_topic()` da `references/schema-sottoskill.md`.
- Non aggiornare un solo README: `README.md` e `README.it.md` vanno tenuti allineati, insieme alla Roadmap.
- Non inventare fonti, citazioni o numeri in nessun contenuto, documentazione inclusa.
