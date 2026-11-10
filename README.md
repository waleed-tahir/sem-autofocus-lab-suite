# SEM Autofocus Lab Suite (Lab Submission Edition)

A high-performance desktop application for scanning electron microscopy (SEM) autofocusing evaluation with a clean, minimal user interface and organized code.

## Key Features & Lab Workflow

### 1. Minimal 4-Tab Interface
- **Datasets**: Load SEM image stacks, calibrate geometry (working distances), and inspect individual frames.
- **Run & Results**: Unified execution controls and output inspection. Select target datasets, algorithms, and focus measures; view the sharpest frame, numeric summaries, and sortable results table.
- **Focus Curve**: Full focal curve trajectory HUD with metric cards, playback controls, live parameter sliders, and step-by-step execution telemetry log.
- **Algorithm Comparison**: Direct trade-off analysis comparing **Global Scan** vs **Gradient Search** with interactive comparative charts, key performance metrics (KPIs), and exposure/beam-time savings matrix.

### 2. Supported Focus Measures
- **Normalized Variance**:
  $$\text{Score} = \frac{\text{Var}(I)}{\text{Mean}(I) + \varepsilon}$$
  Intensity spread normalized by mean brightness.
- **Mean-Normalized Variance**:
  $$\text{Score} = \frac{\text{Var}(I)}{\text{Mean}(I)^2 + \varepsilon}$$
  Illumination-scale and beam-drift invariant formulation.

### 3. Supported Search Algorithms
- **Global Scan (exhaustive)**: Linear sweep across all focal planes $[0, \text{max\_idx}]$; serves as the ground-truth baseline.
- **Gradient Search**: Coarse-to-fine gradient ascent: initial directional slope probe, ascending gradient climb, overshoot reversal, and decayed interval refinement with step-by-step execution telemetry.

## Requirements

- Python 3.10+
- Dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Execute with the batch launcher or Python:
```bash
run.bat
```
or
```bash
python main.py
```

## Running Unit & Algorithm Tests

```bash
python autofocus/algorithms/test_extracted_algorithms.py
```
