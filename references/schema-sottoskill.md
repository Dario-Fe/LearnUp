# Schema di una sotto-skill

Come si scrive una sotto-skill che passi `iv.py validate` e che sia davvero utile.
La fonte di verità formale è `scripts/iv.py` (funzione `validate_topic`): questa pagina la spiega e la estende.

## Dove vive

```
data/topics/<slug>/
├── SKILL.md           # frontmatter + contratto + mappa + come condurre la sessione
├── meta.json          # metadati usati dal registro (non scriverlo a mano: lo gestisce iv.py)
├── percorso.md        # i moduli: il cuore didattico
├── glossario.md       # termini minimi
├── errori-tipici.md   # misconcezioni (la sezione più preziosa)
├── esercizi.md        # esercizi con soluzioni nascoste e criteri di autovalutazione
├── verifica.md        # criteri di padronanza + prova finale
└── fonti.md           # fonti per livello + incertezze dichiarate
```

Lo scheletro lo crea `iv.py create`: non inventare mai la struttura a mano.

## Requisiti bloccanti (il validatore rifiuta)

| File | Minimo richiesto |
|---|---|
| `SKILL.md` | frontmatter con `name: iv-<slug>` e `description:`; sezioni **Contratto didattico**, **Mappa del corso**, **Come condurre una sessione su questo argomento** |
| `percorso.md` | ≥ 3 moduli (`## Modulo N`), ognuno con **Obiettivo verificabile** non vuoto, `### Esempio concreto`, `### Controesempio` |
| `errori-tipici.md` | ≥ 4 voci (`## 1.`, `## 2.`, …) |
| `glossario.md` | ≥ 6 voci in tabella |
| `esercizi.md` | ≥ 6 esercizi (`### Esercizio …`), ognuno con soluzione in `<details>` e criteri *Come valutarti* |
| `verifica.md` | sezioni **Criteri di padronanza** e **Prova finale**, ≥ 6 voci |
| `fonti.md` | sezione **Da verificare** |
| Tutti | nessun placeholder del template ancora presente, nessun commento `ISTRUZIONI:` residuo |

## Qualità, non solo conformità

**`percorso.md` — i moduli.** Ogni modulo è un gradino verificabile, non un capitolo di libro.

- L'obiettivo si scrive al futuro e in termini di prestazione: *"saprai calcolare il tempo di caduta di un corpo"*, non *"capirai la cinematica"*.
- L'**esempio concreto** deve essere risolvibile a mano, con numeri tondi e un contesto riconoscibile.
- Il **controesempio** deve mostrare dove l'idea smette di valere, non essere un secondo esempio.
- I collegamenti *Serve prima / Serve dopo* costruiscono il grafo dei prerequisiti, e sono ciò che permette di creare sotto-skill collegate.

**`errori-tipici.md` — la banca delle misconcezioni.** Formula la voce come la direbbe l'allievo
(errori plausibili, non errori stupidi). Per ognuna servono: perché è allettante, cosa c'è di sbagliato,
la correzione in una riga, il test che la smaschera. Almeno 4 voci, e almeno una per modulo.

**`glossario.md`** — solo termini che l'allievo *deve* conoscere. Definizione in una frase, senza usare
la parola stessa. Aggiungi anche i "termini da non usare" (ambigui o sbagliati nel contesto).

**`esercizi.md`** — difficoltà crescente (base → intermedio → avanzato → trasferimento).
La soluzione contiene sempre i criteri di autovalutazione: *"la tua risposta è giusta se contiene A e B,
anche se la forma è diversa"*. Un esercizio senza criteri è inutile in autovalutazione.

**`verifica.md`** — la prova finale mescola: definizioni operative (non mnemoniche), applicazioni,
domande "spiega come a un principiante" (test Feynman), riconoscimento di un errore tipico,
un problema di trasferimento. In modalità `esame` aggiungi tempo, punteggio, soglia e piano di recupero.

**`fonti.md`** — se non sei sicuro che una fonte esista, descrivi la *categoria* da cercare
("un manuale introduttivo di X, capitolo sulle Y") invece di inventare titoli, autori o URL.
Le incertezze vanno nella sezione **Da verificare**: è ciò che rende la sotto-skill onesta e rigenerabile.

**`SKILL.md` della sotto-skill** — non è una copia della cornice: dice **come** si insegna *questo* argomento.
Da dove partire, quale modulo non saltare mai, dove l'allievo si blocca, quali esempi funzionano.

## Esempio di modulo: cattivo vs buono

Cattivo:

> ### Idea centrale
> La derivata rappresenta il tasso di variazione istantaneo di una funzione rispetto alla sua variabile.

Buono:

> ### Idea centrale
> La derivata risponde a una domanda pratica: **di quanto sta cambiando qualcosa, proprio adesso?**
> Se stai guidando a 90 km/h, il tachimetro non ti dice dove sei, ma quanto velocemente stai cambiando posizione
> in questo istante. La derivata è il tachimetro di una funzione.
>
> ### Esempio concreto
> Un'auto percorre $s(t) = 5t^2$ metri in $t$ secondi. In 2 secondi percorre 20 m, in 2,1 secondi 22,05 m:
> in quel decimo di secondo ha fatto 2,05 m, cioè 20,5 m/s di media. Restringendo l'intervallo a un centesimo
> di secondo la media si avvicina a 20 m/s: quello è il valore della derivata in $t = 2$.
>
> ### Controesempio
> "La derivata è sempre positiva dove la funzione cresce": vero per funzioni derivabili, falso per $|x|$ in 0,
> dove la funzione cresce ma non esiste un tachimetro: la derivata non c'è.

Lo stesso contenuto, ma il secondo si può verificare a mano, non richiede di credere a nulla e finisce
con un confine esplicito.

## Procedura di generazione (in ordine)

1. `iv.py create --title "…" --level N --mode … [--prereq "…"]`
2. Compila `percorso.md` (i moduli sono la struttura: senza quelli gli altri file non si possono scrivere bene).
3. Compila `errori-tipici.md` e `glossario.md` (derivano dai moduli).
4. Compila `esercizi.md` e `verifica.md`.
5. Compila `fonti.md`, poi `SKILL.md` della sotto-skill (riusa ciò che hai già scritto: modalità di conduzione, dove ci si blocca).
6. `iv.py validate <slug>` → correggi tutto ciò che esce come `ERRORE`.
7. `iv.py register <slug> --self-check "…"`.

### Autocheck prima di registrare

- [ ] Ogni modulo ha un obiettivo verificabile con un esercizio corrispondente.
- [ ] Nessun prerequisito citato senza che esista una sotto-skill o una diagnosi che lo escluda.
- [ ] Ogni termine usato nei moduli è nel glossario o è spiegato al primo uso.
- [ ] Nessuna fonte inventata; ogni incertezza è in **Da verificare**.
- [ ] Il livello dichiarato nel frontmatter corrisponde al registro linguistico dei contenuti.
- [ ] Niente frasi generiche ("è molto importante capire bene questo concetto").

## Rigenerazione (il ciclo "rigenerante")

Quando la cornice cambia (`BASE_VERSION` in `scripts/iv.py`), `iv.py status` segnala i topic
`da_rigenerare`. Per riallinearne uno:

1. Rileggi `costituzione.md` e `contratto-output.md`;
2. correggi la sotto-skill dove contraddice la cornice (spesso: etichette di affidabilità, struttura dei moduli, criteri di autovalutazione);
3. `iv.py register <slug> --self-check "riallineata alla cornice vX"`.

**I progressi dell'allievo non si toccano mai**: vivono in `data/progress/`, separati dalla conoscenza.

## Unire invece di duplicare

Se due argomenti si rivelano lo stesso (o uno è un sottoinsieme dell'altro):

```bash
python scripts/iv.py alias <slug> --add "nome alternativo"   # stesso argomento, altro nome
python scripts/iv.py merge <slug-doppione> <slug-tenuto>     # unisci davvero (progressi inclusi)
python scripts/iv.py reindex                                 # ricostruisci l'indice dai file
```
