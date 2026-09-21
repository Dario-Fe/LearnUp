#!/usr/bin/env python3
"""iv.py — motore del sistema Insegnante Virtuale (IV).

Gestisce il ciclo rigenerante: cerca un argomento nel registro, riusa la
sotto-skill esistente o ne crea una nuova, valida, registra e traccia i progressi.

Esempi (lanciati dalla cartella della skill):
    python scripts/iv.py find "equazioni di secondo grado"
    python scripts/iv.py create --title "Equazioni di secondo grado" --level 2
    python scripts/iv.py register equazioni-di-secondo-grado
    python scripts/iv.py validate --all
    python scripts/iv.py log --topic equazioni-di-secondo-grado --minutes 45 \
        --summary "Modulo 1" --concept "formula risolutiva" --grade 4
    python scripts/iv.py due
    python scripts/iv.py stats --write

Solo libreria standard. Nessuna dipendenza esterna.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_VERSION = "1.0.0"

# ---------------------------------------------------------------- percorsi

SKILL_DIR = Path(
    os.environ.get("IV_SKILL_DIR") or Path(__file__).resolve().parent.parent
)
DATA = Path(os.environ.get("IV_DATA") or SKILL_DIR / "data")
REGISTRY = DATA / "registry.json"
TOPICS_DIR = DATA / "topics"
PROGRESS_DIR = DATA / "progress"
MERGED_DIR = DATA / "_merged"
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates" / "topic"

REQUIRED_FILES = [
    "SKILL.md",
    "meta.json",
    "percorso.md",
    "glossario.md",
    "errori-tipici.md",
    "esercizi.md",
    "verifica.md",
    "fonti.md",
]

TOPIC_STATUSES = ("draft", "active", "merged", "stale")
MODES = ("autodidatta", "esame", "docenza")

# ---------------------------------------------------------------- testo

STOPWORDS = {
    "di", "a", "ad", "da", "in", "con", "su", "per", "tra", "fra", "il", "lo", "la",
    "i", "gli", "le", "un", "uno", "una", "del", "dello", "della", "dei", "degli",
    "delle", "al", "allo", "alla", "ai", "agli", "alle", "dal", "dallo", "dalla",
    "dai", "dagli", "dalle", "nel", "nello", "nella", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle", "e", "ed", "o", "od", "ma",
    "che", "chi", "cui", "non", "piu", "come", "cosa", "quale", "quali", "questo",
    "questa", "questi", "queste", "sono", "essere", "avere", "si", "mi", "ti",
    "ci", "vi", "ne", "anche", "molto", "poco", "tanto", "solo", "gia", "ancora",
    "sempre", "mai", "poi", "prima", "dopo", "senza", "contro", "verso", "durante",
    "corso", "corsi", "studio", "studiare", "imparare", "spiegami", "spiega",
    "spiegare", "capire", "nozioni", "basi", "base", "introduzione", "principi",
    "fondamenti", "elementi", "guida", "tutorial", "lezione", "lezioni", "argomento",
    "livello", "approfondimento", "ripasso", "ripassare", "esercizi", "voglio",
}

STEM_LEN = 5
MIN_STEM_WORD = 4

# soglie di similarità
T_EXACT = 0.93
T_VARIANT = 0.68
T_CANDIDATE = 0.42


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def norm(text: str) -> str:
    """Normalizza per confronti: minuscolo, senza accenti, spazi singoli."""
    text = strip_accents(str(text)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    """Parole di contenuto (stopword e monosillabi rimossi)."""
    return [w for w in norm(text).split() if w not in STOPWORDS and len(w) > 1]


def stems(words: list[str]) -> set[str]:
    """Steli grezzi: rendono equivalenti singolare/plurale senza un lemmatizzatore."""
    return {w[:STEM_LEN] for w in words if len(w) >= MIN_STEM_WORD}


def key_of(text: str) -> str:
    """Chiave canonica: parole di contenuto ordinate. Ignora l'ordine delle parole."""
    toks = sorted(set(tokens(text)))
    return "-".join(toks) if toks else norm(text).replace(" ", "-")


def slugify(text: str) -> str:
    return norm(text).replace(" ", "-") or "argomento"


def similarity(query: str, target: str) -> float:
    """Similarità 0..1 fra due etichette di argomento."""
    qa, qb = tokens(query), tokens(target)
    if not qa or not qb:
        return 0.0
    if key_of(query) == key_of(target):
        return 1.0
    sa, sb = stems(qa), stems(qb)
    inter = len(sa & sb)
    if not inter:
        return 0.0
    jaccard = inter / len(sa | sb)
    containment = inter / min(len(sa), len(sb))
    return round(min(1.0, max(jaccard, 0.9 * containment)), 3)


def today() -> str:
    return date.today().isoformat()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- io

def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        die(f"File JSON illeggibile: {path} ({exc})")


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def die(message: str, code: int = 1):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2))
    sys.exit(code)


def emit(payload, as_text: str | None = None, code: int = 0) -> None:
    if as_text is not None:
        print(as_text)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(code)


# ---------------------------------------------------------------- registro

def empty_registry() -> dict:
    return {"version": 1, "base_version": BASE_VERSION, "topics": [], "alias_index": {}}


def load_registry() -> dict:
    reg = read_json(REGISTRY, None)
    if not isinstance(reg, dict) or "topics" not in reg:
        reg = empty_registry()
    reg.setdefault("topics", [])
    reg.setdefault("alias_index", {})
    reg.setdefault("version", 1)
    return reg


def save_registry(reg: dict) -> None:
    reg["base_version"] = BASE_VERSION
    write_json(REGISTRY, reg)


def topic_dir(slug: str) -> Path:
    return TOPICS_DIR / slug


def find_entry(reg: dict, slug: str) -> dict | None:
    for entry in reg["topics"]:
        if entry.get("slug") == slug:
            return entry
    return None


def sync_from_disk(reg: dict) -> dict:
    """Aggiunge al registro i topic presenti su disco ma assenti dall'indice.

    L'indice e' un file derivato: i meta.json sono la fonte di verita'. Serve a
    due cose pratiche. Primo, un clone del repository (dove registry.json manca,
    perche' ignorato da git) funziona al primo comando. Secondo, se un agente
    modifica un meta.json a mano, l'indice si allinea da solo.
    La ricostruzione viene salvata su disco: senza questo salvataggio il file
    resterebbe vuoto finche' non si esegue un comando che scrive, e l'indice
    mentirebbe a ogni lettura successiva.
    """
    if not TOPICS_DIR.exists():
        return reg
    for child in sorted(TOPICS_DIR.iterdir()):
        if not child.is_dir():
            continue
        meta = read_json(child / "meta.json", None)
        if not isinstance(meta, dict) or not meta.get("slug"):
            continue
        if find_entry(reg, meta["slug"]):
            continue
        entry = {k: meta.get(k) for k in REGISTRY_ENTRY_FIELDS}
        entry["slug"] = meta["slug"]
        entry["title"] = meta.get("title", meta["slug"])
        entry["key"] = meta.get("key") or key_of(meta.get("title", meta["slug"]))
        entry["path"] = f"topics/{meta['slug']}/SKILL.md"
        reg["topics"].append(entry)
    rebuild_alias_index(reg)
    if read_json(REGISTRY, None) != reg:
        save_registry(reg)
    return reg


REGISTRY_ENTRY_FIELDS = (
    "slug", "title", "key", "status", "aliases", "level", "mode", "prereqs",
    "tags", "created", "updated", "base_version", "content_hash", "revision",
    "path",
)


def rebuild_alias_index(reg: dict) -> None:
    index: dict[str, str] = {}
    for entry in reg["topics"]:
        slug = entry.get("slug")
        if not slug:
            continue
        index[slug] = slug
        for alias in entry.get("aliases") or []:
            index[norm(alias)] = slug
            index[key_of(alias)] = slug
        if entry.get("key"):
            index[entry["key"]] = slug
    reg["alias_index"] = index


def score_entries(query: str, reg: dict) -> list[dict]:
    scored = []
    for entry in reg["topics"]:
        if entry.get("status") == "merged":
            continue
        best = similarity(query, entry.get("title", ""))
        best = max(best, similarity(query, entry.get("slug", "").replace("-", " ")))
        for alias in entry.get("aliases") or []:
            best = max(best, similarity(query, alias))
        scored.append({"entry": entry, "score": round(best, 3)})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def lookup(query: str) -> dict:
    """Ricerca ibrida: alias/chiave esatta, poi similarità testuale."""
    reg = sync_from_disk(load_registry())
    rebuild_alias_index(reg)
    q_key, q_norm, q_slug = key_of(query), norm(query), slugify(query)

    hit = None
    how = None
    for candidate_norm, kind in ((q_norm, "alias"), (q_key, "chiave")):
        slug = reg["alias_index"].get(candidate_norm)
        if slug:
            entry = find_entry(reg, slug)
            if entry:
                hit, how = entry, kind
                break
    if not hit and q_slug in reg["alias_index"]:
        entry = find_entry(reg, reg["alias_index"][q_slug])
        if entry:
            hit, how = entry, "slug"

    scored = score_entries(query, reg)
    if hit:
        best = next((s for s in scored if s["entry"] is hit), {"score": 1.0})
        status = "exact"
    else:
        best = scored[0] if scored else {"entry": None, "score": 0.0}
        if best["score"] >= T_EXACT:
            status, hit, how = "exact", best["entry"], "similarità"
        elif best["score"] >= T_VARIANT:
            status = "variant"
        elif best["score"] >= T_CANDIDATE:
            status = "candidates"
        else:
            status, best = "none", {"entry": None, "score": best["score"]}

    candidates = [
        {
            "slug": s["entry"]["slug"],
            "title": s["entry"].get("title", s["entry"]["slug"]),
            "score": s["score"],
            "status": s["entry"].get("status"),
            "level": s["entry"].get("level"),
        }
        for s in scored
        if s["score"] >= T_CANDIDATE
    ][:5]

    result = {
        "ok": True,
        "query": query,
        "slug_proposto": q_slug,
        "chiave": q_key,
        "status": status,
        "rilevato_come": how,
        "azione": {
            "exact": "riusa",
            "variant": "chiedi_conferma",
            "candidates": "chiedi_conferma_o_forse_nuovo",
            "none": "genera_nuova",
        }[status],
        "match": None,
        "candidates": candidates,
    }
    if hit:
        result["match"] = {
            "slug": hit["slug"],
            "title": hit.get("title", hit["slug"]),
            "score": best["score"],
            "status": hit.get("status"),
            "level": hit.get("level"),
            "mode": hit.get("mode"),
            "base_version": hit.get("base_version"),
            "percorso": f"topics/{hit['slug']}/SKILL.md",
        }
    if status == "exact" and result["match"] and has_placeholder_issues(hit["slug"]):
        result["status"] = "draft_incompleto"
        result["azione"] = "completa_poi_riusa"
    result["hint"] = HINTS.get(result["status"], "")
    return result


HINTS = {
    "exact": "Sotto-skill già esistente e completa: caricala e riprendi dal progresso salvato.",
    "variant": "Argomento molto simile a uno esistente: chiedi all'utente se è lo stesso (riusa/alias) o un argomento nuovo.",
    "candidates": "Esistono argomenti affini: proponi di riusare uno di quelli oppure crea un nuovo topic collegato come prerequisito.",
    "none": "Nessuna sotto-skill: generala seguendo references/schema-sottoskill.md.",
    "draft_incompleto": "Esiste una sotto-skill incompleta su questo argomento: completala, poi registrala.",
}


# ---------------------------------------------------------------- creazione

PLACEHOLDERS = ("{{TITLE}}", "{{SLUG}}", "{{KEY}}", "{{LEVEL}}", "{{MODE}}",
                "{{PREREQS}}", "{{DATE}}", "{{BASE_VERSION}}")


def render(text: str, values: dict) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def cmd_create(args) -> None:
    title = args.title.strip()
    slug = slugify(args.slug or title)
    if not TEMPLATE_DIR.exists():
        die(f"Template non trovato: {TEMPLATE_DIR}")
    reg = sync_from_disk(load_registry())
    if find_entry(reg, slug):
        die(
            f"Esiste già un argomento con slug '{slug}'. Usa `iv.py find` per riusarlo.",
        )
    existing = lookup(title)
    if existing["status"] == "exact" and existing["match"]:
        die(
            f"'{title}' corrisponde a '{existing['match']['slug']}' "
            f"(score {existing['match']['score']}). Riusa quello invece di crearne uno nuovo."
        )

    target = topic_dir(slug)
    if target.exists():
        die(f"Cartella già presente su disco: {target}")

    values = {
        "TITLE": title,
        "SLUG": slug,
        "KEY": key_of(title),
        "LEVEL": args.level,
        "MODE": args.mode,
        "PREREQS": ", ".join(args.prereq) if args.prereq else "nessuno",
        "DATE": today(),
        "BASE_VERSION": BASE_VERSION,
    }

    target.mkdir(parents=True)
    for src in sorted(TEMPLATE_DIR.iterdir()):
        if not src.is_file():
            continue
        (target / src.name).write_text(render(read_text(src), values), encoding="utf-8")

    meta = read_json(target / "meta.json", {})
    meta["slug"] = slug
    meta["title"] = title
    meta["key"] = values["KEY"]
    meta["level"] = args.level
    meta["mode"] = args.mode
    meta["prereqs"] = list(args.prereq)
    meta["tags"] = list(args.tag)
    meta["aliases"] = list(args.alias)
    meta["created"] = meta["updated"] = today()
    meta["base_version"] = BASE_VERSION
    write_json(target / "meta.json", meta)

    entry = {k: meta.get(k) for k in REGISTRY_ENTRY_FIELDS}
    entry["path"] = f"topics/{slug}/SKILL.md"
    reg["topics"].append(entry)
    rebuild_alias_index(reg)
    save_registry(reg)

    emit(
        {
            "ok": True,
            "slug": slug,
            "title": title,
            "status": "draft",
            "cartella": str(target),
            "file_da_compilare": REQUIRED_FILES,
            "prossimi_passi": [
                "Riempire i file sostituendo ogni commento ISTRUZIONI con contenuto reale.",
                f"python scripts/iv.py validate {slug}",
                f"python scripts/iv.py register {slug}",
            ],
        }
    )


# ---------------------------------------------------------------- validazione

REQUIRED_HEADINGS = {
    "SKILL.md": [
        "## Contratto didattico",
        "## Mappa del corso",
        "## Come condurre una sessione su questo argomento",
    ],
    "percorso.md": ["## Prerequisiti e diagnosi rapida"],
    "verifica.md": ["## Criteri di padronanza", "## Prova finale"],
    "fonti.md": ["## Da verificare"],
}


def count_table_rows(text: str, after_heading: str | None = None) -> int:
    section = text
    if after_heading:
        idx = text.find(after_heading)
        if idx == -1:
            return 0
        section = text[idx:]
    rows = 0
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows += 1
    return max(0, rows - 2 if rows else 0)  # meno intestazione e separatore


def has_placeholder_issues(slug: str) -> bool:
    issues = validate_topic(slug)["problemi"]
    return any(p["livello"] == "errore" for p in issues)


def validate_topic(slug: str) -> dict:
    folder = topic_dir(slug)
    problemi: list[dict] = []

    def err(message: str) -> None:
        problemi.append({"livello": "errore", "messaggio": message})

    def warn(message: str) -> None:
        problemi.append({"livello": "avviso", "messaggio": message})

    if not folder.is_dir():
        return {"slug": slug, "valido": False,
                "problemi": [{"livello": "errore", "messaggio": f"Cartella assente: {folder}"}]}

    texts: dict[str, str] = {}
    for name in REQUIRED_FILES:
        path = folder / name
        if not path.exists():
            err(f"File mancante: {name}")
            continue
        texts[name] = read_text(path)

    for name, text in texts.items():
        leftovers = [p for p in PLACEHOLDERS if p in text]
        if leftovers:
            err(f"{name}: placeholder non sostituiti ({', '.join(leftovers)})")
        if "ISTRUZIONI:" in text:
            err(f"{name}: restano blocchi 'ISTRUZIONI:' da compilare")

    for name, headings in REQUIRED_HEADINGS.items():
        text = texts.get(name, "")
        for heading in headings:
            if heading not in text:
                err(f"{name}: manca la sezione '{heading}'")

    meta = read_json(folder / "meta.json", None)
    if not isinstance(meta, dict):
        err("meta.json non è JSON valido")
        meta = {}
    for field in ("slug", "title", "key", "level", "mode", "status", "prereqs", "base_version"):
        if field not in meta:
            err(f"meta.json: campo obbligatorio mancante '{field}'")
    if meta.get("slug") and meta["slug"] != slug:
        err(f"meta.json: slug '{meta['slug']}' diverso dalla cartella '{slug}'")

    skill_md = texts.get("SKILL.md", "")
    if not skill_md.startswith("---"):
        err("SKILL.md: frontmatter YAML assente")
    else:
        front = skill_md.split("---", 2)[1] if skill_md.count("---") >= 2 else ""
        if f"name: iv-{slug}" not in front:
            err(f"SKILL.md: il frontmatter deve contenere 'name: iv-{slug}'")
        if "description:" not in front:
            err("SKILL.md: il frontmatter deve contenere 'description:'")

    percorso = texts.get("percorso.md", "")
    moduli = re.findall(r"^##\s+Modulo\s+\d+", percorso, flags=re.MULTILINE)
    if len(moduli) < 3:
        err(f"percorso.md: servono almeno 3 moduli, trovati {len(moduli)}")
    for block in re.split(r"^##\s+Modulo\s+\d+", percorso, flags=re.MULTILINE)[1:]:
        if not re.search(r"\*\*Obiettivo verificabile:\*\*\s*\S", block):
            err("percorso.md: un modulo non ha un obiettivo verificabile")
        if "### Esempio concreto" not in block:
            err("percorso.md: un modulo non ha '### Esempio concreto'")
        if "### Controesempio" not in block:
            err("percorso.md: un modulo non ha '### Controesempio'")

    errori = len(re.findall(r"^##\s+\d+\.", texts.get("errori-tipici.md", ""), flags=re.MULTILINE))
    if errori < 4:
        err(f"errori-tipici.md: servono almeno 4 misconcezioni, trovate {errori}")

    voci_glossario = count_table_rows(texts.get("glossario.md", ""))
    if voci_glossario < 6:
        err(f"glossario.md: servono almeno 6 voci, trovate {voci_glossario}")

    esercizi = re.findall(r"^###\s+Esercizio\s+\S+", texts.get("esercizi.md", ""), flags=re.MULTILINE)
    if len(esercizi) < 6:
        err(f"esercizi.md: servono almeno 6 esercizi, trovati {len(esercizi)}")
    testo_esercizi = texts.get("esercizi.md", "")
    if testo_esercizi.count("<details>") < len(esercizi):
        err("esercizi.md: ogni esercizio deve avere la soluzione in <details>")
    if testo_esercizi.count("Come valutarti") < len(esercizi):
        err("esercizi.md: ogni esercizio deve avere i criteri 'Come valutarti'")

    prova = texts.get("verifica.md", "")
    domande = re.findall(r"^\d+\.\s+\S", prova, flags=re.MULTILINE)
    if len(domande) < 6:
        err(f"verifica.md: la prova finale richiede almeno 6 voci, trovate {len(domande)}")

    if meta.get("mode") not in MODES:
        warn(f"meta.json: mode '{meta.get('mode')}' non fra {MODES}")

    hash_source = "".join(texts.get(name, "") for name in sorted(texts) if name != "meta.json")
    return {
        "slug": slug,
        "valido": not any(p["livello"] == "errore" for p in problemi),
        "errori": sum(1 for p in problemi if p["livello"] == "errore"),
        "avvisi": sum(1 for p in problemi if p["livello"] == "avviso"),
        "problemi": problemi,
        "hash": sha1_text(hash_source),
    }


def cmd_validate(args) -> None:
    reg = sync_from_disk(load_registry())
    if args.all:
        slugs = [e["slug"] for e in reg["topics"] if e.get("status") != "merged"]
    elif args.slug:
        slugs = [args.slug]
    else:
        die("Specifica uno slug oppure usa --all")
    reports = [validate_topic(slug) for slug in slugs]
    payload = {
        "ok": all(r["valido"] for r in reports),
        "validati": len(reports),
        "esito": [
            {"slug": r["slug"], "valido": r["valido"], "errori": r["errori"],
             "avvisi": r["avvisi"],
             "problemi": [f"[{p['livello']}] {p['messaggio']}" for p in r["problemi"]]}
            for r in reports
        ],
    }
    if args.json:
        emit(payload, code=0 if payload["ok"] else 1)

    lines = []
    for report in reports:
        state = "OK" if report["valido"] else "DA SISTEMARE"
        lines.append(f"## {report['slug']} — {state}")
        for problem in report["problemi"]:
            mark = "ERRORE" if problem["livello"] == "errore" else "avviso"
            lines.append(f"- [{mark}] {problem['messaggio']}")
        if not report["problemi"]:
            lines.append("- Nessun problema: la sotto-skill rispetta lo schema.")
        lines.append("")
    emit(payload, as_text="\n".join(lines), code=0 if payload["ok"] else 1)


def cmd_register(args) -> None:
    reg = sync_from_disk(load_registry())
    entry = find_entry(reg, args.slug)
    if not entry:
        die(f"Argomento '{args.slug}' non presente nel registro.")
    report = validate_topic(args.slug)
    if not report["valido"] and not args.force:
        emit(
            {
                "ok": False,
                "error": "La sotto-skill non supera la validazione: resta in stato 'draft'.",
                "problemi": [f"[{p['livello']}] {p['messaggio']}" for p in report["problemi"]],
                "suggerimento": "Completa i file, poi rilancia register. Usa --force solo per una bozza esplicita.",
            },
            code=1,
        )

    meta_path = topic_dir(args.slug) / "meta.json"
    meta = read_json(meta_path, {})
    meta["status"] = args.status
    meta["updated"] = today()
    meta["base_version"] = BASE_VERSION
    meta["revision"] = int(meta.get("revision", 1)) + (0 if meta.get("content_hash") == "" else 1)
    meta["content_hash"] = report["hash"]
    meta.setdefault("quality", {})
    meta["quality"] = {
        "validated": report["valido"],
        "errori": report["errori"],
        "avvisi": report["avvisi"],
        "self_check": args.self_check or meta["quality"].get("self_check", ""),
    }
    write_json(meta_path, meta)

    for field in REGISTRY_ENTRY_FIELDS:
        if field in meta:
            entry[field] = meta[field]
    entry["path"] = f"topics/{args.slug}/SKILL.md"
    rebuild_alias_index(reg)
    save_registry(reg)
    emit({"ok": True, "slug": args.slug, "status": entry["status"],
          "validato": report["valido"], "revisione": entry.get("revision"),
          "hash": report["hash"], "azione": "Sotto-skill registrata e pronta al riuso."})


# ---------------------------------------------------------------- alias e merge

def cmd_alias(args) -> None:
    reg = sync_from_disk(load_registry())
    entry = find_entry(reg, args.slug)
    if not entry:
        die(f"Argomento '{args.slug}' non presente nel registro.")
    if args.list:
        emit({"ok": True, "slug": args.slug, "aliases": entry.get("aliases") or []})
    value = (args.add or "").strip()
    if not value:
        die("Indica l'alias: iv.py alias <slug> --add \"nome alternativo\"")
    aliases = list(entry.get("aliases") or [])
    if value not in aliases:
        aliases.append(value)
    meta = read_json(topic_dir(args.slug) / "meta.json", {})
    meta["aliases"] = aliases
    meta["updated"] = today()
    write_json(topic_dir(args.slug) / "meta.json", meta)
    entry["aliases"] = aliases
    rebuild_alias_index(reg)
    save_registry(reg)
    verify = lookup(value)
    emit({"ok": True, "slug": args.slug, "aliases": aliases,
          "verifica": verify["status"], "rilevato_come": verify.get("rilevato_come")})


def cmd_merge(args) -> None:
    reg = sync_from_disk(load_registry())
    src, dst = find_entry(reg, args.from_slug), find_entry(reg, args.into)
    if not src:
        die(f"Argomento sorgente '{args.from_slug}' assente.")
    if not dst:
        die(f"Argomento destinazione '{args.into}' assente.")
    aliases = list(dst.get("aliases") or [])
    for alias in [src.get("title", args.from_slug)] + list(src.get("aliases") or []):
        if alias and alias not in aliases:
            aliases.append(alias)
    meta_dst = read_json(topic_dir(args.into) / "meta.json", {})
    meta_dst["aliases"] = aliases
    meta_dst["updated"] = today()
    write_json(topic_dir(args.into) / "meta.json", meta_dst)
    dst["aliases"] = aliases

    src_progress = progress_path(args.from_slug, args.learner)
    if src_progress.exists():
        dst_progress = progress_for(args.into, args.learner)
        dst_progress.setdefault("log", [])
        moved = read_json(src_progress, {})
        dst_progress["log"].extend(moved.get("log", []))
        dst_progress["total_minutes"] = dst_progress.get("total_minutes", 0) + moved.get("total_minutes", 0)
        for key, card in (moved.get("concepts") or {}).items():
            dst_progress.setdefault("concepts", {})
            current = dst_progress["concepts"].get(key)
            if not current or card.get("reps", 0) > current.get("reps", 0):
                dst_progress["concepts"][key] = card
        dst_progress.setdefault("weak_spots", [])
        dst_progress["weak_spots"] = sorted(set(dst_progress["weak_spots"]) | set(moved.get("weak_spots", [])))
        dst_progress["last_session"] = max(
            [d.get("date", "") for d in dst_progress["log"]] or [""]
        )
        write_progress(args.into, dst_progress, args.learner)
        src_progress.unlink()

    folder = topic_dir(args.from_slug)
    if folder.exists():
        MERGED_DIR.mkdir(parents=True, exist_ok=True)
        destination = MERGED_DIR / args.from_slug
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(folder), str(destination))
    src["status"] = "merged"
    src["merged_into"] = args.into
    src["updated"] = today()
    reg["topics"] = [t for t in reg["topics"] if t.get("slug") != args.from_slug]
    rebuild_alias_index(reg)
    save_registry(reg)
    emit({"ok": True, "unito": args.from_slug, "in": args.into,
          "aliases_ora": aliases, "archivio": str(MERGED_DIR / args.from_slug)})


def cmd_reindex(args) -> None:
    reg = empty_registry()
    reg = sync_from_disk(reg)
    rebuild_alias_index(reg)
    save_registry(reg)
    emit({"ok": True, "argomenti": len(reg["topics"]),
          "slugs": [e["slug"] for e in reg["topics"]]})


# ---------------------------------------------------------------- progressi

def learner_dir(learner: str) -> Path:
    return PROGRESS_DIR / learner


def progress_path(slug: str, learner: str) -> Path:
    return learner_dir(learner) / f"{slug}.json"


def blank_progress(slug: str, learner: str) -> dict:
    return {
        "slug": slug,
        "learner": learner,
        "level": None,
        "created": today(),
        "last_session": "",
        "total_minutes": 0,
        "sessions": 0,
        "modules_seen": [],
        "concepts": {},
        "weak_spots": [],
        "log": [],
    }


def progress_for(slug: str, learner: str) -> dict:
    data = read_json(progress_path(slug, learner), None)
    if not isinstance(data, dict):
        return blank_progress(slug, learner)
    base = blank_progress(slug, learner)
    base.update(data)
    return base


def write_progress(slug: str, data: dict, learner: str) -> None:
    write_json(progress_path(slug, learner), data)


def sm2(card: dict, grade: int) -> dict:
    card.setdefault("reps", 0)
    card.setdefault("ease", 2.5)
    card.setdefault("interval", 0)
    card.setdefault("lapses", 0)
    if grade < 3:
        card["lapses"] += 1
        card["reps"] = 0
        card["interval"] = 1
    else:
        if card["reps"] == 0:
            card["interval"] = 1
        elif card["reps"] == 1:
            card["interval"] = 6
        else:
            card["interval"] = max(1, round(card["interval"] * card["ease"]))
        card["reps"] += 1
    card["ease"] = max(
        1.3, round(card["ease"] + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)), 2)
    )
    card["due"] = (date.today() + timedelta(days=card["interval"])).isoformat()
    card["last_grade"] = grade
    card["last_review"] = today()
    return card


def cmd_log(args) -> None:
    reg = sync_from_disk(load_registry())
    if not find_entry(reg, args.topic):
        die(f"Argomento '{args.topic}' non nel registro: crealo prima con `iv.py create`.")
    data = progress_for(args.topic, args.learner)
    data["sessions"] = int(data.get("sessions", 0)) + 1
    data["total_minutes"] = int(data.get("total_minutes", 0)) + int(args.minutes or 0)
    data["last_session"] = today()
    if args.level:
        data["level"] = args.level
    elif data.get("level") is None:
        # Un agente puo' dimenticare --level alla prima sessione: eredita il
        # livello fissato alla creazione dell'argomento, cosi' i progressi
        # restano leggibili senza dover reinterpretare il meta.json.
        data["level"] = (find_entry(reg, args.topic) or {}).get("level")
    if args.module and args.module not in data["modules_seen"]:
        data["modules_seen"].append(args.module)
    data["log"].append(
        {
            "date": today(),
            "ora": now().split(" ")[1],
            "modalita": args.mode,
            "minuti": int(args.minutes or 0),
            "modulo": args.module or "",
            "sintesi": args.summary or "",
            "domande": args.questions or "",
            "prossimo_passo": args.next or "",
        }
    )

    concepts = args.concept or []
    grades = args.grade or []
    if len(concepts) != len(grades):
        die("Ogni --concept richiede un --grade corrispondente (0-5).")
    scheduled = []
    for name, grade in zip(concepts, grades):
        key = key_of(name) or slugify(name)
        card = data["concepts"].get(key) or {"name": name}
        card["name"] = name
        card = sm2(card, int(grade))
        data["concepts"][key] = card
        scheduled.append({"concetto": name, "voto": int(grade),
                          "prossimo_ripasso": card["due"], "intervallo_giorni": card["interval"],
                          "ease": card["ease"]})
        if int(grade) < 3:
            data["weak_spots"] = sorted(set(data.get("weak_spots", [])) | {name})

    write_progress(args.topic, data, args.learner)
    prossimi = [c["name"] for c in data["concepts"].values() if c.get("due", "") <= today()]
    if args.all_strong and prossimi:
        data["weak_spots"] = [w for w in data["weak_spots"] if w not in prossimi]
        write_progress(args.topic, data, args.learner)
    emit(
        {
            "ok": True,
            "topic": args.topic,
            "learner": args.learner,
            "sessione": data["sessions"],
            "minuti_totali": data["total_minutes"],
            "programmati": scheduled,
            "da_ripassare_oggi": prossimi,
            "file": str(progress_path(args.topic, args.learner)),
        }
    )


def all_progress(learner: str) -> list[dict]:
    folder = learner_dir(learner)
    if not folder.exists():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        data = read_json(path, None)
        if isinstance(data, dict):
            out.append(data)
    return out


def due_items(learner: str, within: int) -> dict:
    limit = (date.today() + timedelta(days=within)).isoformat()
    argomenti, concetti = [], []
    for data in all_progress(learner):
        slug = data.get("slug", "?")
        for card in (data.get("concepts") or {}).values():
            if card.get("due") and card["due"] <= limit:
                concetti.append(
                    {"topic": slug, "concetto": card.get("name", "?"), "scadenza": card["due"],
                     "intervallo_giorni": card.get("interval"), "ease": card.get("ease"),
                     "lacune": card.get("lapses", 0)}
                )
        last = data.get("last_session") or ""
        try:
            giorni = (date.today() - date.fromisoformat(last)).days if last else 0
        except ValueError:
            giorni = 0
        if last and giorni >= 21:
            argomenti.append({"topic": slug, "ultima_sessione": last, "giorni_fa": giorni})
    concetti.sort(key=lambda c: c["scadenza"])
    argomenti.sort(key=lambda a: a["giorni_fa"], reverse=True)
    return {"ok": True, "learner": learner, "entro_il": limit,
            "concetti_da_ripassare": concetti, "argomenti_stagnanti": argomenti}


def cmd_due(args) -> None:
    payload = due_items(args.learner, args.within)
    if args.json or not payload["concetti_da_ripassare"] and not payload["argomenti_stagnanti"]:
        emit(payload)
    lines = [f"# Ripassi entro il {payload['entro_il']}", ""]
    if payload["concetti_da_ripassare"]:
        lines += ["## Concetti in scadenza", ""]
        lines += [
            f"- `{c['concetto']}` ({c['topic']}) — scaduto il {c['scadenza']}, intervallo {c['intervallo_giorni']}g, lacune {c['lacune']}"
            for c in payload["concetti_da_ripassare"]
        ]
        lines.append("")
    if payload["argomenti_stagnanti"]:
        lines += ["## Argomenti trascurati (oltre 21 giorni)", ""]
        lines += [f"- {a['topic']} — {a['giorni_fa']} giorni fa" for a in payload["argomenti_stagnanti"]]
        lines.append("")
    emit(payload, as_text="\n".join(lines))


def cmd_stats(args) -> None:
    reg = sync_from_disk(load_registry())
    data_by_slug = {d.get("slug"): d for d in all_progress(args.learner)}
    rows, total_minutes, total_sessions, cards = [], 0, 0, 0
    weak_counter: dict[str, int] = {}
    stale = []

    for entry in sorted(reg["topics"], key=lambda e: e.get("title", "")):
        if entry.get("status") == "merged":
            continue
        data = data_by_slug.get(entry["slug"], {})
        minutes = int(data.get("total_minutes", 0))
        sessions = int(data.get("sessions", 0))
        concepts = data.get("concepts") or {}
        grades = [c.get("last_grade") for c in concepts.values() if c.get("last_grade") is not None]
        avg = round(sum(grades) / len(grades), 2) if grades else None
        total_minutes += minutes
        total_sessions += sessions
        cards += len(concepts)
        for weak in data.get("weak_spots", []) or []:
            weak_counter[weak] = weak_counter.get(weak, 0) + 1
        last = data.get("last_session") or "mai"
        rows.append(
            {
                "slug": entry["slug"], "title": entry.get("title"),
                "status": entry.get("status"), "level": entry.get("level"),
                "sessions": sessions, "minutes": minutes, "concepts": len(concepts),
                "avg_grade": avg, "last_session": last,
            }
        )
        try:
            raffreddato = last != "mai" and (date.today() - date.fromisoformat(last)).days >= 21
        except ValueError:
            raffreddato = False
        if raffreddato:
            stale.append(f"{entry['slug']} ({last})")

    due = due_items(args.learner, args.within)
    top_weak = sorted(weak_counter.items(), key=lambda kv: kv[1], reverse=True)[:5]

    lines = [
        f"# Diario di apprendimento — {args.learner}",
        "",
        f"_Aggiornato: {now()}_",
        "",
        "## Numeri",
        "",
        "| Metrica | Valore |",
        "|---|---|",
        f"| Argomenti nel registro | {len(rows)} |",
        f"| Sessioni registrate | {total_sessions} |",
        f"| Minuti studiati | {total_minutes} |",
        f"| Concetti tracciati | {cards} |",
        f"| Concetti da ripassare (entro {args.within}g) | {len(due['concetti_da_ripassare'])} |",
        "",
        "## Argomenti",
        "",
        "| Argomento | Stato | Livello | Sessioni | Minuti | Concetti | Voto medio | Ultima sessione |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['title']} (`{r['slug']}`) | {r['status']} | {r['level']} | {r['sessions']} | "
            f"{r['minutes']} | {r['concepts']} | {r['avg_grade'] if r['avg_grade'] is not None else '—'} | {r['last_session']} |"
        )
    lines += ["", "## Dove sbatte la testa (lacune ricorrenti)", ""]
    lines += [f"- {name} — segnalata {count} volta/e" for name, count in top_weak] or ["- Nessuna lacuna registrata."]
    lines += ["", "## Da rivedere adesso", ""]
    lines += [f"- `{c['concetto']}` ({c['topic']}) — scaduto il {c['scadenza']}" for c in due["concetti_da_ripassare"][:10]] or ["- Niente in scadenza."]
    lines += ["", "## Argomenti che stanno raffreddando", ""]
    lines += [f"- {s}" for s in stale] or ["- Nessuno: tutti gli argomenti sono stati ripresi di recente."]
    lines += ["", "## Suggerimenti", ""]
    if due["concetti_da_ripassare"]:
        lines.append("- Apri la sessione con 3 ripassi rapidi prima di andare avanti con contenuti nuovi.")
    if stale:
        lines.append("- Dedica una sessione breve a uno degli argomenti raffreddati: costa poco e salva molto.")
    if top_weak:
        lines.append(f"- Le lacune ricorrenti ({', '.join(n for n, _ in top_weak[:3])}) meritano una sotto-skill di prerequisito.")
    if not lines[-1].startswith("-"):
        lines.append("- Nessun intervento richiesto: continua il percorso previsto.")
    report = "\n".join(lines) + "\n"

    destination = None
    if args.write:
        destination = learner_dir(args.learner) / "DIARIO.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report, encoding="utf-8")

    if args.json:
        emit({"ok": True, "learner": args.learner, "argomenti": rows,
              "minuti_totali": total_minutes, "sessioni": total_sessions,
              "lacune_ricorrenti": top_weak, "riassunto": report,
              "scritto_in": str(destination) if destination else None})
    emit({"ok": True}, as_text=report + (f"\n_Diario salvato in:_ `{destination}`\n" if destination else ""))


# ---------------------------------------------------------------- lettura

def cmd_find(args) -> None:
    result = lookup(args.query)
    if args.json:
        emit(result)
    lines = [f"Ricerca: **{args.query}**", f"- Stato: `{result['status']}`", f"- Azione: `{result['azione']}`"]
    if result["match"]:
        m = result["match"]
        lines.append(f"- Corrispondenza: **{m['title']}** (`{m['slug']}`, score {m['score']}, stato {m['status']})")
        lines.append(f"- Percorso: `{m['percorso']}`")
    if result["candidates"]:
        lines.append("- Candidati affini:")
        lines += [f"  - {c['title']} (`{c['slug']}`, {c['score']})" for c in result["candidates"]]
    lines.append(f"- {result['hint']}")
    emit(result, as_text="\n".join(lines))


def cmd_list(args) -> None:
    reg = sync_from_disk(load_registry())
    rows = []
    for entry in sorted(reg["topics"], key=lambda e: e.get("title", "")):
        progress = progress_for(entry["slug"], args.learner)
        rows.append(
            {
                "slug": entry["slug"],
                "title": entry.get("title"),
                "stato": entry.get("status"),
                "livello": entry.get("level"),
                "modalita": entry.get("mode"),
                "base_version": entry.get("base_version"),
                "sessioni": progress.get("sessions", 0),
                "ultima": progress.get("last_session") or "mai",
                "da_rigenerare": entry.get("base_version") != BASE_VERSION,
            }
        )
    if args.json:
        emit({"ok": True, "base_version": BASE_VERSION, "argomenti": rows})
    if not rows:
        emit({"ok": True}, as_text="Nessun argomento nel registro: al primo avvio se ne crea uno.")
    lines = ["| Argomento | Slug | Stato | Livello | Sessioni | Ultima | Cornice |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        flag = "da rigenerare" if r["da_rigenerare"] else r["base_version"]
        lines.append(
            f"| {r['title']} | `{r['slug']}` | {r['stato']} | {r['livello']} | {r['sessioni']} | {r['ultima']} | {flag} |"
        )
    emit({"ok": True}, as_text="\n".join(lines))


def cmd_show(args) -> None:
    reg = sync_from_disk(load_registry())
    entry = find_entry(reg, args.slug)
    if not entry:
        result = lookup(args.slug)
        if result.get("match"):
            entry = find_entry(reg, result["match"]["slug"])
            args.slug = entry["slug"]
    if not entry:
        die(f"Argomento '{args.slug}' non trovato.")
    folder = topic_dir(args.slug)
    progress = progress_for(args.slug, args.learner)
    payload = {
        "ok": True,
        "topic": entry,
        "cartella": str(folder),
        "file": [str(folder / name) for name in REQUIRED_FILES if (folder / name).exists()],
        "progressi": {
            "sessioni": progress.get("sessions", 0),
            "minuti_totali": progress.get("total_minutes", 0),
            "livello": progress.get("level"),
            "ultima_sessione": progress.get("last_session") or "mai",
            "moduli_visti": progress.get("modules_seen", []),
            "lacune": progress.get("weak_spots", []),
            "concetti": [
                {"concetto": c.get("name"), "voto": c.get("last_grade"), "scadenza": c.get("due")}
                for c in (progress.get("concepts") or {}).values()
            ],
            "ultime_sessioni": progress.get("log", [])[-3:],
        },
    }
    emit(payload)


def cmd_status(args) -> None:
    reg = sync_from_disk(load_registry())
    topics = [e for e in reg["topics"] if e.get("status") != "merged"]
    stale = [e["slug"] for e in topics if e.get("base_version") != BASE_VERSION]
    drafts = [e["slug"] for e in topics if e.get("status") == "draft"]
    due = due_items(args.learner, 0)
    payload = {
        "ok": True,
        "base_version": BASE_VERSION,
        "argomenti": len(topics),
        "attivi": len([e for e in topics if e.get("status") == "active"]),
        "bozze_da_completare": drafts,
        "da_rigenerare": stale,
        "ripassi_oggi": len(due["concetti_da_ripassare"]),
        "prossimo_passo": (
            "Completa le bozze: " + ", ".join(drafts) if drafts
            else "Rigenera gli argomenti con cornice vecchia: " + ", ".join(stale) if stale
            else "Nessun debito tecnico: puoi dedicarti allo studio."
        ),
    }
    emit(payload)


# ---------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iv.py",
        description="Motore del sistema Insegnante Virtuale: registro, sotto-skill, progressi.",
    )
    parser.add_argument("--data", help="Cartella dati alternativa (default: <skill>/data)")
    parser.add_argument("--skill-dir", help="Cartella della skill (default: cartella di questo script)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("find", help="Cerca un argomento nel registro (azione: riusa o genera)")
    p.add_argument("query")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("create", help="Crea lo scheletro di una nuova sotto-skill")
    p.add_argument("--title", required=True)
    p.add_argument("--slug")
    p.add_argument("--level", type=int, default=2, choices=[1, 2, 3, 4])
    p.add_argument("--mode", default="autodidatta", choices=list(MODES))
    p.add_argument("--prereq", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--alias", action="append", default=[])
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("validate", help="Verifica che una sotto-skill rispetti lo schema")
    p.add_argument("slug", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("register", help="Attiva una sotto-skill dopo la generazione")
    p.add_argument("slug")
    p.add_argument("--status", default="active", choices=list(TOPIC_STATUSES))
    p.add_argument("--self-check", dest="self_check", default="")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("alias", help="Aggiungi un nome alternativo a un argomento")
    p.add_argument("slug")
    p.add_argument("--add")
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_alias)

    p = sub.add_parser("merge", help="Unisci due argomenti quasi-duplicati")
    p.add_argument("from_slug")
    p.add_argument("into")
    p.add_argument("--learner", default="default")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("reindex", help="Ricostruisce il registro a partire dai file su disco")
    p.set_defaults(func=cmd_reindex)

    p = sub.add_parser("log", help="Registra una sessione di studio e programma i ripassi")
    p.add_argument("--topic", required=True)
    p.add_argument("--minutes", type=int, default=0)
    p.add_argument("--summary", default="")
    p.add_argument("--module", default="")
    p.add_argument("--mode", default=None, choices=list(MODES))
    p.add_argument("--questions", default="")
    p.add_argument("--next", dest="next", default="")
    p.add_argument("--level", type=int, choices=[1, 2, 3, 4])
    p.add_argument("--concept", action="append", default=[])
    p.add_argument("--grade", type=int, action="append", default=[])
    p.add_argument("--all-strong", dest="all_strong", action="store_true")
    p.add_argument("--learner", default="default")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("due", help="Cosa ripassare adesso")
    p.add_argument("--within", type=int, default=0)
    p.add_argument("--learner", default="default")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_due)

    p = sub.add_parser("stats", help="Diario di apprendimento in Markdown")
    p.add_argument("--learner", default="default")
    p.add_argument("--within", type=int, default=7)
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("list", help="Elenca gli argomenti salvati")
    p.add_argument("--learner", default="default")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Dettagli e progressi di un argomento")
    p.add_argument("slug")
    p.add_argument("--learner", default="default")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("status", help="Stato del sistema")
    p.add_argument("--learner", default="default")
    p.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> None:
    _utf8_stdout()
    args = build_parser().parse_args(argv)
    if args.skill_dir:
        globals()["SKILL_DIR"] = Path(args.skill_dir)
    if args.data:
        set_data_dir(Path(args.data))
    else:
        if not REGISTRY.exists():
            save_registry(empty_registry())
        TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    args.func(args)


def set_data_dir(path: Path) -> None:
    global DATA, REGISTRY, TOPICS_DIR, PROGRESS_DIR, MERGED_DIR
    DATA = Path(path)
    REGISTRY = DATA / "registry.json"
    TOPICS_DIR = DATA / "topics"
    PROGRESS_DIR = DATA / "progress"
    MERGED_DIR = DATA / "_merged"
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY.exists():
        save_registry(empty_registry())
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
