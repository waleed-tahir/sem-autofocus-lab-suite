# Standalone Autofocus Algorithms (Lab Submission Edition)

This package contains the core algorithms required for the scanning electron microscope (SEM) autofocusing lab:

## Focus Measures
- **Normalized Variance (`normalized_variance.py`)**:
  - `normalized_variance`: Intensity variance normalized by mean brightness: $Var(I) / Mean(I)$
  - `mean_normalized_variance`: Intensity variance normalized by mean squared: $Var(I) / Mean(I)^2$ (illumination-scale invariant)

## Search Algorithms
- **Global Scan (`global_scan_search.py`)**: Exhaustive linear sweep across all focal planes $[0, max\_idx]$. Guaranteed global optimum, serving as the baseline reference.
- **Gradient Search (`gradient_descent_search.py`)**: Sub-linear gradient ascent using adaptive centred finite differences and statistical noise verification against fake local maxima.

## Sub-frame Refinement
- **Quadratic Fit (`quadratic_fit.py`)**: Parabolic polynomial fitting around the peak to extract sub-frame focal position and working distance.
