"""Pure-Python core of the autofocus application.

No module in this package imports Qt or matplotlib, so every piece can be used
from a worker thread or from a plain script.  The modules are:

* :mod:`app.core.dataset`        -- image sets, lazy frame loading, working distances.
* :mod:`app.core.focus_measures` -- registry of the five focus measures.
* :mod:`app.core.evaluator`      -- the ``eval_func`` the search algorithms call.
* :mod:`app.core.run_result`     -- the unified result record and its table columns.
* :mod:`app.core.algorithms`     -- registry of searches plus their adapters.
* :mod:`app.core.curve_stats`    -- focus-curve descriptors (FWHM, noise, peaks).
* :mod:`app.core.experiment`     -- ground truth and the runnable jobs.
* :mod:`app.core.export`         -- CSV / JSON export and session files.
"""
