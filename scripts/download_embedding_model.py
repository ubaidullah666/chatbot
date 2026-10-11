"""One-time provisioning only; server and indexer never download models."""
from huggingface_hub import snapshot_download
import os

if __name__ == '__main__':
    snapshot_download('sentence-transformers/all-MiniLM-L6-v2', local_dir=os.getenv('RAG_MODEL', 'models/all-MiniLM-L6-v2'),
                      allow_patterns=['*.json', '*.txt', '*.safetensors', '1_Pooling/*'])
