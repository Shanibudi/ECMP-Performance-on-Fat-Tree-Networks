import networkx as nx
import matplotlib.pyplot as plt
import random
import numpy as np
import hashlib
import os


# -------------------------
# Fat-tree k=4 (small)
# -------------------------

def generate_fat_tree(k=4):
    G = nx.Graph()

    core = [f"C{i}" for i in range((k // 2) ** 2)]
    agg = [f"A{i}" for i in range(k * (k // 2))]
    edge = [f"E{i}" for i in range(k * (k // 2))]
    hosts = [f"H{i}" for i in range((k ** 3) // 4)]

    G.add_nodes_from(core, layer="core")
    G.add_nodes_from(agg, layer="aggregation")
    G.add_nodes_from(edge, layer="edge")
    G.add_nodes_from(hosts, layer="host")

    # Core ↔ Aggregation
    for i, c in enumerate(core):
        for pod in range(k):
            a = agg[pod * (k // 2) + (i // (k // 2))]
            G.add_edge(c, a)

    # Aggregation ↔ Edge
    for pod in range(k):
        for a in range(pod * (k // 2), (pod + 1) * (k // 2)):
            for e in range(pod * (k // 2), (pod + 1) * (k // 2)):
                G.add_edge(agg[a], edge[e])

    # Edge ↔ Hosts
    h = 0
    for e in edge:
        for _ in range(k // 2):
            G.add_edge(e, hosts[h])
            h += 1

    return G


# -------------------------
# ECMP utilities
# -------------------------

def stable_hash(key, n):
    s = "|".join(map(str, key))
    h = int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")
    return h % n


def ecmp_path(G, src, dst, key):
    paths = list(nx.all_shortest_paths(G, src, dst))
    idx = stable_hash(key, len(paths))
    return paths[idx]


def compute_link_loads_by_type(paths, demands, types):
    """
    Compute per-link load separated by flow type.
    types: list of "mice" or "elephant"
    """
    loads = {}
    for path, d, t in zip(paths, demands, types):
        for u, v in zip(path[:-1], path[1:]):
            edge = tuple(sorted((u, v)))
            if edge not in loads:
                loads[edge] = {"mice": 0, "elephant": 0}
            loads[edge][t] += d
    return loads


def random_flow_key(src, dst):
    return (
        src,
        dst,
        random.randint(1024, 65535),
        random.choice([80, 443, 8080]),
        6
    )


# -------------------------
# Scenario A: mice only
# -------------------------

def scenario_a(G, src, dst):
    paths, demands, types = [], [], []

    for _ in range(4):   # 4 mice flows
        key = random_flow_key(src, dst)
        paths.append(ecmp_path(G, src, dst, key))
        demands.append(1)
        types.append("mice")

    return compute_link_loads_by_type(paths, demands, types)


# -------------------------
# Scenario B: mice + elephants
# -------------------------

def find_collision_keys(G, src, dst):
    paths = list(nx.all_shortest_paths(G, src, dst))
    seen = {}

    while True:
        key = random_flow_key(src, dst)
        idx = stable_hash(key, len(paths))
        if idx in seen and seen[idx] != key:
            return seen[idx], key
        seen[idx] = key


def scenario_b(G, src, dst):
    paths, demands, types = [], [], []

    # Two elephant flows with hash collision
    k1, k2 = find_collision_keys(G, src, dst)

    for k in [k1, k2]:
        paths.append(ecmp_path(G, src, dst, k))
        demands.append(20)
        types.append("elephant")

    # Two mice flows
    for _ in range(2):
        key = random_flow_key(src, dst)
        paths.append(ecmp_path(G, src, dst, key))
        demands.append(1)
        types.append("mice")

    return compute_link_loads_by_type(paths, demands, types)


# -------------------------
# Plot
# -------------------------

def plot_sorted_loads(loads, title, filename):
    os.makedirs("plots", exist_ok=True)

    total_loads = [
        v["mice"] + v["elephant"] for v in loads.values()
    ]

    values = sorted(total_loads, reverse=True)

    plt.figure(figsize=(8, 5))
    plt.bar(range(len(values)), values)
    plt.xlabel("Link index (sorted)")
    plt.ylabel("Total traffic load")
    plt.title(title)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"plots/{filename}", dpi=300)
    plt.close()

def draw_topology_with_flow_types(G, loads, title, filename):
    os.makedirs("plots", exist_ok=True)

    # Hierarchical layout
    layers = {"core": 3, "aggregation": 2, "edge": 1, "host": 0}
    pos = {}
    for layer, y in layers.items():
        nodes = [n for n, d in G.nodes(data=True) if d["layer"] == layer]
        xs = np.linspace(0, 1, len(nodes))
        for x, n in zip(xs, nodes):
            pos[n] = (x, y)

    plt.figure(figsize=(12, 7))

    # Draw base topology
    nx.draw_networkx_edges(G, pos, edge_color="lightgray", width=0.5, alpha=0.3)

    # Draw mice and elephant loads
    for edge, load in loads.items():
        u, v = edge
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]

        if load["mice"] > 0:
            plt.plot(
                x, y,
                color="blue",
                linewidth=1 + load["mice"],
                alpha=0.8
            )

        if load["elephant"] > 0:
            plt.plot(
                x, y,
                color="red",
                linewidth=2 + load["elephant"] / 5,
                alpha=0.9
            )

    # Draw nodes
    node_colors = {
        "core": "red",
        "aggregation": "orange",
        "edge": "green",
        "host": "skyblue",
    }

    nx.draw_networkx_nodes(
        G,
        pos,
        node_size=150,
        node_color=[node_colors[G.nodes[n]["layer"]] for n in G.nodes()],
    )

    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(f"plots/{filename}", dpi=300)
    plt.close()
# -------------------------
# Main
# -------------------------

def main():
    random.seed(1)

    G = generate_fat_tree(k=4)
    hosts = [n for n, d in G.nodes(data=True) if d["layer"] == "host"]
    src, dst = random.sample(hosts, 2)

    print(f"Communicating hosts: {src} → {dst}")

    loads_a = scenario_a(G, src, dst)
    plot_sorted_loads(
        loads_a,
        "Scenario A: ECMP Success (Mice Flows Only)",
        "scenario_a_balanced.png"
    )

    loads_b = scenario_b(G, src, dst)
    plot_sorted_loads(
        loads_b,
        "Scenario B: ECMP Failure (Elephant Collision)",
        "scenario_b_unbalanced.png"
    )

    draw_topology_with_flow_types(
        G,
        loads_a,
        "Scenario A: ECMP Success (4 Mice Flows)",
        "scenario_a_topology_load.png"
    )

    draw_topology_with_flow_types(
        G,
        loads_b,
        "Scenario B: ECMP Failure (2 Mice + 2 Elephant)",
        "scenario_b_topology_load.png"
    )
    

if __name__ == "__main__":
    main()