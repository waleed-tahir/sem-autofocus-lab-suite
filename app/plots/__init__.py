"""Pure matplotlib drawing functions.

Every function here takes a :class:`matplotlib.figure.Figure` plus the data to
draw and returns ``None``.  None of them touches Qt, reads a file or saves a
file, which keeps the drawing code testable and lets the same function serve the
embedded canvas and the PNG export.

Modules:
    * :mod:`app.plots.style`             -- colours, markers and axis styling.
    * :mod:`app.plots.focus_curve`       -- reference curve with the visited frames.
    * :mod:`app.plots.search_path`       -- visited frame against step number.
    * :mod:`app.plots.quadratic_fit_plot`-- the fit window and its parabola.
    * :mod:`app.plots.algorithm_bars`    -- cost and accuracy per algorithm.
    * :mod:`app.plots.speed_comparison`  -- one curve per scanning speed.
    * :mod:`app.plots.measure_comparison`-- one curve per focus measure.
    * :mod:`app.plots.robustness`        -- error and success rate against noise.
"""
