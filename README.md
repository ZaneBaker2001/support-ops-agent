# Support Ops Agent

A production-style agentic AI service built with LangChain and FastAPI.

## Features

- LangChain agent with tool calling
- Structured JSON responses for downstream systems
- Knowledge retrieval over local markdown docs
- SQLite analytics tool for ticket trends
- FastAPI API with health check and `/v1/ask`
- Config via environment variables

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
mkdir -p data knowledge
python3 scripts/seed_db.py
export USE_MOCK_LLM=true
uvicorn app.api:app --reload
```

Example request:
```curl
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"We saw a spike in failed password reset tickets this week. Summarize likely causes and next actions."}'
```

Example response:
```json
{
  "summary": "This week’s failures appear concentrated in the password-reset flow. The most likely causes are delayed delivery, invalid or expiring tokens, mobile/browser flow issues, and spam filtering for some recipients.",
  "severity": "high",
  "likely_root_causes": [
    "Email provider throttling or delayed delivery",
    "Expired, invalid, or incorrectly signed reset tokens",
    "Mobile web flow errors or stale CSRF/session state",
    "Spam filtering or low sender reputation"
  ],
  "recommended_actions": [
    "Check email provider logs for bounces, throttling, and delivery delays",
    "Validate token TTL, signing secrets, and auth-service clock synchronization",
    "Review recent auth and mobile-web deploys",
    "Break down failures by tenant, platform, browser, and geography",
    "Escalate unresolved high-priority auth tickets to engineering"
  ],
  "evidence": [
    {
      "source": "password-reset-runbook.md",
      "snippet": "Email provider throttling can delay delivery of password reset emails."
    },
    {
      "source": "password-reset-runbook.md",
      "snippet": "Expired or incorrectly signed reset tokens can happen after auth-service clock drift or stale signing secrets."
    }
  ],
  "needs_human_followup": true
}
```

## Directory Structure 

```
support-ops-agent/
├── app/
│   ├── agent.py
│   ├── api.py
│   ├── config.py
│   ├── db.py
│   ├── knowledge.py
│   ├── logging_config.py
│   ├── schemas.py
│   ├── service.py
│   └── tools.py
├── knowledge/
│   ├── password-reset-runbook.md
│   └── sso-postmortem.md
├── scripts/
│    ├── seed_db.py
│    └── evaluate_model.py 
├── .env.example
├── requirements.txt 
├── main.py
└── README.md
```
## Evaluation

An evaluation script is included to assess the overall quality of the agent.  

The script scores the agent on:
- schema validity
- severity accuracy
- root-cause keyword recall
- action keyword recall
- evidence coverage
- latency

Run:

```bash
python3 -m scripts.evaluate_model
```

A sample run yielded an average root-cause keyword recall of **94.4%** and an overall score of **98.3%**. 


