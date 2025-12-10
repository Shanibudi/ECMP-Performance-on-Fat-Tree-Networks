# ECMP-Performance-on-Fat-Tree-Networks

## Overview

This project extends the fat tree topology generator from Homework 1 in order to study
Equal Cost Multi Path (ECMP) routing. The goal is to demonstrate empirically that,
even in a non blocking fat tree, a static hashing based ECMP scheme can still create
congestion and blocking when traffic patterns have low entropy.

The code uses the same three tier fat tree as in Al Fares et al., "A scalable, commodity
data center network architecture" [1]. On top of this topology, it models flows, ECMP
hashing, and link loads under different traffic scenarios.

All figures produced by the experiments are stored under the `plots/` directory.

### Modeling traffic, flows and hashing

* The topology is an undirected NetworkX graph with four node types (core, aggregation, edge, host).
* Each **flow** is modeled as a long lived unit demand flow between a pair of hosts.
  Every flow contributes a load of 1 to each link on its chosen path.
* Link **capacity** is not modeled explicitly as a number. Instead, congestion is inferred by
  comparing the maximum link load to the average link load. If a few links carry many more flows
  than the rest, we consider this a sign of blocking or congestion.
* ECMP is modeled in two steps:
  1. For each source destination host pair we compute all shortest paths using
     `networkx.all_shortest_paths`. All these paths have equal cost.
  2. We select one of these paths using a static hash:
     ```python
     paths = list(nx.all_shortest_paths(G, src, dst))
     idx = hash(hash_key) % len(paths)
     chosen_path = paths[idx]
     ```
     The **hash key** represents the 5 tuple. In the success scenario it contains a per flow
     identifier so the hash has high entropy. In the failure scenario all flows share the same
     hash key, which models many flows that look identical from the ECMP point of view
     (for example due to tunneling or aggregation).

### Traffic parameters

We consider two traffic scenarios on the same fat tree topology.

#### Scenario A  Success case

* Topology: fat tree with parameter `k` (default `k = 8`).
* Number of flows: configurable, default 500.
* Each flow chooses a random pair of distinct hosts `(src, dst)` uniformly.
* The ECMP hash key is `(src, dst, flow_id)`, where `flow_id` is a running index.
  This gives high entropy in the hash input, so flows between the same pair can be
  spread across different equal cost paths.

This scenario represents a typical high diversity traffic matrix where many different
connections are active at once.

#### Scenario B  Failure case

* Same topology and number of flows as Scenario A.
* A single random pair of hosts `(src, dst)` is chosen once.
* All flows are between this same pair.
* The ECMP hash key is only `(src, dst)` and does not include a per flow identifier.

In this case, all flows look identical to the ECMP hash function. As a result, they
are all pinned to the same ECMP path, even though many other equal cost paths exist.
This models a low entropy traffic pattern, for example many flows inside a single
tunnel or with the same 5 tuple.

### Experimental evidence

Running

```bash
python fattree_ecmp_sim.py --k 8 --flows_success 500 --flows_failure 500
```

produces two main plots:

	1.	plots/ecmp_success_link_loads.png
	
	2.	plots/ecmp_failure_link_loads.png

Each plot shows the sorted link loads (number of flows per link) in the network.

 #### Scenario A  ECMP success

In ecmp_success_link_loads.png, the sorted link loads exhibit a gradual decrease from moderately loaded links to lightly loaded links, rather than a perfectly flat distribution.
The maximum link load is clearly higher than the average link load, indicating that some links carry more flows than others. However, the load decreases smoothly and continuously across the link indices, without sharp spikes or isolated extreme outliers.

This behavior indicates that ECMP achieves partial but not perfect load balancing.
The traffic is spread across many equal cost paths, preventing a single catastrophic bottleneck, but due to the randomness of hashing and the limited number of flows, some statistical imbalance naturally remains. Importantly, no single link dominates the traffic by an order of magnitude, and the network still utilizes a large fraction of its bisection bandwidth efficiently.

Therefore, Scenario A represents a practical success case for ECMP under high entropy traffic, where load imbalance exists but remains bounded and moderate, and no severe congestion hotspots are formed.

#### Scenario B  ECMP failure

IIn ecmp_failure_link_loads.png, the sorted link loads reveal an extreme and absolute traffic concentration.
Only a very small number of links (six links in this experiment) carry all 500 flows, while all remaining links in the network carry zero traffic. The bars in the plot reach the full traffic demand simultaneously, indicating that the same overloaded path is used by every single flow.

This behavior represents a complete collapse of ECMP load balancing.
Because all 500 flows share the exact same hash key (identical source and destination), the static ECMP mechanism maps all flows to one single shortest path, despite the existence of many alternative equal-cost paths in the fat-tree topology. As a result, every link along this single path becomes fully congested, while the rest of the fabric remains entirely idle.

Most importantly, this congestion occurs even though the fat-tree provides more than enough aggregate capacity to support the traffic demand. The observed blocking is therefore not caused by insufficient network resources, but purely by the static nature of the ECMP hashing mechanism and the lack of traffic awareness in the routing decision.

This experiment provides a clear and direct demonstration that fat-tree topologies alone do not guarantee high throughput. When ECMP operates on low-entropy traffic patterns, it can degenerate into effectively single-path routing, producing severe congestion and complete underutilization of the remaining network capacity.

### Why ECMP fails in Scenario B?

ECMP relies on a static hash over the flow's 5 tuple to select one of several equal cost
paths. This works well only when the hash input has high entropy and many different
flow keys are present. In Scenario A, the hash key includes a per flow identifier, so
distinct flows between the same hosts can be mapped to different ECMP paths, which
keeps the load balanced.

In Scenario B the situation is very different. All flows share the same `(src, dst)` pair
and the hash key is identical for every flow. From the ECMP perspective there is only
one "flow". The hash function therefore always returns the same index and all traffic
is sent on a single shortest path. All links along this path become heavily loaded,
while parallel links in other equal cost paths remain almost idle.

This behavior matches the theoretical discussion from class:

* Static hashing can create **collisions** when many flows share the same key.
* Low entropy traffic patterns (for example many flows inside a tunnel) reduce the
  effectiveness of ECMP.
* In a fat tree, multiple equal cost paths exist, but ECMP does not adapt to load.
  It only makes a one time decision based on the hash, so it cannot correct an
  unlucky or adversarial mapping.

The experiments show that the topology itself still has enough aggregate capacity,
but the routing mechanism alone is responsible for the observed congestion.
This demonstrates that full bisection bandwidth of the fabric does not guarantee
full throughput when ECMP is used with static hashing.
