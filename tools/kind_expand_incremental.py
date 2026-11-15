#!/usr/bin/env python3
"""Add a fighter kind to an executable that already has the kind caves (exe_v46n -> exe_v46o: Byleth, kind 0x47).

kind_expand.py, base_effects_cave.py and base_customs_cave.py are built for an un-grown base RPX: they assert the
code space past 0x04BA0000 is free and that every word they hook still holds the game's original. Since exe_v44 the
user's executable has grown past them, and no un-grown base of it is at hand. This runs them on the current
executable as on a virtual base: their reads of it see each hooked word as the original the generator states (the six
switch bounds, kind_expand_ram.json's sites, every `orig` it passes, the two caves' hook sites), and kind_expand's
text-end check is skipped.

  python3 tools/kind_expand_incremental.py build EXE OLD_KINDS.json NEW_KINDS.json ARGS_OUT
      every generator with the spec the executable was built with (OLD) must reproduce it (printed: the words that
      differ, which must be only those other caves re-hooked); the words the NEW spec changes are written to
      ARGS_OUT as rpx_patch.py arguments. Then re-run tools/kirby_copy_pool_cave.py on the result (it hooks the
      load / unload cases of kinds granted as another kind, which move with the cave) and apply its words.
  python3 tools/kind_expand_incremental.py test TEST PATCHED ORIGINAL [args]
      runs tools/TEST.py (kind_expand_test, base_effects_test, base_customs_test) with ORIGINAL read the same way; a
      call the test makes on the original that faults (its unexpanded layout assumptions) returns 0xDEAD and the run
      goes on. Failures that compare with the original's behaviour are expected (the original is expanded already):
      read the new kind's own checks.

OLD_KINDS.json: tools/extra_kinds.json without the new record(s). fighters/master/README.md "Executable" has the
exe_v46o run (Byleth): 6-kind reproduction exact but for kirby_copy_pool_cave's two hooks, 8604 + 2 + 3 words.
"""
import json
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
import base_effects_cave as BE  # noqa: E402
import base_customs_cave as BC  # noqa: E402

OVER = {}                 # address -> the original word the generators expect there
SEEN = {}
ORIG_PATH = [None]        # only images of this path read through OVER


def _install(orig_path):
    ORIG_PATH[0] = os.path.abspath(orig_path)
    for _n, (cmp_, reg, _s, _t) in K.SWITCHES.items():
        OVER[cmp_] = K.one(cmp_, 'cmplwi r%d, 0x40' % reg)
    for a, w0, _arr, _ins in json.load(open(K.RAM_CACHE))['sites']:
        OVER[int(a, 16)] = int(w0, 16)
    OVER.update({site: K.b_word(site, o, link=True) for site, o, _l, _w in BE.SITES + BE.FINAL_SITES})
    OVER.update({BC.OWN_INDEX + 4 * i: w for i, w in enumerate(BC.OWN_ORIG)})
    OVER.update({BC.LINEAR + 4 * i: w for i, w in enumerate(BC.LINEAR_ORIG)})

    def put(self, addr, word, what, orig=None):
        if orig is not None:
            SEEN[addr] = K.one(addr, orig) if isinstance(orig, str) else orig
        assert addr not in self.words, 'patched twice: 0x%08X' % addr
        self.words[addr] = word & 0xFFFFFFFF
        self.what[addr] = what
        if addr < K.CAVE:
            self.inplace.append(addr)
    K.Build.put = put
    for cls in (K.Image, BC.Img):
        _init, _w = cls.__init__, cls.w

        def init(self, path, *a, _init=_init, **k):
            _init(self, path, *a, **k)
            self._is_orig = os.path.abspath(path) == ORIG_PATH[0]
        cls.__init__ = init
        cls.w = (lambda _w: lambda self, a: OVER.get(a, _w(self, a)) if getattr(self, '_is_orig', False)
                 else _w(self, a))(_w)
        cls._raw_w = _w
    _te = K.Image.text_end
    K.Image.text_end = lambda self: K.CAVE if getattr(self, '_is_orig', False) else _te(self)
    for _ in range(3):                    # the generator's stated originals join the overlay
        n = len(OVER)
        K.build(K.SPEC, orig_path)
        OVER.update(SEEN)
        if len(OVER) == n:
            break


def cmd_build(exe, old, new, out):
    _install(exe)
    img = K.Image(exe)
    raw = lambda a: K.Image._raw_w(img, a)                                # noqa: E731
    cimg = BC.Img(exe)
    craw = lambda a: BC.Img._raw_w(cimg, a)                               # noqa: E731
    gens = [('kind_expand', lambda s: K.build(s, exe)[0].words, raw),
            ('base_effects', lambda s: BE.build(s, exe)['patch'], raw),
            ('base_customs', lambda s: BC.build(s, exe)[0], craw)]
    args = []
    for name, run, rd in gens:
        o, n = run(old), run(new)
        bad = [a for a, w in sorted(o.items()) if rd(a) != w]
        diff = [(a, w) for a, w in sorted(n.items()) if rd(a) != w]
        print('%s: old spec %d words, %d differ from the executable %s; new spec %d words, %d to write' % (
            name, len(o), len(bad), ['0x%08X' % a for a in bad[:8]], len(n), len(diff)))
        args += ['0x%08X=0x%08X' % d for d in diff]
    open(out, 'w').write(' '.join(args))
    print('%d words -> %s; next: rpx_patch.py, then kirby_copy_pool_cave.py on the result' % (len(args), out))


def cmd_test(test, patched, orig, rest):
    _install(orig)
    sys.argv = [test + '.py', patched, orig] + rest
    if test != 'kind_expand_test':
        runpy.run_path(os.path.join(HERE, test + '.py'), run_name='__main__')
        return
    import kind_expand_test as T

    class SafeMu:
        """the original's emulator: a read past its mapped memory returns zeros (the test goes on)"""
        def __init__(self, mu):
            self._mu = mu

        def __getattr__(self, k):
            return getattr(self._mu, k)

        def mem_read(self, a, n):
            try:
                return self._mu.mem_read(a, n)
            except Exception:
                return bytearray(n)
    _call, _ei = T.Emu.call, T.Emu.__init__

    def einit(self, path, *a, **k):
        _ei(self, path, *a, **k)
        self._orig = os.path.abspath(path) == ORIG_PATH[0]
        if self._orig:
            self.mu = SafeMu(self.mu)

    def call(self, fn, *a, **k):
        if not getattr(self, '_orig', False):
            return _call(self, fn, *a, **k)
        try:
            return _call(self, fn, *a, **k)
        except Exception as e:
            print('   (original faulted in 0x%08X: %s)' % (fn, e))
            return 0xDEAD
    T.Emu.__init__, T.Emu.call = einit, call
    T.main()


def main():
    if len(sys.argv) >= 6 and sys.argv[1] == 'build':
        cmd_build(*sys.argv[2:6])
    elif len(sys.argv) >= 5 and sys.argv[1] == 'test':
        cmd_test(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
