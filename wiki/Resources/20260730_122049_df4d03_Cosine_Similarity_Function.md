---
category: Resources
date: '2026-07-30T12:20:49.173791+05:30'
id: 20260730_122049_df4d03
source: cli
summary: Function to calculate cosine similarity between two vectors.
tags:
- numpy
- cosine similarity
- embedding
title: Cosine Similarity Function
---

# File: embedding_utils.py

import numpy as np

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))