# 💬 Ask Moussa: an AI assistant for my portfolio

[![tests](https://github.com/moussa197/askMoussa/actions/workflows/tests.yml/badge.svg)](https://github.com/moussa197/askMoussa/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Claude API](https://img.shields.io/badge/Claude%20API-Haiku%204.5-D97757)
![Deployed on Render](https://img.shields.io/badge/deployed%20on-Render-46E3B7)
![License](https://img.shields.io/badge/license-MIT-green)

A chatbot that answers recruiters' questions about my background, skills and projects, **using only my own documents**. It is a small, production-ready **Python / FastAPI** API built on the **Claude API**, following the **RAG** principle (*Retrieval-Augmented Generation*), and it runs live behind the chat bubble of my portfolio.

**▶ Live demo: [moussa197.github.io](https://moussa197.github.io/)** (open the chat bubble and ask *"What projects has Moussa built?"*)
**🇫🇷 Full documentation in French:** [README.fr.md](README.fr.md)

> The API is hosted on Render's free plan, which goes to sleep when idle: the **first** question can take 30 to 60 seconds while the server wakes up. The next ones are answered in a few seconds.

---

## Key facts

| | |
|---|---|
| **Automated tests** | **120**, all offline: they never call the real Claude API, cost nothing and need no network |
| **Production dependencies** | **4** (FastAPI, uvicorn, the official `anthropic` SDK, python-dotenv), to fit in Render's 512 MB of RAM |
| **Knowledge base** | 3 Markdown files (CV, FAQ, projects), about 16 KB of text, sent in full with every question |
| **Model** | `claude-haiku-4-5`, answers capped at 400 tokens |
| **Rate limits** | 10 questions per minute and 30 per day per IP, 300 per day in total |
| **Input limits** | questions up to 500 characters, request bodies up to 8 KB |
| **Claude timeout** | 20 s per call, 1 retry: a visitor never waits for minutes |

## How it works

When a visitor asks a question (`POST /chat`), the request goes through these steps, and **Claude is only called if every check passes**:

```
Visitor's question (chat bubble on the portfolio)
        │
        ▼
 1. CORS            only https://moussa197.github.io may call the API from a browser
 2. Body size       more than 8 KB → 413, rejected before being fully read
 3. Validation      empty question or more than 500 characters → 422
 4. Rate limit      too many questions for this IP, or daily cap reached → 429
 5. Prompt          rules + the 3 documents from data/ + the tagged question
 6. Claude API      short answer in the visitor's language, from the documents only
        │
        ▼
 {"answer": "..."}  or a neutral 503 if Claude is unavailable
```

The documents are loaded and the system prompt is built **once**, when the server starts. If the API key or a document is missing, the server refuses to start with a clear message.

## Technical choices

- **All the documents with every question, no vector database.** The knowledge base is small enough to fit entirely in Claude's context. Embedding search would be heavier, more complex and less reliable at this scale.
- **Minimal dependencies.** No LangChain, PyTorch or vector store: the free hosting plan only has 512 MB of RAM.
- **A hand-written rate limiter.** A ~100-line *sliding window* with no dependency, protected by a lock against concurrent requests, and tested with a fake clock (no waiting in tests).
- **Layered defence against prompt injection.** The rules live in the system prompt; the question is wrapped in `<question>` tags and HTML-escaped, so a visitor cannot close the tag; the prompt states that the question is never an instruction; and both questions and answers are length-limited.
- **Tests with no real API call.** The Claude client is injected, so tests replace it with a fake one. As a safety net, the SDK is also pointed to a closed local address during tests: a test that forgets the fake client fails instead of being billed.
- **Neutral errors for visitors, useful logs for me.** A Claude outage returns a generic 503. Logs record the error type and request ID, but **never** the visitor's question or the API key.
- **Hardened for production.** The interactive `/docs` page is switched off on Render, CORS never allows `*`, and the 422 error never echoes the visitor's input back.

The full architecture and every design decision are documented (in French) in [PLAN.md](PLAN.md).

## Method: supervising AI agents

I built this project by orchestrating AI coding agents (Claude Code), keeping the role of supervisor and architect:

- **A framework set up front.** I wrote the project rules in [CLAUDE.md](CLAUDE.md) (technical constraints, security, chatbot behaviour, how we collaborate) and approved the architecture plan ([PLAN.md](PLAN.md)) before any code was written.
- **One step at a time.** For each feature, the agent explained its choices and the alternatives, then implemented only after my approval. Each step ended with pytest tests that I ran and checked, then a commit that I made myself.
- **Human decisions.** I made the trade-offs, for example lowering the Claude API timeout so that a visitor never waits up to 90 seconds.
- **Real-world testing.** My manual tests revealed problems that automated tests could not see, and I had them fixed: an out-of-credit error returned a raw 500 (now a neutral 503), and answers contained Markdown, addressed visitors too informally in French (*tu* instead of *vous*) and were too long for a chat bubble.
- **Specialised agents** for architecture planning, test writing, code review and security review.

## Limitations

- **Rate-limit counters live in memory.** They reset whenever the server restarts, and the free plan sleeps after a few minutes of inactivity. The **monthly spending limit** set in the Anthropic console remains the real safety net.
- **A single uvicorn worker is required**, otherwise each process would keep its own counters.
- **The visitor's real IP** behind Render's proxy depends on the `XFF_POSITION` setting, which had to be measured at deployment time.
- **The whole knowledge base is sent with every question.** That is the right choice at 16 KB, but it would not scale to a large set of documents. A keyword search (BM25) is designed in [PLAN.md](PLAN.md) for that case, but not implemented, since it is not needed yet.
- **The answers are only as good as the documents.** When the information is missing, the assistant says so and suggests contacting me by email, rather than guessing.

## Run it locally

Requirements: **Python 3.12** and an Anthropic API key ([console.anthropic.com](https://console.anthropic.com/)).

```bash
git clone https://github.com/moussa197/askMoussa.git
cd askMoussa
python -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env               # Windows (PowerShell): Copy-Item .env.example .env
```

Open `.env` and fill in your key (`ANTHROPIC_API_KEY=sk-ant-...`). The `.env` file is ignored by Git and must **never** be committed.

Start the server:

```bash
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** to try the API in your browser.

### Tests

```bash
pytest -v
```

No API key, credits or network connection needed. The same tests run on GitHub Actions on every push.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Returns `{"status": "ok"}`. No Claude call and no rate limit (used by Render's health check and to wake the server up). |
| `POST /chat` | Body `{"question": "What projects has Moussa built?"}` → `{"answer": "..."}` |

```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"question": "What projects has Moussa built?"}'
```

| Code | Meaning |
|---|---|
| 200 | Claude's answer |
| 413 | Request body too large (more than 8 KB) |
| 422 | Missing, empty, malformed or too long question (the input is never echoed back) |
| 429 | Too many questions (per-IP limit or global daily cap) |
| 503 | Claude unavailable (outage, timeout, no credits…) |

Every setting (model, limits, allowed origins…) can be changed with environment variables: see [.env.example](.env.example) and the configuration table in [README.fr.md](README.fr.md#configuration).

## Project structure

```
askMoussa/
├── app/
│   ├── main.py            # FastAPI app: CORS, /health and /chat routes, error handling
│   ├── config.py          # Reads and validates the environment variables
│   ├── documents.py       # Loads the files in data/ (HTML comments removed)
│   ├── prompt.py          # Chatbot rules, tagged documents, tagged question
│   ├── claude_client.py   # The only place that calls the Claude API
│   ├── rate_limit.py      # Per-IP limits, global cap, visitor IP
│   └── limite_corps.py    # Rejects (413) request bodies over 8 KB
├── data/                  # Knowledge base: cv.md, faq.md, projets.md
├── tests/                 # pytest tests, one file per module, no real API call
├── .github/workflows/     # GitHub Actions: runs the tests on every push
├── .env.example           # Configuration template, without a real key
├── requirements.txt       # Production dependencies (installed on Render)
├── requirements-dev.txt   # Development dependencies (pytest, httpx)
├── PLAN.md                # Detailed architecture and project steps (French)
└── CLAUDE.md              # Rules given to the AI agents (French)
```

## Tech stack

Python 3.12 · FastAPI · uvicorn · Anthropic Claude API (`claude-haiku-4-5`) · pytest · GitHub Actions · Render

## Author

**Moussa Keita**, Bachelor's student in Computer Science and Artificial Intelligence at ESEO (Angers, France), looking for an internship or a work-study position.
Portfolio: [moussa197.github.io](https://moussa197.github.io/) · GitHub: [@moussa197](https://github.com/moussa197)

Released under the [MIT License](LICENSE).
