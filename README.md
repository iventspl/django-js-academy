# Django Quest

A local-first learning game for Python, Django, JavaScript and applied AI. It mixes multiple-choice quiz runs, open flashcards (fiszki), spaced repetition, explanations, coding challenges and a progress notebook — with a deliberately polished interface that runs the same way on macOS and Windows.

No account. No cloud. No Node.js. One SQLite file keeps your progress. See [CHANGELOG.md](CHANGELOG.md) for the 4.18 lesson and code-library expansion, the 4.17 home cleanup, the 4.16 project library and code library, the 4.15 applied deep dives, the 4.14 examples and cheat sheet, the 4.13 Python module, the 4.12 practice update, the 4.11 launch, and the earlier search and adaptive-practice releases.

## What is inside

- **360 quiz questions** across 24 learning paths and 3 levels: beginner, intermediate, advanced.
- **168 open flashcards** — question on the front, full answer on the back, optional code and hints.
- **34 real-world cheatsheets** covering permissions, uploads, private storage, email, webhooks, N+1 queries, search, migrations, deployment, LLM gateways, RAG, evals, prompt injection, ADRs, HTMX, typing, and tooling.
- **6 application blueprints** for SaaS, marketplace, booking, CMS, support desk, and mobile API products — with data models, starter code, build order, and production traps.
- **8 Architecture Studio labs** for AI document assistants, tool-using agents, multi-tenant SaaS, webhook platforms, marketplace ledgers, real-time fan-out, analytics pipelines, and legacy modernization.
- **JS Akademia** — a Polish-language JavaScript → TypeScript → React → React Native path with 21 modules, 68 lessons, 144 quiz questions, 132 flashcards, 13 live iframe demos, 31 coding challenges, a live playground, 13 ready-made components, 36 curiosities, a 50-term glossary, 30 interview questions, and XP/streaks.
- **AI Academy** — a 12-month applied AI engineering path with 8 modules, 42 lessons, 48 quiz questions, 40 concept cards, 55 glossary terms, 12 real projects and a career map.
- **Release radar** with current Django versions, LTS windows, CVE summaries, and source links to the official release notes.
- **Spaced repetition** for every card with four recall ratings: Again, Hard, Good, Easy.
- **Explanations for every quiz answer**, often with a code sample, so a wrong answer still teaches something.
- **Learning-friendly scoring:** +10 XP for a correct answer, +2 XP for a useful miss, completion bonuses for strong runs.
- **Progress notebook:** accuracy, mastery per topic, XP levels, daily streak, 28-day activity heatmap, quiz history, and achievements.
- **Global search** at `/search/` (and in the Django sidebar) across questions, flashcards, recipes, blueprints, architecture labs, and release notes.
- **Adaptive practice:** retry only the questions missed in a run, or launch a weak-spot run built from questions you have answered but never answered correctly.
- **Keyboard-friendly study:** `1`–`4` to choose or rate, `Enter` to submit, `Space` to flip a card.
- **Responsive layout** with reduced-motion support and no external fonts, CDNs, or telemetry.

## Quick start

### Requirements

- **Python 3.10 or newer** (3.12+ recommended; Python 3.12+ installs Django 6.1.x, Python 3.10–3.11 installs Django 5.2 LTS).
- Internet access on the first run, so the launcher can install Django into a private `.venv`.
- macOS, Windows 10/11, or Linux.

### Windows

Double-click `start_windows.bat`, or open PowerShell in this folder:

```powershell
python start.py
```

If `python` is not on your PATH, try:

```powershell
py -3 start.py
```

### macOS

Double-click `start_macos.command`, or from Terminal:

```bash
python3 start.py
```

If macOS refuses to run the `.command` file, make it executable once:

```bash
chmod +x start_macos.command
```

### Linux

```bash
python3 start.py
```

`start.py` creates `.venv`, installs Django on first run, applies migrations, seeds the content, chooses a free local port, opens your browser, and starts the server. Normally you will land on **http://127.0.0.1:8000/**. If port 8000 is busy, the launcher quietly picks the next free one and prints the URL.

Stop the server with `Ctrl+C`. Progress is written to disk as you go.

### Useful launcher options

```bash
python start.py --setup-only      # install + migrate + seed, no server
python start.py --update          # upgrade Django/requirements, then start
python start.py --no-browser      # do not open a browser window
python start.py --port 8765       # prefer a specific port
python start.py --host 0.0.0.0    # expose on the local network (set DJANGO_ALLOWED_HOSTS too)
```

## Content map

| Path | Questions | Flashcards | Focus |
| --- | ---: | ---: | --- |
| Python Core | 15 | 7 | Types, mutability, collections, slicing, truthiness |
| Functions & Iteration | 15 | 7 | Scope, closures, decorators, generators, context managers |
| OOP & the Data Model | 15 | 7 | Inheritance, MRO, dunders, descriptors, metaclasses |
| Django Fundamentals | 15 | 7 | MVT, routing, middleware, request lifecycle, WSGI/ASGI |
| Models & the ORM | 15 | 7 | QuerySets, joins, migrations, transactions, validation |
| Views, Forms & Templates | 15 | 7 | Validation, CBVs, escaping, formsets, template inheritance |
| Auth, Security & Testing | 15 | 7 | Permissions, CSRF, XSS, SQL injection, test isolation |
| Performance, Async & Deployment | 15 | 7 | Caching, async boundaries, indexes, deployment checks |
| APIs & Django REST Framework | 15 | 7 | Serializers, viewsets, permissions, pagination, versioning |
| Files, Email & Storage | 15 | 7 | Uploads, object storage, private downloads, deliverability |
| Admin & Internal Tools | 15 | 7 | Changelists, actions, staff security, N+1 admin pages |
| Search & PostgreSQL | 15 | 7 | Full-text, trigram, GIN indexes, query plans, pagination |
| Tasks, Queues & Realtime | 15 | 7 | Django Tasks, Celery, retries, outbox, WebSockets |
| Architecture & Multi-Tenant SaaS | 15 | 7 | Boundaries, tenancy, billing, audits, retention, quotas |
| Modern Django & Release Radar | 15 | 7 | 5.2/6.0/6.1 features, CVEs, deprecations, upgrade strategy |
| Software Architecture & Boundaries | 15 | 7 | Coupling, cohesion, ports/adapters, ADRs, fitness functions |
| Distributed Systems & Reliability | 15 | 7 | Timeouts, retries, idempotency, outbox, sagas, SLOs |
| Data & Domain Modeling | 15 | 7 | Invariants, aggregates, history, ledgers, schema evolution |
| AI Integration Architecture | 15 | 7 | RAG, embeddings, tools, evals, prompt injection, cost |
| AI-Assisted Engineering | 15 | 7 | Specs, context, verification, review, agents, security |
| Platform Engineering & Operations | 15 | 7 | CI/CD, IaC, canaries, observability, incidents, cost |
| Security Architecture & Threat Modeling | 15 | 7 | STRIDE, zero trust, supply chain, AI-specific threats |
| HTMX & Server-Driven UI | 15 | 7 | Hypermedia, partial swaps, CSRF, OOB updates, history, races |
| Python Typing, Packaging & Tooling | 15 | 7 | Type hints, mypy, django-stubs, Ruff, pytest, lockfiles |

Every path has **5 beginner, 5 intermediate, and 5 advanced questions**, so you can start easy and still find sharp edges later.

## The field guide

The **Field guide** in the sidebar is the “real work” companion to the quizzes:

- **Cheatsheets** — 34 copyable patterns for object permissions, login middleware, safe uploads, private object storage, transactional email, signed webhooks, jobs after commit, outbox delivery, N+1 audits, stable pagination, Postgres full-text search, production settings, schema changes, permission tests, scoped DRF querysets, streamed exports, health checks, LLM gateways, RAG citations, evals, prompt-injection defence, ADRs, architecture fitness tests, HTMX partials/CSRF/OOB errors, django-stubs, and Ruff/pre-commit.
- **Application blueprints** — six whole-product studies:
  - SaaS subscription workspace
  - Two-sided marketplace
  - Booking and scheduling system
  - Editorial CMS
  - Customer support desk
  - Mobile app API backend
- **Release radar** — a source-linked snapshot of Django support lines, recent patch releases, CVEs, and the practical action for each.

Each blueprint includes the problem, screens, suggested app boundaries, model sketch, critical-path starter code, implementation order, production traps, and related recipes.

### Release snapshot — reviewed 29 October 2026

| Series | Latest patch | Status | Support window |
| --- | --- | --- | --- |
| **6.1** | 6.1.2 | Current stable | Mainstream through Apr 2027; extended through Dec 2027 |
| **6.0** | 6.0.9 | Extended | Mainstream ended Aug 2026; extended through Apr 2027 |
| **5.2 LTS** | 5.2.18 | LTS | Mainstream ended Dec 2025; extended through Apr 2028 |
| **4.2** | 4.2.30 | Unsupported | Extended support ended 7 Apr 2026 |

The October 2026 patch set (**6.1.2 / 6.0.9 / 5.2.18**) addressed four CVEs and a GeoDjango data-loss issue:

- `CVE-2026-77050` — low-severity denial of service via very long, distinct language codes.
- `CVE-2026-84429` — moderate denial of service in HTTP header parsing, reachable through content negotiation.
- `CVE-2026-87890` — moderate GeoDjango request-forgery/SSRF issue with spatial lookup byte values.
- `CVE-2026-87975` — moderate privilege abuse in model formsets with editable primary keys.

Patch releases are intended to be drop-in compatible within a series. Read the notes, pin exact versions, test, and deploy. The in-app radar is a curated snapshot, not a live vulnerability feed — always confirm against the [official download page](https://www.djangoproject.com/download/), the [Django security archive](https://docs.djangoproject.com/en/dev/internals/security/), and the relevant release notes ([6.1.2](https://docs.djangoproject.com/en/6.1/releases/6.1.2/), [5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/)).

This project itself is tested against **Django 6.1.2** and targets `Django>=5.2,<6.2`.

## Architecture Studio — the AI-era core

The **Architecture** section is built around a simple premise: when code generation becomes cheap, the scarce skills are problem framing, domain modeling, boundary design, data contracts, failure design, verification, and accountability.

Eight design labs start with a scenario, scale, requirements, and constraints — then provide a reference architecture, data flow, model sketch, decision log, starter code, failure modes, trade-offs, and an evolution path:

- **AI document assistant with citations** — tenant-filtered RAG, source spans, evals, provider failure.
- **Tool-using operations agent** — scoped tools, approvals, prompt injection, audit.
- **Multi-tenant SaaS at scale** — shared schema, quotas, reporting isolation, segmentation.
- **High-volume webhook/event platform** — signatures, deduplication, replay, backpressure.
- **Marketplace checkout and ledger** — idempotency, stock, refunds, reconciliation.
- **Real-time notifications** — WebSockets, fan-out, catch-up, at-least-once delivery.
- **Analytics and reporting pipeline** — OLTP protection, idempotent ETL, metric versioning.
- **Legacy monolith modernization** — strangler routing, dual-write risk, parity, retirement.

The studio also has a **durable skills map**, a “what AI changes / what it does not change” section, and a four-step method for using each lab: read the brief, sketch the shape, compare decisions, write an ADR.

The architecture paths in the quiz cover the theory behind those labs: boundaries, distributed reliability, domain modeling, AI integration, AI-assisted engineering, platform operations, and security architecture.

## JS Akademia — Polish JavaScript → React Native platform

Use the **Django / JavaScript / AI** switch in the sidebar to enter **JS Akademia**, a fully Polish-language learning path:

| Module | Lessons | Quiz | Fiszki | Projekt |
| --- | ---: | ---: | ---: | --- |
| Fundamenty JavaScript | 7 | 13 | 11 | Kalkulator budżetu |
| Nowoczesny JavaScript | 3 | 6 | 5 | Klient API z błędami |
| DOM, formularze i przeglądarka | 3 | 6 | 5 | Lista zadań w JS |
| TypeScript w praktyce | 3 | 6 | 5 | Typowany koszyk |
| React — podstawy | 3 | 6 | 5 | Lista zadań React |
| React — hooki i architektura | 3 | 6 | 5 | Mini sklep |
| React Native | 3 | 6 | 5 | Mobilna lista zadań |
| Testy, jakość i publikacja | 3 | 6 | 5 | Wydanie aplikacji |
| Wzorce i architektura frontendu | 3 | 6 | 5 | Kreator zamówienia |
| Struktury danych i algorytmy | 3 | 6 | 5 | Analizator wydatków |
| Node.js i narzędzia | 3 | 6 | 5 | CLI do raportu |
| React w praktyce | 3 | 6 | 5 | Panel produktów |
| React Native w produkcji | 3 | 6 | 5 | Notes offline-first |
| JavaScript + AI | 3 | 6 | 5 | Asystent z cytowaniami |
| Bezpieczeństwo i wydajność frontendu | 3 | 6 | 5 | Audyt aplikacji |
| Mistrzostwo JS: powtórka i rozmowa | 3 | 15 | 25 | Obrona decyzji projektowej |
| AI a praca programisty | 3 | 6 | 5 | Audyt kodu wygenerowanego przez AI |
| MVC w JavaScript | 4 | 8 | 6 | Lista produktów MVC |
| Wzorce projektowe w JS | 3 | 6 | 5 | Mini store z obserwatorem |
| Web APIs w praktyce | 3 | 6 | 5 | Cache offline |
| Debugging i DevTools | 3 | 6 | 5 | Polowanie na błąd |

The platform includes:

- **21 modules / 68 lessons** with Polish explanations, code and practical warnings.
- **144 quiz questions** with detailed explanations.
- **132 open flashcards** with spaced repetition.
- **13 live iframe demos** — real interactive HTML/JS examples embedded directly in lessons.
- **31 coding challenges** with an in-browser editor and automatic tests.
- **13 ready-made components** with live preview, full HTML/CSS/JS and copyable code.
- **36 curiosities**, a **50-term glossary**, and **30 interview questions with model answers**.
- **XP, levels and daily streaks** based on real completed work.
- **21 module projects** with a concrete build checklist.
- Full Polish interface, `lang="pl"`, and a separate yellow JS visual identity.

### Practice and knowledge

The **Wyzwania** tab contains 31 tasks across three levels. Each challenge opens a sandboxed code editor with a `solve` contract, automatic tests, hints and a solution. The editor runs entirely in the browser; no code is sent to the server. Passing tests reveals a completion form and awards XP.

The **Piaskownica** page at `/js/piaskownica/` is a free-form live iframe: write any JavaScript, run it, and see `console.log` and errors. It is for experimentation; the challenge lab provides automated tests and XP.

The **Komponenty** library at `/js/komponenty/` contains 13 real-world UI fragments with live previews and full HTML, CSS and JavaScript: product filter/cart, form validation, debounced search, tabs, dialog, toast queue, sortable table, image preview, countdown, star rating, canvas chart, drag & drop and a full MVC product browser. Each component explains which functions it uses and can be copied into a project.

### MVC in JavaScript

`/js/mvc/` is a long-form guide and `/js/mvc-w-js/` is the matching four-lesson module. It covers:

- model / view / controller responsibilities and when MVC is overkill,
- one `viewState` object with `currentView`, `currentSort`, `currentQuery`, `currentCategory`, `currentPage` and `pageSize`,
- why `currentView` is presentation-only and must not affect filtering,
- `currentSort` as `{ key, direction }` instead of an ambiguous string,
- pure `filterProducts`, `sortProducts`, `paginate` and `selectProducts` selectors,
- immutable `updateViewState(patch)`, resets on query/category/sort, pagination clamping,
- URL synchronisation, async race conditions, empty states and testable reducers,
- a live MVC product browser component.

The key rule: the controller changes state; selectors compute data; the view renders. Do not pass six loose scalars into every function — pass one state object, and let each selector read only the fields it needs.

### Search, practice and milestones

- **Global search** at `/js/szukaj/` (and in the JS sidebar) searches modules, lessons, components, challenges, glossary terms, curiosities and interview questions.
- **Design patterns** module: observer/pub-sub, factory, strategy and command, with a live store demo.
- **Web APIs** module: `fetch`, abort/timeout, localStorage vs IndexedDB, Web Workers, streams and notifications.
- **Debugging** module: breakpoints, call stack, Network/Performance tools, source maps, production errors and regression tests.
- **Achievements** on the progress page: first lesson, ten lessons, first quiz, 80% quiz, 25 cards, first challenge, five challenges and a seven-day streak.

The suite includes tests for search results, empty search, achievements and the new modules.

The **Wiedza** tab contains:

- **Ciekawostki** — 36 short, factual notes about the language, browser, React, security and AI.
- **Słownik** — 50 terms with a Polish definition and a practical snippet.
- **Wywiad** — 30 interview questions with model answers and follow-up questions.

### AI and careers

The **AI a praca programisty** module and the companion page at `/js/wiedza/ai-praca/` answer the question “why learn JS/React if AI writes code faster?” with sources rather than slogans:

- Stack Overflow 2025: **80%** of developers use AI, **29%** trust its accuracy, **66%** spend more time fixing “almost right” code.
- DORA 2025: **90%** of technology professionals use AI; **30%** report little or no trust; higher adoption is associated with both higher throughput and higher instability.
- METR 2025: experienced open-source developers took **19% longer** with AI; later data suggests possible speedup but has selection limitations.
- Veracode 2025: **45%** of AI-generated samples failed security tests across 80 tasks.
- Stack Overflow 2025: **68.8%** of professional developers use JavaScript; **48.8%** use TypeScript.
- npm, 21–27 October 2026: React had **205,386,791** weekly downloads.
- U.S. BLS projects software developer employment **+10.2%** from 2025 to 2035.

The page includes an explicit “what these numbers do not prove” section: BLS is a projection, surveys are self-reports, npm downloads are not jobs, METR has selection effects, and Veracode tested specific tasks. Every number links to its source and a reviewed date.

The home page shows a **fact of the day**, a **challenge of the day**, and the learner's current level, XP and streak.

XP is based on real work: 10 XP per completed lesson, 2 XP per reviewed card, 10 XP per completed module quiz plus a score bonus, and the challenge's XP value after marking it complete. Levels run from **Nowicjusz** to **Mistrz JS**. The streak counts consecutive local days with a lesson, quiz, flashcard review or challenge completion.

The live demos are self-contained HTML documents shown in a sandboxed iframe (`sandbox="allow-scripts"`, no same-origin access). They run real JavaScript in the lesson page: a cart with `reduce`, async loading, form validation, a state machine, event-loop ordering, streaming AI simulation, XSS rendering comparison, and an offline queue.

The path deliberately teaches JavaScript and TypeScript before React, then React before React Native. You can switch platforms at any time; progress for each is independent.

## AI Academy — applied AI engineer path

Use the **AI** switch in the sidebar to enter **AI Academy**, an English-language 12-month route from beginner to job-ready applied AI engineering.

| Stage | Module | Lessons | Project |
| --- | --- | ---: | --- |
| Foundation | Python for AI | 7 | Notes-to-Dataset Pipeline |
| Foundation | AI Foundations & Python | 5 | Study Buddy CLI |
| Foundation | Data, Math & Evaluation | 5 | Churn Dataset Audit |
| Core ML | Classical Machine Learning | 5 | Default-Risk Predictor |
| Core ML | Deep Learning & NLP | 5 | Support Ticket Classifier |
| LLM Engineering | LLM Engineering & RAG | 5 | Docs Answer Engine |
| LLM Engineering | Agents, Tools & Evaluation | 5 | Research Copilot |
| Production & Career | Production, MLOps & Career | 5 | AI Product Capstone |

Every module now has a practical **applied deep-dive lesson** and an extra concept lesson in addition to its core material, and **Python for AI** has seven. Every module has **six quiz questions**, **five concept cards** and a substantial project brief. The path totals **42 lessons, 48 questions, 40 cards and 12 projects**.

### What makes it useful

- **The 12-month calendar** — 8–12 focused hours per week, with explicit monthly outcomes and a capstone in month 11, followed by portfolio and interview work in month 12.
- **Projects are the curriculum** — Notes-to-Dataset Pipeline, Study Buddy CLI, Churn Audit, Default-Risk Predictor, Support Ticket Classifier, Docs Answer Engine, Research Copilot, Support Email Triage, Meeting Action Extractor, Safe Text-to-SQL Analyst, PII Redaction and the AI Product Capstone.
- **Job-readiness score** — a blend of lessons completed, quiz average, concept-card recall and shipped projects. It is a compass, not a certificate.
- **Three role maps** — LLM / GenAI Engineer, Machine Learning Engineer, and AI Automation / Solutions Engineer, with the modules and portfolio pieces that fit each.
- **Evaluation-first** — every project asks for a baseline, a metric, failure analysis and a model or system card. The interview page drills the questions behind the questions.
- **Concept cards** — spaced-repetition prompts for definitions, trade-offs and failure modes, separate from multiple-choice recognition.
- **Lesson takeaways and “Do this now” exercises** — every lesson ends with three durable ideas and one small exercise with a success criterion, so reading turns into practice.
- **Searchable 55-term glossary and course search** — find a term, lesson, project or module by name, definition or concept; the glossary links each term back to the module where it matters.
- **AI code library** at `/ai/code-library/` — 20 real-world patterns for provider calls, structured output, retrieval, evaluation, tools, privacy, streaming, cost logging, embeddings, drift, idempotency, model cards and evaluation reports.
- **Python for AI cheat sheet** at `/ai/python-for-ai/cheatsheet/` — records, JSON, pandas, NumPy, API and pytest patterns in one copyable page.
- **Hidden hints and reference solutions** — every project page has collapsible hints and a ready reference implementation, hidden by default so you can attempt the work first.
- **Downloadable project test packs** — every project page serves a zip with `starter.py`, a pytest acceptance suite, `requirements.txt` and a README, so learners can run the contract in their own environment.
- **No external services required** — the curriculum, projects and progress tracker run locally in the same SQLite database.

AI Academy lives at `/ai/`; the seed command is `python manage.py seed_ai --if-changed`.

## How the learning loop works

### Quiz runs

1. Choose a topic (or all topics), a difficulty (or mixed), and a length of 5–20 questions.
2. Answers are locked in one at a time. You get immediate feedback and the reasoning behind the correct answer.
3. Correct answers earn 10 XP; misses earn 2 XP. Runs of 80%+ earn a +20 bonus; a perfect run earns +25 XP.
4. Your attempt is saved. You can leave and resume; completed runs appear in the notebook with a full answer review.

### Fiszki

1. Pick a deck or review every due card across all decks.
2. Read the open question aloud. Try to answer before turning the card over.
3. Flip it, compare with the back, then rate the recall:
   - **Again** → tomorrow, reset the interval.
   - **Hard** → roughly 2 days and up, easing the interval.
   - **Good** → 3 days and growing with the ease factor.
   - **Easy** → 7 days and up, with a larger multiplier.
4. Rated cards leave today's queue and return when they are due. New cards count as due until first rated.

The scheduler is intentionally small and transparent, inspired by SM-2. It is not a medical-grade memory model; it is a useful daily habit.

## Project structure

```text
.
├── start.py                     # cross-platform launcher
├── start_windows.bat            # double-click entry point for Windows
├── start_macos.command          # double-click entry point for macOS
├── requirements.txt
├── manage.py
├── django_quest/
│   ├── settings.py              # local-first settings + env overrides
│   └── urls.py
├── dojo/
│   ├── models.py                # content, attempts, SRS, architecture cases, events
│   ├── services.py              # quiz creation, scoring, scheduling, stats
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   ├── content.py               # JSON loading + validation + fingerprint
│   ├── field_guide.py           # recipes, blueprints, cases, releases
│   ├── content/*.json           # editable learning content (22 bundles)
│   ├── content/field_guide/     # cheatsheets, blueprints, cases, releases
│   ├── management/commands/
│   │   └── seed_content.py
│   ├── templatetags/
│   ├── templates/dojo/
│   └── static/dojo/
├── js_academy/                  # polska akademia JavaScript
│   ├── models.py                # moduły, lekcje, quizy, fiszki, postęp
│   ├── services.py              # postęp i harmonogram fiszek
│   ├── content.py               # walidacja i seed treści
│   ├── runner.py                # edytor wyzwań w sandbox iframe
│   ├── content/*.json           # 21 modułów: JS → TS → React → RN
│   ├── content/demos.json       # 12 dem iframe
│   ├── content/knowledge.json   # ciekawostki, słownik, wywiad
│   ├── content/challenges.json  # 31 wyzwań z testami
│   ├── content/components.json  # 13 komponentów HTML/CSS/JS
│   ├── templates/js_academy/
│   └── static/js_academy/
├── ai_academy/                  # 12-month applied AI path
│   ├── models.py                # modules, lessons, attempts, cards, projects
│   ├── services.py              # progress, readiness, scheduling, stats
│   ├── content.py               # validation and seeding
│   ├── career.py                # role maps, 12-month plan, interview topics
│   ├── content/*.json           # 8 modules, 42 lessons
│   ├── content/projects.json    # 12 real project briefs
│   ├── content/glossary.json    # 55 plain-language AI terms
│   ├── project_tests/           # downloadable pytest starter packs
│   ├── templates/ai_academy/
│   └── static/ai_academy/
└── templates/                   # 404 / 500 pages
```

## Manual setup (optional)

If you prefer to manage the environment yourself:

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate          # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_content
python manage.py seed_js
python manage.py seed_ai
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

> If you copy the project between computers with different operating systems, delete `.venv` first. Virtual environments are not portable across macOS and Windows.

## Editing the content

All learning content lives in `dojo/content/*.json`. One file is one topic bundle:

```json
{
  "topic": {
    "slug": "python-core",
    "name": "Python Core",
    "tagline": "...",
    "description": "...",
    "glyph": "py",
    "accent": "#F5C451"
  },
  "questions": [
    {
      "key": "python-core-b1",
      "difficulty": "beginner",
      "prompt": "Which group contains only immutable objects?",
      "code": "",
      "choices": ["...", "...", "...", "..."],
      "answer": 1,
      "explanation": "...",
      "explanation_code": ""
    }
  ],
  "flashcards": [
    {
      "key": "python-core-f1",
      "difficulty": "beginner",
      "front": "Open question",
      "back": "Answer",
      "front_code": "",
      "back_code": "",
      "hint": ""
    }
  ]
}
```

Rules enforced by the validator:

- exactly 4 unique choices per question;
- `answer` is a zero-based index into `choices`;
- every question has a non-empty prompt and explanation;
- every card has a non-empty front and back;
- keys are unique across all bundles.

Commands:

```bash
python manage.py seed_content --check      # validate all JSON without writing
python manage.py seed_content              # validate + upsert everything
python manage.py seed_content --if-changed # skip when the content fingerprint is unchanged
```

`seed_content` is idempotent: it updates existing rows by key and keeps choice IDs stable where possible. The command stores a fingerprint of all JSON files, and the launcher uses `--if-changed` so a normal start does not overwrite admin edits. When you edit content, the fingerprint changes and the next seed applies your JSON updates.

### Editing the field guide

The practical content lives in `dojo/content/field_guide/`:

- `cheatsheets.json` — `cheatsheets` array. Required fields: `key`, `title`, `category`, `summary`, `when_to_use`, `code`; optional `language`, `pitfalls`, `topic`.
- `blueprints.json` — `blueprints` array. Required fields: `key`, `name`, `tagline`, `problem`, `complexity`, `stack_notes`, `screens`, `structure`, `models_code`, `starter_code`, `checklist`, `pitfalls`.
- `architecture_cases.json` — `cases` array. Required fields: `key`, `name`, `tagline`, `scenario`, `scale`, `complexity`, `requirements`, `constraints`, `stack`, `components`, `data_flow`, `decisions`, `data_model_code`, `starter_code`, `failure_modes`, `tradeoffs`, `evolution`.
- `releases.json` — `series` and `notes` arrays, plus `reviewed_on`. Release notes require `version`, `kind`, `released_on`, `headline`, `summary`, `why_it_matters`, `action`, and an HTTPS `source_url`.

The release radar is deliberately a curated snapshot. Update `releases.json` when you verify new official notes, and keep the `reviewed_on` date honest.

### Edycja treści JS Akademii

JS Akademia keeps its content in `js_academy/content/*.json` — one JSON file per module. A bundle contains `module`, `lessons`, `questions` and `flashcards`.

- Module: `slug`, `title`, `subtitle`, `description`, `level`, `glyph`, `accent`, `duration_minutes`, `outcomes`, `project_title`, `project_brief`, `project_steps`.
- Lesson: `slug`, `title`, `summary`, `body_html`, `minutes`.
- Question: `key`, `difficulty`, `prompt`, `code`, `choices` (exactly four), `answer` (index), `explanation`, `explanation_code`.
- Flashcard: `key`, `front`, `back`, `front_code`, `back_code`, `hint`.

Commands:

```bash
python manage.py seed_js --check      # walidacja treści
python manage.py seed_js              # walidacja + zapis
python manage.py seed_js --if-changed # pomiń, jeśli fingerprint jest aktualny
```

`body_html` is trusted, seed-controlled HTML rendered with `|safe`. Do not paste untrusted user content into it. The validator rejects `<script>` tags and requires at least 3 lessons, 6 questions and 5 flashcards per module.

Live demos live in `js_academy/content/demos.json`. Each demo targets a `module` + `lesson`, has a title/description, and contains a complete self-contained HTML document. Demos are rendered in an iframe with `sandbox="allow-scripts"` and no same-origin access; they cannot read the parent session or cookies. External scripts and nested iframes are rejected by the validator.

Practice and knowledge content live in:

- `js_academy/content/challenges.json` — 31 challenges. Each has `starter_code`, `solution_code`, `tests` (`name`, `args`, `expected`), `hints`, `explanation`, `xp` and an optional `module`.
- `js_academy/content/knowledge.json` — `facts`, `terms` and `interview` arrays.
- `js_academy/content/components.json` — 13 components with `html_code`, `css_code`, `js_code`, `functions`, `notes`, `category` and `difficulty`.

The challenge runner is rendered server-side and executes only inside a sandboxed iframe. It uses `new Function` in the browser, compares results with a deep-equality helper, and posts a `js-challenge-passed` message to the parent page only after all tests pass. No learner code is sent to Django.

The full test suite also executes every challenge solution against its test cases in Node and checks the generated runner for JavaScript syntax.

### Editing AI Academy content

AI Academy keeps its curriculum in `ai_academy/content/`:

- `00…07_*.json` — one bundle per module with `module`, `lessons`, `questions` and `flashcards`.
- `projects.json` — the twelve project briefs, linked to modules by slug.
- `glossary.json` — the searchable reference terms, optionally linked to a module.
- `project_tests/` — downloadable starter/test packs, one folder per project.

Module fields: `slug`, `title`, `subtitle`, `description`, `stage`, `difficulty`, `glyph`, `accent`, `duration_weeks`, `outcomes`, `skills`.
Lesson fields: `slug`, `title`, `summary`, `body_html`, `minutes`.
Question fields: `key`, `difficulty`, `prompt`, `code`, `choices` (four), `answer`, `explanation`.
Project fields: `slug`, `module`, `title`, `tagline`, `scenario`, `build`, `difficulty`, `duration_hours`, `skills`, `deliverables`, `milestones`, `rubric`, `stretch`, `portfolio_note`.

```bash
python manage.py seed_ai --check
python manage.py seed_ai
python manage.py seed_ai --if-changed
```

The validator requires at least 3 lessons, 5 questions and 4 cards per module, exactly four unique choices per question, and a known module slug for every project. `body_html` is trusted seed content; never render learner input with `|safe`.

### Optional admin

The Django admin is available at `/admin/` for inspecting or editing content and learner data:

```bash
python manage.py createsuperuser
```

## Tests

```bash
python manage.py test
```

The suite covers content validation, quiz selection and scoring, attempt scoping, flashcard scheduling, XP, streaks, resetting progress, global search, weak-spot tracking, retry-only-missed runs, field-guide search/filters, blueprint details, Architecture Studio pages/filters, release-radar content, AI Academy lessons/quizzes/cards/projects/career pages/glossary/search/code-library, JS lessons/quizzes/flashcards/challenges/playground/components/MVC/knowledge/AI-career pages/gamification, and all main pages. There are **121 tests** in total.

You can also run Django's deployment check before hosting anything:

```bash
python manage.py check --deploy
```

## Configuration

The app is configured for local use by default. Environment variables can override the essentials:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | development key | Set a real secret before hosting |
| `DJANGO_DEBUG` | `1` | Set to `0` for production-like behavior |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost,[::1],testserver` | Comma-separated hosts |
| `DJANGO_TIME_ZONE` | `Europe/Warsaw` | Timezone for streaks and due dates |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated trusted origins |

To reset your own progress without touching the content bank, use **Progress → Reset my progress** in the UI.

## Troubleshooting

**`python` opens the Microsoft Store on Windows**  
Use `py -3 start.py` or install Python from <https://www.python.org/downloads/> and tick “Add Python to PATH”.

**Port already in use**  
The launcher auto-selects the next free port. To choose one yourself: `python start.py --port 8765`.

**First-run install fails**  
Check your internet connection and proxy settings. Delete `.venv` and run `start.py` again. On a corporate network, you may need to configure pip's certificate/proxy settings.

**`start_macos.command` will not open**  
Run `chmod +x start_macos.command` once, or just use `python3 start.py`.

**I want a clean database**  
Stop the server, delete `db.sqlite3`, then run `python start.py`. The content will be seeded again and all progress will start fresh. You can also use the in-app reset button.

**The page looks different after editing CSS/JS**  
Hard-refresh the browser (`Ctrl+Shift+R` on Windows, `Cmd+Shift+R` on macOS). If `DEBUG` is off, run `python manage.py collectstatic` and serve `staticfiles/` from your web server.

## Notes on scope

This is a personal learning app, not a multi-tenant SaaS. It uses a single local learner profile, SQLite, Django's development server, and no authentication wall. That is intentional: the shortest path from “I want to practice” to a question is the product.

For real deployment, set `DEBUG=False`, a strong `DJANGO_SECRET_KEY`, correct `ALLOWED_HOSTS`, HTTPS/secure cookies, a production WSGI/ASGI server, database backups, and a static-file host. See Django's deployment checklist.

Built to be read, changed, and played with. Enjoy the reps.
