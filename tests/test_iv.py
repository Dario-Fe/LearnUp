"""Test del motore iv.py — schema delle sotto-skill, riuso, alias, progressi.

Esecuzione (dalla radice del repository):
    python -m unittest discover -s tests -t tests
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import re
import subprocess
import time
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
IV_PATH = SKILL_DIR / "scripts" / "iv.py"


def load_iv():
    spec = importlib.util.spec_from_file_location("iv_engine", IV_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


iv = load_iv()

VALID_TOPIC_MD = """---
name: iv-{slug}
description: Sotto-skill di prova.
---

# Sotto-skill: {title}

## Contratto didattico

Al termine saprai fare la cosa.

## Mappa del corso

| # | Modulo | Obiettivo verificabile | Concetti chiave |
|---|---|---|---|
| 1 | Uno | Fare uno | uno |
| 2 | Due | Fare due | due |
| 3 | Tre | Fare tre | tre |

## Come condurre una sessione su questo argomento

Parti dal modulo 1 e non saltare gli esempi.
"""

VALID_PERCORSO = """# Percorso: {title}

## Prerequisiti e diagnosi rapida

| Prerequisito | Sotto-skill esistente | Domanda di diagnosi |
|---|---|---|
| nessuno | - | sai contare? |

{moduli}
"""

VALID_MODULO = """## Modulo {n} — Modulo {n}

**Obiettivo verificabile:** saprai fare la cosa {n}

### Idea centrale

Testo dell'idea centrale.

### Esempio concreto

Un esempio concreto.

### Perché funziona

Perché funziona davvero.

### Controesempio

Un controesempio.

### Domande di verifica

1. Domanda?

"""

VALID_ERRORI = """# Errori tipici

## 1. Primo errore

- **Perché è allettante:** sembra ovvio
- **Cosa c'è di sbagliato:** è falso
- **La correzione in una riga:** correggi così
- **Test che la smaschera:** prova questo

## 2. Secondo errore

- **Perché è allettante:** a
- **Cosa c'è di sbagliato:** b
- **La correzione in una riga:** c
- **Test che la smaschera:** d

## 3. Terzo errore

- **Perché è allettante:** a
- **Cosa c'è di sbagliato:** b
- **La correzione in una riga:** c
- **Test che la smaschera:** d

## 4. Quarto errore

- **Perché è allettante:** a
- **Cosa c'è di sbagliato:** b
- **La correzione in una riga:** c
- **Test che la smaschera:** d
"""

VALID_GLOSSARIO = """# Glossario: {title}

| Termine | Definizione (una frase) | Perché conta | Esempio lampo |
|---|---|---|---|
| A | def A | conta | es |
| B | def B | conta | es |
| C | def C | conta | es |
| D | def D | conta | es |
| E | def E | conta | es |
| F | def F | conta | es |
| G | def G | conta | es |
"""

VALID_ESERCIZI = """# Esercizi: {title}

{esercizi}
"""

VALID_ESERCIZIO = """### Esercizio {tag}

Testo dell'esercizio {tag}.

<details>
<summary>Mostra soluzione e criteri di autovalutazione</summary>

**Soluzione:** la soluzione.

**Come valutarti:** deve contenere questo e quello.

**Errore tipico qui:** l'errore.

</details>
"""

VALID_VERIFICA = """# Verifica: {title}

## Criteri di padronanza

| Livello | Cosa sai fare | Come lo dimostri |
|---|---|---|
| Base | cosa | come |

## Prova finale (forma breve)

1. Domanda uno
2. Domanda due
3. Domanda tre
4. Domanda quattro
5. Domanda cinque
6. Domanda sei
"""

VALID_FONTI = """# Fonti: {title}

## Per chi parte da zero

| Fonte | Tipo | Perché | Affidabilità |
|---|---|---|---|
| Manuale introduttivo | libro | chiaro | consolidato |

## Da verificare (incertezze dichiarate)

- La data esatta del primo utilizzo è incerta.
"""


def run(argv: list[str]) -> tuple[int, str]:
    """Esegue un comando catturando stdout e codice di uscita."""
    args = iv.build_parser().parse_args(argv)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        try:
            args.func(args)
            code = 0
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0
    return code, buffer.getvalue()


def fill_topic(slug: str, title: str, folder: Path) -> None:
    """Riempie una sotto-skill appena creata con contenuto conforme allo schema."""
    moduli = "\n---\n\n".join(VALID_MODULO.format(n=n) for n in (1, 2, 3))
    esercizi = "\n".join(VALID_ESERCIZIO.format(tag=f"E{i}") for i in range(1, 7))
    (folder / "SKILL.md").write_text(VALID_TOPIC_MD.format(slug=slug, title=title), encoding="utf-8")
    (folder / "percorso.md").write_text(VALID_PERCORSO.format(title=title, moduli=moduli), encoding="utf-8")
    (folder / "errori-tipici.md").write_text(VALID_ERRORI, encoding="utf-8")
    (folder / "glossario.md").write_text(VALID_GLOSSARIO.format(title=title), encoding="utf-8")
    (folder / "esercizi.md").write_text(VALID_ESERCIZI.format(title=title, esercizi=esercizi), encoding="utf-8")
    (folder / "verifica.md").write_text(VALID_VERIFICA.format(title=title), encoding="utf-8")
    (folder / "fonti.md").write_text(VALID_FONTI.format(title=title), encoding="utf-8")


class BaseIV(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        iv.set_data_dir(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def crea(self, title: str, **kwargs) -> str:
        argv = ["create", "--title", title] + [item for k, v in kwargs.items() for item in (f"--{k}", str(v))]
        code, out = run(argv)
        self.assertEqual(code, 0, out)
        return json.loads(out)["slug"]

    def crea_completo(self, title: str) -> str:
        slug = self.crea(title)
        fill_topic(slug, title, iv.topic_dir(slug))
        code, out = run(["register", slug])
        self.assertEqual(code, 0, out)
        return slug


class TestNormalizzazione(BaseIV):
    def test_norm_rimuove_accenti_e_punteggiatura(self):
        self.assertEqual(iv.norm("Probabilità & Statistica!"), "probabilita statistica")

    def test_tokens_eliminano_stopword(self):
        self.assertEqual(iv.tokens("Corso di introduzione alla statistica"), ["statistica"])

    def test_chiave_ignora_ordine_delle_parole(self):
        self.assertEqual(iv.key_of("storia romana"), iv.key_of("romana storia"))

    def test_slug_leggibile(self):
        self.assertEqual(iv.slugify("Equazioni di secondo grado"), "equazioni-di-secondo-grado")

    def test_steli_uniscono_singolare_e_plurale(self):
        self.assertEqual(iv.similarity("equazione di secondo grado", "equazioni di secondo grado"), 1.0)


class TestSimilarita(BaseIV):
    def test_argomenti_diversi_non_si_somigliano(self):
        self.assertLess(iv.similarity("impero romano", "filosofia kantiana"), 0.3)

    def test_argomenti_affini_si_riconoscono(self):
        self.assertGreaterEqual(iv.similarity("calcolo delle probabilita", "probabilita"), iv.T_VARIANT)

    def test_ordine_delle_parole_irrilevante(self):
        self.assertEqual(iv.similarity("statistica inferenziale", "inferenziale statistica"), 1.0)


class TestCicloRigenerante(BaseIV):
    def test_find_su_registro_vuoto_propone_nuova(self):
        code, out = run(["find", "analisi matematica", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["status"], "none")
        self.assertEqual(payload["azione"], "genera_nuova")

    def test_crea_poi_find_riusa(self):
        slug = self.crea_completo("Metodo Feynman")
        self.assertEqual(slug, "metodo-feynman")
        code, out = run(["find", "metodo Feynman", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["status"], "exact")
        self.assertEqual(payload["azione"], "riusa")
        self.assertEqual(payload["match"]["slug"], "metodo-feynman")

    def test_find_ignora_stopword_e_maiuscole(self):
        self.crea_completo("Metodo Feynman")
        code, out = run(["find", "Il Metodo di Feynman", "--json"])
        self.assertEqual(json.loads(out)["status"], "exact")

    def test_find_su_variante_chiede_conferma(self):
        self.crea("Equazioni di secondo grado")
        code, out = run(["find", "equazioni di secondo grado complete", "--json"])
        payload = json.loads(out)
        self.assertIn(payload["status"], ("variant", "exact", "candidates"))

    def test_bozza_incompleta_viene_segnalata(self):
        self.crea("Analisi matematica")
        code, out = run(["find", "analisi matematica", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["status"], "draft_incompleto")
        self.assertEqual(payload["azione"], "completa_poi_riusa")

    def test_creazione_duplicata_rifiutata(self):
        self.crea("Termodinamica")
        code, out = run(["create", "--title", "Termodinamica"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["ok"])

    def test_list_mostra_gli_argomenti(self):
        self.crea("Termodinamica")
        code, out = run(["list", "--json"])
        payload = json.loads(out)
        self.assertEqual([row["slug"] for row in payload["argomenti"]], ["termodinamica"])


class TestAliasEMerge(BaseIV):
    def test_alias_rendono_riusabile_un_nome_alternativo(self):
        self.crea_completo("Roma antica")
        code, out = run(["alias", "roma-antica", "--add", "Impero romano"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["verifica"], "exact")
        code, out = run(["find", "impero romano", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["status"], "exact")
        self.assertEqual(payload["match"]["slug"], "roma-antica")

    def test_merge_unifica_progressi_e_alias(self):
        slug_a = self.crea_completo("Impero romano")
        slug_b = self.crea_completo("Roma antica")
        run(["log", "--topic", slug_a, "--minutes", "30", "--summary", "prima sessione"])
        code, out = run(["merge", slug_a, slug_b])
        self.assertEqual(code, 0)
        self.assertFalse(iv.topic_dir(slug_a).exists())

        code, out = run(["find", "impero romano", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["match"]["slug"], slug_b)
        progress = iv.progress_for(slug_b, "default")
        self.assertEqual(progress["total_minutes"], 30)

    def test_reindex_ricostruisce_il_registro(self):
        self.crea("Metodo Feynman")
        iv.REGISTRY.unlink()
        code, out = run(["reindex"])
        self.assertEqual(json.loads(out)["slugs"], ["metodo-feynman"])


class TestValidazione(BaseIV):
    def test_scheletro_appena_creato_non_e_valido(self):
        slug = self.crea("Analisi matematica")
        code, out = run(["validate", slug, "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertFalse(payload["esito"][0]["valido"])
        self.assertGreater(payload["esito"][0]["errori"], 0)

    def test_sotto_skill_completa_e_valida(self):
        slug = self.crea_completo("Analisi matematica")
        code, out = run(["validate", slug, "--json"])
        self.assertEqual(code, 0, out)
        self.assertTrue(json.loads(out)["esito"][0]["valido"])

    def test_register_rifiuta_una_bozza(self):
        slug = self.crea("Analisi matematica")
        code, out = run(["register", slug])
        self.assertEqual(code, 1)
        self.assertIn("draft", json.loads(out)["error"])

    def test_register_aggiorna_lo_stato_nel_registro(self):
        slug = self.crea_completo("Analisi matematica")
        code, out = run(["list", "--json"])
        row = json.loads(out)["argomenti"][0]
        self.assertEqual(row["stato"], "active")
        self.assertEqual(row["slug"], slug)
        self.assertFalse(row["da_rigenerare"])

    def set_cornice(self, slug: str, version: str) -> None:
        """Simula una sotto-skill generata con una cornice diversa da quella corrente."""
        reg = iv.load_registry()
        for entry in reg["topics"]:
            if entry["slug"] == slug:
                entry["base_version"] = version
        iv.save_registry(reg)
        meta = json.loads((iv.topic_dir(slug) / "meta.json").read_text(encoding="utf-8"))
        meta["base_version"] = version
        (iv.topic_dir(slug) / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    def test_cornice_major_diversa_segnala_da_rigenerare(self):
        """Major = regole che invalidano i contenuti: vanno rigenerati."""
        slug = self.crea_completo("Analisi matematica")
        self.set_cornice(slug, "0.9.0")
        code, out = run(["status"])
        payload = json.loads(out)
        self.assertEqual(payload["da_rigenerare"], [slug])
        self.assertEqual(payload["cornice_aggiornabile"], [])
        code, out = run(["list"])
        self.assertIn("da rigenerare", out)

    def test_cornice_minor_non_obbliga_a_rigenerare(self):
        """Minor = aggiunte compatibili: aggiornamento opzionale, la sotto-skill resta usabile."""
        slug = self.crea_completo("Analisi matematica")
        major = iv.version_major(iv.BASE_VERSION)
        self.set_cornice(slug, f"{major}.0.5")
        code, out = run(["status"])
        payload = json.loads(out)
        self.assertEqual(payload["da_rigenerare"], [])
        self.assertEqual(payload["cornice_aggiornabile"], [slug])
        self.assertIn("opzionale", payload["prossimo_passo"])
        code, out = run(["list", "--json"])
        row = json.loads(out)["argomenti"][0]
        self.assertFalse(row["da_rigenerare"])
        self.assertTrue(row["cornice_aggiornabile"])

    def test_versione_illeggibile_conta_come_da_rigenerare(self):
        """Provenienza ignota: meglio ricontrollare che fidarsi."""
        slug = self.crea_completo("Analisi matematica")
        self.set_cornice(slug, "boh")
        code, out = run(["status"])
        self.assertEqual(json.loads(out)["da_rigenerare"], [slug])

    def test_version_major_legge_le_versioni(self):
        self.assertEqual(iv.version_major("2.10.3"), "2")
        self.assertEqual(iv.version_major(" v1"), "1")
        self.assertIsNone(iv.version_major(""))
        self.assertIsNone(iv.version_major(None))

    def test_validate_all_su_cartella_vuota(self):
        code, out = run(["validate", "--all", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["validati"], 0)


class TestProgressiERipasso(BaseIV):
    def test_log_registra_sessione_e_programma_ripasso(self):
        slug = self.crea_completo("Probabilita")
        code, out = run([
            "log", "--topic", slug, "--minutes", "45", "--summary", "Modulo 1",
            "--module", "1", "--concept", "probabilita condizionata", "--grade", "4",
        ])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual(payload["minuti_totali"], 45)
        self.assertEqual(payload["programmati"][0]["intervallo_giorni"], 1)

    def test_voto_basso_finisce_nelle_lacune(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "20",
             "--concept", "teorema di Bayes", "--grade", "1"])
        progress = iv.progress_for(slug, "default")
        self.assertIn("teorema di Bayes", progress["weak_spots"])
        self.assertEqual(progress["concepts"][iv.key_of("teorema di Bayes")]["interval"], 1)

    def test_ripetizione_spaziata_allunga_gli_intervalli(self):
        card = {"reps": 0, "ease": 2.5, "interval": 0, "lapses": 0}
        card = iv.sm2(card, 5)
        self.assertEqual(card["interval"], 1)
        card = iv.sm2(card, 5)
        self.assertEqual(card["interval"], 6)
        card = iv.sm2(card, 5)
        self.assertGreater(card["interval"], 6)
        self.assertGreater(card["due"], date.today().isoformat())
        self.assertGreater(card["ease"], 2.5)

    def test_voto_basso_azzera_l_intervallo(self):
        card = iv.sm2({"reps": 4, "ease": 2.6, "interval": 30, "lapses": 0}, 2)
        self.assertEqual(card["interval"], 1)
        self.assertEqual(card["reps"], 0)
        self.assertEqual(card["lapses"], 1)
        self.assertEqual(card["due"], (date.today() + timedelta(days=1)).isoformat())

    def test_due_elenca_i_ripassi_in_scadenza(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30",
             "--concept", "teorema di Bayes", "--grade", "1"])
        progress = iv.progress_for(slug, "default")
        progress["concepts"][iv.key_of("teorema di Bayes")]["due"] = date.today().isoformat()
        iv.write_progress(slug, progress, "default")
        code, out = run(["due", "--within", "0", "--json"])
        self.assertEqual(len(json.loads(out)["concetti_da_ripassare"]), 1)

    def test_stats_genera_il_diario(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "60", "--summary", "giro completo",
             "--concept", "Bayes", "--grade", "5"])
        code, out = run(["stats", "--write", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["minuti_totali"], 60)
        self.assertIn("Diario di apprendimento", payload["riassunto"])
        self.assertTrue((iv.PROGRESS_DIR / "default" / "DIARIO.md").exists())

    def test_progressi_separati_per_allievo(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "marco"])
        self.assertEqual(iv.progress_for(slug, "marco")["total_minutes"], 30)
        self.assertEqual(iv.progress_for(slug, "default")["total_minutes"], 0)

    def test_show_riassume_argomento_e_progressi(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10"])
        code, out = run(["show", slug])
        payload = json.loads(out)
        self.assertEqual(payload["progressi"]["sessioni"], 1)
        self.assertTrue(payload["file"])

    def test_log_senza_livello_eredita_quello_del_meta(self):
        slug = self.crea("Probabilita", level=3)
        fill_topic(slug, "Probabilita", iv.topic_dir(slug))
        run(["register", slug])
        run(["log", "--topic", slug, "--minutes", "10"])
        self.assertEqual(iv.progress_for(slug, "default")["level"], 3)

    def test_livello_esplicito_prevale_sul_meta(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--level", "3"])
        self.assertEqual(iv.progress_for(slug, "default")["level"], 3)


class TestIndiceDerivato(BaseIV):
    """Il registro e' un file derivato dai meta.json: deve auto-ricostruirsi."""

    def test_registro_assente_viene_ricostruito_e_salvato_su_disco(self):
        slug = self.crea_completo("Metodo Feynman")
        iv.REGISTRY.unlink()
        code, out = run(["list", "--json"])
        self.assertEqual(json.loads(out)["argomenti"][0]["slug"], slug)
        salvato = json.loads(iv.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual([e["slug"] for e in salvato["topics"]], [slug])
        self.assertEqual(salvato["alias_index"]["metodo-feynman"], slug)

    def test_alias_scritto_nel_meta_sopravvive_alla_ricostruzione(self):
        """Su un clone l'indice riparte dai meta.json: gli alias non si perdono."""
        slug = self.crea_completo("Roma antica")
        run(["alias", slug, "--add", "Impero romano"])
        iv.REGISTRY.unlink()
        code, out = run(["find", "Impero romano", "--json"])
        self.assertEqual(json.loads(out)["status"], "exact")
        salvato = json.loads(iv.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(salvato["alias_index"][iv.norm("Impero romano")], slug)

    def test_indice_allineato_non_viene_riscritto(self):
        self.crea_completo("Metodo Feynman")
        run(["list", "--json"])
        prima = iv.REGISTRY.stat().st_mtime_ns
        time.sleep(0.01)
        run(["status"])
        self.assertEqual(iv.REGISTRY.stat().st_mtime_ns, prima)


class TestGaranzieSuiDatiRegistrati(BaseIV):
    """Errori veri osservati con agenti diversi (opencode, Pi, modello locale)."""

    def test_log_eredita_la_modalita_dal_meta(self):
        """Senza ereditarla il diario registrava `modalita: null` su un corso in docenza."""
        slug = self.crea("Probabilita", mode="docenza")
        fill_topic(slug, "Probabilita", iv.topic_dir(slug))
        run(["register", slug])
        run(["log", "--topic", slug, "--minutes", "30"])
        progress = iv.progress_for(slug, "default")
        self.assertEqual(progress["mode"], "docenza")
        self.assertEqual(progress["log"][0]["modalita"], "docenza")

    def test_modalita_esplicita_prevale_sul_meta(self):
        slug = self.crea("Probabilita", mode="docenza")
        fill_topic(slug, "Probabilita", iv.topic_dir(slug))
        run(["register", slug])
        run(["log", "--topic", slug, "--minutes", "30", "--mode", "esame"])
        self.assertEqual(iv.progress_for(slug, "default")["mode"], "esame")

    def test_log_rifiuta_un_marcatore_di_sessione(self):
        """'fine sessione' come concetto creava una lacuna finta e un ripasso inutile."""
        slug = self.crea_completo("Probabilita")
        code, out = run(["log", "--topic", slug, "--minutes", "30",
                         "--concept", "fine sessione: moduli 1-3 completati", "--grade", "4"])
        self.assertEqual(code, 1)
        self.assertIn("sessione", json.loads(out)["error"])
        progress = iv.progress_for(slug, "default")
        self.assertEqual(progress["concepts"], {})
        self.assertEqual(progress["weak_spots"], [])

    def test_log_rifiuta_un_avvio_percorso(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["log", "--topic", slug, "--minutes", "5",
                         "--concept", "avvio percorso", "--grade", "0"])
        self.assertEqual(code, 1)
        self.assertEqual(iv.progress_for(slug, "default")["concepts"], {})

    def test_log_accetta_concetti_che_nominano_un_modulo(self):
        """La guardia non deve colpire i contenuti veri che citano 'modulo'."""
        slug = self.crea_completo("Probabilita")
        code, out = run(["log", "--topic", slug, "--minutes", "30",
                         "--concept", "il modulo 3: somma pesata e ReLU", "--grade", "4"])
        self.assertEqual(code, 0, out)
        codice = json.loads(out)["programmati"][0]["concetto"]
        self.assertIn("somma pesata", codice)

    def test_profilo_allievo_non_sensibile_a_maiuscole(self):
        """'Dario' e 'dario' devono restare lo stesso profilo, non due."""
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Dario"])
        self.assertEqual(iv.progress_for(slug, "dario")["total_minutes"], 30)
        self.assertEqual(len(iv.learner_profiles()), 1)

    def test_list_segnala_i_progressi_di_altri_profili(self):
        """La tabella non deve dire 'mai' su un argomento studiato in un altro profilo."""
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Dario"])
        code, out = run(["list", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["argomenti"][0]["sessioni"], 0)
        self.assertEqual(payload["altri_profili"][0]["learner"], "Dario")
        code, out = run(["list"])
        self.assertIn("Dario", out)

    def test_status_indica_dove_sono_i_progressi(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Dario"])
        code, out = run(["status"])
        self.assertIn("Dario", json.loads(out)["prossimo_passo"])

    def test_log_aggiorna_il_diario(self):
        """Il diario e' derivato: non deve restare indietro se l'agente salta stats --write."""
        slug = self.crea_completo("Probabilita")
        diary = iv.PROGRESS_DIR / "default" / "DIARIO.md"
        self.assertFalse(diary.exists())
        code, out = run(["log", "--topic", slug, "--minutes", "45", "--summary", "Modulo 1"])
        self.assertEqual(code, 0, out)
        self.assertTrue(diary.exists())
        self.assertEqual(Path(json.loads(out)["diario"]), diary)
        testo = diary.read_text(encoding="utf-8")
        self.assertIn("45", testo)
        self.assertIn("Sessioni registrate | 1", testo)

    def test_prereq_multipli_diventano_voci_distinte(self):
        slug = self.crea("Probabilita", prereq="programmazione di base; concetti di base dell'AI")
        meta = json.loads((iv.topic_dir(slug) / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["prereqs"], ["programmazione di base", "concetti di base dell'AI"])


class TestProfiliAllievo(BaseIV):
    """Due nomi per la stessa persona non devono spezzare la storia di studio."""

    def test_merge_unifica_i_progressi(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "60", "--concept", "Bayes", "--grade", "5"])
        run(["log", "--topic", slug, "--minutes", "15", "--concept", "Bayes", "--grade", "3",
             "--learner", "Dario"])
        code, out = run(["learner", "merge", "default", "--into", "Dario"])
        self.assertEqual(code, 0, out)
        data = iv.progress_for(slug, "Dario")
        self.assertEqual(data["sessions"], 2)
        self.assertEqual(data["total_minutes"], 75)
        self.assertEqual(len(data["concepts"]), 1)
        self.assertEqual(json.loads(out)["alias_registrato"], {"default": "Dario"})
        self.assertFalse((iv.PROGRESS_DIR / "default").exists())

    def test_dopo_il_merge_il_nome_vecchio_scrive_nel_profilo_nuovo(self):
        """Un agente che omette --learner non deve ricreare il profilo assorbito."""
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Dario"])
        run(["log", "--topic", slug, "--minutes", "10"])
        run(["learner", "merge", "default", "--into", "Dario"])
        run(["log", "--topic", slug, "--minutes", "20"])  # nessun --learner
        self.assertEqual(iv.progress_for(slug, "default")["total_minutes"], 60)
        self.assertEqual(iv.learner_profiles(), ["Dario"])
        self.assertTrue((iv.PROGRESS_DIR / "Dario" / "DIARIO.md").exists())

    def test_merge_conserva_la_scheda_piu_avanzata(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--concept", "Bayes", "--grade", "4"])
        for _ in range(2):
            run(["log", "--topic", slug, "--minutes", "10", "--concept", "Bayes", "--grade", "5",
                 "--learner", "Dario"])
        run(["learner", "merge", "default", "--into", "Dario"])
        card = iv.progress_for(slug, "Dario")["concepts"][iv.key_of("Bayes")]
        self.assertEqual(card["reps"], 2)
        self.assertGreaterEqual(card["interval"], 6)

    def test_merge_rifiuta_lo_stesso_profilo(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Dario"])
        code, out = run(["learner", "merge", "dario", "--into", "Dario"])
        self.assertEqual(code, 1)
        self.assertIn("stesso profilo", json.loads(out)["error"])

    def test_merge_senza_progressi_avvisa(self):
        self.crea_completo("Probabilita")
        code, out = run(["learner", "merge", "nessuno", "--into", "Dario"])
        self.assertEqual(code, 1)
        self.assertIn("nessuno", json.loads(out)["error"])

    def test_un_nuovo_allievo_si_crea_col_primo_log(self):
        """Per un secondo studente basta dichiararlo: non c'e' nulla da registrare a mano."""
        slug = self.crea_completo("Probabilita")
        code, out = run(["log", "--topic", slug, "--minutes", "40", "--summary", "Modulo 1",
                         "--concept", "Bayes", "--grade", "4", "--learner", "Marco Rossi"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["learner"], "Marco Rossi")
        profile = iv.PROGRESS_DIR / "Marco Rossi"
        self.assertTrue((profile / f"{slug}.json").exists())
        self.assertTrue((profile / "DIARIO.md").exists())
        self.assertIn("Marco Rossi", (profile / "DIARIO.md").read_text(encoding="utf-8"))

    def test_due_allievi_non_si_mescolano(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "40", "--concept", "Bayes", "--grade", "4",
             "--learner", "Marco"])
        run(["log", "--topic", slug, "--minutes", "10", "--concept", "Bayes", "--grade", "2",
             "--learner", "Giulia"])
        self.assertEqual(iv.progress_for(slug, "Marco")["total_minutes"], 40)
        self.assertEqual(iv.progress_for(slug, "Giulia")["total_minutes"], 10)
        self.assertEqual(iv.progress_for(slug, "Marco")["concepts"][iv.key_of("Bayes")]["last_grade"], 4)
        self.assertEqual(iv.progress_for(slug, "Giulia")["weak_spots"], ["Bayes"])
        self.assertEqual(len(iv.learner_profiles()), 2)

    def test_nome_con_maiuscole_diverse_resta_un_profilo(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "15", "--learner", "Marco Rossi"])
        run(["log", "--topic", slug, "--minutes", "5", "--learner", "marco rossi"])
        self.assertEqual(iv.learner_profiles(), ["Marco Rossi"])
        self.assertEqual(iv.progress_for(slug, "marco rossi")["total_minutes"], 20)

    def test_nome_con_caratteri_di_percorso_rifiutato(self):
        """Un nome relativo scriverebbe fuori da data/progress/: va bloccato."""
        slug = self.crea_completo("Probabilita")
        for name in ["../fuori", "a/b", "..\\x"]:
            code, out = run(["log", "--topic", slug, "--minutes", "5", "--learner", name])
            self.assertEqual(code, 1, name)
            self.assertIn("non ammessi", json.loads(out)["error"])
        # `../fuori` avrebbe scritto in data/fuori, un livello sopra i progressi
        self.assertFalse((iv.PROGRESS_DIR.parent / "fuori").exists())
        self.assertFalse(iv.learner_profiles())

    def test_nome_di_soli_punti_rifiutato(self):
        self.assertEqual(iv.clean_profile_name("Marco Rossi"), "Marco Rossi")
        self.assertEqual(iv.clean_profile_name("  Marco   Rossi "), "Marco Rossi")
        scarto = io.StringIO()
        with contextlib.redirect_stdout(scarto):
            with self.assertRaises(SystemExit):
                iv.clean_profile_name("...")
            with self.assertRaises(SystemExit):
                iv.clean_profile_name("x" * 61)

    def test_nome_vuoto_resta_anonimo(self):
        """Chi non vuole dare un nome non deve essere bloccato: profilo `default`."""
        slug = self.crea_completo("Probabilita")
        code, out = run(["log", "--topic", slug, "--minutes", "5", "--learner", "   "])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["learner"], "default")
        self.assertEqual(iv.learner_profiles(), ["default"])

    def test_rinomina_uno_studente_con_merge(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Giulia"])
        code, out = run(["learner", "merge", "Giulia", "--into", "Giulia Bianchi"])
        self.assertEqual(code, 0, out)
        self.assertEqual(iv.progress_for(slug, "Giulia")["total_minutes"], 10)
        self.assertEqual(iv.learner_profiles(), ["Giulia Bianchi"])
        self.assertEqual(iv.profile_aliases(), {"Giulia": "Giulia Bianchi"})

    def test_rename_sposta_i_progressi_e_lascia_un_alias(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--concept", "Bayes", "--grade", "5",
             "--learner", "Marco Rossi"])
        code, out = run(["learner", "rename", "Marco Rossi", "--to", "Marco Rosi"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual((payload["da"], payload["a"]), ("Marco Rossi", "Marco Rosi"))
        self.assertEqual(iv.learner_profiles(), ["Marco Rosi"])
        self.assertTrue((iv.PROGRESS_DIR / "Marco Rosi" / "DIARIO.md").exists())
        # il vecchio nome continua a scrivere nel profilo giusto
        run(["log", "--topic", slug, "--minutes", "5", "--learner", "Marco Rossi"])
        self.assertEqual(iv.progress_for(slug, "Marco Rossi")["total_minutes"], 35)
        self.assertEqual(iv.learner_profiles(), ["Marco Rosi"])
        salvato = json.loads((iv.PROGRESS_DIR / "Marco Rosi" / f"{slug}.json").read_text(encoding="utf-8"))
        self.assertEqual(salvato["learner"], "Marco Rosi")

    def test_rename_di_solo_maiuscole(self):
        """Su Windows una rinomina che cambia solo maiuscole puo' fallire: si passa da un nome temporaneo."""
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Giulia"])
        code, out = run(["learner", "rename", "Giulia", "--to", "GIULIA"])
        self.assertEqual(code, 0, out)
        self.assertEqual(iv.learner_profiles(), ["GIULIA"])
        self.assertEqual(iv.progress_for(slug, "giulia")["total_minutes"], 10)

    def test_rename_rifiuta_se_la_destinazione_ha_progressi(self):
        """Due profili con progressi non si rinominano insieme: e' un'unione, va chiesta come tale."""
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Luca"])
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Marco"])
        code, out = run(["learner", "rename", "Luca", "--to", "Marco"])
        self.assertEqual(code, 1)
        self.assertIn("learner merge", json.loads(out)["error"])
        self.assertEqual(sorted(iv.learner_profiles()), ["Luca", "Marco"])

    def test_rename_di_un_profilo_inesistente(self):
        self.crea_completo("Probabilita")
        code, out = run(["learner", "rename", "Nessuno", "--to", "Qualcuno"])
        self.assertEqual(code, 1)
        self.assertIn("Nessuno", json.loads(out)["error"])

    def test_delete_senza_conferma_non_cancella_niente(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Marco"])
        code, out = run(["learner", "delete", "Marco"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["sessioni"], 1)
        self.assertEqual(payload["minuti"], 30)
        self.assertIn("--yes", payload["conferma"])
        self.assertTrue((iv.PROGRESS_DIR / "Marco").is_dir())

    def test_delete_con_conferma_toglie_profilo_e_alias(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Giulia"])
        run(["learner", "rename", "Giulia", "--to", "Giulia Bianchi"])
        code, out = run(["learner", "delete", "Giulia Bianchi", "--yes"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["alias_rimossi"], ["Giulia"])
        self.assertEqual(iv.learner_profiles(), [])
        self.assertEqual(iv.profile_aliases(), {})
        # niente profilo zombie: il vecchio alias riparte da un profilo con il suo nome
        run(["log", "--topic", slug, "--minutes", "5", "--learner", "Giulia"])
        self.assertEqual(iv.learner_profiles(), ["Giulia"])
        self.assertEqual(iv.progress_for(slug, "Giulia")["total_minutes"], 5)

    def test_delete_non_tocca_le_sotto_skill_gli_argomenti_e_gli_altri_profili(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Marco"])
        run(["log", "--topic", slug, "--minutes", "20", "--learner", "Giulia"])
        code, out = run(["learner", "delete", "Marco", "--yes"])
        self.assertEqual(code, 0, out)
        self.assertEqual(iv.learner_profiles(), ["Giulia"])
        self.assertEqual(iv.progress_for(slug, "Giulia")["total_minutes"], 20)
        self.assertTrue((iv.topic_dir(slug) / "SKILL.md").exists())
        code, out = run(["validate", slug, "--json"])
        self.assertEqual(code, 0, out)

    def test_learner_list_mostra_profili_e_alias(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30"])
        run(["log", "--topic", slug, "--minutes", "20", "--learner", "Dario"])
        code, out = run(["learner", "list", "--json"])
        payload = json.loads(out)
        self.assertEqual([r["learner"] for r in payload["profili"]], ["Dario", "default"])
        code, out = run(["learner", "merge", "default", "--into", "Dario"])
        code, out = run(["learner", "list", "--json"])
        payload = json.loads(out)
        self.assertEqual([r["learner"] for r in payload["profili"]], ["Dario"])
        self.assertEqual(payload["profili"][0]["minuti"], 50)
        self.assertEqual(payload["alias"], {"default": "Dario"})


class TestPersonaDichiarata(BaseIV):
    """La persona (chi studia, con che registro, con quanto tempo) non e' un argomento.

    Vive nella cartella del profilo come `_persona.json` e non deve mai essere
    scambiata per una storia di studio: ne' dai conteggi, ne' da `merge`.
    """

    def test_persona_non_conta_come_argomento(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--learner", "Dario"])
        code, out = run(["learner", "persona", "--learner", "Dario", "--banda-eta", "adulto"])
        self.assertEqual(code, 0, out)
        code, out = run(["learner", "list", "--json"])
        riga = [r for r in json.loads(out)["profili"] if r["learner"] == "Dario"][0]
        self.assertEqual((riga["argomenti"], riga["minuti"]), (1, 30))
        self.assertEqual([d["slug"] for d in iv.all_progress("Dario")], [slug])
        code, out = run(["stats", "--learner", "Dario"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("_persona", out)
        self.assertNotIn("_persona", json.dumps(iv.due_items("Dario", 30)))

    def test_dichiara_e_rilegge_la_persona(self):
        code, out = run(["learner", "persona", "--learner", "Dario", "--banda-eta", "ragazzo",
                         "--configurato-da", "il padre", "--budget-minuti", "180",
                         "--scadenza", "2026-12-15", "--obiettivo", "27/30"])
        self.assertEqual(code, 0, out)
        persona = json.loads(out)["persona"]
        self.assertEqual(persona["banda_eta"], "ragazzo")
        self.assertEqual(persona["banda_eta_aggiornata"], date.today().isoformat())
        self.assertEqual(persona["budget_minuti_settimana"], 180)
        self.assertEqual(persona["scadenza"], {"data": "2026-12-15", "obiettivo": "27/30",
                                                "argomento": None})
        code, out = run(["learner", "persona", "--learner", "dario", "--json"])
        payload = json.loads(out)
        self.assertTrue(payload["esiste"])
        self.assertEqual(payload["learner"], "Dario")
        self.assertEqual(payload["persona"]["configurato_da"], "il padre")

    def test_leggere_una_persona_assente_non_crea_profili(self):
        code, out = run(["learner", "persona", "--learner", "Dario"])
        self.assertEqual(code, 0, out)
        self.assertIn("Nessuna persona dichiarata", out)
        self.assertEqual(iv.learner_profiles(), [])

    def test_lo_stesso_argomento_per_un_bambino_e_un_adulto(self):
        """La persona non entra nella sotto-skill: l'argomento resta lo stesso per tutti."""
        slug = self.crea_completo("Probabilita")
        run(["learner", "persona", "--learner", "Giulia", "--banda-eta", "bambino"])
        run(["learner", "persona", "--learner", "Dario", "--banda-eta", "adulto"])
        self.assertEqual(iv.read_persona("Giulia")["banda_eta"], "bambino")
        self.assertEqual(iv.read_persona("Dario")["banda_eta"], "adulto")
        meta = (iv.topic_dir(slug) / "meta.json").read_text(encoding="utf-8")
        self.assertNotIn("banda_eta", meta)

    def test_merge_adotta_la_persona_del_profilo_assorbito(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "default"])
        run(["learner", "persona", "--learner", "default", "--banda-eta", "ragazzo"])
        code, out = run(["learner", "merge", "default", "--into", "Dario"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["persona"], "adottata")
        self.assertEqual(iv.read_persona("Dario")["banda_eta"], "ragazzo")
        self.assertEqual(iv.learner_profiles(), ["Dario"])

    def test_merge_tiene_la_persona_della_destinazione(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "default"])
        run(["learner", "persona", "--learner", "default", "--banda-eta", "bambino"])
        run(["learner", "persona", "--learner", "Dario", "--banda-eta", "adulto"])
        code, out = run(["learner", "merge", "default", "--into", "Dario"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["persona"], "destinazione")
        self.assertEqual(iv.read_persona("Dario")["banda_eta"], "adulto")
        self.assertFalse((iv.PROGRESS_DIR / "default").exists())

    def test_merge_di_un_profilo_che_ha_solo_la_persona(self):
        """Anche senza progressi il profilo assorbito non deve restare in giro da solo."""
        self.crea_completo("Probabilita")
        run(["learner", "persona", "--learner", "Giulia", "--banda-eta", "bambino"])
        code, out = run(["learner", "merge", "Giulia", "--into", "Dario"])
        self.assertEqual(code, 0, out)
        self.assertEqual(iv.read_persona("Dario")["banda_eta"], "bambino")
        self.assertEqual(iv.learner_profiles(), ["Dario"])

    def test_rename_porta_con_se_la_persona(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "10", "--learner", "Marco Rosi"])
        run(["learner", "persona", "--learner", "Marco Rosi", "--banda-eta", "adulto"])
        code, out = run(["learner", "rename", "Marco Rosi", "--to", "Marco Rossi"])
        self.assertEqual(code, 0, out)
        persona = iv.read_persona("Marco Rossi")
        self.assertEqual((persona["banda_eta"], persona["learner"]), ("adulto", "Marco Rossi"))
        self.assertFalse((iv.PROGRESS_DIR / "Marco Rosi" / "_persona.json").exists())
        self.assertEqual(iv.read_persona("Marco Rosi")["banda_eta"], "adulto")

    def test_reset_dimentica_la_persona_ma_non_i_progressi(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "25", "--learner", "Dario"])
        run(["learner", "persona", "--learner", "Dario", "--banda-eta", "adulto"])
        code, out = run(["learner", "persona", "--learner", "Dario", "--reset"])
        self.assertEqual(code, 0, out)
        self.assertFalse((iv.PROGRESS_DIR / "Dario" / "_persona.json").exists())
        self.assertEqual(iv.progress_for(slug, "Dario")["total_minutes"], 25)
        self.assertEqual(iv.learner_profiles(), ["Dario"])

    def test_reset_su_un_profilo_senza_progressi_toglie_anche_la_cartella(self):
        run(["learner", "persona", "--learner", "Giulia", "--banda-eta", "bambino"])
        code, out = run(["learner", "persona", "--learner", "Giulia", "--reset"])
        self.assertEqual(code, 0, out)
        self.assertEqual(iv.learner_profiles(), [])

    def test_reset_senza_persona_avvisa(self):
        code, out = run(["learner", "persona", "--learner", "Giulia", "--reset"])
        self.assertEqual(code, 1)
        self.assertIn("non ha una persona", json.loads(out)["error"])

    def test_scadenza_in_formato_sbagliato_rifiutata(self):
        code, out = run(["learner", "persona", "--banda-eta", "adulto", "--scadenza", "15/12/2026"])
        self.assertEqual(code, 1)
        self.assertIn("YYYY-MM-DD", json.loads(out)["error"])
        self.assertEqual(iv.learner_profiles(), [])   # nessun profilo a meta'

    def test_obiettivo_senza_scadenza_rifiutato(self):
        code, out = run(["learner", "persona", "--obiettivo", "27/30"])
        self.assertEqual(code, 1)
        self.assertIn("--scadenza", json.loads(out)["error"])

    def test_senza_scadenza_la_dimentica_e_lascia_il_resto(self):
        run(["learner", "persona", "--banda-eta", "adulto", "--scadenza", "2026-12-15"])
        code, out = run(["learner", "persona", "--senza-scadenza"])
        self.assertEqual(code, 0, out)
        persona = json.loads(out)["persona"]
        self.assertIsNone(persona["scadenza"])
        self.assertEqual(persona["banda_eta"], "adulto")

    def test_budget_non_positivo_rifiutato(self):
        code, out = run(["learner", "persona", "--budget-minuti", "0"])
        self.assertEqual(code, 1)
        self.assertIn("maggiore di zero", json.loads(out)["error"])

    def test_delete_anteprima_dichiara_la_persona(self):
        run(["learner", "persona", "--learner", "Marco", "--banda-eta", "bambino"])
        code, out = run(["learner", "delete", "Marco"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["persona"]["banda_eta"], "bambino")
        self.assertEqual(payload["argomenti"], 0)
        self.assertTrue((iv.PROGRESS_DIR / "Marco").is_dir())

    def test_campi_aggiunti_da_un_agente_non_si_perdono(self):
        run(["learner", "persona", "--banda-eta", "adulto"])
        path = iv.PROGRESS_DIR / "default" / "_persona.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["nota_di_un_agente"] = "campo aggiunto"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(["learner", "persona", "--budget-minuti", "60"])
        aggiornata = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(aggiornata["nota_di_un_agente"], "campo aggiunto")
        self.assertEqual(aggiornata["banda_eta"], "adulto")


class TestRegistroDellaPersona(BaseIV):
    """Il registro dice *come* si parla: stringe gli obiettivi del livello, mai li allenta."""

    FITTO = "uno, due, tre, quattro, cinque, sei. sette, otto, nove, dieci, undici, dodici. " * 2

    def test_precedenza_sessione_persona_banda(self):
        self.assertEqual(iv.registro_effettivo("Dario"), "standard")
        run(["learner", "persona", "--learner", "Dario", "--banda-eta", "bambino"])
        self.assertEqual(iv.registro_effettivo("Dario"), "bambino")
        run(["learner", "persona", "--learner", "Dario", "--registro", "standard"])
        self.assertEqual(iv.registro_effettivo("Dario"), "standard")
        self.assertEqual(iv.registro_effettivo("Dario", override="scolastico"), "scolastico")
        # il livello suggerito resta quello della banda: il registro non lo tocca
        self.assertEqual(iv.livello_suggerito("Dario"), 1)

    def test_livello_suggerito_solo_se_la_banda_e_dichiarata(self):
        self.assertIsNone(iv.livello_suggerito("Nessuno"))
        run(["learner", "persona", "--learner", "Giulia", "--banda-eta", "adolescente"])
        self.assertEqual(iv.livello_suggerito("Giulia"), 2)

    def test_il_registro_non_allenta_mai_il_livello(self):
        self.assertEqual(iv.style_target(4, "bambino")["gulpease"], 80.0)
        self.assertEqual(iv.style_target(1, "bambino")["parole_frase"], 12.0)
        self.assertEqual(iv.style_target(2, "standard"), iv.STYLE_TARGETS[2])
        self.assertNotIn("virgole_frase", iv.STYLE_TARGETS[2])

    def test_style_con_registro_stringe_l_obiettivo(self):
        lungo = (TestStileMisurabile.LUNGHETTO + " ") * 4
        code, out = run(["style", "--text", lungo, "--level", "4", "--json"])
        self.assertEqual(code, 0, out)
        code, out = run(["style", "--text", lungo, "--level", "4", "--registro", "bambino", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["registro"], "bambino")
        self.assertEqual(payload["criterio"]["parole_frase"], 12.0)
        self.assertTrue(any("registro" in p for p in payload["problemi"]["testo"]), payload["problemi"])

    def test_il_registro_segnala_il_periodare_fitto(self):
        """Frasi corte ma fitte di virgole: semplici in apparenza, difficili da leggere."""
        metrics = iv.style_metrics(self.FITTO)
        self.assertEqual(iv.style_problems(metrics, 2), [])
        problemi = iv.style_problems(metrics, 2, "bambino")
        self.assertTrue(any("virgole" in p for p in problemi), problemi)

    def test_la_persona_espone_registro_effettivo_e_livello(self):
        code, out = run(["learner", "persona", "--learner", "Giulia", "--banda-eta", "bambino"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual(payload["registro_effettivo"], "bambino")
        self.assertEqual(payload["livello_suggerito"], 1)
        code, out = run(["learner", "persona", "--learner", "Giulia", "--json"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["registro_effettivo"], "bambino")
        code, out = run(["learner", "persona", "--learner", "Giulia"])
        self.assertIn("bambino", out)


class TestPianoDiStudio(BaseIV):
    """Scadenza e budget dichiarati devono servire a qualcosa, non restare campi morti."""

    def fra(self, giorni: int) -> str:
        return (date.today() + timedelta(days=giorni)).isoformat()

    def test_senza_persona_non_c_e_piano(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30"])
        self.assertEqual(iv.piano_di_studio("default"), {})
        code, out = run(["status"])
        self.assertEqual(json.loads(out)["piano"], {})
        self.assertIn("Nessun debito tecnico", json.loads(out)["prossimo_passo"])

    def test_moduli_visti_accetta_etichette_libere(self):
        self.assertEqual(iv.moduli_visti({"modules_seen": ["2", "Modulo 3", "modulo 1: somma"]}),
                         {1, 2, 3})
        self.assertEqual(iv.moduli_visti({}), set())

    def test_conta_i_moduli_che_restano(self):
        slug = self.crea_completo("Probabilita")
        self.assertEqual(iv.moduli_nel_topic(slug), 3)
        run(["log", "--topic", slug, "--minutes", "60", "--module", "1"])
        run(["learner", "persona", "--budget-minuti", "300"])
        piano = iv.piano_di_studio("default")
        argomento = piano["argomenti"][0]
        self.assertEqual((argomento["moduli_totali"], argomento["moduli_visti"],
                          argomento["moduli_rimasti"]), (3, 1, 2))
        # 60 minuti su un modulo: la stima usa quello che e' costato davvero
        self.assertEqual(argomento["minuti_stimati_per_modulo"], 60)
        self.assertEqual(piano["minuti_rimasti_stimati"], 120)
        self.assertEqual(piano["minuti_ultimi_7_giorni"], 60)

    def test_budget_e_scadenza_dicono_se_il_materiale_ci_sta(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--module", "1"])
        run(["learner", "persona", "--budget-minuti", "300", "--scadenza", self.fra(7)])
        piano = iv.piano_di_studio("default")
        self.assertEqual(piano["giorni_alla_prova"], 7)
        self.assertEqual(piano["minuti_disponibili_stimati"], 300)
        self.assertTrue(piano["ci_sta"])
        code, out = run(["status"])
        self.assertIn("ci sta", json.loads(out)["prossimo_passo"])

    def test_il_piano_dice_quando_non_ci_sta(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--module", "1"])
        run(["learner", "persona", "--budget-minuti", "30", "--scadenza", self.fra(7)])
        code, out = run(["status"])
        payload = json.loads(out)
        self.assertFalse(payload["piano"]["ci_sta"])
        self.assertIn("non ci sta", payload["prossimo_passo"])

    def test_senza_budget_il_piano_invita_a_dichiararlo(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--module", "1"])
        run(["learner", "persona", "--scadenza", self.fra(10)])
        code, out = run(["status"])
        payload = json.loads(out)
        self.assertIsNone(payload["piano"]["ci_sta"])
        self.assertIn("budget", payload["prossimo_passo"])

    def test_una_prova_passata_si_segnala_e_non_blocca(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "30", "--module", "1"])
        run(["learner", "persona", "--scadenza", self.fra(-1)])
        code, out = run(["status"])
        payload = json.loads(out)
        self.assertEqual(payload["piano"]["giorni_alla_prova"], -1)
        self.assertIn("passata", payload["prossimo_passo"])

    def test_l_argomento_della_prova_entra_nella_stima_anche_se_non_avviato(self):
        """Chi ha una prova su un argomento mai iniziato deve vedere il lavoro che lo aspetta."""
        slug = self.crea_completo("Probabilita")
        run(["learner", "persona", "--budget-minuti", "120", "--scadenza", self.fra(14),
             "--scadenza-argomento", slug])
        piano = iv.piano_di_studio("default")
        self.assertEqual(piano["argomenti"][0]["topic"], slug)
        self.assertEqual(piano["moduli_rimasti"], 3)
        self.assertEqual(piano["minuti_rimasti_stimati"], 3 * iv.MINUTI_PER_MODULO_DEFAULT)

    def test_due_anticipa_i_concetti_che_cadono_dopo_la_prova(self):
        slug = self.crea_completo("Probabilita")
        for _ in range(2):
            run(["log", "--topic", slug, "--minutes", "20", "--concept", "Bayes", "--grade", "5"])
        run(["learner", "persona", "--scadenza", self.fra(3)])
        code, out = run(["due", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["prova"]["giorni_rimasti"], 3)
        self.assertEqual([c["concetto"] for c in payload["prova"]["da_anticipare"]], ["Bayes"])
        self.assertEqual(payload["concetti_da_ripassare"], [])
        code, out = run(["due"])
        self.assertIn("Da anticipare prima della prova", out)

    def test_due_senza_prova_non_cambia_niente(self):
        slug = self.crea_completo("Probabilita")
        run(["log", "--topic", slug, "--minutes", "20", "--concept", "Bayes", "--grade", "5"])
        code, out = run(["due", "--within", "30", "--json"])
        payload = json.loads(out)
        self.assertNotIn("prova", payload)
        self.assertIn("oltre_la_prova", payload["concetti_da_ripassare"][0])
        self.assertFalse(payload["concetti_da_ripassare"][0]["oltre_la_prova"])


class TestLezioneDelDocente(BaseIV):
    """In docenza serve un artefatto verificabile, non la promessa di un artefatto."""

    VALIDA = """# Lezione: Probabilita

| Campo | Valore |
|---|---|
| Classe | 3B |
| Durata | 60 minuti |

## Destinatari e prerequisiti

Sanno contare e leggere una tabella.

## Obiettivo della lezione

Al termine sanno calcolare una probabilita' contando i casi.

## Scaletta

| Minuti | Cosa | Cosa fa la classe |
|---|---|---|
| 10 | Apertura con una domanda | Risponde |
| 25 | Idea centrale ed esempio | Ascolta |
| 15 | Esercizio guidato | Prova da sola |
| 10 | Chiusura e compito | Annota |

## Esempi alla lavagna

- Un dado con sei facce.
- Una moneta lanciata due volte.

## Esercizi con soluzioni

- Quanti casi ha un dado: sei.
- Quanti esiti sono pari: tre.

## Domande probabili

- Prof, ma se il dado e' truccato?
- Prof, conta anche il caso zero?
- Prof, come si scrive in frazione?

## Compiti e materiali

- Leggere la pagina venti.
- Servono dadi e monete.

## Verifica alla prossima lezione

- Cosa vuol dire casi possibili?
- Calcola la probabilita' di un numero pari.
"""

    def lezione(self, slug: str, **kwargs) -> Path:
        argv = ["lezione", slug] + [item for k, v in kwargs.items() for item in (f"--{k}", str(v))]
        code, out = run(argv)
        self.assertEqual(code, 0, out)
        return Path(json.loads(out)["file"])

    def test_crea_lo_scheletro_nei_materiali_del_docente(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        self.assertTrue(path.exists())
        self.assertIn(str(iv.LEZIONI_DIR), str(path))
        self.assertEqual(path.name, f"{date.today().isoformat()}-3b.md")
        # materiale del docente, non progressi dell'allievo e non sotto-skill
        self.assertFalse((iv.PROGRESS_DIR / "default").exists())
        self.assertNotIn("probabilita", [p.name for p in iv.LEZIONI_DIR.parent.glob("*")])

    def test_lo_scheletro_non_passa_il_controllo(self):
        slug = self.crea_completo("Probabilita")
        self.lezione(slug, classe="3B")
        code, out = run(["lezione", slug, "--check", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertGreater(payload["errori"], 0)
        self.assertTrue(any("ISTRUZIONI" in p["messaggio"] for p in payload["problemi"]))

    def test_una_lezione_compilata_passa(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        path.write_text(self.VALIDA, encoding="utf-8")
        code, out = run(["lezione", slug, "--check", "--json"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual(payload["errori"], 0)
        self.assertEqual(payload["livello"], 2)

    def test_una_sezione_mancante_viene_segnalata(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        path.write_text(self.VALIDA.replace("## Domande probabili", "## Altro"), encoding="utf-8")
        code, out = run(["lezione", slug, "--check", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertTrue(any("Domande probabili" in p["messaggio"] for p in payload["problemi"]))

    def test_due_domande_probabili_non_bastano(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        testo = self.VALIDA.replace("- Prof, come si scrive in frazione?\n", "")
        path.write_text(testo, encoding="utf-8")
        code, out = run(["lezione", slug, "--check", "--json"])
        payload = json.loads(out)
        self.assertTrue(any("ne servono almeno 3" in p["messaggio"] for p in payload["problemi"]))

    def test_il_registro_del_docente_alza_l_asticella(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        densa = self.VALIDA + "\n" + (TestStileMisurabile.DENSO + " ") * 20
        path.write_text(densa, encoding="utf-8")
        code, out = run(["lezione", slug, "--check", "--registro", "bambino", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["registro"], "bambino")
        self.assertTrue(any("leggibilita'" in p["messaggio"] for p in payload["problemi"]))

    def test_check_senza_lezioni_avvisa(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["lezione", slug, "--check"])
        self.assertEqual(code, 1)
        self.assertIn("Nessuna lezione salvata", json.loads(out)["error"])

    def test_non_riscrive_in_silenzio_una_lezione_esistente(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        path.write_text(self.VALIDA, encoding="utf-8")
        code, out = run(["lezione", slug, "--classe", "3B"])
        self.assertEqual(code, 1)
        self.assertIn("--force", json.loads(out)["error"])
        self.assertEqual(path.read_text(encoding="utf-8"), self.VALIDA)
        code, out = run(["lezione", slug, "--classe", "3B", "--force"])
        self.assertEqual(code, 0, out)

    def test_lezione_su_argomento_inesistente(self):
        code, out = run(["lezione", "mai-visto", "--classe", "3B"])
        self.assertEqual(code, 1)
        self.assertIn("non nel registro", json.loads(out)["error"])

    def test_data_non_valida_rifiutata(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["lezione", slug, "--classe", "3B", "--giorno", "25/12/2026"])
        self.assertEqual(code, 1)
        self.assertIn("YYYY-MM-DD", json.loads(out)["error"])

    def test_log_registra_la_lezione_consegnata(self):
        slug = self.crea_completo("Probabilita")
        path = self.lezione(slug, classe="3B")
        path.write_text(self.VALIDA, encoding="utf-8")
        code, out = run(["log", "--topic", slug, "--minutes", "60", "--lesson", str(path),
                         "--summary", "Lezione sui casi possibili"])
        self.assertEqual(code, 0, out)
        voce = iv.progress_for(slug, "default")["log"][-1]
        self.assertEqual(voce["lezione"], str(path))

    def test_log_rifiuta_una_lezione_che_non_esiste(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["log", "--topic", slug, "--minutes", "30", "--lesson", "lezioni/mai.md"])
        self.assertEqual(code, 1)
        self.assertIn("non trovato", json.loads(out)["error"])
        self.assertEqual(iv.progress_for(slug, "default")["sessions"], 0)


class TestMaterialiDellUtente(BaseIV):
    """I materiali dell'utente sono la fonte da privilegiare, e restano suoi."""

    def materiale(self, nome: str = "appunti.md", testo: str = "Contenuto di prova.\n") -> Path:
        path = Path(self._tmp.name) / nome
        path.write_text(testo, encoding="utf-8")
        return path

    def test_aggiunge_e_scrive_l_indice(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["materiali", "add", slug, "--file", str(self.materiale()),
                         "--tipo", "appunti", "--titolo", "Appunti del corso"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["totale"], 1)
        cartella = iv.MATERIALI_DIR / slug
        self.assertTrue((cartella / "appunti.md").exists())
        self.assertTrue((cartella / "materiali.json").exists())
        indice = (cartella / "INDICE.md").read_text(encoding="utf-8")
        self.assertIn("Appunti del corso", indice)
        self.assertIn("fonte da privilegiare", indice)

    def test_il_materiale_e_una_copia_non_un_collegamento(self):
        """Se l'utente cancella l'originale, il materiale del corso resta leggibile."""
        slug = self.crea_completo("Probabilita")
        origine = self.materiale()
        run(["materiali", "add", slug, "--file", str(origine)])
        origine.unlink()
        self.assertTrue((iv.MATERIALI_DIR / slug / "appunti.md").exists())

    def test_non_sovrascrive_senza_force(self):
        slug = self.crea_completo("Probabilita")
        origine = self.materiale()
        run(["materiali", "add", slug, "--file", str(origine)])
        code, out = run(["materiali", "add", slug, "--file", str(origine)])
        self.assertEqual(code, 1)
        self.assertIn("--force", json.loads(out)["error"])

    def test_argomento_e_file_inesistenti(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["materiali", "add", "mai-visto", "--file", str(self.materiale())])
        self.assertEqual(code, 1)
        self.assertIn("non nel registro", json.loads(out)["error"])
        code, out = run(["materiali", "add", slug, "--file", "non/esiste.pdf"])
        self.assertEqual(code, 1)
        self.assertIn("File non trovato", json.loads(out)["error"])

    def test_una_voce_senza_file_non_sopravvive(self):
        """`materiali.json` registra, `INDICE.md` racconta: se il file sparisce, la voce no."""
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale())])
        (iv.MATERIALI_DIR / slug / "appunti.md").unlink()
        code, out = run(["materiali", "list", slug, "--json"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["totale"], 0)
        indice = (iv.MATERIALI_DIR / slug / "INDICE.md").read_text(encoding="utf-8")
        self.assertNotIn("appunti.md", indice)
        self.assertIn("nessun materiale", indice)

    def test_list_mostra_gli_argomenti_con_materiali(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale())])
        code, out = run(["materiali", "list"])
        self.assertEqual(code, 0, out)
        self.assertIn(slug, out)
        code, out = run(["materiali", "list", "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["totale"], 1)
        self.assertEqual(payload["argomenti"][0]["argomento"], slug)

    def test_list_su_un_argomento_senza_materiali(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["materiali", "list", slug, "--json"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["totale"], 0)

    def test_la_lista_degli_argomenti_dichiara_i_materiali(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale())])
        code, out = run(["list", "--json"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["argomenti"][0]["materiali"], 1)

    def test_i_materiali_non_finiscono_nei_topic_nei_progressi(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale())])
        self.assertFalse((iv.topic_dir(slug) / "appunti.md").exists())
        self.assertFalse((iv.PROGRESS_DIR / "default").exists())
        self.assertEqual(iv.all_progress("default"), [])


class TestRicercaNeiMateriali(BaseIV):
    """Il testo trascritto rende il materiale cercabile: e' l'unico "RAG" che c'e'.

    Lessicale, locale, senza dipendenze: il motore non legge PDF e non capisce i
    sinonimi. Questi test difendono i limiti dichiarati, non solo la funzionalita'.
    """

    PARAGRAFO_1 = (
        "## Capitolo 1 — Spazi campionari\n\n"
        "Uno spazio campionario e' l'insieme di tutti i risultati possibili di un "
        "esperimento. Un evento e' un sottoinsieme dello spazio campionario, e si dice "
        "certo quando coincide con tutto l'insieme.\n\n"
    )
    PARAGRAFO_2 = (
        "## Capitolo 2 — Probabilita' condizionata\n\n"
        "La probabilita' condizionata di A dato B si ottiene dividendo la probabilita' "
        "dell'intersezione per la probabilita' di B, purche' B non abbia probabilita' "
        "nulla. La formula regge anche quando gli eventi non sono indipendenti.\n"
    )

    def materiale(self, nome: str = "appunti.md", testo: str = "Contenuto di prova.\n") -> Path:
        path = Path(self._tmp.name) / nome
        path.write_text(testo, encoding="utf-8")
        return path

    def collegato(self, slug: str, testo: str | None = None, pagine: str = "1",
                  extra: list[str] | None = None) -> str:
        """Un argomento con un materiale e il suo testo trascritto, gia' cercabile."""
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        # Il nome del file di origine — non quello del materiale — da' il nome alla copia:
        # cosi' due estratti dello stesso documento convivono (vedi `test_due_estratti...`).
        origine = self.materiale("programma.txt", testo or (self.PARAGRAFO_1 + self.PARAGRAFO_2))
        code, out = run(["materiali", "testo", slug, "--material", "programma.pdf",
                         "--file", str(origine), "--pagine", pagine] + (extra or []))
        self.assertEqual(code, 0, out)
        return out

    def corpus(self, pagine: int) -> str:
        """Un testo lungo quanto `pagine` pagine vere: ~2000 caratteri ciascuna."""
        frase = ("Un evento e' un sottoinsieme dello spazio campionario e la sua probabilita' "
                 "si somma a quella degli altri eventi disgiunti. ")
        return "# Appunti del corso\n\n" + frase * (pagine * 18)

    def test_un_materiale_senza_testo_non_e_cercabile_ma_non_e_vuoto(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        code, out = run(["materiali", "search", slug, "probabilita condizionata", "--json"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual(payload["trovati"], 0)
        # Il vuoto non e' una prova: il payload dice cosa non ha potuto cercare.
        self.assertEqual(payload["materiali_senza_testo"], ["programma.pdf"])
        self.assertEqual(payload["blocchi_cercati"], 0)

    def test_il_testo_trascritto_rende_il_materiale_cercabile(self):
        slug = self.crea_completo("Probabilita")
        out = self.collegato(slug)
        self.assertEqual(json.loads(out)["caratteri"] > 0, True)
        code, out = run(["materiali", "search", slug, "probabilita condizionata", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0, out)
        self.assertEqual(payload["trovati"], 1)
        self.assertEqual(payload["blocchi_cercati"], 2)   # due capitoli, un blocco ciascuno
        primo = payload["risultati"][0]
        self.assertEqual(primo["materiale"], "programma.pdf")
        self.assertEqual(primo["pagine"], "1")
        self.assertIn("probabilita' condizionata", primo["estratto"])
        self.assertGreater(primo["riga"], 0)   # citabile: "programma.pdf, riga N"

    def test_la_ricerca_e_lessicale_e_lo_dichiara(self):
        """I sinonimi non si trovano: e' un limite dichiarato, non un bug nascosto."""
        slug = self.crea_completo("Probabilita")
        self.collegato(slug)
        code, out = run(["materiali", "search", slug, "dipendenza stocastica", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0, out)
        self.assertEqual(payload["trovati"], 0)
        self.assertIn("lessicale", payload["metodo"])
        self.assertIn("sinonim", payload["metodo"])

    def test_il_blocco_che_contiene_tutta_la_query_viene_prima(self):
        slug = self.crea_completo("Probabilita")
        self.collegato(slug)
        code, out = run(["materiali", "search", slug, "spazio campionario evento", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0, out)
        primi = payload["risultati"]
        self.assertEqual(primi[0]["punteggio"], 1.0)
        self.assertIn("Uno spazio campionario", primi[0]["estratto"])
        # L'altro capitolo condivide una parola sola: sta sotto, non alla pari.
        self.assertEqual([r["punteggio"] for r in primi[1:]], [0.333])
        self.assertIn("Capitolo 1", primi[0]["estratto"])   # il titolo resta nel blocco

    def test_due_estratti_dello_stesso_materiale_convivono_e_si_cercano_entrambi(self):
        """Visto sul campo: il secondo estratto cancellava il primo, in silenzio.

        Due modi di estrarre lo stesso PDF (`-layout` e non) hanno contenuti diversi e
        servono entrambi: le pagine con tabelle e quelle con riquadri centrati. Il nome
        della copia viene dal file di origine, quindi non si sovrascrivono.
        """
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])

        def capitolo(marcatore: str) -> str:
            riempimento = "Questa parte serve solo a superare il minimo di caratteri. " * 12
            return f"# Capitolo\n\nNota sul {marcatore}: {riempimento}"

        for nome, testo in (("capitolo-1-layout.txt", capitolo("spazio campionario")),
                            ("capitolo-1-flow.txt", capitolo("probabilita' condizionata"))):
            code, out = run(["materiali", "testo", slug, "--material", "programma.pdf",
                             "--file", str(self.materiale(nome, testo)), "--pagine", "1"])
            self.assertEqual(code, 0, out)
            self.assertFalse(json.loads(out)["sostituito"])
            self.assertEqual(len(json.loads(out)["testi_del_materiale"]),
                             1 if nome.endswith("layout.txt") else 2)
        code, out = run(["materiali", "search", slug, "spazio campionario", "--json"])
        self.assertEqual(json.loads(out)["trovati"], 1)   # il primo estratto c'e' ancora
        code, out = run(["materiali", "search", slug, "probabilita' condizionata", "--json"])
        self.assertEqual(json.loads(out)["trovati"], 1)   # e c'e' anche il secondo
        code, out = run(["materiali", "list", slug])
        self.assertIn("2 testi", out)

    def test_lo_stesso_estratto_rifatto_aggiorna_e_lo_dichiara(self):
        """Rifare l'estrazione dello stesso file e' un aggiornamento, non una perdita."""
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        origine = self.materiale("capitolo-1.txt", self.PARAGRAFO_1 * 3)
        comando = ["materiali", "testo", slug, "--material", "programma.pdf",
                   "--file", str(origine), "--pagine", "1"]
        code, primo = run(comando)
        self.assertEqual(code, 0, primo)
        self.assertEqual(json.loads(primo)["testi_del_materiale"], ["capitolo-1.estratto.md"])
        code, out = run(comando)
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertTrue(payload["sostituito"])
        self.assertEqual(payload["testi_del_materiale"], ["capitolo-1.estratto.md"])
        self.assertIn("Aggiornata", " ".join(payload["avvisi"]))

    def test_i_blocchi_sono_fini_abbastanza_da_essere_una_citazione(self):
        """Visto sul campo: senza `-layout` una pagina intera diventava un blocco solo,
        e «riga 1» non e' una citazione che si possa andare a controllare."""
        lungo = " ".join(f"Frase numero {n} sullo spazio campionario." for n in range(1, 61))
        blocchi = iv.chunk_di_testo("# Appunti\n\n" + lungo)
        self.assertGreaterEqual(len(blocchi), 3)
        self.assertTrue(all(len(b["testo"]) <= iv.CHUNK_CARATTERI + 200 for b in blocchi))
        self.assertLessEqual(iv.CHUNK_CARATTERI, 600)

    def test_si_cerca_un_argomento_per_volta(self):
        uno = self.crea_completo("Probabilita")
        altro = self.crea_completo("Statistica descrittiva")
        self.collegato(altro)
        code, out = run(["materiali", "search", uno, "probabilita condizionata", "--json"])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["trovati"], 0)

    def test_rifiuta_un_testo_troppo_corto(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        corto = self.materiale("pezzo.md", "due parole\n")
        code, out = run(["materiali", "testo", slug, "--material", "programma.pdf",
                         "--file", str(corto)])
        self.assertEqual(code, 1)
        self.assertIn("troppo corto", json.loads(out)["error"])

    def test_rifiuta_un_testo_oltre_il_limite_e_con_force_lo_accetta(self):
        """Il limite e' un contratto: sopra, l'agente non poteva averlo letto davvero."""
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("manuale.pdf"))])
        enorme = self.materiale("estratto.md", "parola " * 70_000)   # 490k caratteri
        comando = ["materiali", "testo", slug, "--material", "manuale.pdf", "--file", str(enorme)]
        code, out = run(comando)
        self.assertEqual(code, 1)
        self.assertIn("in blocco", json.loads(out)["error"])
        code, out = run(comando + ["--force"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertTrue(payload["avvisi"])
        self.assertIn("fonti.md", " ".join(payload["avvisi"]))

    def test_il_testo_si_aggancia_solo_a_un_materiale_registrato(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        origine = self.materiale("estratto.md", self.PARAGRAFO_1)
        code, out = run(["materiali", "testo", slug, "--material", "mai-visto.pdf",
                         "--file", str(origine)])
        self.assertEqual(code, 1)
        self.assertIn("materiali add", json.loads(out)["error"])

    def test_un_estratto_cancellato_smette_di_essere_cercabile(self):
        """Un file derivato non mente: senza il testo, il materiale torna non cercabile."""
        slug = self.crea_completo("Probabilita")
        self.collegato(slug)
        (iv.MATERIALI_DIR / slug / "programma.estratto.md").unlink()
        code, out = run(["materiali", "search", slug, "probabilita condizionata", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0, out)
        self.assertEqual(payload["trovati"], 0)
        self.assertEqual(payload["materiali_senza_testo"], ["programma.pdf"])
        code, out = run(["materiali", "list", slug, "--json"])
        materiali = json.loads(out)["argomenti"][0]["materiali"]
        self.assertEqual(materiali[0]["testi"], [])

    def test_una_copia_completa_di_tre_pagine_passa(self):
        """Il rapporto caratteri/pagina e' aritmetica: una copia vera non lo teme."""
        slug = self.crea_completo("Probabilita")
        testo = self.corpus(3)
        out = self.collegato(slug, testo, pagine="1-3")
        payload = json.loads(out)
        self.assertEqual(payload["pagine"], 3)
        self.assertGreaterEqual(payload["caratteri_per_pagina"], 250)
        self.assertLessEqual(payload["caratteri_per_pagina"], 6000)
        self.assertEqual(payload["avvisi"], [])

    def test_una_copia_troppo_magra_per_le_pagine_dichiarate_viene_rifiutata(self):
        """500 caratteri dichiarati come 12 pagine sono un indice, non una trascrizione."""
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        origine = self.materiale("estratto.md", self.PARAGRAFO_1 + self.PARAGRAFO_2)
        comando = ["materiali", "testo", slug, "--material", "programma.pdf",
                   "--file", str(origine), "--pagine", "1-12"]
        code, out = run(comando)
        self.assertEqual(code, 1)
        self.assertIn("troncato o riassunto", json.loads(out)["error"])
        self.assertFalse((iv.MATERIALI_DIR / slug / "programma.estratto.md").exists())
        code, out = run(comando + ["--force"])
        self.assertEqual(code, 0, out)
        self.assertIn("incompleta", " ".join(json.loads(out)["avvisi"]))

    def test_pagine_non_numeriche_non_impediscono_il_collegamento(self):
        """Meglio nessun controllo che un controllo inventato: e il payload lo dice."""
        slug = self.crea_completo("Probabilita")
        out = self.collegato(slug, pagine="cap. 3")
        payload = json.loads(out)
        self.assertIsNone(payload["pagine"])
        self.assertIsNone(payload["caratteri_per_pagina"])
        self.assertIn("troncato", " ".join(payload["avvisi"]))

    def test_pagine_sottostimate_vengono_avvisate_non_bloccate(self):
        """Troppo testo per le pagine dichiarate: la copia c'e', l'etichetta no."""
        slug = self.crea_completo("Probabilita")
        out = self.collegato(slug, self.corpus(4), pagine="1")
        payload = json.loads(out)
        self.assertIn("sottostimate", " ".join(payload["avvisi"]))

    def test_mezzo_e_campione_restano_dichiarazioni_visibili(self):
        """Nessun codice distingue una trascrizione da una parafrasi: si dichiara."""
        slug = self.crea_completo("Probabilita")
        out = self.collegato(slug, extra=["--mezzo", "vista",
                                          "--campione", "3 citazioni confrontate"])
        payload = json.loads(out)
        self.assertEqual(payload["mezzo"], "vista")
        self.assertEqual(payload["campione"], "3 citazioni confrontate")
        code, out = run(["materiali", "search", slug, "probabilita condizionata", "--json"])
        primo = json.loads(out)["risultati"][0]
        self.assertEqual(primo["mezzo"], "vista")
        self.assertEqual(primo["campione"], "3 citazioni confrontate")

    def test_una_trascrizione_non_verificata_e_dichiarata_tale(self):
        slug = self.crea_completo("Probabilita")
        self.collegato(slug)
        code, out = run(["materiali", "list", slug])
        self.assertIn("NON verificata a campione", out)
        code, out = run(["materiali", "search", slug, "probabilita condizionata", "--json"])
        primo = json.loads(out)["risultati"][0]
        self.assertEqual(primo["mezzo"], "non dichiarato")
        self.assertEqual(primo["campione"], "")

    def test_un_estratto_non_utf8_viene_rifiutato(self):
        """Visto sul campo: `pdftotext` senza `-enc UTF-8` scrive Latin-1, e sembra a posto."""
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        latin1 = Path(self._tmp.name) / "estratto-latin1.md"
        # 'à' e 'è' sono validi in latin-1 e non in UTF-8: e' esattamente il caso reale.
        latin1.write_bytes(("Capitolo 1 - Probabilità\n\n" + "riga di prova. " * 60)
                           .encode("latin-1"))
        code, out = run(["materiali", "testo", slug, "--material", "programma.pdf",
                         "--file", str(latin1), "--pagine", "1"])
        self.assertEqual(code, 1)
        errore = json.loads(out)["error"]
        self.assertIn("non e' UTF-8", errore)
        self.assertIn("-enc UTF-8", errore)
        self.assertFalse((iv.MATERIALI_DIR / slug / "programma.estratto.md").exists())

    def test_mezzo_sconosciuto_viene_rifiutato(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        origine = self.materiale("estratto.md", self.PARAGRAFO_1)
        scarto = io.StringIO()
        with contextlib.redirect_stderr(scarto):   # argparse stampa l'uso su stderr
            with self.assertRaises(SystemExit):
                run(["materiali", "testo", slug, "--material", "programma.pdf",
                     "--file", str(origine), "--mezzo", "intuito"])
        with contextlib.redirect_stdout(scarto):
            with self.assertRaises(SystemExit):
                iv.collega_testo(slug, "programma.pdf", origine, "1", "intuito")

    def test_indice_e_lista_dicono_cosa_e_cercabile(self):
        slug = self.crea_completo("Probabilita")
        run(["materiali", "add", slug, "--file", str(self.materiale("programma.pdf"))])
        indice = (iv.MATERIALI_DIR / slug / "INDICE.md").read_text(encoding="utf-8")
        self.assertIn("non cercabile", indice)
        self.collegato(slug)
        indice = (iv.MATERIALI_DIR / slug / "INDICE.md").read_text(encoding="utf-8")
        self.assertIn("non verificata", indice)
        code, out = run(["materiali", "list", slug])
        self.assertEqual(code, 0, out)
        self.assertIn("cercabile", out)
        code, out = run(["materiali", "list", slug, "--json"])
        self.assertEqual(json.loads(out)["con_testo"], 1)


class TestStrumentiDiEstrazione(BaseIV):
    """La macchina decide quanto ci si puo' fidare: il motore rileva, non esegue mai."""

    def test_senza_strumenti_si_legge_a_vista_e_il_campione_e_obbligatorio(self):
        disponibili = iv.strumenti_disponibili({})
        self.assertEqual(set(disponibili), {v["chiave"] for v in iv.STRUMENTI_PDF})
        metodo = iv.metodo_estrazione(disponibili)
        self.assertFalse(metodo["copia_meccanica"])
        self.assertIsNone(metodo["metodo_consigliato"])
        self.assertEqual(metodo["mezzo_da_dichiarare"], "vista")
        self.assertEqual(metodo["controllo_a_campione"], "obbligatorio")

    def test_con_pdftotext_la_copia_e_meccanica(self):
        metodo = iv.metodo_estrazione(iv.strumenti_disponibili({"pdftotext": True}))
        self.assertTrue(metodo["copia_meccanica"])
        self.assertIn("pdftotext", metodo["metodo_consigliato"])
        self.assertEqual(metodo["mezzo_da_dichiarare"], "testo")
        self.assertEqual(metodo["controllo_a_campione"], "consigliato")

    def test_il_comando_consigliato_chiede_esplicitamente_utf8(self):
        """Senza `-enc UTF-8` pdftotext scrive Latin-1 e il motore non sa leggerlo."""
        metodo = iv.metodo_estrazione(iv.strumenti_disponibili({"pdftotext": True}))
        self.assertIn("-enc UTF-8", metodo["metodo_consigliato"])
        self.assertIn("-enc UTF-8", metodo["metodo_alternativo"])

    def test_il_flag_layout_non_e_sempre_giusto_e_il_motore_lo_dice(self):
        """Visto sul campo: con `-layout` un riquadro centrato finisce in mezzo a una frase.

        I due comandi hanno difetti opposti (struttura vs ordine di lettura) e nessuno
        vince sempre: la scelta si fa **guardando** i primi righi dell'estratto, e il
        motore non puo' farla al posto di chi legge.
        """
        metodo = iv.metodo_estrazione(iv.strumenti_disponibili({"pdftotext": True}))
        self.assertEqual(metodo["metodo_alternativo"], "pdftotext -enc UTF-8")
        self.assertIn("-layout", metodo["metodo_consigliato"])
        self.assertIn("in mezzo a una frase", metodo["quando_cambiare"])
        self.assertIn("convivere", metodo["quando_cambiare"])

    def test_senza_copia_meccanica_non_c_e_un_alternativa_da_proporre(self):
        """Senza estrattore, l'unica strada e' leggere: non c'e' un secondo comando da scegliere."""
        metodo = iv.metodo_estrazione(iv.strumenti_disponibili({"pdfinfo": True}))
        self.assertFalse(metodo["copia_meccanica"])
        self.assertIsNone(metodo["metodo_alternativo"])
        self.assertIsNone(metodo["quando_cambiare"])

    def test_un_modulo_python_basta_per_la_copia_meccanica(self):
        metodo = iv.metodo_estrazione(iv.strumenti_disponibili({"pypdf": True}))
        self.assertTrue(metodo["copia_meccanica"])
        self.assertIn("pypdf", metodo["metodo_consigliato"])

    def test_un_attrezzo_che_conta_solo_le_pagine_non_e_una_copia(self):
        """`pdfinfo` dice quante pagine, non cosa c'e' scritto: il testo resta da leggere."""
        metodo = iv.metodo_estrazione(iv.strumenti_disponibili({"pdfinfo": True}))
        self.assertFalse(metodo["copia_meccanica"])
        self.assertEqual(metodo["controllo_a_campione"], "obbligatorio")

    def test_il_rilevamento_reale_restituisce_booleani(self):
        for valore in iv.strumenti_disponibili().values():
            self.assertIsInstance(valore, bool)

    def test_un_rilevamento_impossibile_vale_assente_non_errore(self):
        self.assertFalse(iv.modulo_esiste("modulo-che-non-esiste-di-sicuro-xyz"))

    def test_la_cli_riporta_e_dichiara_di_non_eseguire(self):
        code, out = run(["strumenti", "--json"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual(set(payload["disponibili"]), {v["chiave"] for v in iv.STRUMENTI_PDF})
        self.assertIn("non li esegue", payload["nota"])
        self.assertIn(payload["mezzo_da_dichiarare"], iv.MATERIALI_MEZZI)
        # La sonda riporta **entrambi** i comandi quando c'e' un estrattore con alternativa:
        # dipende dalla macchina, quindi si verifica su un rilevamento costruito, non su questa.
        costruito = iv.metodo_estrazione(iv.strumenti_disponibili({"pdftotext": True}))
        self.assertEqual(costruito["metodo_alternativo"], "pdftotext -enc UTF-8")
        self.assertIn("pdftotext", payload["dettaglio"][0]["comando"])

    def test_lo_stato_dichiara_cosa_puo_fare_la_macchina(self):
        """Il primo comando della sessione deve dire se si copia o si legge."""
        code, out = run(["status"])
        self.assertEqual(code, 0, out)
        strumenti = json.loads(out)["strumenti"]
        self.assertIn("copia_meccanica", strumenti)
        self.assertIn(strumenti["mezzo"] or "", iv.MATERIALI_MEZZI)


class TestLintDiProsa(BaseIV):
    """Lo schema non vede la scrittura: il lint rende visibile la deriva di qualita'."""

    def lint(self, slug: str) -> list[str]:
        code, out = run(["validate", slug, "--json"])
        return [p for p in json.loads(out)["esito"][0]["problemi"] if "avviso" in p]

    def test_carattere_non_latino_viene_segnalato(self):
        slug = self.crea_completo("Probabilita")
        percorso = iv.topic_dir(slug) / "percorso.md"
        percorso.write_text(percorso.read_text(encoding="utf-8") + "\nVedi completarlа frase.", encoding="utf-8")
        avvisi = self.lint(slug)
        self.assertTrue(any("U+0430" in a for a in avvisi), avvisi)

    def test_riga_duplicata_viene_segnalata(self):
        slug = self.crea_completo("Probabilita")
        percorso = iv.topic_dir(slug) / "percorso.md"
        percorso.write_text(
            percorso.read_text(encoding="utf-8") + "\nIl testo rigenerato che ripete la coda della riga." * 2,
            encoding="utf-8",
        )
        self.assertTrue(any("duplicat" in a for a in self.lint(slug)))

    def test_markdown_sbilanciato_viene_segnalato(self):
        slug = self.crea_completo("Probabilita")
        glossario = iv.topic_dir(slug) / "glossario.md"
        glossario.write_text(glossario.read_text(encoding="utf-8") + "\nErrore con backtick spaiato `qui.\n", encoding="utf-8")
        self.assertTrue(any("markdown sbilanciato" in a for a in self.lint(slug)))

    def test_gli_avvisi_non_bloccano_il_riuso(self):
        slug = self.crea_completo("Probabilita")
        percorso = iv.topic_dir(slug) / "percorso.md"
        percorso.write_text(percorso.read_text(encoding="utf-8") + "\nVedi completarlа frase.", encoding="utf-8")
        code, out = run(["validate", slug, "--json"])
        payload = json.loads(out)["esito"][0]
        self.assertEqual(code, 0)
        self.assertTrue(payload["valido"])
        self.assertGreater(payload["avvisi"], 0)

    def test_una_sotto_skill_pulita_non_produce_avvisi(self):
        slug = self.crea_completo("Probabilita")
        self.assertEqual(self.lint(slug), [])


class TestStileMisurabile(BaseIV):
    """La promessa "spiegazione semplice" non resta un auspicio: si misura."""

    SEMPLICE = (
        "Il gatto dorme sul divano. Il cane corre nel parco. Il sole scalda la casa. "
        "La mamma prepara la cena. Il pane e' caldo."
    )
    # 20 parole per frase, tutte corte: lungo ma non difficile
    LUNGHETTO = (
        "casa sole pane muro tetto prato ramo foglia vento nube pioggia neve ghiaccio "
        "monte valle fiume lago ponte strada."
    )
    DENSO = (
        "La rappresentazione distribuita della conoscenza contestuale implica una "
        "riorganizzazione progressiva delle attivazioni dei nodi interconnessi, cosi' che "
        "l'elaborazione complessiva emerga dalla interazione non lineare fra i livelli "
        "successivi dell'architettura stessa, la quale, in funzione della distribuzione "
        "statistica degli esempi, modifica i propri parametri in modo graduale."
    )

    def test_leggibilita_distingue_semplice_da_denso(self):
        semplice = iv.style_metrics(self.SEMPLICE * 4)
        denso = iv.style_metrics(self.DENSO * 4)
        self.assertGreater(semplice["gulpease"], denso["gulpease"])
        self.assertGreater(semplice["gulpease"], 70)
        self.assertLess(denso["gulpease"], 45)

    def test_metriche_conta_frasi_e_parole(self):
        metrics = iv.style_metrics("Il gatto dorme. Il cane corre.")
        self.assertEqual(metrics["frasi"], 2)
        self.assertEqual(metrics["parole"], 6)
        self.assertEqual(metrics["frase_piu_lunga"], "Il gatto dorme.")

    def test_righe_di_elenco_contano_come_frasi(self):
        """Senza questo, le voci di elenco si fondono e le misure mentono."""
        metrics = iv.style_metrics("- uno due tre\n- quattro cinque sei\n- sette otto nove\n")
        self.assertEqual(metrics["frasi"], 3)

    def test_il_livello_alza_o_abbassa_l_asticella(self):
        metrics = iv.style_metrics((self.LUNGHETTO + " ") * 4)
        self.assertTrue(iv.style_problems(metrics, 1), "20 parole/frase sono troppe per il livello 1")
        self.assertEqual(iv.style_problems(metrics, 4), [], "per il livello 4 sono accettabili")

    def test_style_command_su_un_testo(self):
        code, out = run(["style", "--text", self.DENSO, "--level", "2", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["problemi"]["testo"])
        code, out = run(["style", "--text", self.SEMPLICE * 4, "--level", "2", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["problemi"]["testo"], [])

    def test_style_su_una_sotto_skill(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["style", slug, "--file", "percorso.md"])
        self.assertEqual(code, 0, out)
        self.assertIn("Gulpease", out)

    def test_validate_segnala_un_file_denso(self):
        slug = self.crea_completo("Probabilita")
        percorso = iv.topic_dir(slug) / "percorso.md"
        denso = "\n\n".join(self.DENSO for _ in range(15))
        percorso.write_text(percorso.read_text(encoding="utf-8") + "\n" + denso, encoding="utf-8")
        code, out = run(["validate", slug, "--json"])
        payload = json.loads(out)["esito"][0]
        self.assertTrue(any("leggibilita" in p for p in payload["problemi"]), payload["problemi"])
        self.assertTrue(payload["valido"])

    def test_validate_non_giudica_i_file_corti(self):
        slug = self.crea_completo("Probabilita")
        code, out = run(["validate", slug, "--json"])
        problemi = json.loads(out)["esito"][0]["problemi"]
        self.assertFalse([p for p in problemi if "leggibilita" in p])


class TestCLI(BaseIV):
    def test_nessun_sottocomando_ridefinisce_le_opzioni_globali(self):
        """Un sottocomando che ridefinisce `--data` la azzera: il comando ignora la data dir.

        Gli unit test non lo vedono, perche' chiamano le funzioni con la data dir gie' fissata:
        l'unico modo per accorgersene e' guardare il parser (o passare dalla CLI vera).
        """
        globali = {"--data", "--skill-dir"}
        conflitti = []

        def controlla(parser, percorso: str) -> None:
            for azione in parser._actions:
                scelte = getattr(azione, "choices", None)
                if not isinstance(scelte, dict):
                    continue
                for nome, sotto in scelte.items():
                    if not isinstance(sotto, argparse.ArgumentParser):
                        continue
                    opzioni = {o for a in sotto._actions for o in a.option_strings}
                    for opzione in sorted(globali & opzioni):
                        conflitti.append(f"{percorso}{nome} ridefinisce {opzione}")
                    controlla(sotto, f"{percorso}{nome} ")

        controlla(iv.build_parser(), "iv.py ")
        self.assertEqual(conflitti, [])

    def test_lezione_dalla_cli_esterna_rispetta_la_data_dir(self):
        """Il percorso reale (subprocess + --data) e' quello che ha scoperto il conflitto."""
        data = self._tmp.name
        subprocess.run(
            [sys.executable, str(IV_PATH), "--data", data, "create", "--title", "Prova"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        result = subprocess.run(
            [sys.executable, str(IV_PATH), "--data", data, "lezione", "prova", "--classe", "3B"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(json.loads(result.stdout)["ok"])
        self.assertTrue((Path(data) / "lezioni" / "prova").is_dir())

    def test_runner_esterno_produce_json(self):
        result = subprocess.run(
            [sys.executable, str(IV_PATH), "--data", self._tmp.name, "find", "algebra lineare", "--json"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "none")

    def test_comando_inesistente_fallisce(self):
        result = subprocess.run(
            [sys.executable, str(IV_PATH), "nonesiste"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)


class TestDocumentazioneAllineata(BaseIV):
    """La documentazione dichiara cose contabili: se deriva, lo dice un test.

    Nasce da due derive reali, trovate il 2026-09-22 e non da un bug del motore:
    `AGENTS.md` dichiarava **14** sottocomandi quando erano gia' 18, e i README hanno
    riportato 54, 158, 168 e 173 test in momenti diversi. Sono esattamente le cose che
    nessuno nota finche' non le cerca (vedi §6 di `AGENTS.md`), e l'unica difesa che non
    costa disciplina e' farle controllare a un test invece che alla buona volonta'.
    """

    def documento(self, nome: str) -> str:
        path = SKILL_DIR / nome
        if not path.exists():
            self.skipTest(f"{nome} non fa parte di questa copia")
        return path.read_text(encoding="utf-8")

    def sottocomandi_veri(self) -> list[str]:
        for azione in iv.build_parser()._actions:
            if getattr(azione, "dest", "") == "command":
                return sorted(azione.choices)
        self.fail("il parser non ha un elenco di sottocomandi")

    def test_i_sottocomandi_documentati_sono_quelli_veri(self):
        riga = next((r for r in self.documento("AGENTS.md").splitlines()
                     if "sottocomandi (" in r), None)
        self.assertIsNotNone(riga, "AGENTS.md non elenca piu' i sottocomandi: aggiorna la riga")
        # Solo l'elenco fra parentesi: sulla stessa riga ci sono anche `build_parser` e `--data`.
        elenco = riga.split("sottocomandi (", 1)[1].split(")", 1)[0]
        documentati = sorted(re.findall(r"`([a-z]+)`", elenco))
        veri = self.sottocomandi_veri()
        self.assertEqual(documentati, veri,
                         f"AGENTS.md elenca {documentati}, il parser ne ha {veri}: "
                         f"allinea la riga di `build_parser` in §3")
        quanti = re.search(r"\*\*(\d+)\*\* sottocomandi", riga)
        self.assertIsNotNone(quanti, "manca il conteggio esplicito dei sottocomandi")
        self.assertEqual(int(quanti.group(1)), len(veri))

    def test_il_numero_di_test_dichiarato_e_quello_vero(self):
        """I README hanno gia' riportato 54, 158 e 168 test: il numero va contato, non ricordato."""
        sorgente = (SKILL_DIR / "tests" / "test_iv.py").read_text(encoding="utf-8")
        quanti = len(re.findall(r"\n    def test_", sorgente))
        self.assertGreater(quanti, 0)
        for nome, formula in (("README.it.md", f"{quanti} test del motore"),
                              ("README.md", f"{quanti} engine tests")):
            self.assertIn(formula, self.documento(nome),
                          f"{nome} non dichiara «{formula}»: aggiornalo insieme alla suite")


if __name__ == "__main__":
    unittest.main()
