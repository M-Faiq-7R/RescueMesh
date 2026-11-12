# RescueMesh: 3-minute video pitch script

Target length: 3:00 (about 400 spoken words at a calm pace). All numbers below come from `results/phase5_results.json` (final run).

**Recording note.** `python main.py` takes about 2 minutes (QAOA parameter tuning dominates). For the demo, start the command on screen, then cut or speed up to the finished output, or run it beforehand and scroll through the saved terminal output. Say so on camera if you cut: "this takes about two minutes, so I've sped it up." Show only real output and the real files in `results/`.

---

## 0:00-0:30  The problem  (visual: title slide, then `results/network_graph.png`)

"After an earthquake or a flood, phone networks can go down. Rescue teams set up portable radio nodes: a command center, a medical unit, rescue teams and a shelter. But if two nearby nodes use the same radio channel, they talk over each other. There are only a few channels, and choosing them by hand is easy to get wrong."

## 0:30-1:00  The solution and architecture  (visual: `report/architecture_diagram.png`, point to the colours)

"RescueMesh turns this into a puzzle. Each node is a dot. A line between two dots means they interfere, and the number on it says how badly. The task: give every node one of three channels with the least total interference. We encode the puzzle, solve it with a quantum algorithm called QAOA on Qiskit's simulator, and check it against an exact classical solver. On this diagram, blue is classical, purple is the quantum part, and green is the exact check."

## 1:00-1:40  QUBO and QAOA in plain words  (visual: the formula on a slide, then the circuit idea)

"To give a quantum algorithm a puzzle, we write it as a score. Score equals interference cost, plus a penalty if any node does not have exactly one channel. That is called a QUBO. We convert it into an energy for each of the 32,768 on-off patterns of 15 qubits. QAOA starts with all patterns at once, then repeats two steps. A cost step tags each pattern with its energy. A mixer step lets patterns interfere, so low-energy ones become more likely. Measuring gives one possible allocation each time, and a classical optimizer tunes two numbers until good allocations show up more often."

## 1:40-2:30  Live demo and results  (visual: terminal running `python main.py`, then `fig1_valid_rates.png`, `fig2_optimal_rates.png`)

"Here is the run. First the checks: all 32,768 patterns are verified against the original math, and every check passes. Now the results, with 8,192 samples per method. Random guessing gives 62 valid allocations. QAOA with one layer gives 1,461, about 17.8 percent. With two layers, 2,288. For optimal allocations, random guessing finds 2, and QAOA finds 43 and 82. The best allocation has zero interference: A on channel 1, B on 0, C on 2, D on 1, E on 0. Most QAOA samples are still invalid, and the two-layer result is a single run with different tuning effort, so we treat it as suggestive."

## 2:30-3:00  Classical comparison, limitations and conclusion  (visual: comparison table, `fig5_runtime.png`)

"Exhaustive search tries all 243 options and finds every optimal answer in about two milliseconds. Random guessing even found an optimal allocation twice. So we do not claim quantum advantage. This is a noiseless simulation of a small, easy problem. What we show is a complete, verified pipeline, and that QAOA gives roughly 24 times more valid allocations than random guessing. Next steps are harder networks, noise models and real hardware. Thank you."

---

### Quick answers if judges ask

* **Is it faster than classical?** No. Exhaustive search takes milliseconds here; QAOA needs about a minute of simulated tuning.
* **Why did random guessing also find the optimum?** The optimum is zero interference and 6 of 243 valid assignments reach it, so the instance is easy. The difference is how often each method finds it.
* **Why is the invalid rate high?** Only 243 of 32,768 patterns are valid, and one or two QAOA layers reshape the odds only partly.
* **Was this run on a quantum computer?** No, on Qiskit's local noiseless simulator.
