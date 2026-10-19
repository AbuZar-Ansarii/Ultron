"""
actions/cerebro_memory.py — Project Cerebro: Infinite Neural Memory Vector Graph for Ultron AI.

Exposes Ultron's multi-hop semantic vector knowledge graph. Performs RAG cosine recall,
associates connected knowledge nodes, indexes flight details/personal projects/code snippets,
and visualizes semantic subgraphs.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from memory.cerebro_graph import (
    upsert_node,
    link_entities,
    semantic_query,
    get_graph_metrics,
)


def recall_graph(query: str, top_k: int = 5) -> str:
    """Performs semantic RAG vector search across Cerebro Knowledge Graph."""
    clean_q = (query or "").strip()
    if not clean_q:
        return "Please specify a query concept to search the Cerebro Neural Graph."

    results = semantic_query(clean_q, top_k=top_k, depth=1)
    if not results:
        return f"No semantic neural graph nodes found matching '{clean_q}' in Cerebro."

    lines = [
        f"[CEREBRO] NEURAL GRAPH RAG - Query: '{clean_q}'",
        f"Retrieved {len(results)} top semantic nodes with topological connections:",
        "=" * 55,
    ]

    for item in results:
        ent = item["entity"]
        lbl = item["label"]
        score = item["relevance_score"]
        props = item["properties"]
        conns = item["connections"]

        props_preview = ", ".join(f"{k}: {v}" for k, v in list(props.items())[:4]) if props else "No custom properties"
        lines.append(f"* [{item['type'].upper()}] {lbl} (Entity: @{ent} | Relevance: {score:.2f})")
        lines.append(f"    |- Attributes: {props_preview}")

        if conns:
            lines.append("    +- Topological Connections:")
            for c in conns[:4]:
                if c["direction"] == "out":
                    lines.append(f"        -> -[{c['relation']}]-> {c['label']} (@{c['target']})")
                else:
                    lines.append(f"        <- <-[{c['relation']}]- {c['label']} (@{c['source']})")
        else:
            lines.append("    +- Isolated Node (No active edges)")
        lines.append("")

    lines.append("=" * 55)
    return "\n".join(lines)


def store_entity_node(
    entity: str,
    node_type: str = "concept",
    label: str = "",
    properties: dict | None = None,
    link_to: str = "",
    relation: str = "related_to"
) -> str:
    """Stores an entity node and optionally links it to another node."""
    clean_ent = (entity or "").strip().lower()
    if not clean_ent:
        return "Entity identifier is required (e.g. 'flight:del_bom', 'project:ultron')."

    node_id = upsert_node(
        entity=clean_ent,
        node_type=node_type,
        label=label or entity,
        properties=properties
    )

    msg = f"[CEREBRO] Node Indexed [ID #{node_id}]: @{clean_ent} ({node_type.upper()})"
    if link_to:
        link_msg = link_entities(clean_ent, link_to.strip().lower(), relation=relation)
        msg += f"\n   +- {link_msg}"

    return msg


def render_subgraph(entity: str) -> str:
    """Renders a textual/ASCII graph visualization of an entity and all its neighbors."""
    clean_ent = (entity or "").strip().lower()
    if not clean_ent:
        return "Specify entity to render subgraph for."

    results = semantic_query(clean_ent, top_k=1, depth=2)
    if not results:
        return f"Entity '@{clean_ent}' not found in Cerebro Knowledge Graph."

    root = results[0]
    lines = [
        f"[CEREBRO] TOPOLOGICAL SUBGRAPH: @{root['entity']}",
        f"Class: {root['type'].upper()} | Label: '{root['label']}'",
        "-" * 55,
        f"(@{root['entity']})",
    ]

    conns = root.get("connections", [])
    if not conns:
        lines.append("   +- [No connected edges]")
    else:
        for i, c in enumerate(conns):
            prefix = "   |-" if i < len(conns) - 1 else "   +-"
            if c["direction"] == "out":
                lines.append(f"{prefix}==[{c['relation']}]==> (@{c['target']}) \"{c['label']}\"")
            else:
                lines.append(f"{prefix}<==[{c['relation']}]== (@{c['source']}) \"{c['label']}\"")

    lines.append("-" * 55)
    return "\n".join(lines)


def render_metrics() -> str:
    """Renders high-level metrics for the Cerebro neural graph."""
    m = get_graph_metrics()
    types_str = ", ".join(f"{k}: {v}" for k, v in m["node_types"].items()) or "None"
    return (
        f"[CEREBRO] KNOWLEDGE GRAPH METRICS\n"
        f"=" * 55 + "\n"
        f"* Total Concept Nodes:  {m['node_count']}\n"
        f"* Semantic Edges:       {m['edge_count']}\n"
        f"* Network Density:      {m['density']:.4f}\n"
        f"* Node Type Breakdown:  {types_str}\n"
        f"* Local Vector Engine:  TF-IDF L2 Cosine (<1ms RAG latency)\n"
        f"* Storage Location:     {m['storage_path']}\n"
        f"=" * 55
    )


def cerebro_memory(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for cerebro_memory tool."""
    action = (parameters.get("action") or "query").lower().strip()
    query = parameters.get("query") or parameters.get("concept") or ""
    entity = parameters.get("entity") or query
    node_type = parameters.get("node_type") or "concept"
    label = parameters.get("label") or entity
    props = parameters.get("properties")
    target = parameters.get("target_entity") or ""
    relation = parameters.get("relation") or "related_to"

    if isinstance(props, str):
        try:
            props = json.loads(props)
        except Exception:
            props = {"raw": props}

    if player:
        try:
            player.write_log(f"[Cerebro] Executing {action} (Entity: {entity[:30]})")
        except Exception:
            pass

    try:
        if action in ("query", "recall", "search", "find", "ask"):
            return recall_graph(query=query or entity)
        elif action in ("remember", "store", "upsert", "add"):
            return store_entity_node(
                entity=entity,
                node_type=node_type,
                label=label,
                properties=props,
                link_to=target,
                relation=relation
            )
        elif action in ("link", "connect", "associate"):
            if not target:
                return "Connecting entities requires both 'entity' and 'target_entity'."
            return link_entities(entity, target, relation=relation)
        elif action in ("subgraph", "graph", "tree", "visualize"):
            return render_subgraph(entity)
        elif action in ("metrics", "stats", "status"):
            return render_metrics()
        else:
            return (
                f"Unknown Cerebro action '{action}'. "
                "Available actions: query, remember, link, subgraph, metrics."
            )
    except Exception as e:
        return f"Cerebro Neural Memory Graph error: {e}"


TOOL = {
    "name": "cerebro_memory",
    "description": (
        "Project Cerebro: Infinite Neural Memory Vector Graph & Local RAG Engine for Ultron. "
        "Performs semantic vector recall across past context, flight bookings, user preferences, and code concepts (query), "
        "stores structured entities with custom properties (remember), "
        "connects two entities with weighted directed semantic relations (link), "
        "renders topological ASCII subgraphs for an entity (subgraph), "
        "and reviews knowledge graph metrics (metrics). "
        "Use whenever user asks to remember structured facts, query their history semantically, or examine connected relationships."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "query (semantic RAG recall) | remember (store entity node) | link (connect two concepts) | subgraph (ASCII graph) | metrics (graph metrics)"
            },
            "query": {
                "type": "STRING",
                "description": "Semantic search query or concept name (e.g. 'plane tickets to Mumbai', 'authentication bug', 'user preferences')"
            },
            "entity": {
                "type": "STRING",
                "description": "Entity identifier (e.g. 'flight:del_bom', 'user:abuzar', 'project:ultron')"
            },
            "node_type": {
                "type": "STRING",
                "description": "Category: 'user', 'project', 'flight', 'code', 'task', 'preference', 'device'. Default: 'concept'"
            },
            "label": {
                "type": "STRING",
                "description": "Human-readable label or title for this node"
            },
            "target_entity": {
                "type": "STRING",
                "description": "Target entity when creating a link (e.g. 'city:mumbai')"
            },
            "relation": {
                "type": "STRING",
                "description": "Semantic relationship name (e.g. 'destination', 'booked_by', 'builds', 'prefers'). Default: 'related_to'"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": cerebro_memory,
}
