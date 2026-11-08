"""One module per tab of the main window.

In the order they appear:

1.  :mod:`app.ui.tabs.datasets_tab`             -- load image sets, browse frames.
2.  :mod:`app.ui.tabs.run_tab`                  -- choose and start the searches.
3.  :mod:`app.ui.tabs.results_tab`              -- the required outputs.
4.  :mod:`app.ui.tabs.focus_curve_tab`          -- focus curve and search path.
5.  :mod:`app.ui.tabs.fine_fit_tab`             -- the quadratic fit, zoomed in.
6.  :mod:`app.ui.tabs.algorithm_comparison_tab` -- cost against accuracy.
7.  :mod:`app.ui.tabs.speed_comparison_tab`     -- the four scanning speeds.
8.  :mod:`app.ui.tabs.measure_comparison_tab`   -- the five focus measures.
9.  :mod:`app.ui.tabs.robustness_tab`           -- accuracy against injected noise.
10. :mod:`app.ui.tabs.export_tab`               -- CSV, JSON, PNG and sessions.

:mod:`app.ui.tabs.common` holds the pieces they share: the sortable table, the
selector lists and the small info panel.
"""
