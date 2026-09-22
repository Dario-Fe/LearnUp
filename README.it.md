# Insegnante Virtuale

**Una Skill che trasforma un agente nel tuo insegnante, in qualsiasi materia.**

**Una skill per agenti AI che studia con te e impara gli argomenti una volta sola.**
Rigorosa nei contenuti, divulgativa nel modo: esempi concreti, verifiche continue, e una memoria
dei progressi che sopravvive alle sessioni.

[English version →](README.md)

**Repository:** https://github.com/Dario-Fe/LearnUp — il nome della skill è `insegnante-virtuale`.

---

## Il problema

Ogni volta che chiedi a un assistente *"spiegami le equazioni di secondo grado"* riparti da zero.
La spiegazione è generica, lo stile cambia, non c'è un percorso, nessuno ricorda che tre giorni fa
ti eri bloccato sulla formula risolutiva, e la settimana dopo rispieghi tutto daccapo.

## L'idea: un sistema rigenerante

Una **cornice fissa** di regole pedagogiche, più **sotto-skill generate su misura** per ogni argomento,
salvate su disco e **riusate** nelle sessioni successive.

```
                 ┌──────────────────────────────┐
   tu: "voglio   │  CORNICE (invariante)        │
   studiare X"   │  rigore, chiarezza, esempi   │
        │        │  livelli, verifica, memoria  │
        ▼        └──────────────┬───────────────┘
 ┌─────────────┐              │ vincola
 │ iv.py find  │              ▼
 │ X esiste?   │      ┌──────────────────────┐
 └──────┬──────┘      │ SOTTO-SKILL di X     │  ← generata una volta,
        │             │ percorso · glossario │    poi RIUSATA
   ┌────┴────┐        │ errori · esercizi    │
   │ sì  │ no│        │ verifica · fonti     │
   ▼     ▼   └────────┴──────────────────────┘
 RIUSA  GENERA → valida → registra
        │
        ▼
 ┌──────────────────────────────┐
 │ STATO DELL'ALLIEVO           │  ← non si rigenera mai
 │ sessioni · lacune · SM-2     │
 └──────────────────────────────┘
```

Quattro strati con cicli di vita diversi:

| Strato | Dove vive | Cambia quando |
|---|---|---|
| **Cornice** (regole comuni) | `references/` | Quasi mai; ha una versione (`BASE_VERSION`) |
| **Sotto-skill** (conoscenza dell'argomento) | `data/topics/<slug>/` | Generata la prima volta, poi affinata o rigenerata |
| **Stato dell'allievo** | `data/progress/<learner>/` | Ogni sessione |
| **Orchestrazione** | `SKILL.md` + `scripts/iv.py` | Ogni sessione |

Questa separazione è il cuore del progetto: la conoscenza è rigenerabile, i tuoi progressi no.

---

## Cosa fa

- **All'avvio chiede cosa vuoi studiare** e cerca prima di generare: gli argomenti già studiati si riusano.
- **Genera una sotto-skill completa** per ogni nuovo argomento: percorso a moduli, glossario,
  banca degli errori tipici, esercizi a difficoltà crescente con criteri di autovalutazione,
  prova finale, fonti per livello.
- **Valida prima di usare**: uno scheletro non compilato non può essere attivato (il validatore blocca
  placeholder, moduli senza obiettivo verificabile, esercizi senza soluzioni) e avvisa sui difetti di
  scrittura tipici degli agenti: caratteri non latini, righe duplicate, markdown rotto.
- **Riconosce i doppioni**: alias e unione di argomenti simili, senza perdere i progressi.
- **Ricorda e programma i ripassi**: ripetizione spaziata (SM-2 semplificato) su ogni concetto verificato.
- **Tiene un diario**: minuti, argomenti che stanno raffreddando, lacune ricorrenti, cosa rivedere adesso.
- **Ti chiede il nome una volta sola** (al primo avvio) e tiene i progressi in un profilo per persona —
  in `data/progress/<nome>/`, che resta sulla tua macchina. Se preferisci restare anonimo, il profilo è `default`.
- **Più studenti sullo stesso computer**: basta dichiararli (`--learner "Marco Rossi"`). Un profilo nuovo nasce
  al primo log con il suo diario, e le sotto-skill restano condivise: la conoscenza si rigenera, i progressi no.
- **Tre modalità**: autodidatta, preparazione esame, docenza (più profili allievo separati).
- **Rigore dichiarato**: ogni affermazione è etichettata *consolidato / semplificato / dibattuto /
  inferenza / da verificare*, e ogni sotto-skill ha una sezione **Da verificare**. Mai fonti inventate.
- **Semplicità verificabile**: ogni livello ha obiettivi numerici di leggibilità (indice Gulpease, parole
  per frase) controllati da `iv.py style` e dal validatore — così "spiega semplice" non dipende dal modello. Il
  **registro** (a chi si parla: `standard`, `scolastico`, `bambino`) aggiunge vincoli a quelli del livello e
  non li allenta mai: è dichiarato nella persona del profilo e misurato con `style --registro` prima di
  consegnare un modulo.
- **Piano dalla scadenza**: dichiarata la data della prova e il tempo a disposizione, `status` stima se il
  materiale che resta ci sta, e `due` anticipa i ripassi che cadrebbero dopo la prova.
- **I tuoi materiali sono la fonte**: `materiali add` copia appunti, programmi e prove passate in
  `data/materiali/` (restano tuoi, non vengono versionati) e i contenuti generati si allineano a quelli.
  Collega la trascrizione in testo (`materiali testo`) e il motore ci cerca dentro **in locale**, senza
  dipendenze: `materiali search` risponde con file, pagina e riga. È una ricerca *lessicale* — non trova
  sinonimi — e funziona solo su ciò che è stato trascritto: il comando lo dichiara invece di far credere
  di aver guardato tutto.
  Prima di trascrivere, `strumenti` dice cosa sa fare **questa** macchina: se trova `pdftotext` (o `pypdf`,
  o `pymupdf`) il testo si **copia** dal PDF invece di essere letto, ed è la differenza fra una copia e una
  lettura. Sono attrezzi opzionali: se non ci sono, si legge a vista e il controllo a campione diventa
  obbligatorio. (`pdftotext` va invocato con `-enc UTF-8`: senza quel flag scrive Latin-1 e il motore
  rifiuta il file, perché gli accenti rotti non sono una fonte citabile.) Il flag `-layout` invece **non è
  sempre giusto**: conserva elenchi e tabelle ma fa entrare i riquadri centrati in mezzo alle frasi, e
  l'ordine di lettura conta quanto le parole. La scelta si fa guardando i primi righi dell'estratto, e due
  estratti diversi dello stesso documento convivono: la ricerca li interroga tutti e dice da quale viene.
  Il motore non può leggere il PDF né giudicare la fedeltà di una trascrizione, quindi fa **l'unica
  verifica possibile senza fidarsi di nessuno**: il rapporto caratteri/pagina. Dichiari `--pagine "1-50"`
  e il testo ha 8.000 caratteri? Ti rifiuta la copia invece di accettarla in silenzio. E riporta `--mezzo`
  (come l'hai ottenuto) e `--campione` (se l'hai controllata a campione) accanto a ogni risultato, così
  sai quanto fidarti invece di dovertelo ricordare.
  Il resto lo tiene la procedura: prima di citare una trascrizione come fonte, l'agente deve confrontare
  **almeno tre citazioni prese a caso** con l'originale e registrarne l'esito. Se una non combacia, quella
  trascrizione non è una fonte — e viene detto, invece di essere citata come se lo fosse.
- **Lezioni per una classe** (docenza): `lezione <slug> --classe "3B"` crea l'artefatto della lezione, e
  `lezione <slug> --check` non lascia portare in aula uno scheletro non compilato.

---

## Requisiti

- **Python 3.10+** (nessuna dipendenza esterna: solo libreria standard)
- Un agente AI che sappia leggere file ed eseguire comandi (Claude Code, Codebuff, Cursor, Windsurf…)
- Git, se vuoi versionare i tuoi argomenti

---

## Installazione

La skill segue lo standard **Agent Skills** (`SKILL.md` con frontmatter `name` + `description`).

### 1. Con `skills` CLI (consigliato)

```bash
npx skills add Dario-Fe/LearnUp --skill insegnante-virtuale --yes
```

Il repository è `Dario-Fe/LearnUp`; la *skill* si chiama `insegnante-virtuale` — è il nome che
`--skill` si aspetta e il nome con cui l'agente la carica.

### 2. A mano, dentro un progetto

Copia il contenuto di questo repository in:

```
tuo-progetto/.agents/skills/insegnante-virtuale/
```

(per Claude Code va bene anche `tuo-progetto/.claude/skills/insegnante-virtuale/`)

L'agente troverà la skill per nome: basta chiedergli di studiare qualcosa.

### 3. Sviluppo: il repository *è* la skill

Clona il repository e collega la cartella alla posizione di discovery:

```bash
git clone https://github.com/Dario-Fe/LearnUp.git
cd LearnUp
# Linux / macOS
mkdir -p .agents/skills && ln -s "$(pwd)" .agents/skills/insegnante-virtuale
# Windows (junction, non richiede permessi di amministratore)
powershell -NoProfile -Command "New-Item -ItemType Junction -Path '.agents\skills\insegnante-virtuale' -Target (Get-Location)"
```

---

## Avvio rapido

Non serve configurare nulla: chiedi e basta.

| Tu dici | Cosa succede |
|---|---|
| *(primo avvio in assoluto)* | Ti chiede come chiamarti — per separare i tuoi progressi, e resta su questo computer. Puoi rispondere "resto anonimo" |
| *"Voglio studiare il metodo Feynman"* | Cerca nel registro; se l'argomento non c'è, genera la sotto-skill, la valida e comincia |
| *"Riprendiamo il metodo Feynman"* | Riusa la sotto-skill salvata, legge i progressi e riparte dal punto giusto |
| *"Prepariamo l'esame di statistica"* | Passa in modalità esame: piano a ritroso, simulazioni a tempo, soglie |
| *"Ripassiamo"* | Mostra i concetti in scadenza e apre con 5 minuti di recupero attivo |
| *"Spiegami *X* come a un principiante"* | Livello 1-2, esempio concreto, micro-verifica, e registra il voto |
| *"Com'è andato il mio studio questo mese?"* | Aggiorna e mostra il diario di apprendimento |

La prima volta su un argomento nuovo l'agente compila otto file (percorso, errori tipici, glossario,
esercizi, verifica, fonti, metadati, contratto) e verifica lo schema prima di iniziare: richiede
qualche minuto, ma quella conoscenza resta e si riusa per sempre.

---

## Come funziona

### Il ciclo rigenerante

| Passo | Cosa succede | Comando |
|---|---|---|
| **Ricerca** | Normalizzazione (accenti, stopword, steli), alias e similarità → `exact` / `variant` / `candidates` / `none` | `iv.py find "…"` |
| **Decisione** | L'agente riusa, chiede conferma sui casi dubbi, unisce o genera | `iv.py alias` · `iv.py merge` |
| **Generazione** | Scheletro dal template, poi contenuto scritto dall'agente | `iv.py create --title "…"` |
| **Controllo** | Schema, minimi di sostanza, placeholder residui: blocca le bozze | `iv.py validate <slug>` |
| **Attivazione** | Stato `active`, hash del contenuto, versione della cornice | `iv.py register <slug>` |
| **Memoria** | Sessioni, voti, lacune, ripetizione spaziata | `iv.py log` · `iv.py due` |
| **Rigenerazione** | Cambia la cornice: major nuova → topic `da_rigenerare`; minor nuova → `cornice_aggiornabile` (opzionale) | `iv.py status` |

Il registro confronta **chiavi canoniche** (parole di contenuto, ordinate, senza accenti) e **alias**:
"Roma antica", "Impero romano" e "Storia romana" possono convergere sullo stesso argomento invece di
generare tre doppioni.

### Cosa contiene una sotto-skill

```
data/topics/<slug>/
├── SKILL.md            # contratto didattico, mappa dei moduli, come condurre la sessione
├── percorso.md         # i moduli: idea centrale, esempio concreto, controesempio, verifica
├── errori-tipici.md    # misconcezioni: perché sono allettanti e come smontarle
├── glossario.md        # termini minimi + termini da NON usare
├── esercizi.md         # base → intermedio → avanzato, soluzioni nascoste con criteri di autovalutazione
├── verifica.md         # criteri di padronanza, prova finale, piano di recupero
├── fonti.md            # fonti per livello, dibattiti aperti, incertezze dichiarate
└── meta.json           # metadati gestiti dal motore
```

### La cornice invariante

- **Rigore dichiarato.** Ogni affermazione porta la sua etichetta di affidabilità; le incertezze finiscono
  in *Da verificare*. Vietato inventare fonti, date, numeri o citazioni: se non si sa, si dice e si indica come verificare.
- **Divulgazione con dosatore.** Quattro livelli (curioso → principiante → studente → collega), dichiarati
  e modificabili in corsa.
- **Esempi concreti obbligatori.** Nessun concetto astratto senza un esempio verificabile a mano e un controesempio.
- **Verifica prima di procedere.** Micro-domande dopo ogni concetto, e un voto registrato: 0-2 lacuna
  (ripasso ravvicinato), 3 fragile, 4 solido, 5 lo sa spiegare.
- **Disponibile ma non complacente.** Niente "hai capito benissimo" senza prova, niente fatti piegati
  a quello che l'allievo spera di sentire.
- **Carico cognitivo controllato.** Massimo tre concetti nuovi per sessione, poi consolidamento.
- **Prerequisiti prima delle scorciatoie.** Se manca un prerequisito si crea la sua sotto-skill, invece di
  spiegarlo male in trenta secondi.

### Memoria e ripetizione spaziata

Ogni concetto verificato diventa un elemento da ripassare con **SM-2 semplificato** (intervalli 1 → 6 →
intervallo × fattore di facilità, con azzeramento dopo un voto basso). Il diario mostra minuti studiati,
voto medio per argomento, **lacune ricorrenti**, argomenti che stanno raffreddando (oltre 21 giorni) e
suggerimenti operativi.

---

## Riferimento dei comandi

Tutti i comandi si lanciano dalla cartella della skill. `--json` dove presente per output leggibile da un agente.

```bash
# ciclo rigenerante
python scripts/iv.py status                      # debiti, bozze, da rigenerare, ripassi di oggi
python scripts/iv.py find "<argomento>" [--json] # esiste già? → riusa / chiedi / genera
python scripts/iv.py create --title "…" --level 2 --mode esame --prereq "…" --tag "…" --alias "…"
python scripts/iv.py validate <slug> | --all [--json]
python scripts/iv.py register <slug> [--self-check "…"] [--force]
python scripts/iv.py list [--json]               # argomenti salvati
python scripts/iv.py show <slug>                 # file della sotto-skill + progressi
python scripts/iv.py style <slug> | --text "…" [--level 2]   # leggibilità (Gulpease) vs obiettivo del livello
python scripts/iv.py style --text "…" --registro bambino        # ...stringendo l'obiettivo: a chi stai parlando

# manutenzione del registro
python scripts/iv.py alias <slug> --add "nome alternativo" | --list
python scripts/iv.py merge <doppione> <slug-tenuto> [--learner nome]
python scripts/iv.py reindex                     # ricostruisce l'indice dai file su disco

# studio e ripasso
python scripts/iv.py log --topic <slug> --minutes 45 --summary "…" --module 2 \
      --concept "concetto" --grade 4 --concept "altro" --grade 1 --next "…" [--learner nome]
python scripts/iv.py due [--within 7] [--json]   # cosa ripassare adesso
python scripts/iv.py stats [--write] [--json]    # diario di apprendimento (Markdown)
python scripts/iv.py learner list | --json       # profili allievo con progressi e alias
python scripts/iv.py learner merge <da> --into <a>   # unisce due profili senza perdere storia
python scripts/iv.py learner rename <nome> --to "<nome corretto>"   # corregge un nome (lascia un alias)
python scripts/iv.py learner delete <nome> [--yes]   # senza --yes mostra solo l'anteprima
python scripts/iv.py learner persona --learner <nome>   # persona dichiarata: banda d'eta', tempi, scadenza
python scripts/iv.py learner persona --banda-eta ragazzo --configurato-da "il padre" \
      --budget-minuti 180 --scadenza 2026-12-15 --obiettivo "27/30"

# materiali dell'utente e lezioni (docenza)
python scripts/iv.py strumenti   # cosa c'e' su questa macchina per estrarre il testo da un PDF
python scripts/iv.py materiali add <slug> --file "<appunti.pdf>" --tipo appunti   # copia, non collega
python scripts/iv.py materiali list [<slug>] [--json]   # elenco e indice rigenerato
python scripts/iv.py materiali testo <slug> --material "<appunti.pdf>" --file "<trascrizione.md>" \
      --pagine "1-40" --mezzo testo|vista|ocr --campione "3 citazioni confrontate con l'originale"
python scripts/iv.py materiali search <slug> "<frase del materiale>" [--json]   # file, pagina, riga
python scripts/iv.py lezione <slug> --classe "3B" [--registro scolastico]   # crea la lezione
python scripts/iv.py lezione <slug> --check   # sezioni, sostanza minima, leggibilità
python scripts/iv.py learner persona --reset   # dimentica la persona: i progressi non si toccano
```

Opzioni globali: `--data <cartella>` (o variabile d'ambiente `IV_DATA`) per tenere i dati fuori dalla skill,
`--skill-dir <cartella>` per indicare dove sono template e reference.

---

## Struttura del repository

```
.
├── SKILL.md                  # orchestratore: avvio, riuso o generazione, insegnamento, chiusura
├── README.md / README.it.md  # questa documentazione
├── AGENTS.md                 # note per gli agenti che manterranno la skill
├── LICENSE                   # MIT
├── references/               # LA CORNICE (regole comuni, invarianti)
│   ├── costituzione.md
│   ├── protocollo-sessione.md
│   ├── contratto-output.md
│   ├── modalita.md
│   └── schema-sottoskill.md
├── scripts/iv.py             # motore: registro, ricerca, validazione, progressi, ripassi
├── assets/templates/topic/   # scheletro di una nuova sotto-skill
├── assets/templates/lezione/ # scheletro della lezione per una classe (docenza)
├── tests/test_iv.py          # 175 test del motore
└── data/
    ├── registry.json         # indice (rigenerabile, non versionato)
    ├── topics/<slug>/        # LE SOTTO-SKILL SALVATE
    │   └── metodo-feynman/   # esempio di riferimento completo e validato
    ├── materiali/<slug>/     # i tuoi materiali e le loro trascrizioni (non versionati)
    ├── lezioni/<slug>/       # lezioni preparate per una classe (non versionate)
    └── progress/<learner>/   # stato dell'allievo (non versionato)
```

### Esempio incluso

`data/topics/metodo-feynman/` è una sotto-skill completa e validata che serve da **standard di qualità**:
esempi verificabili a mano, controesempi, cinque misconcezioni smontate, sette esercizi autovalutabili,
incertezze dichiarate. Si può cancellare:

```bash
rm -rf data/topics/metodo-feynman && python scripts/iv.py reindex
```

---

## Estendere il sistema

- **Nuova regola pedagogica** → aggiungila a `references/costituzione.md`, incrementa `BASE_VERSION`
  in `scripts/iv.py`. Solo una **major** nuova mette gli argomenti esistenti in `da_rigenerare` (i contenuti
  vanno rifatti); una **minor** nuova li elenca in `cornice_aggiornabile` (arricchimento opzionale).
- **Nuova modalità** (corso aziendale, ripetizioni…) → `references/modalita.md` + la tupla `MODES` in `iv.py`.
- **Nuovo file di sotto-skill** (flashcard, mappe…) → template in `assets/templates/topic/`,
  `REQUIRED_FILES` in `iv.py`, sezione in `references/schema-sottoskill.md`.
- **Nuovo controllo di qualità** → `validate_topic()` in `iv.py`, con un test in `tests/test_iv.py`.
- **Nuovo campo nei metadati** → template `meta.json` + `REGISTRY_ENTRY_FIELDS` in `iv.py`.

### Test

```bash
python -m unittest discover -s tests -t tests
python scripts/iv.py validate --all     # salute delle sotto-skill + lint di prosa + leggibilità
```

---

## Roadmap

Le idee sono ordinate per rapporto fra valore e costo. *Stato: 💡 idea · 🔍 in esplorazione · 🛠 pianificato.*

### v0.2 — Esportazione dei risultati 🛠

Il patrimonio che si accumula (`data/`) oggi si legge solo da terminale. Obiettivo: portarlo fuori.

- `iv.py export --format md|json|csv|html` con `--topic`, `--learner`, `--output`.
  - **Markdown**: report di studio leggibile (per una sessione, per un argomento, per il mese).
  - **JSON**: esportazione completa e stabile, per integrazioni.
  - **CSV per Anki**: una riga per concetto tracciato (`fronte`, `retro`, `tag`, `scadenza`, `ease`),
    con **ID stabili** derivati dallo slug del concetto per non perdere lo storico dei ripassi a ogni reimport.
  - **HTML statico**: diario + elenco argomenti + roadmap di ripasso, pubblicabile su GitHub Pages
    senza alcun backend.
- `iv.py export --format pdf` tramite Pandoc, se installato (fallback: Markdown).
- Report "pagella": per ogni argomento, livello raggiunto, lacune aperte, tempo investito, prossimi passi.
- Backup/ripristino dell'intero `data/` in un singolo archivio (`iv.py backup --out studio.zip`).

### v0.3 — Interfaccia web 💡

Il salto di usabilità: studiare e rivedere senza passare dal terminale.
Approccio in due tempi, per non introdurre un backend finché non serve:

1. **Dashboard statica** (deriva da v0.2): pagine HTML generate dai dati, zero dipendenze, funziona offline
   e su GitHub Pages. Viste: diario, argomenti, concetti in scadenza, salute delle sotto-skill.
2. **App locale** (FastAPI o Flask + HTMX, sempre senza build step JS):
   - *Sessione guidata*: rende i moduli uno alla volta, con verifica e voti;
   - *Ripasso*: flashcard dai concetti tracciati, con i pulsanti di voto che aggiornano SM-2;
   - *Editor di argomento*: crea e modifica una sotto-skill con validazione in tempo reale;
   - *Diario*: grafici di tempo, lacune ricorrenti, argomenti che stanno raffreddando.
   Requisito di progetto: **local-first**, nessun account, i dati non escono dalla macchina.

### v0.4 — Argomenti più intelligenti 🔍

- **Ricerca semantica** accanto a quella lessicale (embedding locali), per riconoscere i doppioni
  anche quando le parole sono diverse.
- **Import del programma d'esame** (*parziale*): il programma si aggancia e si interroga già con
  `materiali`, ma il piano dei moduli si scrive ancora a mano. Manca: da un elenco di capitoli,
  generazione assistita del piano con revisione umana prima della validazione.
- **Sotto-skill figlie automatiche**: dai prerequisiti rilevati nel percorso, proposta di creazione a cascata.
- **Analisi delle lacune**: se lo stesso errore ricorre in argomenti diversi, proporre una sotto-skill trasversale.

### v0.5 — Integrazioni 💡

- **Server MCP**: esporre `iv.py` come strumenti MCP, così qualunque client compatibile può usare
  il sistema senza conoscere l'interfaccia a riga di comando.
- **Promemoria**: notifiche di ripasso via email o calendario (`.ics` esportabile già in v0.2).
- **RAG sui tuoi materiali** (*avviato*): `materiali testo` + `materiali search` cercano già dentro le
  trascrizioni, in locale e senza dipendenze; il controllo caratteri/pagina becca la copia troncata o
  riassunta; le estrazioni dello stesso documento (capitolo per capitolo, oppure con e senza `-layout`)
  **convivono** e si cercano tutte, così il flusso "un capitolo per volta" è possibile. Mancano: un flusso
  **guidato** per i documenti grandi (oggi è una sequenza che l'agente esegue a mano), una rilevanza che
  vada oltre la sovrapposizione lessicale, il riconoscimento di una parafrasi **della lunghezza giusta**, e
  un controllo automatico della **leggibilità dell'estratto** (un riquadro centrato finito in mezzo a una
  frase passa tutti i controlli: lo vede solo chi legge).
- **GitHub Action**: validazione automatica delle sotto-skill nelle pull request (`iv.py validate --all`),
  utile quando il repository diventa una libreria condivisa di percorsi.
- **Registro condiviso di argomenti**: importare/esportare singole sotto-skill da altri utenti,
  con merge dei progressi locali.
- **Hook di aggiornamento**: sessione guidata di rigenerazione quando cambia la cornice.

### Idee nel cassetto 💡

Internazionalizzazione della cornice (le reference sono in italiano), pacchetti pedagogici per disciplina
(matematica, lingue, diritto hanno bisogno di dosaggi diversi), quiz a correzione automatica con valutazione
delle risposte aperte, sintesi vocale per riascoltare una lezione, integrazione con Obsidian.

---

## Il repository: cosa versionare e come forkarlo

Il repository **è** la skill: tutto ciò che serve è già nella radice. Da versionare:

```
SKILL.md  README.md  README.it.md  AGENTS.md  LICENSE  .gitignore
references/  scripts/  assets/  tests/
data/topics/metodo-feynman/     # esempio di riferimento (opzionale)
```

Restano fuori (già in `.gitignore`): `data/progress/` (i tuoi progressi), `data/materiali/` (i materiali
che hai fornito e le loro trascrizioni: sono tuoi), `data/lezioni/` (lezioni scritte per una classe),
`data/registry.json` (rigenerabile: si ricostruisce al primo comando da `data/topics/*/meta.json`),
`data/_merged/`, `.agents/` (collegamento locale), `__pycache__/`.

```bash
git init
git add .
git status          # controlla che non compaia nulla di personale
git commit -m "Insegnante Virtuale: skill di studio rigenerante"
git branch -M main
git remote set-url origin https://github.com/<tuo-utente>/LearnUp.git   # oppure: git remote add origin ...
git push -u origin main
```

Con GitHub CLI, se crei un repository tutto tuo:
`gh repo create <tuo-utente>/LearnUp --public --source=. --push`.

Il repository di riferimento esiste già: **https://github.com/Dario-Fe/LearnUp**. Per un fork quindi
non serve `git init`: fai il fork su GitHub, clona il tuo fork e pusha lì. In quel caso sostituisci il
titolare del copyright in `LICENSE` con il tuo nome.

---

## Limiti da conoscere

- **Il "RAG" sui tuoi materiali non è affidabile al 100%, e non lo diventerà.** Non è una cautela
  generica: sono tre limiti precisi, ognuno verificabile da te.
  1. **Cerca solo ciò che è stato trascritto.** Un PDF che non contiene testo (una scansione, o una
     "stampa in PDF" fatta dal browser) non ha niente da estrarre: il motore lo rifiuta e il materiale
     resta non cercabile, dichiarato come tale. Lì serve un OCR o la lettura a vista.
  2. **La ricerca è lessicale**: i sinonimi e le riformulazioni non si trovano. Cercare «riduzione di
     precisione dei pesi» non trova il paragrafo che dice «quantizzazione».
  3. **La fedeltà della copia non è garantita dal motore**, che non legge i documenti. La controlla
     l'aritmetica (i caratteri per pagina beccano il troncamento e il riassunto grosso) e il controllo a
     campione (tre citazioni confrontate con l'originale, prima di citare). La **parafrasi della stessa
     lunghezza** non è distinguibile da una trascrizione con nessun controllo automatico: quella la vede
     solo chi legge. E l'ordine delle frasi può essere alterato dall'impaginazione del PDF.

  In pratica: ogni risultato porta **file, pagina e riga**, così vai a verificare invece di fidarti. Un
  "RAG" affidabile, qui, significa *verificabile* — non *infallibile*.
- **La validazione garantisce struttura e minimi, non la verità dei contenuti né la scrittura.** La qualità
  delle spiegazioni dipende dall'agente che le genera: per questo esistono le etichette di affidabilità,
  la sezione *Da verificare* in ogni sotto-skill e il passo di rilettura obbligatorio (il lint di prosa
  intercetta gli artefatti meccanici, non i refusi).
- **La ripetizione spaziata è SM-2 semplificato**, un solo elemento per concetto (niente card multiple).
- **Le sotto-skill vivono dentro la skill** e non sono skill di primo livello: così non inquinano il routing
  dell'agente con decine di descrizioni concorrenti. Si caricano leggendo il file per percorso.
- **La cornice è in italiano**: i contenuti generati seguono la lingua dell'allievo, ma le regole no
  (internazionalizzazione in roadmap).

---

## FAQ

**Come la attivo?** Basta chiedere: *"voglio studiare X"*, *"spiegami Y"*, *"prepariamo l'esame di Z"*,
*"ripassiamo"*. La skill si carica da sola in base alla sua descrizione. Se il client non la attiva,
richiamala esplicitamente: *"usa la skill insegnante-virtuale"*. Dopo averla installata, apri una chat nuova.

**Funziona in inglese?** Sì: le sotto-skill vengono scritte nella lingua dell'allievo. La cornice
(i file in `references/`) è in italiano.

**Ho aggiornato le regole: perdo i progressi?** No. I progressi vivono in `data/progress/`, separati dalla
conoscenza. Cambiando la **major** di `BASE_VERSION` gli argomenti vengono marcati `da_rigenerare` e si
riallineano; con una minor nuova restano usabili e compaiono in `cornice_aggiornabile`.

**Posso studiare in due?** Sì: `--learner <nome>` su `log`, `due` e `stats` mantiene profili separati.

**Devo tenere Python?** Serve al motore. Senza Python la skill perde ricerca affidabile, validazione e
ripetizione spaziata.

**Posso condividere i miei argomenti?** Sì: `data/topics/<slug>/` è autocontenuto. Copia la cartella,
lancia `python scripts/iv.py reindex` e l'argomento compare nel registro.

---

## Contribuire

Issue e pull request sono benvenute. Prima di aprire una PR:

1. `python -m unittest discover -s tests -t tests` (tutti verdi);
2. `python scripts/iv.py validate --all` (nessuna sotto-skill rotta);
3. se cambi la cornice, aggiorna `BASE_VERSION` e le reference coinvolte (major = contenuti da rifare,
   minor = aggiornamento opzionale).

Se aggiungi un esempio di argomento, fallo passare dal validatore: gli esempi incompleti non entrano.

Per chi mantiene la skill: `AGENTS.md` contiene architettura, invarianti, ricette operative, registro delle
decisioni e backlog tecnico.

## Licenza

MIT — vedi [LICENSE](LICENSE). La conoscenza che generi con il sistema resta tua.
