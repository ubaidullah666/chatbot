"""Small transparent semantic smoke set, not a held-out quality benchmark."""
import json
from pathlib import Path
from app.retrieval import Retriever

CASES = [
    ('What is the fee if I return a car 90 minutes late?', 'late-return.md'),
    ('May my dog travel in the rental car?', 'pets.md'),
    ('When does the Airport desk open?', 'airport-hours.md'),
    ('Can I drive across an international border?', 'cross-border.md'),
    ('What happens if I lose my car keys?', 'lost-keys.md'),
    ('Explain photosynthesis in plants.', None),
    ('Who won the football world cup?', None),
]

if __name__ == '__main__':
    retriever = Retriever()
    rows = []
    for query, expected in CASES:
        result = retriever.search(query)
        sources = [h.source for h in result.hits]
        rows.append({'query': query, 'expected': expected, 'sources': sources,
                     'scores': [round(h.score, 4) for h in result.hits],
                     'passed': expected in sources if expected else not sources})
    Path('data/retrieval_evaluation.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))
