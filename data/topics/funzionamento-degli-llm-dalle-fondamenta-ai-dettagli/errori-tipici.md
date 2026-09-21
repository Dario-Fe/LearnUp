# Errori tipici: funzionamento degli LLM

Banca delle misconcezioni. Ogni voce è formulata come la direbbe l'allievo — errori plausibili, non
errori stupidi. Per ognuna: perché è allettante, dove sta l'errore, la correzione, il test che la
smaschera.

## 1. "Un LLM è un motore di ricerca più potente"

**Perché è allettante.** Li usiamo entrambi per "trovare informazioni", quindi sembrano la stessa cosa,
solo con risultati diversi.

**C'è di sbagliato.** Google *recupera* pagine esistenti; l'LLM *genera* testo nuovo. Uno ha un indice
di documenti reali, l'altro ha pesi imparati sui dati. Se chiedi "fammi le fonti", Google te le mostra,
l'LLM te le inventa (con nomi di studi, URL, citazioni che non esistono).

**Correzione in una riga.** La ricerca recupera, la generazione produce: non sono potenze diverse della
stessa cosa.

**Test che la smaschera.** "Un LLM sa ciò che è successo ieri?" — se rispondi "sì, perché ha tutto
l'internet", hai commesso l'errore. Un LLM sa solo ciò che era nei suoi dati di allenamento fino a una
determinata data.

## 2. "Ogni parola ha un embedding con un significato preciso in una colonna"

**Perché è allettante.** Immaginiamo una tabella con una colonna = un concetto, comodo da visualizzare.

**C'è di sbagliato.** Un embedding è una *posizione* in uno spazio multidimensionale in cui nessun
singolo asse corrisponde a un significato. Il significato è *distribuito* e deriva dalle relazioni con
gli altri punti, non da una colonna.

**Correzione in una riga.** Il valore di una parola è "dove si trova tra tutte le altre", non "cosa c'è
in una sua specifica colonna".

**Test che la smaschera.** "In quale colonna dell'embedding di 'gatto' sta scritto che è un animale?" —
la domanda presuppone qualcosa che non esiste: non c'è una colonna "gatto".

## 3. "Più layer ci sono, più il modello è intelligente"

**Perché è allettante.** Strati in più sembrano sempre "più calcolo", quindi più capace.

**C'è di sbagliato.** Strati di somme pure (lineari) sono matematicamente identici a uno strato solo: la
potenza arriva *dalla non linearità fra uno strato e l'altro*, non dal loro numero. Un modello grande
non è soltanto "più strati": sono strati *con attivazioni non lineari* e molti parametri.

**Correzione in una riga.** Non è il numero degli strati a contare, è la non linearità che li collega.

**Test che la smaschera.** "Due strati di somme pesate valgono quanto uno strato?" — sì, se non c'è una
funzione di attivazione in mezzo. La risposta "no, due sono sempre meglio" rivela il malinteso.

## 4. "Attention = il modello dà più attenzione alle parole importanti"

**Perché è allettante.** "Attention" in italiano suona esattamente come "attenzione umana alle cose
importanti".

**C'è di sbagliato.** L'attention non è importanza generale: è *relazione specifica e dinamica*. Una
parola può guardare un'altra per il soggetto, un'altra per il tempo, un'altra per il tema. E il
transformer non "legge da sinistra a destra": vede tutte le parole insieme in un colpo solo.

**Correzione in una riga.** L'attention è "con quanto peso ogni parola si collega a ogni altra parola,
dipendente dal contesto", non "nota le parole chiave".

**Test che la smaschera.** "In 'Lo ha pulito perché era sporco', come fa il modello a sapere che 'lo'
è il gatto?" — non è che 'lo' è importante; l'attention collega 'lo' a 'gatto' con un peso elevato in
quel contesto specifico.

## 5. "La temperatura controlla quanto il modello 'sa'"

**Perché è allettante.** "Temperatura alta = più creativo" sembra un'intelligenza che si accende.

**C'è di sbagliato.** La temperatura controlla *solo* la dispersione del campionamento, non la
conoscenza. Con temperatura alta un LLM non "pensa di più": estrae parole più lontane dalla moda della
distribuzione, rendendo il testo più variato e più rischioso.

**Correzione in una riga.** La temperatura è una manopola di casualità, non di conoscenza.

**Test che la smaschera.** "Un LLM a temperatura alta sa più fatti di uno a temperatura bassa?" — no,
conosce esattamente le stesse cose; cambia solo quanto è pronto a mescolare le opzioni.

## 6. "Se produce testo plausibile, quindi capisce"

**Perché è allettante.** Il testo è così bene scritto che attribuire comprensione è naturale.

**C'è di sbagliato.** Il modello completa una frase secondo regolarità statistiche: può imitare la
comprensione senza avere un *modello del mondo*. Questo spiega le allucinazioni: nessun controllo di
verità, solo plausibilità statistica.

**Correzione in una riga.** Comportarsi *come se* capisse non è avere un modello del mondo.

**Test che la smaschera.** "Perché un LLM inventa citazioni con tanto di nome e URL?" — perché non sta
controllando la verità, sta completando una frase plausibile. Se "capisse", non inventerebbe fonti.
