# Protocollo di sessione

Tutti i comandi si lanciano dalla cartella della skill (`insegnante-virtuale/`).
Sostituisci `<slug>` con lo slug reale, senza parentesi angolari.

## FASE 0 — Avvio (obbligatoria, in quest'ordine)

**0.1 Debiti tecnici.** Sempre, come primo comando della sessione:

```bash
python scripts/iv.py status
```

Se `bozze_da_completare` non è vuoto → completa quelle sotto-skill (FASE 1.B).
Se `da_rigenerare` non è vuoto → cornice aggiornata: rigenera quei topic prima di usarli.
Se `ripassi_oggi > 0` → proponi 5 minuti di riscaldamento (FASE 2.C).

**0.2 Chiedi l'argomento.** Se l'utente non l'ha già detto, chiedi: *cosa vuoi studiare oggi?*
Se non sa da dove partire, mostra gli argomenti già avviati (`python scripts/iv.py list`) e proponine la ripresa.

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
esercizi senza soluzioni, banche di errori troppo povere. Correggi finché non passa.

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

**2.B Registra i voti di verifica appena li ottieni** (non a fine sessione, si perdono):

```bash
python scripts/iv.py log --topic <slug> --minutes 0 --concept "<concetto>" --grade <0-5>
```

Voto: 0-2 = non padroneggiato (finisce nelle lacune), 3 = fragile, 4 = solido, 5 = lo sa spiegare.
Un voto basso non è un fallimento: è la programmazione di un ripasso ravvicinato.

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
  --module <M> --concept "<concetto>" --grade <0-5> --next "<prossimo passo>"
```

4. **Comunica il ripasso**: *"Rivediamo Bayes tra 2 giorni"* (i tempi vengono da `iv.py log`).
5. **Se emergono lacune ricorrenti**: proponi di creare la sotto-skill di prerequisito.
6. Il diario si aggiorna con `python scripts/iv.py stats --write`.

## Cosa non fare mai

- Insegnare senza aver lanciato `iv.py find` sull'argomento.
- Lasciare una sotto-skill in stato `draft` e usarla comunque.
- Chiudere una sessione senza `iv.py log`.
- Duplicare un argomento invece di aggiungere un alias o unire (`iv.py merge`).
- Promettere una ripetizione spaziata e non registrarla.
