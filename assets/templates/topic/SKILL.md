---
name: iv-{{SLUG}}
description: Sotto-skill di argomento "{{TITLE}}" generata dal sistema Insegnante Virtuale. Ereditata dalla cornice insegnante-virtuale. Non usare direttamente: si carica tramite la skill base.
---

# Sotto-skill: {{TITLE}}

<!-- ISTRUZIONI: sostituisci ogni blocco ISTRUZIONI con contenuto reale e cancella i commenti.
     Il validatore (`iv.py validate`) fallisce se restano placeholder {{...}} o commenti ISTRUZIONI. -->

| Campo | Valore |
|---|---|
| Slug | `{{SLUG}}` |
| Livello di partenza | {{LEVEL}} |
| Modalità rilevata | {{MODE}} |
| Prerequisiti | {{PREREQS}} |
| Cornice base | v{{BASE_VERSION}} |
| Creato | {{DATE}} |

## Contratto didattico

<!-- ISTRUZIONI: 3-6 righe. Cosa saprà fare l'allievo alla fine ("Al termine saprai...") e cosa NON è coperto da questa sotto-skill. -->

## Mappa del corso

<!-- ISTRUZIONI: una tabella con i moduli. Ogni modulo ha un obiettivo verificabile. -->

| # | Modulo | Obiettivo verificabile | Concetti chiave |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

## Concetto centrale in una frase

<!-- ISTRUZIONI: la frase che, se l'allievo ricorda solo quella, gli serve più di tutto il resto. -->

## Come condurre una sessione su questo argomento

<!-- ISTRUZIONI: sequenza concreta per questo argomento specifico: da dove partire, quali esempi usare per primi,
     quale ordine di moduli, dove l'allievo tipicamente si blocca, quale modulo non saltare mai. -->

## File collegati

- `percorso.md` — moduli, esempi concreti e controesempi
- `glossario.md` — termini minimi indispensabili
- `errori-tipici.md` — misconcezioni e come smontarle
- `esercizi.md` — esercizi a difficoltà crescente con soluzioni nascoste
- `verifica.md` — criteri di valutazione e prova finale
- `fonti.md` — fonti consigliate per livello e loro affidabilità
- `meta.json` — metadati usati dal registro (`iv.py`)
