"""One place through which every tab starts a background job.

Without this, each of the four job-starting tabs would have to connect and
disconnect the worker signals itself, and two tabs could end up both reacting to
the same outcome.  Instead a tab hands over a job plus one callback, and the
service takes care of the rest:

* reference curves a job computed are merged into :class:`~app.ui.app_state.AppState`
  on the GUI thread, which keeps that cache single-writer;
* progress and log lines are re-emitted once, for the window to show;
* only the tab that submitted the job gets its callback.

Main contents:
    * :class:`JobService` -- submit, cancel and busy state.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, Slot

from app.core.experiment import JobOutcome
from app.ui.app_state import AppState
from app.workers.run_worker import Job, JobRunner

LOGGER = logging.getLogger(__name__)

#: Signature of the callback a tab hands over with its job.
OutcomeCallback = Callable[[JobOutcome], None]


class JobService(QObject):
    """Starts jobs in the worker thread and routes their outcome back.

    Signals:
        progress: ``(done, total, message)`` of the running job.
        message: One log line of the running job.
        failed: ``(message, traceback)`` of a job that raised.
        busy_changed: ``True`` while a job runs, ``False`` when it ends.
        job_finished: A job ended, whatever the outcome; the tabs use it to
            re-enable their buttons.
    """

    progress = Signal(int, int, str)
    message = Signal(str)
    failed = Signal(str, str)
    busy_changed = Signal(bool)
    job_finished = Signal()

    def __init__(self, state: AppState, parent: Optional[QObject] = None) -> None:
        """Create a service bound to one application state.

        Args:
            state: State whose reference-curve cache receives what jobs compute.
            parent: Parent object.
        """
        super().__init__(parent)
        self._state = state
        self._runner = JobRunner(self)
        self._callback: Optional[OutcomeCallback] = None
        self._job_name = ""

        self._runner.progress.connect(self.progress)
        self._runner.message.connect(self.message)
        self._runner.finished_ok.connect(self._on_finished_ok)
        self._runner.failed.connect(self._on_failed)
        self._runner.cancelled.connect(self._on_cancelled)
        self._runner.busy_changed.connect(self._on_busy_changed)

    @property
    def is_busy(self) -> bool:
        """Whether a job is currently running."""
        return self._runner.is_busy

    @property
    def job_name(self) -> str:
        """Name of the running job, or an empty string when idle."""
        return self._job_name

    def submit(self, job: Job, on_outcome: Optional[OutcomeCallback] = None) -> bool:
        """Start a job, unless one is already running.

        Args:
            job: The job to run.
            on_outcome: Called on the GUI thread with the outcome, after the
                reference curves it produced have been merged into the state.

        Returns:
            ``True`` when the job was started.
        """
        if self.is_busy:
            self.message.emit(
                f"'{self._job_name}' is still running; wait for it or press Cancel."
            )
            return False

        self._callback = on_outcome
        self._job_name = getattr(job, "name", type(job).__name__)
        started = self._runner.start(job, known_ground_truth=self._state.ground_truth)
        if not started:
            self._callback = None
            self._job_name = ""
        return started

    def cancel(self) -> None:
        """Ask the running job to stop at its next cancellation check."""
        self._runner.cancel()

    def shutdown(self, timeout_ms: int = 30_000) -> bool:
        """Cancel and wait, so no job outlives the window.

        Args:
            timeout_ms: How long to wait for the thread.

        Returns:
            ``True`` when the worker thread finished in time.
        """
        return self._runner.wait_for_finish(timeout_ms)

    @Slot(object)
    def _on_finished_ok(self, outcome: object) -> None:
        """Merge the reference curves, then hand the outcome to the tab."""
        callback, self._callback = self._callback, None
        if not isinstance(outcome, JobOutcome):
            LOGGER.error("A job returned %s instead of a JobOutcome.", type(outcome))
            return

        self._state.add_ground_truths(outcome.ground_truths)
        if callback is not None:
            callback(outcome)

    @Slot(str, str)
    def _on_failed(self, message: str, details: str) -> None:
        """Forward a failure and forget the callback."""
        self._callback = None
        self.failed.emit(message, details)

    @Slot()
    def _on_cancelled(self) -> None:
        """Forget the callback of a cancelled job."""
        self._callback = None

    @Slot(bool)
    def _on_busy_changed(self, busy: bool) -> None:
        """Track the busy state and tell the tabs when a job ends."""
        if not busy:
            self._job_name = ""
            self.job_finished.emit()
        self.busy_changed.emit(busy)
