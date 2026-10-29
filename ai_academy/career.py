"""Static career guidance for the Applied AI Engineer path."""

ROLE_PATHS = [
    {
        "key": "llm-engineer",
        "title": "LLM / GenAI Engineer",
        "tagline": "The default destination for this path: build reliable LLM features and products.",
        "modules": "All eight modules",
        "focus": "Prompting, RAG, tools, evaluation, serving",
        "portfolio": "Docs Answer Engine + Research Copilot + Capstone",
        "fit": "Best fit if you enjoy product engineering, APIs and fast iteration.",
    },
    {
        "key": "ml-engineer",
        "title": "Machine Learning Engineer",
        "tagline": "A more model- and data-centric route with the same foundations.",
        "modules": "Modules 0–4, 7",
        "focus": "Data, classical ML, PyTorch, model evaluation and deployment",
        "portfolio": "Churn Audit + Default-Risk Predictor + Ticket Classifier",
        "fit": "Best fit if you like statistics, experimentation and model behaviour.",
    },
    {
        "key": "ai-automation",
        "title": "AI Automation / Solutions Engineer",
        "tagline": "Build workflows that remove repetitive work inside real businesses.",
        "modules": "Modules 0, 1, 5, 6, 7",
        "focus": "LLM APIs, workflow design, tools, integrations and cost control",
        "portfolio": "Study Buddy CLI + Research Copilot + an internal automation",
        "fit": "Best fit if you enjoy talking to users and shipping practical systems.",
    },
]

TWELVE_MONTH_PLAN = [
    {
        "months": "Weeks 1–3",
        "title": "Python for AI, without the detours",
        "modules": "Python for AI",
        "output": "Notes-to-Dataset Pipeline with tests",
        "hours": "6–8 h / week",
    },
    {
        "months": "Months 1–2",
        "title": "Foundations that do not collapse",
        "modules": "AI Foundations & Python · Data, Math & Evaluation",
        "output": "Study Buddy CLI and a churn data audit",
        "hours": "8–10 h / week",
    },
    {
        "months": "Months 3–4",
        "title": "Classical ML and honest evaluation",
        "modules": "Classical Machine Learning",
        "output": "Default-Risk Predictor with a model card",
        "hours": "10–12 h / week",
    },
    {
        "months": "Months 5–6",
        "title": "Neural networks and NLP",
        "modules": "Deep Learning & NLP",
        "output": "Support Ticket Classifier with error analysis",
        "hours": "10–12 h / week",
    },
    {
        "months": "Months 7–8",
        "title": "LLM engineering and RAG",
        "modules": "LLM Engineering & RAG",
        "output": "Docs Answer Engine with citations and evals",
        "hours": "10–12 h / week",
    },
    {
        "months": "Months 9–10",
        "title": "Agents, tools and evaluation",
        "modules": "Agents, Tools & Evaluation",
        "output": "Research Copilot with approvals and traces",
        "hours": "10–12 h / week",
    },
    {
        "months": "Month 11",
        "title": "Production and capstone",
        "modules": "Production, MLOps & Career",
        "output": "Deployed capstone with monitoring and a case study",
        "hours": "12–15 h / week",
    },
    {
        "months": "Month 12",
        "title": "Portfolio, applications and interviews",
        "modules": "Career module",
        "output": "Three case studies, a demo video and a weekly application cadence",
        "hours": "8–10 h / week",
    },
]

INTERVIEW_TOPICS = [
    {
        "area": "Python and software engineering",
        "questions": [
            "Design a small service with typed inputs, timeouts and structured errors.",
            "How do you test a function that calls an external model?",
            "What belongs in a lockfile, and why does it matter for reproducibility?",
        ],
    },
    {
        "area": "ML fundamentals",
        "questions": [
            "Explain bias and variance with an example from your own project.",
            "When would you choose a linear model over gradient boosting?",
            "How do you detect and prevent data leakage?",
        ],
    },
    {
        "area": "LLM systems",
        "questions": [
            "Walk through a RAG request from document ingestion to citation.",
            "How do you evaluate retrieval separately from generation?",
            "What is prompt injection, and which defences are actually enforceable?",
        ],
    },
    {
        "area": "System design",
        "questions": [
            "Design an AI support assistant for a multi-tenant SaaS product.",
            "Where do you put human approval, and why?",
            "How would you monitor quality, cost and safety after launch?",
        ],
    },
    {
        "area": "Project deep-dive",
        "questions": [
            "What was the baseline, and what did your model add?",
            "Describe a failure you found and how you fixed it.",
            "What would you do differently with twice the time?",
        ],
    },
]
