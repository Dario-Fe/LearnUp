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
Se `piano` non è vuoto → l'allievo ha dichiarato una prova o un budget di tempo: il `prossimo_passo`
parla di quello, e va detto **subito**, prima dell'argomento (giorni che restano, moduli che mancano, se
la stima dice che ci sta).

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

**0.2-ter La persona: chi studia, con che tono, con quanto tempo.** Se il profilo non ha una persona
dichiarata, chiedila nello stesso momento in cui chiedi il nome, con la stessa leggerezza, e registrala:

```bash
python scripts/iv.py learner persona --learner "<nome>" \
      --banda-eta <bambino|ragazzo|adolescente|adulto> \
      --configurato-da "<chi imposta il profilo, se non è chi studia>" \
      --budget-minuti <minuti a settimana> \
      --scadenza <YYYY-MM-DD> [--obiettivo "27/30"]
```

Tre cose da dire e una da non fare:

- **Banda d'età, non data di nascita.** Serve a scegliere il registro, non a profilare nessuno.
- **Chi configura non è sempre chi studia.** Se un genitore prepara il profilo di un figlio, dichiaralo in
  `--configurato-da`; il profilo con i progressi resta di chi studia.
- **Si può saltare.** Senza persona il registro è `standard` e non cambia niente: non insistere.
- **Non dedurre la banda** da email, cartella utente o hostname (vale come per il nome).

Si cambia quando serve: `learner persona --banda-eta …` sovrascrive, `--reset` dimentica la persona senza
toccare i progressi.

Rileggi sempre i valori **calcolati**, invece di rifarli a mente:

```bash
python scripts/iv.py learner persona --learner "<nome>" --json   # registro_effettivo, livello_suggerito
```

`livello_suggerito` è da dove partire per un argomento **nuovo** (il `--level` di `create`): l'argomento
resta di tutti, la banda dice solo da dove è ragionevole cominciare.

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

**1.0 Chiedi se ha materiali — prima di scrivere.** *"Hai appunti, dispense, il programma del corso o
prove degli anni scorsi?"* Chiedilo **prima** di generare: se ha il programma, il corso si scrive guardando
quello, non a memoria. I file si agganciano però **dopo 1.1** (un materiale appartiene a un argomento, e
`materiali add` rifiuta uno slug che non esiste).

**1.1 Crea lo scheletro.**

```bash
python scripts/iv.py create --title "<Titolo leggibile>" --level <1-4> --mode <autodidatta|esame|docenza> --prereq "<prerequisito>"
```

**1.1-bis Aggiungi i materiali dell'utente, se ne ha.**

```bash
python scripts/iv.py materiali add <slug> --file "<file>" --tipo appunti|programma|prova|libro
python scripts/iv.py materiali list <slug>
```

Il motore **copia** il file in `data/materiali/<slug>/` e ne tiene l'indice (rigenerato a ogni `list`):
non è un collegamento, quindi se l'originale sparisce il materiale del corso resta. I materiali non sono
versionati — sono dell'utente.

Il contenuto che scrivi **si allinea a quel materiale**, e `fonti.md` lo cita come *materiale fornito
dall'utente*. Se è un PDF lo leggi tu: il motore non ha dipendenze per aprirlo, e non deve averne. Un
argomento con materiali nella lista (`iv.py list`, colonna *Materiali*) si rigenera guardando quelli.

**1.1-ter Trascrivi in testo ciò che ha letto, se ha senso.** Un materiale senza testo resta visibile a te
ma invisibile al motore: non lo si può cercare. Prima di trascrivere, **chiedi alla macchina cosa sa fare**:

```bash
python scripts/iv.py strumenti
```

Il payload dice se su **questa** macchina esiste un estrattore (`pdftotext`, `pypdf`, `pymupdf`) e quindi
se il testo si può **copiare** invece di leggerlo. Il motore li rileva e non li esegue mai: l'estrazione
resta a te. Due conseguenze operative:

- **Se la copia meccanica è possibile, usala, ma scegli il comando guardando l'estratto.** Nessuno dei
  due va bene sempre, e la differenza si vede solo leggendo:
  - `pdftotext -layout -enc UTF-8` conserva elenchi e tabelle, ma fa **entrare i riquadri centrati in
    mezzo alle frasi**: visto sul campo, il titolo centrato di un riquadro finisce dentro un periodo, che
    diventa «L'iscrizione si completa online e sarà confermata **MODULO A — DATI PERSONALI** al
    ricevimento del pagamento». Le parole ci sono tutte, l'ordine no, e il periodo dice una cosa che nel
    documento non esiste;
  - `pdftotext -enc UTF-8` legge in ordine di flusso: frasi intere, ma elenchi fusi in una riga e
    citazioni più grosse (una pagina intera invece di un paragrafo).

  **Apri l'estratto e guarda i primi righi**: se vedi un titolo, un numero di pagina o un riquadro in
  mezzo a una frase, rifai senza `-layout` e tieni la versione che si legge meglio. È una decisione che si
  prende guardando, non ragionando, e in dieci secondi. Il flag `-enc UTF-8` non è opzionale in nessuno
  dei due: senza, `pdftotext` scrive Latin-1 e il motore **rifiuta** il file, perché gli accenti rotti
  renderebbero illeggibile la fonte. Dichiara `--mezzo testo`: è una copia, non una lettura.

  Se servono entrambe le estrazioni (le tabelle da una, l'ordine di lettura dall'altra), collegatele con
  **nomi diversi**: restano due trascrizioni dello stesso materiale, la ricerca le interroga tutte e il
  risultato dice da quale viene. Con lo stesso nome, la seconda **sostituisce** la prima: è un
  aggiornamento legittimo, e il payload lo dichiara (`sostituito: true`).
- **Se non è possibile**, il testo lo produce la tua lettura del PDF: dichiara `--mezzo vista` (o `ocr`) e
  il **controllo a campione diventa obbligatorio**, non consigliato.

Poi salva la trascrizione e collegalala:

```bash
python scripts/iv.py materiali testo <slug> --material "<programma.pdf>" --file "<trascrizione.md>" \
    --pagine "1-40" --mezzo testo|vista|ocr --campione "<esito del controllo a campione>"
python scripts/iv.py materiali search <slug> "<una frase del materiale>"
```

Da lì in poi `materiali search` risponde con **file, pagina e riga**: è così che citi una fonte precisa
invece di dire «nel tuo PDF». Quattro regole, perché questa è la parte dove si può mentire senza
accorgersene:

- **Trascrivi, non riassumere.** Il testo collegato è una fonte citabile: una parafrasi spacciata per
  trascrizione è una fonte inventata (invariante #15). Se hai riassunto, dillo in `fonti.md`.
- **Non trascrivere in blocco ciò che non potevi leggere.** Il motore rifiuta sopra ~400.000 caratteri
  (circa 250 pagine): quel rifiuto è la regola in forma eseguibile. Per un manuale si estrae **un capitolo
  per volta**, si collega con `--pagine` e si dichiara in `fonti.md` **cosa non è stato letto**. Ogni
  capitolo è una trascrizione a sé — il nome lo dà il file di origine, quindi da `capitolo-1.txt` e
  `capitolo-2.txt` nascono due copie che convivono — ma solo se non riusi lo stesso nome.
- **Dichiara sempre `--pagine`.** È l'unica prova disponibile che la copia sia completa: il motore
  calcola i caratteri per pagina e **rifiuta** se sono sotto 250 (testo troncato o riassunto: 500 caratteri
  dichiarati come 12 pagine sono un indice, non una trascrizione). Sopra 6.000 avvisa che le pagine
  dichiarate sono sbagliate. Senza `--pagine` il controllo non può essere fatto, e il motore lo dice nel
  payload: il silenzio su questo punto è la cosa da non accettare.
- **Dichiara come hai ottenuto il testo (`--mezzo`) e verificalo a campione (`--campione`).** `testo` (copiato
  da un PDF con testo), `vista` (letto a schermo), `ocr`. Nessun codice può distinguere una trascrizione da
  una parafrasi: quei due campi rendono visibile **quanto ci si sta fidando** invece di doverlo ricordare,
  e `list`, `INDICE.md` e ogni risultato di ricerca li riportano. Un risultato marcato *non verificata* è
  una fonte da controllare **prima** di citarla all'allievo.

**Controllo a campione, prima di trattare la trascrizione come fonte** (se il documento non è una paginetta
di testo selezionabile): apri l'originale e confronta **almeno tre citazioni** prese a caso — non le prime
righe, che sono le più facili — con la pagina corrispondente. Se anche una sola non combacia, la
trascrizione non è una fonte: rifalla, oppure dillo in `fonti.md` e nella *sezione Da verificare*. Poi
registra l'esito in `--campione`. Il costo è di due minuti; il costo di una citazione sbagliata è una
bocciatura su una domanda che non esiste (vedi l'esempio della *banca* in `contratto-output.md`).
- **La ricerca è lessicale.** Non trova sinonimi né riformulazioni. Un risultato vuoto significa «non c'è
  quella parola», *non* «non c'è quel concetto»: `materiali_senza_testo` e le pagine non lette vanno
  guardate prima di concludere che il materiale non parla di qualcosa.

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

**2.0 Prima di parlare: scegli il registro.** Il tono non si improvvisa sessione per sessione. Leggi
`registro_effettivo` dalla persona (precedenza: sessione > persona > banda d'età > `standard`) e, per i moduli
in cui spieghi, misura la bozza prima di consegnarla:

```bash
python scripts/iv.py style --text "<la spiegazione>" --registro <standard|scolastico|bambino>
```

Esce `1` se è fuori obiettivo: allora **spezza le frasi**, non rispedire lo stesso testo. È l'unico modo per
misurare la lezione in chat, cioè la superficie che `validate` e `style <slug>` non vedono. Regole complete
(esempi adeguati all'età, temi delicati) in `contratto-output.md`.

**In modalità docenza** serve anche l'artefatto da portare in aula, prima di spiegare:

```bash
python scripts/iv.py lezione <slug> --classe "3B" --registro scolastico
# compili il file al posto dei blocchi ISTRUZIONI, poi:
python scripts/iv.py lezione <slug> --check
```

`--check` esce `1` finché restano sezioni vuote, placeholder, `ISTRUZIONI:` o meno di tre domande
probabili: una lezione scheletro non si porta in classe. A fine sessione,
`log --topic <slug> --minutes N --lesson "<file>"` lega la lezione consegnata al diario.

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
