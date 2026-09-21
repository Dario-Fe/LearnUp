# Modalità operative

La modalità si rileva all'avvio e vale per la sessione. Si può cambiare in qualsiasi momento:
basta dirlo e si riparte dal punto giusto. Il default è **autodidatta**.

## Rilevamento in 3 domande (non un questionario)

1. *Per cosa ti serve?* → capire / ripassare / un esame / il lavoro.
2. *Quanto tempo hai adesso, e entro quando ti serve?* → ritmo e profondità.
3. *Preferisci che ti interroghi o che ti spieghi?* → socratico o frontale.

Da qui: "esame" se c'è una prova, "docenza" se studia per altri o tiene una lezione, altrimenti "autodidatta".

---

## Autodidatta

**Scopo:** capire e applicare, al ritmo dell'allievo.

- Si parte dall'**uso**: "a cosa ti serve questa cosa domani".
- Nessun voto formale, ma `--grade` continua a servire per programmare i ripassi.
- Più esempi applicativi, meno formalismo (livello 1-2 di default).
- Il percorso si può saltare a pezzi: dichiara sempre cosa si sta saltando.
- Chiusura: "cosa sai fare adesso che non sapevi fare prima".

## Esame

**Scopo:** passare una prova con un formato e una scadenza.

- **Piano a ritroso**: dalla data d'esame ai moduli (`verifica.md` → simulazione).
- Se l'allievo fornisce programma, dispense o prove passate, la sotto-skill si **allinea a quelli**
  (è la fonte da rispettare, annotata in `fonti.md`).
- Ogni modulo chiude con una **prova in formato esame**: tempo, punteggio, soglia.
- Ripetizione spaziata più aggressiva: intervalli brevi, simulazioni complete ogni 2 moduli.
- Si registrano gli errori per tipologia: *"tre errori su cinque sono di segno nell'algebra, non di concetto"*.
- Chiusura: punteggio stimato + i due argomenti che valgono più punti nel tempo rimasto.

## Docenza (studio per altri)

**Scopo:** preparare materiale o verifiche per studenti.

- Ogni allievo ha il suo profilo: usa `--learner <nome>` su `log`, `due` e `stats`. In questa modalità il
  nome da chiedere è quello **dello studente**, non del tuo interlocutore; e vale la regola del primo avvio
  (`protocollo-sessione.md`, FASE 0.2): si chiede una volta e resta comunque in locale.
- **Il profilo di uno studente nasce al primo `log`**: non c'è niente da creare o registrare prima. Le
  sotto-skill sono condivise fra tutti gli allievi (imparano lo stesso argomento senza rigenerarlo);
  separati restano i progressi, le lacune, i ripassi e il diario di ciascuno.
- Il nome si corregge con `learner rename` (un cognome scritto male è la norma) e un doppione si unisce con
  `learner merge`; entrambi lasciano un alias. `learner delete` esiste, ma si usa solo su richiesta esplicita
  del docente: cancellare un profilo significa cancellare la storia di studio di una persona.
- Il sistema produce anche **materiale per il docente**: spiegazioni, correzioni, criteri di valutazione.
- `verifica.md` diventa la fonte principale: griglia di correzione, livelli di padronanza, recupero.
- Il diario (`iv.py stats --write`) è il report per allievo: dove sta, dove sbatte, cosa proporre.
- Il tono resta quello dell'allievo finale, non del collega: la chiarezza va scritta, non presupposta.

---

## Come cambiano le sotto-skill per modalità

| Elemento | Autodidatta | Esame | Docenza |
|---|---|---|---|
| `verifica.md` | Criteri di padronanza essenziali | Simulazione completa, punteggi, soglie | Griglia di correzione e recupero |
| Check di modulo | Domande di verifica | Prova a tempo | Compito con soluzioni |
| Ritmo | Flessibile | Piano a ritroso dalla data | Calendario delle lezioni |
| Fonti | Introduzioni e riferimenti pratici | Programma, prove passate, manuale adottato | Testi + materiale dell'allievo |

## Cambio di modalità a metà percorso

1. Dillo all'utente: *"passiamo in modalità esame: cambia il ritmo e aggiungo le simulazioni"*.
2. Aggiorna `meta.json` (`mode`) e rigenera le parti dipendenti dalla modalità:

```bash
python scripts/iv.py register <slug> --self-check "modalità passata a esame"
```

3. Riconfigura il piano in `verifica.md` e `percorso.md`, senza toccare i progressi già registrati.
