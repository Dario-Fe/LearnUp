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

    def test_cornice_vecchia_segnala_da_rigenerare(self):
        slug = self.crea_completo("Analisi matematica")
        reg = iv.load_registry()
        reg["topics"][0]["base_version"] = "0.9.0"
        iv.save_registry(reg)
        meta = json.loads((iv.topic_dir(slug) / "meta.json").read_text(encoding="utf-8"))
        meta["base_version"] = "0.9.0"
        (iv.topic_dir(slug) / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        code, out = run(["status"])
        payload = json.loads(out)
        self.assertEqual(payload["da_rigenerare"], [slug])

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
