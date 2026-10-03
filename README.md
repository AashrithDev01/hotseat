# HotSeat 🔥

**Rehearse high-stakes conversations out loud — before they count.**

HotSeat is a voice-native AI panel for Alexa+, built for the
[Build, Ship, Shape: Amazon Developer Hackathon](https://amazonappdev2026.devpost.com/).
It puts you in the hot seat in two arenas:

1. **Interview Panel** — multi-persona mock interviews with adaptive follow-ups
   and live STAR scoring.
2. **Stakeholder Room** — rehearse presentations and pitches while AI
   stakeholders (a skeptical CFO, a technician, a time-crunched exec) grill you
   like the real room would.

## How it works

HotSeat is a self-hosted **MCP server** (Streamable HTTP, MCP spec 2025-11-25+)
that exposes four tools:

| Tool | What it does |
|---|---|
| `analyze_brief` | Turns a job description *or* a meeting brief into a structured brief card |
| `start_session` | Starts an interview or stakeholder session with your chosen panel |
| `submit_answer` | Scores your spoken answer and returns a follow-up, objection, or next question |
| `get_session_report` | Final report: scores, strengths, gaps, tips + thank-you email or exec summary |

The agent layer runs on the **Strands Agents SDK** with **AWS Bedrock (Claude)**
for reasoning, and session state lives in **DynamoDB**. A simulated Alexa+ web
experience (voice in/out via the Web Speech API) is the demo frontend.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add AWS credentials when available
uvicorn src.server:app --host 0.0.0.0 --port 8000
```

The MCP endpoint is served at `http://localhost:8000/mcp`.

## Project layout

```
hotseat/
├── src/
│   ├── server.py            # FastAPI + MCP StreamableHTTP app
│   ├── tools/               # analyze_brief, session, report tool implementations
│   ├── agents/              # persona definitions + evaluator rubric
│   ├── models/              # session state pydantic models
│   └── llm/                 # LLM client interface (Bedrock when AWS is live)
├── prompts/                 # persona + rubric prompt source files
├── frontend/                # simulated Alexa+ web experience
├── FRICTION_LOG.md          # build friction log (judging bonus!)
└── requirements.txt
```

## Status

🚧 Week 1 scaffold — MCP server skeleton, tool stubs, persona/rubric content.
Bedrock + Strands integration lands once the AWS account is live.

## License

MIT — see [LICENSE](LICENSE).
