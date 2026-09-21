# Glossario: funzionamento degli LLM

Termini che l'allievo **deve** conoscere alla fine del corso. Definizione in una frase. In fondo, i
termini "da non usare" (ambigui o sbagliati nel contesto).

| Termine | Definizione | Dove compare |
|---|---|---|
| **LLM** (Large Language Model) | Modello addestrato a prevedere la parola seguente in una sequenza di testo, che per questa ragione genera testo plausibile. | Modulo 1 |
| **Token** | Il più piccolo pezzo di testo che il modello vede: spesso una parte di parola, a volte una parola intera o un segno di punteggiatura. | Modulo 2 |
| **Tokenizzatore** | La parte del modello che spezza il testo in token. Non divide come un umano legge: divide per statistica su cosa capita spesso insieme. | Modulo 2 |
| **Embedding** | Una riga di numeri (un vettore) che rappresenta un token in modo che significati simili siano vicini nello spazio. | Modulo 2 |
| **Spazio degli embedding** | Lo "spazio" multidimensionale in cui ogni token ha una posizione; la lontananza/vicinanza tra posizioni codifica similarità di significato. | Modulo 2 |
| **Layer / strato** | Un blocco che fa una somma ponderata degli input seguita da una funzione di attivazione. La rete è molti layer impilati. | Modulo 3 |
| **Peso** | Un numero che dice quanto conta un input nella somma pesata di uno strato. Si impara durante l'allenamento. | Modulo 3 |
| **Bias** | Un numero aggiunto dopo la somma pesata che sposta in su o in giù il risultato. | Modulo 3 |
| **Funzione di attivazione** | Regola non lineare (es. ReLU) applicata dopo la somma: decide se uno strato "si accende". Senza di essa, molti strati equivalgono a uno. | Modulo 3 |
| **Attention** | Meccanismo che, per ogni parola, decide con quanto peso guardare le altre parole del contesto e ne combina il contenuto. | Modulo 4 |
| **Query / Key / Value** | Tre vettori per parola: la query "sta cercando", la key "offre come etichetta", il value "cede contenuto". Usati nell'attention. | Modulo 4 |
| **Softmax** | Funzione che trasforma dei numeri in probabilità che sommano a 1. Serve a trasformare "somiglianza" in "quanto peso dare". | Modulo 4 |
| **Decoding** | L'ultimo passaggio: da un vettore finale si ottiene una distribuzione di probabilità su tutte le parole del vocabolario e si sceglie la prossima. | Modulo 5 |
| **Distribuzione di probabilità** | La lista, su tutte le parole possibili, di quanto ciascuna è adatta come prossima parola. Sommano al 100%. | Modulo 5 |
| **Temperatura** | Manopola che controlla quanto la scelta della parola seguente è concentrata (bassa) o dispersiva (alta). | Modulo 5 |
| **Allucinazione** | Testo plausibile ma falso prodotto perché il modello completa la frase senza controllare se il mondo la conferma. | Modulo 5 |
| **Gradiente** | Indicatore di *come regolare* pesi e bias per ridurre l'errore. È lo strumento dell'allenamento; qui lo nomino, non lo calcolo. | Modulo 3 (cenno) |
| **Overfitting / memorizzazione** | Quando un modello impara *troppo bene* i dati di esempio e non va più bene su dati nuovi. Concetto sorella di "non rappresenta il mondo". | Modulo 3 (cenno), 5 |

## Termini da non usare (nel corso)

- **"Il modello capisce / pensa / sa"** — nel corso usiamo *predice / combina / stima*: "capire" presuppone
  un modello del mondo che il meccanismo di previsione non ha. Meglio: "si comporta come se capisse".
- **"rete neurale" vago senza struttura** — ogni volta che dici "rete neurale", specifica *che cosa fa*
  quel layer. "rete neurale" non è una spiegazione.
- **"Deep learning" come scusa** — dire "è deep learning" non spiega nulla. Se non puoi dire *cosa* fa,
  non stai spiegando.
- **"AI che decide"** — il modello non decide: estrae una parola da una distribuzione di probabilità.
  "Decidere" carica di agente ciò che è campionamento statistico.
- **"Google è un LLM"** — errore di categoria: cerca, non genera. Non sono la stessa cosa.
