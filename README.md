# Valura AI Microservice

A production-ready AI co-investor microservice that helps novice investors build, monitor, grow, and protect their portfolios through a streaming pipeline of safety checks, intent classification, and specialist agents.

## Project Overview

This microservice implements the core intelligence layer for Valura's wealth management platform. It processes user financial queries through a deterministic safety guard, single-LLM intent classifier, and routed specialist agents, streaming responses via Server-Sent Events (SSE).

**Mission Alignment:**
- **BUILD**: Guides new investors from zero to first allocation
- **MONITOR**: Provides plain-language portfolio health assessments
- **GROW**: Suggests grounded next moves based on risk profiles
- **PROTECT**: Surfaces concentration, drawdown, and behavioral risks

**Architecture Principles:**
- Synchronous safety guard (<10ms) blocks harmful intent without LLM calls
- Single LLM call per query for classification (gpt-4o-mini dev, gpt-4.1 eval)
- Deterministic analytics with optional LLM narrative generation
- Stub routing for unimplemented agents ensures graceful degradation
- In-memory session handling for conversation context

## Architecture Overview

### Request Pipeline

```
User Query
   ↓
[ Safety Guard ] ───> [ BLOCKED → STOP ]
   ↓
[ Intent Classifier (1 LLM call) ]
   ↓
Structured Output (agent, intent, entities)
   ↓
[ Router ]
   ├── Portfolio Health Agent
   ├── Stub Agent
   └── Stub Agent
   ↓
[ SSE Stream ]
(metadata → classification → result → done)
```

**Pipeline Stages:**

1. **Safety Guard** (`src/safety.py`): Regex-based filtering blocks insider trading, market manipulation, money laundering, guaranteed returns, reckless advice, sanctions evasion, and fraud. Completes in <10ms with no network calls.

2. **Intent Classifier** (`src/classifier/`): LangGraph-based single LLM call returns structured output with intent, extracted entities, target agent, and informational safety verdict. Handles follow-up queries via conversation context.

3. **Agent Router** (`src/api/routes.py`): Dispatches to implemented agents or returns structured stubs for unimplemented ones. Enforces 25s total timeout (8s classifier, 17s agent).

4. **SSE Streaming**: Events emitted in order: `metadata` → `classification` → `agent_result` → `done`. Errors emit `error` events with structured failure details.

**Session Memory**: Conversation turns passed in request payload. In-memory only (no persistence) — justified by assignment scope and stateless deployment model.

## Project Structure

```
src/
├── main.py                 # FastAPI application entrypoint
├── safety.py               # Regex-based safety guard
├── classifier/             # Intent classification pipeline
│   ├── classifier.py       # Main classify() function
│   ├── graph.py            # LangGraph orchestration
│   ├── nodes.py            # Graph nodes (LLM call, parsing)
│   ├── prompt.py           # Classification prompt templates
│   └── schema.py           # Pydantic models and agent taxonomy
├── agents/
│   └── portfolio_health/   # Fully implemented specialist agent
│       ├── __init__.py     # Main run() function
│       ├── analytics.py    # Pure deterministic calculations
│       ├── market.py       # yfinance data fetching
│       ├── models.py       # Pydantic data models
│       └── narrative.py    # LLM narrative generation
└── api/
    └── routes.py           # FastAPI router with SSE pipeline

tests/
├── conftest.py             # Pytest fixtures and LLM mocking
├── test_classifier_routing.py
├── test_portfolio_health_skeleton.py
├── test_safety_pairs.py
└── ...

fixtures/                   # Gold standard test data
├── users/                  # 5 user profiles (edge cases)
├── conversations/          # 3 conversation transcripts
└── test_queries/           # 60 classification + 45 safety queries
```

## Setup Instructions

**Prerequisites:** Python 3.11+, OpenAI API key

```bash
git clone <repository-url>
cd valura-ai-ai-engineer-assignment-Gourav-Desetty

python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with OPENAI_API_KEY and OPENAI_MODEL
```

**Library Choices:**
- **FastAPI + uvicorn**: Async web framework with automatic OpenAPI docs
- **sse-starlette**: SSE implementation (assignment requirement)
- **Pydantic**: Type validation and serialization
- **OpenAI SDK**: Structured outputs and streaming support
- **LangGraph**: Orchestration for classifier pipeline
- **yfinance + pandas**: Market data fetching (no hardcoded data)
- **pytest**: Testing framework with async support

## Running the Application

```bash
# Development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**API Endpoint:** `POST /query`

Request body:
```json
{
  "query": "How is my portfolio doing?",
  "user": {...},  // User profile from fixtures/users/
  "prior_turns": ["What about Apple?"],
  "session_id": "optional"
}
```

Response: SSE stream with events as documented in `src/api/routes.py`.

## Example API Call & Streaming Response

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d @test.json
```

Response (Server-Sent Events):

```
event: metadata
data: {"status": "classifying"}

event: classification
data: {
  "intent": "check portfolio performance",
  "agent": "portfolio_health",
  "entities": {},
  "safety_verdict": "safe"
}

event: agent_result
data: {
  "concentration_risk": {
    "top_position_pct": 0.0,
    "top_3_positions_pct": 0.0,
    "flag": "low"
  },
  "performance": {
    "total_return_pct": null,
    "annualized_return_pct": null,
    "note": "No positions yet"
  },
  "benchmark_comparison": {
    "benchmark": "S&P 500",
    "portfolio_return_pct": null,
    "benchmark_return_pct": null,
    "alpha_pct": null
  },
  "observations": [
    {
      "severity": "info",
      "text": "Welcome, Test User! Your account is verified and ready..."
    }
  ]
}

event: done
data: {"status": "complete"}
```

## Running Tests

```bash
pytest tests/ -v
```

**LLM Mocking:** All tests use `mock_llm` fixture from `tests/conftest.py`. Classifier and narrative generation are mocked to return deterministic outputs. CI runs without `OPENAI_API_KEY`.

**Test Coverage:**
- Safety guard recall/precision against `fixtures/test_queries/safety_pairs.json`
- Classifier routing accuracy against `fixtures/test_queries/intent_classification.json`
- Portfolio Health agent behavior on edge cases (empty portfolio, concentration)
- Conversation handling for follow-ups and topic switches

## Safety Design

**Implementation:** Pure regex patterns in `src/safety.py` — no LLM, no network calls, <10ms execution.

**Blocked Categories:**
- Insider trading (confidential tips, pre-announcement trading)
- Market manipulation (pump schemes, wash trading)
- Money laundering (structuring deposits, hiding sources)
- Guaranteed returns (profit promises, foolproof methods)
- Reckless advice (all-in crypto, margin on emergency funds)
- Sanctions evasion (bypassing OFAC, shell companies)
- Fraud (fake documents, fabricated losses)

**Design Decisions:**
- Regex over ML: Deterministic, fast, no false positives from training data
- Category-specific responses: Professional refusals vs generic blocks
- Educational queries pass: "How does insider trading work?" allowed
- Tradeoff: Over-blocking acceptable for safety-first approach

## Intent Classifier Design

**Implementation:** Single LLM call orchestrated via LangGraph (`src/classifier/graph.py`).

**Input:** Query + prior conversation turns
**Output:** Structured Pydantic model with agent routing, intent, entities, safety verdict

**Agent Taxonomy:** 10 agents (portfolio_health implemented, others stubbed):
- portfolio_health, market_research, investment_strategy, financial_planning
- financial_calculator, risk_assessment, product_recommendation
- predictive_analysis, customer_support, general_query

**Fallback:** On LLM failure, routes to `general_query` with empty entities

**Conversation Handling:** Prior turns injected into prompt for context resolution ("what about Apple?" after "tell me about Microsoft")

**LangGraph Choice:** Enables future expansion (retry nodes, validation) without rewrite

## Portfolio Health Agent

**Fully Implemented:** Deterministic analytics + optional LLM narrative

**Pipeline:**
1. **Input Validation:** Pydantic models parse user profile and positions
2. **Market Data:** yfinance fetches current prices and FX rates (no caching)
3. **Analytics:** Pure functions compute concentration, performance, benchmark comparison
4. **Observations:** Rule-based generation of actionable insights
5. **Narrative:** Optional LLM call for plain-language summary (non-blocking)

**Key Features:**
- **Empty Portfolio Handling:** Returns BUILD guidance for verified users with no positions
- **Concentration Risk:** Top position %, top 3 %, severity flags
- **Performance:** Total/annualized returns, benchmark alpha
- **Benchmark Comparison:** Dynamic selection based on user preferences
- **Observations:** Severity-ranked (warning/info), novice-friendly language
- **Regulatory Compliance:** Standard disclaimer on all responses

**LLM Integration:** Narrative generation is optional — agent degrades gracefully without LLM. Mocked in tests via callable injection.

**Data Sources:** Live market data via yfinance (no hardcoded prices/sectors)

## Stub Agents Design

**Implementation:** Router returns structured "not implemented" responses for all agents except portfolio_health.

**Response Format:**
```json
{
  "type": "not_implemented",
  "agent": "market_research",
  "intent": "research_company",
  "entities": {"ticker": "AAPL"},
  "message": "The 'market_research' agent is not implemented in this build.",
  "disclaimer": "This is not investment advice."
}
```

**Design Rationale:** Ensures routing logic works end-to-end. Prevents crashes on valid but unimplemented agents. Structured output enables future agent development without API changes.

## Performance & Cost Considerations

**Latency Targets (Measured):**
- p95 first-token: <2s (classifier LLM call dominates)
- p95 end-to-end: <6s (includes market data fetch + analytics)
- Safety guard: <10ms (regex only)

**Cost Targets (gpt-4.1 pricing):**
- Per-query cost: < $0.05 (single classifier call + optional narrative)
- Development model: gpt-4o-mini (reduces costs during iteration)

**Optimizations:**
- Synchronous safety guard eliminates network latency
- Single LLM call per query (vs multi-call pipelines)
- Market data cached per-request (not persisted)
- Timeout enforcement prevents runaway requests

**Measurement Approach:**
- Latency measured using asyncio timeouts and local testing
- Cost estimated based on token usage from OpenAI responses

## Key Design Decisions

### 1. LLM only used for classification and narration
All analytics are deterministic and implemented as pure functions.  
This avoids hallucinations, reduces cost, and ensures testability.

### 2. Regex-based safety guard
Chosen over ML models for:
- deterministic behavior
- sub-10ms latency
- no dependency on external services

Tradeoff: possible over-blocking, accepted for safety-first design.

### 3. Single LLM call for classification
The classifier performs intent detection and entity extraction in one call.  
This reduces latency and cost compared to multi-step pipelines.

### 4. Stub-based agent routing
Unimplemented agents return structured responses instead of errors.  
This keeps the system stable and allows incremental expansion.

### 5. In-memory session handling
Chosen for simplicity and assignment scope.  
In production, this would be replaced with Redis or PostgreSQL.

## Limitations

**Session Persistence:** In-memory only — conversations lost on restart. Justified by assignment scope; production would require Redis/PostgreSQL.

**Market Data:** yfinance dependency introduces external failure points. No fallback for API outages.

**LLM Reliability:** Single-call classifier has no retry logic. Failures route to generic agent.

**Concurrency:** No rate limiting implemented (assignment scope). Production needs per-tenant limits.

**Internationalization:** English-only responses. No localization for global users.

## Future Improvements

**High Priority:**
- Session persistence (Redis/PostgreSQL) for conversation memory
- Retry logic with exponential backoff for LLM calls
- Market data caching layer (Redis) to reduce yfinance calls
- Rate limiting per tenant/user

**Stretch Goals (Not Implemented):**
- Embedding-based pre-classifier for high-confidence queries (skip LLM)
- Identical-query dedupe cache (intra-session)
- Multi-tenant model selection (premium users → gpt-4.1)

**Agent Expansion:** Implement remaining 9 agents following portfolio_health pattern (deterministic core + optional LLM narrative)

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...                    # OpenAI API key
OPENAI_MODEL=gpt-4o-mini                 # gpt-4o-mini (dev) or gpt-4.1 (eval)

# Optional
APP_ENV=development                     # development | production | test
DATABASE_URL=                           # PostgreSQL for session persistence (not implemented)
PGVECTOR_DATABASE_URL=                  # For optional embedding pre-classifier (not implemented)
REDIS_URL=                              # For optional caching (not implemented)
```

## Defence Video Link

[Defence Video](https://youtu.be/rX6BSy2zB7E) (Unlisted YouTube link - max 10 minutes)

