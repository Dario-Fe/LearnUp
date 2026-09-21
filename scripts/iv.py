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


def split_prereqs(values: list[str]) -> list[str]:
    """Normalizza i prerequisiti: una voce per prerequisito.

    Gli agenti scrivono a volte `--prereq "a; b"`: senza questo split restano
    un'unica stringa e la mappa del corso li mostra fusi in una voce sola.
    """
    out: list[str] = []
    for value in values or []:
        for piece in str(value).split(";"):
            piece = piece.strip(" .")
            if piece and piece not in out:
                out.append(piece)
    return out


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


def version_major(version) -> str | None:
    """Parte major di una versione ('1.2.3' -> '1', 'v1.0' -> '1'). None se illeggibile."""
    match = re.match(r"\s*v?(\d+)", str(version or ""))
    return match.group(1) if match else None


def frame_state(entry: dict) -> dict:
    """Confronta la cornice di una sotto-skill con quella corrente.

    Semantica dichiarata nelle reference: **major** = regole che invalidano i
    contenuti generati (vanno rigenerati); **minor** = aggiunte compatibili
    (aggiornamento opzionale, la sotto-skill resta usabile cosi' com'e').
    Una versione assente o illeggibile conta come da rigenerare: provenienza
    ignota, meglio ricontrollare che fidarsi.
    """
    stored = entry.get("base_version")
    major_now, major_then = version_major(BASE_VERSION), version_major(stored)
    return {
        "versione": stored,
        "da_rigenerare": major_then != major_now,
        "aggiornabile": major_then == major_now and str(stored) != BASE_VERSION,
    }


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
    meta["prereqs"] = split_prereqs(args.prereq)
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


# Obiettivi di leggibilita' per livello dichiarato (il "dosatore" della cornice).
# Gulpease: >=80 molto facile, 60-79 facile, 40-59 difficile, <40 molto difficile.
# "frasi_lunghe" = percentuale massima di frasi oltre 30 parole.
STYLE_TARGETS = {
    1: {"gulpease": 60.0, "parole_frase": 16.0, "frasi_lunghe": 10},
    2: {"gulpease": 60.0, "parole_frase": 16.0, "frasi_lunghe": 10},
    3: {"gulpease": 50.0, "parole_frase": 20.0, "frasi_lunghe": 20},
    4: {"gulpease": 40.0, "parole_frase": 24.0, "frasi_lunghe": 30},
}

LONG_SENTENCE = 30
MIN_UNITS_FOR_STYLE = 12

_WORD = re.compile(r"[A-Za-zÀ-ÿ']+")


def style_units(text: str) -> list[str]:
    """Frasi misurabili: via codice, titoli e righe di separazione; una cella per riga."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " parola ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s*#{1,6}.*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|?[\s:|-]+\|?\s*$", " ", text, flags=re.MULTILINE)
    text = text.replace("|", ". ")
    text = re.sub(r"\*\*|\*|_", "", text)
    units = []
    for line in text.splitlines():
        # in Markdown ogni riga e' un'unita' di senso: senza questo, le voci di
        # elenco si fondono con la riga successiva e le misure mentono.
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line.strip())
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) <= 2:
            continue
        for part in re.split(r"(?<=[.!?…])\s+", line):
            part = part.strip()
            if len(part) > 2:
                units.append(part)
    return units


def style_metrics(text: str) -> dict:
    """Leggibilita' misurabile: indice Gulpease, parole per frase, frasi troppo lunghe.

    Misura la *scrittura*, non la verita' ne' la profondita': serve a rendere
    verificabile la promessa "spiegazione semplice", che altrimenti resta un
    auspicio e dipende interamente dal modello che genera.
    """
    units = style_units(text)
    lengths = [len(_WORD.findall(unit)) for unit in units]
    words = sum(lengths)
    if not units or not words:
        return {"frasi": 0, "parole": 0, "gulpease": None, "parole_frase": None,
                "frasi_lunghe_pct": 0, "virgole_frase": 0,
                "frase_piu_lunga": "", "parole_frase_piu_lunga": 0}
    letters = sum(len("".join(_WORD.findall(unit))) for unit in units)
    longest = max(units, key=lambda unit: len(_WORD.findall(unit)))
    long_count = sum(1 for n in lengths if n > LONG_SENTENCE)
    return {
        "frasi": len(units),
        "parole": words,
        "gulpease": round(89 + (300 * len(units) - 10 * letters) / words, 1),
        "parole_frase": round(words / len(units), 1),
        "frasi_lunghe_pct": round(100 * long_count / len(units)),
        "virgole_frase": round(sum(unit.count(",") for unit in units) / len(units), 2),
        "frase_piu_lunga": " ".join(longest.split())[:120],
        "parole_frase_piu_lunga": len(_WORD.findall(longest)),
    }


def style_problems(metrics: dict, level: int) -> list[str]:
    """Cosa non rispetta l'obiettivo di leggibilita' del livello dichiarato."""
    target = STYLE_TARGETS.get(int(level or 2), STYLE_TARGETS[2])
    if not metrics.get("frasi") or metrics.get("gulpease") is None:
        return []
    out = []
    if metrics["gulpease"] < target["gulpease"]:
        out.append(
            f"leggibilita' {metrics['gulpease']} < {target['gulpease']} (Gulpease) per il livello {level}: "
            f"{metrics['parole_frase']} parole per frase di media"
        )
    if metrics["parole_frase"] > target["parole_frase"] and metrics["gulpease"] >= target["gulpease"]:
        out.append(
            f"frasi lunghe ({metrics['parole_frase']} parole/frase, obiettivo "
            f"<= {target['parole_frase']}): spezza le subordinate in frasi autonome"
        )
    if metrics["frasi_lunghe_pct"] > target["frasi_lunghe"]:
        out.append(
            f"{metrics['frasi_lunghe_pct']}% di frasi oltre {LONG_SENTENCE} parole "
            f"(obiettivo <= {target['frasi_lunghe']}%)"
        )
    if out:
        out.append(f"frase piu' lunga ({metrics['parole_frase_piu_lunga']} parole): «{metrics['frase_piu_lunga']}»")
    return out


def cmd_style(args) -> None:
    """Misura la leggibilita' di una sotto-skill o di un testo (bozza di spiegazione)."""
    if args.text:
        label, level = "testo", args.level or 2
        metrics = style_metrics(args.text)
        files = [(label, metrics)]
    else:
        if not args.slug:
            die("Indica uno slug oppure usa --text \"<spiegazione>\"")
        reg = sync_from_disk(load_registry())
        entry = find_entry(reg, args.slug)
        if not entry:
            die(f"Argomento '{args.slug}' non nel registro.")
        level = args.level or entry.get("level") or 2
        names = [args.file] if args.file else [
            n for n in REQUIRED_FILES if n not in ("SKILL.md", "meta.json")
        ]
        files = []
        for name in names:
            path = topic_dir(args.slug) / name
            if not path.exists():
                die(f"File assente: {name}")
            files.append((name, style_metrics(read_text(path))))

    payload = {
        "ok": True,
        "criterio": STYLE_TARGETS[int(level or 2)],
        "livello": int(level or 2),
        "misure": [{"file": name, **metrics} for name, metrics in files],
        "problemi": {name: style_problems(metrics, level) for name, metrics in files},
    }
    payload["ok"] = not any(payload["problemi"][name] for name, _ in files)
    if args.json:
        emit(payload, code=0 if payload["ok"] else 1)

    lines = [
        f"# Leggibilita' (livello {level}: Gulpease >= {payload['criterio']['gulpease']}, "
        f"<= {payload['criterio']['parole_frase']} parole/frase)",
        "",
        "| File | Gulpease | Parole/frase | Frasi | >30 parole | Virgole/frase |",
        "|---|---|---|---|---|---|",
    ]
    for name, metrics in files:
        if not metrics["frasi"]:
            lines.append(f"| {name} | — | — | 0 | — | — |")
            continue
        lines.append(
            f"| {name} | {metrics['gulpease']} | {metrics['parole_frase']} | {metrics['frasi']} | "
            f"{metrics['frasi_lunghe_pct']}% | {metrics['virgole_frase']} |"
        )
    for name, metrics in files:
        for problem in payload["problemi"][name]:
            lines.append(f"- {name}: {problem}")
    if payload["ok"]:
        lines.append("- Tutto entro l'obiettivo di leggibilita' del livello.")
    emit(payload, as_text="\n".join(lines), code=0 if payload["ok"] else 1)


# caratteri fuori dal latino: quasi sempre refusi dell'agente, non contenuto
SUSPECT_RANGES = (
    (0x0370, 0x03FF), (0x0400, 0x04FF), (0x0590, 0x05FF),
    (0x0600, 0x06FF), (0x3000, 0x303F), (0x4E00, 0x9FFF),
)

# parole funzionali straniere che un modello lascia dentro la prosa italiana
FOREIGN_WORDS = ("through", "because", "which", "must", "there", "instead", "however", "between")


class ProseLint:
    """Refusi che lo schema non vede: lingua, ripetizioni, markdown rotto.

    Il validatore controlla la struttura; questo lint controlla la scrittura.
    Sono avvisi, non errori: non bloccano il riuso, ma rendono visibile il
    calo di qualita' di un modello piccolo o distratto.
    """

    def __init__(self) -> None:
        self.messages: list[str] = []

    def run(self, name: str, text: str) -> None:
        prose = self._strip_code(text)
        self._non_latin(name, prose)
        self._duplicate_lines(name, text)
        self._truncated_line(name, text)
        self._repeated_words(name, prose)
        self._repeated_fragment(name, prose)
        self._unbalanced_markdown(name, text)
        self._foreign_words(name, prose)

    @staticmethod
    def _strip_code(text: str) -> str:
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        return re.sub(r"`[^`]*`", " ", text)

    def _non_latin(self, name: str, prose: str) -> None:
        found: dict[str, int] = {}
        for char in prose:
            point = ord(char)
            if any(lo <= point <= hi for lo, hi in SUSPECT_RANGES):
                found[char] = found.get(char, 0) + 1
        if found:
            shown = ", ".join(f"{c} (U+{ord(c):04X})" for c in sorted(found))
            self.messages.append(f"{name}: caratteri non latini in prosa: {shown}")

    def _duplicate_lines(self, name: str, text: str) -> None:
        previous = ""
        for index, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped and len(stripped) > 20 and stripped == previous:
                self.messages.append(f"{name}: riga {index} duplicata di seguito a riga {index - 1}")
                return
            previous = stripped

    def _truncated_line(self, name: str, text: str) -> None:
        """Riga che ripete la coda della precedente: testo rigenerato due volte."""
        previous = ""
        for index, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if len(stripped) >= 18 and previous and stripped != previous and stripped in previous:
                self.messages.append(
                    f"{name}: riga {index} ripete la coda della riga {index - 1} (testo duplicato)"
                )
                return
            if stripped:
                previous = stripped

    def _repeated_words(self, name: str, prose: str) -> None:
        for match in re.finditer(r"\b(\w{4,})\s+\1\b", prose, flags=re.IGNORECASE):
            self.messages.append(f"{name}: parola ripetuta «{match.group(1)} {match.group(1)}»")
            return

    def _repeated_fragment(self, name: str, prose: str) -> None:
        pattern = r"\b((?:\w+\s+){2,6}\w+)\s+\1"
        for match in re.finditer(pattern, prose, flags=re.IGNORECASE):
            fragment = " ".join(match.group(1).split())
            self.messages.append(f"{name}: frammento ripetuto «{fragment}»")
            return

    def _unbalanced_markdown(self, name: str, text: str) -> None:
        problems = []
        if text.count("`") % 2:
            problems.append(f"{text.count('`')} backtick")
        if text.count("**") % 2:
            problems.append(f"{text.count('**')} «**»")
        if problems:
            self.messages.append(f"{name}: markdown sbilanciato ({', '.join(problems)})")

    def _foreign_words(self, name: str, prose: str) -> None:
        for word in FOREIGN_WORDS:
            if re.search(rf"\b{word}\b", prose, flags=re.IGNORECASE):
                self.messages.append(f"{name}: parola straniera rimasta in prosa: «{word}»")


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
    if meta.get("prereqs") and not isinstance(meta["prereqs"], list):
        warn("meta.json: 'prereqs' dovrebbe essere una lista di prerequisiti distinti")
    elif isinstance(meta.get("prereqs"), list):
        for item in meta["prereqs"]:
            if isinstance(item, str) and ";" in item:
                warn(f"meta.json: prerequisito multiplo in una voce sola «{item}»")

    lint = ProseLint()
    for name, text in texts.items():
        lint.run(name, text)
    for message in lint.messages:
        warn(message)

    level = meta.get("level") or 2
    for name, text in texts.items():
        metrics = style_metrics(text)
        if metrics["frasi"] < MIN_UNITS_FOR_STYLE:
            continue  # un glossario o una griglia corta non si giudicano sulla media
        for problem in style_problems(metrics, level):
            warn(f"{name}: {problem}")

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

# etichette che descrivono la sessione, non un contenuto da ripassare
SESSION_MARKERS = (
    "fine sessione", "chiusura sessione", "sessione conclusa", "sessione completata",
    "sessione completa", "avvio percorso", "inizio percorso", "avvio del percorso",
    "inizio del percorso", "avvio corso", "inizio corso", "fine corso", "riepilogo",
    "ripasso generale", "prima sessione",
)

# parole che non rendono "concetto" un'etichetta di sessione
SESSION_GENERIC = {
    "modulo", "moduli", "corso", "percorso", "sessione", "sessione", "parte", "parti",
    "lezione", "lezioni", "completato", "completati", "completata", "completate",
    "concluso", "conclusi", "chiuso", "chiusi", "fatto", "fatta", "svolto", "svolta",
    "terminato", "terminata", "nuovo", "nuova", "primo", "prima", "secondo", "seconda",
    "terzo", "terza", "quarto", "quinto", "tutto", "tutti", "tutte", "oggi", "finale",
}


def session_marker(name: str) -> str | None:
    """Se l'etichetta descrive la sessione invece di un contenuto, la marca.

    Serve a difendere la ripetizione spaziata: 'fine sessione: moduli 1-3'
    registrato come concetto crea una lacuna finta e un ripasso inutile.
    """
    flat = " ".join(norm(name).split())
    if not flat:
        return None
    for marker in SESSION_MARKERS:
        if marker not in flat:
            continue
        residue = [
            word for word in flat.replace(marker, " ").split()
            if word not in STOPWORDS and word not in SESSION_GENERIC and not word.isdigit()
        ]
        if not residue:
            return marker
    return None


def profiles_file() -> Path:
    """Alias dei profili allievo (`default` -> `Dario`) usati dopo un'unione."""
    return PROGRESS_DIR / ".profiles.json"


def profile_aliases() -> dict[str, str]:
    data = read_json(profiles_file(), {})
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def resolve_learner(learner: str) -> str:
    """Nome canonico del profilo: segue gli alias registrati da `iv.py learner merge`.

    Serve a non far ripartire i progressi da zero: dopo aver unito `default` in
    `Dario`, un agente che omette `--learner` deve continuare a scrivere in `Dario`.
    """
    name = (learner or "default").strip() or "default"
    aliases = {key.casefold(): value for key, value in profile_aliases().items()}
    for _ in range(5):
        target = aliases.get(name.casefold())
        if not target or target.casefold() == name.casefold():
            break
        name = target
    return name


# caratteri che non possono stare in un nome di cartella (o che aprono percorsi)
UNSAFE_PROFILE = re.compile(r'[\\/:*?"<>|]')


def clean_profile_name(name: str) -> str:
    """Nome profilo leggibile e sicuro come nome di cartella.

    Spazi e accenti sono ammessi ('Marco Rossi' e' un nome normale); separatori
    di percorso e metacaratteri no, altrimenti `--learner ..\\x` scriverebbe
    fuori da `data/progress/`.
    """
    cleaned = re.sub(r"\s+", " ", str(name or "")).strip().strip(".")
    if not cleaned:
        die("Nome profilo vuoto: passane uno come `--learner \"Marco Rossi\"`.")
    if UNSAFE_PROFILE.search(cleaned):
        die(
            f"Nome profilo '{name}' contiene caratteri non ammessi (\\ / : * ? \" < > |): "
            "usane uno semplice, anche con spazi."
        )
    if len(cleaned) > 60:
        die(f"Nome profilo troppo lungo ({len(cleaned)} caratteri, massimo 60).")
    return cleaned


def learner_dir(learner: str) -> Path:
    """Cartella del profilo allievo.

    Segue gli alias e riusa un profilo esistente ignorando maiuscole e spazi:
    'Dario', 'dario' e ' Dario ' sono la stessa persona, non tre profili con
    progressi separati.
    """
    name = resolve_learner(learner)
    cleaned = clean_profile_name(name)
    if PROGRESS_DIR.is_dir():
        for path in sorted(PROGRESS_DIR.iterdir()):
            if path.is_dir() and path.name.casefold() == cleaned.casefold():
                return path
    return PROGRESS_DIR / cleaned


def learner_profiles() -> list[str]:
    """Profili che hanno gia' dei progressi su disco."""
    if not PROGRESS_DIR.is_dir():
        return []
    return sorted(p.name for p in PROGRESS_DIR.iterdir() if p.is_dir())


def other_profiles(learner: str, slug: str | None = None) -> list[dict]:
    """Profili diversi da quello selezionato, con quanti progressi contengono.

    Serve a rendere visibile uno sbaglio frequente degli agenti: registrare con
    un nome allievo diverso e poi leggere i progressi con quello di default.
    """
    selected = learner_dir(learner).name
    found = []
    for name in learner_profiles():
        if name == selected:
            continue
        folder = PROGRESS_DIR / name
        if slug is None:
            count = len(list(folder.glob("*.json")))
        else:
            count = 1 if (folder / f"{slug}.json").exists() else 0
        if count:
            found.append({"learner": name, "argomenti": count})
    return found


def progress_path(slug: str, learner: str) -> Path:
    return learner_dir(learner) / f"{slug}.json"


def blank_progress(slug: str, learner: str) -> dict:
    return {
        "slug": slug,
        "learner": learner,
        "level": None,
        "created": today(),
        "last_session": "",
        "mode": None,
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
    entry = find_entry(reg, args.topic)
    if not entry:
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
        data["level"] = entry.get("level")
    # Stessa cosa per la modalita': senza ereditarla il diario diceva `null`
    # per sessioni condotte in modalita' docenza o esame.
    if args.mode:
        data["mode"] = args.mode
    elif data.get("mode") is None:
        data["mode"] = entry.get("mode")
    effective_mode = data.get("mode")
    if args.module and args.module not in data["modules_seen"]:
        data["modules_seen"].append(args.module)
    data["log"].append(
        {
            "date": today(),
            "ora": now().split(" ")[1],
            "modalita": effective_mode,
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
        marker = session_marker(name)
        if marker:
            die(
                f"«{name}» descrive la sessione, non un concetto da ripassare ({marker}). "
                "Registra i contenuti verificati con --concept (es. 'previsione della parola "
                "successiva') e la sintesi della sessione con --summary: le etichette di "
                "sessione inquinano lacune e ripetizione spaziata."
            )
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
    # Il diario e' un file derivato: si rigenera dai progressi, come il registro.
    # Cosi' non resta indietro se l'agente si dimentica `stats --write`.
    diary = write_diary(args.learner)
    resolved = learner_dir(args.learner).name
    emit(
        {
            "ok": True,
            "topic": args.topic,
            "learner": resolved,   # profilo reale su disco (alias e varianti risolte)
            "sessione": data["sessions"],
            "minuti_totali": data["total_minutes"],
            "modalita": effective_mode,
            "programmati": scheduled,
            "da_ripassare_oggi": prossimi,
            "file": str(progress_path(args.topic, args.learner)),
            "diario": str(diary),
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
    return {"ok": True, "learner": learner_dir(learner).name, "entro_il": limit,
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


def build_diary(learner: str, within: int) -> dict:
    """Compone il diario a partire dai progressi: usato sia da `stats` sia da `log`."""
    reg = sync_from_disk(load_registry())
    data_by_slug = {d.get("slug"): d for d in all_progress(learner)}
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

    due = due_items(learner, within)
    top_weak = sorted(weak_counter.items(), key=lambda kv: kv[1], reverse=True)[:5]

    lines = [
        f"# Diario di apprendimento — {learner}",
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
        f"| Concetti da ripassare (entro {within}g) | {len(due['concetti_da_ripassare'])} |",
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
    return {
        "learner": learner, "rows": rows, "total_minutes": total_minutes,
        "total_sessions": total_sessions, "top_weak": top_weak, "stale": stale,
        "due": due, "report": "\n".join(lines) + "\n",
    }


def write_diary(learner: str, within: int = 7) -> Path:
    """Scrive `DIARIO.md`: file derivato, rigenerabile dai progressi."""
    destination = learner_dir(learner) / "DIARIO.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_diary(learner, within)["report"], encoding="utf-8")
    return destination


def cmd_stats(args) -> None:
    diary = build_diary(args.learner, args.within)
    destination = write_diary(args.learner, args.within) if args.write else None
    if args.json:
        emit({"ok": True, "learner": learner_dir(args.learner).name, "argomenti": diary["rows"],
              "minuti_totali": diary["total_minutes"], "sessioni": diary["total_sessions"],
              "lacune_ricorrenti": diary["top_weak"], "riassunto": diary["report"],
              "scritto_in": str(destination) if destination else None})
    emit({"ok": True}, as_text=diary["report"] + (f"\n_Diario salvato in:_ `{destination}`\n" if destination else ""))


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
                "da_rigenerare": frame_state(entry)["da_rigenerare"],
                "cornice_aggiornabile": frame_state(entry)["aggiornabile"],
            }
        )
    altri = other_profiles(args.learner)
    if args.json:
        emit({"ok": True, "base_version": BASE_VERSION, "learner": learner_dir(args.learner).name,
              "argomenti": rows, "altri_profili": altri})
    if not rows:
        emit({"ok": True}, as_text="Nessun argomento nel registro: al primo avvio se ne crea uno.")
    lines = ["| Argomento | Slug | Stato | Livello | Sessioni | Ultima | Cornice |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        flag = (
            "da rigenerare" if r["da_rigenerare"]
            else f"{r['base_version']} (aggiornabile)" if r["cornice_aggiornabile"]
            else r["base_version"]
        )
        lines.append(
            f"| {r['title']} | `{r['slug']}` | {r['stato']} | {r['livello']} | {r['sessioni']} | {r['ultima']} | {flag} |"
        )
    if altri:
        # Visibilita' sui progressi registrati sotto un altro nome allievo: senza
        # questa riga la tabella direbbe "0 sessioni, mai" su un argomento studiato.
        elenco = ", ".join(f"{a['learner']} ({a['argomenti']})" for a in altri)
        lines += ["", f"_Progressi di altri profili: {elenco}. Usa `--learner <nome>` per vederli._"]
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


def merge_cards(left: dict, right: dict) -> dict:
    """Sceglie la scheda SM-2 piu' avanzata fra due versioni dello stesso concetto.

    Vince chi ha piu' ripetizioni; a parita', chi e' stato ripassato piu' di recente.
    Unire i progressi non deve mai far *retrocedere* una scadenza.
    """
    def rank(card: dict) -> tuple:
        return (int(card.get("reps", 0)), str(card.get("last_review") or ""))

    winner = left if rank(left) >= rank(right) else right
    merged = dict(winner)
    merged["lapses"] = int(left.get("lapses", 0)) + int(right.get("lapses", 0))
    return merged


def merge_progress_data(source: dict, target: dict) -> dict:
    """Unisce i progressi dello stesso argomento in due profili diversi."""
    merged = dict(target)
    merged["sessions"] = int(target.get("sessions", 0)) + int(source.get("sessions", 0))
    merged["total_minutes"] = int(target.get("total_minutes", 0)) + int(source.get("total_minutes", 0))
    merged["level"] = target.get("level") or source.get("level")
    merged["mode"] = target.get("mode") or source.get("mode")
    merged["created"] = min(
        [d for d in (target.get("created"), source.get("created")) if d] or [today()]
    )
    merged["last_session"] = max(
        [d for d in (target.get("last_session"), source.get("last_session")) if d] or [""]
    )

    modules = list(target.get("modules_seen") or [])
    for module in source.get("modules_seen") or []:
        if module not in modules:
            modules.append(module)
    merged["modules_seen"] = modules

    concepts = dict(target.get("concepts") or {})
    for key, card in (source.get("concepts") or {}).items():
        concepts[key] = merge_cards(concepts[key], card) if key in concepts else card
    merged["concepts"] = concepts

    merged["weak_spots"] = sorted(set(target.get("weak_spots") or []) | set(source.get("weak_spots") or []))
    entries = list(target.get("log") or []) + list(source.get("log") or [])
    merged["log"] = sorted(entries, key=lambda e: (e.get("date", ""), e.get("ora", "")))
    return merged


def profile_summary(folder: Path) -> dict:
    """Contenuto di un profilo: serve a elencare, rinominare e cancellare."""
    files = sorted(folder.glob("*.json"))
    sessions = minutes = 0
    slugs = []
    for path in files:
        data = read_json(path, {})
        if not isinstance(data, dict):
            continue
        slugs.append(data.get("slug") or path.stem)
        sessions += int(data.get("sessions", 0) or 0)
        minutes += int(data.get("total_minutes", 0) or 0)
    return {"learner": folder.name, "argomenti": len(files), "sessioni": sessions,
            "minuti": minutes, "slug": slugs}


def rewrite_profile_aliases(source: str, target: str) -> dict:
    """Il nome vecchio punta al nuovo, e chi puntava al vecchio lo segue.

    Senza questo, `--learner Giulia` dopo una rinomina ricreerebbe un profilo
    vuoto e le sessioni successive finirebbero nel posto sbagliato.
    """
    aliases = profile_aliases()
    updated = {
        key: (target if value.casefold() == source.casefold() else value)
        for key, value in aliases.items()
    }
    updated.pop(target, None)  # un alias con il nome nuovo sarebbe un auto-riferimento
    if source.casefold() != target.casefold():
        updated[source] = target
    write_json(profiles_file(), updated)
    return updated


def cmd_learner(args) -> None:
    if args.action == "list":
        rows = [profile_summary(PROGRESS_DIR / name) for name in learner_profiles()]
        payload = {"ok": True, "profili": rows, "alias": profile_aliases()}
        if args.json:
            emit(payload)
        lines = ["| Profilo | Argomenti | Sessioni | Minuti |", "|---|---|---|---|"]
        lines += [f"| {r['learner']} | {r['argomenti']} | {r['sessioni']} | {r['minuti']} |" for r in rows]
        if not rows:
            lines.append("| (nessun profilo) | 0 | 0 | 0 |")
        for alias, canonical in sorted(profile_aliases().items()):
            lines.append(f"\n_`{alias}` è un alias di `{canonical}`._")
        emit(payload, as_text="\n".join(lines))

    if args.action == "rename":
        source_dir = learner_dir(args.source)
        if not source_dir.is_dir():
            die(f"Il profilo '{args.source}' non ha progressi in {source_dir}.")
        new_name = clean_profile_name(args.to)
        if source_dir.name == new_name:
            die(f"Il profilo si chiama già '{new_name}'.")
        existing = learner_dir(args.to)
        if existing.is_dir() and existing.name.casefold() != source_dir.name.casefold():
            die(
                f"Esiste già un profilo '{existing.name}' con dei progressi: per unire i due usa "
                f"`iv.py learner merge \"{source_dir.name}\" --into \"{existing.name}\"`."
            )
        summary = profile_summary(source_dir)
        target_dir = PROGRESS_DIR / new_name
        if source_dir.name.casefold() == new_name.casefold():
            # solo maiuscole/spazi diversi: su Windows la rinomina diretta puo' fallire
            through = PROGRESS_DIR / f".{new_name}.tmp"
            source_dir.rename(through)
            through.rename(target_dir)
        else:
            source_dir.rename(target_dir)
        for path in sorted(target_dir.glob("*.json")):
            data = read_json(path, None)
            if isinstance(data, dict):
                data["learner"] = target_dir.name
                write_json(path, data)
        aliases = rewrite_profile_aliases(source_dir.name, target_dir.name)
        diary = write_diary(target_dir.name)
        emit(
            {
                "ok": True, "azione": "Profilo allievo rinominato",
                "da": source_dir.name, "a": target_dir.name,
                "argomenti": summary["argomenti"], "sessioni": summary["sessioni"],
                "minuti": summary["minuti"], "slug": summary["slug"],
                "alias": aliases, "diario": str(diary),
                "nota": f"Il vecchio nome '{source_dir.name}' resta come alias: i comandi che lo usano "
                        f"continuano a scrivere in '{target_dir.name}'.",
            }
        )

    if args.action == "delete":
        target_dir = learner_dir(args.name)
        if not target_dir.is_dir():
            die(f"Il profilo '{args.name}' non ha progressi in {target_dir}.")
        summary = profile_summary(target_dir)
        aliases = profile_aliases()
        removed = sorted(
            key for key, value in aliases.items()
            if key.casefold() == target_dir.name.casefold()
            or value.casefold() == target_dir.name.casefold()
        )
        payload = {
            "profilo": target_dir.name, "cartella": str(target_dir),
            "argomenti": summary["argomenti"], "sessioni": summary["sessioni"],
            "minuti": summary["minuti"], "slug": summary["slug"],
            "alias_che_verrebbero_rimossi": removed,
            "irreversibile": "sessioni, voti, lacune e diario di questo profilo vanno persi; "
                             "le sotto-skill e gli altri profili non si toccano",
        }
        if not args.yes:
            emit(
                {"ok": False, "azione": "Anteprima di cancellazione: niente è stato modificato",
                 **payload, "conferma": "Rilancia con --yes per cancellare definitivamente."},
                code=1,
            )
        shutil.rmtree(target_dir)
        for key in removed:
            aliases.pop(key, None)
        write_json(profiles_file(), aliases)
        emit({"ok": True, "azione": "Profilo allievo cancellato", **payload,
              "alias_rimossi": removed})

    if args.action != "merge":
        die(f"Azione '{args.action}' non riconosciuta.")

    source = (args.source or "").strip()
    target = (args.into or "").strip()
    if not source or not target:
        die("Indica profilo sorgente e destinazione: iv.py learner merge <sorgente> --into <destinazione>")
    if learner_dir(source).name.casefold() == learner_dir(target).name.casefold():
        die("Sorgente e destinazione sono lo stesso profilo: non c'è niente da unire.")
    if not learner_dir(source).is_dir():
        die(f"Il profilo '{source}' non ha progressi in {learner_dir(source)}.")

    target_dir = learner_dir(target)
    target_dir.mkdir(parents=True, exist_ok=True)
    source_dir = learner_dir(source)
    uniti = []
    for path in sorted(source_dir.glob("*.json")):
        incoming = read_json(path, None)
        if not isinstance(incoming, dict):
            continue
        slug = incoming.get("slug") or path.stem
        incoming["slug"] = slug
        destination = target_dir / f"{slug}.json"
        existing = read_json(destination, None)
        merged = merge_progress_data(incoming, existing) if isinstance(existing, dict) else incoming
        merged["learner"] = target_dir.name
        write_json(destination, merged)
        path.unlink()  # il file del profilo assorbito non deve restare (né essere riletto)
        uniti.append({"slug": slug, "sessioni": int(merged.get("sessions", 0) or 0),
                      "minuti": int(merged.get("total_minutes", 0) or 0),
                      "unito_a_esistente": isinstance(existing, dict)})

    # Il diario del profilo assorbito non ha più senso: quello della destinazione sì.
    source_diary = source_dir / "DIARIO.md"
    if source_diary.exists():
        source_diary.unlink()
    if not any(source_dir.iterdir()):
        source_dir.rmdir()

    aliases = profile_aliases()
    aliases[source_dir.name] = target_dir.name
    write_json(profiles_file(), aliases)
    diary = write_diary(target_dir.name)

    emit(
        {
            "ok": True,
            "azione": "Profili allievo uniti",
            "sorgente": source_dir.name,
            "destinazione": target_dir.name,
            "argomenti": uniti,
            "alias_registrato": {source_dir.name: target_dir.name},
            "diario": str(diary),
            "nota": (
                f"Da adesso `--learner {source_dir.name}` (e l'omissione di --learner se sul profilo "
                f"'{source_dir.name}') scrive in '{target_dir.name}': i progressi non si riseparano."
            ),
        }
    )


def cmd_status(args) -> None:
    reg = sync_from_disk(load_registry())
    topics = [e for e in reg["topics"] if e.get("status") != "merged"]
    stale = [e["slug"] for e in topics if frame_state(e)["da_rigenerare"]]
    updateable = [e["slug"] for e in topics if frame_state(e)["aggiornabile"]]
    drafts = [e["slug"] for e in topics if e.get("status") == "draft"]
    due = due_items(args.learner, 0)
    profili = learner_profiles()
    altri = other_profiles(args.learner)
    resolved = learner_dir(args.learner).name
    payload = {
        "ok": True,
        "base_version": BASE_VERSION,
        "learner": resolved,   # nome reale del profilo, anche se e' un alias
        "profilo_richiesto": args.learner if resolved != args.learner else None,
        "profili": profili,
        "altri_profili_con_progressi": altri,
        "argomenti": len(topics),
        "attivi": len([e for e in topics if e.get("status") == "active"]),
        "bozze_da_completare": drafts,
        "da_rigenerare": stale,
        "cornice_aggiornabile": updateable,
        "ripassi_oggi": len(due["concetti_da_ripassare"]),
        "prossimo_passo": (
            "Completa le bozze: " + ", ".join(drafts) if drafts
            else "Rigenera gli argomenti con cornice vecchia: " + ", ".join(stale) if stale
            else (
                "Nessun debito bloccante. Aggiornamento opzionale (cornice "
                f"{BASE_VERSION}) disponibile per: " + ", ".join(updateable)
                if updateable else
                (
                    "I progressi sono in un altro profilo allievo ("
                    + ", ".join(a["learner"] for a in altri)
                    + "): rilancia il comando con `--learner <nome>`."
                    if altri and not any(learner_dir(args.learner).glob("*.json")) else
                    "Nessun debito tecnico: puoi dedicarti allo studio."
                )
            )
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

    p = sub.add_parser("style", help="Misura la leggibilita' di una sotto-skill o di una bozza")
    p.add_argument("slug", nargs="?")
    p.add_argument("--file")
    p.add_argument("--text")
    p.add_argument("--level", type=int, choices=[1, 2, 3, 4])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_style)

    p = sub.add_parser("learner", help="Profili allievo: elenco e unione dei progressi")
    actions = p.add_subparsers(dest="action", required=True)
    pl = actions.add_parser("list", help="Profili con progressi e alias")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_learner)
    pm = actions.add_parser("merge", help="Unisce un profilo in un altro")
    pm.add_argument("source")
    pm.add_argument("--into", required=True)
    pm.add_argument("--json", action="store_true")
    pm.set_defaults(func=cmd_learner)
    pr = actions.add_parser("rename", help="Rinomina un profilo (il vecchio nome resta come alias)")
    pr.add_argument("source")
    pr.add_argument("--to", required=True)
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_learner)
    pd = actions.add_parser("delete", help="Cancella un profilo e i suoi progressi (serve --yes)")
    pd.add_argument("name")
    pd.add_argument("--yes", action="store_true")
    pd.add_argument("--json", action="store_true")
    pd.set_defaults(func=cmd_learner)

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
