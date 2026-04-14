# Input-Aware NFA State Activation Pruning 

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Dependencies](https://img.shields.io/badge/dependencies-matplotlib%20%7C%20numpy-orange)
![Topic](https://img.shields.io/badge/topic-Automata%20Theory%20%26%20Optimization-success)

> **Overview**
> This project investigates a runtime optimization technique for Non-deterministic Finite Automaton (NFA) based multi-pattern matching on byte streams. The central idea is to exploit the observed character-set distribution of a sliding window over the input to skip NFA state evaluations that cannot possibly fire, without altering the set of matches produced.

---

##  The Research Problem

Multi-pattern NFA matching is a foundational operation in network security systems (e.g., Deep Packet Inspection, Intrusion Detection). A standard NFA simulator must evaluate transitions from every active state for *every* incoming byte. 

As the number of patterns grows, the active state set expands. Consequently, the per-byte evaluation cost rises proportionally—even when the majority of those states are waiting for characters that are simply not present in the current network traffic.

**The core research question:**
> *Can we use knowledge of which characters have recently appeared in the stream to prune, at runtime, the set of NFA states that need to be evaluated—and if so, by how much?*

---

##  Proposed Approach

### 1. Sliding-Window Character Profiling ($\Sigma'$)
At each byte position in the stream, a fixed-size sliding window of the last $W$ bytes is maintained. The set of distinct characters present in this window is called $\Sigma'$ (the active character set). 

The `WindowProfiler` class implements this with an $O(1)$-per-byte update using a deque and a frequency dictionary.

### 2. State-Level Pruning
Each NFA state is annotated with its *required character set* (the set of characters it can transition on). Before evaluating transitions from a given active state, the engine checks whether any of that state's required characters belong to $\Sigma'$. 

If the intersection (`required_chars` $\cap$ $\Sigma'$) is empty, the state cannot produce a valid transition on the current or any recently observed byte, and is **skipped entirely**. Because this is a simple set intersection test, the overhead of the pruning decision itself is negligible.

### 3. Simulation Modes

| Mode | Behaviour | Correctness Guarantee |
| :--- | :--- | :--- |
| **Standard** | Evaluates transitions from every active state for every byte. (Baseline) | N/A |
| **Pruned** | Skips states whose required characters are absent from $\Sigma'$. | Pruning is only applied when a state's *entire* transition alphabet is absent from the window. |

---

##  Experimental Benchmarks

Five benchmark experiments are conducted to rigorously characterize this technique:

| # | Experiment | Primary Goal |
| :---: | :--- | :--- |
| **1** | **Pruning Ratio vs. Window Size ($W$)** | Observe how $\Sigma'$ coverage (and pruning opportunity) changes as $W$ grows from 4 to 256. |
| **2** | **Transition Reduction by Input** | Quantify skipped vs. evaluated transitions across HTTP, DNS, JSON, binary, and mixed traffic. |
| **3** | **Throughput Comparison** | Determine if pruning translates into measurable MB/s improvements, or if overhead negates the gains. |
| **4** | **Effect of Pattern Count** | Measure how the pruning ratio scales as the number of patterns increases (4 $\rightarrow$ 24). |
| **5** | **Correctness Verification** | Ensure standard and pruned engines produce identical match counts across all inputs and window sizes. |

---

##  Key Hypotheses

* **Traffic Structure Matters:** Structured traffic (HTTP, DNS, JSON) utilizes a narrow character set. $\Sigma'$ will be small, allowing many state transitions (especially those waiting for rare characters) to be profitably pruned.
* **Binary Data is Resistant:** Binary or highly random data fills $\Sigma'$ rapidly, reducing pruning effectiveness since almost all characters will constantly be present in the window.
* **Window Size Trade-offs:** Smaller windows are more selective (smaller $\Sigma'$) yielding higher pruning ratios. Larger windows accumulate more characters and converge toward the full alphabet.
* **Scaling Potential:** Adding more patterns increases the active state set, giving the pruner a larger pool of states to potentially skip, thereby improving the absolute number of skipped evaluations.

---

##  Repository Structure

```text
.
├── nfa_engine.py          # Core: MultiPatternNFA with standard & pruned simulation
├── window_profiler.py     # Sliding-window character-set tracker
├── benchmark.py           # Runs the 5 benchmark experiments (outputs tables)
├── plot_results.py        # Generates the report figures
├── figures/               # Output directory for visual data
│   ├── fig1_pruning_vs_window.png
│   ├── fig2_transition_reduction.png
│   ├── fig3_pattern_count.png
│   ├── fig4_stream_profile.png
│   └── fig5_correctness.png
└── NSD_PS5_Report_CS22B2031.pdf  # Comprehensive written report
```

---

##  Reproducing Results

**Prerequisites:** Ensure you have Python 3.8+ installed along with the required plotting libraries.
```bash
pip install matplotlib numpy
```

**Run Benchmarks:** Execute the benchmarking suite to print the data tables directly to your standard output.
```bash
python benchmark.py
```

**Generate Figures:** Compile the visual graphs into the `/figures` directory.
```bash
python plot_results.py
```

---

##  Scope and Limitations

* **Automaton Complexity:** The NFA used is a simple chain-of-states model (no epsilon transitions, no wildcards). While the technique is general, these benchmarks are explicitly scoped to literal multi-pattern matching.
* **Traffic Generation:** All benchmarks run on synthetic traffic generated deterministically (seed `42`) to guarantee reproducibility. Real-world network packet captures may exhibit different $\Sigma'$ dynamics.
* **Interpreter Overhead:** The implementation is in pure Python. The pruning ratio measurements reflect algorithmic work saved rather than raw wall-clock speedups, as Python's interpreter overhead can obscure micro-optimizations.