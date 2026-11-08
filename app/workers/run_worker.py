"""Runs a core job in a background thread.

A focus search reads hundreds of images, which takes seconds.  Doing that on the
GUI thread would freeze the window, so every job runs here instead.

Main contents:
    * :class:`RunWorker` -- the ``QObject`` that executes one job and emits
      progress, log lines and the outcome.
    * :class:`JobRunner` -- owns the ``QThread``, starts a job and cancels it.

Rules this module keeps:

* Nothing inside :meth:`RunWorker.run` touches a widget or a matplotlib figure.
  Results travel back as signal payloads and are drawn on the GUI thread.
* Cancellation is a flag the GUI sets and the job polls between steps, so a
  running search stops at its next frame instead of being killed mid-call.
"""

from __future__ import annotations

import logging
import traceback
from typing import Mapping, Optional, Protocol

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.core.experiment import GroundTruth, JobCancelledError, JobContext, JobOutcome

LOGGER = logging.getLogger(__name__)


class Job(Protocol):
    """What :class:`RunWorker` needs from a job.

    Attributes:
        name: Short description used in log and status messages.
    """

    name: str

    def execute(self, ctx: JobContext) -> JobOutcome:
        """Run the job and return its outcome."""
        ...


class RunWorker(QObject):
    """Executes one job and reports back through signals.

    The object is moved into a :class:`~PySide6.QtCore.QThread` before
    :meth:`run` is invoked, so every line of :meth:`run` happens off the GUI
    thread.

    Signals:
        progress: ``(done, total, message)`` while the job advances.
        message: One log line for the log panel.
        finished_ok: The job finished; carries its :class:`JobOutcome`.
        failed: The job raised; carries a user-facing message and the traceback.
        cancelled: The job stopped because the user asked for it.
        done: Always emitted last, whatever the outcome, so the GUI can tidy up.
    """

    progress = Signal(int, int, str)
    message = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str, str)
    cancelled = Signal()
    done = Signal()

    def __init__(
        self,
        job: Job,
        known_ground_truth: Optional[Mapping[tuple[str, str], GroundTruth]] = None,
    ) -> None:
        """Prepare a worker for one job.

        Args:
            job: The job to execute.
            known_ground_truth: Reference curves computed earlier.  The job only
                reads this snapshot; anything it computes comes back in the
                outcome, so the GUI thread stays the only writer of the cache.
        """
        super().__init__()
        self._job = job
        self._known_ground_truth = dict(known_ground_truth or {})
        self._cancel_requested = False

    @property
    def job_name(self) -> str:
        """Name of the job this worker runs."""
        return getattr(self._job, "name", type(self._job).__name__)

    def request_cancel(self) -> None:
        """Ask the job to stop at its next cancellation check.

        Safe to call from the GUI thread: it only sets a flag that the job polls.
        """
        self._cancel_requested = True

    def is_cancelled(self) -> bool:
        """Whether a cancellation has been requested."""
        return self._cancel_requested

    @Slot()
    def run(self) -> None:
        """Execute the job, translating its outcome into signals.

        Every exception is caught on purpose: an exception escaping a slot in a
        ``QThread`` would end the thread silently.  The error is logged, sent to
        the log panel and raised to the user as a dialog instead.
        """
        self.message.emit(f"Started: {self.job_name}.")
        ctx = JobContext(
            report=self._report,
            log=self.message.emit,
            cancelled=self.is_cancelled,
            known_ground_truth=self._known_ground_truth,
        )

        try:
            outcome = self._job.execute(ctx)
        except JobCancelledError:
            LOGGER.info("Job '%s' was cancelled by the user.", self.job_name)
            self.message.emit(f"Cancelled: {self.job_name}.")
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001 - see the docstring above.
            LOGGER.exception("Job '%s' failed.", self.job_name)
            self.message.emit(f"Failed: {self.job_name} - {exc}")
            self.failed.emit(str(exc), traceback.format_exc())
        else:
            self.message.emit(f"Finished: {self.job_name}. {outcome.message}")
            self.finished_ok.emit(outcome)
        finally:
            self.done.emit()

    def _report(self, done: int, total: int, message: str) -> None:
        """Forward one progress update to the GUI thread."""
        self.progress.emit(int(done), int(max(1, total)), message)


class JobRunner(QObject):
    """Owns the worker thread and offers start, cancel and busy state.

    One runner per window is enough: it refuses a second job while one is still
    running, which keeps the progress bar and the log unambiguous.

    Signals:
        progress: ``(done, total, message)`` forwarded from the worker.
        message: Log lines forwarded from the worker.
        finished_ok: Forwarded :class:`JobOutcome` of a successful job.
        failed: ``(message, traceback)`` of a failed job.
        cancelled: The running job stopped on request.
        busy_changed: ``True`` when a job starts, ``False`` when it ends.
    """

    progress = Signal(int, int, str)
    message = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str, str)
    cancelled = Signal()
    busy_changed = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Create an idle runner."""
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[RunWorker] = None

    @property
    def is_busy(self) -> bool:
        """Whether a job is currently running."""
        return self._thread is not None and self._thread.isRunning()

    def start(
        self,
        job: Job,
        known_ground_truth: Optional[Mapping[tuple[str, str], GroundTruth]] = None,
    ) -> bool:
        """Start a job in the worker thread.

        Args:
            job: The job to run.
            known_ground_truth: Reference curves the job may reuse.

        Returns:
            ``True`` when the job was started, ``False`` when one was already
            running.
        """
        if self.is_busy:
            LOGGER.warning("Refused to start '%s': a job is still running.",
                           getattr(job, "name", job))
            return False

        thread = QThread()
        worker = RunWorker(job, known_ground_truth)
        worker.moveToThread(thread)

        # The worker starts when the thread starts, and the thread quits as soon
        # as the worker is done, so no thread is ever left running.
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress)
        worker.message.connect(self.message)
        worker.finished_ok.connect(self.finished_ok)
        worker.failed.connect(self.failed)
        worker.cancelled.connect(self.cancelled)
        worker.done.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)

        self._thread = thread
        self._worker = worker
        self.busy_changed.emit(True)
        thread.start()
        return True

    def cancel(self) -> None:
        """Ask the running job to stop; does nothing when idle."""
        if self._worker is not None:
            self._worker.request_cancel()
            self.message.emit("Cancel requested; the job stops after the current frame.")

    def wait_for_finish(self, timeout_ms: int = 30_000) -> bool:
        """Block until the worker thread has finished.

        Only used while the window closes, so that a running search cannot
        outlive the application.

        Args:
            timeout_ms: How long to wait before giving up.

        Returns:
            ``True`` when the thread finished in time.
        """
        if self._thread is None:
            return True
        self.cancel()
        return self._thread.wait(timeout_ms)

    @Slot()
    def _on_thread_finished(self) -> None:
        """Drop the finished thread and worker, then report being idle."""
        thread, self._thread = self._thread, None
        self._worker = None
        if thread is not None:
            thread.deleteLater()
        self.busy_changed.emit(False)
