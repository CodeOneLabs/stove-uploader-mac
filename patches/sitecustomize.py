# macOS compatibility patches for running STOVE's Windows uploader bytecode.
# Loaded automatically because the launcher puts this folder first on PYTHONPATH.
import os
import subprocess
import sys

import psutil

# macOS denies other users' process info; the uploader only scans for its own processes.
_orig_iter = psutil.process_iter
def _safe_iter(*a, **k):
    try:
        return list(_orig_iter(*a, **k))
    except (PermissionError, psutil.AccessDenied):
        return []
psutil.process_iter = _safe_iter
_orig_pids = psutil.pids
def _safe_pids():
    try:
        return _orig_pids()
    except (PermissionError, psutil.AccessDenied):
        return []
psutil.pids = _safe_pids

# macOS: multiprocessing.Queue.qsize() raises NotImplementedError (sem_getvalue missing).
import multiprocessing.queues as _mq
_Q = _mq.Queue
_orig_init, _orig_put, _orig_get = _Q.__init__, _Q.put, _Q.get
_orig_getstate, _orig_setstate = _Q.__getstate__, _Q.__setstate__
def _init(self, maxsize=0, *, ctx):
    _orig_init(self, maxsize, ctx=ctx)
    self._mac_size = ctx.Value('i', 0)
def _put(self, obj, block=True, timeout=None):
    _orig_put(self, obj, block, timeout)
    with self._mac_size.get_lock():
        self._mac_size.value += 1
def _get(self, block=True, timeout=None):
    r = _orig_get(self, block, timeout)
    with self._mac_size.get_lock():
        self._mac_size.value -= 1
    return r
def _qsize(self):
    return max(0, self._mac_size.value)
def _getstate(self):
    return (_orig_getstate(self), self._mac_size)
def _setstate(self, state):
    st, self._mac_size = state
    _orig_setstate(self, st)
_Q.__init__, _Q.put, _Q.get, _Q.qsize = _init, _put, _get, _qsize
_Q.__getstate__, _Q.__setstate__ = _getstate, _setstate
_Q.empty = lambda self: _qsize(self) == 0

# The CLI launches STOVEUpdater.exe and STOVEUploaderCLICore.exe, which it downloads itself.
# Run their bytecode with this Python instead, unpacking each into its runner folder on first use.
_ROOT = os.environ.get("STOVE_MAC_ROOT", "")
_RUNNERS = {
    "STOVEUpdater.exe": "updater_runner",
    "STOVEUploaderCLICore.exe": "core_runner",
}
_orig_popen_init = subprocess.Popen.__init__
def _popen_init(self, args, *a, **k):
    if _ROOT and isinstance(args, (list, tuple)) and args:
        folder = _RUNNERS.get(os.path.basename(str(args[0])))
        if folder:
            import stove_mac
            runner = os.path.join(_ROOT, folder)
            entry, version = stove_mac.extract(str(args[0]), runner)
            args = [sys.executable, os.path.join(runner, entry)] + [str(x) for x in args[1:]]
            env = dict(k.get("env") or os.environ)
            env["FAKE_APP_VERSION"] = version
            env["PYTHONPATH"] = os.pathsep.join(
                [os.path.join(_ROOT, "patches"), runner, os.path.join(_ROOT, "deps")])
            k["env"] = env
            k["cwd"] = runner
    _orig_popen_init(self, args, *a, **k)
subprocess.Popen.__init__ = _popen_init
