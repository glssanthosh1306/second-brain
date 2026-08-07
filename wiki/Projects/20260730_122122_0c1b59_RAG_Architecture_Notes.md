---
category: Projects
date: '2026-07-30T12:21:22.573402+05:30'
id: 20260730_122122_0c1b59
source: cli
summary: Retrieval-Augmented Generation relies on high-quality text chunking and dense
  vector embeddings.
tags:
- RAG
- Architecture
- Notes
title: RAG Architecture Notes
---

# File: rag_architecture_notes.txt

RAG Architecture Notes:
Retrieval-Augmented Generation relies on high-quality text chunking, dense vector embeddings (e.g., sentence-transformers all-MiniLM-L6-v2), and fast similarity search (cosine distance / FAISS).
Grounding system prompts with retrieved context reduces model hallucinations significantly.