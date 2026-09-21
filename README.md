# Virtual Teacher

**A skill that turns an agent into your teacher, in any subject.**

**An AI agent skill that studies with you and learns each topic only once.**
Rigorous about content, plain-spoken in delivery: concrete examples, constant checking,
and a memory of your progress that survives across sessions.

[Versione italiana →](README.it.md)

**Repository:** https://github.com/Dario-Fe/LearnUp — the skill's name is `insegnante-virtuale`.

---

## The problem

Every time you ask an assistant *"explain quadratic equations"*, you start from scratch. The explanation
is generic, the style changes, there is no path, nobody remembers that three days ago you got stuck on
the quadratic formula — and next week you explain it all over again.

## The idea: a regenerating system

A fixed **frame** of pedagogical rules, plus **tailor-made sub-skills** generated per topic, saved to disk,
and **reused** in later sessions.

```
                 ┌──────────────────────────────┐
   you: "I want  │  FRAME (invariant)           │
   to study X"   │  rigor, clarity, examples,   │
        │        │  levels, checking, memory    │
        ▼        └──────────────┬───────────────┘
 ┌─────────────┐              │ constrains
 │ iv.py find  │              ▼
 │ does X exist│      ┌──────────────────────┐
 └──────┬──────┘      │ SUB-SKILL for X      │  ← generated once,
        │             │ path · glossary      │    then REUSED
   ┌────┴────┐        │ mistakes · exercises │
   │ yes │ no│        │ assessment · sources │
   ▼     ▼   └────────┴──────────────────────┘
 REUSE  GENERATE → validate → register
        │
        ▼
 ┌──────────────────────────────┐
 │ LEARNER STATE                │  ← never regenerated
 │ sessions · weak spots · SM-2 │
 └──────────────────────────────┘
```

Four layers, four different lifecycles:

| Layer | Lives in | Changes when |
|---|---|---|
| **Frame** (shared rules) | `references/` | Almost never; it is versioned (`BASE_VERSION`) |
| **Sub-skills** (topic knowledge) | `data/topics/<slug>/` | Generated once, then refined or regenerated |
| **Learner state** | `data/progress/<learner>/` | Every session |
| **Orchestration** | `SKILL.md` + `scripts/iv.py` | Every session |

That separation is the heart of the project: knowledge is regenerable, your progress is not.

---

## What it does

- **Asks what you want to study on startup**, and searches before generating: topics you have already
  studied are reused.
- **Generates a complete sub-skill** for a new topic: a modular learning path, a glossary, a bank of
  typical mistakes, exercises of increasing difficulty with self-assessment criteria, a final assessment,
  and per-level sources.
- **Validates before use**: an uncompiled skeleton cannot be activated (the validator blocks placeholders,
  modules with no verifiable objective, exercises with no solutions).
- **Recognises duplicates**: aliases and merging of similar topics, without losing progress.
- **Remembers and schedules reviews**: simplified SM-2 spaced repetition on every checked concept.
- **Keeps a learning diary**: minutes studied, topics going cold, recurring weak spots, what to review now.
- **Three modes**: self-learner, exam preparation, teaching others (with separate learner profiles).
- **Declared rigor**: every claim is labelled *well-established / simplified / contested / inference /
  to be verified*, and every sub-skill has a **To be verified** section. No invented sources.

---

## Requirements

- **Python 3.10+** (no external dependencies, standard library only)
- An AI agent able to read files and run commands (Claude Code, Codebuff, Cursor, Windsurf…)
- Git, if you want to version your topics

---

## Installation

The skill follows the **Agent Skills** standard (`SKILL.md` with `name` + `description` frontmatter).

### 1. With the `skills` CLI (recommended)

```bash
npx skills add Dario-Fe/LearnUp --skill insegnante-virtuale --yes
```

The repository is `Dario-Fe/LearnUp`; the *skill* is called `insegnante-virtuale` — that is the name
`--skill` expects, and the name your agent loads.

### 2. Manually, inside a project

Copy the contents of this repository into:

```
your-project/.agents/skills/insegnante-virtuale/
```

(Claude Code also accepts `your-project/.claude/skills/insegnante-virtuale/`)

The agent finds the skill by name: just ask it to teach you something.

### 3. Development: the repository *is* the skill

Clone the repository and link the folder to the discovery location:

```bash
git clone https://github.com/Dario-Fe/LearnUp.git
cd LearnUp
# Linux / macOS
mkdir -p .agents/skills && ln -s "$(pwd)" .agents/skills/insegnante-virtuale
# Windows (junction, no administrator rights required)
powershell -NoProfile -Command "New-Item -ItemType Junction -Path '.agents\skills\insegnante-virtuale' -Target (Get-Location)"
```

---

## Quick start

Nothing to configure: just ask.

| You say | What happens |
|---|---|
| *"I want to study the Feynman technique"* | Searches the registry; if the topic is missing it generates the sub-skill, validates it and starts |
| *"Let's continue the Feynman technique"* | Reuses the saved sub-skill, reads your progress and resumes where you left off |
| *"Let's prepare for my statistics exam"* | Switches to exam mode: backwards plan, timed mock exams, pass thresholds |
| *"Let's review"* | Shows concepts due for review and opens with 5 minutes of active recall |
| *"Explain X to a beginner"* | Level 1-2, concrete example, micro-check, and records your score |
| *"How did my studying go this month?"* | Updates and shows the learning diary |

The first time you study a new topic, the agent fills in eight files (path, typical mistakes, glossary,
exercises, assessment, sources, metadata, contract) and checks the schema before starting. It takes a few
minutes, but that knowledge stays and is reused forever.

---

## How it works

### The regenerating cycle

| Step | What happens | Command |
|---|---|---|
| **Search** | Normalisation (accents, stopwords, stems), aliases and similarity → `exact` / `variant` / `candidates` / `none` | `iv.py find "…"` |
| **Decision** | The agent reuses, asks about ambiguous matches, merges, or generates | `iv.py alias` · `iv.py merge` |
| **Generation** | Skeleton from the template, then content written by the agent | `iv.py create --title "…"` |
| **Check** | Schema, substance minimums, leftover placeholders: blocks drafts | `iv.py validate <slug>` |
| **Activation** | Status `active`, content hash, frame version | `iv.py register <slug>` |
| **Memory** | Sessions, grades, weak spots, spaced repetition | `iv.py log` · `iv.py due` |
| **Regeneration** | The frame changes → topics with an older version are flagged | `iv.py status` |

The registry matches **canonical keys** (content words, sorted, accent-free) and **aliases**: "Ancient Rome",
"Roman Empire" and "Roman history" can converge on one topic instead of generating three near-duplicates.

### What a sub-skill contains

```
data/topics/<slug>/
├── SKILL.md            # teaching contract, module map, how to run a session
├── percorso.md         # modules: core idea, concrete example, counterexample, check
├── errori-tipici.md    # misconceptions: why they are tempting and how to dismantle them
├── glossario.md        # minimum vocabulary + terms NOT to use
├── esercizi.md         # basic → intermediate → advanced, hidden solutions with self-assessment
├── verifica.md         # mastery criteria, final assessment, recovery plan
├── fonti.md            # sources per level, open debates, declared uncertainties
└── meta.json           # metadata managed by the engine
```

### The invariant frame

- **Declared rigor.** Every claim carries its reliability label; uncertainties go into *To be verified*.
  Inventing sources, dates, numbers or citations is forbidden: if you don't know, say so and say how to check.
- **Dosable teaching.** Four levels (curious → beginner → student → colleague), stated up front and changeable.
- **Concrete examples are mandatory.** No abstract concept without a hand-checkable example and a counterexample.
- **Check before moving on.** Micro-questions after each concept, and a recorded grade: 0-2 weak spot
  (short review interval), 3 fragile, 4 solid, 5 can explain it.
- **Available but not complacent.** No "you got it perfectly" without evidence, no facts bent to what the
  learner hopes to hear.
- **Controlled cognitive load.** At most three new concepts per session, then consolidation.
- **Prerequisites before shortcuts.** A missing prerequisite becomes its own sub-skill, instead of being
  badly explained in thirty seconds.

### Memory and spaced repetition

Every checked concept becomes an item scheduled with **simplified SM-2** (intervals 1 → 6 → interval × ease
factor, reset after a low grade). The diary shows minutes studied, average grade per topic, **recurring weak
spots**, topics going cold (over 21 days) and actionable suggestions.

---

## Command reference

All commands run from the skill folder. `--json` where available, for agent-friendly output.

```bash
# regenerating cycle
python scripts/iv.py status                      # debts, drafts, to-regenerate, due today
python scripts/iv.py find "<topic>" [--json]     # does it exist? → reuse / ask / generate
python scripts/iv.py create --title "…" --level 2 --mode esame --prereq "…" --tag "…" --alias "…"
python scripts/iv.py validate <slug> | --all [--json]
python scripts/iv.py register <slug> [--self-check "…"] [--force]
python scripts/iv.py list [--json]               # saved topics
python scripts/iv.py show <slug>                 # sub-skill files + progress

# registry maintenance
python scripts/iv.py alias <slug> --add "alternative name" | --list
python scripts/iv.py merge <duplicate> <kept-slug> [--learner name]
python scripts/iv.py reindex                     # rebuild the index from files on disk

# studying and review
python scripts/iv.py log --topic <slug> --minutes 45 --summary "…" --module 2 \
      --concept "concept" --grade 4 --concept "other" --grade 1 --next "…" [--learner name]
python scripts/iv.py due [--within 7] [--json]   # what to review now
python scripts/iv.py stats [--write] [--json]    # learning diary (Markdown)
```

Global options: `--data <folder>` (or the `IV_DATA` environment variable) to keep data outside the skill,
`--skill-dir <folder>` to point at templates and references.

---

## Repository structure

```
.
├── SKILL.md                  # orchestrator: startup, reuse or generate, teach, close
├── README.md / README.it.md  # this documentation
├── AGENTS.md                 # notes for agents maintaining the skill
├── LICENSE                   # MIT
├── references/               # THE FRAME (shared, invariant rules)
│   ├── costituzione.md
│   ├── protocollo-sessione.md
│   ├── contratto-output.md
│   ├── modalita.md
│   └── schema-sottoskill.md
├── scripts/iv.py             # engine: registry, search, validation, progress, reviews
├── assets/templates/topic/   # skeleton of a new sub-skill
├── tests/test_iv.py          # 39 engine tests
└── data/
    ├── registry.json         # index (regenerable, not versioned)
    ├── topics/<slug>/        # THE SAVED SUB-SKILLS
    │   └── metodo-feynman/   # complete, validated reference example
    └── progress/<learner>/   # learner state (not versioned)
```

### Included example

`data/topics/metodo-feynman/` is a complete, validated sub-skill that doubles as the **quality standard**:
hand-checkable examples, counterexamples, five dismantled misconceptions, seven self-assessable exercises,
declared uncertainties. Delete it with:

```bash
rm -rf data/topics/metodo-feynman && python scripts/iv.py reindex
```

---

## Extending the system

- **New pedagogical rule** → add it to `references/costituzione.md`, bump `BASE_VERSION` in `scripts/iv.py`:
  topics with an older version will show up in `iv.py status` as `da_rigenerare`.
- **New mode** (corporate course, tutoring…) → `references/modalita.md` + the `MODES` tuple in `iv.py`.
- **New sub-skill file** (flashcards, mind maps…) → template in `assets/templates/topic/`,
  `REQUIRED_FILES` in `iv.py`, section in `references/schema-sottoskill.md`.
- **New quality check** → `validate_topic()` in `iv.py`, with a test in `tests/test_iv.py`.
- **New metadata field** → `meta.json` template + `REGISTRY_ENTRY_FIELDS` in `iv.py`.

### Tests

```bash
python -m unittest discover -s tests -t tests
python scripts/iv.py validate --all     # health of every sub-skill
```

---

## Roadmap

Ordered by value for effort. *Status: 💡 idea · 🔍 exploring · 🛠 planned.*

### v0.2 — Exporting results 🛠

Everything the system accumulates in `data/` is currently readable only from a terminal. The goal is to
get it out.

- `iv.py export --format md|json|csv|html` with `--topic`, `--learner`, `--output`.
  - **Markdown**: readable study report (per session, per topic, per month).
  - **JSON**: complete, stable export for integrations.
  - **Anki CSV**: one row per tracked concept (`front`, `back`, `tags`, `due`, `ease`) with **stable IDs**
    derived from the concept key, so re-importing never loses review history.
  - **Static HTML**: diary + topic list + review schedule, publishable on GitHub Pages with no backend.
- `iv.py export --format pdf` via Pandoc when installed (Markdown fallback).
- "Report card" output: per topic, level reached, open weak spots, time invested, next steps.
- Backup/restore of the whole `data/` folder in a single archive (`iv.py backup --out study.zip`).

### v0.3 — Web interface 💡

The usability leap: studying and reviewing without a terminal. Two stages, to avoid adding a backend
before it is needed:

1. **Static dashboard** (derived from v0.2): HTML generated from the data, zero dependencies, works offline
   and on GitHub Pages. Views: diary, topics, concepts due, sub-skill health.
2. **Local app** (FastAPI or Flask + HTMX, no JS build step):
   - *Guided session*: renders one module at a time, with checks and grades;
   - *Review*: flashcards from tracked concepts, with grade buttons that update SM-2;
   - *Topic editor*: create and edit a sub-skill with live validation;
   - *Diary*: charts of time, recurring weak spots, topics going cold.
   Design requirement: **local-first**, no accounts, data never leaves your machine.

### v0.4 — Smarter topics 🔍

- **Semantic search** alongside lexical matching (local embeddings) to catch duplicates worded differently.
- **Syllabus import**: from a PDF or a list of chapters, assisted generation of the module plan with human
  review before validation.
- **Automatic child sub-skills**: from prerequisites detected in the path, propose cascading creation.
- **Weak-spot analysis**: if the same mistake recurs across topics, propose a cross-cutting sub-skill.

### v0.5 — Integrations 💡

- **MCP server**: expose `iv.py` as MCP tools so any compatible client can use the system without knowing
  the command line.
- **Reminders**: review notifications by email or calendar (exportable `.ics` available from v0.2).
- **RAG over your own material**: index your lecture notes and PDFs as the preferred source of a sub-skill.
- **GitHub Action**: automatic sub-skill validation on pull requests (`iv.py validate --all`) once the repo
  becomes a shared library of learning paths.
- **Shared topic registry**: import/export individual sub-skills from other users, merging local progress.
- **Upgrade hook**: guided regeneration session when the frame changes.

### Parking lot 💡

Internationalisation of the frame (the references are in Italian), per-discipline pedagogical packs
(maths, languages, law need different dosage), auto-graded quizzes for open answers, text-to-speech to
re-listen to a lesson, Obsidian integration.

---

## The repository: what is versioned, and how to fork it

The repository **is** the skill: everything needed is already in the root. Version these:

```
SKILL.md  README.md  README.it.md  AGENTS.md  LICENSE  .gitignore
references/  scripts/  assets/  tests/
data/topics/metodo-feynman/     # reference example (optional)
```

These stay out (already in `.gitignore`): `data/progress/` (your progress), `data/registry.json`
(regenerable: rebuilt on first command from `data/topics/*/meta.json`), `data/_merged/`, `.agents/`
(local link), `__pycache__/`.

```bash
git init
git add .
git status          # make sure nothing personal shows up
git commit -m "Virtual Teacher: a regenerating study skill"
git branch -M main
git remote set-url origin https://github.com/<your-user>/LearnUp.git   # or: git remote add origin ...
git push -u origin main
```

With the GitHub CLI, when creating a new repository of your own:
`gh repo create <your-user>/LearnUp --public --source=. --push`.

The upstream repository already exists at **https://github.com/Dario-Fe/LearnUp**, so for a fork you
do not need `git init` at all: fork it on GitHub, clone your fork, and push there. In that case
replace the copyright holder in `LICENSE` with your own name.

---

## Known limitations

- **Validation guarantees structure and minimums, not the truth of the content.** Quality depends on the
  generating agent: that is why reliability labels exist, and why every sub-skill has a *To be verified* section.
- **Search is lexical**, not semantic: ambiguous cases are decided by the agent, which asks you to confirm.
- **Spaced repetition is simplified SM-2**, one item per concept (no multiple cards).
- **Sub-skills live inside the skill** rather than being top-level skills, so they do not pollute the agent's
  routing with dozens of competing descriptions. They are loaded by reading the file path.
- **The frame is in Italian**: generated content follows the learner's language, the rules do not
  (internationalisation is on the roadmap).

---

## FAQ

**How do I activate it?** Just ask: *"I want to study X"*, *"explain Y"*, *"let's prepare for my Z exam"*,
*"let's review"*. The skill loads itself based on its description. If your client doesn't pick it up, ask
for it explicitly: *"use the insegnante-virtuale skill"*. After installing it, start a new chat.

**Does it work in English?** Yes: sub-skills are written in the learner's language. The frame
(the files in `references/`) is in Italian.

**I updated the rules — do I lose my progress?** No. Progress lives in `data/progress/`, separate from
knowledge. Bumping `BASE_VERSION` flags topics as `da_rigenerare` so they can be realigned.

**Can two people study with it?** Yes: `--learner <name>` on `log`, `due` and `stats` keeps profiles separate.

**Do I need Python?** The engine does. Without Python the skill loses reliable search, validation and
spaced repetition.

**Can I share my topics?** Yes: `data/topics/<slug>/` is self-contained. Copy the folder, run
`python scripts/iv.py reindex`, and the topic appears in the registry.

---

## Contributing

Issues and pull requests are welcome. Before opening a PR:

1. `python -m unittest discover -s tests -t tests` (all green);
2. `python scripts/iv.py validate --all` (no broken sub-skill);
3. if you change the frame, bump `BASE_VERSION` and update the affected references.

If you add an example topic, make it pass the validator: incomplete examples do not get in.

For maintainers: `AGENTS.md` holds the architecture, invariants, operational recipes, decision log and
technical backlog.

## License

MIT — see [LICENSE](LICENSE). The knowledge you generate with the system stays yours.
