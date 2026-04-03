# r2y — Project governance document

**Project:** response-yolo (r2y)
**Purpose:** Modernize Response-2000 as a web application (Python/FastAPI + React)
**Created:** 2026-04-03
**Status:** Pre-development

---

## 1. Scope

### 1.1 In scope

r2y replicates the **Response-2000** sectional analysis program for reinforced concrete beams and columns. The target feature set for the initial release:

- Cross-section definition: rectangular, T-beam, I-beam, and circular geometries
- Material models: concrete (Popovics/Thorenfeldt/Collins compression, Bentz 1999 tension stiffening, Vecchio-Collins 1986 compression softening) and reinforcing steel (bilinear with strain hardening)
- Layered sectional analysis using the Modified Compression Field Theory (MCFT)
- Longitudinal stiffness method for shear stress distribution (Bentz, Chapter 6)
- Load stepping: full load-deformation response from zero to failure
- Sectional response to arbitrary combinations of axial load (N), moment (M), and shear (V)
- M-V interaction diagram
- 9-plot visualization matching the Response-2000 visual style
- Crack diagram with widths and angles

### 1.2 Out of scope

- Membrane-2000 (biaxial plate analysis)
- Shell-2000 (out-of-plane forces)
- Triax-2000 (3D block analysis)
- GUI input forms (CLI-based input for initial release)
- Full member analysis (integration along beam length) — deferred to future work
- Prestressing (may be added later but not in initial release)
- Long-term effects (creep, shrinkage, relaxation)
- Code checks (AASHTO, ACI, CSA interaction diagrams)

### 1.3 Scope changes

Any scope change must be recorded in Section 9 (Decision log) with rationale.

---

## 2. Architecture

### 2.1 Tech stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Analysis engine | Python 3.11+ | NumPy for numerics |
| API | FastAPI | Serves analysis results as JSON |
| Frontend | React | Visualization only (no input forms) |
| Data format | JSON | Single consolidated schema (see Section 3) |
| Testing | pytest | Unit + integration tests |

### 2.2 Project structure (target)

```
r2y/
├── r2y/                    # Python package
│   ├── __init__.py
│   ├── schema.py           # Pydantic models for the consolidated JSON schema
│   ├── materials/          # Constitutive models
│   │   ├── concrete.py
│   │   └── steel.py
│   ├── section/            # Cross-section geometry and layering
│   │   ├── geometry.py
│   │   └── layers.py
│   ├── mcft/               # MCFT biaxial element solver
│   │   ├── solver.py
│   │   └── crack_check.py
│   ├── analysis/           # Sectional analysis engine
│   │   ├── sectional.py    # Layered integration + longitudinal stiffness method
│   │   └── response.py     # Load stepping / full response
│   └── api/                # FastAPI app
│       └── main.py
├── frontend/               # React app
│   └── src/
│       ├── plots/          # 9-plot components
│       └── crack/          # Crack diagram component
├── tests/
│   ├── unit/               # Per-module unit tests
│   ├── integration/        # End-to-end analysis tests
│   └── validation/         # Comparison against R2K outputs (Session 6)
├── examples/               # Example JSON input files
├── cli.py                  # CLI entry point
└── r2y-governance.md       # This document
```

### 2.3 Design principles

1. **Single JSON schema governs all data.** Every input, intermediate result, and output is represented in one consolidated schema. This enables modular execution, human inspection, and test reproducibility.

2. **Modules are independently testable.** Each module (materials, section, mcft, analysis) reads from and writes to the JSON schema. A module can be run in isolation given the right JSON input.

3. **Analysis engine has zero frontend dependencies.** The Python package produces complete results as JSON. The React frontend is a pure visualization layer.

4. **CLI is the primary interface.** Input is a JSON file. Output is a JSON file. The CLI is thin — it deserializes, calls the engine, serializes.

---

## 3. Consolidated JSON schema

The schema serves three roles: program input, program output, and inter-module communication. A single JSON file fully describes a problem and its solution.

### 3.1 Schema overview

```
R2YModel
├── metadata                # Version, units, description
├── materials               # Concrete and steel definitions
│   ├── concrete[]          # One or more concrete types
│   └── steel[]             # One or more steel types
├── section                 # Cross-section geometry
│   ├── geometry            # Shape definition (type, dimensions)
│   ├── reinforcement[]     # Bar layers (area, depth, material ref)
│   └── stirrups            # Transverse reinforcement (area/spacing, material ref)
├── loading                 # Analysis control
│   ├── axial_load          # Applied N (positive = compression)
│   ├── load_type           # "sectional" | "full_response"
│   └── increments          # Number of load steps
├── results (output)        # Populated by the engine
│   ├── layers[]            # Per-layer state at each load step
│   │   ├── y_position
│   │   ├── epsilon_x       # Longitudinal strain
│   │   ├── epsilon_y       # Transverse strain  
│   │   ├── gamma_xy        # Shear strain
│   │   ├── sigma_x         # Longitudinal stress
│   │   ├── tau_xy          # Shear stress
│   │   ├── fc1, fc2        # Principal concrete stresses
│   │   ├── theta           # Crack angle
│   │   └── crack_width     # Crack width (mm)
│   ├── response[]          # Load step history
│   │   ├── step
│   │   ├── moment
│   │   ├── shear
│   │   ├── curvature
│   │   ├── gamma_xy_mid    # Mid-depth shear strain
│   │   └── epsilon_top, epsilon_bot
│   ├── interaction         # M-V interaction diagram points
│   └── failure             # Failure mode and load at failure
```

### 3.2 Schema design rules

1. All field names use `snake_case`.
2. Material references are by `id` string (e.g., `"concrete_1"`), not by index.
3. Units are declared once in `metadata.units` (`"SI"` or `"US"`). All values conform.
4. Arrays of layer results are ordered top-to-bottom (y = 0 at top fiber).
5. `results` is absent or `null` in input files; populated by the engine in output files.
6. The schema is versioned. `metadata.schema_version` tracks breaking changes.

### 3.3 Schema implementation

Pydantic v2 models in `r2y/schema.py`. Serialization via `.model_dump_json()`. The CLI reads and writes this schema exclusively.

---

## 4. Validation strategy

### 4.1 Philosophy

**We validate r2y against Response-2000 software output, not against experimental data.** Bentz validated R2K against experiments (Chapter 8–10 of the thesis). Our job is to reproduce R2K's numerical output for identical inputs. If r2y matches R2K, it inherits R2K's experimental validation.

### 4.2 Validation tiers

| Tier | What | How | When |
|------|------|-----|------|
| **Unit tests** | Individual functions produce correct intermediate values | pytest assertions against hand-calculated or textbook values | Every session, during development |
| **Smoke tests** | Modules run without error on representative inputs | JSON in → JSON out, no crashes | Every session, end of session |
| **Output tests** | r2y full results match R2K results for the same section and loading | Compare r2y JSON output against R2K-generated reference data | Session 6 |

### 4.3 Session 6 — R2K comparison (future)

Response-2000 does not have a known CLI or scriptable interface. Reference data will be generated by:

1. Running the R2K Windows desktop application manually (or via Cowork automation)
2. Entering identical cross-section definitions and loadings
3. Exporting or transcribing R2K's numerical output
4. Storing as JSON test fixtures in `tests/validation/`

Comparison criteria (per load step):
- Moment within ±1% of R2K
- Shear within ±1% of R2K  
- Curvature within ±2% of R2K
- Failure load within ±2% of R2K
- Failure mode matches (shear vs. flexure)

Tolerances are initial targets and may be adjusted based on findings.

### 4.4 Test beams

Priority test cases from the thesis (to be generated in Session 6):

1. **Simple rectangular beam** — basic case, no prestressing
2. **T-beam with stirrups** — the 1m deep T-beam from Chapter 6 (f'c = 100 MPa)
3. **Angelakos beams** — large, lightly reinforced, varying concrete strength (Chapter 10)
4. **Shioya beam** — 3000mm deep, 36m long, uniformly loaded (Chapter 10)

---

## 5. Session plan

Each session corresponds to one Claude Code usage block (within 5x plan limits). Sessions are sequential — each builds on the prior.

### Session 1: Foundation

**Goal:** Establish the project, implement material models, cross-section builder, and layer system. Define and implement the consolidated JSON schema.

**Deliverables:**
- [ ] Project structure created per Section 2.2
- [ ] `r2y/schema.py` — full Pydantic schema (Section 3)
- [ ] `r2y/materials/concrete.py` — Popovics/Thorenfeldt/Collins, Bentz 1999 tension stiffening, Vecchio-Collins 1986 softening
- [ ] `r2y/materials/steel.py` — bilinear with strain hardening
- [ ] `r2y/section/geometry.py` — rectangular and T-beam definitions
- [ ] `r2y/section/layers.py` — layer generation including dynamic subdivision
- [ ] `cli.py` — reads JSON input, dumps section/material summary
- [ ] `examples/rect_beam.json` — example input file
- [ ] Unit tests for all material curves (stress-strain values at key points)
- [ ] Unit tests for layer generation

**Acceptance criteria:**
- `python cli.py examples/rect_beam.json` runs without error and prints a summary
- Material model unit tests pass
- JSON schema round-trips (load → dump → load produces identical object)

**Exit artifact:** Working material models + section builder, validated by unit tests.

---

### Session 2: MCFT engine

**Goal:** Implement the 2D MCFT biaxial element solver — the analytical core that every layer in the cross-section will use.

**Deliverables:**
- [ ] `r2y/mcft/solver.py` — given (εx, εy, γxy), iterate to MCFT equilibrium
- [ ] `r2y/mcft/crack_check.py` — 2D crack check per Chapter 4
- [ ] Tangent stiffness matrix calculation [Dxx, Dyy, Dxy]
- [ ] Shear on crack calculation and limiting
- [ ] Unit tests: known strain states → verify stress output
- [ ] Smoke test: sweep εx from 0 to 10 mm/m, verify reasonable stress-strain curve

**Acceptance criteria:**
- For a biaxially loaded element with known reinforcement, the solver converges and produces stresses consistent with MCFT equilibrium (sum of forces = 0 in x and y)
- Crack check correctly limits concrete tension when steel yields at a crack
- Tangent stiffness matrix is symmetric and positive-definite for stable states

**Exit artifact:** Working MCFT point solver, independently testable via JSON.

---

### Session 3: Sectional analysis

**Goal:** Integrate the MCFT solver across the depth of a beam cross-section using the longitudinal stiffness method. Implement load stepping.

**Deliverables:**
- [ ] `r2y/analysis/sectional.py` — given (N, M, V) and a cross section, solve for the full stress/strain state through the depth
- [ ] Longitudinal stiffness method for shear stress distribution (Chapter 6)
- [ ] Equilibrium iteration (plane sections remain plane)
- [ ] `r2y/analysis/response.py` — load stepping from zero to failure
- [ ] M-V interaction diagram generation
- [ ] Full `results` block populated in the JSON schema
- [ ] Integration tests: rectangular beam from zero to failure

**Acceptance criteria:**
- Sectional analysis converges for a representative beam under combined M and V
- Shear stress profile integrates to the applied shear force (equilibrium check)
- Axial force equilibrium: sum of layer forces = applied N
- Moment equilibrium: sum of layer force × arm = applied M
- Load stepping traces a reasonable load-deformation curve (linear elastic at low load, softening near failure)

**Exit artifact:** Complete analysis engine. `python cli.py examples/rect_beam.json --output results.json` produces a full results JSON.

---

### Session 4: Visualization

**Goal:** Build the React frontend that renders r2y results in the classic Response-2000 visual style.

**Deliverables:**
- [ ] React project scaffolded (Vite + React)
- [ ] 9-plot General view: stress, strain, and shear distributions over beam depth
- [ ] Crack diagram with crack widths and angles
- [ ] Control plots: V vs. γ (shear-strain) and M vs. φ (moment-curvature)
- [ ] Load stage navigation (click or keyboard to step through load history)
- [ ] Visual styling matching R2K (plot colors, axis labels, grid style)
- [ ] Reads results JSON directly (no API needed yet)

**Acceptance criteria:**
- Loading a results JSON renders all 9 plots correctly
- Crack diagram shows inclined cracks with widths labeled
- Plots are visually recognizable to an R2K user
- Load stage selector works (stepping through shows progressive cracking/failure)

**Exit artifact:** Standalone React app that visualizes any r2y results JSON.

---

### Session 5: Integration

**Goal:** Wire the FastAPI backend to the React frontend. End-to-end: JSON input → analysis → visualization in browser.

**Deliverables:**
- [ ] `r2y/api/main.py` — FastAPI app with POST `/analyze` endpoint
- [ ] API accepts JSON input, returns JSON results
- [ ] React frontend calls API instead of reading static JSON
- [ ] Loading/error states in the UI
- [ ] End-to-end demo with at least 2 example beams
- [ ] Docker or simple run script for local development
- [ ] README with setup and usage instructions

**Acceptance criteria:**
- `docker compose up` (or equivalent) starts both backend and frontend
- Submitting a JSON input via CLI or API returns complete results
- Browser displays the 9-plot view for the analyzed section
- Two different beam geometries produce visually distinct results

**Exit artifact:** Running web application, end-to-end.

---

### Session 6: Validation against R2K (future)

**Goal:** Generate R2K reference data and compare r2y output.

**Method:**
1. Run Response-2000 desktop application (manually or via Cowork)
2. Enter test beam definitions matching r2y example inputs exactly
3. Record R2K output: M-φ curve, V-γ curve, stress profiles at key load stages, failure load and mode
4. Store as JSON fixtures in `tests/validation/`
5. Write comparison tests with tolerances per Section 4.3

**Test cases:** Per Section 4.4.

---

## 6. Key technical references

All analysis methods are documented in:

- **Thesis:** "Sectional Analysis of Reinforced Concrete Members" by Evan C. Bentz, University of Toronto, 2000. Available in project knowledge as `thesis.pdf`.
- **Appendix A:** User manual for the four programs. Available as `appen_a.pdf`.
- **Key chapters:**
  - Chapter 3: MCFT implementation in 2D (constitutive relations, iteration)
  - Chapter 4: Crack check (1D, 2D, and flexural yield)
  - Chapter 5: Constitutive models (concrete tension, compression softening)
  - Chapter 6: Longitudinal stiffness method (the core innovation)
  - Chapter 7: Response-2000 member analysis details
  - Chapter 10: Experimental verification and beam database

---

## 7. Conventions

- **Shorthand:** r2y = response-yolo, R2K = Response-2000
- **Sign convention:** Compression positive (following R2K convention — confirm in Session 1)
- **Coordinate system:** y = 0 at top fiber, positive downward
- **Units:** SI metric by default (MPa, mm, kN). US customary as alternate.
- **Python style:** Black formatter, type hints on all public functions
- **Git branching:** `main` + feature branches per session (`session-1-foundation`, etc.)

---

## 8. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Longitudinal stiffness method is complex to implement correctly | Core feature doesn't work | Study Chapter 6 in detail before coding. Implement incrementally with equilibrium checks at each step. |
| MCFT iteration may not converge for some load states | Analysis fails mid-response | Implement robust iteration with line search and fallback strategies. Dynamic layering helps. |
| R2K output data is hard to extract (no CLI) | Session 6 is slow/incomplete | Start with simple beams. Use Cowork if possible. Manually transcribe key data points if needed. |
| 5 sessions may not be enough for full feature set | Incomplete at end of plan | Sessions are prioritized. Sessions 1-3 produce a working engine. Sessions 4-5 add visualization. Core value is in the engine. |
| JSON schema may need revision as we learn more | Rework across modules | Schema is versioned. Design for extension (optional fields, nullable results). |

---

## 9. Decision log

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| D001 | 2026-04-03 | Scope limited to Response-2000 only (no Membrane, Shell, Triax) | Focus and achievability within 5 sessions |
| D002 | 2026-04-03 | CLI-based input, R2K-style visual output | Maximize analysis fidelity first, input UX later |
| D003 | 2026-04-03 | Single consolidated JSON schema for all I/O | Enables modularity, human inspection, test reproducibility |
| D004 | 2026-04-03 | Validate against R2K output, not experimental data | R2K is already experimentally validated. Our job is numerical reproduction. |
| D005 | 2026-04-03 | Python backend + React frontend | FastAPI for API, React for visualization. Clean separation. |
| D006 | 2026-04-03 | Defer prestressing to future work | Reduces Session 1-3 complexity significantly |

---

## 10. Revision history

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-04-03 | Claude (PM) | Initial governance document |
