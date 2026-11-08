"""Qt workers that run core jobs off the GUI thread.

The only module here is :mod:`app.workers.run_worker`.  It owns the boundary
between the pure-Python jobs of :mod:`app.core.experiment` and the Qt event
loop: the job runs in a ``QThread`` and reports back with signals, so the
window stays responsive and no widget is ever touched from the worker.
"""
