"""Phase 3 – build_graph.py
Generate a graph representation from the linked wiki markdown notes.
Outputs:
  - data/graph.json          (structured data)
  - static/graph.html        (self-contained interactive visualisation)
"""

import json
from pathlib import Path
import frontmatter

# Paths (keep in sync with config.py)
ROOT = Path(__file__).parent
WIKI_DIR = ROOT / "wiki"
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
OUTPUT_PATH = DATA_DIR / "graph.json"
HTML_PATH = STATIC_DIR / "graph.html"


def scan_wiki_notes(wiki_dir: Path) -> list[Path]:
    """Return a list of all markdown note files under the PARA folders."""
    return list(wiki_dir.rglob("*.md"))


def parse_wiki_note(path: Path) -> dict:
    """Load a markdown file with front-matter and return a dict with metadata and content."""
    post = frontmatter.load(path)
    meta = post.metadata or {}
    return {
        "id": meta.get("id"),
        "para": meta.get("para"),
        "tags": meta.get("tags", []),
        "summary": meta.get("summary", ""),
        "links": meta.get("links", []),
        "content": post.content,
        "path": str(path),
    }


def note_to_node(note: dict) -> dict:
    """Convert a note dict into a node dict for the graph JSON.
    Node label uses the full summary as requested.
    """
    preview = note["content"].strip().replace("\n", " ")[:200]
    return {
        "id": note["id"],
        "label": note.get("summary", preview),
        "para": note.get("para"),
        "tags": note.get("tags", []),
        "content_preview": preview,
        "group": note.get("para"),
    }


def links_to_edges(note: dict) -> list[dict]:
    """Create edge dicts from a note's `links` front-matter list."""
    edges = []
    source = note["id"]
    for target in note.get("links", []):
        if not target:
            continue
        # Skip self-referencing edges
        if target == source:
            continue
        edges.append({
            "source": source,
            "target": target,
            "weight": 1.0,
            "type": "semantic_similarity",
        })
    return edges


def build_graph(wiki_dir: Path) -> dict:
    """Assemble nodes and edges from all notes, deduplicate, and return a graph dict."""
    notes = [parse_wiki_note(p) for p in scan_wiki_notes(wiki_dir)]

    # --- Deduplicate nodes by ID (prefer the version that has a PARA group) ---
    node_map: dict[str, dict] = {}
    for n in notes:
        if not n["id"]:
            continue
        node = note_to_node(n)
        nid = node["id"]
        if nid not in node_map:
            node_map[nid] = node
        else:
            # Keep the one with a PARA group if the existing one lacks it
            if node.get("group") and not node_map[nid].get("group"):
                node_map[nid] = node
    nodes = list(node_map.values())

    # --- Collect edges, deduplicate, skip self-refs ---
    valid_ids = {n["id"] for n in nodes}
    edge_set: set[tuple[str, str]] = set()
    edges: list[dict] = []
    for note in notes:
        for e in links_to_edges(note):
            # Only keep edges where both endpoints exist as nodes
            if e["source"] not in valid_ids or e["target"] not in valid_ids:
                continue
            key = tuple(sorted([e["source"], e["target"]]))
            if key in edge_set:
                continue
            edge_set.add(key)
            edges.append(e)

    return {"nodes": nodes, "edges": edges}


def export_graph(graph: dict, output_path: Path):
    """Write the graph dict as pretty-printed JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Graph JSON written to {output_path}")
    print(f"    Nodes: {len(graph['nodes'])}  |  Edges: {len(graph['edges'])}")


def export_html(graph: dict, html_path: Path):
    """Generate a self-contained HTML file with the graph data embedded inline.
    This avoids fetch() CORS issues when opening directly from the filesystem.
    """
    graph_json = json.dumps(graph, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SecondSelf Brain Graph</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{ margin: 0; height: 100%; font-family: 'Inter', sans-serif; }}
    body {{ background: #0a0a0f; color: #eee; overflow: hidden; }}
    #network {{ width: 100%; height: 100%; }}

    /* Legend overlay */
    #legend {{
      position: fixed; bottom: 20px; left: 20px;
      background: rgba(15,15,25,0.85); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px; padding: 16px 20px;
      backdrop-filter: blur(10px); z-index: 10;
      font-size: 13px;
    }}
    #legend h3 {{ margin: 0 0 10px; font-size: 14px; color: #fff; }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; }}

    /* Stats overlay */
    #stats {{
      position: fixed; top: 20px; right: 20px;
      background: rgba(15,15,25,0.85); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px; padding: 14px 20px;
      backdrop-filter: blur(10px); z-index: 10;
      font-size: 13px;
    }}
    #stats span {{ color: #ff00ff; font-weight: 600; }}

    /* Title */
    #title {{
      position: fixed; top: 20px; left: 20px;
      font-size: 22px; font-weight: 600; z-index: 10;
      background: linear-gradient(135deg, #ff00ff, #00ffff);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
  </style>
  <script src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
</head>
<body>

<div id="title">SecondSelf Brain Graph</div>

<div id="stats">
  Nodes: <span id="node-count">0</span> &nbsp;|&nbsp;
  Edges: <span id="edge-count">0</span>
</div>

<div id="legend">
  <h3>PARA Groups</h3>
  <div class="legend-item"><div class="legend-dot" style="background:#ff00ff;box-shadow:0 0 8px #ff00ff"></div> Projects</div>
  <div class="legend-item"><div class="legend-dot" style="background:#00ffff;box-shadow:0 0 8px #00ffff"></div> Areas</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ffea00;box-shadow:0 0 8px #ffea00"></div> Resources</div>
  <div class="legend-item"><div class="legend-dot" style="background:#7fff00;box-shadow:0 0 8px #7fff00"></div> Archives</div>
  <div class="legend-item"><div class="legend-dot" style="background:#888;box-shadow:0 0 8px #888"></div> Unclassified</div>
</div>

<div id="network"></div>

<script>
  // Graph data is embedded inline — no fetch() needed
  const graphData = {graph_json};

  document.getElementById('node-count').textContent = graphData.nodes.length;
  document.getElementById('edge-count').textContent = graphData.edges.length;

  const container = document.getElementById('network');

  const nodes = new vis.DataSet(graphData.nodes.map(n => ({{
    id: n.id,
    label: n.label,
    group: n.group || 'Unclassified',
    title: '<div style="max-width:300px;font-family:Inter,sans-serif;font-size:13px">'
         + '<b>' + n.label + '</b><br/>'
         + '<em style="color:#aaa">' + (n.group || 'Unclassified') + '</em><br/><br/>'
         + (n.content_preview || '') + '</div>',
    font: {{ color: '#eee', size: 12 }},
  }})));

  const edges = new vis.DataSet(graphData.edges.map(e => ({{
    from: e.source,
    to: e.target,
    color: {{ color: 'rgba(255,255,255,0.15)', highlight: '#ff00ff', hover: '#00ffff' }},
    width: 1,
    smooth: {{ type: 'continuous' }},
  }})));

  const options = {{
    physics: {{
      stabilization: {{ iterations: 150 }},
      barnesHut: {{ gravitationalConstant: -3000, springLength: 150, springConstant: 0.04 }},
    }},
    groups: {{
      Projects:     {{ color: {{ background: '#ff00ff', border: '#ff00ff', highlight: {{ background: '#ff66ff', border: '#ff00ff' }} }}, shadow: {{ enabled: true, color: 'rgba(255,0,255,0.5)', size: 10 }} }},
      Areas:        {{ color: {{ background: '#00ffff', border: '#00ffff', highlight: {{ background: '#66ffff', border: '#00ffff' }} }}, shadow: {{ enabled: true, color: 'rgba(0,255,255,0.5)', size: 10 }} }},
      Resources:    {{ color: {{ background: '#ffea00', border: '#ffea00', highlight: {{ background: '#fff066', border: '#ffea00' }} }}, shadow: {{ enabled: true, color: 'rgba(255,234,0,0.5)', size: 10 }} }},
      Archives:     {{ color: {{ background: '#7fff00', border: '#7fff00', highlight: {{ background: '#a5ff4d', border: '#7fff00' }} }}, shadow: {{ enabled: true, color: 'rgba(127,255,0,0.5)', size: 10 }} }},
      Unclassified: {{ color: {{ background: '#888',    border: '#888',    highlight: {{ background: '#aaa',    border: '#888'    }} }}, shadow: {{ enabled: true, color: 'rgba(136,136,136,0.3)', size: 6  }} }},
    }},
    nodes: {{
      shape: 'dot',
      size: 18,
      borderWidth: 2,
      font: {{ color: '#eee', size: 12 }},
    }},
    edges: {{
      smooth: {{ type: 'continuous' }},
    }},
    interaction: {{
      hover: true,
      tooltipDelay: 150,
      navigationButtons: true,
      keyboard: true,
      zoomView: true,
    }},
  }};

  new vis.Network(container, {{ nodes, edges }}, options);
</script>
</body>
</html>"""

    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [OK] Interactive HTML written to {html_path}")


if __name__ == "__main__":
    print("Building graph from wiki notes...")
    g = build_graph(WIKI_DIR)
    export_graph(g, OUTPUT_PATH)
    export_html(g, HTML_PATH)
    print("\nDone! Open static/graph.html in your browser.")
