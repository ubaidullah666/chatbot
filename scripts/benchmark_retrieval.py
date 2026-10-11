"""Real local-model retrieval timing; never substitute mocked embeddings."""
import json
import platform
import time
from pathlib import Path
import numpy as np
from app.retrieval import Retriever

QUERIES = ['What is the late return fee?', 'Can I take a pet?', 'What are airport opening hours?',
           'How much does an SUV cost?', 'Are cross border trips allowed?', 'What if I lose the keys?']

if __name__ == '__main__':
    retriever = Retriever()
    started = time.perf_counter()
    retriever.search(QUERIES[0])
    cold = (time.perf_counter() - started) * 1000
    uncached, cached = [], []
    for _ in range(5):
        for query in QUERIES:
            retriever.cache.clear()
            started = time.perf_counter()
            retriever.search(query)
            uncached.append((time.perf_counter() - started) * 1000)
            started = time.perf_counter()
            retriever.search(query)
            cached.append((time.perf_counter() - started) * 1000)
    result = {'platform': platform.platform(), 'cold_ms': cold, 'runs': len(uncached),
              'uncached_p50_ms': float(np.median(uncached)), 'uncached_p95_ms': float(np.percentile(uncached,95)),
              'cached_p50_ms': float(np.median(cached)), 'cached_p95_ms': float(np.percentile(cached,95))}
    Path('data/retrieval_benchmark.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
