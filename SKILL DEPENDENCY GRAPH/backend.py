"""Graph algorithms for the Skill Dependency Graph app.

An edge (A, B) means A must be learned before B.
"""

from collections import defaultdict, deque


def normalize_edges(edges):
    """Trim names, remove duplicates, and reject self-dependencies."""
    result = []
    seen = set()

    for prerequisite, skill in edges:
        prerequisite = prerequisite.strip()
        skill = skill.strip()

        if not prerequisite or not skill:
            continue

        if prerequisite == skill:
            raise ValueError(f"A skill cannot depend on itself: {skill}")

        edge = (prerequisite, skill)
        if edge not in seen:
            seen.add(edge)
            result.append(edge)

    return result


def build_graph(edges):
    edges = normalize_edges(edges)
    graph = defaultdict(list)
    nodes = set()
    indegree = defaultdict(int)

    for prerequisite, skill in edges:
        graph[prerequisite].append(skill)
        nodes.update((prerequisite, skill))
        indegree[skill] += 1
        indegree.setdefault(prerequisite, 0)

    for node in nodes:
        graph[node]
        indegree[node] += 0

    return graph, nodes, indegree


def topological_sort(edges):
    """Return (learning_order, cycle_nodes)."""
    graph, nodes, indegree = build_graph(edges)
    ready = deque(sorted(node for node in nodes if indegree[node] == 0))
    order = []

    while ready:
        node = ready.popleft()
        order.append(node)

        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)

    if len(order) != len(nodes):
        blocked = sorted(node for node in nodes if indegree[node] > 0)
        return None, blocked

    return order, []


def all_prerequisites(target, edges):
    """Find all direct and indirect prerequisites for a skill."""
    reverse_graph = defaultdict(list)

    for prerequisite, skill in normalize_edges(edges):
        reverse_graph[skill].append(prerequisite)

    found = set()
    stack = list(reverse_graph[target])

    while stack:
        prerequisite = stack.pop()

        if prerequisite not in found:
            found.add(prerequisite)
            stack.extend(reverse_graph[prerequisite])

    return found


def missing_prerequisites(target, completed, edges):
    return all_prerequisites(target, edges) - set(completed)


def weakly_connected_components(edges):
    """Group skills connected when edge direction is ignored."""
    graph, nodes, _ = build_graph(edges)
    undirected = defaultdict(set)

    for source, destinations in graph.items():
        for destination in destinations:
            undirected[source].add(destination)
            undirected[destination].add(source)

    components = []
    seen = set()

    for start in sorted(nodes):
        if start in seen:
            continue

        component = []
        stack = [start]
        seen.add(start)

        while stack:
            node = stack.pop()
            component.append(node)

            for neighbor in undirected[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        components.append(sorted(component))

    return components


def find_cycle(edges):
    """Return one directed cycle, or an empty list if no cycle exists."""
    graph, nodes, _ = build_graph(edges)
    state = {node: 0 for node in nodes}  # 0 unseen, 1 visiting, 2 finished
    parent = {}

    def visit(node):
        state[node] = 1

        for neighbor in graph[node]:
            if state[neighbor] == 0:
                parent[neighbor] = node
                cycle = visit(neighbor)

                if cycle:
                    return cycle

            elif state[neighbor] == 1:
                chain = [node]

                while chain[-1] != neighbor:
                    chain.append(parent[chain[-1]])

                chain.reverse()
                return chain + [neighbor]

        state[node] = 2
        return []

    for node in sorted(nodes):
        if state[node] == 0:
            cycle = visit(node)

            if cycle:
                return cycle

    return []