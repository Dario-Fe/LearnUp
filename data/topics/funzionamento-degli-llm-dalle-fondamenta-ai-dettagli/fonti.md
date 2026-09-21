# Fonti: funzionamento degli LLM

Regola del corso: **non invento titoli, autori o URL** che non posso verificare che esistano. Qui trovi
le *categorie* di fonte da cercare per ogni livello, e le incertezze dichiarate nella sezione
**Da verificare**. Se vuoi i titoli esatti, cerca le categorie sotto: sono tutte facilmente reperibili
su un motore di ricerca o in una biblioteca universitaria.

## Per chi vuole andare più a fondo

- **Livello curioso (1).** Una lettura lunga e senza formule che spieghi "come funziona un chatbot" con
  analogie. Cerca: *introduzione agli LLM per non tecnici*, video divulgativi (canali di scienza/tech,
  in italiano e inglese). Obiettivo: consolidare l'immagine mentale, non studiare i dettagli.
- **Livello studente (3).** Un manuale introduttivo di **machine learning** con un capitolo sulle reti
  neurali, e un'introduzione al **natural language processing**. Cerca: *machine learning introduttivo
  capitolo reti neurali*, *introduzione al NLP*. Il riferimento accademico sull'architettura
  transformer è il paper *Attention is All You Need* (Vaswani et al., 2017): è reperibile online ed è
  la fonte primaria per l'attention.
- **Livello collega (4).** Testi sull'allenamento (ottimizzazione per gradiente, loss), sulla
  tokenizzazione subword, e sulla teoria degli embedding. Cerca: *neural language model training*,
  *subword tokenization survey*, *embedding spaces semantics*.

## Come usare queste fonti nel corso

- Il **modulo 2** (embedding) si approfondisce con qualsiasi manuale di ML sul "rappresentare i dati in
  vettori".
- Il **modulo 3** (layer) richiede un capitolo su "una neurone / uno strato di rete" e sulla funzione
  ReLU.
- Il **modulo 4** (attention) ha come fonte prima il paper del 2017 citato sopra.
- Il **modulo 5** (temperatura, allucinazioni) tocca la letteratura su "decoding strategies" e "hallucination
  in LLM": è la zona dove la ricerca è più viva e dove ci sono più dubbi (vedi sotto).

## Da verificare

Queste sono le aree in cui **non affermo nulla di preciso senza fonte**, o in cui la conoscenza cambia
in fretta. Prima di citarle come fatti, controlla su una fonte aggiornata:

- **Numeri esatti dei modelli** (dimensione degli embedding, numero di layer, conteggio parametri):
  variano da una versione all'altra, non li do come fissi.
- **La data di conoscenza** dei modelli attuali: cambia continuamente, non è un dato che posso fissare.
- **Il meccanismo esatto dell'attention** a livello di formule: qui la mia descrizione è volutamente
  concettuale ("query/value che si confrontano"), non la formula del prodotto scalare softmax. Se ti
  serve l'equazione precisa, vai al paper del 2017.
- **Le cause delle allucinazioni:** è un campo di ricerca aperto. Esistono ipotesi (per esempio
  l'eccesso di sicurezza con cui il modello produce il testo, oppure la discrepanza fra ciò che "sa"
  e ciò che genera), ma non c'è consenso. Tratta ogni spiegazione specifica come *ipotesi*, non come
  verità.
- **"Quanto è etico / giusto" un LLM** su un dato input: giudizio di valore, non fatto verificabile.

> Nota sull'affidabilità: le categorie sopra sono tutte reperibili. Se un motore di ricerca non trova
> la fonte che cerchi per un titolo specifico, descrivi di nuovo la *categoria* invece di inventare il
> titolo. È la stessa regola del corso: meglio "non lo so, ma ecco come trovarlo" di una citazione che
> forse non esiste.
