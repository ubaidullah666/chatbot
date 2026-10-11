# ApexDrive — Assignment 2: local RAG

Extends the Assignment 1 FastAPI/WebSocket assistant with 60 authored Markdown documents for a fictional car-rental business. Documents are teaching examples, not real company policies. No agent, external search, hosted embedding API, or tool calling is used at runtime. Original documentation is retained in ASSIGNMENT1.md for historical reference; its prompt-only architecture and performance claims do not describe this version.

## Setup (Python 3.12 recommended)

On Windows, after setup, double-click **run.bat** in the project folder. It checks dependencies and model files, builds the index if missing, starts local Ollama if needed, and runs the server. Open http://localhost:8000 once startup completes (or the configured PORT). Keep the window open; Ctrl+C stops the assistant. Missing dependencies or models produce setup instructions instead of automatic downloads. Rerun the indexer manually after editing documents.

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# One-time online provisioning, or copy an already downloaded model to this directory:
python -m scripts.download_embedding_model
python -m scripts.index_documents
python -m scripts.benchmark_retrieval
# Provision qwen2.5:3b in Ollama, then run Ollama locally.
python -m scripts.run_server
```

After dependencies and model weights are provisioned, indexing and retrieval run offline. RAG_MODEL defaults to models/all-MiniLM-L6-v2; local_files_only prevents automatic network downloads. The assistant uses the existing local Ollama endpoint for generation. The existing UI uses CDN resources; an offline browser needs those cached or served locally.

## Data and indexing

The checked-in data/documents directory contains 60 documents: 4 category guides, 8 vehicle guides, 3 protection guides, 3 add-on guides, 6 core policies and 36 operational policies. Edit these files directly. scripts/build_corpus.py reproduces the original corpus and overwrites matching documents; do not run it to index edits.

150-word windows overlap by 30 words. Short policy documents stay intact, so exceptions remain beside the rule. MiniLM runs on CPU and creates normalized embeddings. SQLite stores float32 vectors and provenance; NumPy performs exact cosine search. This is a small CPU vector store, with linear scan appropriate for this corpus. It requires no separate database service.

The indexer hashes each document and chunking version, skips unchanged sources, replaces changed chunks, and removes deleted sources in one SQLite transaction. Failed embedding rolls back all changes. Changing embedding models requires a new index path. Reindex with python -m scripts.index_documents. Every successful build changes the revision, invalidating cached results.

## Query path and streaming

ConversationManager.prepare_messages embeds each new query and requests top-4 results, retaining cosine scores >= RAG_MIN_SCORE (default 0.40). This threshold is a heuristic, not a calibrated probability. An empty accepted set produces explicit no-match instructions. The LLM must acknowledge missing evidence and continue useful rental conversation without inventing business facts.

The prompt uses retrieved facts rather than Assignment 1's hardcoded business catalogue. Previous answers are not treated as authoritative sources. Source text is JSON-quoted untrusted data. The bonus chosen is visible citations: the model is instructed to write [source-filename.md] beside supported claims, rendered through the existing chat message content. Citations are model-generated and are not independently verified.

The WebSocket request/event schemas and token streaming are unchanged. Retrieval happens before the first generation token. Existing end_turn latency metrics still describe generation only; retrieval_ms is logged separately. User-perceived first-token latency is retrieval plus generation TTFT and transport time.

## Context budget

The default Qwen context window is explicitly configured as 8192 tokens in Ollama, with 512 output tokens and a 256-token safety reserve. The prompt budget is at most 7168. For Qwen's byte-level tokenizer, UTF-8 bytes plus 32 tokens per message and 32 final framing tokens form a deliberately conservative bound. Retain mandatory instructions and latest question, add complete retrieved chunks in score order, then fit recent history. Oversized user input is truncated with an explicit disclosure. Oversized chunks and old history are omitted, never silently sent beyond the budget. A replacement tokenizer needs a compatible bound or exact token counter. Long-range extracted Assignment 1 state is not injected because it contains hardcoded prices and assistant-derived facts.

## Responsiveness and failure handling

A single dedicated worker protects the embedding model and cache while keeping the event loop responsive. Lookup has a 900 ms deadline, including loading and disk access. A still-running timed-out lookup holds its slot; concurrent callers receive a busy fallback immediately. This bounds work and preserves responsiveness, but under load some users receive a lookup-unavailable response rather than grounded retrieval. Startup attempts a warmup. A 128-entry LRU cache keys exact queries by index revision, k and threshold. Case and whitespace are preserved.

Missing/corrupt indexes, embedding errors and timeouts become unavailable results. Native inference threads cannot be forcibly killed; a permanently stuck worker keeps retrieval unavailable until restart, while chat remains operational. Per-session locks preserve turn order; generation remains asynchronously streamed.

## Validation and viva

```powershell
python -m pytest tests/test_rag.py tests/test_memory.py -q
python -m scripts.benchmark_retrieval
```

Tests cover incremental updates/deletion, cache invalidation, no-match handling, missing store, timeout, bounded concurrency, event-loop responsiveness, Unicode context overflow, chunk overlap and the unchanged WebSocket token/end-turn contract. Test embeddings are deterministic doubles; they do not establish semantic quality. Existing guardrail and generation tests require a running Ollama model.

For the walkthrough inspect app/retrieval.py, app/rag_prompt.py and ConversationManager.prepare_messages. The exact generation prompt is SYSTEM in app/rag_prompt.py plus serialized retrieved passages and admitted dialogue. Try: "What happens if I return 90 minutes late?", "Can I cross an international border?", "What are Airport opening hours?", and "Do you rent helicopters?". Rename the index to demonstrate unavailable lookup; add a long user message to demonstrate bounded context. Change a policy and rerun indexing to demonstrate updates.

## Retrieval benchmark

Measured on Windows 11 with local all-MiniLM-L6-v2, two PyTorch CPU threads, 60 documents / 60 chunks, and networking disabled (HF_HUB_OFFLINE=1). Thirty queries across six policy topics:

| Retrieval path | Median | p95 |
| --- | ---: | ---: |
| Warmed model, uncached query | 22.80 ms | 32.51 ms |
| Cached result | 1.52 ms | 2.44 ms |

Cold initialization plus first lookup: **16,722 ms**. This is separate from steady-state latency and explains the startup warmup; requests arriving before initialization completes receive a graceful unavailable/busy fallback. The warmed p95 meets the under-one-second target on this machine. These numbers exclude LLM generation and do not establish end-to-end response latency. Raw measurements are in data/retrieval_benchmark.json. Reproduce with python -m scripts.benchmark_retrieval.

Validation: **21 tests passed** in the project virtual environment. These include streaming with a mocked generator; live Ollama answer quality and full user-perceived latency remain to be checked with the local generation model running. Run python -m scripts.evaluate_retrieval for the small semantic smoke set; this is not a held-out evaluation.

Semantic smoke result: **7/7 passed**: all five policy questions retrieved their intended source (rank 1), and both unrelated questions returned no accepted matches. Raw scores and source lists are in data/retrieval_evaluation.json. The set is intentionally small and does not prove general retrieval accuracy. Ollama was not listening on localhost:11434 during validation, so live answer generation was not measured.
