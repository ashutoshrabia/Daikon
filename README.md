# Daikon
This repository contains two independent projects:

## 1) `vivaran_binaries/` — Spec-driven testing + rule mining on C binaries
A systems project from last semester focused on automatically testing and analyzing **25 C string-function binaries**.

**Highlights**
- Spec-driven test harness (Python + C) that auto-generates argument vectors from JSON specs  
- Builds and runs **instrumented binaries** using GCC with **ASan/UBSan**
- Executes experiments, records outcomes, and produces labeled traces suitable for rule mining / analysis

**Typical workflow**
- Provide/extend JSON specs for each function/binary
- Compile with sanitizers enabled
- Run harness to generate inputs + collect labeled results

---

## 2) `vivaran_interpretability/` — ML interpretability via invariants + SMT refinement
Current UGP project on extracting **human-readable rules** that characterize a model’s *accepted region* on the **UCI Adult (Census Income)** dataset.

**High-level pipeline**
1. Train a neural network (MLP) on Adult (one-hot categoricals + scaled numerics)
2. Collect accepted samples (positive / high-income region to explain)
3. Run **Daikon** to mine candidate invariants (logical rules)
4. Refine rules with an **SMT loop (Z3)**:
   - Negate candidate invariants
   - Synthesize counterexamples
   - Validate counterexamples using the neural model as an oracle
   - Prune/relax/tighten rules until convergence
5. Output a compact, stable set of accepted rules

**Tech stack**
Python, pandas/NumPy, TensorFlow/Keras, Z3, Daikon (Java), joblib.

---

## Repository structure
- `vivaran_binaries/` — binary testing + sanitizers + spec-driven harness
- `vivaran_interpretability/` — Adult dataset pipeline + Daikon + Z3 refinement

## Notes
- The two directories are separate projects and can be run independently.
- For the interpretability project, ensure Java (for Daikon) and Z3 are installed and available on PATH.
