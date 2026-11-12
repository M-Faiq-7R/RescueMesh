// Builds RescueMesh_Report.docx. Every number comes from results/phase5_results.json.
// Needs Node.js and the `docx` npm package:  node report/build_report.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, LevelFormat, BorderStyle, Footer, PageNumber, PageBreak,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const R = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "phase5_results.json"), "utf8"));
const M = R.methods, RND = M["Random sampling"], P1 = M["QAOA p=1"], P2 = M["QAOA p=2"], RT = R.runtime_seconds;
const SH = R.config.shots;
const n = (x) => x.toLocaleString("en-US");
const pc = (x) => x.toFixed(2) + "%";
const f2 = (x) => x.toFixed(2);
const sec = (x) => (x < 0.01 ? (x * 1000).toFixed(1) + " ms" : x < 1 ? x.toFixed(2) + " s" : x.toFixed(0) + " s");
const invalidPct = (m) => pc(100 - m.valid_pct);
const expectedValid = (SH * R.exact.n_assignments) / 2 ** 15;                    // uniform expectation
const expectedOptimal = (SH * R.exact.n_optimal_assignments) / 2 ** 15;

// ---- helpers --------------------------------------------------------------------------
const FONT = "Arial";
function runs(text, base = {}) {            // **bold** markup
  return text.split("**").map((t, i) => new TextRun({ text: t, bold: i % 2 === 1 || base.bold, font: FONT, size: base.size || 22, italics: base.italics }));
}
const p = (text, opts = {}) => new Paragraph({ children: runs(text, opts), spacing: { after: 120, line: 276 }, alignment: opts.align });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(t), spacing: { after: 60, line: 276 } });
const eq = (t) => new Paragraph({
  children: [new TextRun({ text: t, font: "Courier New", size: 20 })],
  indent: { left: 360 }, spacing: { before: 60, after: 120 },
  shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
});
function png(file) { const d = fs.readFileSync(file); return { w: d.readUInt32BE(16), h: d.readUInt32BE(20) }; }
function figure(rel, caption, maxW = 600) {
  const file = path.join(ROOT, rel), s = png(file), w = Math.min(maxW, s.w), h = Math.round((w * s.h) / s.w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: w, height: h },
        altText: { title: caption, description: caption, name: path.basename(rel) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: caption, italics: true, size: 18, font: FONT })] }),
  ];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(widths, header, rows) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, head) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: { type: ShadingType.CLEAR, fill: head ? "D9E2F3" : "FFFFFF" },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: String(t), bold: head, size: 18, font: FONT })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, widths[i], false)) }))],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 120 } });

// ---- content --------------------------------------------------------------------------
const C = [];
C.push(
  new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "RescueMesh", bold: true, size: 64, font: FONT })] }),
  new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Quantum-Assisted Channel Allocation for Emergency Wireless Mesh Networks", size: 32, font: FONT })] }),
  new Paragraph({ spacing: { after: 120 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Technical report, Qiskit Fall Fest 2026 Hackathon", size: 24, font: FONT })] }),
  new Paragraph({ spacing: { after: 120 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Domain: disaster response  |  Simulation and optimization study (noiseless simulator)", size: 22, font: FONT })] }),
  new Paragraph({ spacing: { after: 120 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "[Team name and authors to be added before submission]", italics: true, size: 22, font: FONT })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// 1 Abstract
C.push(h1("1. Abstract"),
  p(`Emergency mesh networks suffer from interference when nearby nodes share a wireless channel. RescueMesh formulates channel allocation for five nodes and three channels as a QUBO, converts it to an Ising Hamiltonian over 15 qubits and solves it with the Quantum Approximate Optimization Algorithm (QAOA) in Qiskit on a local, noiseless simulator. An independent exhaustive search over all 243 assignments provides the exact optimum, which is zero interference with six optimal assignments.`),
  p(`With ${n(SH)} samples per sampled method, QAOA with p = 1 produced ${n(P1.valid_count)} valid (${pc(P1.valid_pct)}) and ${P1.optimal_count} optimal (${pc(P1.optimal_pct)}) allocations; QAOA with p = 2 produced ${n(P2.valid_count)} valid (${pc(P2.valid_pct)}) and ${P2.optimal_count} optimal (${pc(P2.optimal_pct)}); uniform random sampling produced ${RND.valid_count} valid (${pc(RND.valid_pct)}) and ${RND.optimal_count} optimal (${pc(RND.optimal_pct)}). All methods found a best valid score of 0, so the optimum alone does not separate them; QAOA changes how often good allocations appear. Exhaustive search is exact and far cheaper on this instance. **We do not claim quantum advantage or speedup.**`));

// 2 Introduction
C.push(h1("2. Introduction"),
  p(`Quantum optimization is often discussed in broad terms. This project asks a narrower question: can a small, realistic-looking resource-allocation problem be formulated correctly for a gate-based quantum algorithm, run end to end, and judged honestly against exact classical methods? We built a complete pipeline in Python with Qiskit, validated each stage, and compared QAOA with an exact solver and with random sampling.`),
  p(`The report describes the problem, the mathematics, the algorithm, the software, the results and, importantly, the limits of what the results show.`));

// 3 Problem statement
C.push(h1("3. Problem Statement"),
  p(`A rescue operation deploys five portable mesh nodes. Each node must be assigned exactly one of three channels. If two nodes that interfere are given the same channel, a cost equal to the interference weight is paid. The goal is to find the assignment with minimum total interference. The instance is a synthetic simulation, not measured radio data.`),
  table([1800, 1100, 6460], ["Edge", "Weight", "Meaning (synthetic)"], [
    ["A - B", "5", "Command center and rescue team 1: strong overlap"],
    ["A - C", "2", "Command center and medical unit: weak overlap"],
    ["B - C", "4", "Rescue team 1 and medical unit: medium overlap"],
    ["B - D", "3", "Rescue team 1 and rescue team 2: moderate overlap"],
    ["C - D", "6", "Medical unit and rescue team 2: strongest overlap"],
    ["C - E", "2", "Medical unit and emergency shelter: weak overlap"],
    ["D - E", "5", "Rescue team 2 and emergency shelter: strong overlap"],
  ]),
  ...figure("results/network_graph.png", "Figure 1. Weighted interference graph (edge label = interference cost if both nodes share a channel).", 420));

// 4 Real-world application
C.push(h1("4. Real-World Application"),
  p(`After earthquakes or floods, cellular infrastructure may be unavailable. Responders then rely on portable mesh nodes linking command centers, medical units, rescue teams and shelters. Spectrum is limited, and neighboring nodes on the same channel degrade each other. Channel assignment is closely related to graph colouring and is a standard example of a combinatorial resource-allocation task. RescueMesh is a small-scale simulation of this task and not a deployable wireless system.`));

// 5 Math formulation
C.push(h1("5. Mathematical Formulation"),
  p(`Let nodes be i = 1..5 and channels c = 0..2. The binary variable x(i,c) equals 1 if node i uses channel c and 0 otherwise, giving 15 variables. For each edge (i,j) with weight w_ij:`),
  eq("Interference = sum over edges (i,j) of  w_ij * sum over c of  x(i,c) * x(j,c)"),
  p(`The product x(i,c)*x(j,c) is 1 only when both nodes use channel c, so each edge costs its weight exactly when its endpoints clash. The requirement that every node uses exactly one channel is not imposed as a hard constraint (QUBO has none) but added as a penalty:`),
  eq("Penalty = P * sum over nodes i of ( sum over c of x(i,c) - 1 )^2"),
  eq("Minimize  E(x) = Interference + Penalty,   P = 15"),
  p(`The penalty is 0 if node i has exactly one channel, and at least P if it has none or several. No additional constraints are introduced.`),
  p(`**Choice of P.** The largest weighted degree in the graph is 14 (node C: 2 + 4 + 6 + 2). A node left without a channel can remove at most this much interference, so P must exceed 14 for the penalty to always outweigh the saving. We therefore use P = 15. (An earlier value of P = 13 also happened to work on this instance, but P = 15 does not depend on that.)`));

// 6 QUBO
C.push(h1("6. QUBO Construction"),
  p(`A QUBO (Quadratic Unconstrained Binary Optimization) problem asks for the 0/1 vector x that minimizes x^T Q x + offset. Because x*x = x for binary variables, linear terms are stored on the diagonal of Q. Variables are numbered x(node k, channel c) -> index 3k + c.`),
  bullet("**Interference term:** for each edge and each channel, add w_ij to the entry coupling x(i,c) and x(j,c): 7 edges x 3 channels = 21 entries."),
  bullet("**Penalty term:** expanding P*(x0 + x1 + x2 - 1)^2 with x^2 = x gives P*(1 - sum x + 2*sum of pair products). Per node this adds -P on 3 diagonal entries, +2P on 3 pair entries and +P to the offset: 15 diagonal and 15 pair entries in total, and offset 5P = 75."),
  p(`The resulting Q has 15 + 15 + 21 = 51 non-zero entries. **Validation.** All 2^15 = 32,768 bit patterns were evaluated. Of these, 243 are valid and 32,525 are invalid. For every valid pattern the QUBO energy equals the classical interference. For all patterns it equals interference + P*sum(count - 1)^2 (maximum difference 0). The smallest penalty of an invalid pattern is 15 = P, the lowest invalid energy is 15, above the valid optimum of 0, and the QUBO minimizers are exactly the six classically optimal assignments.`));

// 7 Ising
C.push(h1("7. Ising Hamiltonian Conversion"),
  p(`Quantum circuits work with qubit operators, so the QUBO is rewritten with spins z = +1 or -1 using x = (1 - z)/2 (x = 0 maps to z = +1, x = 1 to z = -1, matching the Z eigenvalues of |0> and |1>). The two kinds of QUBO terms transform as:`),
  eq("Q_ii * x_i        = Q_ii/2 - (Q_ii/2) z_i"),
  eq("Q_ij * x_i * x_j  = (Q_ij/4) (1 - z_i - z_j + z_i z_j)"),
  p(`Collecting terms gives E = const + sum h_i z_i + sum J_ij z_i z_j with J_ij = Q_ij/4, h_i = -Q_ii/2 - (1/4) times the sum of the Q entries touching i, and const = offset + sum Q_ii/2 + sum Q_ij/4. For our instance there are 15 Z terms, 36 ZZ terms and a constant of 95.25. The constant shifts all energies equally and does not change which pattern is best. Each z_i becomes a Pauli Z on qubit i. Numerically, the Ising energy equals the QUBO energy for all 32,768 patterns.`));

// 8 QAOA
C.push(h1("8. QAOA Methodology"),
  p(`QAOA prepares a quantum state whose measurement outcomes are biased toward low-energy bit patterns, with the bias controlled by a few classical parameters.`),
  bullet("**Initial state:** a Hadamard gate on each of the 15 qubits creates an equal superposition of all 32,768 bit patterns."),
  bullet("**Cost layer** exp(-i*gamma*H_C): implemented with RZ(2*gamma*h_i) on single qubits and RZZ(2*gamma*J_ij) on coupled pairs (15 + 36 gates). It attaches to each pattern a phase that depends on its energy; by itself it does not change measurement probabilities."),
  bullet("**Mixer layer** exp(-i*beta*sum X_i): implemented with RX(2*beta) on every qubit. It moves amplitude between neighboring bit patterns so that the phases interfere, which raises or lowers probabilities."),
  bullet("**Measurement:** all qubits are measured in the computational basis; each shot returns one bit string, with probability equal to the squared amplitude of that pattern. Samples are decoded into node-channel assignments and scored with the QUBO energy."),
  bullet("**Parameter tuning:** a classical optimizer adjusts gamma and beta to minimize the sampled mean energy. With p layers, the cost and mixer layers repeat with separate parameters."),
  p(`**Bit ordering.** Qiskit prints qubit 0 as the rightmost character of a bit string. Decoding reads qubit k as the k-th character from the right, and this was verified by comparing the circuit Hamiltonian's diagonal with the QUBO energy for all patterns (difference 0) and by decoding the best sample by hand.`),
  h2("8.1 Parameter-binding bug and correction"),
  p(`During development, circuit parameters were bound from a plain list [gamma, beta]. Qiskit orders circuit parameters alphabetically, so beta came before gamma and the two values were silently swapped. The circuits still were valid QAOA circuits, so every internal check passed, but the labels were wrong: the reported "gamma = 2.74, beta = 0.03" was in fact a mixer angle of 2.74 and a cost angle of 0.03, and the explanation that the optimum lies at small beta was incorrect. We found this while setting up the p = 2 experiment. Parameters are now bound by name, a test confirms that gamma drives the RZ/RZZ angles and beta drives the RX angles, and the grid ranges were corrected accordingly. All experiments were re-run. The corrected p = 1 figures (valid ${pc(P1.valid_pct)}, optimal ${pc(P1.optimal_pct)}) differ slightly from the pre-correction values (17.99% and 0.56%); **only corrected results are reported here.**`.replace("${pc(P1.valid_pct)}", pc(P1.valid_pct)).replace("${pc(P1.optimal_pct)}", pc(P1.optimal_pct))));

// 9 Architecture
C.push(h1("9. System Architecture"),
  p(`The network topology is turned into a weighted interference graph, then into binary variables, a QUBO and an Ising Hamiltonian. The Hamiltonian feeds the quantum branch (QAOA circuit, measurement and decoding), while an independent classical branch solves the same weighted graph exactly. A random-sampling baseline is scored the same way as the QAOA output. All branches meet in the evaluation and visualization stage.`),
  ...figure("report/architecture_diagram.png", "Figure 2. RescueMesh architecture. Blue: classical; purple: quantum (simulated); green: independent exact baseline; grey: random-sampling reference.", 620),
  table([2500, 6860], ["File", "Responsibility"], [
    ["main.py", "Runs all phases, prints checks and tables, saves results and figures"],
    ["config.py", "Fixed instance: nodes, channels, edges, penalty P"],
    ["graph_generator.py", "Builds the weighted interference graph (NetworkX)"],
    ["qubo_model.py", "QUBO matrix, bit-pattern helpers, QUBO-to-Ising conversion"],
    ["quantum_solver.py", "QAOA circuit, Aer simulation, parameter optimization, decoding"],
    ["classical_solver.py", "Exhaustive search and validation (no Qiskit)"],
    ["evaluation.py", "QUBO validation, sample statistics, verification from raw counts"],
    ["visualization.py", "Network plot, comparison figures, architecture diagram"],
  ]));

// 10 Implementation
C.push(h1("10. Implementation"),
  p(`The project is written in Python 3.12 with qiskit 2.6.2, qiskit-aer 0.18.2, numpy 2.5.4, scipy 1.18.1, networkx 3.7 and matplotlib 3.11.2 (pinned in requirements.txt). The circuit is built with a ParameterVector, transpiled once and executed on Qiskit Aer's state-vector simulator with a fixed simulator seed.`),
  bullet("The classical solver and the QUBO model use no Qiskit code, so each stage can be checked independently."),
  bullet("The independent verification step recomputes valid counts, optimal counts, percentages and mean energies from the raw bit strings using the Phase 1 formula directly, without reusing the QUBO matrix."),
  bullet("The full pipeline ran from a clean virtual environment created from the documented steps and produced results identical to earlier runs (runtimes excluded)."));

// 11 Experimental setup
C.push(h1("11. Experimental Setup"),
  table([3000, 6360], ["Item", "Setting"], [
    ["Instance", "5 nodes, 3 channels, 7 edges (Table in Section 3), P = 15"],
    ["Qubits / variables", "15 qubits; 2^15 = 32,768 bit patterns, 243 valid"],
    ["Simulator", "Qiskit Aer state-vector, noiseless, seed 42"],
    ["Sampling budget", `${n(SH)} samples for QAOA p = 1, QAOA p = 2 and random sampling`],
    ["Optimization shots", `${n(P1.optimization.shots_per_evaluation)} shots per circuit evaluation`],
    ["QAOA p = 1 tuning", `Grid of 43 gamma values x 61 beta values (2,623 evaluations), then COBYLA; ${n(P1.optimization.evaluations)} evaluations in total`],
    ["QAOA p = 2 tuning", `COBYLA from 8 starting points (2 built from the p = 1 optimum, 6 random with a fixed seed), two stages each; ${n(P2.optimization.evaluations)} evaluations in total`],
    ["p = 1 parameters", `gamma = ${P1.parameters.gamma[0].toFixed(4)}, beta = ${P1.parameters.beta[0].toFixed(4)}`],
    ["p = 2 parameters", `gamma = [${P2.parameters.gamma.map((x) => x.toFixed(4)).join(", ")}], beta = [${P2.parameters.beta.map((x) => x.toFixed(4)).join(", ")}]`],
    ["Baselines", "Exact exhaustive search (243 assignments); uniform random bit strings (same budget)"],
  ]),
  gap(),
  p(`The grid design for p = 1 was informed by an exact landscape scan (a diagnostic that is not available on real hardware): the energy is lowest at a small cost-phase gamma, so the gamma grid is dense on [0, 0.3] and coarse up to pi/2, while beta covers [0, pi]. The optimizer itself uses only sampled energies. p = 2 used a different optimization effort than p = 1 (fewer circuit evaluations, local search from several starts), so the two are not matched in effort.`));

// 12 Results
const exRow = ["Exhaustive search", "243 (all)", "243 (100%)", `${R.exact.n_optimal_assignments} (${pc((100 * R.exact.n_optimal_assignments) / R.exact.n_assignments)} of assignments)`, "6 of 6", "0", "0", "n/a (see note)"];
const mRow = (name, m) => [name, n(m.shots), `${n(m.valid_count)} (${pc(m.valid_pct)})`, `${m.optimal_count} (${pc(m.optimal_pct)})`, `${m.distinct_optimal_assignments} of 6`, String(m.best_valid_score), String(m.gap), f2(m.mean_energy_all_samples)];
C.push(h1("12. Results and Comparison"),
  p(`**Exhaustive search is exact; the other rows are sampled.** Exhaustive search enumerates every valid assignment, so its figures are exact counts of assignments, not samples. The other three rows are ${n(SH)} random draws each.`),
  table([1500, 1000, 1360, 1360, 900, 900, 600, 1740],
    ["Method", "Samples", "Valid (count, %)", "Optimal (count, %)", "Distinct optima", "Best valid score", "Gap", "Mean energy (all samples)"],
    [exRow, mRow("Random sampling", RND), mRow("QAOA p = 1", P1), mRow("QAOA p = 2", P2)]),
  p(`Note: the mean interference over the 243 valid assignments is ${f2(R.exact.mean_interference_over_valid)}. It is not comparable with the sampled mean energies, which include the penalty of invalid samples, so it is left out of the last column.`, { size: 18, italics: true }),
  p(`**Key observations.**`),
  bullet(`Every method reached the exact optimum (best valid score 0, gap 0). **The random baseline also found optimal allocations (${RND.optimal_count} samples).**`),
  bullet(`Valid samples: ${n(P1.valid_count)} (p = 1) and ${n(P2.valid_count)} (p = 2) versus ${RND.valid_count} for random sampling. Uniform sampling would be expected to give about ${expectedValid.toFixed(0)} valid samples out of ${n(SH)}.`),
  bullet(`Optimal samples: ${P1.optimal_count} (p = 1) and ${P2.optimal_count} (p = 2) versus ${RND.optimal_count} for random sampling and about ${expectedOptimal.toFixed(1)} expected under uniform sampling. The random baseline count is very small, so ratios computed from it are noisy.`),
  bullet(`QAOA found all 6 optimal assignments at both depths; random sampling found 2 of 6.`),
  bullet(`${invalidPct(P1)} (p = 1) and ${invalidPct(P2)} (p = 2) of QAOA samples are still invalid.`),
  bullet(`**p = 2 improvement is suggestive, not conclusive.** It is a single run with a different optimization effort (${n(P2.optimization.evaluations)} evaluations versus ${n(P1.optimization.evaluations)}), and no study over several random seeds was done.`),
  ...figure("results/fig1_valid_rates.png", `Figure 3. Share of valid allocations (counts shown). Random ${RND.valid_count}/${n(SH)}, QAOA p = 1 ${n(P1.valid_count)}/${n(SH)}, QAOA p = 2 ${n(P2.valid_count)}/${n(SH)}.`, 400),
  ...figure("results/fig2_optimal_rates.png", `Figure 4. Share of optimal allocations (counts shown: ${RND.optimal_count}, ${P1.optimal_count} and ${P2.optimal_count} out of ${n(SH)}).`, 400),
  ...figure("results/fig3_energy_distribution.png", "Figure 5. Energy distribution of all samples (left) and interference scores of valid samples (right).", 620),
  ...figure("results/fig4_best_vs_optimum.png", "Figure 6. Best valid score (all methods reach the optimum 0) and mean interference of valid samples.", 560),
  h2("12.1 Runtime"),
  table([4200, 2400, 2760], ["Step", "Wall-clock time", "Notes"], [
    ["Exhaustive search (243 assignments)", sec(RT.exhaustive), "Exact"],
    [`Random sampling (${n(SH)} samples)`, sec(RT.random_sampling), "Generate and decode"],
    [`QAOA p = 1 parameter optimization`, sec(RT.qaoa_p1_optimization), `${n(P1.optimization.evaluations)} circuit evaluations`],
    [`QAOA p = 1 final sampling (${n(SH)} shots)`, sec(RT.qaoa_p1_sampling), "Simulation"],
    [`QAOA p = 2 parameter optimization`, sec(RT.qaoa_p2_optimization), `${n(P2.optimization.evaluations)} circuit evaluations`],
    [`QAOA p = 2 final sampling (${n(SH)} shots)`, sec(RT.qaoa_p2_sampling), "Simulation"],
  ]),
  p(`Runtimes are from one run on one CPU and vary with machine load (earlier runs of the same code gave about 58 s and 21 s for the two optimizations). QAOA times are classical simulation of the circuit, not quantum-hardware time.`, { size: 18, italics: true }),
  ...figure("results/fig5_runtime.png", "Figure 7. Runtime comparison on a logarithmic scale.", 520));

// 13 Discussion
C.push(h1("13. Discussion"),
  bullet("**Why QAOA gives more valid samples than random sampling.** Invalid patterns carry the penalty and therefore high energy. The tuned cost and mixer layers shift probability toward lower-energy patterns, which are mostly valid."),
  bullet(`**Why most QAOA samples are still invalid.** Only 243 of 32,768 patterns are valid, and a shallow circuit reshapes the probabilities only partly. ${invalidPct(P1)} and ${invalidPct(P2)} of samples remain invalid.`),
  bullet("**Why finding the optimum is not quantum advantage.** Random sampling also found optimal allocations in the same budget. Advantage would require beating the best classical method as problems grow, which a 15-qubit noiseless simulation cannot show."),
  bullet(`**Why exhaustive search wins here.** With only 243 candidates it finds all six optima exactly in ${sec(RT.exhaustive)}, while QAOA needed thousands of simulated circuit runs for tuning. Exhaustive search grows exponentially with problem size, which motivates studying alternatives, but this experiment says nothing about where that crossover lies.`),
  bullet("**Effect of the penalty coefficient.** P = 15 places every invalid pattern at energy 15 or above (typically around 95 on average), so constraint terms dominate the Hamiltonian and the interference differences (2 to 6 per edge) are comparatively small. This makes the landscape rugged and explains why good cost-phase angles are tiny (about 0.03). A larger P would strengthen this effect."),
  bullet("**Why the instance is relatively easy.** The graph can be coloured with three channels without any clash, so the optimum is 0 and 6 of 243 valid assignments (about 2.5%) are optimal. Instances with unavoidable interference would be a stricter test."));

// 14 Limitations
C.push(h1("14. Limitations"),
  bullet("Small instance: 5 nodes, 15 qubits, synthetic interference weights."),
  bullet("Noiseless simulator only; no hardware execution and no noise model were tested."),
  bullet("No quantum speedup or advantage was demonstrated."),
  bullet("Results depend on classical parameter optimization. The gamma search covers only [0, pi/2] and the grid was informed by an exact diagnostic scan, so the tuned parameters are not guaranteed to be globally optimal."),
  bullet(`High invalid-measurement rate (${invalidPct(P1)} for p = 1, ${invalidPct(P2)} for p = 2).`),
  bullet("p = 2 is a single run with a different optimization effort; no multi-seed statistics."),
  bullet("The zero-interference optimum makes the instance relatively easy."),
  bullet("Runtime numbers come from one machine and vary between runs."));

// 15 Future
C.push(h1("15. Future Improvements"),
  bullet("Test harder instances with unavoidable interference and more nodes, and report results over many random seeds."),
  bullet("Add a noise model and, if available, run on real quantum hardware."),
  bullet("Reduce invalid samples with constraint-aware encodings or mixers, and study the effect of the penalty value."),
  bullet("Compare against stronger classical heuristics (for example simulated annealing or greedy colouring) on larger graphs."),
  bullet("Use measured radio-interference data instead of synthetic weights."));

// 16 Conclusion
C.push(h1("16. Conclusion"),
  p(`RescueMesh shows a complete and verified pipeline from a disaster-communication problem to a QUBO, an Ising Hamiltonian, a QAOA circuit and decoded allocations. On the five-node instance, QAOA produced many more valid and optimal samples than random sampling (${n(P1.valid_count)} and ${n(P2.valid_count)} valid, ${P1.optimal_count} and ${P2.optimal_count} optimal, versus ${RND.valid_count} and ${RND.optimal_count}), but random sampling also hit the optimum and exact classical search remains far cheaper. The results are a working demonstration on a noiseless simulator, not evidence of quantum advantage.`));

// 17 References
C.push(h1("17. References"),
  p("[1] E. Farhi, J. Goldstone and S. Gutmann, \"A Quantum Approximate Optimization Algorithm\", arXiv:1411.4028 (2014)."),
  p("[2] A. Lucas, \"Ising formulations of many NP problems\", Frontiers in Physics 2, 5 (2014), doi:10.3389/fphy.2014.00005."),
  p("[3] A. Javadi-Abhari et al., \"Quantum computing with Qiskit\", arXiv:2405.08810 (2024)."),
  p("[4] Qiskit Aer simulator, https://github.com/Qiskit/qiskit-aer."),
  p("[5] Software used: SciPy (https://scipy.org), NetworkX (https://networkx.org), Matplotlib (https://matplotlib.org)."));

const doc = new Document({
  creator: "RescueMesh", title: "RescueMesh technical report",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 25, bold: true, color: "2F5496" }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "RescueMesh | Page ", size: 18, font: FONT }), new TextRun({ children: [PageNumber.CURRENT], size: 18, font: FONT })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "report", "RescueMesh_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, buf.length, "bytes");
});
