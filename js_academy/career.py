"""Sprawdzone dane do sekcji „AI a praca programisty”.

Każda liczba ma źródło i datę. To celowo nie jest zbiór prognoz ani cytatów
z marketingu dostawców AI.
"""

REVIEWED_ON = "29 października 2026"

FACTS = [
    {
        "value": "80%",
        "label": "deweloperów używa AI",
        "detail": "Stack Overflow Developer Survey 2025, 49 000+ respondentów.",
        "source": "Stack Overflow 2025",
        "url": "https://survey.stackoverflow.co/2025/ai",
    },
    {
        "value": "29%",
        "label": "ufa dokładności AI",
        "detail": "Ten sam survey. 66% twierdzi, że spędza więcej czasu na poprawianiu kodu „prawie dobrego”.",
        "source": "Stack Overflow 2025",
        "url": "https://stackoverflow.blog/2025/12/29/developers-remain-willing-but-reluctant-to-use-ai-the-2025-developer-survey-results-are-here/",
    },
    {
        "value": "90%",
        "label": "specjalistów tech używa AI",
        "detail": "DORA 2025. Ponad 80% deklaruje wzrost produktywności; 30% ma małe lub żadne zaufanie do kodu AI.",
        "source": "DORA 2025",
        "url": "https://dora.dev/research/2025/dora-report/",
    },
    {
        "value": "+19%",
        "label": "dłużej w badaniu METR",
        "detail": "Randomizowane zadania doświadczonych deweloperów open source, początek 2025. Późniejsze dane sugerują możliwe przyspieszenie, ale mają ograniczenia selekcji.",
        "source": "METR 2026",
        "url": "https://metr.org/blog/2026-02-24-uplift-update/",
    },
    {
        "value": "45%",
        "label": "próbek kodu AI oblało testy bezpieczeństwa",
        "detail": "Veracode 2025 GenAI Code Security Report: 80 zadań, ponad 100 modeli, OWASP Top 10.",
        "source": "Veracode 2025",
        "url": "https://www.veracode.com/resources/analyst-reports/2025-genai-code-security-report/",
    },
    {
        "value": "68,8%",
        "label": "profesjonalistów pracuje z JavaScriptem",
        "detail": "Stack Overflow 2025. TypeScript deklaruje 48,8% profesjonalistów.",
        "source": "Stack Overflow 2025",
        "url": "https://survey.stackoverflow.co/2025/technology",
    },
    {
        "value": "205 mln",
        "label": "pobrań Reacta w tygodniu",
        "detail": "npm, 21–27 października 2026. To wskaźnik adopcji ekosystemu, nie liczba miejsc pracy.",
        "source": "npm registry",
        "url": "https://api.npmjs.org/downloads/point/last-week/react",
    },
    {
        "value": "+10,2%",
        "label": "prognoza wzrostu miejsc pracy dla software developerów",
        "detail": "BLS, USA, 2025–2035: z 1,72 mln do 1,89 mln. Prognoza, nie gwarancja.",
        "source": "U.S. BLS",
        "url": "https://data.bls.gov/projections/nationalMatrix?queryParams=15-1252&ioType=o",
    },
]

SOURCES = [
    {
        "label": "Stack Overflow Developer Survey 2025 — AI",
        "detail": "49 000+ respondentów; użycie, zaufanie, frustracje.",
        "url": "https://survey.stackoverflow.co/2025/ai",
    },
    {
        "label": "Stack Overflow 2025 — Technology",
        "detail": "JavaScript 66% ogółem i 68,8% wśród profesjonalistów; TypeScript 48,8%.",
        "url": "https://survey.stackoverflow.co/2025/technology",
    },
    {
        "label": "DORA 2025 — State of AI-assisted Software Development",
        "detail": "90% adopcji, 30% niskiego zaufania, „podatek weryfikacji”, throughput i instability.",
        "url": "https://dora.dev/research/2025/dora-report/",
    },
    {
        "label": "DORA — Balancing AI tensions",
        "detail": "Analiza 1 110 odpowiedzi inżynierów Google, Q3 2025.",
        "url": "https://dora.dev/insights/balancing-ai-tensions/",
    },
    {
        "label": "METR — Changing our developer productivity experiment design",
        "detail": "19% dłużej w 2025; późniejsze wyniki i problem selekcji uczestników.",
        "url": "https://metr.org/blog/2026-02-24-uplift-update/",
    },
    {
        "label": "METR — Measuring the impact of AI on experienced OSS developers",
        "detail": "Papier i dane źródłowe wczesnego badania.",
        "url": "https://arxiv.org/pdf/2507.09089",
    },
    {
        "label": "Veracode — 2025 GenAI Code Security Report",
        "detail": "45% próbek z podatnościami OWASP Top 10; 80 zadań, 100+ modeli.",
        "url": "https://www.veracode.com/resources/analyst-reports/2025-genai-code-security-report/",
    },
    {
        "label": "U.S. Bureau of Labor Statistics — Employment Matrix 15-1252",
        "detail": "Prognoza 2025–2035 dla software developers: +10,2%.",
        "url": "https://data.bls.gov/projections/nationalMatrix?queryParams=15-1252&ioType=o",
    },
    {
        "label": "npm registry — React weekly downloads",
        "detail": "205 386 791 pobrań w tygodniu 21–27 października 2026.",
        "url": "https://api.npmjs.org/downloads/point/last-week/react",
    },
]
