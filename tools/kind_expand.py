#!/usr/bin/env python3
"""New fighter kinds (0x41, 0x42, ...): the executable side of docs/kind-expansion.md, generated from
an "extra kinds" JSON (one record per new kind). Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py build/cross_f.rpx OUT.rpx $(python3 tools/biome_select_cave.py) \\
      $(python3 tools/monster_roll_cave.py) $(python3 tools/trait_badge_cave.py) \\
      $(python3 tools/kind_expand.py)
  python3 tools/kind_expand.py [--kinds FILE] [--rpx RPX] [--info]
  python3 tools/kind_expand.py --rescan-ram [--rpx RPX]   (refresh tools/kind_expand_ram.json, ~10 s)

FILE defaults to tools/extra_kinds.json, RPX (the base whose words are checked and copied) to
build/cross_f.rpx. tools/add_fighter.py makes the data files from the same records;
tools/kind_expand_test.py runs the patched functions in unicorn.

The JSON:
  {"capacity": "0x60",                       kinds the per-kind arrays and tables hold (default 0x60)
   "kinds": [{"kind": "0x41", "name": "supamario", "cap": "Supamario", "base": "mario",
              "ai": "base",                   or "generic" (default "base")
              "ui": {"id": 59, "name": "Supamario"},       (also read by add_fighter.py)
              "vl": "fighter_param_vl_supamario",           (optional, this default)
              "descriptor": {"from": "mario"}}]}            (optional, the base by default)
Kinds are consecutive from 0x41 and below the capacity; "base" is a kind name or number of a game
kind (0x00-0x40) whose native code the new kind uses. Capacity: everything kind-sized is made for
`capacity` kinds, so adding a fighter only adds its record (the RAM layout stays the same); only the
random-fighter picks use the real count (the highest kind + 1), so they don't waste draws.

What it patches (addresses are the game's; docs/kind-expansion*.md have the research):
1. FighterParamManager [0x102FF448] (docs/kind-expansion-ram.md, plan (d)): the 9 per-kind arrays
   (0x111C-0x2364, [0x41] each) get a copy for `capacity` kinds at the end of a bigger allocation
   (0x25B0 + capacity * 0x48: the two `li r3, 0x25B0`); the 164 instructions that address them with a
   variable kind (tools/kind_ram_scan.py plan_sites(), cached in tools/kind_expand_ram.json and
   checked word for word) and the 3 loops over 0x41 kinds use the new arrays. The 928 reads with the
   kind built into the offset (vanilla kinds reading their own params) keep reading the old vl array,
   which stays a mirror: hook A at the vl load's common tail (0x02EA8D50) copies old vl[k] to new
   vl[k] for k < 0x41, hook B at the unload's store (0x02EA6AF8) clears both.
2. The equipment-ability object (0x424 bytes, its [0x41] array at +0x320 ends it): grown in place to
   0x320 + 4 * capacity (0x02EA5964, 0x02EA5978).
3. AI (amiibo learning counts, [0x41] at the end of each AI record): the two increments in 0x0274FE18
   (0x02751B04 / 0x02751B28) skip kinds >= 0x41, rewritten in place (no cave: the code is out of a
   branch's reach from the grown code space).
4. The six 65-case kind switches (specializer 0x02E669F0, descriptor 0x02E43148, vl load 0x02EA6C94,
   vl unload 0x02EA5DA0, AI 0x02E02458 and 0x0275B44C): their `b` jump tables become tables of
   addresses in the cave (`add` -> `lwzx`, the table address and the bound changed, 3-4 words each),
   so cases anywhere are reachable; entries 0x00-0x40 are the game's own targets. A new kind gets:
   specializer = the base's case (its static singleton), descriptor = its own (below), vl load /
   unload = its own cases (below), AI = the base's cases ("ai": "base") or the default (generic).
   Unused kinds up to the capacity go to the default, as kinds past the capacity do.
5. Tables (cave copies with `capacity` rows, readers repointed, the readers' relocations moved to a
   dead word so the loader doesn't put the old addresses back): names (lowercase 0x102FF484,
   Capitalised 0x102FF588, vl file 0x10353DB4), special-block sizes (u16 0x1012F638, u8 x4
   0x1012F6BC...) with their getters' bounds, sound class (0x100D21D8), and the character id -> UI
   name table (0x1033BE68, 0x0293DCCC) with {ui id, ui name} for each new kind. New rows = the
   base's values; unused kinds: "" and 0.
6. Kind-count immediates: random fighter picks (0x021ED1A0 / B0 / E0, 0x021E6E30: the count),
   kind -> character id (0x0309FE68), sound banks (0x02A79158), AI motion count (0x0275BAC0), AI
   files (0x02DE1DDC), fighter resource holders (0x02AC3F7C, 0x02761528): the capacity; the
   character-name count (0x0293DCD4) and the random-select entries (0x02FFB644) + 1 per UI entry.
7. Per new kind, in the cave: its descriptor (a copy of the base's with +0 = kind, +4 = its own motion
   info and main motion table (written at run time by 0x02EA9008, so the cave must be writable:
   it is on Cemu), +0x1C = 0); its descriptor case; its vl load case (the base's case copied: it
   first loads the base's params (the base's native code reads the base's slot), then parses
   fighter_param_vl_<name>.bin with the base's parser into the equipment object's +0x320 + 4 * kind and
   the new vl / vl50 arrays); its vl unload case (the base's, the kind's fields, then unloads the base).

Space: the grown code space from 0x04B85000 (trait_badge_cave.py ends at 0x04B84800) to at most
0x04BB8000 (the text region ends at 0x04BB8670).
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch  # noqa: E402
from ppcasm import Asm, ha  # noqa: E402

RPX = os.path.join(HERE, '..', 'build', 'cross_f.rpx')
SPEC = os.path.join(HERE, 'extra_kinds.json')
RAM_CACHE = os.path.join(HERE, 'kind_expand_ram.json')
CAVE = 0x04B85000
LIMIT = 0x04BB8000
RELOC_DUMMY = 0x037EE73C       # dead word for moved relocations (starcopy_cave.py / stage_slot_cave.py)
OLD_N = 0x41
DEFAULT_CAPACITY = 0x60

# FighterParamManager (docs/kind-expansion-ram.md)
MGR_SIZE = 0x25B0
MGR_ALLOC = (0x02E4E684, 0x02EA5860)                     # li r3, 0x25B0
MGR_LOOPS = ((0x02EA5C9C, 'li r0, %d'), (0x02EA5CBC, 'li r11, %d'), (0x02EA6B8C, 'li r29, %d'))
MGR_ARRAYS = [(0x111C, 4, 'vl'), (0x1220, 4, 'refcnt'), (0x1324, 4, 'x1324'), (0x1428, 4, 'x1428'),
              (0x152C, 4, 'x152C'), (0x1630, 4, 'fpidx'), (0x1734, 4, 'vl50'), (0x1838, 0x24, 'att'),
              (0x215C, 8, 'attp')]
EQ_ALLOC = ((0x02EA5964, 'li r3, %d'), (0x02EA5978, 'li r4, %d'))   # 0x424
EQ_ARRAY = 0x320
VL_LOAD, VL_TAIL = 0x02EA6BC4, 0x02EA8D50
VL_UNLOAD, VL_UNLOAD_TAIL, VL_UNLOAD_STORE = 0x02EA5D64, 0x02EA6AF4, 0x02EA6AF8
AI_GUARD = 0x02751B00          # beq 0x02751B28; the two increments 0x02751B04-0x02751B3B

# the six 65-case switches: compare, kind register, shape, jump table
SWITCHES = {
    'specializer': (0x02E669F0, 4, 'r0', 0x02E66A10),
    'descriptor': (0x02E43148, 4, 'r0', 0x02E43168),
    'vl_load': (0x02EA6C94, 12, 'r0', 0x02EA6CB4),
    'vl_unload': (0x02EA5DA0, 6, 'r0li', 0x02EA5DC4),
    'ai_a': (0x02E02458, 11, 'r12', 0x02E02474),
    'ai_b': (0x0275B44C, 5, 'r0', 0x0275B46C),
}

# tables: name -> (address, entry size, [(reader word, original, new with {T})])
TABLES = {
    'lower': (0x102FF484, 4, [(0x0275DB24, 'lis r0, 0x1030', 'lis r0, {ha}'),
                              (0x0275DB2C, 'addic r0, r0, -0xB7C', 'addic r0, r0, {lo}')]),
    'cap': (0x102FF588, 4, [(0x0275DB38, 'lis r0, 0x1030', 'lis r0, {ha}'),
                            (0x0275DB40, 'addic r0, r0, -0xA78', 'addic r0, r0, {lo}')]),
    'vl': (0x10353DB4, 4, [(0x02EA6C40, 'addis r10, r27, 0x1035', 'addis r10, r27, {ha}'),
                           (0x02EA6C4C, 'lwz r6, 0x3DB4(r10)', 'lwz r6, {lo}(r10)')]),
    'sp16': (0x1012F638, 2, [(0x02EA90E8, 'lis r0, 0x1013', 'lis r0, {ha}'),
                             (0x02EA90F0, 'addic r0, r0, -0x9C8', 'addic r0, r0, {lo}')]),
    'spN': (0x1012F6BC, 1, [(0x02EA910C, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'),
                            (0x02EA9110, 'lbz r3, -0x944(r12)', 'lbz r3, {lo}(r12)')]),
    'spS': (0x1012F700, 1, [(0x02EA9128, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'),
                            (0x02EA912C, 'lbz r3, -0x900(r12)', 'lbz r3, {lo}(r12)')]),
    'spHi': (0x1012F744, 1, [(0x02EA9144, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'),
                             (0x02EA9148, 'lbz r3, -0x8BC(r12)', 'lbz r3, {lo}(r12)')]),
    'spLw': (0x1012F788, 1, [(0x02EA9160, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'),
                             (0x02EA9164, 'lbz r3, -0x878(r12)', 'lbz r3, {lo}(r12)')]),
    'snd': (0x100D21D8, 4, [(0x02AB8CB0, 'lis r0, 0x100D', 'lis r0, {ha}'),
                            (0x02AB8CB8, 'addic r0, r0, 0x21D8', 'addic r0, r0, {lo}')]),
}
NAME_TABLES = ('lower', 'cap', 'vl')
SIZE_GETTERS = ((0x02EA90E0, 'cmplwi r4, %d'), (0x02EA9104, 'cmplwi r4, %d'), (0x02EA9120, 'cmplwi r4, %d'),
                (0x02EA913C, 'cmplwi r4, %d'), (0x02EA9158, 'cmplwi r4, %d'))
CHR_TABLE, CHR_COUNT = 0x1033BE68, 0x53       # {u32 id, char *name}, the first {-1, set at run time}
CHR_READER = ((0x0293DCD0, 'lis r3, 0x1034', 'lis r3, {ha}'), (0x0293DCD8, 'addi r3, r3, -0x4198', 'addi r3, r3, {lo}'))
CHR_COUNT_SITE = 0x0293DCD4                    # li r4, 0x53
RANDOM_SELECT, RANDOM_SELECT_COUNT = 0x02FFB644, 0x51   # li r23, 0x51 (database entries scanned)
# (address, original, new with %d, 'cap' = capacity / 'cap-1' / 'count')
IMMEDIATES = [
    (0x021ED1A0, 'li r4, 0x41', 'li r4, %d', 'count'),          # random fighter: rand(0x41)
    (0x021ED1B0, 'cmpwi r27, 0x41', 'cmpwi r27, %d', 'count'),  # wrap
    (0x021ED1E0, 'cmplwi r28, 0x41', 'cmplwi r28, %d', 'count'),  # retries
    (0x021E6E30, 'li r4, 0x41', 'li r4, %d', 'count'),          # second random pick
    (0x0309FE68, 'cmpwi r4, 0x41', 'cmpwi r4, %d', 'cap-1'),    # kind -> character id (ble)
    (0x02A79158, 'cmplwi r29, 0x41', 'cmplwi r29, %d', 'cap'),  # sound bank loader
    (0x0275BAC0, 'cmpwi r4, 0x41', 'cmpwi r4, %d', 'cap'),      # kind -> motion count (AI)
    (0x02DE1DDC, 'cmplwi r6, 0x41', 'cmplwi r6, %d', 'cap'),    # AI file loader
    (0x02AC3F7C, 'cmplwi r0, 0x41', 'cmplwi r0, %d', 'cap'),    # fighter resource holder
    (0x02761528, 'cmplwi r5, 0x41', 'cmplwi r5, %d', 'cap'),    # its twin
]
DESC_SIZE, MINFO_SIZE = 0x38, 0x18
# kinds whose vl load tail (0x02EA8DA4-) stores an extra vector (x1324 / x152C) keyed by the kind
# itself: a new kind with one of these bases doesn't get it (the base's own slot still has it)
TAIL_EXTRA_KINDS = (5, 6, 8, 0x17, 0x18, 0x19, 0x1C, 0x20, 0x21, 0x23, 0x26, 0x35)
KIND_NAMES = None              # filled from the RPX (lowercase name table)


def sx16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def slo(v):
    return sx16(v)


def num(v):
    return int(v, 0) if isinstance(v, str) else int(v)


def one(addr, text):
    a = Asm(addr)
    a.asm(text)
    w = a.words()
    assert len(w) == 1, text
    return w[0]


def branch_target(addr, w):
    op = w >> 26
    if op == 18:
        off = w & 0x3FFFFFC
        off -= 0x4000000 if off & 0x2000000 else 0
        return (off if w & 2 else addr + off) & 0xFFFFFFFF
    if op == 16:
        return ((sx16(w & 0xFFFC) if w & 2 else addr + sx16(w & 0xFFFC))) & 0xFFFFFFFF
    raise ValueError('not a branch: %08X at %08X' % (w, addr))


def b_word(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, 'branch out of reach: %08X -> %08X' % (src, dst)
    return (18 << 26) | (off & 0x3FFFFFC) | int(link)


def bc_word(src, dst, w):
    off = dst - src
    assert -0x8000 <= off < 0x8000, 'conditional branch out of reach'
    return (w & 0xFFFF0003) | (off & 0xFFFC)


class Image:
    """the base RPX: loadable sections and the relocation offsets"""

    def __init__(self, path):
        self.path = path
        self.d, _o, _e, self.secs = rpx_patch.load(path)
        self.mem = []
        for s in self.secs:
            if s[1] == 1 and s[3] and s[5]:
                self.mem.append((s[3], bytes(rpx_patch.section_data(self.d, s))))
        self._rel = None

    def blob(self, a, n):
        for base, data in self.mem:
            if base <= a and a + n <= base + len(data):
                return data[a - base:a - base + n]
        raise KeyError('0x%08X not in the RPX' % a)

    def w(self, a):
        return struct.unpack('>I', self.blob(a, 4))[0]

    def h(self, a):
        return struct.unpack('>H', self.blob(a, 2))[0]

    def b(self, a):
        return self.blob(a, 1)[0]

    def cstr(self, a):
        out = b''
        while True:
            c = self.blob(a + len(out), 1)
            if c == b'\0':
                return out.decode('latin1')
            out += c

    def text_end(self):
        return max(base + len(data) for base, data in self.mem if base < 0x10000000)

    def relocs(self):
        """offsets of every relocation (each word a relocation patches is in [off & ~3, +4))"""
        if self._rel is None:
            self._rel = set()
            for s in self.secs:
                if s[1] == 4:   # SHT_RELA
                    data = rpx_patch.section_data(self.d, s)
                    for o in range(0, len(data), 12):
                        self._rel.add(struct.unpack('>I', data[o:o + 4])[0] & ~3)
        return self._rel


def load_spec(path):
    spec = json.load(open(path))
    if isinstance(spec, list):
        spec = {'kinds': spec}
    cap = num(spec.get('capacity', DEFAULT_CAPACITY))
    kinds = []
    for i, r in enumerate(spec['kinds']):
        ui = dict(r.get('ui') or {})
        if r.get('ui_id') is not None:
            ui.setdefault('id', r['ui_id'])
        rec = {'kind': num(r['kind']), 'name': r['name'], 'cap': r.get('cap') or r['name'].capitalize(),
               'base': r['base'], 'ai': r.get('ai', 'base'),
               'ui_id': num(ui['id']) if ui.get('id') is not None else None}
        rec['ui_name'] = ui.get('name') or rec['cap']
        rec['vl'] = r.get('vl') or 'fighter_param_vl_' + rec['name']
        rec['desc_from'] = (r.get('descriptor') or {}).get('from', r['base'])
        assert rec['kind'] == OLD_N + i, 'kinds must be consecutive from 0x41 (record %d is 0x%X)' % (i, rec['kind'])
        assert rec['ai'] in ('base', 'generic'), rec['ai']
        assert len(rec['vl']) + len('param/fighter/.bin') < 0x64, 'vl file name too long'
        kinds.append(rec)
    assert kinds, 'no kinds'
    assert kinds[-1]['kind'] < cap, 'capacity 0x%X is too small for kind 0x%X' % (cap, kinds[-1]['kind'])
    assert cap <= 0x13F, 'capacity above 0x13F: the relocated arrays would pass +0x8000'
    uis = [k['ui_id'] for k in kinds if k['ui_id'] is not None]
    assert len(set(uis)) == len(uis), 'duplicate ui ids'
    for u in uis:
        assert 59 <= u <= 0xC7, 'ui id %d: 59-199 (positional database ids)' % u
    return cap, kinds


def mgr_layout(cap):
    """the relocated per-kind block: the same arrays in the same order, cap entries each, from 0x25B0"""
    out, at = {}, MGR_SIZE
    for st, es, name in MGR_ARRAYS:
        out[name] = (st, at)
        at = (at + cap * es + 3) & ~3
    return out, at


def rescan_ram(rpx):
    import kind_ram_scan as K
    img = K.Image(rpx)
    sc = K.Scanner(img)
    sc.run(False)
    sites, keep = K.plan_sites(sc)
    out = {'about': 'tools/kind_ram_scan.py plan_sites(): FighterParamManager per-kind accesses with a '
                    'variable kind (address, original word, array, instruction); kind_expand.py moves '
                    'their immediates to the relocated arrays',
           'kept': dict(keep),
           'sites': [['0x%08X' % a, '0x%08X' % img.w(a), arr, ins] for a, ins, arr in sorted(sites)]}
    with open(RAM_CACHE, 'w') as f:      # one site a line
        f.write('{"about": %s,\n "kept": %s,\n "sites": [\n' % (json.dumps(out['about']), json.dumps(out['kept'])))
        f.write(',\n'.join('  ' + json.dumps(x) for x in out['sites']))
        f.write('\n ]}\n')
    print('%d sites -> %s' % (len(sites), RAM_CACHE), file=sys.stderr)


class Build:
    """the patch: in-place words (checked against their expected originals), relocations to move,
    and the cave"""

    def __init__(self, img):
        self.img = img
        self.words = {}          # address -> word (in place and cave)
        self.what = {}           # address -> what it is (asm text / 'data' / ('copy', from, change))
        self.inplace = []        # in-place addresses
        self.pc = CAVE

    # --- in place
    def put(self, addr, word, what, orig=None):
        assert addr not in self.words, 'patched twice: 0x%08X' % addr
        if orig is not None:
            want = one(addr, orig) if isinstance(orig, str) else orig
            got = self.img.w(addr)
            assert got == want, '0x%08X is 0x%08X, expected 0x%08X (%s): not the base this was made for' % (
                addr, got, want, orig)
        self.words[addr] = word & 0xFFFFFFFF
        self.what[addr] = what
        if addr < CAVE:
            self.inplace.append(addr)

    def asm(self, addr, text, orig=None):
        self.put(addr, one(addr, text), text, orig)

    # --- cave
    def alloc(self, n, align=4):
        self.pc = (self.pc + align - 1) & ~(align - 1)
        a = self.pc
        self.pc += n
        assert self.pc <= LIMIT, 'cave full'
        return a

    def data(self, addr, blob, what='data'):
        blob = bytes(blob) + b'\0' * (-len(blob) % 4)
        for i in range(0, len(blob), 4):
            self.put(addr + i, struct.unpack('>I', blob[i:i + 4])[0], what)

    def code(self, addr, text):
        a = Asm(addr)
        a.asm(text)
        for i, (line, w) in enumerate(zip(a.items, a.words())):
            self.put(addr + 4 * i, w, resolved(a, line))
        return a

    def reloc_args(self):
        rel = self.img.relocs()
        return sorted(a for a in self.inplace if a in rel)


def resolved(a, line):
    """an assembled line with its label operand as an address (it then assembles on its own)"""
    op, _, rest = line.partition(' ')
    if op.startswith('b') and rest.strip() in a.labels:
        return '%s 0x%08X' % (op, a.labels[rest.strip()])
    return line


def kind_index(names, base):
    if isinstance(base, int) or (isinstance(base, str) and base[:1].isdigit()):
        k = num(base)
    else:
        k = names.index(base)
    assert 0 <= k < OLD_N, 'base must be a game kind: %r' % base
    return k


def switch_targets(img, name):
    """the game's 65 case targets and the default of a switch (checked shape)"""
    cmp_, reg, shape, table = SWITCHES[name]
    w = img.w(cmp_)
    assert w == one(cmp_, 'cmplwi r%d, 0x40' % reg), name
    bgt = cmp_ + (8 if shape == 'r0li' else 4)
    default = branch_target(bgt, img.w(bgt))
    targets = []
    for k in range(OLD_N):
        e = table + 4 * k
        assert img.w(e) >> 26 == 18 and not img.w(e) & 3, '%s table entry %d is not a b' % (name, k)
        targets.append(branch_target(e, img.w(e)))
    return targets, default


def copy_load_case(img, src, bkind, kind, at, lay):
    """the base's vl load case (src) for `kind`: loads the base first, then the base's parser storing into
    the kind's equipment-object field and the new vl / vl50 arrays. Returns (words, notes)."""
    eq_b, eq_k = EQ_ARRAY + 4 * bkind, EQ_ARRAY + 4 * kind
    vl_new, vl50_new = lay['vl'][1], lay['vl50'][1]
    out, notes = [], []
    pre = Asm(at)
    pre.asm('mr r3, r29\nli r4, %d\nbl 0x%08X' % (bkind, VL_LOAD))
    for line, w in zip(pre.items, pre.words()):
        out.append(w)
        notes.append(line)
    n = {'eq': 0, 'vl': 0, 'vladdi': 0, 'vl50': 0, 'bl': 0}
    a = src
    while True:
        w = img.w(a)
        op, ra, d = w >> 26, (w >> 16) & 31, sx16(w)
        pc = at + 4 * len(out)
        change = 'same'
        if op == 18:
            t = branch_target(a, w)
            if w & 1:
                w = b_word(pc, t, True)
                n['bl'] += 1
                change = 'branch'
            else:
                assert t == VL_TAIL, 'load case 0x%08X: b to 0x%08X' % (a, t)
                out.append(b_word(pc, VL_TAIL))
                notes.append(('copy', a, 'branch'))
                break
        elif op in (16, 19):
            raise AssertionError('load case 0x%08X: unexpected branch' % a)
        elif op in (32, 36) and d == eq_b:
            w = (w & 0xFFFF0000) | eq_k
            n['eq'] += 1
            change = 'eq'
        elif op == 36 and ra == 29 and d == 0x111C + 4 * bkind:
            w = (w & 0xFFFF0000) | (vl_new + 4 * kind)
            n['vl'] += 1
            change = 'vl'
        elif op == 14 and ra == 29 and d == 0x111C:
            w = (w & 0xFFFF0000) | vl_new
            n['vladdi'] += 1
            change = 'vladdi'
        elif op == 36 and d == 0x1734:
            w = (w & 0xFFFF0000) | vl50_new
            n['vl50'] += 1
            change = 'vl50'
        out.append(w)
        notes.append(('copy', a, change))
        a += 4
        if a == VL_TAIL:                      # the last case falls through into the tail
            out.append(b_word(at + 4 * len(out), VL_TAIL))
            notes.append(('copy', a - 4, 'fallthrough'))
            break
        assert len(out) < 64, 'load case 0x%08X too long' % src
    assert n == {'eq': 3, 'vl': 1, 'vladdi': 1, 'vl50': 1, 'bl': 6}, 'load case 0x%08X: %r' % (src, n)
    return out, notes


def copy_unload_case(img, src, bkind, kind, at):
    """the base's vl unload case for `kind`'s equipment-object field, then the base's unload"""
    eq_b, eq_k = EQ_ARRAY + 4 * bkind, EQ_ARRAY + 4 * kind
    body = []
    a = src
    while True:
        w = img.w(a)
        if w >> 26 == 18 and not w & 1:
            assert branch_target(a, w) == VL_UNLOAD_TAIL, 'unload case 0x%08X' % a
            break
        body.append((a, w))
        a += 4
        if a == VL_UNLOAD_TAIL:
            break
        assert len(body) < 32, 'unload case 0x%08X too long' % src
    rel = at + 4 * len(body)             # the release of the base and the common tail
    out, notes = [], []
    n = {'eq': 0, 'bl': 0, 'bc': 0}
    for a, w in body:
        op, d = w >> 26, sx16(w)
        pc = at + 4 * len(out)
        change = 'same'
        if op == 18:
            assert w & 1
            w = b_word(pc, branch_target(a, w), True)
            n['bl'] += 1
            change = 'branch'
        elif op == 16:
            assert branch_target(a, w) == VL_UNLOAD_TAIL
            w = bc_word(pc, rel, w)
            n['bc'] += 1
            change = 'branch'
        elif op == 19:
            raise AssertionError('unload case 0x%08X: unexpected branch' % a)
        elif op in (32, 36) and d == eq_b:
            w = (w & 0xFFFF0000) | eq_k
            n['eq'] += 1
            change = 'eq'
        out.append(w)
        notes.append(('copy', a, change))
    assert n == {'eq': 3, 'bl': 2, 'bc': 1}, 'unload case 0x%08X: %r' % (src, n)
    tail = Asm(rel)
    tail.asm('mr r3, r30\nli r4, %d\nbl 0x%08X\nb 0x%08X' % (bkind, VL_UNLOAD, VL_UNLOAD_TAIL))
    for line, w in zip(tail.items, tail.words()):
        out.append(w)
        notes.append(line)
    return out, notes


def build(spec_path=SPEC, rpx=RPX):
    cap, kinds = load_spec(spec_path)
    img = Image(rpx)
    B = Build(img)
    assert img.text_end() <= CAVE, 'the base already uses the code space at 0x%08X' % CAVE
    names = [img.cstr(img.w(TABLES['lower'][0] + 4 * k)) for k in range(OLD_N)]
    count = kinds[-1]['kind'] + 1
    for r in kinds:
        r['bkind'] = kind_index(names, r['base'])
        r['dkind'] = kind_index(names, r['desc_from'])
        assert r['name'] not in names and r['vl'] not in [img.cstr(img.w(TABLES['vl'][0] + 4 * k))
                                                          for k in range(OLD_N)], 'name %s is taken' % r['name']
    info = {'capacity': cap, 'count': count, 'kinds': kinds, 'names': names}

    # ---- 1. FighterParamManager: relocated per-kind arrays + mirror hooks
    lay, end = mgr_layout(cap)
    info['mgr_layout'], info['mgr_size'] = lay, end
    for a in MGR_ALLOC:
        B.asm(a, 'li r3, %d' % end, 'li r3, 0x%X' % MGR_SIZE)
    for a, t in MGR_LOOPS:
        B.asm(a, t % cap, t % OLD_N)
    ram = json.load(open(RAM_CACHE))
    for a, w0, arr, ins in ram['sites']:
        a, w0 = int(a, 16), int(w0, 16)
        if a == VL_UNLOAD_STORE:          # hook B replaces it
            continue
        st, nst = lay[arr]
        v = sx16(w0) + nst - st
        assert -0x8000 <= v < 0x8000
        B.put(a, (w0 & 0xFFFF0000) | (v & 0xFFFF), ('ram', arr, ins), w0)
    info['ram_sites'] = len(ram['sites'])

    # ---- 2. equipment-ability object grown in place
    for a, t in EQ_ALLOC:
        B.asm(a, t % (EQ_ARRAY + 4 * cap), t % 0x424)

    # ---- 3. AI amiibo-learning increments: kinds >= 0x41 skip them (rewritten in place)
    ai = Asm(AI_GUARD)
    ai.asm('''
        beq g280                    # (was beq 0x02751B28)
        cmplwi r10, 0x41            # rec+0x384 [kind] += 1
        bge 0x02751B3C
        slwi r0, r10, 2
        addi r5, r8, 0x384
        b inc
g280:   cmplwi r10, 0x41            # rec+0x280 [kind] += 1
        bge 0x02751B3C
        slwi r0, r10, 2
        addi r5, r8, 0x280
inc:    lwzx r4, r5, r0
        addi r4, r4, 1
        stwx r4, r5, r0
        b 0x02751B3C                # lwz r6, 0x1C(r30); the shared continuation
        nop
    ''')
    ai_orig = Asm(AI_GUARD)
    ai_orig.asm('''
        beq 0x02751B28
        slwi r0, r10, 2
        addi r5, r8, 0x384
        lwzx r4, r5, r0
        addi r4, r4, 1
        stwx r4, r5, r0
        lwz r6, 0x1C(r30)
        cmplwi r6, 0x23B
        blt 0x02752098
        b 0x02751B48
        slwi r0, r10, 2
        addi r5, r8, 0x280
        lwzx r4, r5, r0
        addi r4, r4, 1
        stwx r4, r5, r0
        lwz r6, 0x1C(r30)
    ''')
    ow = ai_orig.words()
    assert ai.pc == AI_GUARD + 0x3C and len(ow) == 16
    for i, (line, w) in enumerate(zip(ai.items, ai.words())):
        B.put(AI_GUARD + 4 * i, w, resolved(ai, line), ow[i])
    assert img.w(AI_GUARD + 0x3C) == ow[15]   # the continuation stays

    # ---- 5. tables (data in the cave)
    strings = {}
    sblob = bytearray()

    def string(s):
        if s not in strings:
            strings[s] = len(sblob)
            sblob.extend(s.encode('ascii') + b'\0')
        return s
    string('')
    for r in kinds:
        for s in (r['name'], r['cap'], r['vl'], r['ui_name']):
            string(s)
    sblob.extend(b'\0' * (-len(sblob) % 4))
    s_at = B.alloc(len(sblob))
    B.data(s_at, sblob, 'strings')
    sptr = {s: s_at + o for s, o in strings.items()}
    info['strings'] = sptr
    by_kind = {r['kind']: r for r in kinds}
    tables = {}
    for name, (addr, es, readers) in TABLES.items():
        size = cap * es
        at = B.alloc(size + (-size % 4), 4)
        tables[name] = at
        blob = bytearray()
        for k in range(cap):
            if k < OLD_N:
                src = k
            elif k in by_kind:
                src = by_kind[k]['bkind']
            else:
                src = None
            if name in NAME_TABLES:
                if k < OLD_N:
                    v = img.w(addr + 4 * k)
                elif k in by_kind:
                    v = sptr[{'lower': by_kind[k]['name'], 'cap': by_kind[k]['cap'], 'vl': by_kind[k]['vl']}[name]]
                else:
                    v = sptr['']
                blob += struct.pack('>I', v)
            else:
                v = 0 if src is None else {1: img.b, 2: img.h, 4: img.w}[es](addr + es * src)
                blob += v.to_bytes(es, 'big')
        B.data(at, blob, 'table ' + name)
        for site, orig, new in readers:
            B.asm(site, new.format(ha='0x%X' % ha(at), lo='%d' % slo(at)), orig)
    for a, t in SIZE_GETTERS:
        B.asm(a, t % (cap - 1), t % 0x40)
    info['tables'] = tables
    # character id -> UI name
    uis = [r for r in kinds if r['ui_id'] is not None]
    rows = [(img.w(CHR_TABLE + 8 * i), img.w(CHR_TABLE + 8 * i + 4)) for i in range(CHR_COUNT)]
    assert rows[0][0] == 0xFFFFFFFF and rows[1] == (0, rows[1][1]), 'unexpected character-name table'
    used = {i for i, _ in rows}
    rows[0] = (0xFFFFFFFF, sptr[''])       # its name is set at run time (0x0293E0B8) in the old table only
    for r in uis:
        assert r['ui_id'] not in used, 'ui id %d is the game\'s' % r['ui_id']
        rows.append((r['ui_id'], sptr[r['ui_name']]))
    chr_at = B.alloc(8 * len(rows))
    B.data(chr_at, b''.join(struct.pack('>II', i, p) for i, p in rows), 'table chr')
    for site, orig, new in CHR_READER:
        B.asm(site, new.format(ha='0x%X' % ha(chr_at), lo='%d' % slo(chr_at)), orig)
    B.asm(CHR_COUNT_SITE, 'li r4, %d' % len(rows), 'li r4, 0x%X' % CHR_COUNT)
    n_sel = RANDOM_SELECT_COUNT + len(uis)
    assert n_sel <= 96, 'the random-select set holds 96 database entries'
    B.asm(RANDOM_SELECT, 'li r23, %d' % n_sel, 'li r23, 0x%X' % RANDOM_SELECT_COUNT)
    info['chr_table'], info['chr_count'] = chr_at, len(rows)

    # ---- 6. immediates
    for a, orig, new, which in IMMEDIATES:
        v = {'count': count, 'cap': cap, 'cap-1': cap - 1}[which]
        B.asm(a, new % v, orig)

    # ---- 7. per kind: descriptor, motion info, main motion table
    sw = {name: switch_targets(img, name) for name in SWITCHES}
    for r in kinds:
        dsrc = sw['descriptor'][0][r['dkind']]
        # case: bl getter; getter: lis r3 / addi r3 / blr
        g = branch_target(dsrc, img.w(dsrc))
        assert img.w(dsrc) & 1 and img.w(g + 8) == 0x4E800020
        dbase = ((img.w(g) & 0xFFFF) << 16) + sx16(img.w(g + 4))
        assert img.w(dbase) == r['dkind'], 'descriptor of 0x%X' % r['dkind']
        minfo = img.w(dbase + 4)
        main, mcount = img.w(minfo), img.w(minfo + 4)
        d_at = B.alloc(DESC_SIZE, 8)
        m_at = B.alloc(MINFO_SIZE, 8)
        t_at = B.alloc(8 * mcount, 8)
        desc = bytearray(img.blob(dbase, DESC_SIZE))
        struct.pack_into('>III', desc, 0, r['kind'], m_at, img.w(dbase + 8))
        struct.pack_into('>I', desc, 0x1C, 0)
        mi = bytearray(img.blob(minfo, MINFO_SIZE))
        struct.pack_into('>I', mi, 0, t_at)
        B.data(d_at, desc, 'descriptor 0x%X' % r['kind'])
        B.data(m_at, mi, 'motion info 0x%X' % r['kind'])
        B.data(t_at, img.blob(main, 8 * mcount), 'motion table 0x%X' % r['kind'])
        r.update(desc=d_at, minfo=m_at, mtable=t_at, mcount=mcount, base_desc=dbase)

    # ---- code: descriptor cases, vl load / unload cases, mirror hooks
    for r in kinds:
        at = B.alloc(6 * 4)
        B.code(at, '''
            lis r3, 0x%X
            addi r3, r3, %d
            lwz r0, 0xC(r1)                 # the getter's epilogue (as the game's cases)
            mtlr r0
            addi r1, r1, 8
            blr''' % (ha(r['desc']), slo(r['desc'])))
        r['desc_case'] = at
        src = sw['vl_load'][0][r['bkind']]
        size = len(copy_load_case(img, src, r['bkind'], r['kind'], CAVE, lay)[0])
        at = B.alloc(4 * size)
        words, notes = copy_load_case(img, src, r['bkind'], r['kind'], at, lay)
        for i, (w, nt) in enumerate(zip(words, notes)):
            B.put(at + 4 * i, w, nt)
        r['load_case'] = at
        src = sw['vl_unload'][0][r['bkind']]
        size = len(copy_unload_case(img, src, r['bkind'], r['kind'], CAVE)[0])
        at = B.alloc(4 * size)
        words, notes = copy_unload_case(img, src, r['bkind'], r['kind'], at)
        for i, (w, nt) in enumerate(zip(words, notes)):
            B.put(at + 4 * i, w, nt)
        r['unload_case'] = at
    # hook A: the vl load's common tail (lwz r7, 0xC(r10)): mirror old vl[k] -> new vl[k], k < 0x41
    hook_a = B.alloc(7 * 4)
    B.code(hook_a, '''
        cmplwi r31, 0x41
        bge ha_done
        add r11, r29, r27               # mgr + 4 * kind (r7 / r11 are written next anyway)
        lwz r7, 0x111C(r11)
        stw r7, %d(r11)
ha_done:
        lwz r7, 0xC(r10)
        b 0x%08X''' % (lay['vl'][1], VL_TAIL + 4))
    B.put(VL_TAIL, b_word(VL_TAIL, hook_a), 'b 0x%08X' % hook_a, 'lwz r7, 0xC(r10)')
    # hook B: the unload's store (stw r29, 0x111C(r12), r29 = 0, r12 = mgr + 4 * kind): both arrays
    hook_b = B.alloc(5 * 4)
    B.code(hook_b, '''
        stw r29, %d(r12)
        cmplwi r31, 0x41
        bge hb_done
        stw r29, 0x111C(r12)
hb_done:
        b 0x%08X''' % (lay['vl'][1], VL_UNLOAD_STORE + 4))
    B.put(VL_UNLOAD_STORE, b_word(VL_UNLOAD_STORE, hook_b), 'b 0x%08X' % hook_b, 'stw r29, 0x111C(r12)')
    info['hooks'] = (hook_a, hook_b)

    # ---- 4. the six switches: address tables in the cave
    info['switch_tables'] = {}
    for name, (cmp_, reg, shape, table) in SWITCHES.items():
        targets, default = sw[name]
        entries = list(targets)
        for k in range(OLD_N, cap):
            r = by_kind.get(k)
            if r is None:
                entries.append(default)
            elif name == 'specializer':
                entries.append(targets[r['bkind']])
            elif name == 'descriptor':
                entries.append(r['desc_case'])
            elif name == 'vl_load':
                entries.append(r['load_case'])
            elif name == 'vl_unload':
                entries.append(r['unload_case'])
            else:
                entries.append(targets[r['bkind']] if r['ai'] == 'base' else default)
        at = B.alloc(4 * cap)
        B.data(at, b''.join(struct.pack('>I', e) for e in entries), 'switch ' + name)
        info['switch_tables'][name] = (at, default)
        B.asm(cmp_, 'cmplwi r%d, %d' % (reg, cap - 1), 'cmplwi r%d, 0x40' % reg)
        if shape in ('r0', 'r0li'):
            o = cmp_ + (4 if shape == 'r0' else 8)      # the bgt
            hi, tbl_lo, add = o + 4, o + 12, o + 16
            B.asm(hi, 'lis r0, 0x%X' % ha(at), 'lis r0, 0x%X' % ha(table))
            B.asm(tbl_lo, 'addic r0, r0, %d' % slo(at), 'addic r0, r0, %d' % slo(table))
            B.asm(add, 'lwzx r0, r%d, r0' % reg, 'add r0, r%d, r0' % reg)
            assert img.w(o + 8) == one(o + 8, 'slwi r%d, r%d, 2' % (reg, reg))
            assert img.w(o + 20) == one(o + 20, 'mtctr r0') and img.w(o + 24) == 0x4E800420
        else:                                           # ai_a: addis r12, r11, hi / addi r12, r12, lo
            o = cmp_ + 4
            assert img.w(o + 4) == one(o + 4, 'slwi r11, r11, 2')
            B.asm(o + 8, 'addis r12, r11, 0x%X' % ha(at), 'addis r12, r11, 0x%X' % ha(table))
            B.asm(o + 12, 'lwz r12, %d(r12)' % slo(at), 'addi r12, r12, %d' % slo(table))
            assert img.w(o + 16) == one(o + 16, 'mtctr r12') and img.w(o + 20) == 0x4E800420
    info['cave_end'] = B.pc
    return B, info


def args(B):
    out = ['grow:0x%08X' % ((B.pc + 0xFFF) & ~0xFFF)]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B.words.items())]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, RELOC_DUMMY) for a in B.reloc_args()]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--kinds', default=SPEC)
    ap.add_argument('--rpx', default=RPX)
    ap.add_argument('--info', action='store_true', help='print the layout (stderr)')
    ap.add_argument('--rescan-ram', action='store_true', help='refresh %s from the RPX' % os.path.basename(RAM_CACHE))
    a = ap.parse_args()
    if a.rescan_ram:
        rescan_ram(a.rpx)
        return
    B, info = build(a.kinds, a.rpx)
    print(' '.join(args(B)))
    err = sys.stderr
    print('kind expansion: capacity 0x%X, %d new kind(s); %d words in place, %d relocations moved, '
          'cave 0x%08X-0x%08X' % (info['capacity'], len(info['kinds']), len(B.inplace), len(B.reloc_args()),
                                  CAVE, info['cave_end']), file=err)
    for r in info['kinds']:
        if r['bkind'] in TAIL_EXTRA_KINDS:
            print('  WARNING: base %s: its vl tail sets x1324 / x152C for its own kind only; kind 0x%X gets 0 '
                  'there (untested)' % (info['names'][r['bkind']], r['kind']), file=err)
        print('  0x%X %s / %s (base %s): descriptor 0x%08X (motion table 0x%08X, %d motions), vl load case '
              '0x%08X, unload case 0x%08X, ui id %s' % (r['kind'], r['name'], r['cap'], info['names'][r['bkind']],
                                                         r['desc'], r['mtable'], r['mcount'], r['load_case'],
                                                         r['unload_case'], r['ui_id']), file=err)
    if a.info:
        for k, v in sorted(info['tables'].items()):
            print('  table %-6s 0x%08X' % (k, v), file=err)
        for k, (t, d) in info['switch_tables'].items():
            print('  switch %-11s table 0x%08X default 0x%08X' % (k, t, d), file=err)
        print('  character names 0x%08X (%d)' % (info['chr_table'], info['chr_count']), file=err)
        print('  hooks 0x%08X 0x%08X' % info['hooks'], file=err)
        for nm, (o, n) in info['mgr_layout'].items():
            print('  mgr %-6s 0x%04X -> 0x%04X' % (nm, o, n), file=err)
        print('  mgr size 0x%X' % info['mgr_size'], file=err)


if __name__ == '__main__':
    main()
