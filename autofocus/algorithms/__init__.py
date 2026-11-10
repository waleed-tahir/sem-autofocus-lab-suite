"""
Streamlined Algorithm Package for Electron Microscope Autofocus (Lab Submission Edition)

Core algorithms:
- Search:
    * Global Linear Scan Search (global_scan_search.py)
    * Gradient Descent / Ascent Search (gradient_descent_search.py)
- Focus Score:
    * Normalized Variance (normalized_variance.py)
    * Mean-Normalized Variance (normalized_variance.py)
- Refinement:
    * Quadratic Polynomial Curve Fitting (quadratic_fit.py)
"""

from __future__ import annotations

from .global_scan_search import (
    global_scan_search,
    global_search,
    SearchResult,
)
from .gradient_descent_search import (
    gradient_descent_search,
    gradient_ascent_search,
    gradient_search,
    gradient_ascent,
    verify_peak,
)
from .quadratic_fit import (
    quadratic_fit,
    fit_quadratic_vertex,
    QuadraticFitResult,
)
from .normalized_variance import (
    normalized_variance,
    mean_normalized_variance,
)

__all__ = [
    # Search algorithms
    "global_scan_search",
    "global_search",
    "gradient_descent_search",
    "gradient_ascent_search",
    "gradient_search",
    "gradient_ascent",
    "verify_peak",
    "SearchResult",
    # Fine refinement
    "quadratic_fit",
    "fit_quadratic_vertex",
    "QuadraticFitResult",
    # Focus score algorithms
    "normalized_variance",
    "mean_normalized_variance",
]
