import asyncio
import time
import numpy as np
import pytest
from app.config import settings
from app.retrieval import Retriever, RetrievalResult, Hit, index_documents, chunks
from app.rag_prompt import build_rag_messages, cost


class FakeEmbedder:
    def encode(self, texts):
        return np.array([[1., 0.] if 'car' in t else [0., 1.] for t in texts], dtype='float32')


def test_incremental_delete_cache_and_no_match(tmp_path):
    corpus = tmp_path / 'docs'
    corpus.mkdir()
    doc = corpus / 'car.md'
    doc.write_text('car rental costs 45 dollars')
    database = tmp_path / 'index.sqlite3'
    embedder = FakeEmbedder()
    assert index_documents(corpus, database, embedder, settings.RAG_MODEL)['changed'] == 1
    assert index_documents(corpus, database, embedder, settings.RAG_MODEL)['changed'] == 0
    retriever = Retriever(database, embedder)
    assert retriever.search('car').hits[0].source == 'car.md'
    assert retriever.search('penguin').status == 'no_match'
    doc.write_text('car price changed to 50 dollars')
    index_documents(corpus, database, embedder, settings.RAG_MODEL)
    assert '50' in retriever.search('car').hits[0].text
    doc.unlink()
    index_documents(corpus, database, embedder, settings.RAG_MODEL)
    assert retriever.search('car').status == 'no_match'


@pytest.mark.asyncio
async def test_failure_timeout_concurrency(tmp_path, monkeypatch):
    retriever = Retriever(tmp_path / 'missing')
    assert (await retriever.retrieve('car')).status == 'unavailable'
    monkeypatch.setattr(settings, 'RAG_TIMEOUT', 0.02)
    def slow(query):
        time.sleep(0.15)
        return RetrievalResult(status='no_match')
    monkeypatch.setattr(retriever, 'search', slow)
    ticks = []
    async def heartbeat():
        for _ in range(5):
            await asyncio.sleep(0.005)
            ticks.append(1)
    results = await asyncio.gather(retriever.retrieve('car'), retriever.retrieve('car'), heartbeat())
    assert results[0].status == 'unavailable'
    assert results[1].status == 'busy'
    assert len(ticks) == 5
    assert (await retriever.retrieve('car')).status == 'busy'
    await asyncio.sleep(0.16)
    assert not retriever.busy.locked()


def test_budget_and_grounding():
    result = RetrievalResult((Hit('policy.md', 0, 'Car deposit is $200.', .8),), 'ok')
    history = [{'role': 'user', 'content': 'What is the deposit?'}]
    messages = build_rag_messages(history, result)
    assert 'policy.md' in messages[0]['content']
    assert 'Car deposit is $200.' in messages[0]['content']
    huge = [{'role': 'user', 'content': '你好' * 20000}]
    messages = build_rag_messages(huge, result)
    assert cost(messages) <= min(settings.MAX_PROMPT_TOKENS, settings.CONTEXT_WINDOW-settings.MAX_OUTPUT_TOKENS-256)
    assert 'truncated' in messages[-1]['content']


def test_corpus_and_chunk_overlap():
    from pathlib import Path
    assert 50 <= len(list(Path('data/documents').glob('*.md'))) <= 100
    windows = list(chunks(' '.join(str(i) for i in range(400))))
    assert windows[0].split()[-30:] == windows[1].split()[:30]


def test_failed_reindex_preserves_previous_index(tmp_path):
    corpus = tmp_path / 'docs'
    corpus.mkdir()
    doc = corpus / 'car.md'
    doc.write_text('car original policy')
    database = tmp_path / 'index.sqlite3'
    index_documents(corpus, database, FakeEmbedder(), settings.RAG_MODEL)
    doc.write_text('car replacement policy')
    class BrokenEmbedder:
        def encode(self, texts):
            raise RuntimeError('embedding failed')
    with pytest.raises(RuntimeError):
        index_documents(corpus, database, BrokenEmbedder(), settings.RAG_MODEL)
    assert 'original' in Retriever(database, FakeEmbedder()).search('car').hits[0].text


@pytest.mark.asyncio
async def test_embedding_failure_becomes_fallback(tmp_path):
    corpus = tmp_path / 'docs'
    corpus.mkdir()
    (corpus / 'car.md').write_text('car policy')
    database = tmp_path / 'index.sqlite3'
    index_documents(corpus, database, FakeEmbedder(), settings.RAG_MODEL)
    class BrokenEmbedder:
        def encode(self, texts):
            raise RuntimeError('embedding failed')
    assert (await Retriever(database, BrokenEmbedder()).retrieve('car')).status == 'unavailable'


def test_websocket_contract_with_rag(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.retrieval import retriever
    from app.llm_engine import llm_engine
    async def retrieve(query):
        return RetrievalResult((Hit('deposit.md', 0, 'Deposit is $200', .9),), 'ok')
    async def stream(messages):
        assert 'deposit.md' in messages[0]['content']
        yield 'Deposit is $200 [deposit.md].', None
    monkeypatch.setattr(retriever, 'retrieve', retrieve)
    monkeypatch.setattr(llm_engine, 'stream_chat', stream)
    with TestClient(app).websocket_connect('/ws/chat') as ws:
        ws.send_json({'type': 'user_message', 'content': 'Deposit?'})
        token = ws.receive_json()
        end = ws.receive_json()
        assert set(token) == {'type', 'session_id', 'delta'}
        assert end['type'] == 'end_turn'
        assert end['full_response'] == token['delta']
        ws.send_json({'type': 'ping'})
        assert ws.receive_json() == {'type': 'pong'}
