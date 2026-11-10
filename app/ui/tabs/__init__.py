"""Workflow tabs of the application.

Lab Submission Edition:
1. :mod:`app.ui.tabs.datasets_tab` -- Load image stacks, browse frames and metadata.
2. :mod:`app.ui.tabs.run_tab` -- Search algorithms & focus measure controls.
3. :mod:`app.ui.tabs.results_tab` -- Sharpest frame output, metrics, and sortable runs table.
4. :mod:`app.ui.tabs.run_results_tab` -- Unified Run & Results workspace.
5. :mod:`app.ui.tabs.focus_curve_tab` -- Focus curve trajectory and step replay.
6. :mod:`app.ui.tabs.algorithm_comparison_tab` -- Cost against accuracy (Global vs Gradient).
7. :mod:`app.ui.tabs.export_tab` -- CSV, JSON, PNG exports and session persistence.
"""

from __future__ import annotations

from .datasets_tab import DatasetsTab
from .run_tab import RunTab
from .results_tab import ResultsTab
from .run_results_tab import RunAndResultsTab
from .focus_curve_tab import FocusCurveTab
from .algorithm_comparison_tab import AlgorithmComparisonTab
from .export_tab import ExportTab

__all__ = [
    "DatasetsTab",
    "RunTab",
    "ResultsTab",
    "RunAndResultsTab",
    "FocusCurveTab",
    "AlgorithmComparisonTab",
    "ExportTab",
]
