# Native Autofocus Desktop Application (Fluent Edition)

A high-performance native desktop implementation of scanning electron microscopy (SEM) autofocusing algorithms with an edge-to-edge Fluent user interface.

## Overview

This application provides a completely redesigned, standalone desktop architecture for SEM focal-series acquisition and focus search optimization:
- **4-Tab Unified Workflow**: `Datasets`, `Run & Results`, `Curves & Fit`, and `Comparative Analysis`.
- **Hardware-Accelerated Visualizations**: Interactive PyQtGraph & Matplotlib plotting pipelines with real-time probe overlays.
- **Smart Disk Caching**: On-disk persistent caching for precomputed ground truth curves and search runs.
- **Robust Algorithms**: Comprehensive suite of focus measure operators (Normalized Variance, Variance of Laplacian, Laplacian of Gaussian, Modified Laplacian SML) and search algorithms (Global scan, Coarse-Fine Hybrid, Gradient search, Parabolic polynomial fitting).

## Requirements

- Python 3.10+
- Windows 10 / Windows 11 (or compatible Linux/macOS desktop environments)

Install runtime dependencies:
```bash
python -m pip install -r requirements.txt
```

## Running the Application

Execute via the included batch launcher or Python:
```bash
python main.py
```

## Packaging Standalone Executable

To compile into a standalone Windows executable with all assets and runtime libraries:
```bash
pyinstaller autofocus.spec --clean
```
The compiled output will be generated in `dist/Autofocus/Autofocus.exe`.
