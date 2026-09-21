# Verifica: funzionamento degli LLM

Criteri di padronanza e prova finale. In modalità **docenza**, la griglia di correzione e il piano di
recupero sono all'inizio: sono la fonte per spiegare l'argomento ad altri.

## Criteri di padronanza

Per ogni modulo, l'allievo è **padrone** se supera il criterio operativo (non a memoria).

| Modulo | Criterio di padronanza operativa |
|---|---|
| 1 — Previsione parola | Spiega in 60 secondi la differenza fra "ricerca" e "predizione parola seguente" e lo fa con un esempio che si può verificare a mano. |
| 2 — Token/embedding | Trasforma una frase corta in token, spiega perché servono i numeri (non le parole) e descrive con un disegno cosa significa "due concetti vicini nello spazio". |
| 3 — Layer | Calcola a mano una somma pesata con pesi e bias, e spiega perché serve la non linearità (senza ReLU molti strati = uno). |
| 4 — Attention | Spiega cosa sono query/key/value con un esempio, e identifica *dove* un modello "guarda" quando interpreta una frase ambigua. |
| 5 — Generazione/limiti | Spiega come da un vettore si ottiene una distribuzione e cosa fa la temperatura, ed elenca i tre limiti strutturali derivanti da "non rappresenta il mondo". |

## Prova finale (per l'allievo)

Rispondi senza guardare gli appunti. Ordine consigliato: le domande di definizione poi quelle operative.

1. **(Definizione operativa)** In una frase, che cos'è un LLM *senza* usare la parola "intelligenza" o "AI"?
2. **(Applicazione)** Dividi in token *"Non ho visto il cane di Marco ieri"* e spiega in una riga come un
   embedding lo rappresenta.
3. **(Applicazione)** Pesi `[3, 0.5]`, bias `1`, input `[2, 4]`. Calcola la somma pesata e, con ReLU,
   il valore in uscita.
4. **(Spiega come a un principiante)** "L'attention fa sì che ogni parola guardi le altre. Spiegamelo
   come se non sapessi mai cosa fa un chatbot."
5. **(Riconoscimento errore)** "Un LLM a temperatura alta sa più di uno a temperatura bassa." Perché
   questa frase è sbagliata?
6. **(Trasferimento)** Prendi un'app che usi ogni giorno e spiega quale dei cinque meccanismi del corso
   la fa funzionare, e quale limite le deriva.

**Come valutarti:**

- **Padrone (4-5):** rispondi 1–4 in modo preciso, fai correttamente il calcolo del punto 3, e il punto 6
  collega un meccanismo specifico a un limite.
- **Fragile (3):** sai spiegare i concetti ma sbagli il calcolo o dai definizioni a memoria.
- **Non padrone (0-2):** ti blocchi sui punti 3 o 4, o confondi ricerca e generazione ai punti 1 e 6.

## Piano di recupero (per il docente)

Se un allievo non raggiunge un modulo, non si ripete la stessa spiegazione: si torna al meccanismo più
basso.

| Modulo non raggiunto | Ripartire a | Strumento di recupero |
|---|---|---|
| 1 — previsione parola | Modulo 1 stesso | Gioco: completare 5 frasi a voce, notare *come* "sai" la parola seguente senza pensarci. |
| 2 — token/embedding | Modulo 2 | Tokenizzare testi reali (messaggi, titoli); disegnare uno "spazio delle parole" con 6 concetti vicini/lontani. |
| 3 — layer/pesi | **Modulo 3** | Ripassare grafico cartesiano e media, poi rifare la somma pesata con numeri più piccoli. Non saltare: il modulo 4 non entra. |
| 4 — attention | **Modulo 3** | Se l'attention non entra, è perché la somma pesata (modulo 3) non è padroneggiata. Tornare là. |
| 5 — generazione/limiti | Modulo 5 | Simulare una distribuzione con dei dadi: decidere una parola "a sorte pesando le probabilità". |

Nota del docente: il modulo 4 (attention) è quello dove si blocca la maggioranza degli allievi. La
causa quasi sempre non è l'attention in sé, ma il modulo 3 (somma pesata + non linearità) che non è
stato padroneggiato. Prima di "ripassare l'attention", verifica il modulo 3.

## Simulazione per corso (se insegni tu)

Formato consigliato: 25 minuti, 6 domande della prova finale (saltando quella che preferisci), 3 punti
ciascuna. Soglia di passaggio: 15/18. Sotto soglia, l'allievo rivede un modulo e rifà la simulazione
nella prossima lezione.
