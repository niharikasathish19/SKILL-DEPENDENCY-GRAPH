"""Skill Dependency Graph web app. Uses only Python's standard library."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from backend import (
    find_cycle,
    missing_prerequisites,
    normalize_edges,
    topological_sort,
    weakly_connected_components,
)

DEFAULT_EDGES = [
    ["Python basics", "Data structures"],
    ["Discrete mathematics", "Graph algorithms"],
    ["Data structures", "Graph algorithms"],
    ["Graph algorithms", "Depth-First Search (DFS)"],
    ["Graph algorithms", "Topological sort"],
    ["Graph algorithms", "Connected components"],
]

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill Dependency Graph</title>
<style>
:root{font:16px system-ui,sans-serif;color:#172033;background:#f4f7fb}
*{box-sizing:border-box}
body{margin:0}
.wrap{max-width:1100px;margin:auto;padding:28px 18px}
h1{margin:0 0 5px;color:#183b68}
p{color:#596579}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:20px}
.card{background:white;border:1px solid #dfe6ef;border-radius:14px;padding:20px;box-shadow:0 5px 18px #2538580c}
.full{grid-column:1/-1}
h2{font-size:1.15rem;margin:0 0 14px}
label{display:block;font-weight:600;margin:10px 0 5px}
input,select,button{font:inherit;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
input,select{width:100%}
button{background:#245b99;color:white;border:0;font-weight:650;cursor:pointer;margin-top:12px}
button.secondary{background:#e9eef5;color:#22344d}
button.remove{background:#fff0f0;color:#a22;padding:5px 9px;margin:0}
form{display:grid;grid-template-columns:1fr 1fr;gap:0 12px}
form button{grid-column:1/-1}
.row{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #edf0f4;padding:8px 0;gap:12px}
.msg{padding:12px;border-radius:8px;background:#edf6ff}
.error{background:#fff0ef;color:#942d20}
.success{background:#eaf8ef;color:#17633a}
.tag{display:inline-block;background:#edf2f8;border-radius:99px;padding:5px 9px;margin:3px;font-size:.9rem}
svg{width:100%;min-height:190px;background:#fbfcfe;border-radius:9px}
.node{fill:#e9f2ff;stroke:#3874b9;stroke-width:1.5}
.edge{stroke:#71839a;stroke-width:1.5;marker-end:url(#arrow)}
.nodeText{font:12px system-ui;fill:#172033;text-anchor:middle}
.muted{color:#667085}
@media(max-width:700px){.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
</head>
<body>
<main class="wrap">
<h1>🧭 Skill Dependency Graph</h1>
<p>Add prerequisites, find a learning order, and check what skills are missing.</p>

<div class="grid">
<section class="card">
<h2>Add a prerequisite link</h2>
<form id="addForm">
<div>
<label for="pre">Prerequisite</label>
<input id="pre" required placeholder="e.g. Python basics">
</div>
<div>
<label for="skill">Skill to learn next</label>
<input id="skill" required placeholder="e.g. Data structures">
</div>
<button>Add relationship</button>
</form>
<button class="secondary" id="reset">Restore sample graph</button>
</section>

<section class="card">
<h2>Learning order</h2>
<div id="order"></div>
</section>

<section class="card">
<h2>Prerequisite graph</h2>
<div id="graph"></div>
</section>

<section class="card">
<h2>Check missing prerequisites</h2>
<label for="target">Skill you want to learn</label>
<select id="target"></select>
<label for="completed">Skills you already know</label>
<select id="completed" multiple size="5"></select>
<div id="missing" style="margin-top:12px"></div>
</section>

<section class="card full">
<h2>Prerequisite links</h2>
<div id="edges"></div>
</section>

<section class="card full">
<h2>Related skill groups</h2>
<p class="muted">Groups are found by treating links as undirected.</p>
<div id="groups"></div>
</section>
</div>
</main>

<script>
let state = {edges: []};

async function api(path, body) {
  const options = body ? {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  } : {};
  const response = await fetch(path, options);
  return await response.json();
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function drawGraph(edges) {
  const names = [...new Set(edges.flat())];

  if (!names.length) {
    return '<p class="muted">Add links to see the graph.</p>';
  }

  const width = 650;
  const height = Math.max(190, names.length * 55);
  const positions = {};

  names.forEach((name, index) => {
    positions[name] = {
      x: 120 + (index % 2) * 390,
      y: 32 + index * 45
    };
  });

  const lines = edges.map(([from, to]) => `
    <line class="edge"
      x1="${positions[from].x}" y1="${positions[from].y}"
      x2="${positions[to].x}" y2="${positions[to].y}"/>
  `).join("");

  const nodes = names.map(name => `
    <g>
      <rect class="node"
        x="${positions[name].x - 90}"
        y="${positions[name].y - 15}"
        width="180" height="30" rx="9"/>
      <text class="nodeText"
        x="${positions[name].x}"
        y="${positions[name].y + 4}">${escapeHtml(name)}</text>
    </g>
  `).join("");

  return `
    <svg viewBox="0 0 ${width} ${height}">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8"
          refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="#71839a"/>
        </marker>
      </defs>
      ${lines}${nodes}
    </svg>
  `;
}

async function refresh() {
  state = await api("/api/state");

  document.getElementById("edges").innerHTML =
    state.edges.length
      ? state.edges.map((edge, index) => `
          <div class="row">
            <span>${escapeHtml(edge[0])} → ${escapeHtml(edge[1])}</span>
            <button class="remove" onclick="removeEdge(${index})">Remove</button>
          </div>
        `).join("")
      : '<p class="muted">No prerequisite links yet.</p>';

  document.getElementById("graph").innerHTML = drawGraph(state.edges);

  const orderBox = document.getElementById("order");

  if (state.order) {
    orderBox.innerHTML =
      '<div class="msg success">Valid order found</div>' +
      state.order.map((name, index) => `
        <div class="row"><b>${index + 1}.</b><span>${escapeHtml(name)}</span></div>
      `).join("");
  } else {
    orderBox.innerHTML = `
      <div class="msg error">
        A complete learning order is impossible.<br>
        Cycle: ${state.cycle.map(escapeHtml).join(" → ")}
      </div>`;
  }

  const target = document.getElementById("target");
  const completed = document.getElementById("completed");
  const oldTarget = target.value;
  const oldCompleted = [...completed.selectedOptions].map(option => option.value);

  target.innerHTML = state.skills
    .map(name => `<option>${escapeHtml(name)}</option>`).join("");

  completed.innerHTML = state.skills
    .map(name => `<option>${escapeHtml(name)}</option>`).join("");

  if (state.skills.includes(oldTarget)) target.value = oldTarget;

  [...completed.options].forEach(option => {
    option.selected = oldCompleted.includes(option.value);
  });

  document.getElementById("groups").innerHTML =
    state.groups.map((group, index) => `
      <span class="tag">Group ${index + 1}: ${group.map(escapeHtml).join(", ")}</span>
    `).join("") || '<span class="muted">Add links to find groups.</span>';

  await updateMissing();
}

async function updateMissing() {
  const target = document.getElementById("target").value;
  const completed = [...document.getElementById("completed").selectedOptions]
    .map(option => option.value);

  if (!target) return;

  const result = await api("/api/missing", {target, completed});
  document.getElementById("missing").innerHTML = result.missing.length
    ? `<div class="msg">Still needed first: ${result.missing.map(escapeHtml).join(", ")}</div>`
    : '<div class="msg success">You have completed the listed prerequisites.</div>';
}

async function removeEdge(index) {
  await api("/api/remove", {index});
  refresh();
}

document.getElementById("addForm").addEventListener("submit", async event => {
  event.preventDefault();

  const result = await api("/api/add", {
    prerequisite: document.getElementById("pre").value,
    skill: document.getElementById("skill").value
  });

  if (!result.ok) {
    alert(result.error);
  } else {
    event.target.reset();
    refresh();
  }
});

document.getElementById("reset").onclick = async () => {
  await api("/api/reset", {});
  refresh();
};

document.getElementById("target").onchange = updateMissing;
document.getElementById("completed").onchange = updateMissing;
refresh();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    # Shared by all requests while the server is running.
    edges = [edge[:] for edge in DEFAULT_EDGES]

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        route = urlparse(self.path).path

        if route == "/api/state":
            edges = type(self).edges
            order, _ = topological_sort(edges)
            cycle = find_cycle(edges) if order is None else []
            skills = sorted({name for edge in edges for name in edge})

            return self.send_json({
                "edges": edges,
                "order": order,
                "cycle": cycle,
                "skills": skills,
                "groups": weakly_connected_components(edges),
            })

        if route == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)

        self.send_error(404)

    def do_POST(self):
        route = urlparse(self.path).path
        data = self.read_json()

        try:
            if route == "/api/add":
                edge = [
                    data.get("prerequisite", "").strip(),
                    data.get("skill", "").strip(),
                ]

                if not all(edge):
                    return self.send_json({
                        "ok": False,
                        "error": "Enter both skill names.",
                    }, 400)

                candidate = normalize_edges(type(self).edges + [edge])
                type(self).edges = [list(item) for item in candidate]
                return self.send_json({"ok": True})

            if route == "/api/remove":
                index = int(data["index"])
                edges = type(self).edges

                if 0 <= index < len(edges):
                    edges.pop(index)

                return self.send_json({"ok": True})

            if route == "/api/reset":
                type(self).edges = [edge[:] for edge in DEFAULT_EDGES]
                return self.send_json({"ok": True})

            if route == "/api/missing":
                target = data.get("target", "")
                missing = sorted(missing_prerequisites(
                    target,
                    data.get("completed", []),
                    type(self).edges,
                ))
                return self.send_json({"missing": missing})

            self.send_error(404)

        except (ValueError, KeyError, TypeError) as error:
            return self.send_json({"ok": False, "error": str(error)}, 400)

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8501), Handler)
    print("App running at http://127.0.0.1:8501")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()