"""Builds are all or nothing.

A build writes into the project folder as it goes (labels, parameter rows, the new kind and character id, files).
Before 1.5.1 a build that stopped part way left those behind while the project file (written last) didn't list the
clone, so every later build found the next kind / id / labels taken. Now:

- Transaction(out): before anything is written, the project folder is snapshotted into
  <out>/.sm4shclonetool_rollback/ as hard links (no extra disk space; a plain copy where the drive has no hard
  links). While the build runs, a file the build opens for writing that still shares its data with the snapshot is
  first given its own copy, so the snapshot keeps the file as it was. On an error the folder is put back exactly as
  it was before the build; on success the snapshot is deleted.
- recover(out): a build cut off without an error (a crash, the window closed, the power) leaves the snapshot
  behind; the next session puts the folder back from it before doing anything.
"""
import builtins
import io
import json
import os
import shutil
import threading

SNAP = '.sm4shclonetool_rollback'
STATE = 'state.json'
TREE = 'tree'
_WRITE = set('wax+')
_lock = threading.Lock()
_active = []                     # the running transactions' folders (normcased, with a trailing separator)
_orig_open = builtins.open


class RollbackError(Exception):
    pass


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def _inside(path):
    try:
        p = _norm(os.fspath(path))
    except TypeError:
        return False
    return any(p.startswith(root) and not p.startswith(root + SNAP + os.sep) for root in _active)


def _unshare(path):
    """the file stops sharing its data with the snapshot (a copy of it replaces it)"""
    try:
        st = os.stat(path)
    except OSError:
        return
    if st.st_nlink < 2:
        return
    tmp = path + '.sm4shclonetool_cow'
    shutil.copy2(path, tmp)
    os.replace(tmp, path)


def _open(file, mode='r', *args, **kw):
    if isinstance(mode, str) and _WRITE & set(mode) and not isinstance(file, int) and _active and _inside(file):
        _unshare(os.fspath(file))
    return _orig_open(file, mode, *args, **kw)


def _install():
    builtins.open = _open
    io.open = _open


def _uninstall():
    builtins.open = _orig_open
    io.open = _orig_open


def _entries(out):
    return sorted(n for n in os.listdir(out) if n != SNAP) if os.path.isdir(out) else []


def _link_tree(src, dst, manifest, rel=''):
    """dst mirrors src: files hard-linked (copied where links don't work); manifest: relpath -> [size, mtime_ns]"""
    if os.path.isdir(src) and not os.path.islink(src):
        os.makedirs(dst, exist_ok=True)
        shutil.copystat(src, dst)
        for n in os.listdir(src):
            _link_tree(os.path.join(src, n), os.path.join(dst, n), manifest, os.path.join(rel, n))
        return 0
    try:
        os.link(src, dst)
        linked = 1
    except OSError:
        shutil.copy2(src, dst)
        linked = 0
    st = os.stat(dst)
    manifest[rel] = [st.st_size, st.st_mtime_ns]
    return linked


def _remove(p):
    if os.path.isdir(p) and not os.path.islink(p):
        shutil.rmtree(p)
    elif os.path.lexists(p):
        os.unlink(p)


def _write_state(snap, state):
    tmp = os.path.join(snap, STATE + '.new')
    with _orig_open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, os.path.join(snap, STATE))


def _read_state(snap):
    try:
        with _orig_open(os.path.join(snap, STATE)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def snapshot(out):
    """<out>/.sm4shclonetool_rollback/: the folder as it is now. Returns the state."""
    snap = os.path.join(out, SNAP)
    if os.path.exists(snap):
        recover(out, print)
    os.makedirs(os.path.join(snap, TREE))
    _write_state(snap, {'complete': False})
    manifest = {}
    tops = _entries(out)
    for n in tops:
        _link_tree(os.path.join(out, n), os.path.join(snap, TREE, n), manifest, n)
    state = {'complete': True, 'top': tops, 'files': manifest}
    _write_state(snap, state)
    return state


def restore(out, log=print):
    """puts <out> back as the snapshot has it (safe to run again if it is itself cut off). Returns the files the
    snapshot could not keep as they were (written in place by something that bypassed the copy-on-write)."""
    snap = os.path.join(out, SNAP)
    state = _read_state(snap)
    if not state or not state.get('complete'):
        # cut off while the snapshot was being made: nothing had been written to the folder yet
        _remove(snap)
        return []
    tree = os.path.join(snap, TREE)
    changed = []
    for rel, (size, mtime) in sorted(state['files'].items()):
        p = os.path.join(tree, rel)
        if os.path.exists(p):
            st = os.stat(p)
            if st.st_size != size or st.st_mtime_ns != mtime:
                changed.append(rel)
    if not state.get('restoring'):
        state['restoring'] = True
        _write_state(snap, state)
    for n in state['top']:                 # moved back one by one; a name already moved is no longer in the tree
        src = os.path.join(tree, n)
        if os.path.lexists(src):
            _remove(os.path.join(out, n))
            os.replace(src, os.path.join(out, n))
    for n in _entries(out):                # what the build added
        if n not in state['top']:
            _remove(os.path.join(out, n))
    _remove(snap)
    if changed:
        log('WARNING: %d file(s) were changed in place during the build and could not be put back exactly: %s'
            % (len(changed), ', '.join(changed[:10])))
    return changed


def discard(out):
    _remove(os.path.join(out, SNAP))


def recover(out, log=print):
    """after a build that was cut off (crash, window closed): put the project folder back. True if it did."""
    snap = os.path.join(out, SNAP)
    if not os.path.exists(snap):
        return False
    state = _read_state(snap)
    restore(out, log)
    if state and state.get('complete'):
        log('NOTE: the last build did not finish (the tool was closed or stopped while building): the project folder '
            'was put back as it was before that build')
        return True
    return False


class Transaction:
    """with Transaction(out, log): ... -- the folder is put back as it was if the block raises"""

    def __init__(self, out, log=print):
        self.out = os.path.abspath(out)
        self.log = log

    def __enter__(self):
        os.makedirs(self.out, exist_ok=True)
        snapshot(self.out)
        with _lock:
            if not _active:
                _install()
            _active.append(_norm(self.out) + os.sep)
        return self

    def __exit__(self, et, ev, tb):
        with _lock:
            _active.remove(_norm(self.out) + os.sep)
            if not _active:
                _uninstall()
        if et is None:
            discard(self.out)
            return False
        try:
            restore(self.out, self.log)
            self.log('the build stopped (%s): the project folder was put back as it was before it; nothing of the '
                     'unfinished clone is left' % (ev,))
        except Exception as e:                 # leave the snapshot for recover() on the next start
            self.log('WARNING: could not put the project folder back (%s): it will be put back the next time the '
                     'project is opened' % e)
        return False
