# Esercizi: funzionamento degli LLM

Difficoltà crescente: base → intermedio → avanzato → trasferimento. Ogni esercizio ha soluzione in
`<details>` con i criteri di autovalutazione: *la tua risposta è giusta se contiene A e B, anche se la
forma è diversa*.

---

### Esercizio 1 (base) — Prevedi la prossima parola
**Modulo 1.** Per ogni frase, scrivi la parola più probabile che la completa e spiega in una riga *perché*
il modello la eleggerebbe.

a) *"In cucina ho preso una tazza e ho fatto …"*
b) *"L'avvocato è entrato in tribunale per …"*

<details>
<summary>Soluzione</summary>

a) «della» (o «caffè», «tè»): il contesto "cucina + tazza" attira bevande e oggetti da cucina.
b) «giudicare» / «difendere»: "avvocato + tribunale" attira termini giuridici.

**Come valutarti:** la tua risposta è giusta se (1) hai dato una parola plausibile nel contesto e
(2) hai spiegato che il modello sceglie in base alle regolarità statistiche viste nei dati, non perché
"sapeva" cosa significava la parola. Se hai scritto la parola ma non il "perché statistico", è parziale.
</details>

---

### Esercizio 2 (base) — Tokenizzare a mano
**Modulo 2.** Dividi la frase *"Non ho idea di cosa mangiare stasera"* in token come farebbe un
tokenizzatore semplificato (puoi usare spazi e parti di parola). Poi spiega in una riga perché una
parola come *"impossibile"* potrebbe essere divisa in più token.

<details>
<summary>Soluzione</summary>

Esempio: `["Non", " ho", " idea", " di", " cosa", " mangi", "are", " stasera"]` (le divisioni esatte
variano da tokenizzatore a tokenizzatore: l'importante è vedere che le parole lunghe si frammentano in
pezzi ricorrenti). *"impossibile"* → `["im", "poss", "ibile"]`: perché quei frammenti ("poss-",
"-ibile") compaiono in tante parole ("impossibile", "possibile", "impossibilità"), quindi
rappresentarli come token unici è più efficiente del trattare ogni parola come unità intera.

**Come valutarti:** giusto se (1) hai diviso tenendo conto degli spazi e delle parti ricorrenti e
(2) hai spiegato che la divisione è *statistica*: si privilegiano frammenti frequenti, non si usa una
regola grammaticale.
</details>

---

### Esercizio 3 (intermedio) — La somma pesata di uno strato
**Modulo 3.** Uno strato ha pesi `[0.8, −0.3, 0.1]`, bias `−0.2`, e riceve input
`[1, 0, 0.5]` (tre misure numeriche su un testo). Calcola la somma pesata e, con ReLU
(`f(x) = x se x > 0, altrimenti 0`), il valore di attivazione in uscita.

<details>
<summary>Soluzione</summary>

Somma pesata = `0.8·1 + (−0.3)·0 + 0.1·0.5 + (−0.2)` = `0.8 + 0 + 0.05 − 0.2` = `0.65`.
ReLU(0.65) = `0.65` (perché > 0).

Se i pesi fossero stati `[−0.8, …]` e la somma fosse stata `−0.4`, ReLU darebbe `0`: lo strato "non si
accende".

**Come valutarti:** giusto se (1) il calcolo dà 0.65 e (2) spieghi che la ReLU "taglia" i valori
negativi a zero, ed è questa non linearità che permette a uno strato di decidere "sì/non mi interessa".
Se hai dimenticato il bias, rifai: il bias è un termine a parte che si aggiunge *dopo* la somma.
</details>

---

### Esercizio 4 (intermedio) — Dove guarda l'attention
**Modulo 4.** Frase: *"La madre di Marco ha trovato le chiavi che aveva perso il figlio."* Quando il
modello elabora la parola *"perso"*, quali parole del contesto pensa che avrà come key più forti
(query·key alti)? Spiega in una riga cosa indica.

<details>
<summary>Soluzione</summary>

Probabilmente *«Marco»* (il possessore) e forse *«chiavi»*. Il key di «Marco» risponderebbe forte alla
query di «perso» perché "avere perso" implica una persona, e Marco è la persona più vicina. Questo
indica che l'attention collega il verbo alla sua entità, aiutando a risolvere "chi l'ha perso?".

*Nota di rigore:* questa è un'*inferenza didattica* su come funziona il meccanismo, non una misura
letta da un modello reale. L'esercizio serve a far ragionare sui pesi, non ad affermare cosa fa
esattamente un modello specifico su questa frase.

**Come valutarti:** giusto se (1) hai indicato almeno una persona del contesto come key forte e
(2) hai spiegato che l'attention pesa *relazioni dipendenti dal contesto*, non l'importanza fissa delle
parole. Se hai detto "ha dato attenzione a 'chiavi' perché è la parola importante", è impreciso.
</details>

---

### Esercizio 5 (avanzato) — Effetto della temperatura
**Modulo 5.** Hai una distribuzione di uscita sulla prossima parola: `[parolaA 50%, parolaB 30%,
parolaC 15%, parolaD 5%]`. Descrivi cosa succede, a livello concettuale, quando alzi la temperatura da
0.1 a 1.5. Poi spiega in una riga se il modello "conosce più fatti" con temperatura alta.

<details>
<summary>Soluzione</summary>

Temperatura bassa (0.1): la distribuzione diventa quasi tutta su parolaA (50% → ~99%), scelta quasi
deterministica, testo coerente ma ripetitivo. Temperatura alta (1.5): la distribuzione si appiattisce
(parolaD passa dal 5% a un 12-15%), tutte le parole diventano competitive, testo più variato e più
rischioso. **Non** conosce più fatti: la temperatura cambia solo quanto è dispersivo il campionamento,
non la conoscenza.

**Come valutarti:** giusto se (1) hai descritto l'appiattimento/centramento della distribuzione e
(2) hai dichiarato esplicitamente che la conoscenza non cambia. Se hai scritto "a temperatura alta il
modello è più intelligente", è l'errore n. 5.
</details>

---

### Esercizio 6 (avanzato) — Allucinazione come conseguenza necessaria
**Modulo 5.** Spiega, usando *solo* il fatto che un LLM "predice la parola seguente senza controllare il
mondo", perché un LLM può citare con sicurezza un articolo scientifico che non è mai esistito.

<details>
<summary>Soluzione</summary>

Il modello genera una citazione perché *plausibile* nel suo contesto (formato "autore, rivista, anno"
è uno schema statistico frequente), non perché abbia verificato l'esistenza dell'articolo. Manca il
passo "il mondo conferma?": non c'è, quindi la plausibilità statistica basta al modello per scrivere.
L'allucinazione non è un difetto occasionale: è la conseguenza diretta di "completa senza controllare".

**Come valutarti:** giusto se colleghi la allucinazione alla *mancanza di controllo sulla verità*, non
a "il modello sbaglia a caso". Se non hai menzionato che non c'è alcun meccanismo di verifica, manca
il punto chiave.
</details>

---

### Esercizio 7 (trasferimento) — Ricostruisci un LLM con le tue parole
**Modulo 1–5.** Prendi un'app che usi ogni giorno (una ricerca, un feed, un suggerimento di testo su un
telefono). Descrivi, in al massimo 8 righe, quale dei cinque concetti del corso (previsione parola,
token/embedding, layer/pesi, attention, distribuzione+temperatura) spiega *al meglio* quel comportamento.
Poi indica un limite di quell'app che deriva dal meccanismo stesso.

<details>
<summary>Soluzione</summary>

Esempio — "suggerimento del testo sul telefono": è previsione della parola seguente (modulo 1) +
token/embedding (modulo 2): il telefono stima la parola più probabile dato ciò che hai digitato.
Limite derivato: come un LLM, può suggerire parole plausibili ma sbagliate, e non può sapere se ciò che
sta per suggerire è vero.

**Come valutarti:** giusto se (1) hai collegato l'app a *uno* dei meccanismi in modo preciso (non "è
tutto AI") e (2) hai indicato un limite che *deriva* da quel meccanismo, non un difetto generico.
Una risposta generica tipo "il feed usa l'AI per mostrarti cose" non raggiunge il criterio: serve il
meccanismo specifico.
</details>
