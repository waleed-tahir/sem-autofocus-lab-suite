"""Entry point of the Native Static Autofocusing Application."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import APP_NAME, APP_VERSION
from app.plots.style import configure_matplotlib
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme

LOG_FORMAT = "%(levelname)-8s %(name)-28s %(message)s"


def configure_logging(verbose: bool = False) -> None:
    # If frozen (packaged as an EXE), also log to a local file for diagnosis
    handlers = [logging.StreamHandler(sys.stderr)]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        log_file = exe_dir / "autofocus_startup.log"
        handlers.append(logging.FileHandler(str(log_file), mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=LOG_FORMAT,
        handlers=handlers,
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def ensure_default_desktop() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    configure_logging(verbose="--verbose" in arguments)
    logging.getLogger(__name__).info("Starting %s %s (Edition)", APP_NAME, APP_VERSION)

    ensure_default_desktop()
    configure_matplotlib()

    application = QApplication(arguments)
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion(APP_VERSION)

    # Set clean window and application icon
    icon_path = Path(__file__).resolve().parent / "app_icon.ico"
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        application.setWindowIcon(app_icon)

    # Apply Fluent Theme
    apply_theme(application)

    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(app_icon)
    window.show()
    window.raise_()
    window.activateWindow()
    return application.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("root").exception("Fatal uncaught startup exception: %s", exc)
        if getattr(sys, "frozen", False):
            try:
                import traceback
                exe_dir = Path(sys.executable).parent
                (exe_dir / "crash_dump.txt").write_text(traceback.format_exc(), encoding="utf-8")
            except Exception:
                pass
        raise

