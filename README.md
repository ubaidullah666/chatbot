# Assignment 1 — Local Conversational AI System

## ApexDrive AI: Car Rental Concierge

> **100% local CPU inference · No cloud APIs · Real-time WebSocket streaming**

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Domain Design — Car Rental](#3-domain-design--car-rental)
4. [Model Selection & Compliance](#4-model-selection--compliance)
5. [Prompt Engineering Strategy](#5-prompt-engineering-strategy)
6. [Context Memory Management](#6-context-memory-management)
7. [Topic Switching & Guardrails](#7-topic-switching--guardrails)
8. [Project Structure](#8-project-structure)
9. [Installation & Running](#9-installation--running)
10. [API Reference](#10-api-reference)
11. [Test Suite](#11-test-suite)
12. [Latency Benchmarks](#12-latency-benchmarks)
13. [Example Dialogues](#13-example-dialogues)

---

## 1. Project Overview

**ApexDrive AI** is a production-grade, domain-specific conversational AI system that acts as an intelligent Car Rental Concierge. The system runs entirely on local CPU hardware — no third-party cloud model APIs (OpenAI, Anthropic, Google AI, etc.) are used. All inference is performed locally via [Ollama](https://ollama.com/).

### Key Features
- ✅ **100% local inference** — `qwen2.5:3b` quantized Q4_K_M running on CPU via Ollama
- ✅ **Real-time token streaming** — WebSocket endpoint with word-by-word response delivery
- ✅ **Live latency telemetry** — TTFT (Time to First Token), tokens/sec, total duration per turn
- ✅ **Strict domain guardrails** — Politely refuses off-domain requests (coding, trivia, etc.)
- ✅ **Sliding-window memory** — Context window management with pinned reservation state
- ✅ **Multi-session concurrency** — Per-session async locking for safe multi-user operation
- ✅ **ChatGPT-style UI** — Modern dark-mode frontend with streaming, chips, and benchmark modal

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               Web Browser (ChatGPT-Style Interface)             │
│  ▸ Real-time WebSocket token streaming                          │
│  ▸ Latency telemetry (TTFT, tok/s, duration)                   │
│  ▸ Session reset, suggestion chips, benchmark modal             │
└────────────────────────┬────────────────────────────────────────┘
                         │  WS: /ws/chat  │  REST: /api/*
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Application Server                      │
│  ▸ /ws/chat  — streaming WebSocket endpoint                     │
│  ▸ /api/sessions  — session CRUD                                │
│  ▸ /api/health  — Ollama connectivity check                     │
│  ▸ /api/benchmark  — CPU throughput measurement                 │
│  ▸ /api/domain/info  — catalog, pricing, policy export          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Conversation & Session Manager                      │
│  ▸ In-memory per-session state store                            │
│  ▸ asyncio.Lock for safe concurrent access                      │
│  ▸ Sliding-window context + pinned entity extraction            │
│  ▸ Turn-taking hygiene (user ↔ assistant alternation)           │
└────────────────────────┬────────────────────────────────────────┘
                         │ async HTTP streaming
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Local LLM Engine (Ollama / CPU)                     │
│  Model: qwen2.5:3b  ·  Q4_K_M quantization  ·  3.1B params     │
│  Endpoint: http://127.0.0.1:11434/api/chat                      │
│  CPU-only · Zero cloud API dependency                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Domain Design — Car Rental

**Business Domain:** Car Rental Booking Concierge ("ApexDrive AI")

### Fleet Catalog

| Category | Models | Daily Rate | Seats | Luggage |
|---|---|---|---|---|
| Economy | Toyota Corolla, Hyundai Elantra | $45/day | 5 | 2 Large Bags |
| SUV | Toyota RAV4, Ford Explorer | $75/day | 5 | 4 Large Bags |
| Electric | Tesla Model 3, Polestar 2 | $85/day | 5 | 3 Bags + Frunk |
| Luxury | BMW 4 Series, Mercedes C-Class | $135/day | 5 | 3 Large Bags |

### Insurance Tiers

| Plan | Daily Cost | Deductible | Coverage |
|---|---|---|---|
| Standard CDW | $15/day | $500 | Collision + 3rd party |
| Zero Excess Premium | $28/day | $0 | Full + tyre + windscreen |
| Roadside Plus | $7/day | $0 | 24/7 towing + lockout |

### Rental Policies
- **Minimum age:** 21 years (Young Driver Surcharge $20/day for ages 21-24)
- **License:** Valid 1+ year; IDP required for international renters
- **Deposit:** $200 refundable credit card pre-authorization at pickup
- **Cancellation:** 100% free up to 24 hours before pickup
- **Fuel:** Full-to-Full policy

### Booking Stages
1. **GREETING** — Welcome, inquire about dates/location/category
2. **INFORMATION GATHERING** — Collect rental period, vehicle tier, driver age, insurance
3. **QUOTATION** — Itemized price breakdown with confirmation request
4. **CLOSING** — Issue `APX-XXXXX` confirmation code + pickup instructions

---

## 4. Model Selection & Compliance

| Requirement | Specification |
|---|---|
| Parameter Range | 0.5B – 4B, Q4 quantization |
| **Selected Model** | **`qwen2.5:3b` — 3.1B params, Q4_K_M** |
| Inference Runtime | Ollama v0.32+ (local CPU) |
| Cloud APIs Used | **None** |
| Context Length | 32,768 tokens |
| Quantization | Q4_K_M (GGUF format) |

The model was selected for its strong instruction-following capabilities in the 3B class, reliable conversational structure, and the availability of Q4_K_M quantization allowing efficient CPU inference.

---

## 5. Prompt Engineering Strategy

### System Prompt Structure (`app/prompt_builder.py`)

The system prompt is dynamically assembled from modular sections:

```
1. IDENTITY & ROLE DECLARATION
   → Who ApexDrive AI is, its purpose, its constraints

2. FLEET CATALOG & DAILY PRICING
   → All vehicle tiers with models, rates, specs, and use cases

3. INSURANCE PACKAGES
   → All three tiers with daily cost, deductible, and coverage

4. OPTIONAL ADD-ONS
   → Child seats, additional drivers, GPS units

5. RENTAL REQUIREMENTS & POLICIES
   → Age, license, deposit, cancellation, fuel rules

6. CONVERSATIONAL STAGES & WORKFLOW
   → Stage-by-stage progression from greeting → closing
   → Itemized quote format template
   → Confirmation code format (APX-XXXXX)

7. TOPIC SWITCHING & PIVOT HANDLING
   → Acknowledge pivot, answer question, re-anchor to booking

8. STRICT DOMAIN GUARDRAILS (CRITICAL SECTION)
   → What the assistant WILL NOT do
   → Explicit deflection strategy with example phrasing

9. RESPONSE STYLE & TONE
   → Professional, concise, structured with bullet points
```

### Key Design Decisions
- **No RAG / No Tools:** All knowledge is encoded directly in the system prompt at startup — this satisfies the "no tools" assignment constraint while ensuring consistent, accurate responses.
- **Stage injection:** The prompt explicitly defines Stage 1–4 workflow so the model naturally progresses bookings without special turn detection logic.
- **Quote template embedded in prompt:** A precise itemized quote format is specified, ensuring predictable, structured pricing outputs.
- **Pinned summary injection:** When history slides beyond the window, a compact "Current Reservation Context" block is appended to the system prompt to prevent loss of earlier booking details.

---

## 6. Context Memory Management

### Sliding Window + Pinned Entity Extraction

```
Session History (grows with each turn)
┌──────────────────────────────────────────────────────────────────┐
│ Turn 1: User asks about SUV         → Entity: vehicle = SUV      │
│ Turn 2: AI explains options         → Entity: days = 4 detected  │
│ Turn 3: User confirms age 22        → Entity: age = 22 detected  │
│  ...                                                              │
│ Turn 9: (now beyond MAX_TURNS=8)    ← TRUNCATION POINT           │
│  ↑ Older turns removed from prompt window                        │
│  ↑ BUT entities extracted to "Pinned Summary"                    │
│  ↑ Pinned Summary injected into System Prompt                    │
└──────────────────────────────────────────────────────────────────┘

Prompt sent to model = [System Prompt + Pinned Summary] + [Last 8 Turns]
```

### Entity Extraction (Heuristic)
The `Session._update_extracted_state()` method uses regex patterns to detect and persist:
- **Vehicle category** (Economy / SUV / Electric / Luxury)
- **Rental duration** (`\d+ day(s)`)
- **Driver age** (`i am \d{2}`)
- **Insurance selection** (zero excess / standard cdw / roadside)
- **Pickup location** (airport / downtown)
- **Confirmation code** (`APX-\d{5}`)

This ensures that even after context window sliding, a booking halfway through won't lose the customer's chosen vehicle or dates.

---

## 7. Topic Switching & Guardrails

### Topic Switching
When a customer pivots mid-conversation (e.g., asks about insurance while reviewing a quote):
1. The new question is answered using in-prompt knowledge
2. All previously collected state (vehicle, dates, age) is preserved in extracted entities
3. The model naturally re-anchors to the booking flow from the stage prompt

### Domain Guardrails
The guardrail strategy is defined in the system prompt's critical section and tested via `tests/test_guardrails.py`:

| Query Type | Expected Behavior |
|---|---|
| In-domain: Fleet questions | Full, accurate answer from catalog |
| In-domain: Quote request | Itemized breakdown with total |
| Off-domain: Coding request | Polite deflection to car rental |
| Off-domain: Jailbreak attempt | Stays in character as ApexDrive AI |
| Off-domain: General knowledge | Polite deflection and re-anchoring |

---

## 8. Project Structure

```
NLP/
├── app/
│   ├── __init__.py              # Package initialization
│   ├── config.py                # All configurable settings (env-var driven)
│   ├── models.py                # Pydantic schemas for REST and WebSocket
│   ├── domain_config.py         # Fleet catalog, pricing, insurance, policies
│   ├── prompt_builder.py        # System prompt orchestration
│   ├── conversation_manager.py  # Session store + sliding-window memory
│   ├── llm_engine.py            # Async Ollama HTTP streaming client
│   └── main.py                  # FastAPI app + REST + WebSocket endpoints
├── static/
│   ├── index.html               # ChatGPT-style single-page frontend
│   ├── css/
│   │   └── style.css            # Modern dark theme + glassmorphism
│   └── js/
│       └── chat.js              # WebSocket client + streaming renderer
├── tests/
│   ├── test_api.py              # REST + WebSocket endpoint tests (7 tests)
│   ├── test_memory.py           # Context memory + entity extraction (2 tests)
│   ├── test_concurrency.py      # Multi-session isolation + WS concurrency (2 tests)
│   ├── test_failure_handling.py # Error resilience + protocol tests (3 tests)
│   └── test_guardrails.py       # Live LLM domain policy tests (3 tests)
├── scripts/
│   ├── benchmark.py             # CPU latency + throughput benchmark
│   └── run_server.py            # Production server launcher
├── pytest.ini                   # asyncio_mode = auto
├── requirements.txt             # Python dependencies
└── README.md                    # This document
```

---

## 9. Installation & Running

### Prerequisites
- Python 3.12+
- [Ollama](https://ollama.com/) installed and running
- `qwen2.5:3b` model pulled

### Step 1: Pull the Model
```powershell
ollama pull qwen2.5:3b
```

### Step 2: Start Ollama
```powershell
ollama serve
```

### Step 3: Install Python Dependencies
```powershell
py -3.12 -m pip install -r requirements.txt
```

### Step 4: Launch the Server
```powershell
py -3.12 scripts/run_server.py
```

Or directly with uvicorn:
```powershell
py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Step 5: Open the Chat Interface
Navigate to: **http://127.0.0.1:8000**

### Configuration (Optional Environment Variables)
| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:3b` | Ollama model to use |
| `TEMPERATURE` | `0.4` | Generation temperature |
| `MAX_HISTORY_TURNS` | `8` | Sliding window size |
| `PORT` | `8000` | Server port |

---

## 10. API Reference

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serve chat frontend |
| GET | `/api/health` | System health + Ollama status |
| GET | `/api/domain/info` | Fleet catalog, insurance, policies |
| POST | `/api/sessions` | Create new session (returns session_id) |
| GET | `/api/sessions/{id}` | Get session history |
| POST | `/api/sessions/{id}/reset` | Reset session to fresh start |
| POST | `/api/benchmark?runs=N` | Run CPU inference benchmark |

### WebSocket Protocol: `ws://127.0.0.1:8000/ws/chat`

**Client → Server Messages:**
```json
// Start a chat turn
{ "type": "user_message", "session_id": "abc-123", "content": "I need an SUV for 3 days." }

// Heartbeat
{ "type": "ping" }

// Reset current session
{ "type": "reset_session", "session_id": "abc-123" }
```

**Server → Client Messages:**
```json
// Streaming token
{ "type": "token", "session_id": "abc-123", "delta": "We " }

// End of turn with metrics
{ "type": "end_turn", "session_id": "abc-123", "full_response": "We have...",
  "metrics": { "ttft_ms": 1240, "total_duration_ms": 8500, "tokens_generated": 87, "tokens_per_sec": 10.2 } }

// Error (connection stays open)
{ "type": "error", "session_id": "abc-123", "message": "...", "code": "EMPTY_CONTENT" }

// Session reset confirmation
{ "type": "session_reset", "session_id": "abc-123", "welcome_message": "Hello and welcome..." }

// Pong
{ "type": "pong" }
```

---

## 11. Test Suite

Run all non-LLM tests (fast, no Ollama required):
```powershell
py -3.12 -m pytest tests/test_api.py tests/test_memory.py tests/test_concurrency.py tests/test_failure_handling.py -v
```

Run live guardrail tests (requires Ollama running, ~3-5 min on CPU):
```powershell
py -3.12 -m pytest tests/test_guardrails.py -v -s
```

### Test Coverage Summary

| Test File | Tests | What Is Tested |
|---|---|---|
| `test_api.py` | 7 | REST endpoints, session CRUD, WS ping, empty content, session reset |
| `test_memory.py` | 2 | Entity extraction accuracy, sliding window truncation |
| `test_concurrency.py` | 2 | Session isolation across users, simultaneous WS connections |
| `test_failure_handling.py` | 3 | Malformed JSON recovery, unknown type handling, auto session creation |
| `test_guardrails.py` | 3 | In-domain fleet query, off-domain coding deflection, jailbreak resistance |
| **Total** | **17** | |

---

## 12. Latency Benchmarks

Run the benchmark script:
```powershell
py -3.12 scripts/benchmark.py
```

### Representative CPU Results (Qwen 2.5 3B — Q4_K_M — No GPU)

> _Note: First inference includes model loading (~50s cold start). Subsequent turns are significantly faster._

| Metric | Warm Inference |
|---|---|
| Time to First Token (TTFT) | ~7–12 seconds |
| Token Generation Speed | ~8–12 tokens/second |
| Average Response Duration | ~15–25 seconds |
| Context Window Used | ≤2,048 tokens per call |

The in-browser benchmark modal (`Benchmark CPU` button) runs 3 passes and displays aggregate statistics without leaving the UI.

### Performance Notes
- **Cold start** (first request after model load): ~50–60s TTFT due to CPU model initialization
- **Warm requests**: 7–12s TTFT after the model is cached in Ollama
- **Memory footprint**: ~2.5GB RAM for qwen2.5:3b at Q4_K_M
- The system uses `httpx.AsyncClient` with streaming, ensuring the FastAPI server remains **non-blocking** during long inference periods — other concurrent sessions proceed unimpaired

---

## 13. Example Dialogues

### Example 1: Complete Booking Flow

```
User: Hi, I need a car for a long weekend trip.

AI: Hello and welcome to ApexDrive! 🚗
    For a long weekend trip, how many days exactly are you thinking?
    And do you prefer Economy (great value), SUV (space + AWD),
    Electric (eco-friendly), or Luxury (premium comfort)?

User: SUV sounds good. 3 days. I'm 23 years old.

AI: Great choice! Here's your itemized quote for an SUV:

    • Base Rate: Toyota RAV4 / Ford Explorer @ $75/day × 3 days = $225
    • Young Driver Surcharge: $20/day × 3 days = $60 (ages 21-24)
    • Insurance: Standard CDW @ $15/day × 3 days = $45
    • ─────────────────────────────────────────
    • Estimated Total: $330
    • + $200 refundable deposit held at pickup

    Would you like to add Zero Excess protection ($28/day) for $0 deductible,
    or shall I confirm this booking?

User: Yes, confirm it please.

AI: Your reservation is confirmed! 🎉

    Booking Reference: APX-74192

    Pickup Instructions:
    • Bring your physical driver's license (held 1+ year)
    • Bring a credit card in your name for the $200 deposit hold
    • Free cancellation up to 24 hours before pickup

    Is there anything else I can help you with?
```

### Example 2: Guardrail Deflection (Off-Domain)

```
User: Can you write me a Python script to scrape car prices?

AI: I apologize, but as the ApexDrive Car Rental concierge, I specialize 
    exclusively in vehicle rentals, fleet options, pricing, and booking policies. 
    I'm not able to assist with programming or web scraping topics.

    However, I'd be happy to help you find the perfect rental vehicle and give 
    you an instant quote! Would you like to check out our fleet options today?
```

### Example 3: Topic Pivot Mid-Booking

```
User: I want an Economy car for 4 days.

AI: Perfect! The Toyota Corolla or Hyundai Elantra at $45/day would be ideal...
    [quote summary for $180 base + insurance]

User: Actually wait — what does Zero Excess insurance actually cover?

AI: Great question! Zero Excess Premium ($28/day) provides:
    • $0 damage deductible — you pay nothing even if the car is damaged
    • Tyre and windscreen protection
    • Theft waiver
    Compared to Standard CDW which has a $500 excess liability.

    Going back to your Economy booking for 4 days — would you like to add
    Zero Excess? That would bring your total to $292 vs $240 with Standard CDW.

User: Let's go with Zero Excess.

AI: Done! Updated quote:
    • Toyota Corolla/Hyundai Elantra @ $45/day × 4 = $180
    • Zero Excess Premium @ $28/day × 4 = $112
    • Total: $292 + $200 deposit
    Shall I confirm this reservation?
```
