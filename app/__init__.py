"""Static autofocusing application (SEM focal stacks).

The package is split into four layers so that each part can be read, graded and
tested on its own:

* ``app.core``    -- pure Python: image sets, focus measures, evaluator,
                     algorithm adapters, experiments, export.  No Qt imports.
* ``app.plots``   -- pure matplotlib drawing functions ``(figure, data) -> None``.
* ``app.workers`` -- Qt worker objects that run core jobs off the GUI thread.
* ``app.ui``      -- the Qt widgets, tabs and the main window.

The search and focus-measure algorithms themselves live in the read-only
``autofocus.algorithms`` package and are only ever imported, never copied.
"""

__all__ = ["APP_NAME", "APP_VERSION"]

APP_NAME = "Autofocus"
APP_VERSION = ""
