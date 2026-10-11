import argparse
import json
from app.config import settings
from app.retrieval import LocalEmbedder, index_documents

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--documents', default='data/documents')
    parser.add_argument('--index', default=settings.RAG_INDEX)
    args = parser.parse_args()
    print(json.dumps(index_documents(args.documents, args.index, LocalEmbedder(), settings.RAG_MODEL), indent=2))
