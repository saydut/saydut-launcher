"""
Threading Utilities for Saydut Launcher
QThread workers for background tasks
"""
from typing import Callable, Any, Optional
from PySide6.QtCore import QThread, Signal


class WorkerThread(QThread):
    """
    Generic worker thread for background tasks

    Signals:
        status(str): Status message
        progress(float, int, int): Progress (ratio, current, total)
        finished(dict): Task completed successfully (result dict)
        failed(str): Task failed (error message)

    Example:
        class EncryptWorker(WorkerThread):
            def do_work(self):
                self.status.emit("Encrypting...")
                self.progress.emit(0.5, 5, 10)
                # ... do encryption
                return {"encrypted": 10}

        worker = EncryptWorker()
        worker.finished.connect(on_done)
        worker.failed.connect(on_error)
        worker.start()
    """

    # Signals
    status = Signal(str)
    progress = Signal(float, int, int)  # ratio, current, total
    finished = Signal(dict)  # Result dictionary
    failed = Signal(str)  # Error message

    def __init__(self):
        super().__init__()

    def run(self):
        """
        Thread entry point

        Calls do_work() and emits appropriate signals.
        Override do_work() in subclass, not run().
        """
        try:
            result = self.do_work()

            # Emit success
            if result is None:
                result = {}
            self.finished.emit(result)

        except Exception as e:
            # Emit failure
            self.failed.emit(str(e))

    def do_work(self) -> Optional[dict]:
        """
        Override this method in subclass

        Returns:
            dict: Result data (or None)

        Raises:
            Exception: Any error will be caught and emitted via failed signal
        """
        raise NotImplementedError("Subclass must implement do_work()")

    def emit_status(self, message: str):
        """Emit status message"""
        self.status.emit(message)

    def emit_progress(self, current: int, total: int):
        """Emit progress"""
        ratio = current / total if total > 0 else 0.0
        self.progress.emit(ratio, current, total)


class SimpleWorker(WorkerThread):
    """
    Simple worker that runs a callable

    Example:
        def my_task():
            # Long running task
            return {"result": 123}

        worker = SimpleWorker(my_task)
        worker.finished.connect(lambda result: print(result))
        worker.start()
    """

    def __init__(self, task: Callable[[], Any]):
        super().__init__()
        self.task = task

    def do_work(self) -> Optional[dict]:
        """Run the task"""
        result = self.task()

        # Wrap result in dict if not already
        if isinstance(result, dict):
            return result
        else:
            return {"result": result}


def run_in_thread(
    task: Callable[[], Any],
    on_finished: Optional[Callable[[dict], None]] = None,
    on_failed: Optional[Callable[[str], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[float, int, int], None]] = None,
) -> SimpleWorker:
    """
    Run a task in a background thread

    Convenience function for quick threading.

    Args:
        task: Callable to run in thread
        on_finished: Callback for success (receives result dict)
        on_failed: Callback for error (receives error string)
        on_status: Callback for status updates
        on_progress: Callback for progress updates

    Returns:
        SimpleWorker: The worker thread (already started)

    Example:
        def encrypt_files():
            # ... encryption logic
            return {"count": 10}

        def on_done(result):
            print(f"Encrypted {result['count']} files")

        run_in_thread(encrypt_files, on_finished=on_done)
    """
    worker = SimpleWorker(task)

    # Connect signals
    if on_finished:
        worker.finished.connect(on_finished)
    if on_failed:
        worker.failed.connect(on_failed)
    if on_status:
        worker.status.connect(on_status)
    if on_progress:
        worker.progress.connect(on_progress)

    # Start thread
    worker.start()

    return worker
