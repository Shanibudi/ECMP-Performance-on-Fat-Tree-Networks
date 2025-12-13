# ECMP Performance on Fat-Tree Networks

## Overview

This project extends the Fat-Tree topology implementation from Homework 1 in order to study
the behavior of Equal-Cost Multi-Path (ECMP) routing under different traffic patterns.

Although Fat-Tree topologies offer full bisection bandwidth in theory, the actual network
performance is dictated by the routing mechanism. ECMP relies on static hashing to distribute
flows across equal-cost paths, without considering real-time link utilization.

The goal of this project is to demonstrate empirically that static hashing is not perfect.
Even in a non-blocking Fat-Tree topology, ECMP alone can cause severe congestion and blocking
when traffic entropy is low.

## How to Run

Clone the repository and run: 
	```bash
	python fattree_ecmp_sim.py

The script uses a fixed Fat-Tree with k = 4 and a fixed random seed for reproducibility.

After execution, the following figures will be generated in the plots/ directory:

• scenario_a_balanced.png
• scenario_a_topology_load.png
• scenario_b_unbalanced.png
• scenario_b_topology_load.png

---

## Topology

We use a three-tier Fat-Tree topology with parameter `k = 4`, following the design described
by Al-Fares et al. [1].

The topology consists of four types of nodes:
- Core switches
- Aggregation switches
- Edge switches
- Hosts

The network is modeled as an undirected graph using NetworkX. For any pair of hosts, multiple
equal-cost shortest paths exist, ensuring full bisection bandwidth in theory.

---

## Modeling Traffic, Flows, and Hashing

### Flows

Traffic is modeled at the flow level, rather than packet level. This abstraction is sufficient
to demonstrate ECMP behavior, since ECMP decisions are made per flow.

Each flow is defined by a simplified 5-tuple:

(source host, destination host, source port, destination port, protocol)

#### Flow Types

Two types of flows are modeled:
Mice flows:
  - Small, short-lived flows
  - Contribute a unit load of `1` to each link along their path

Elephant flows:
  - Large, long-lived flows
  - Contribute a load of `20` to each link along their path

Thus, in the simulation, an elephant flow is **20× larger** than a mice flow.

### ECMP Hashing

ECMP routing is implemented as follows:

1. For a given `(src, dst)` pair, all shortest paths are computed using:
   ```python
   networkx.all_shortest_paths

2.	A single path is selected using a static hash over the flow’s 5-tuple:
	```python
   idx = hash(flow_key) % number_of_paths

This models real ECMP behavior, where all packets belonging to the same flow are routed on the
same path to prevent packet reordering.


### Experimental Setup

A single, fixed pair of hosts (src, dst) is chosen randomly at the beginning of the experiment.
All traffic in both scenarios is exchanged between this same pair of hosts.

Fixing the communicating hosts isolates the effect of ECMP hashing and avoids averaging effects
that would mask congestion.

## Scenario A – ECMP Success

### Parameters
	•	Number of flows: 4
	•	Flow types: 4 mice flows
	•	Traffic pattern: All flows use distinct 5-tuples (random ports)
	•	ECMP entropy: high

### Expected Behavior

Because each flow has a different hash key, ECMP distributes flows across multiple equal-cost
paths. The load is spread relatively evenly, and no single link becomes a bottleneck.

### Evidence:

File: scenario_a_balanced.png

• The bar chart shows total load per link (sorted)
• Loads are small and spread across many links
• Sorted link-load plot shows moderate and smoothly decreasing loads
• No sharp spikes or dominant links

This indicates successful load balancing

File: scenario_a_topology_load.png

• Blue links represent mice traffic
• Line width corresponds to load
• Traffic is distributed across multiple core and aggregation paths

ECMP behaves as intended under high-entropy traffic.

## Scenario B – ECMP Failure

### Parameters
	•	Number of flows: 4
	•	Flow types: 2 elephant flows (red) + 2 mice flows(blue)
	•	Elephant flow size: 20× mice flow
	•	Traffic pattern: All flows communicate between the same (src, dst) pair
	•	ECMP entropy: low

### Hash Collision

The two elephant flows have different 5-tuples, but due to the finite number of ECMP paths,
their hash values collide and map to the same ECMP path.

This collision is discovered automatically by the code and is not hard-coded.

### Observed Behavior
	•	Both elephant flows are routed over the same physical path
	•	Links on that path become heavily overloaded
	•	Parallel equal-cost paths remain underutilized

### Evidence

File: scenario_b_unbalanced.png
• Sorted link-load plot shows extreme load concentration
• A small number of links carry ~40 units of traffic
• Most links carry almost no load
• Clear separation between overloaded and idle links

Severe congestion appears despite enough aggregate capacity.

File: scenario_b_topology_load.png

• Topology visualization clearly highlights a single thick red path represent elephant traffic
• Very thick links highlight congestion
• Blue (mice) traffic is negligible in comparison

One ECMP path is saturated while parallel paths remain underutilized.

## Why ECMP Fails

ECMP is congestion-oblivious. It relies solely on static hashing and does not adapt to link utilization.

When traffic entropy is low, or when large elephant flows collide in the hash space, ECMP can
degenerate into effectively single-path routing. The Fat-Tree topology itself provides ample
capacity, but ECMP cannot exploit it due to its static nature.

This experiment demonstrates that full bisection bandwidth does not guarantee high throughput
when ECMP is used with static hashing.
