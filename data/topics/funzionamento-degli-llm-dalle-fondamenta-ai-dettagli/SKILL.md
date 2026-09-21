---
name: iv-funzionamento-degli-llm-dalle-fondamenta-ai-dettagli
description: Sotto-skill di argomento "funzionamento degli LLM: dalle fondamenta ai dettagli" generata dal sistema Insegnante Virtuale. Ereditata dalla cornice insegnante-virtuale. Non usare direttamente: si carica tramite la skill base.
---

# Sotto-skill: funzionamento degli LLM — dalle fondamenta ai dettagli

| Campo | Valore |
|---|---|
| Slug | `funzionamento-degli-llm-dalle-fondamenta-ai-dettagli` |
| Livello di partenza | 2 (principiante/tecnico) |
| Modalità rilevata | docenza |
| Prerequisiti | programmazione di base; concetti di base dell'AI |
| Cornice base | v1.0.0 |
| Creato | 2026-09-21 |

## Contratto didattico

**Al termine saprai:** spiegare a voce, in una sequenza logica, come un LLM passa da *prevedere la parola
successiva* a *generare un testo plausibile*, passando per token ed embedding, layer (somma pesata +
attivazione), attention e distribuzione in uscita. Saprai anche riconoscere i tre limiti strutturali che
derivano dal fatto che il modello "non rappresenta il mondo" (allucinazioni, nessun accesso alla
realtà in tempo reale, non ragiona ma completa).

**Cosa NON copre questa sotto-skill:** come si *allena* un modello (ottimizzazione per gradiente in
profondità, loss, backpropagation), come si *prompta* efficacemente un LLM, e gli aspetti etici/sociali.
Sono sotto-skill separate: se l'allievo le vuole, si creano collegate (vedi `percorso.md`).

## Mappa del corso

| # | Modulo | Obiettivo verificabile | Concetti chiave |
|---|---|---|---|
| 1 | Da "cerca la parola vicina" a "predice la parola successiva" | Spiega la differenza fra ricerca e previsione e predice a mano la parola seguente | previsione parola, ricerca vs generazione, plausibilità vs verità |
| 2 | Token, embedding e lo spazio dei significati | Trasforma una frase in token e spiega perché servono i numeri | token, tokenizzatore, embedding, spazio degli embedding |
| 3 | Il layer: pesi, somme pesate e funzione di attivazione | Calcola una somma pesata e spiega perché serve la non linearità | layer, peso, bias, ReLU, non linearità |
| 4 | Il transformer: attention, perché separa le parole e come le ricombina | Spiega query/key/value e identifica dove il modello "guarda" | attention, query, key, value, softmax |
| 5 | Da un vettore a una distribuzione: generazione, temperatura e limiti | Spiega decoding, temperatura e i tre limiti strutturali | decoding, temperatura, allucinazione, distribuzione |

## Concetto centrale in una frase

Un LLM **non rappresenta il mondo**: rappresenta la *probabilità delle parole seguenti*, e tutto il
resto (compresa l'illusione di capire) nasce da questa singola scelta.

## Come condurre una sessione su questo argomento

**Punto di partenza:** sempre dal **modulo 1**, mai dall'attention. La trappola in cui cadono quasi
tutti gli insegnanti di LLM è iniziare da "l'attention è magico", e lasciare l'allievo senza basi su
*come* il modello lavora sui numeri. Inizia con il test della parola seguente ("il contrario del fuoco
è…"): è un esercizio che tutti possono fare, e diventa l'aggancio per tutto il resto.

**Ordine dei moduli:** 1 → 2 → 3 → 4 → 5 **senza inversioni**. Questo corso è una piramide, non una
lista. Il modulo 4 (attention) è dove si blocca la maggioranza: e la causa è quasi sempre che il
modulo 3 (somma pesata) non è stato padroneggiato. Prima di "ripassare l'attention", verifica che la
somma pesata con pesi e bias funzioni a mano.

**Dove l'allievo si blocca (il punto critico):**

- **Modulo 2 → 3:** non vede *perché* le parole devono diventare numeri. Risolvi con l'embedding che
  "parole simili sono vicine" e il fatto che una rete può operare solo su numeri. Un esempio concreto
  (una riga di tabella con 4–5 colonne numeriche) batte ogni definizione.
- **Modulo 3 (la somma pesata):** è l'unico calcolo aritmetico del corso, ed è anche l'unico che va
  *fatto a mano*. Fallo fare all'allievo, non limitarti a mostrarlo. Se non sa sommare tre prodotti
  pesati, il modulo 4 non entrerà.
- **Modulo 4 (attention):** "attention" suona come "attenzione umana". Riempi subito il vuoto col
  significato tecnico ("con quanto peso ogni parola si collega alle altre, dipendente dal contesto") e
  usa l'esempio del pronome ambiguo ("lo ha pulito" → "lo" = il gatto).
- **Modulo 5:** confondono temperatura con conoscenza. Ripeti la regola: la temperatura è una manopola
  di *casualità*, non di *sapere*.

**Cosa non saltare mai:** il modulo 3 con l'esercizio calcolato a mano. È il cardine: se lo salti,
l'attention (modulo 4) diventa magia non spiegata.

**Registro linguistico:** livello 2 (principiante tecnico). L'allievo sa programmare e conosce l'AI per
concetti, quindi non spieghi cos'è un file o un grafico, ma **spieghi ogni termine nuovo dei LLM**.
Niente calculus né algebra lineare: tutto ciò che serve (somma, prodotto scalare, grafico) è aritmetica
e algebra di base, e lo spiego qui. I termini tecnici (token, embedding, attention) si introducono con
definizione e non si riusano mai senza averli ricordati.

**Etichette di affidabilità:** quasi tutto il corso è **consolidato** (è scienza consolidata del ML).
Due punti vanno marcati:

- **Dibattuto / da verificare:** le *cause* delle allucinazioni (campo di ricerca aperto, nessun
  consenso) e la data di conoscenza dei modelli. Non presentarli come fatti.
- **Semplificato:** la tokenizzazione subword e l'attention sono descritte in modo concettuale, non
  con le formule. Se l'allievo vuole l'equazione, rimanda al paper "Attention is All You Need" (2017).

**Verifica della comprensione, in due domande che funzionano sempre:**

1. *"Secondo te, se un LLM produce testo plausibile, sta capire o statistivamente combinando? Come
   fai a distinguerlo?"* (risposta attesa: probabilmente combina; si verifica cercando fonti inventate
   o allucinazioni)
2. *"Se un modello fa solo somme pesate senza funzione di attivazione, cosa succede?"* (risposta attesa:
   molti strato valgono uno; serve la non linearità — se non sa questo, il modulo 4 non è ancora pronto)

**Se l'allievo chiede "ma come si allena davvero?":** è una domanda legittima ma fuori dal perimetro di
questa sotto-skill. Mettila nel *parcheggio* (vedi `contratto-output.md`) e proponi una sotto-skill
dedicata sull'allenamento dopo aver chiuso questo percorso.

## File collegati

- `percorso.md` — i cinque moduli con esempi concreti e controesempi; da leggere per ogni sessione
- `glossario.md` — termini minimi e termini da non usare
- `errori-tipici.md` — sei misconcezioni e come smontarle
- `esercizi.md` — sette esercizi a difficoltà crescente con soluzioni nascoste
- `verifica.md` — criteri di padronanza, prova finale, griglia di recupero (per il docente)
- `fonti.md` — categorie di fonte per livello, con incertezze dichiarate
- `meta.json` — metadati usati dal registro (`iv.py`)
