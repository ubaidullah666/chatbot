"""Local CPU embeddings and transactional SQLite/NumPy exact cosine vector store."""
import asyncio
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import sqlite3
import threading
import time

from app.config import settings


class LocalEmbedder:
    def __init__(self, model=None):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(2)
        self.model = SentenceTransformer(model or settings.RAG_MODEL, device="cpu", local_files_only=True)
        self.model.max_seq_length = 256

    def encode(self, texts):
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def chunks(text, size=150, overlap=30):
    """Small overlapping word windows, safe for typical MiniLM document passages."""
    words = text.split()
    for start in range(0, len(words), size - overlap):
        yield " ".join(words[start:start + size])
        if start + size >= len(words):
            break


def index_documents(root, database, embedder, model_id):
    import numpy as np
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS chunks (source TEXT, ordinal INTEGER, digest TEXT, text TEXT, vector BLOB, PRIMARY KEY(source, ordinal))")
        old = db.execute("SELECT value FROM metadata WHERE key='model'").fetchone()
        if old and old[0] != model_id:
            raise ValueError("Embedding model changed: use a new index path.")
        changed = 0
        sources = []
        for path in sorted(Path(root).rglob('*')):
            if path.suffix not in {'.md', '.txt'}:
                continue
            source = path.relative_to(root).as_posix()
            sources.append(source)
            text = path.read_text(encoding='utf-8')
            digest = hashlib.sha256(('chunk-v1:' + text).encode()).hexdigest()
            old = db.execute("SELECT digest FROM chunks WHERE source=? LIMIT 1", (source,)).fetchone()
            if old and old[0] == digest:
                continue
            passages = list(chunks(text))
            vectors = embedder.encode(passages) if passages else []
            db.execute("DELETE FROM chunks WHERE source=?", (source,))
            for i, (passage, vector) in enumerate(zip(passages, vectors)):
                db.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", (source, i, digest, passage, np.asarray(vector, dtype='float32').tobytes()))
            changed += 1
        for (source,) in db.execute("SELECT DISTINCT source FROM chunks").fetchall():
            if source not in sources:
                db.execute("DELETE FROM chunks WHERE source=?", (source,))
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('model',?)", (model_id,))
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('revision',?)", (str(time.time_ns()),))
        return {'documents': len(sources), 'changed': changed, 'chunks': db.execute('SELECT count(*) FROM chunks').fetchone()[0]}


@dataclass(frozen=True)
class Hit:
    source: str
    ordinal: int
    text: str
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    hits: tuple = ()
    status: str = 'unavailable'


class Retriever:
    def __init__(self, database=None, embedder=None):
        self.database = database or settings.RAG_INDEX
        self.embedder = embedder
        self.cache = OrderedDict()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='rag')
        self.busy = threading.Lock()

    def search(self, query, k=4):
        import numpy as np
        if k < 3:
            raise ValueError('top-k must be at least 3')
        with sqlite3.connect(Path(self.database).resolve().as_uri() + '?mode=ro', uri=True, timeout=0.1) as db:
            revision = db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
            model = db.execute("SELECT value FROM metadata WHERE key='model'").fetchone()[0]
            if model != settings.RAG_MODEL:
                raise ValueError('Index embedding model mismatch')
            key = (revision, query, k, settings.RAG_MIN_SCORE)
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            rows = db.execute('SELECT source,ordinal,text,vector FROM chunks ORDER BY source,ordinal').fetchall()
        if not rows:
            return RetrievalResult(status='no_match')
        if self.embedder is None:
            self.embedder = LocalEmbedder()
        vector = self.embedder.encode([query])[0]
        matrix = np.stack([np.frombuffer(r[3], dtype='float32') for r in rows])
        scores = matrix @ vector
        hits = tuple(Hit(*rows[i][:3], float(scores[i])) for i in np.argsort(-scores)[:k] if scores[i] >= settings.RAG_MIN_SCORE)
        result = RetrievalResult(hits, 'ok' if hits else 'no_match')
        self.cache[key] = result
        while len(self.cache) > 128:
            self.cache.popitem(last=False)
        return result

    async def retrieve(self, query):
        # Admission is bounded: a timed-out native call retains its slot until it exits.
        # No unbounded executor queue and no blocking of the event loop.
        if not self.busy.acquire(blocking=False):
            return RetrievalResult(status='busy')
        def work():
            try:
                return self.search(query)
            finally:
                self.busy.release()
        started = time.perf_counter()
        try:
            future = asyncio.get_running_loop().run_in_executor(self.pool, work)
            # Consume late failures after a caller times out or disconnects.
            future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
            return await asyncio.wait_for(asyncio.shield(future), settings.RAG_TIMEOUT)
        except Exception:
            logging.getLogger(__name__).warning('Retrieval unavailable', exc_info=True)
            return RetrievalResult(status='unavailable')
        finally:
            logging.getLogger(__name__).info('retrieval_ms=%.2f', (time.perf_counter() - started) * 1000)


retriever = Retriever()
