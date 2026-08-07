---
created: '2026-07-30T12:20:49.169259+05:30'
id: 20260730_122049_84acb3
links:
- 20260730_122049_84acb3
- 20260730_122122_0c1b59
- 20260730_130014_c1953d
- 20260730_122122_0c1b59
- 20260730_130014_c1953d
para: Resources
summary: Notes on RAG architecture, including text chunking, vector embeddings, and
  similarity search.
tags:
- rag
- architecture
- notes
---

# File: rag_architecture_notes.txt

RAG Architecture Notes:
Retrieval-Augmented Generation relies on high-quality text chunking, dense vector embeddings (e.g., sentence-transformers all-MiniLM-L6-v2), and fast similarity search (cosine distance / FAISS).
Grounding system prompts with retrieved context reduces model hallucinations significantly.