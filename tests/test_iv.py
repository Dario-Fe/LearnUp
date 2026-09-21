"""Test del motore iv.py — schema delle sotto-skill, riuso, alias, progressi.

Esecuzione (dalla radice del repository):
    python -m unittest discover -s tests -t tests
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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


if __name__ == "__main__":
    unittest.main()
