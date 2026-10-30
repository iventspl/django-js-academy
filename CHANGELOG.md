# Changelog

## 4.22 — 2026-10-30

### Mobile-first responsive repair

- Added a real mobile navigation menu instead of a squeezed horizontal nav row.
- Kept the Django / JavaScript / AI platform switch visible on small screens.
- Added a shared `mobile.css` loaded after all platform styles.
- Improved touch targets: 44px buttons and navigation rows.
- Prevented iOS input zoom with 16px form controls on small screens.
- Collapsed cards, stats, notes, components, challenges and project grids for phones.
- Added horizontal scrolling for tables and code blocks.
- Resized lesson, demo and challenge iframes to the viewport.
- Added `viewport-fit=cover` and safe-area padding for notches.
- Added mobile web-app meta tags for Home Screen launch.
- Added a test for the mobile navigation markup and stylesheet.
- Fixed a hidden JS module overflow: the lesson list and nowrap lesson subtitles could force an 800px-wide page on a 390px phone.
- Reworked AI summary bands: `ai-stat-band` stays in one compact five-column row, `ai-project-summary`/result bands stay in one four-column row, and `ai-next-band` stacks cleanly on phones.
- Added a **Copy** button in the top-right corner of every code block across Django, JavaScript and AI. It uses the Clipboard API where available and a textarea fallback for plain HTTP on the LAN.
- Fixed duplicate dev servers on port 8000, which could serve stale desktop CSS after a rebuild.

### Verification

- **135 tests pass**.
- Mobile page over LAN checked at `/`, `/js/` and `/ai/`.
- ZIP rebuilt and verified.

## 4.21 — 2026-10-30

### Cross-platform learner tools

The same learner tools are now available in Django, JavaScript and AI:

- **Notes and bookmarks**
  - Django: topic-linked notebook at `/notes/`.
  - JavaScript: per-lesson notes at `/js/notatki/`, with a save form on every lesson.
  - AI: existing lesson notes.
- **Progress export** — Markdown reports in all three platforms, available from the progress page.
- **Retry missed** — JavaScript now has “Tylko błędne” on quiz results, joining Django and AI.
- **Weak-spot practice** — JavaScript and AI now build a run from questions answered incorrectly and never correctly answered.
- **Reset progress** — JavaScript and AI now offer a confirmed reset, joining Django.
- **Navigation and tests** — notes links, tool bands, reset confirmation and parity tests across all three.

### Verification

- **134 tests pass**.
- Django, JavaScript and AI tests cover notes, export, retry, weak spots and reset.
- The LAN server was restarted with the new code.

## 4.20 — 2026-10-30

### Local Wi-Fi access

- Added `python start.py --lan`: binds to `0.0.0.0` and detects the host's private IPv4 address.
- Automatically configures `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` for the LAN address and hostname.
- Prints both the local URL and the LAN URL, e.g. `http://192.168.1.23:8000/`.
- Added a clear warning that the app has no login and should only be exposed on a trusted private network.
- Added `allow_lan_windows.bat` to create a local-subnet-only inbound firewall rule (run as administrator), plus `start_lan_windows.bat`.
- Documented Windows/macOS firewall requirements and the difference between local and LAN mode.

## 4.19 — 2026-10-30

### AI Academy learner tools

- Added **private lesson notes and bookmarks**, stored in the local SQLite database and available from a new Notes page and the AI sidebar.
- Added **retry missed** on AI quiz results: rebuild a run from only the questions answered incorrectly.
- Added a downloadable **Markdown progress report** with readiness, module completion, quiz scores, cards and shipped projects — useful for a job-search log.
- Added note, retry and export tests; the suite now has **127 tests**.

## 4.18 — 2026-10-29

### AI Academy: more lessons and a 20-example code library

- Added eight more substantial lessons, one to every module:
  - reproducible Python project setup
  - reading AI research and documentation
  - probability, uncertainty and calibration
  - imbalanced data and cost-sensitive decisions
  - embeddings and semantic search
  - structured extraction with schemas
  - agent memory, state and planning
  - model cards, audits and incidents
- Expanded the **AI code library from 8 to 20 examples**, adding batch embedding caches, cosine search, prompt-injection tests, model-card generation, drift checks, idempotent writes, provider injection, LLM judging, cost estimation, tracing, dead-letter queues and evaluation reports.
- AI Academy now has **42 lessons and a 20-example code library**; **121 tests pass**.

## 4.17 — 2026-10-29

### AI Academy home cleanup

- Simplified the hero to two actions: continue learning and explore projects.
- Removed the redundant career CTA and the closing CTA band.
- Shortened the hero copy to one clear promise.
- Kept the next lesson, path stages, project highlights and role destinations.
- Verified the cleaned home in Chrome; **121 tests pass**.

## 4.16 — 2026-10-29

### More real-world AI projects and a code library

- Added four projects with briefs, hints, reference solutions, test packs and project pages:
  - Support Email Triage
  - Meeting Notes → Action Items
  - Safe Text-to-SQL Analyst
  - PII Redaction Pipeline
- Added a real-world **AI code library** at `/ai/code-library/` covering safe provider calls, structured output, retrieval with citations, evaluation harnesses, approval-aware tools, PII redaction, streaming endpoints and cost/latency logging.
- AI Academy now has **12 projects**; the suite has **121 tests**.

## 4.15 — 2026-10-29

### AI Academy: applied deep dives and hidden solutions

- Added an **applied deep-dive lesson to every AI module**: Study Buddy walkthrough, churn audit, served tabular model, text classifier, RAG engine, tool-using agent, shipped API and Python debugging/profiling.
- Added **progressive hints** and a **reference solution** to every project. Both are collapsed by default on the project page, with a reminder to attempt the work first.
- The reference solutions cover the downloadable acceptance-test contracts and explicitly note that the full project still needs README, evaluation and failure analysis.
- AI Academy now has **8 modules, 34 lessons, 48 questions, 40 cards, 8 projects and 55 glossary terms**.
- The suite still has **120 tests**.

## 4.14 — 2026-10-29

### AI Academy: more worked examples and a Python cheat sheet

- Expanded all four core Python for AI lessons with worked examples and common-mistake sections:
  - records from nested API responses, sets for deduplication and JSONL;
  - typed settings, pytest fakes and project structure;
  - a five-minute pandas audit, safe filtering/merging and split checks;
  - a safe provider client, async fan-out and failure-path tests.
- Added a fifth lesson, **“Put it together: the notes pipeline”**, with a complete load → clean → split → artifact pipeline and tests.
- Added a **Python for AI cheat sheet** page at `/ai/python-for-ai/cheatsheet/` with copyable records, JSON, pandas, NumPy, API and pytest patterns.
- Added the cheat-sheet link to the Python for AI module.
- Total AI content is now **8 modules, 26 lessons, 48 questions, 40 cards, 8 projects and 55 glossary terms**.
- The suite now has **120 tests**.

## 4.13 — 2026-10-29

### AI Academy: Python for AI prerequisite module

- Added a four-lesson **Python for AI** module at the start of the path:
  - Python data structures, comprehensions, JSON and generators.
  - Typed functions, dataclasses, project structure, environments and tests.
  - NumPy vectorisation, pandas cleaning, summaries and leakage-safe splits.
  - API calls with secrets, timeouts, bounded retries, async boundaries and pytest mocks.
- Added a real **Notes-to-Dataset Pipeline** project and a matching downloadable test pack.
- Updated the 12-month calendar, role maps and all course counts: **8 modules, 25 lessons, 48 questions, 40 cards and 8 projects**.
- Added tests for the new module and project pack; the suite now has **119 tests**.

## 4.12 — 2026-10-29

### AI Academy: active practice and a reference layer

- Added **key takeaways** and a **“Do this now” exercise** to all 21 AI lessons, each with a concrete success criterion.
- Added a searchable **55-term AI glossary** with categories, examples and links back to the relevant module.
- Added **AI Academy search** across modules, lessons, projects and glossary terms, with word-start matching so “RAG” does not match “average”.
- Added an AI sidebar search field plus Glossary and Search navigation.
- Added glossary/search tests and documentation; the suite now has **118 tests**.

## 4.11 — 2026-10-29

### AI Academy: a 12-month applied AI engineering path

- Added a third learning platform, **AI Academy**, at `/ai/`.
- Added seven modules and 21 lessons:
  - AI Foundations & Python
  - Data, Math & Evaluation
  - Classical Machine Learning
  - Deep Learning & NLP
  - LLM Engineering & RAG
  - Agents, Tools & Evaluation
  - Production, MLOps & Career
- Added 42 quiz questions and 35 concept cards with spaced repetition.
- Added seven real project briefs: Study Buddy CLI, Churn Dataset Audit, Default-Risk Predictor, Support Ticket Classifier, Docs Answer Engine, Research Copilot and the AI Product Capstone.
- Added a 12-month calendar, job-readiness score, three role maps, portfolio checklist and interview map.
- Integrated a third platform switch, AI sidebar navigation, the AI home bridge and the `seed_ai` startup command.
- Added AI Academy tests and documentation.
- Added a downloadable **test pack** for every AI project: starter module, pytest acceptance suite, requirements and README.
- The suite now has **114 tests**.

## 4.10 — 2026-10-29

### Larger, more readable typography

- Raised the project root from 16px to an 18px scale and set the body to `1rem`, so the common 12–13px copy now renders around 14–16px.
- Set a readable floor for code blocks and inline code (about 14.4px), including JS Akademia lesson code, glossary snippets, and flashcard code.
- Adjusted the home date heading so the larger scale does not wrap it.
- Verified desktop and 390px mobile layouts in Chrome; no horizontal page overflow.

## 4.9 — 2026-10-29

### HTMX, typing, search and adaptive practice

- Added two Django Quest paths:
  - **HTMX & Server-Driven UI** — HTML fragments, `hx-target`/`hx-swap`, CSRF, 422 validation, out-of-band swaps, `HX-Trigger`, history, request races, and when not to use HTMX.
  - **Python Typing, Packaging & Tooling** — runtime vs static typing, unions and `Protocol`, `django-stubs` + mypy, Ruff, pytest-django, `TypeVar`/`ParamSpec`, `TYPE_CHECKING`, and reproducible lockfiles.
- Added 30 questions, 14 flashcards and six field-guide recipes: HTMX partials, CSRF headers, OOB feedback, form errors, django-stubs, and Ruff/pre-commit.
- Added **global search** at `/search/` and in the Django sidebar across topics, questions, flashcards, recipes, blueprints, architecture labs, and release notes.
- Added **retry missed**: after a run, rebuild a quiz from only the questions answered incorrectly.
- Added **weak-spot practice**: questions answered but never answered correctly are collected into a focused run from the progress page or home.
- Fixed stale “all eight paths” and JS lesson-count copy.
- Django Quest now has **24 paths, 360 questions, 168 flashcards, 34 recipes, 6 blueprints, 8 architecture labs and 6 release notes**.

### Verification

- **98 tests pass**, including search coverage, weak-spot tracking, retry-only-missed runs, and the expanded content counts.
- New pages and the search layout were rendered in Chrome at desktop size.

## 4.8 — 2026-10-29

### Function fundamentals: arguments and return values

- Expanded **Fundamenty JavaScript** from 3 to 7 lessons:
  - **Parametry i argumenty** — positional binding, missing/extra arguments, defaults, rest, destructuring, primitives vs references, and who supplies callback arguments.
  - **Return: wartość, którą funkcja oddaje** — `undefined` without `return`, early returns, returning objects, implicit arrow returns, query vs command, and the missing-`return` bug in `controller.js`.
  - **Callbacki i funkcje wyższego rzędu** — callback contracts, array-method arguments, `map(parseInt)`, event handlers and returning functions.
  - **Funkcje czyste i kontroler** — pure selectors, side-effecting views, explicit arguments instead of globals, and the `event → update → selectProducts → render` flow.
- Added 7 quiz questions, 6 flashcards and a live **“Argumenty wchodzą, return wychodzi”** demo with a simulated missing `return`.
- Fixed the MVC examples to declare view state with `let` before reassigning it.
- JS Akademia now has **21 modules, 68 lessons, 144 questions, 132 flashcards, 13 demos, 31 challenges and 13 components**.

### Verification

- **83 tests pass**, including content counts, quiz length and demo sandbox checks.
- The new demo script is syntax-checked with Node and rendered in Chrome.

## 4.7 — 2026-10-29

### More modules, global search and achievements

- Added three modules:
  - **Wzorce projektowe w JS** — observer/pub-sub, factory, strategy and command, with a live store demo.
  - **Web APIs w praktyce** — fetch/abort/timeout, localStorage vs IndexedDB, Web Workers, streams and notifications.
  - **Debugging i DevTools** — breakpoints, call stack, Network/Performance, source maps and production errors.
- Added **global search** at `/js/szukaj/` and in the JS sidebar across modules, lessons, components, challenges, glossary, facts and interview questions.
- Added **8 achievements** to the progress page: first lesson, ten lessons, first quiz, 80% quiz, 25 cards, first challenge, five challenges and a seven-day streak.
- Added the 12th live demo: a store with two observer views and an unsubscribe control.
- JS Akademia now has **21 modules, 64 lessons, 137 questions, 126 flashcards, 12 demos, 31 challenges and 13 components**.

### Verification

- **83 tests pass**.
- Search, empty search, achievements and new module counts are covered by tests.
- Component and demo scripts are syntax-checked with Node.

## 4.6 — 2026-10-29

### MVC in JavaScript

- Added the **MVC w JavaScript** module: 4 lessons, 8 questions and 6 flashcards.
- Added a long-form `/js/mvc/` guide covering:
  - model/view/controller responsibilities and when MVC is overkill,
  - `currentView`, `currentSort`, `currentQuery`, `currentCategory`, `currentPage` and `pageSize` in one view-state object,
  - why `currentView` is presentation-only and must not affect filtering,
  - `currentSort` as `{ key, direction }`,
  - pure `filterProducts`, `sortProducts`, `paginate` and `selectProducts` functions,
  - immutable updates, page resets, pagination clamping, URL sync, async races and testable reducers.
- Added a live MVC demo and the **Lista produktów MVC** component with search, category, sort, grid/list and pagination.
- Added the **MVC** navigation entry and module/component links.
- Added a 31st challenge: **Selektor produktów MVC** (filter + sort + paginate).
- JS Akademia now has **18 modules, 55 lessons, 119 questions, 111 flashcards, 11 demos, 31 challenges and 13 components**.

### Verification

- **80 tests pass**.
- MVC guide, module, demo and component are covered by tests.
- All component and demo scripts are syntax-checked with Node.

## 4.5 — 2026-10-29

### Ready-made component library

- Added **12 real-world components** with live previews and separate HTML, CSS and JavaScript code:
  - product filter and cart
  - form validation
  - debounced search with cancellation
  - accessible tabs
  - native dialog modal
  - toast queue
  - sortable table
  - image upload preview
  - countdown timer
  - star rating
  - canvas bar chart
  - drag & drop list
- Added the **Komponenty** tab and pages at `/js/komponenty/` and `/js/komponenty/<slug>/`.
- Each component page has a sandboxed iframe preview, copyable code tabs, a list of JavaScript functions used in context, and notes about production use.
- Added a home-page feature band and navigation entry.
- Added component model, JSON loading, fingerprinting, admin, preview builder and tests.
- Added tests for component rendering, categories and preview documents.

### Verification

- **78 tests pass**.
- All 12 component scripts are syntax-checked with Node.
- Component previews render through the same sandboxed iframe policy as lessons and challenges.

## 4.4 — 2026-10-29

### More challenges and a live playground

- Expanded the challenge lab from **18 to 30 tasks**.
- Added pure-data challenges (palindrome, word count, `range`, `slugify`, `sumBy`, intersection, `zipObject`, query parsing, partitioning) and async challenges (`sleep`, `retry`).
- The challenge runner now supports **async `solve` functions**; tests await the result.
- Added **Piaskownica** at `/js/piaskownica/`: a free-form code editor with a sandboxed iframe output console, examples, `Ctrl/Cmd+Enter`, and no server-side execution.
- Added links from the challenge index and challenge sidebar to the playground.
- Added tests for the playground and an async challenge.
- Updated the challenge count and documentation.

### Verification

- **75 tests pass**.
- All 30 challenge solutions are executed against their tests, including async cases.
- The generated iframe runner and playground scripts are syntax-checked with Node.

## 4.3 — 2026-10-29

### AI and programmer careers

- Added the **AI a praca programisty** module: 3 lessons, 6 questions and 5 flashcards.
- Added a special, source-backed page at `/js/wiedza/ai-praca/` with 8 facts, limitations, a learning plan and 9 primary sources.
- The page separates measured data from claims:
  - Stack Overflow 2025: 80% use AI, 29% trust accuracy, 66% spend more time fixing “almost right” code.
  - DORA 2025: 90% adoption, 30% little/no trust, verification tax and higher instability.
  - METR 2025: 19% longer for experienced open-source developers; later results and selection limits are stated explicitly.
  - Veracode 2025: 45% of AI-generated samples failed security tests.
  - BLS: +10.2% projected software developer employment, 2025–2035.
  - Stack Overflow 2025: 68.8% of professionals use JavaScript; 48.8% use TypeScript.
  - npm: 205,386,791 React downloads in the week of 21–27 October 2026.
- Added an explicit “what these numbers do not prove” section: projections are not guarantees, surveys are self-reports, npm downloads are not jobs, and METR has selection effects.
- Added a home-page feature band and module-to-section link.
- JS Akademia now has **17 modules, 51 lessons, 111 questions and 105 flashcards**.

### Verification

- **73 tests pass**.
- Every career fact has an HTTPS source URL and a reviewed date.
- The AI page is covered by tests for key facts, sources and module routing.

## 4.2 — 2026-10-29

### JS Akademia — practice pack

- Added **18 coding challenges** with a sandboxed in-browser editor, automatic tests, progressive hints and solutions.
- Added **36 curiosities** about JavaScript, the browser, React, security and AI.
- Added a **50-term glossary** with Polish definitions and practical snippets.
- Added **30 interview questions** with model answers and follow-up questions.
- Added the **Mistrzostwo JS** module: 3 lessons, 15 mixed questions and 25 flashcards.
- JS Akademia now has **16 modules, 48 lessons, 105 questions and 100 flashcards**.
- Added **XP, levels and daily streaks** based on completed lessons, quizzes, flashcards and challenges.
- Added a daily fact and daily challenge to the JS home page.
- Challenge completion is stored per learner and awards XP once.
- Added tests for challenges, knowledge pages, gamification and content counts.

### Verification

- **70 tests pass**.
- Challenge solutions are executed against every test case in Node.
- The challenge runner is checked for JavaScript syntax.
- Final ZIP is extracted and verified with the full suite.

## 4.1 — 2026-10-29

### JS Akademia — więcej modułów, fiszek i żywych dem

- Expanded JS Akademia from 8 to **15 modules**, from 24 to **45 lessons**, from 48 to **90 quiz questions**, and from 24 to **75 flashcards**.
- Added seven advanced modules:
  - Wzorce i architektura frontendu
  - Struktury danych i algorytmy
  - Node.js i narzędzia
  - React w praktyce
  - React Native w produkcji
  - JavaScript + AI
  - Bezpieczeństwo i wydajność frontendu
- Added **10 interactive iframe demos** embedded in lessons:
  - cart total with `reduce`
  - async/await loading and errors
  - live form validation
  - state → render model
  - form state machine
  - expense grouping with Map/reduce
  - event-loop ordering
  - LLM streaming simulation with stop
  - XSS: `textContent` vs `innerHTML`
  - offline queue
- Demos are self-contained HTML documents rendered in a sandboxed iframe with `allow-scripts` only and no same-origin access.
- Added live-demo fields, validation, seeding, admin support, and tests.
- Added sixteen extra flashcards to the original eight modules.

### Verification

- **64 tests pass**.
- JS content: 15 modules, 45 lessons, 90 questions, 75 flashcards, 10 demos.
- Iframe sandbox and lesson rendering are tested.

## 4.0.1 — 2026-10-29

### Fixed

- **Flashcard rating did not advance to the next card.** The double-submit guard disabled the clicked submit button before the browser serialized the form, so the `rating` value was omitted and the server redirected back to the same card. The guard now keeps the submitter enabled and uses a form-level submitting flag instead.
- Added cache-busting query strings for the shared CSS/JS so the fixed script is loaded without a hard refresh.
- Added a regression test for the rating submission script.

## 4.0 — 2026-10-29

### JS Akademia — nowa platforma w Django Quest

- Added a separate **JavaScript tab** in the sidebar with a yellow visual identity and full Polish interface (`lang="pl"`).
- Added a guided path: **JavaScript → TypeScript → React → React Native**.
- Added **8 modules, 24 lessons, 48 quiz questions, 24 flashcards and 8 projects**.
- Added lesson completion tracking, module quizzes with answer explanations, spaced-repetition flashcards, and a Polish progress notebook.
- Added module-level projects, learning outcomes, time estimates, and a roadmap with prerequisites/order.
- Content lives in `js_academy/content/*.json` with validation, fingerprinting, and `seed_js`.
- Added a platform switcher so Django Quest and JS Akademia remain one local app with independent progress.
- Added **18 JS Academy tests**; the full suite now has **63 tests**.

## 3.0 — 2026-10-29

### Architecture Studio

- Added **8 system-design labs** with scenario, scale, requirements, constraints, reference components, data flow, data model sketch, decision log, starter code, failure modes, trade-offs, and evolution.
- Labs cover AI document RAG, tool-using agents, multi-tenant SaaS, webhook platforms, marketplace ledgers, real-time notifications, analytics pipelines, and legacy modernization.
- Added the **AI-era durable skills map** and a “what AI changes / what it does not change” explanation.
- Added a top-level Architecture navigation section and a home-page studio teaser.

### More advanced paths

- Grew the quiz bank from 225 to **330 questions**, flashcards from 105 to **154**, and topics from 15 to **22**.
- Added:
  - Software Architecture & Boundaries
  - Distributed Systems & Reliability
  - Data & Domain Modeling
  - AI Integration Architecture
  - AI-Assisted Engineering
  - Platform Engineering & Operations
  - Security Architecture & Threat Modeling

### Field guide expansion

- Grew cheatsheets from 19 to **28**, adding LLM gateways, RAG citations, structured AI output, human approval for tools, eval harnesses, prompt-injection defence, ADRs, architecture fitness tests, and AI cost budgets.
- Extended validation, seeding, admin, and tests for architecture cases.

### Verification

- **44 automated tests pass** on Django 6.1.2.
- Main routes, architecture labs, field guide, blueprints, releases, and progress pages were live-checked.
- Portable ZIP is rebuilt and validated with the full test suite.

## 2.0 — 2026-10-29

### Expanded curriculum

- Grew the quiz bank from 120 to **225 questions** and from 8 to **15 topics**.
- Grew the flashcard bank from 56 to **105 cards**.
- Added seven advanced paths:
  - APIs & Django REST Framework
  - Files, Email & Storage
  - Admin & Internal Tools
  - Search & PostgreSQL
  - Tasks, Queues & Realtime
  - Architecture & Multi-Tenant SaaS
  - Modern Django & Release Radar

### Field guide

- Added **19 real-world cheatsheets** with code, situations, and production traps.
- Added **6 application blueprints** with domain models, screens, starter code, checklists, and pitfalls.
- Added a **Release Radar** with support windows, patch summaries, CVE notes, and links to official sources.
- Added server-side recipe search and category filtering, copyable code blocks, and linked release anchors.

### Platform and maintenance

- Upgraded and verified against **Django 6.1.2**.
- Changed requirements to `Django>=5.2,<6.2`: Python 3.12+ receives 6.1.x, Python 3.10–3.11 receives 5.2 LTS.
- Added content fingerprinting so `start.py` seeds new/updated JSON without overwriting admin edits on every launch.
- Added `start.py --update` for intentional dependency upgrades.
- Added field-guide validation, seeding, admin registration, and automated tests.
- Increased the test suite to **40 tests**, including field-guide search, blueprints, release content, and link checks.

### Release snapshot

The release data was reviewed on **29 October 2026**. Current lines at that time:

- Latest stable: **Django 6.1.2**
- Latest LTS: **Django 5.2.18**
- 6.0 patch line: **6.0.9**, in extended support
- 4.2 is unsupported

The in-app radar is curated documentation, not a live advisory feed. Always verify against the [official Django download page](https://www.djangoproject.com/download/) and release notes before deploying.

## 1.0

- Initial local-first Django quiz and fiszki app.
- 120 questions, 56 flashcards, 8 topics, spaced repetition, XP, streaks, achievements, and cross-platform launcher.
