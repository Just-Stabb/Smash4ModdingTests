#!/usr/bin/env python3
"""Find every instruction that addresses a per-fighter-kind array in RAM (docs/kind-expansion-ram.md).

  python3 tools/kind_ram_scan.py [RPX] [-S MGR|EQ|AI|AIM] [--all] [--summary] [--csv FILE]
                                       [--missed] [--loops] [--plan N]

RPX defaults to build/cave_fix_s4/cross_f.rpx (the vanilla code addresses; the caves only add
code). Takes about 10 s.

Smash 4 sizes some objects for exactly 65 fighter kinds (0x00-0x40). Growing the roster past 0x40
means growing or moving those arrays, and every instruction that addresses them has to agree. This
tool is the inventory: a static data-flow pass over `.text` that follows the pointers to those
objects from where they are loaded, and prints every access with the array and the kind it touches.

How it works
------------
1. Function boundaries: every `bl` target, every ADDR32 relocation into `.text`, and every
   `stwu r1,-N(r1)` prologue (with its `mflr r0` / `stw r0,4(r1)`). A function ends at the next
   start. Code a function's entry doesn't reach (after a `blr`, entered by a `b` from elsewhere) is
   analysed too, from an unknown state.
2. Roots: loads of a global that holds an object pointer (`GLOBALS`, e.g. `[0x102FF448]` = the
   FighterParamManager), loads of pointer fields of tracked objects (`FIELD_PTRS`, e.g.
   `[mgr+0x2574]` = the equipment-ability object), the allocation sites (`ALLOCS`: `li r3, SIZE`
   + `bl` allocator, so the constructors are followed) and functions reached only through a
   function pointer (`SEEDS`: the AI record constructor).
3. Per function, a forward data-flow over the basic blocks (`bctr` jump tables included) with an
   abstract value per GPR and per stack slot (`r1+d`):
     ('#', v, ())          a constant (lis / addi / ori / li / slwi / mulli folded),
     (None, off, strides)  an index expression: unknown * stride + off,
     (S, off, strides)     a pointer into tracked object S: S + off + sum(index_i * stride_i),
     ('@...', off, ...)    a pointer into some other object (only to tell its accesses apart).
   A stride is an int (computed: `slwi rK, kind, 2`, `mulli`), '?' (an unknown register added to a
   pointer) or 'L<n>' (a loop step: two values n apart met at a join, i.e. a `stwu` / `lwzu` /
   `addi rP, rP, n` walker or a loop counter). `add`, `addi`, `addic`, `subf`, `slwi` / `rlwinm`,
   `mulli`, `mullw`, `mr`, update forms and `lmw` / `stmw` are modelled; anything else clears its
   destination. A call clears the volatile registers, or for a leaf callee only the registers it
   writes (the compiler relies on that and keeps values in r4-r12 across such calls).
4. Inter-procedural: a tracked pointer passed in r3-r10 to a `bl` (or a tail `b`) seeds the callee,
   which is analysed again in that context (up to MAX_CTX contexts a function). A callee that
   returns a tracked pointer in r3 (a getter) gives the caller that value. Rounds repeat until no
   new context or return value appears.
5. Every load / store / `addi` / call argument / pointer store whose base is a tracked pointer is a
   site. Its field offset (index 0) is matched to the object's layout (`LAYOUTS`) and classified:
     const     the kind is built into the displacement (e.g. Kirby's vl param `[mgr+0x113C]`),
     indexed   kind * element size added at run time,
     walk      a loop walking the array (`lwzu` / `stwu` / `addi` steps, loop counters),
     addr      a pointer into the array is formed (`addi rX, mgr, 0x111C`); its uses follow,
     arg       a pointer into the array is passed to a call (r3-r10 at the `bl`),
     escape    a pointer into the array is stored to memory (the data-flow loses it there),
     other     the field is not in a per-kind array (only with --all).
   `*imm`: the instruction's own 16-bit immediate holds the array offset (its base pointer comes
   from outside the per-kind block): these are the words to patch when the arrays move.
   `[via arg]`: the function receives the pointer as an argument (a method of the object).

--struct S  only that object;  --all  also the non-per-kind fields;  --summary  counts only;
--csv FILE  the sites as CSV (addr, function, object, class, array, instruction, detail, via_arg,
            imm, field offset);
--missed    completeness check: in the functions that touch the FighterParamManager, the D-form
            loads / stores / addi with a displacement in 0x111C-0x25B0 whose base register the
            data-flow did not resolve, and that are no address constant (with -S ALL: all .text);
--loops     the loops that run 0x41 / 0x42 times (`li rC, N` + `mtctr` / `addic.` countdown,
            `cmpwi rI, N` + branch back) and the arrays they walk ($: static data, STACK: the
            frame, @: other objects);
--plan N    the word patches of the recommended plan for N kinds (rpx_patch.py arguments,
            UNTESTED): the FighterParamManager's per-kind block relocated to the end of a bigger
            allocation with the old vl array kept as a mirror, the equipment object grown in place,
            and the AI-record guards still to write.

Layouts (offsets in the object):
  MGR  FighterParamManager [0x102FF448], 0x25B0 bytes (`li r3,0x25B0` at 0x02E4E684 / 0x02EA5860):
       per-kind arrays 0x111C-0x2364 (see LAYOUTS), then the common effect table and three fields
  EQ   fighter_param_equipment_ability object [0x10353FC0] = [mgr+0x2574], 0x424 bytes (0x02EA5964),
       ending in a [0x41] array of vl struct pointers at +0x320
  AIM  AI manager [0x102FAD78]; +0x794 = AI object
  AI   AI object, 0x26D0 bytes (`li r3,0x26D0` at 0x02758574): 8 x 0x488 per-player records at
       +0x290, each ending in two [0x41] word arrays (+0x280, +0x384), amiibo (nfp) learning counts
       per fighter kind
"""
import argparse
import array
import bisect
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.environ.get('S4_TOOLS', HERE)
sys.path.insert(0, TOOLS)
import fighter_kind_tables as FKT  # noqa: E402

RPX = os.path.join(TOOLS, '..', 'build', 'cave_fix_s4', 'cross_f.rpx')
NK = 0x41
MAX_CTX = 6

# global word -> object it points to
GLOBALS = {0x102FF448: 'MGR', 0x10353FC0: 'EQ', 0x102FAD78: 'AIM'}
# allocation sites `li r3, SIZE` (the `bl` allocator follows): r3 after the call is the new object
AI_RECORD = ('AI', 0x290, ('L%d' % 0x488,))       # one of the AI object's 0x488-byte records
ALLOCS = {0x02E4E684: ('MGR', 0, ()), 0x02EA5860: ('MGR', 0, ()), 0x02EA5964: ('EQ', 0, ()),
          0x02758574: ('AI', 0, ()), 0x02758700: AI_RECORD}
# functions only reached through a function pointer, with their argument: the AI record constructor
# (passed to the array constructor 0x02003E30 at 0x027585A8; r3 = one record)
SEEDS = {0x027586EC: {3: AI_RECORD}}
# (object, field) -> object the field points to
FIELD_PTRS = {('MGR', 0x2574): 'EQ', ('AIM', 0x794): 'AI'}

# object -> (size, [(start, count, elem_size, name, meaning)])  per-kind arrays
# and [(start, size, name)] other fields.  Element counts are kinds unless noted.
LAYOUTS = {
    'MGR': (0x25B0, [
        (0x111C, NK, 4, 'vl', 'parsed fighter_param_vl struct (vl load 0x02EA6BC4)'),
        (0x1220, NK, 4, 'refcnt', 'vl load reference count'),
        (0x1324, NK, 4, 'x1324', 'extra vl pointer (vl tail 0x02EA8D50, kinds 0x17/0x18/0x1C/0x21/0x23/0x26/8)'),
        (0x1428, NK, 4, 'x1428', 'cleared on load / unload'),
        (0x152C, NK, 4, 'x152C', 'extra vl pointer (vl tail, kinds 5/6/0x19/0x20/0x35)'),
        (0x1630, NK, 4, 'fpidx', 'fighter_param.bin entry index'),
        (0x1734, NK, 4, 'vl50', 'vl struct +0x50 (hurtbox vector)'),
        (0x1838, NK, 0x24, 'att', '3 x 0xC lists (vl groups 9/10 attach points), set in vl tail'),
        (0x215C, NK, 8, 'attp', '{ptr to the +0x1838 record, 3}'),
    ], [
        (0x2364, 0x210, 'common effect table (0x42 x 8: effect_Xlu ... effect_ColorNormal, names '
                        '0x10353EB8; NOT per kind; init 0x02EA5B7C)'),
        (0x0000, 0x38, 'fighter_param vector (count +8, data +0xC; entries 0x588)'),
        (0x0038, 0xD68, 'fighter_param_common'),
        (0x0DA0, 0x2B8, 'fighter_param_etc'),
        (0x1058, 0xC4, 'fighter_param_power_up'),
        (0x2574, 4, 'equipment_ability object pointer'),
        (0x2578, 0x1C, 'common container (WorkModule category 2)'),
        (0x2594, 0x1C, 'equipment container (WorkModule category 9)'),
    ]),
    'EQ': (0x424, [
        (0x320, NK, 4, 'vlptr', 'parsed fighter_param_vl struct (owner of the allocation)'),
    ], [(0x0, 0x320, 'equipment_ability data')]),
    'AIM': (0x810, [], [(0x794, 4, 'AI object pointer')]),
    'AI': (0x26D0, [], [(0x0, 0x10, 'header'), (0x10, 0x280, '8 x 0x50 records')]),
}
AI_REC, AI_RSTRIDE, AI_NREC = 0x290, 0x488, 8
AI_REC_ARRAYS = [(0x280, NK, 4, 'rec.k280', 'per-kind word (count)'),
                 (0x384, NK, 4, 'rec.k384', 'per-kind word')]


def sx16(v):
    return v - 0x10000 if v & 0x8000 else v


# ---------------------------------------------------------------- RPX
class Image:
    def __init__(self, path):
        self.rpx = FKT.Rpx(path)
        self.base, data = self.rpx.text()
        self.W = array.array('I', bytes(data[:len(data) // 4 * 4]))
        if sys.byteorder == 'little':
            self.W.byteswap()
        self.end = self.base + 4 * len(self.W)
        self.rel = FKT.relocations(self.rpx)
        self._starts()

    def w(self, a):
        return self.W[(a - self.base) >> 2]

    def _starts(self):
        W, base = self.W, self.base
        st = set()
        self.calls = collections.defaultdict(list)
        for i, w in enumerate(W):
            if (w >> 26) == 18:
                if w & 1:
                    off = w & 0x3FFFFFC
                    if off & 0x2000000:
                        off -= 0x4000000
                    t = base + 4 * i + off
                    st.add(t)
                    self.calls[t].append(base + 4 * i)
            elif (w >> 16) == 0x9421:
                a = base + 4 * i
                if i and W[i - 1] == 0x7C0802A6:                       # mflr r0
                    a -= 4
                elif i > 1 and W[i - 1] == 0x90010004 and W[i - 2] == 0x7C0802A6:   # stw r0,4(r1)
                    a -= 8
                st.add(a)
        for off, typ, val in self.rel:
            if typ == 1 and base <= val < self.end:
                st.add(val)
        self.starts = sorted(a for a in st if base <= a < self.end)
        self.reloc_targets = sorted(val for off, typ, val in self.rel
                                    if typ == 1 and base <= val < self.end)

    def func_of(self, a):
        i = bisect.bisect_right(self.starts, a) - 1
        s = self.starts[i]
        e = self.starts[i + 1] if i + 1 < len(self.starts) else self.end
        return s, e


# ---------------------------------------------------------------- abstract values
def is_other(t):
    return t is not None and t[0] not in ('#', None) and t[0][0] == '@'


def t_add(a, b):
    """a + b. A tracked pointer plus an unknown value is the pointer with an unknown index '?'."""
    if is_other(a) and b is not None and b[0] not in ('#', None) and not is_other(b):
        a = None
    elif is_other(b) and a is not None and a[0] not in ('#', None) and not is_other(a):
        b = None
    elif is_other(a) and is_other(b):
        return None
    if a is None or b is None:
        if a is not None and a[0] not in ('#', None):
            return (a[0], a[1], a[2] + ('?',))
        if b is not None and b[0] not in ('#', None):
            return (b[0], b[1], b[2] + ('?',))
        return None
    sa, sb = a[0], b[0]
    if sa == '#' and sb == '#':
        return ('#', (a[1] + b[1]) & 0xFFFFFFFF, ())
    if sa not in ('#', None) and sb not in ('#', None):
        return None
    if sb not in ('#', None):
        a, b = b, a
    off = a[1] + (b[1] if b[0] != '#' or b[1] < 0x80000000 else b[1] - 0x100000000)
    return (a[0], off, tuple(sorted(a[2] + b[2], key=str)))


def sval(x):
    """numeric value of a stride: an int (computed index) or 'L<n>' (loop step); None for '?'"""
    if isinstance(x, int):
        return x
    if x.startswith('L'):
        return int(x[1:])
    return None


def t_scale(t, m):
    """t * m (slwi / mulli)"""
    if t is None or is_other(t):
        return (None, 0, (m,))
    if t[0] == '#':
        return ('#', (t[1] * m) & 0xFFFFFFFF, ())
    if t[0] is None:
        out = []
        for x in t[2]:
            if isinstance(x, int):
                out.append(x * m)
            elif x.startswith('L'):
                out.append('L%d' % (int(x[1:]) * m))
            else:
                out.append('?')
        return (None, t[1] * m, tuple(out))
    return None


def _as_index(t):
    if t[0] == '#':
        v = t[1] - 0x100000000 if t[1] & 0x80000000 else t[1]
        return (None, v, ())
    return t


def t_merge(a, b):
    """join of two values at a control-flow merge. Two offsets of one pointer / index become a
    loop stride 'L<diff>' (a walker: `stwu rX, 4(rY)`, `addi rI, rI, 0x488`)."""
    if a == b:
        return a
    if a is None or b is None:
        return None
    if a[0] != b[0]:
        if a[0] in ('#', None) and b[0] in ('#', None):
            a, b = _as_index(a), _as_index(b)
        else:
            return None
    elif a[0] == '#':
        if all(0x10000000 <= x[1] < 0x11000000 for x in (a, b)):
            a, b = ('$', a[1], ()), ('$', b[1], ())      # a static array walked in a loop
        else:
            a, b = _as_index(a), _as_index(b)
    S = a[0]
    sa, sb = list(a[2]), list(b[2])
    lo = min(a[1], b[1])
    if sa == sb:
        diff = abs(a[1] - b[1])
        if diff == 0 or len(sa) > 3:
            return None
        for v in sa:
            sv = sval(v)
            if isinstance(v, str) and sv and diff % sv == 0:
                return (S, lo, tuple(sa))         # the same walker one more step on
        return (S, lo, tuple(sorted(sa + ['L%d' % diff], key=str)))
    for x, y in ((sa, sb), (sb, sa)):       # one already has the loop stride the other lacks
        rest = list(x)
        ok = True
        for v in y:
            if v in rest:
                rest.remove(v)
            else:
                ok = False
                break
        if ok and rest and all(isinstance(v, str) and v.startswith('L') for v in rest):
            return (S, lo, tuple(sorted(x, key=str)))
    return None


def merge_state(x, y):
    out = {}
    for k, v in x.items():
        if k in y:
            m = t_merge(v, y[k])
            if m is not None:
                out[k] = m
    return out


LOADS = {32: ('lwz', 4, 0), 33: ('lwzu', 4, 1), 34: ('lbz', 1, 0), 35: ('lbzu', 1, 1), 40: ('lhz', 2, 0),
         41: ('lhzu', 2, 1), 42: ('lha', 2, 0), 43: ('lhau', 2, 1)}
FLOADS = {48: ('lfs', 4, 0), 49: ('lfsu', 4, 1), 50: ('lfd', 8, 0), 51: ('lfdu', 8, 1)}
STORES = {36: ('stw', 4, 0), 37: ('stwu', 4, 1), 38: ('stb', 1, 0), 39: ('stbu', 1, 1), 44: ('sth', 2, 0),
          45: ('sthu', 2, 1), 52: ('stfs', 4, 0), 53: ('stfsu', 4, 1), 54: ('stfd', 8, 0), 55: ('stfdu', 8, 1)}
# op 31 indexed forms: xo -> (name, size, is_store, update, fp)
XFORMS = {23: ('lwzx', 4, 0, 0, 0), 55: ('lwzux', 4, 0, 1, 0), 87: ('lbzx', 1, 0, 0, 0), 119: ('lbzux', 1, 0, 1, 0),
          279: ('lhzx', 2, 0, 0, 0), 311: ('lhzux', 2, 0, 1, 0), 343: ('lhax', 2, 0, 0, 0), 375: ('lhaux', 2, 0, 1, 0),
          151: ('stwx', 4, 1, 0, 0), 183: ('stwux', 4, 1, 1, 0), 215: ('stbx', 1, 1, 0, 0), 247: ('stbux', 1, 1, 1, 0),
          407: ('sthx', 2, 1, 0, 0), 439: ('sthux', 2, 1, 1, 0), 535: ('lfsx', 4, 0, 0, 1), 567: ('lfsux', 4, 0, 1, 1),
          599: ('lfdx', 8, 0, 0, 1), 631: ('lfdux', 8, 0, 1, 1), 663: ('stfsx', 4, 1, 0, 1), 695: ('stfsux', 4, 1, 1, 1),
          727: ('stfdx', 8, 1, 0, 1), 759: ('stfdux', 8, 1, 1, 1), 534: ('lwbrx', 4, 0, 0, 0), 662: ('stwbrx', 4, 1, 0, 0)}
# op 31 xo that write rA (logical / shifts) and that write nothing
X_WRITES_RA = {28, 60, 124, 284, 316, 412, 444, 476, 24, 536, 792, 824, 26, 954, 922, 986}
X_NO_WRITE = {0, 32, 54, 86, 246, 278, 470, 982, 1014, 598, 854, 4, 150, 214, 918, 146, 467, 144}
VOLATILE = [0] + list(range(3, 13))


# ---------------------------------------------------------------- analysis
class Scanner:
    def __init__(self, img):
        self.img = img
        self.sites = {}           # (addr, kind, struct, off, strides) -> info
        self.ret = {}             # (fn, ctxkey) -> r3 tag at return
        self.ctx = collections.defaultdict(set)   # fn -> set of ctx (frozenset of (reg, tag))
        self.pending = []
        self.touched = set()      # functions where a tracked pointer was seen
        self.leaf_ret = {}
        self.other = set()        # accesses whose base is some other (untracked) object
        self.clob = {}
        self.trace = set()        # functions whose every access is recorded (kind-count loops)
        self.traced = []

    # -- CFG
    def blocks(self, s, e):
        img = self.img
        leaders = {s}
        a = s
        while a < e:
            w = img.w(a)
            op = w >> 26
            if op == 18 and not (w & 1):
                t = self._btarget(a, w)
                if s <= t < e:
                    leaders.add(t)
                leaders.add(a + 4)
            elif op == 16:
                t = self._bctarget(a, w)
                if not (w & 1) and s <= t < e:
                    leaders.add(t)
                leaders.add(a + 4)
            elif op == 19 and ((w >> 1) & 0x3FF) in (16, 528) and not (w & 1):
                leaders.add(a + 4)
            a += 4
        rt = self.img.reloc_targets
        i = bisect.bisect_left(rt, s)
        while i < len(rt) and rt[i] < e:
            leaders.add(rt[i])
            i += 1
        return sorted(x for x in leaders if s <= x < e)

    @staticmethod
    def _btarget(a, w):
        off = w & 0x3FFFFFC
        if off & 0x2000000:
            off -= 0x4000000
        return (off if w & 2 else a + off) & 0xFFFFFFFF

    @staticmethod
    def _bctarget(a, w):
        off = w & 0xFFFC
        if off & 0x8000:
            off -= 0x10000
        return (off if w & 2 else a + off) & 0xFFFFFFFF

    def site(self, a, fn, kind, tag, disp, ins, extra=''):
        S, off, strides = tag
        if fn in self.trace and kind != 'root':
            self.traced.append((a, fn, kind, S, off + disp, strides, ins))
        if S[0] in '@$' or S == 'STACK':   # an untracked object: only remember that the base is known
            self.other.add(a)
            return
        key = (a, kind, S, off + disp, strides)
        if key not in self.sites:
            self.sites[key] = dict(addr=a, fn=fn, kind=kind, S=S, off=off + disp, strides=strides,
                                   ins=ins, extra=extra, disp=disp, base=off)

    def analyse(self, fn, ctx):
        img = self.img
        s, e = img.func_of(fn)
        if fn != s:
            s = fn
        leaders = self.blocks(s, e)
        lset = set(leaders)
        init = dict(ctx)
        if not ctx:                     # a root context: the arguments are some other objects
            for r in range(3, 11):
                init[r] = ('@arg%d' % r, 0, ())
            if fn in self.trace:
                init[1] = ('STACK', 0, ())
        states = {s: init}
        visits = collections.Counter()
        covered = set()
        rets = []
        work = [s]
        nxt = s
        while True:
            while work:
                b = work.pop()
                visits[b] += 1
                if visits[b] > 12:
                    continue
                R = dict(states[b])
                a = b
                outs = []
                while a < e:
                    w = img.w(a)
                    covered.add(a)
                    flow = self.step(a, w, R, fn, s, e, rets)
                    a += 4
                    if flow is not None:
                        outs = flow
                        break
                    if a in lset:
                        outs = [a]
                        break
                for t in outs:
                    if t is None or not (s <= t < e):
                        continue
                    if t in states:
                        m = merge_state(states[t], R)
                        if m != states[t]:
                            states[t] = m
                            work.append(t)
                    else:
                        states[t] = dict(R)
                        work.append(t)
            if ctx:
                break
            # code not reached from the entry (after a blr / b, entered by a tail `b` from
            # elsewhere or a jump table): analyse it too, from an unknown state
            while nxt < e and (nxt in covered or img.w(nxt) == 0):
                nxt += 4
            if nxt >= e:
                break
            states[nxt] = {}
            lset.add(nxt)
            work = [nxt]
        r = None
        if rets and all(x == rets[0] for x in rets) and rets[0] is not None and rets[0][0] not in ('#', None):
            r = rets[0]
        self.ret[(fn, frozenset(ctx))] = r

    def call(self, a, tgt, R, fn, tail=False):
        seeds = []
        for r in range(3, 11):
            t = R.get(r)
            if t is not None and t[0] not in ('#', None):
                if t[0] not in LAYOUTS:
                    continue
                seeds.append((r, t))
                self.site(a, fn, 'arg', t, 0, 'r%d -> %s %s' % (r, 'b' if tail else 'bl',
                                                                 '0x%08X' % tgt if tgt is not None else 'ctr'))
        ctx = frozenset(seeds)
        if seeds and tgt is not None and self.img.base <= tgt < self.img.end:
            if ctx not in self.ctx[tgt] and len(self.ctx[tgt]) < MAX_CTX:
                self.ctx[tgt].add(ctx)
                self.pending.append((tgt, ctx))
        ret = None
        if a - 4 in ALLOCS:
            ret = ALLOCS[a - 4]
        elif tgt is not None:
            ret = self.ret.get((tgt, ctx))
            if ret is None and not seeds:
                ret = self.leaf_return(tgt)
        for r in self.clobbers(tgt):
            R.pop(r, None)
        if ret is not None:
            R[3] = ret

    def clobbers(self, tgt):
        """registers a call may change: the volatile ones, or for a leaf callee (no calls of its own,
        as the compiler knows and exploits) only the ones it writes"""
        if tgt is None or not (self.img.base <= tgt < self.img.end):
            return VOLATILE
        if tgt in self.clob:
            return self.clob[tgt]
        img = self.img
        s, e = img.func_of(tgt)
        out = set()
        if e - tgt > 4 * 600:
            out = None
        a = tgt
        while out is not None and a < e:
            w = img.w(a)
            op = w >> 26
            rD, rA = (w >> 21) & 31, (w >> 16) & 31
            if (op == 18 and w & 1) or (op == 19 and w & 1) or (op == 16 and w & 1):
                out = None
                break
            if op in (7, 8, 12, 13, 14, 15) or op in LOADS:
                out.add(rD)
                if op in LOADS and LOADS[op][2]:
                    out.add(rA)
            elif op == 46:
                out.update(range(rD, 32))
            elif op in (20, 21, 23, 24, 25, 26, 27, 28, 29, 30):
                out.add(rA)
            elif op in (33, 35, 37, 39, 41, 43, 45, 49, 51, 53, 55, 57, 61):
                out.add(rA)
            elif op == 31:
                xo = (w >> 1) & 0x3FF
                if xo in XFORMS:
                    nm, sz, st, upd, fp = XFORMS[xo]
                    if not st and not fp:
                        out.add(rD)
                    if upd:
                        out.add(rA)
                elif xo in X_WRITES_RA:
                    out.add(rA)
                elif xo not in X_NO_WRITE:
                    out.add(rD)
            a += 4
        res = VOLATILE if out is None else sorted(out | {0, 3})
        self.clob[tgt] = res
        return res

    def leaf_return(self, tgt):
        """r3 of a small argument-free getter (e.g. `lis; lwz r3, g; blr`)"""
        if tgt in self.leaf_ret:
            return self.leaf_ret[tgt]
        self.leaf_ret[tgt] = None
        img = self.img
        R = {}
        a = tgt
        for _ in range(24):
            if not (img.base <= a < img.end):
                break
            w = img.w(a)
            if w == 0x4E800020:
                t = R.get(3)
                if t is not None and t[0] not in ('#', None):
                    self.leaf_ret[tgt] = t
                break
            op = w >> 26
            if op in (18, 16) or (op == 19 and w != 0x4E800020):
                break
            self.step(a, w, R, None, a, a + 4, [])
            a += 4
        return self.leaf_ret[tgt]

    def step(self, a, w, R, fn, s, e, rets):
        """execute one instruction on R; returns None (fall through) or a successor list"""
        op = w >> 26
        rD, rA, rB = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
        imm = w & 0xFFFF
        g = R.get
        rec = fn is not None
        if op in (14, 12, 13):          # addi / addic / addic.
            d = sx16(imm)
            if op == 14 and rA == 0:
                R[rD] = ('#', d & 0xFFFFFFFF, ())
                return None
            t = g(rA)
            nt = t_add(t, ('#', d & 0xFFFFFFFF, ())) if t is not None else None
            if t is not None and t[0] not in ('#', None) and rec:
                self.site(a, fn, 'addr', t, d, 'addi r%d, r%d, 0x%X' % (rD, rA, d & 0xFFFF))
            R.pop(rD, None)
            if nt is not None:
                R[rD] = nt
            return None
        if op == 15:                    # addis / lis
            t = ('#', 0, ()) if rA == 0 else g(rA)
            R.pop(rD, None)
            if t is not None:
                nt = t_add(t, ('#', (imm << 16) & 0xFFFFFFFF, ()))
                if nt is not None:
                    R[rD] = nt
            return None
        if op in (24, 25):              # ori / oris
            t = g(rD)
            R.pop(rA, None)
            if t is not None and t[0] == '#':
                R[rA] = ('#', t[1] | (imm if op == 24 else imm << 16), ())
            elif t is not None and imm == 0:
                R[rA] = t
            return None
        if op == 7:                     # mulli
            t = g(rA)
            R.pop(rD, None)
            nt = t_scale(t, sx16(imm))
            if nt is not None:
                R[rD] = nt
            return None
        if op == 21:                    # rlwinm
            sh, mb, me = (w >> 11) & 31, (w >> 6) & 31, (w >> 1) & 31
            t = g(rD)
            R.pop(rA, None)
            if mb == 0 and me == 31 - sh:
                nt = t_scale(t, 1 << sh)
                if nt is not None:
                    R[rA] = nt
            elif t is not None and t[0] == '#':
                v = t[1]
                v = ((v << sh) | (v >> (32 - sh))) & 0xFFFFFFFF if sh else v
                if mb <= me:
                    m = ((0xFFFFFFFF >> mb) & (0xFFFFFFFF << (31 - me))) & 0xFFFFFFFF
                else:
                    m = ((0xFFFFFFFF >> mb) | (0xFFFFFFFF << (31 - me))) & 0xFFFFFFFF
                R[rA] = ('#', v & m, ())
            elif sh == 0 and me == 31 and (t is None or t[0] is None):
                R[rA] = (None, 0, (1,)) if t is None else t       # clrlwi of an index
            return None
        if op in (20, 23, 26, 27, 28, 29, 30):
            R.pop(rA, None)
            return None
        if op in (8, 10, 11, 3, 2):
            if op == 8:
                R.pop(rD, None)
            return None
        if op in LOADS or op in FLOADS:
            nm, sz, upd = LOADS.get(op) or FLOADS[op]
            d = sx16(imm)
            t = g(rA) if rA else ('#', 0, ())
            nt = None
            if t is not None:
                if t[0] == '#':
                    ga = (t[1] + d) & 0xFFFFFFFF
                    if nm in ('lwz', 'lwzu') and ga in GLOBALS:
                        nt = (GLOBALS[ga], 0, ())
                        if rec:
                            self.site(a, fn, 'root', ('#', ga, ()), 0, '%s r%d <- [0x%08X]' % (nm, rD, ga))
                    elif nm in ('lwz', 'lwzu') and 0x10000000 <= ga < 0x11000000:
                        nt = ('@%08X' % ga, 0, ())          # some other object: tracked locally only
                elif t[0] is not None:
                    if rec:
                        self.site(a, fn, 'load', t, d, '%s %s%d, 0x%X(r%d)' % (nm, 'f' if op in FLOADS else 'r', rD, d & 0xFFFF, rA))
                    if nm in ('lwz', 'lwzu') and not t[2] and (t[0], t[1] + d) in FIELD_PTRS:
                        nt = (FIELD_PTRS[(t[0], t[1] + d)], 0, ())
                    elif nm in ('lwz', 'lwzu') and t[0].count('.') < 2:
                        nt = ('@%s.%X' % (t[0].lstrip('@'), t[1] + d), 0, ())
            if rA == 1 and op in LOADS and nm in ('lwz', 'lwzu'):
                nt = R.get(('s', d))
            if op in LOADS:
                R.pop(rD, None)
                if nt is not None:
                    R[rD] = nt
            if upd and rA:
                R.pop(rA, None)
                if t is not None:
                    na = t_add(t, ('#', d & 0xFFFFFFFF, ()))
                    if na is not None and rA != rD:
                        R[rA] = na
            return None
        if op in STORES:
            nm, sz, upd = STORES[op]
            d = sx16(imm)
            t = g(rA)
            if t is not None and t[0] not in ('#', None) and rec:
                self.site(a, fn, 'store', t, d, '%s %s%d, 0x%X(r%d)' % (nm, 'f' if op >= 52 else 'r', rD, d & 0xFFFF, rA))
            if op < 52:
                v = g(rD)
                if v is not None and v[0] not in ('#', None) and rec and rA != 1:
                    self.site(a, fn, 'escape', v, 0, '%s r%d, 0x%X(r%d)' % (nm, rD, d & 0xFFFF, rA))
                if rA == 1 and nm == 'stw':
                    if v is not None:
                        R[('s', d)] = v
                    else:
                        R.pop(('s', d), None)
            if upd:
                R.pop(rA, None)
                if t is not None and rA != 1:
                    na = t_add(t, ('#', d & 0xFFFFFFFF, ()))
                    if na is not None:
                        R[rA] = na
                if rA == 1 and t is not None:
                    R[1] = t                  # stwu r1: offsets stay frame-relative
            return None
        if op in (56, 57, 60, 61):      # psq_l / psq_lu / psq_st / psq_stu
            d = w & 0xFFF
            d = d - 0x1000 if d & 0x800 else d
            t = g(rA)
            if t is not None and t[0] not in ('#', None) and rec:
                self.site(a, fn, 'load' if op < 60 else 'store', t, d, 'psq_%s f%d, 0x%X(r%d)' % ('l' if op < 60 else 'st', rD, d & 0xFFFF, rA))
            if op in (57, 61):
                R.pop(rA, None)
            return None
        if op == 46:                    # lmw
            d = sx16(imm)
            for r in range(rD, 32):
                R.pop(r, None)
                if rA == 1 and ('s', d + 4 * (r - rD)) in R:
                    R[r] = R[('s', d + 4 * (r - rD))]
            return None
        if op == 47:                    # stmw
            d = sx16(imm)
            if rA == 1:
                for r in range(rD, 32):
                    if R.get(r) is not None:
                        R[('s', d + 4 * (r - rD))] = R[r]
                    else:
                        R.pop(('s', d + 4 * (r - rD)), None)
            return None
        if op == 31:
            xo = (w >> 1) & 0x3FF
            if xo in XFORMS:
                nm, sz, st, upd, fp = XFORMS[xo]
                ta, tb = (g(rA) if rA else None), g(rB)
                pt = None
                if ta is not None and ta[0] not in ('#', None):
                    pt = t_add(ta, tb if tb is not None else (None, 0, ('?',)))
                elif tb is not None and tb[0] not in ('#', None):
                    pt = t_add(tb, ta if ta is not None else (None, 0, ('?',)))
                if pt is not None and rec:
                    self.site(a, fn, 'store' if st else 'load', pt, 0, '%s %s%d, r%d, r%d' % (nm, 'f' if fp else 'r', rD, rA, rB))
                if st and not fp:
                    v = g(rD)
                    if v is not None and v[0] not in ('#', None) and rec:
                        self.site(a, fn, 'escape', v, 0, '%s r%d, r%d, r%d' % (nm, rD, rA, rB))
                if not st and not fp:
                    R.pop(rD, None)
                if upd:
                    R.pop(rA, None)
                    if pt is not None:
                        R[rA] = pt
                return None
            if xo == 444:               # or (mr)
                t = g(rD) if rD == rB else None
                R.pop(rA, None)
                if t is not None:
                    R[rA] = t
                return None
            if xo in (266, 10, 138):    # add / addc / adde
                ta, tb = g(rA), g(rB)
                R.pop(rD, None)
                if ta is None and tb is None:
                    return None
                nt = t_add(ta, tb)
                if nt is not None:
                    R[rD] = nt
                return None
            if xo in (40, 8):           # subf rD = rB - rA
                ta, tb = g(rA), g(rB)
                R.pop(rD, None)
                if tb is not None and ta is not None and ta[0] == '#':
                    nt = t_add(tb, ('#', (-ta[1]) & 0xFFFFFFFF, ()))
                    if nt is not None:
                        R[rD] = nt
                return None
            if xo == 235:               # mullw
                ta, tb = g(rA), g(rB)
                R.pop(rD, None)
                for x, y in ((ta, tb), (tb, ta)):
                    if x is not None and x[0] == '#' and (y is None or y[0] is None):
                        nt = t_scale(y, x[1] if x[1] < 0x80000000 else x[1] - 0x100000000)
                        if nt is not None:
                            R[rD] = nt
                        break
                return None
            if xo in X_WRITES_RA:
                R.pop(rA, None)
                return None
            if xo in X_NO_WRITE:
                return None
            if xo == 339 or xo == 371 or xo == 19 or xo == 83:   # mfspr / mftb / mfcr / mfmsr
                R.pop(rD, None)
                return None
            R.pop(rD, None)
            return None
        if op == 18:
            t = self._btarget(a, w)
            if w & 1:
                if rec:
                    self.call(a, t, R, fn)
                else:
                    for r in VOLATILE:
                        R.pop(r, None)
                return None
            if s <= t < e:
                return [t]
            if rec:                      # tail call
                self.call(a, t, R, fn, tail=True)
            return []
        if op == 16:
            t = self._bctarget(a, w)
            if w & 1:
                if rec:
                    self.call(a, None, R, fn)
                return None
            bo = (w >> 21) & 31
            if bo & 0x14 == 0x14:
                return [t]
            return [t, a + 4]
        if op == 19:
            xo = (w >> 1) & 0x3FF
            if xo == 16:                 # bclr
                bo = (w >> 21) & 31
                if w & 1:
                    if rec:
                        self.call(a, None, R, fn)
                    return None
                rets.append(R.get(3))
                return [] if bo & 0x14 == 0x14 else [a + 4]
            if xo == 528:                # bcctr
                if w & 1:
                    if rec:
                        self.call(a, None, R, fn)
                    return None
                # jump table: consecutive `b` words after the bctr, and relocated targets in fn
                succ = []
                x = a + 4
                while x < e and (self.img.w(x) >> 26) == 18 and not (self.img.w(x) & 3):
                    succ.append(x)
                    x += 4
                rt = self.img.reloc_targets
                i = bisect.bisect_left(rt, s)
                while i < len(rt) and rt[i] < e:
                    succ.append(rt[i])
                    i += 1
                return succ
            if xo in (0, 33, 129, 193, 225, 257, 289, 417, 449, 150):
                return None
            return None
        if op in (59, 63, 4, 17):
            return None
        R.pop(rD, None)
        return None

    def run(self, verbose=False):
        img = self.img
        seeds = set()
        for off, typ, val in img.rel:
            if typ in (4, 6) and val in GLOBALS and img.base <= off < img.end:
                seeds.add(img.func_of(off)[0])
        for a in ALLOCS:
            seeds.add(img.func_of(a)[0])
        for f, regs in SEEDS.items():
            c = frozenset(regs.items())
            self.ctx[f].add(c)
            self.pending.append((f, c))
        for f in sorted(seeds):
            self.ctx[f].add(frozenset())
            self.pending.append((f, frozenset()))
        rnd = 0
        while True:
            rnd += 1
            before = (len(self.pending), dict(self.ret))
            done = set()
            todo = [(f, c) for f in self.ctx for c in self.ctx[f]] if rnd > 1 else []
            todo += self.pending
            self.pending = []
            while todo:
                f, c = todo.pop()
                if (f, c) in done:
                    continue
                done.add((f, c))
                self.analyse(f, c)
                todo.extend(self.pending)
                self.pending = []
            if verbose:
                print('round %d: %d contexts, %d sites' % (rnd, len(done), len(self.sites)), file=sys.stderr)
            if self.ret == before[1] or rnd >= 4:
                break


# ---------------------------------------------------------------- classification
def locate(S, off):
    """(array tuple or None, kind index, offset in element, record) for object S field off"""
    if S == 'AI':
        if AI_REC <= off < AI_REC + AI_RSTRIDE * AI_NREC:
            rec, ro = divmod(off - AI_REC, AI_RSTRIDE)
            for arr in AI_REC_ARRAYS:
                st, n, es = arr[:3]
                if st <= ro < st + n * es:
                    k, sub = divmod(ro - st, es)
                    return arr, k, sub, rec
            return None, None, ro, rec
        return None, None, off, None
    lay = LAYOUTS.get(S)
    if not lay:
        return None, None, off, None
    for arr in lay[1]:
        st, n, es = arr[:3]
        if st <= off < st + n * es:
            k, sub = divmod(off - st, es)
            return arr, k, sub, None
    return None, None, off, None


def classify(site):
    S, off, strides, kind = site['S'], site['off'], site['strides'], site['kind']
    if kind == 'root':
        return dict(cls='root', array='-', detail='', patch=False)
    arr, k, sub, rec = locate(S, off)
    unk = '?' in strides
    recs = ''
    rest = list(strides)
    if S == 'AI':
        idx = [x for x in strides if sval(x) == AI_RSTRIDE]
        if idx:
            recs = 'record[i]'
            rest.remove(idx[0])
        elif rec is not None:
            recs = 'record %d' % rec
        if unk and not idx:
            recs = 'record ?'
    if arr is None:
        cls = 'other' if kind not in ('arg', 'escape') else 'other-' + kind
        reg = fieldregion(S, off)
        patch = bool(site.get('disp')) and reg is not None and not (reg[0] <= site['base'] < reg[1])
        det = recs
        ks = [x for x in rest if not (S == 'AI' and x == '?' and recs == 'record ?')]
        if ks:
            det += ' stride ' + '/'.join(('0x%X' % x) if isinstance(x, int) else
                                        ('L0x%X' % sval(x) if x != '?' else x) for x in ks)
        if kind == 'addr':
            for a2 in LAYOUTS.get(S, (0, []))[1] if S != 'AI' else AI_REC_ARRAYS:
                o2 = (off - AI_REC) % AI_RSTRIDE if S == 'AI' else off
                if 0 < a2[0] - o2 <= max(8, a2[2]):
                    det += ' loop base of %s@0x%X (start - 0x%X)' % (a2[3], a2[0], a2[0] - o2)
                    patch = bool(site.get('disp'))
                    cls = 'addr'
                    return dict(cls=cls, array='%s@0x%X' % (a2[3], a2[0]), detail=det.strip(), patch=patch)
        return dict(cls=cls, array=fieldname(S, off), detail=det, patch=patch)
    st, n, es, name = arr[:4]
    # does this instruction's own immediate carry the array base? (then a move of the array patches it)
    # (a pointer already inside the per-kind block moves with it: only displacements taken from
    # outside the block are patched when the block moves)
    lo_, hi_ = per_kind_range(S)
    b = site.get('base', 0)
    if S == 'AI':
        lo_, hi_ = AI_REC_ARRAYS[0][0], AI_RSTRIDE
        b = (b - AI_REC) % AI_RSTRIDE if b >= AI_REC else -1
    patch = bool(site.get('disp')) and not (lo_ - 8 <= b < hi_)   # (-8: a loop's pre-increment base)
    note = ''
    if kind == 'addr' and k == n - 1 and sub == 0:
        arrs = LAYOUTS.get(S, (0, []))[1] if S != 'AI' else AI_REC_ARRAYS
        for a2 in arrs:
            if a2[0] == st + n * es:
                note = ' (or the loop base of %s@0x%X, start - 0x%X)' % (a2[3], a2[0], es)
        for f0, fsz, fnm in (LAYOUTS[S][2] if S in LAYOUTS else []):
            if f0 == st + n * es:
                note = ' (or the loop base of %s, start - 0x%X)' % (fnm.split(' (')[0], es)
    kinds_idx = list(rest)
    if S == 'AI' and '?' in rest and not any(sval(x) == AI_RSTRIDE for x in strides):
        kinds_idx.remove('?')                        # an unknown index taken as the record index
    if kind in ('arg', 'escape', 'addr'):
        cls = kind
    elif not kinds_idx:
        cls = 'const'
    elif any(isinstance(x, str) and x.startswith('L') for x in kinds_idx):
        cls = 'walk'
    else:
        cls = 'indexed'
    det = []
    if recs:
        det.append(recs)
    if not kinds_idx:
        det.append('kind 0x%02X' % k + (' +0x%X' % sub if sub else ''))
    else:
        det.append('stride ' + '/'.join(('0x%X' % x) if isinstance(x, int) else
                                       ('L0x%X' % sval(x) if x != '?' else x) for x in kinds_idx) +
                   (' +0x%X' % (k * es + sub) if (k * es + sub) else ''))
        sv = [sval(x) for x in kinds_idx if sval(x)]
        if sv and es not in sv and '?' not in kinds_idx:
            det.append('(stride != elem 0x%X)' % es)
    return dict(cls=cls, array='%s@0x%X' % (name, st), detail=' '.join(det) + note, patch=patch)


def fieldregion(S, off):
    lay = LAYOUTS.get(S)
    if lay:
        for st, sz, nm in lay[2]:
            if st <= off < st + sz:
                return st, st + sz
    return None


def fieldname(S, off):
    lay = LAYOUTS.get(S)
    if lay:
        for st, sz, nm in lay[2]:
            if st <= off < st + sz:
                return '%s+0x%X' % (nm.split(' (')[0], off - st)
    return '+0x%X' % off


def per_kind_range(S):
    if S == 'AI':
        return AI_REC + AI_REC_ARRAYS[0][0], AI_REC + AI_RSTRIDE * AI_NREC
    arrs = LAYOUTS.get(S, (0, []))[1]
    if not arrs:
        return (0, 0)
    return min(a[0] for a in arrs), max(a[0] + a[1] * a[2] for a in arrs)


def missed(img, sc, all_text=False, lo=0x111C, hi=0x25B0, struct='MGR'):
    """D-form accesses with a displacement in [lo, hi) whose base the data-flow did not resolve, in
    the functions that touch `struct` (or in all of .text)"""
    seen = set(x['addr'] for x in sc.sites.values()) | sc.other
    fns = set(x['fn'] for x in sc.sites.values()
              if x['S'] == struct or (x['kind'] == 'root' and GLOBALS.get(x['off']) == struct))
    out = []
    W, base = img.W, img.base
    lo16 = set(off - 2 for off, typ, val in img.rel if typ in (4, 6))   # address constants
    rng = range(len(W)) if all_text else None
    if not all_text:
        idx = []
        for f in sorted(fns):
            s, e = img.func_of(f)
            idx.extend(range((s - base) >> 2, (e - base) >> 2))
        rng = sorted(set(idx))
    for i in rng:
        w = W[i]
        op = w >> 26
        if op in LOADS or op in FLOADS or op in STORES or op in (14, 12, 13):
            d = w & 0xFFFF
            ra = (w >> 16) & 31
            if lo <= d < hi and ra not in (0, 1):
                a = base + 4 * i
                if a not in seen and a not in lo16:
                    out.append(a)
    return out


def count_loops(img, counts=(0x40, 0x41, 0x42)):
    """Loops that run 0x40-0x42 times: (counter set-up address, count, how, loop head, loop end).
    how: 'ctr' (`li rC, N` ... `mtctr rC` ... `bdnz`), 'dec' (`li rC, N` ... `addic. rC, rC, -1` ...
    `bne` back), 'cmp' (`cmpwi / cmplwi rI, N` then a conditional branch back)."""
    W, base = img.W, img.base
    out = []
    n = len(W)

    def back_branch(i0, lo):
        for j in range(i0, min(i0 + 600, n)):
            x = W[j]
            op = x >> 26
            if op == 16 and not (x & 1):
                off = x & 0xFFFC
                off = off - 0x10000 if off & 0x8000 else off
                if off < 0 and base + 4 * j + off >= lo:
                    return j, base + 4 * j + off
            if x == 0x4E800020:
                return None
        return None

    for i, w in enumerate(W):
        op = w >> 26
        if op == 14 and ((w >> 16) & 31) == 0 and (w & 0xFFFF) in counts:
            r = (w >> 21) & 31
            how = None
            for j in range(i + 1, min(i + 16, n)):
                x = W[j]
                if x == (0x7C0903A6 | (r << 21)):
                    how = 'ctr'
                    break
                if (x >> 26) == 13 and ((x >> 21) & 31) == r and ((x >> 16) & 31) == r and (x & 0xFFFF) == 0xFFFF:
                    how = 'dec'
                    break
            if how is None:
                for j in range(i + 1, min(i + 200, n)):
                    x = W[j]
                    if (x >> 26) == 13 and ((x >> 21) & 31) == r and ((x >> 16) & 31) == r and (x & 0xFFFF) == 0xFFFF:
                        how = 'dec'
                        break
                    if (x >> 26) == 31 and ((x >> 1) & 0x3FF) in (0, 32) and ((x >> 11) & 31) == r:
                        how = 'cmp'
                        break
                    if ((x >> 21) & 31) == r and (x >> 26) in (14, 15, 32, 34, 21, 7):
                        break       # counter register overwritten: not a loop count
            if how is None:
                continue
            bb = back_branch(i + 1, base + 4 * i - 0x40)
            if bb:
                out.append((base + 4 * i, w & 0xFFFF, how, bb[1], base + 4 * bb[0]))
        elif op in (10, 11) and (w & 0xFFFF) in counts:
            nx = W[i + 1] if i + 1 < n else 0
            if (nx >> 26) == 16:
                off = nx & 0xFFFC
                off = off - 0x10000 if off & 0x8000 else off
                if off < 0:
                    out.append((base + 4 * i, w & 0xFFFF, 'cmp', base + 4 * (i + 1) + off, base + 4 * (i + 1)))
    return out


def loop_arrays(img, sc, loops):
    """for each count loop, the arrays it walks (accesses inside the loop whose address has a loop stride)"""
    by_fn = collections.defaultdict(list)
    for lp in loops:
        by_fn[img.func_of(lp[0])[0]].append(lp)
    sc.trace = set(by_fn)
    sc.traced = []
    for f in sorted(by_fn):
        sc.analyse(f, frozenset())
    acc = collections.defaultdict(list)
    for a, fn, kind, S, off, strides, ins in sc.traced:
        acc[fn].append((a, kind, S, off, strides, ins))
    res = []
    for f in sorted(by_fn):
        for lp in by_fn[f]:
            li, cnt, how, head, end = lp
            arrs = {}
            for a, kind, S, off, strides, ins in acc[f]:
                if not (head <= a <= end) or kind in ('arg', 'escape'):
                    continue
                st = [x for x in strides if isinstance(x, str) and x.startswith('L')]
                if not st:
                    continue
                key = (S, off, tuple(strides))
                arrs.setdefault(key, (a, kind, ins))
            res.append((lp, f, arrs))
    return res


PRIO = {'escape': 0, 'arg': 1, 'walk': 2, 'indexed': 3, 'addr': 4, 'const': 5}


def report_rows(sc, struct=None, show_all=False):
    """one row per (instruction, object, array): the same instruction met in several contexts or
    data-flow passes keeps its most general class (walk > indexed > const)"""
    best = {}
    for s in sc.sites.values():
        if s['S'] not in LAYOUTS and s['kind'] != 'root':
            continue
        S = s['S'] if s['kind'] != 'root' else GLOBALS.get(s['off'], '?')
        if struct and struct != 'ALL' and S != struct:
            continue
        c = classify(s)
        if c['cls'].startswith('other') and not show_all:
            continue
        key = (s['addr'], S, c['array'], c['cls'] in ('arg', 'escape'))
        old = best.get(key)
        if old is None or PRIO.get(c['cls'], 9) < PRIO.get(old[1]['cls'], 9):
            best[key] = (dict(s, S=S), c)
    rows = sorted(best.values(), key=lambda r: (r[0]['S'], r[0]['addr']))
    for s, c in rows:       # a function only reached with a tracked pointer argument (shared helper)
        c['helper'] = frozenset() not in sc.ctx.get(s['fn'], ())
    return rows


VL_LOAD, VL_TAIL, VL_DEFAULT, VL_UNLOAD_STORE = 0x02EA6BC4, 0x02EA8D50, 0x02EA6DB8, 0x02EA6AF8
MGR_ALLOC = (0x02E4E684, 0x02EA5860)          # li r3, 0x25B0
MGR_LOOPS = (0x02EA5C9C, 0x02EA5CBC, 0x02EA6B8C)   # li rX, 0x41 (refcnt clear, index map, unload all)
EQ_ALLOC = (0x02EA5964, 0x02EA5978)           # li r3, 0x424 / li r4, 0x424 (alloc, clear)
AI_GUARDS = (0x02751B04, 0x02751B28)          # the two `slwi r0, r10, 2` before rec+0x384 / +0x280 [k] += 1


def mgr_layout(n):
    """the relocated per-kind block: the same arrays in the same order, n entries each, from 0x25B0"""
    out, at = {}, 0x25B0
    for st, cnt, es, name, _m in LAYOUTS['MGR'][1]:
        out[name] = (st, at)
        at += n * es
        at = (at + 3) & ~3
    return out, at


def imm_patch(img, a, delta):
    w = img.w(a)
    v = sx16(w & 0xFFFF) + delta
    if not -0x8000 <= v < 0x8000:
        return None
    return (w & 0xFFFF0000) | (v & 0xFFFF)


def plan(img, sc, n):
    """The word patches of the relocate-and-mirror plan for the FighterParamManager (docs/kind-expansion-ram.md):
    every per-kind access that computes its address from outside the block gets the new array's offset,
    except the reads that have the kind built in (kinds 0x00-0x40, they keep reading the old arrays,
    which stay a mirror) and the vanilla vl-load cases. Prints rpx_patch.py arguments. Untested."""
    rows = report_rows(sc, 'MGR', False)
    lay, end = mgr_layout(n)
    names = [x[3] for x in LAYOUTS['MGR'][1]]
    out, keep = [], collections.Counter()
    for s, c in rows:
        if not c['patch'] or c['cls'] in ('root',):
            continue
        arr = c['array'].split('@')[0]
        if c['cls'] == 'addr' and arr in names:
            # `addi rX, mgr, start - step` before a `stwu` loop: the last element of one array or the
            # loop base of what follows it? Decided by what the function walks.
            a0 = LAYOUTS['MGR'][1][names.index(arr)]
            nxt_start = a0[0] + a0[1] * a0[2]
            if s['off'] == nxt_start - a0[2] or s['off'] in (nxt_start - 4, nxt_start - 8):
                walked = [x for x in sc.sites.values() if x['fn'] == s['fn'] and x['S'] == 'MGR' and
                          any(isinstance(v, str) and v.startswith('L') for v in x['strides']) and
                          nxt_start <= x['off'] < nxt_start + 0x10]
                if walked:
                    nxt = [x for x in LAYOUTS['MGR'][1] if x[0] == nxt_start]
                    if not nxt:
                        keep['loop bases of fields after the block (they do not move)'] += 1
                        continue
                    arr = nxt[0][3]
        st, nst = lay[arr]
        store = s['ins'].startswith('st')
        if arr == 'vl' and c['cls'] == 'const' and not store and s['fn'] != VL_LOAD:
            keep['vl reads with the kind built in (mirror)'] += 1
            continue
        if s['fn'] == VL_LOAD and arr == 'vl' and s['addr'] != VL_DEFAULT and c['cls'] in ('const', 'addr'):
            keep['vanilla vl-load cases (old vl, mirrored at the tail)'] += 1
            continue
        new = imm_patch(img, s['addr'], nst - st)
        out.append((s['addr'], new, s['ins'], arr, nst - st))
    print('# FighterParamManager: relocate + mirror, N = 0x%X kinds; new block 0x25B0-0x%X' % (n, end))
    for nm in names:
        print('#   %-7s 0x%04X -> 0x%04X' % (nm, lay[nm][0], lay[nm][1]))
    print('# kept (not patched): %s' % ', '.join('%s %d' % kv for kv in sorted(keep.items())))
    print('# allocation size (li r3, 0x25B0):')
    for a in MGR_ALLOC:
        w = img.w(a)
        print('0x%08X=0x%08X' % (a, (w & 0xFFFF0000) | end))
    print('# loop counts 0x41 -> N:')
    for a in MGR_LOOPS:
        w = img.w(a)
        print('0x%08X=0x%08X' % (a, (w & 0xFFFF0000) | n))
    print('# %d immediates (address=new word  # instruction, array, delta):' % len(out))
    for a, new, ins, arr, d in sorted(out):
        print('0x%08X=%s  # %s  [%s %+#x]' % (a, '0x%08X' % new if new is not None else 'OUT-OF-RANGE', ins, arr, d))
    print('# hooks (caves, to write): vl-load common tail 0x%08X: if kind < 0x41, new vl[kind] = old vl[kind];'
          ' unload 0x%08X: also clear old vl[kind] when kind < 0x41' % (VL_TAIL, VL_UNLOAD_STORE))
    print('# EQ (equipment object, array at its end): 0x424 -> 0x%X' % (0x320 + 4 * n))
    for a in EQ_ALLOC:
        w = img.w(a)
        print('0x%08X=0x%08X' % (a, (w & 0xFFFF0000) | (0x320 + 4 * n)))
    print('# AI records (cap plan): guard kind < 0x41 before 0x%08X and 0x%08X (two small caves)' % AI_GUARDS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('rpx', nargs='?', default=RPX)
    ap.add_argument('--struct', '-S', help='MGR, EQ, AI or AIM (ALL with --missed: all of .text)')
    ap.add_argument('--all', action='store_true', help='also fields that are not per-kind')
    ap.add_argument('--summary', action='store_true', help='counts only')
    ap.add_argument('--missed', action='store_true', help='completeness check (see above)')
    ap.add_argument('--loops', action='store_true', help='li 0x40-0x42 -> mtctr loops in .text')
    ap.add_argument('--csv')
    ap.add_argument('--plan', metavar='N', help='print the word patches of the recommended plan for N kinds')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    img = Image(a.rpx)
    sc = Scanner(img)
    sc.run(a.v)
    if a.plan:
        plan(img, sc, int(a.plan, 0))
        return
    rows = report_rows(sc, a.struct, a.all)
    fmt = '0x%08X 0x%08X %-4s %-8s %-14s %-36s %s'
    if not a.summary:
        print('%-10s %-10s %-4s %-8s %-14s %-36s %s' % ('addr', 'function', 'obj', 'class', 'array',
                                                        'instruction', 'detail'))
        for s, c in rows:
            print(fmt % (s['addr'], s['fn'], s['S'], c['cls'], c['array'], s['ins'],
                         c['detail'] + ('  [via arg]' if c['helper'] else '') +
                         ('  *imm' if c['patch'] else '')))
    cnt = collections.Counter()
    imm = collections.Counter()
    addrs = collections.defaultdict(set)
    fns = collections.defaultdict(set)
    for s, c in rows:
        key = (s['S'], c['array'], c['cls'] + ('/viaarg' if c['helper'] else ''))
        cnt[key] += 1
        imm[key] += c['patch']
        addrs[s['S']].add(s['addr'])
        fns[s['S']].add(s['fn'])
    print('\n# summary: object, array, class (/viaarg: in a function that receives the pointer as an '
          'argument), instructions, of which *imm (the instruction\'s own immediate holds the array '
          'offset: patched if the array moves)')
    for k in sorted(cnt):
        print('%-4s %-28s %-15s %5d %5d' % (k + (cnt[k], imm[k])))
    for S in sorted(addrs):
        print('%-4s: %d instructions in %d functions' % (S, len(addrs[S]), len(fns[S])))
    if a.missed:
        print('\n# unresolved D-form displacements in 0x111C..0x25B0 (%s)' %
              ('all of .text' if a.struct == 'ALL' else 'functions with sites'))
        m = missed(img, sc, a.struct == 'ALL')    # (MGR's range; see the docstring)
        for x in m:
            print('0x%08X 0x%08X 0x%08X' % (x, img.func_of(x)[0], img.w(x)))
        print('%d unresolved' % len(m))
    if a.loops:
        print('\n# loops that run 0x40-0x42 times, and what they walk '
              '(S+off: object; $: static data; STACK: the frame; @: other object; L: step)')
        for lp, f, arrs in loop_arrays(img, sc, count_loops(img, (0x41, 0x42))):
            li, cnt, how, head, end = lp
            print('0x%08X fn 0x%08X count 0x%X %-3s loop 0x%08X-0x%08X' % (li, f, cnt, how, head, end))
            for (S, off, strides), (x, kind, ins) in sorted(arrs.items(), key=lambda kv: kv[1][0]):
                st = '/'.join(('0x%X' % v) if isinstance(v, int) else
                              ('L0x%X' % sval(v) if v != '?' else v) for v in strides)
                print('      0x%08X %-6s %s+0x%X step %s   %s' % (x, kind, S, off, st, ins))
    if a.csv:
        with open(a.csv, 'w') as f:
            f.write('addr,function,object,class,array,instruction,detail,via_arg,imm,field\n')
            for s, c in rows:
                f.write('0x%08X,0x%08X,%s,%s,%s,"%s","%s",%d,%d,0x%X\n' % (
                    s['addr'], s['fn'], s['S'], c['cls'], c['array'], s['ins'], c['detail'],
                    c['helper'], c['patch'], s['off'] if s['kind'] != 'root' else 0))


if __name__ == '__main__':
    main()

