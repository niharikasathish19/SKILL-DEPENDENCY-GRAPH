# Skill Dependency Graph

A small hackathon prototype with a browser interface and a Python graph-algorithm backend. It uses only Python's standard library, so no package download is required.

## Run it

Use Python 3.9 or newer. From this folder, start the local web app with:

```bash
/usr/bin/python3 app.py
```

Then open <http://127.0.0.1:8501> in your browser. Stop the app with Ctrl+C.

## What it does

- Stores prerequisite links as directed edges: `Prerequisite -> Skill`.
- Uses Kahn's topological-sort algorithm to produce a valid learning order.
- Uses depth-first search to report one concrete cycle when an order is impossible.
- Finds direct and indirect prerequisites for a selected skill.
- Groups related skills into weakly connected components (edge direction ignored).
- Draws the graph and lets the user add relationships in the sidebar.

The graph algorithms take O(V + E) time, where V is the number of skills and E is the number of prerequisite links.

## Files

- `app.py`: standard-library HTTP server, JSON API, and browser frontend.
- `backend.py`: graph data handling and algorithms.
- `requirements.txt`: no external dependencies are needed.