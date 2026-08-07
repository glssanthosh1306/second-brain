---
category: Resources
date: '2026-07-30T12:20:49.173791+05:30'
id: 20260730_122049_df4d03
source: cli
summary: Cosine similarity function using numpy
tags:
- numpy
- python
- embedding
- utils
title: embedding_utils.py
---

# File: embedding_utils.py

import numpy as np

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))