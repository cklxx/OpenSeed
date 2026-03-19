"""Thread-safe pool of PaperLibrary instances for concurrent web requests.

SQLite with WAL mode allows concurrent readers and serializes writers,
avoiding 'database is locked' errors under normal web load.
"""

from __future__ import annotations

import queue
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from openseed.storage.library import PaperLibrary


class LibraryPool:
    """Fixed-size pool of PaperLibrary connections.

    Each instance holds its own SQLite connection. WAL mode (enabled in
    PaperLibrary._connect) handles concurrent reads; writes are serialized
    by SQLite itself.
    """

    def __init__(self, library_dir: Path, size: int = 5) -> None:
        self._dir = library_dir
        self._pool: queue.Queue[PaperLibrary] = queue.Queue(maxsize=size)
        for _ in range(size):
            self._pool.put(PaperLibrary(library_dir))

    @contextmanager
    def acquire(self, timeout: float = 5.0) -> Iterator[PaperLibrary]:
        """Borrow a PaperLibrary from the pool, returning it when done."""
        lib = self._pool.get(timeout=timeout)
        try:
            yield lib
        finally:
            self._pool.put(lib)

    def close(self) -> None:
        """Close all pooled connections."""
        while not self._pool.empty():
            try:
                self._pool.get_nowait().close()
            except queue.Empty:
                break
