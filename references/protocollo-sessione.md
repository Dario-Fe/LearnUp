# Protocollo di sessione

Tutti i comandi si lanciano dalla cartella della skill (`insegnante-virtuale/`).
Sostituisci `<slug>` con lo slug reale, senza parentesi angolari.

## FASE 0 — Avvio (obbligatoria, in quest'ordine)

**0.1 Debiti tecnici.** Sempre, come primo comando della sessione:

```bash
python scripts/iv.py status
```

Se `bozze_da_completare` non è vuoto → completa quelle sotto-skill (FASE 1.B).
Se `da_rigenerare` non è vuoto → la cornice è cambiata in modo **incompatibile** (major): rigenera quei
topic prima di usarli. Se invece `cornice_aggiornabile` non è vuoto → cambiamenti **compatibili** (minor):
la sotto-skill si usa così com'è, e si arricchisce con le regole nuove alla prossima rigenerazione.
Se `ripassi_oggi > 0` → proponi 5 minuti di riscaldamento (FASE 2.C).

**0.2 Fissa il profilo allievo (una volta per persona).** I progressi vivono in `data/progress/<profilo>/`.
Prima guarda chi c'è già:

```bash
python scripts/iv.py learner list
```

| Cosa vedi | Cosa fai |
|---|---|
| Nessun profilo | **Primo avvio**: chiedi il nome (sotto), poi usalo |
| Un profilo | **Riusalo senza chiedere niente**: niente domanda, niente attrito |
| Più profili | Chiedi *per chi* stai studiando (l'allievo stesso o uno studente) e usa quello |

Al primo avvio chiedi il nome **nella stessa domanda** con cui chiedi l'argomento, e di' dove finisce:

> *"Prima di iniziare: come vuoi che ti chiami? Lo uso solo per tenere separati i tuoi progressi, e resta
> su questo computer — la cartella dei progressi non è versionata e non finisce nel repository.
> Se preferisci, resto anonimo."*

Poi passa **sempre** lo stesso nome con `--learner` su `log`, `due`, `stats`, `list`, `show`, `status`.
Se l'allievo resta anonimo, ometti `--learner` (vale `default`) e non richiederlo più nella sessione.

**Un nuovo allievo non si registra: nasce al primo `log`.** Per uno studente in più basta dichiararlo con
`--learner "Marco Rossi"`: il sistema crea la sua cartella, il suo diario separato, e riusa le stesse
sotto-skill (la conoscenza è condivisa, i progressi no). I nomi con spazi e accenti vanno bene; nomi con
`/`, `\` o `..` vengono rifiutati dal motore, perché diventerebbero percorsi.

Tre comandi per la manutenzione dei profili, tutti da usare **su richiesta dell'utente**:

```bash
python scripts/iv.py learner rename "Marco Rosi" --to "Marco Rossi"   # errore di battitura
python scripts/iv.py learner merge "Marco" --into "Marco Rossi"       # due profili, stessa persona
python scripts/iv.py learner delete "Marco Rossi" [--yes]             # senza --yes è solo un'anteprima
```

`rename` non unisce: se il nome di destinazione ha già dei progressi si ferma e propone `merge`. Entrambi
lasciano un **alias**, così le sessioni vecchie continuano a trovare il profilo. `delete` cancella sessioni,
voti, lacune e diario di quel profilo: **non proporlo mai per "pulizia"**, solo se l'utente lo chiede, e
mostra prima l'anteprima (senza `--yes` non modifica niente).

Due regole che evitano i guai visti sul campo:

- **Non inventare e non dedurre il nome** (cartella utente, email, hostname): un profilo sbagliato è peggio
  di uno anonimo.
- **Un nome, un profilo.** Se in futuro l'allievo si presenta con una variante (`Dario F.`, `Dario` con
  maiuscole diverse), non creare un secondo profilo: `learner list` te lo mostra e `iv.py learner merge`
  li unisce lasciando un alias. Se `status` dice che i progressi stanno in un altro profilo, **non**
  ripartire da zero: aggiungi quel `--learner`.

**0.2-bis Chiedi l'argomento.** Se l'utente non l'ha già detto, chiedi: *cosa vuoi studiare oggi?*
Se non sa da dove partire, mostra gli argomenti già avviati (`python scripts/iv.py list --learner <profilo>`)
e proponine la ripresa.

Nella stessa domanda raccogli, in modo naturale e non a questionario:

- **obiettivo**: capire / ripassare / preparare un esame / usarlo al lavoro
- **tempo**: quanto tempo ha adesso
- **livello**: da dove parte (vedi `contratto-output.md` per i livelli 1-4)
- **modalità**: autodidatta / esame / docenza (vedi `modalita.md`)

**0.3 Cerca prima di generare.** Mai creare una sotto-skill prima di questa ricerca:

```bash
python scripts/iv.py find "<argomento>"
```

Interpreta la risposta:

| `status` | Cosa fai |
|---|---|
| `exact` | **Riusa.** `python scripts/iv.py show <slug>`, leggi `topics/<slug>/SKILL.md` e riprendi dal progresso salvato |
| `draft_incompleto` | Esiste ma è una bozza: completala (FASE 1.B), registrala, poi insegna |
| `variant` | Molto simile a un esistente: chiedi all'utente *"intendi lo stesso argomento di X?"*. Se sì → `iv.py alias <slug> --add "<nuovo nome>"` e riusa. Se no → nuovo topic con `--prereq` verso l'esistente se è un approfondimento |
| `candidates` | Argomenti affini: proponi di riusare uno di quelli, oppure crea il nuovo e collegalo |
| `none` | **Genera** (FASE 1) |

Non saltare mai questo passaggio: è ciò che rende il sistema rigenerante invece che ripetitivo.

## FASE 1 — Generazione di una nuova sotto-skill

**1.1 Crea lo scheletro.**

```bash
python scripts/iv.py create --title "<Titolo leggibile>" --level <1-4> --mode <autodidatta|esame|docenza> --prereq "<prerequisito>"
```

**1.2 Gestisci i prerequisiti.** Per ogni prerequisito dichiarato, lancia `iv.py find "<prerequisito>"`.
Se manca e l'allievo non lo padroneggia, creane la sotto-skill (cascata massima: 2 livelli) e dillo all'utente.
Se l'allievo ha già il prerequisito, segnalo nel campo diagnosi e vai avanti.

**1.3 Compila i file.** Rispetta `schema-sottoskill.md`, che elenca per ogni file cosa deve contenere
e quali sono i minimi di sostanza. Scrivi contenuto vero: i template contengono commenti `ISTRUZIONI:`
che vanno **sostituiti**, non riempiti di frasi generiche.

**1.4 Valida e correggi.**

```bash
python scripts/iv.py validate <slug>
```

Il validatore blocca placeholder, sezioni mancanti, moduli senza obiettivo verificabile,
esercizi senza soluzioni, banche di errori troppo povere.

**1.4-bis Rileggi come un correttore di bozze.** Gli avvisi di prosa del validatore (caratteri non
latini, righe duplicate, markdown sbilanciato, parole straniere rimaste) sono solo una rete: **non è un
correttore di bozze e non lo diventerà**. Rileggi i file generati e sistema a mano:

- refusi e parole inventate; termini stranieri in mezzo alla prosa italiana;
- **terminologia coerente col glossario** (se il glossario dice «somma pesata», nessun file scrive «suma»);
- frasi interrotte, ripetizioni, riferimenti a sezioni che non esistono («vedi sotto»);
- ogni affermazione che il corso non sostiene con un esempio o con un'etichetta di rigore.

Correggi finché non passa e non resta nessun avviso.

**1.4-ter Misura la leggibilità.** Lo stile è una parte del contratto, non un gusto:

```bash
python scripts/iv.py style <slug>
```

Ogni file deve stare entro l'obiettivo del livello dichiarato (Gulpease, parole per frase, frasi oltre 30
parole: vedi la tabella in `contratto-output.md`). Se il comando segnala "frasi lunghe", **spezza le frasi**:
non riformulare con parole più semplici, non aggirare il numero. Un avviso di leggibilità si corregge, non
si accetta.

**1.5 Attiva.**

```bash
python scripts/iv.py register <slug> --self-check "<una riga: come hai verificato la qualità>"
```

**1.6 Annuncia in una riga.** All'utente interessa il percorso, non l'architettura:
*"Ho preparato il percorso su X con 4 moduli, partiamo dalle basi?"*

## FASE 2 — Insegnamento

**2.A Un modulo per volta**, con questa sequenza:

1. **Aggancio** — una domanda o un problema a cui l'allievo non sa ancora rispondere.
2. **Idea centrale** — 3-6 righe, linguaggio piano, nessun termine non definito.
3. **Esempio concreto** — verificabile, con numeri o oggetti reali.
4. **Perché funziona** — il meccanismo, non la ripetizione dell'esempio.
5. **Controesempio o errore tipico** — "questo è il punto in cui quasi tutti sbagliano".
6. **Micro-verifica** — 1-2 domande, poi **fermati e aspetta la risposta**.

**2.A-bis Se la spiegazione è densa, misurala prima di consegnarla.** Cioè quando introduce un meccanismo
con più passaggi, o spiega un concetto astratto, o temi di aver scritto "da manuale":

```bash
python scripts/iv.py style --text "<la spiegazione>" --level <1-4>
```

Se esce `1`, spezza le frasi lunghe e rimisura. Costa un comando, e rende la semplicità una cosa che si
controlla invece di una cosa che si spera: vale soprattutto per i modelli più piccoli, che compilano bene
la struttura ma tendono a scrivere denso.

**2.B Registra i voti di verifica appena li ottieni** (non a fine sessione, si perdono):

```bash
python scripts/iv.py log --topic <slug> --minutes 0 --concept "<concetto>" --grade <0-5> --learner <profilo>
```

Voto: 0-2 = non padroneggiato (finisce nelle lacune), 3 = fragile, 4 = solido, 5 = lo sa spiegare.
Un voto basso non è un fallimento: è la programmazione di un ripasso ravvicinato.

**`--concept` è un contenuto, non una tappa.** Va bene «somma pesata e ReLU», «previsione della parola
successiva»; non va bene «fine sessione», «avvio percorso», «moduli 1-3 completati»: quelli descrivono la
sessione e inquinano lacune e ripetizione spaziata (il motore li rifiuta). Cosa hai fatto e dove sei
arrivato si scrive in `--summary`, `--module` e `--next`.

**2.C Regola del riscaldamento.** Se `iv.py due` segnala concetti in scadenza, i primi 5 minuti
sono di ripasso (domande rapide, non rispiegazioni), poi si prosegue.

**2.D Se l'allievo non capisce due volte di fila:** cambia strada, non volume.
Tre mosse in ordine: (1) esempio più concreto, (2) scomposizione in passi più piccoli,
(3) risalita al prerequisito. Se serve il prerequisito → FASE 1.

## FASE 3 — Chiusura (mai saltata)

1. **Riassunto in 3 punti** + *"cosa sai fare adesso"*.
2. **Autoverifica**: 3 domande senza guardare gli appunti. Se una va male, dillo e programma il ripasso.
3. **Persistenza**:

```bash
python scripts/iv.py log --topic <slug> --minutes <N> --summary "<cosa è stato fatto>" \
  --module <M> --concept "<concetto>" --grade <0-5> --next "<prossimo passo>" --learner <profilo>
```

Il diario si riscrive da solo con questo comando (è un file derivato dai progressi).

4. **Comunica il ripasso**: *"Rivediamo Bayes tra 2 giorni"* (i tempi vengono da `iv.py log`).
5. **Se emergono lacune ricorrenti**: proponi di creare la sotto-skill di prerequisito.
6. Se vuoi vedere o salvare il diario a mano: `python scripts/iv.py stats --write --learner <profilo>`.

## Cosa non fare mai

- Insegnare senza aver lanciato `iv.py find` sull'argomento.
- Lasciare una sotto-skill in stato `draft` e usarla comunque.
- Chiudere una sessione senza `iv.py log`.
- Duplicare un argomento invece di aggiungere un alias o unire (`iv.py merge`).
- Promettere una ripetizione spaziata e non registrarla.
- Consegnare un modulo che `iv.py style` segnala fuori obiettivo, senza aver provato ad accorciare le frasi.
