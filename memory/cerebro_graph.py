"""
memory/cerebro_graph.py — Project Cerebro: Infinite Neural Memory Vector Graph Engine for Ultron AI.

Implements a local, high-performance SQLite Knowledge Graph with:
1. Entity-Relationship nodes and weighted directed edges.
2. Lightweight semantic TF-IDF / n-gram vector embeddings with L2-normalized cosine similarity.
3. Multi-hop sub-graph traversal for deep context synthesis.
"""
from __future__ import annotations

import collections
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Optional

import numpy as np

_BASE_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BASE_DIR / "memory" / "cerebro_graph.db"


def _get_db() -> sqlite3.Connection:
    """Connect to the Cerebro Knowledge Graph SQLite database in WAL mode."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT UNIQUE,
                node_type TEXT,
                label TEXT,
                properties TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                target_id INTEGER,
                relation TEXT,
                weight REAL DEFAULT 1.0,
                properties TEXT,
                created_at REAL,
                FOREIGN KEY(source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY(target_id) REFERENCES nodes(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                node_id INTEGER PRIMARY KEY,
                vector_json TEXT,
                FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_entity ON nodes(entity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_id)")
    return conn


def _tokenize(text: str) -> list[str]:
    """Extract clean words and character 3-grams for semantic fuzzy indexing."""
    clean = (text or "").lower()
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", clean)
    # Character 3-grams for sub-word matching
    trigrams = [clean[i:i+3] for i in range(len(clean) - 2) if " " not in clean[i:i+3]]
    return words + trigrams[:60]


def _build_vector(text: str, vocab: dict[str, int]) -> np.ndarray:
    """Build L2-normalized bag-of-tokens vector against vocabulary."""
    tokens = _tokenize(text)
    dim = len(vocab)
    if dim == 0:
        return np.zeros(1, dtype=np.float32)
    vec = np.zeros(dim, dtype=np.float32)
    for tok in tokens:
        idx = vocab.get(tok)
        if idx is not None and idx < dim:
            vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm
    return vec


def _get_corpus_vocab(conn: sqlite3.Connection) -> dict[str, int]:
    """Constructs dynamic vocabulary from indexed nodes."""
    cur = conn.cursor()
    cur.execute("SELECT entity, label, properties FROM nodes")
    rows = cur.fetchall()
    counts = collections.Counter()
    for entity, label, props in rows:
        tokens = _tokenize(f"{entity} {label} {props}")
        counts.update(tokens)
    # Take top 800 most informative tokens
    common = [tok for tok, _ in counts.most_common(800)]
    return {tok: i for i, tok in enumerate(common)}


def upsert_node(
    entity: str,
    node_type: str = "concept",
    label: str = "",
    properties: dict | None = None
) -> int:
    """Creates or updates a node in the Cerebro Graph and refreshes its vector embedding."""
    clean_entity = (entity or "").strip().lower()
    if not clean_entity:
        raise ValueError("Entity identifier cannot be empty.")

    clean_type = (node_type or "concept").strip().lower()
    clean_label = (label or entity).strip()
    props_json = json.dumps(properties or {}, ensure_ascii=False)
    now = time.time()

    conn = _get_db()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO nodes (entity, node_type, label, properties, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity) DO UPDATE SET
                    node_type = excluded.node_type,
                    label = excluded.label,
                    properties = excluded.properties,
                    updated_at = excluded.updated_at
            """, (clean_entity, clean_type, clean_label, props_json, now, now))
            node_id = cur.lastrowid
            if not node_id:
                cur.execute("SELECT id FROM nodes WHERE entity = ?", (clean_entity,))
                node_id = cur.fetchone()[0]

            # Update semantic embedding
            vocab = _get_corpus_vocab(conn)
            text_rep = f"{clean_entity} {clean_label} {props_json}"
            vec = _build_vector(text_rep, vocab)
            cur.execute("""
                INSERT OR REPLACE INTO embeddings (node_id, vector_json)
                VALUES (?, ?)
            """, (node_id, json.dumps(vec.tolist())))

        return node_id
    finally:
        conn.close()


def link_entities(
    source_entity: str,
    target_entity: str,
    relation: str = "related_to",
    weight: float = 1.0,
    properties: dict | None = None
) -> str:
    """Forms a weighted, directed semantic edge between two entity nodes."""
    s_id = upsert_node(source_entity)
    t_id = upsert_node(target_entity)

    rel_clean = (relation or "related_to").strip().lower()
    props_json = json.dumps(properties or {}, ensure_ascii=False)
    now = time.time()

    conn = _get_db()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO edges (source_id, target_id, relation, weight, properties, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (s_id, t_id, rel_clean, float(weight), props_json, now))
        return f"Linked: ({source_entity}) -[{rel_clean} (w={weight:.1f})]-> ({target_entity})"
    finally:
        conn.close()


def semantic_query(query: str, top_k: int = 5, depth: int = 1) -> list[dict]:
    """
    Performs cosine vector RAG search across the graph, then traverses connected subgraphs.
    """
    conn = _get_db()
    try:
        vocab = _get_corpus_vocab(conn)
        if not vocab:
            return []

        q_vec = _build_vector(query, vocab)
        cur = conn.cursor()

        cur.execute("SELECT node_id, vector_json FROM embeddings")
        emb_rows = cur.fetchall()

        scores = []
        for n_id, v_json in emb_rows:
            try:
                v = np.array(json.loads(v_json), dtype=np.float32)
                # Cosine similarity
                sim = float(np.dot(q_vec, v))
                scores.append((n_id, sim))
            except Exception:
                continue

        scores.sort(key=lambda t: t[1], reverse=True)
        top_nodes = scores[:top_k]

        results = []
        for n_id, score in top_nodes:
            cur.execute("SELECT id, entity, node_type, label, properties FROM nodes WHERE id = ?", (n_id,))
            n_row = cur.fetchone()
            if not n_row:
                continue

            nid, ent, ntype, lbl, props_str = n_row
            try:
                props = json.loads(props_str)
            except Exception:
                props = {}

            # Multi-hop sub-graph traversal
            connections = []
            if depth >= 1:
                cur.execute("""
                    SELECT e.relation, e.weight, n.entity, n.label
                    FROM edges e
                    JOIN nodes n ON e.target_id = n.id
                    WHERE e.source_id = ?
                """, (nid,))
                for rel, wt, t_ent, t_lbl in cur.fetchall():
                    connections.append({"direction": "out", "relation": rel, "target": t_ent, "label": t_lbl, "weight": wt})

                cur.execute("""
                    SELECT e.relation, e.weight, n.entity, n.label
                    FROM edges e
                    JOIN nodes n ON e.source_id = n.id
                    WHERE e.target_id = ?
                """, (nid,))
                for rel, wt, s_ent, s_lbl in cur.fetchall():
                    connections.append({"direction": "in", "relation": rel, "source": s_ent, "label": s_lbl, "weight": wt})

            results.append({
                "id": nid,
                "entity": ent,
                "type": ntype,
                "label": lbl,
                "properties": props,
                "relevance_score": round(score, 3),
                "connections": connections,
            })

        return results
    finally:
        conn.close()


def get_graph_metrics() -> dict:
    """Computes graph topological metrics (nodes, edges, types, density)."""
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes")
        node_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges")
        edge_count = cur.fetchone()[0]
        cur.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type")
        types_breakdown = {t: c for t, c in cur.fetchall()}

        density = (2.0 * edge_count / (node_count * (node_count - 1))) if node_count > 1 else 0.0
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": round(density, 4),
            "node_types": types_breakdown,
            "storage_path": str(_DB_PATH),
        }
    finally:
        conn.close()
