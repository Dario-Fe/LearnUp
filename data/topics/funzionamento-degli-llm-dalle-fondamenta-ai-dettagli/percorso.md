# Percorso: funzionamento degli LLM — dalle fondamenta ai dettagli

## Prerequisiti e diagnosi rapida

| Prerequisito | Sotto-skill esistente | Domanda di diagnosi |
|---|---|---|
| Pensare in termini di tabelle: righe, colonne, indici | nessuna (competenza di programmazione) | *Hai una lista di 5 numeri. Come selezioneresti solo il secondo e l'ultimo?* |
| Grafico cartesiano: asse x, asse y, punto (x, y), retta | nessuna (competenza scolastica) | *Se y = 2x + 1, quale è il valore di y quando x = 3? Sai disegnare quel punto?* |
| Media semplice e concetto di "errore" come distanza | nessuna | *Hai i voti 18, 24, 21. Qual è la media? Che cosa vuol dire che uno devia dalla media?* |
| Concetto base di "modello" come funzione input→output | parziale | *Per te un modello di machine learning è una formula che prende dei dati in uscita e dà un numero in output. Ti suona come qualcosa che sai descrivere?* |

Il modulo 3 legge un grafico cartesiano e calcola a mano una somma pesata: se le diagnosi 2 e 3
non reggono, dedica 15 minuti a ripassare grafici e media prima di iniziare. La matematica richiesta
è aritmetica, algebra di base e lettura di grafici — **non** calculus né algebra lineare. Tutto ciò
che serve lo spiego qui.

## Come è fatto questo percorso

| Modulo | Titolo | Tempo stimato | Dipende da |
|---|---|---|---|
| 1 | Da "cerca la parola vicina" a "predice la parola successiva" | 35 min | — |
| 2 | Token, embedding e lo spazio dei significati | 35 min | Modulo 1 |
| 3 | Il layer: pesi, somme ponderate e funzione di attivazione | 40 min | Modulo 2 |
| 4 | Il transformer: attention, perché separa le parole e come le ricombina | 45 min | Moduli 2, 3 |
| 5 | Da un vettore a una distribuzione: generazione, temperatura e limiti | 35 min | Moduli 3, 4 |

Ritmo consigliato: un modulo al giorno (5 giorni), con i primi 5 minuti di ogni giornata dedicati al
ripasso del giorno precedente. Ogni modulo termina con una micro-verifica: la risposta è parte della
lezione, non un test da finire in fondo alla pagina.

Nota per il docente: questo percorso è costruito come una piramide, non come una lista. Ogni modulo
si appoggia al precedente senza eccezioni. Il modulo 4 (attention) è quello dove gli studenti si
blocca più spesso: se un allievo non padroneggia il modulo 3 (un layer "come una somma pesata"),
il modulo 4 non entrerà. In quel caso si riparte dal modulo 3, non si salta.

---

## Modulo 1 — Da "cerca la parola vicina" a "predice la parola successiva"

**Obiettivo verificabile:** saprai spiegare a voce, in un minuto, la differenza fra un motore di
ricerca che *cerca* parole e un LLM che *predice* la parola successiva, e saprai predire a mano
qual è la parola più probabile che segue una frase corta.

### Idea centrale

Un motore di ricerca funziona per *ricerca*: tu digiti parole, lui trova pagine che contengono quelle
parole. Non "capisce", associa. Un LLM (Large Language Model) funziona in modo radicalmente diverso:
non cerca, **predice**. Impara **una sola regola** — data una sequenza di parole, qual è la più
probabile che viene dopo? — e la applica parola per parola: ne produce una, la aggiunge alla sequenza,
ripete. Da questa catena di previsioni molto semplici nasce tutto il resto.

### Esempio concreto

Frase: *"Il caffè era così forte che di notte non riuscivo a…"*.

Cosa fa un motore di ricerca: cerca pagine che contengono "caffè forte insonnia" e te le mostra.
Cosa fa l'LLM: stima "dato questo contesto, le parole più probabili per chiudere sono *dormire*
(60%), *dormitare* (15%), *riposare* (10%)". Sceglie *dormire*, l'aggiunge, e continua: *"di notte
non riuscivo a dormire perché…"* → stima *rimuginavo*, e così via.

Il modello non "sa" cos'è il caffè né perché lo si beve. Ha visto miliardi di frasi simili e ha
imparato una distribuzione di probabilità sulle parole seguenti. La forza — e il limite — di tutto il
resto del corso sta qui: **non rappresenta il mondo, rappresenta la probabilità delle parole**.

### Perché funziona

La lingua ha una struttura ripetibile: certe parole "attirano" le altre secondo regole statistiche
molto stabili. Se un modello è abbastanza grande da memorizzare quelle regolarità su dati enormi,
predire la parola seguente produce testi che *sembrano* capire. È una distinzione importante che
tornerà spesso: **comportarsi come se capisse** non è la stessa cosa di **avere un modello del mondo**.

### Controesempio

"Un LLM è come un motore di ricerca potenziato" è l'errore più comune, ed è falso in modo rilevante.
Google può trovarti 10.000 pagine sul caffè ma non sa completare la frase "il contrario del fuoco è…".
Invertendo i ruoli: se chiedi a un LLM "fammi fonti sull'insonnia da troppo caffè", lui *genera* testo
(plausibile, ma potenzialmente inventato) invece di *recuperare* fonti reali. La ricerca recupera, la
generazione produce. Confonderle porta a fidarsi ciecamente di un LLM che cita fonti inesistenti.

### Domande di verifica

1. "Il lato positivo dell'intelligenza artificiale è che…" — qual è la parola più probabile? Perché?
2. Se un LLM produce testo plausibile, come fai a capire se sta *capendo* o *statisticamente combinando*?

### Collegamenti

- Serve prima: nessuno.
- Serve dopo: Modulo 2 (come rappresenta il modello "le parole" per poterle prevedere).

---

## Modulo 2 — Token, embedding e lo spazio dei significati

**Obiettivo verificabile:** saprai trasformare una frase in token, spiegare perché un modello non
lavora su parole ma su vettori di numeri, e descrivere cosa significa "due concetti sono vicini
nello spazio degli embedding" con un esempio che si può disegnare.

### Idea centrale

Un LLM non legge "parole": legge numeri. La prima trasformazione è il **tokenizzatore**, che spezza
il testo in pezzi (token) — spesso parti di parola, a volte parole intere, a volte punteggiatura.
Poi un **embedding** trasforma ogni token in una lista di numeri (un vettore). Immagina un vettore
come una riga di una tabella con molte colonne numeriche: è l'unico "linguaggio" che una rete
neurale può manipolare. Il trucco è tutto qui: vettori con significato simile finiscono *vicini* in
quello che si chiama **spazio degli embedding**.

### Esempio concreto

Frase: *"Il gatto dorme sul divano."*

1. **Tokenizzazione** (esempio semplificato): `["Il", " gatto", " dorme", " sul", " divano", "."]`.
   Nota: " gatto" ha uno spazio all'inizio perché il tokenizzatore separa gli spazi — nel linguaggio
   reale i token sono spesso frammenti. Una parola come "impossibile" potrebbe diventare
   `["im", "poss", "ibile"]`.
2. **Embedding**: ogni token diventa, diciamo, una riga di 256 numeri (i modelli reali usano da
   qualche centinaio a più di diecimila colonne). Il token "re" non è `"1, 5, 3, …"` a caso: è
   posizionato nello spazio vicino a "regina", "corona", "regno", e lontano da "pizza", "cucina",
   "forchetta".
3. **Relazioni:** la posizione di un vettore codifica *relazioni*, non solo somiglianze. Un esempio
   classico: `embedding("re") − embedding("uomo") + embedding("donna") ≈ embedding("regina")`. La
   direzione che porta da "uomo" a "donna" porta anche da "re" a "regina". Nessuno glielo ha
   insegnato: lo ha ricavato dalla statistica del testo.

Disegnato a mano: metti "gatto" e "cane" vicini, "pizza" lontano, "re" vicino a "regina". Lo spazio
degli embedding è proprio questo: una mappa concettuale che il modello ha *imparato*, non disegnata
da un umano.

### Perché funziona

Un numero da solo non significa nulla, ma una *posizione* in uno spazio multidimensionale sì.
Durante l'allenamento il modello aggiusta quegli numeri finché non riesce a prevedere le parole
successive: il processo di conseguenza *organizza* lo spazio in modo che concetti correlati (stesso
tema, stessa grammatica, stessa parola) finiscano vicini. È l'unico modo in cui una rete può "pensare"
parole senza averle mai viste insieme.

### Controesempio

"Pensare che ogni parola abbia un embedding con una colonna = un significato preciso" è falso. Un
vettore non ha significati separati, ha una *posizione* che codifica milioni di relazioni in modo
distribuito: nessuno dice "questa colonna vale 'gatto'". E c'è un limite pratico che tornerà nel
modulo 4: l'embedding di una parola è *ambiguo* ("bank" = banca del fiume o banco? "bank" cambia
significato nel contesto). Serviranno altri meccanismi per risolvere l'ambiguità.

### Domande di verifica

1. Perché il tokenizzatore divide "impossibile" in pezzi invece di tenerlo intero?
2. Se "cane" è vicino a "cucciolo" e lontano da "macchina", cosa ci dice sulla qualità dello spazio?

### Collegamenti

- Serve prima: Modulo 1 (serve prevedere parole per capire come vengono rappresentate).
- Serve dopo: Modulo 3 (come quella tabella di numeri viene trasformata dentro il layer).

---

## Modulo 3 — Il layer: pesi, somme ponderate e funzione di attivazione

**Obiettivo verificabile:** saprai descrivere un singolo "layer" (strato) di rete come una somma
ponderata di input seguita da una funzione non lineare, calcolare una piccola somma pesata a mano, e
spiegare perché serve la non linearità.

### Idea centrale

Tutto ciò che fa una rete neurale, in fondo, è **sommare**. Prende i numeri in ingresso (i token, o i
risultati di uno strato precedente), moltiplica ciascuno per un *peso* (un numero che dice "quanto
conta"), li somma, aggiunge un *bias*, e infine applica una **funzione di attivazione** che decide se
quel calcolo "si accende" o meno. Un layer è quindi: `uscita = attivazione(pesi · input + bias)`.
Impilare molti layer — ognuno riceve in ingresso l'uscita del precedente — è ciò che forma la rete.

### Esempio concreto

Immagina un layer che deve decidere se un testo parla di "sport", dati tre input numerici:
`[presenza_parole_sport, presenza_parole_cucina, presenza_parole_finanza]`.

Diciamo che il layer usa questi pesi: `[0.9, −0.2, −0.1]` (molto peso allo sport, poco — e con segno
negativo — a cucina e finanza) e bias `−0.5`.

Somma pesata = `0.9·input1 + (−0.2)·input2 + (−0.1)·input3 + (−0.5)`.

Se il testo è `input = [1, 0, 0]` (parla solo di sport): somma = `0.9·1 − 0 − 0 − 0.5 = 0.4`.
Se il testo è `input = [0, 1, 0]` (parla solo di cucina): somma = `−0.2 − 0.5 = −0.7`.

La somma pesata dà 0.4 per lo sport e −0.7 per la cucina: il layer "preferisce" lo sport.

### Perché funziona

La somma ponderata è un modo per *pesare le prove*: ogni input contribuisce alla decisione in misura
determinata dal suo peso. Durante l'allenamento il modello non inventa i pesi: li regola con il
**gradiente**, cioè correggendoli in proporzione all'errore. Qui lo nomino soltanto: *come* si allena
un modello è un altro argomento. Il meccanismo è semplicissimo, ma impilandone molti si costruisce
qualcosa di potentissimo.

La **funzione di attivazione** entra perché le somme pure sono troppo semplici: comporre più somme
dà ancora una somma, quindi una rete di soli strati lineari equivale a un unico strato lineare, che
in due dimensioni traccia solo confini dritti. Applicando una funzione non lineare
(diciamo: "se il risultato > 0, usa quel valore; altrimenti usa 0" — è la funzione ReLU) la rete
può piegare lo spazio e separare cose che una retta sola non separerebbe. **Senza non linearità,
centinaia di layer equivalgono a uno solo.**

### Controesempio

"Più layer = sempre meglio, tanto vale sommare di più" è falso. Una rete di soli strati lineari è
matematicamente identica a un solo strato lineare: la potenza arriva *dalla non linearità fra uno
strato e l'altro*, non dal numero di strati. Altro errore: credere che un peso "alto" significhi
sempre "importante". L'effetto di un peso dipende anche dal segno dell'input: con un input negativo
un peso positivo *abbassa* il risultato. Il modello usa pesi negativi per smorzare i segnali che
disturbano la previsione.

### Domande di verifica

1. Calcola a mano: pesi `[2, 0.5]`, bias `1`, input `[3, 4]`. Qual è la somma pesata?
2. Perché non basta impilare somme pesate senza funzione di attivazione?

### Collegamenti

- Serve prima: Modulo 2 (i layer lavorano sui numeri degli embedding).
- Serve dopo: Modulo 4 (i layer si impacchettano in blocchi chiamati "transformer").

---

## Modulo 4 — Il transformer: attention, perché separa le parole e come le ricombina

**Obiettivo verificabile:** saprai spiegare cos'è l'attention e perché è l'invenzione che ha reso
possibili gli LLM moderni, descrivere query/key/value con un esempio, e identificare dove un modello
"guarda" quando interpreta una frase ambigua.

### Idea centrale

Quando leggi "il gatto **lo** ha pulito", come fai a capire che "lo" si riferisce al gatto e non a
qualcos'altro? I modelli precedenti leggevano il testo una parola per volta, da sinistra a destra:
per collegare due parole distanti l'informazione doveva attraversare tutti i passaggi intermedi, e si
perdeva per strada. L'**attention** (in inglese, "attenzione") risolve questo: permette a ogni
parola, ogni volta che viene elaborata, di **guardarsi attorno e decidere a quali altre parole
dare peso**. L'idea nasce nel 2014 nella traduzione automatica; il paper *Attention is All You Need*
(Vaswani et al., 2017) ha mostrato che con la sola attention si può costruire un'intera architettura
— il **transformer** — senza ricorrenza. Ed è da lì che vengono gli LLM attuali.

### Esempio concreto

Frase di esempio (volutamente ambigua): *"Il gatto non ha mangiato perché era **sazio**."*

Ogni parola è rappresentata da tre vettori:
- **Query (Q):** "cosa sto cercando?" — la domanda che la parola si pone.
- **Key (K):** "cosa offro?" — l'etichetta con cui la parola risponde alle domande altrui.
- **Value (V):** "ecco il mio contenuto" — l'informazione reale che passo agli altri.

Quando il modello elabora "sazio", fa la query "di cosa ho bisogno per capire?". Confronta quella query
con i key di tutte le altre parole (misurando la somiglianza). Il key di "gatto" risponderà forte
("parlo di animali"), quello di "mangiato" medio, quello di "il" debole. Il modello dà quindi più
peso a "gatto" quando aggiorna la rappresentazione di "sazio". Risultato: sa che è *il gatto* ad
essere sazio, non il verbo.

In pratica: per ogni parola, l'attention fa un prodotto scalare tra query e key per ogni parola,
ottiene dei punteggi, li passa attraverso una **softmax** (diventano pesi che sommano a 1) e combina i
value con quei pesi. È una specie di "somma pesata" — ma *dinamica*: cambia a seconda del contesto.

### Perché funziona

Le parole non hanno significato fisso: "lo" in "lo ho visto" e "lo ha pulito" sono parole identiche
ma significati diversi. L'attention risolve l'ambiguità *per contesto*: la rappresentazione di una
parola diventa una sintesi delle parole intorno a lei, pesate in base a quanto c'entrano. Ripetuto a
ogni livello della rete, e in parallelo con più "teste" (ogni testa guarda un tipo diverso di
relazione), costruisce una comprensione profondamente contestuale.

### Controesempio

"Attention = il modello legge le parole nell'ordine e dà più attenzione a quelle importanti" è parzialmente
falso. L'attention non è "importanza" generale: è *relazione specifica*. Una parola può "guardarne" un'altra
per il soggetto, un'altra per il tempo verbale, un'altra per il tema. E non è sequenziale come una
lettura umana: il transformer vede *tutte* le parole insieme e calcola tutte le relazioni in un colpo
solo (per questo è veloce da allenare). Dire "legge da sinistra a destra come fai tu" è un'immagine
utile ma che nasconde il parallelismo: è uno dei motivi per cui non "pensa" come un umano.

### Domande di verifica

1. In "La banca era vicina ma alluvionata perché il **fiume** era in piena", quando il modello elabora
   "banca" quale parola troverà il key più forte? Perché?
2. Perché senza attention un modello fatica a risolvere l'ambiguità dei pronomi?

### Collegamenti

- Serve prima: Modulo 3 (attention = somma pesata dinamica; Modulo 2 = i vettori query/key/value).
- Serve dopo: Modulo 5 (come da queste rappresentazioni si arriva a prevedere la parola seguente).

---

## Modulo 5 — Da un vettore a una distribuzione: generazione, temperatura e limiti

**Obiettivo verificabile:** saprai spiegare come un modello produca una *distribuzione di probabilità*
sulle parole possibili in uscita, cosa fa la **temperatura** su quella distribuzione, e elencare i
tre limiti strutturali di un LLM che derivano direttamente da "non rappresenta il mondo".

### Idea centrale

All'esterno della rete c'è un ultimo passaggio: ogni vettore finale viene confrontato con *tutte le
parole del vocabolario* (dicendo, per ciascuna, "quanto è adatta come prossima?") e trasformato in una
lista di probabilità che sommano a 100%. Il modello **sceglie** (o estrae a sorte) una parola da quella
distribuzione, l'aggiunge al testo, e ricomincia. Questo passo si chiama **decoding**. La qualità e la
"personalità" del testo dipendono da *come* si sceglie: la strategia di scelta e le sue varianti
controllano il compromesso fra coerenza e varietà.

### Esempio concreto

Frase: *"Nel parco i bambini giocavano e ridevano sotto il…"*

Distribuzione estimata dal modello (semplificata):
`[albero (35%), sole (20%), ombra (15%), panchina (8%), nuvola (7%), …]`

Tre modi di scegliere la prossima parola:

- **Greedy (avida):** prendi sempre la più alta → *albero*. Sempre la stessa parola, prevedibile, a volte sbagliata.
- **Sampling con temperatura alta (T=1.5):** il campionamento appiattisce le probabilità, quindi
  *sole*, *ombra*, *nuvola* diventano competitive. Testo più variato, più rischioso.
- **Sampling con temperatura bassa (T=0.2):** quasi greedy, ma lascia una minima casualità. Testo
  focalizzato, quasi deterministico.

La temperatura *applatta* o *concentra* la distribuzione, non cambia le parole possibili. T molto
alto → testo casuale e confuso; T molto basso → ripetizioni e blocco.

### Perché funziona

Predire sempre la parola *più probabile in assoluto* (greedy) rende il testo prevedibile e ripetitivo.
**Estraendo a sorte, pesando le probabilità** (sampling), permetti al modello di esplorare opzioni
valide, come un autore che "lascia fluire" la storia. La temperatura è la manopola con cui decidi
quanto "fidarti della casualità". Tutto questo funziona perché la distribuzione deriva dalle stesse
regolarità statistiche del modulo 1: non stai inventando, stai mescolando ciò che il modello ha imparato.

### Controesempio

"Un LLM con temperatura alta sta 'creando'. Uno a temperatura bassa 'sa'" è falso. La temperatura
controlla *solo* la dispersione del campionamento, non la conoscenza. E tre limiti strutturali, tutti
derivanti dal fatto che il modello "non rappresenta il mondo":

1. **Allucinazioni:** se la distribuzione dà peso a una parola plausibile ma sbagliata, il modello la
   scrive convintissimo. Non ha un controllo "è vero?" perché non sta controllando il mondo, sta
   completando una frase.
2. **Nessun accesso alla realtà in tempo reale:** da solo conosce solo ciò che era nei dati di
   allenamento (fino a una certa data). Non "sa" ciò che è successo ieri; se trova una data, è una
   data *plausibile*, non verificata. (Un LLM collegato a strumenti esterni, tipo una ricerca sul web,
   può accedere a fatti nuovi — ma la conoscenza viene da fuori, non dal modello.)
3. **Non ragiona, completa:** un problema logico può essere risolto se il modello ha visto schemi
   simili, ma fallisce dove non ha esempi statistici. Non deduce come una dimostrazione.

### Domande di verifica

1. Perché una temperatura alta può far "inventare" un LLM qualcosa di plausibile ma falso?
2. Se un LLM risolve un problema di logica, come fai a capire se *ragiona* o *riconosce uno schema visto*?

### Collegamenti

- Serve prima: Moduli 1 (previsione parola), 4 (rappresentazioni contestuali pronte a essere usate).
- Serve dopo: verifica finale, approfondimenti (allenamento di un modello, prompt engineering).
