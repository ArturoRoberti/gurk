# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from filelock import FileLock, Timeout

from gurk.lib.shared.printers import richprint
from gurk.lib.utils import GURK_LOCKFILE_PATH

from .logger import LoggerSeverity


class GurkLock:
    """
    Context manager for acquiring a lock on the Gurk lockfile, ensuring only one core Gurk command is running at a time.
    """

    def __enter__(self):
        # Acquire the lockfile, failing immediately if already held
        self._file_lock = FileLock(GURK_LOCKFILE_PATH)
        try:
            self._file_lock.acquire(timeout=0)
        except Timeout:
            richprint(
                f"Stopping, as gurk lock ({GURK_LOCKFILE_PATH}) is already "
                "held by another process. If you are sure that no other "
                "gurk process is running, delete this file and try again.",
                color=LoggerSeverity.FATAL.color,
                file=sys.stderr,
            )
            raise SystemExit(1)

        return self

    def __exit__(self, exc_type, exc, tb):
        # Release the lockfile
        self._file_lock.release()

        # Propagate exceptions
        return False
