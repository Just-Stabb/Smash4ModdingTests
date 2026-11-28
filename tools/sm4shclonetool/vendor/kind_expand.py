"""New fighter kinds 0x41 and up: the per-kind tables (names, special-block sizes, sound class, character names),
the six 65-case kind switches, the parameter manager's per-kind arrays (moved to a larger allocation), the
kind-count bounds, the save's per-character records, the sound files' name tables, and per new kind its
descriptor, motion table and vl load / unload cases, all copied from its base kind. Reads a kinds spec (JSON)
and a vanilla RPX; every hooked word is checked against the game's original.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import argparse
import json
import os
import struct
import sys
import zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch
from ppcasm import Asm, ha
RPX = None
SPEC = None
RAM_CACHE = os.path.join(HERE, 'kind_expand_ram.json')
CAVE = 79167488
LIMIT = 79331328
RELOC_DUMMY = 79151096
OLD_N = 65
DEFAULT_CAPACITY = 96
MGR_SIZE = 9648
MGR_ALLOC = (48555652, 48912480)
MGR_LOOPS = ((48913564, 'li r0, %d'), (48913596, 'li r11, %d'), (48917388, 'li r29, %d'))
MGR_ARRAYS = [(4380, 4, 'vl'), (4640, 4, 'refcnt'), (4900, 4, 'x1324'), (5160, 4, 'x1428'), (5420, 4, 'x152C'), (5680, 4, 'fpidx'), (5940, 4, 'vl50'), (6200, 36, 'att'), (8540, 8, 'attp')]
EQ_ALLOC = ((48912740, 'li r3, %d'), (48912760, 'li r4, %d'))
EQ_ARRAY = 800
VL_LOAD, VL_TAIL = (48917444, 48926032)
VL_UNLOAD, VL_UNLOAD_TAIL, VL_UNLOAD_STORE = (48913764, 48917236, 48917240)
AI_GUARD = 41229056
SWITCHES = {'specializer': (48654832, 4, 'r0', 48654864), 'descriptor': (48509256, 4, 'r0', 48509288), 'vl_load': (48917652, 12, 'r0', 48917684), 'vl_unload': (48913824, 6, 'r0li', 48913860), 'ai_a': (48243800, 11, 'r12', 48243828), 'ai_b': (41268300, 5, 'r0', 41268332)}
TABLES = {'lower': (271578244, 4, [(41278244, 'lis r0, 0x1030', 'lis r0, {ha}'), (41278252, 'addic r0, r0, -0xB7C', 'addic r0, r0, {lo}')]), 'cap': (271578504, 4, [(41278264, 'lis r0, 0x1030', 'lis r0, {ha}'), (41278272, 'addic r0, r0, -0xA78', 'addic r0, r0, {lo}')]), 'vl': (271924660, 4, [(48917568, 'addis r10, r27, 0x1035', 'addis r10, r27, {ha}'), (48917580, 'lwz r6, 0x3DB4(r10)', 'lwz r6, {lo}(r10)')]), 'sp16': (269678136, 2, [(48926952, 'lis r0, 0x1013', 'lis r0, {ha}'), (48926960, 'addic r0, r0, -0x9C8', 'addic r0, r0, {lo}')]), 'spN': (269678268, 1, [(48926988, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'), (48926992, 'lbz r3, -0x944(r12)', 'lbz r3, {lo}(r12)')]), 'spS': (269678336, 1, [(48927016, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'), (48927020, 'lbz r3, -0x900(r12)', 'lbz r3, {lo}(r12)')]), 'spHi': (269678404, 1, [(48927044, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'), (48927048, 'lbz r3, -0x8BC(r12)', 'lbz r3, {lo}(r12)')]), 'spLw': (269678472, 1, [(48927072, 'addis r12, r4, 0x1013', 'addis r12, r4, {ha}'), (48927076, 'lbz r3, -0x878(r12)', 'lbz r3, {lo}(r12)')]), 'snd': (269296088, 4, [(44797104, 'lis r0, 0x100D', 'lis r0, {ha}'), (44797112, 'addic r0, r0, 0x21D8', 'addic r0, r0, {lo}')])}
NAME_TABLES = ('lower', 'cap', 'vl')
SIZE_GETTERS = ((48926944, 'cmplwi r4, %d'), (48926980, 'cmplwi r4, %d'), (48927008, 'cmplwi r4, %d'), (48927036, 'cmplwi r4, %d'), (48927064, 'cmplwi r4, %d'))
CHR_TABLE, CHR_COUNT = (271826536, 83)
CHR_READER = ((43244752, 'lis r3, 0x1034', 'lis r3, {ha}'), (43244760, 'addi r3, r3, -0x4198', 'addi r3, r3, {lo}'))
CHR_COUNT_SITE = 43244756
SAVE_RECORD_GET = 44383316
SAVE_RECORD_HOOK = 44383328
SAVE_RECORD_MAKE = 44383356
SAVE_RECORD_NONE = 44383380
SAVE_RECORDS, SAVE_RECORD_SIZE, FIRST_UI = (82, 80, 59)
RANDOM_SELECT, RANDOM_SELECT_COUNT = (50312772, 81)
IMMEDIATES = [(35574176, 'li r4, 0x41', 'li r4, %d', 'count'), (35574192, 'cmpwi r27, 0x41', 'cmpwi r27, %d', 'count'), (35574240, 'cmplwi r28, 0x41', 'cmplwi r28, %d', 'count'), (35548720, 'li r4, 0x41', 'li r4, %d', 'count'), (50986600, 'cmpwi r4, 0x41', 'cmpwi r4, %d', 'cap-1'), (44536152, 'cmplwi r29, 0x41', 'cmplwi r29, %d', 'cap'), (41269952, 'cmpwi r4, 0x41', 'cmpwi r4, %d', 'cap'), (48111068, 'cmplwi r6, 0x41', 'cmplwi r6, %d', 'cap'), (44842876, 'cmplwi r0, 0x41', 'cmplwi r0, %d', 'cap'), (41293096, 'cmplwi r5, 0x41', 'cmplwi r5, %d', 'cap')]
DESC_SIZE, MINFO_SIZE = (56, 24)
SOUND_NAME_TABLES = {'fbb': (271846332, (44448288, 'lis r28, 0x1034'), (44448296, 'addi r28, r28, 0xBBC'), (44448508, 'cmplwi r25, %d'), 58), 'csb': (271847308, (44803096, 'lis r23, 0x1034'), (44803104, 'addi r23, r23, 0xF8C'), (44803272, 'cmplwi r28, %d'), 62)}

def sound_record(table, kind):
    return kind if table == 'fbb' else SOUND_NAME_TABLES['csb'][4] + kind - OLD_N
TAIL_EXTRA_KINDS = (5, 6, 8, 23, 24, 25, 28, 32, 33, 35, 38, 53)
TAIL_BLOCKS = (48926264, 48926688)

def tail_block(img, bkind):

    def fields(w):
        return (w >> 26, w >> 21 & 31, w >> 16 & 31, sx16(w))
    for a in range(TAIL_BLOCKS[0], TAIL_BLOCKS[1], 4):
        op, rd, ra, d = fields(img.w(a))
        if op == 32 and ra == 10 and (d == EQ_ARRAY + 4 * bkind) and (fields(img.w(a - 4))[1:] == (10, 29, 9588)):
            s_reg = rd
            o1, rc, rs1, count = fields(img.w(a + 4))
            assert o1 == 32 and rs1 == s_reg, 'tail block 0x%08X: count' % a
            o2, rv, rs2, data = fields(img.w(a + 16))
            assert o2 == 32 and rs2 == s_reg, 'tail block 0x%08X: data' % a
            o3, rv2, r29, dest = fields(img.w(a + 24))
            assert o3 == 36 and rv2 == rv and (r29 == 29), 'tail block 0x%08X: store' % a
            for name, old in (('x1324', 4900), ('x152C', 5420)):
                if dest == old + 4 * bkind:
                    return (count, data, name)
            raise AssertionError('tail block 0x%08X: store to 0x%X' % (a, dest))
    raise AssertionError('no vl tail block for kind 0x%X' % bkind)
KIND_NAMES = None

def sx16(v):
    v &= 65535
    return v - 65536 if v & 32768 else v

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
        off = w & 67108860
        off -= 67108864 if off & 33554432 else 0
        return (off if w & 2 else addr + off) & 4294967295
    if op == 16:
        return (sx16(w & 65532) if w & 2 else addr + sx16(w & 65532)) & 4294967295
    raise ValueError('not a branch: %08X at %08X' % (w, addr))

def b_word(src, dst, link=False):
    off = dst - src
    assert -33554432 <= off < 33554432 and off % 4 == 0, 'branch out of reach: %08X -> %08X' % (src, dst)
    return 18 << 26 | off & 67108860 | int(link)

def bc_word(src, dst, w):
    off = dst - src
    assert -32768 <= off < 32768, 'conditional branch out of reach'
    return w & 4294901763 | off & 65532

class Image:

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
            if c == b'\x00':
                return out.decode('latin1')
            out += c

    def text_end(self):
        return max((base + len(data) for base, data in self.mem if base < 268435456))

    def relocs(self):
        if self._rel is None:
            self._rel = set()
            for s in self.secs:
                if s[1] == 4:
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
        rec = {'kind': num(r['kind']), 'name': r['name'], 'cap': r.get('cap') or r['name'].capitalize(), 'base': r['base'], 'ai': r.get('ai', 'base'), 'ui_id': num(ui['id']) if ui.get('id') is not None else None}
        rec['ui_name'] = ui.get('name') or rec['cap']
        rec['vl'] = r.get('vl') or 'fighter_param_vl_' + rec['name']
        rec['desc_from'] = (r.get('descriptor') or {}).get('from', r['base'])
        rec['motions'] = {num(i): m for i, m in (r.get('motions') or {}).items()}
        rec['tail_vector'] = bool(r.get('tail_vector'))
        assert rec['kind'] == OLD_N + i, 'kinds must be consecutive from 0x41 (record %d is 0x%X)' % (i, rec['kind'])
        assert rec['ai'] in ('base', 'generic'), rec['ai']
        assert len(rec['vl']) + len('param/fighter/.bin') < 100, 'vl file name too long'
        kinds.append(rec)
    assert kinds, 'no kinds'
    assert kinds[-1]['kind'] < cap, 'capacity 0x%X is too small for kind 0x%X' % (cap, kinds[-1]['kind'])
    assert cap <= 319, 'capacity above 0x13F: the relocated arrays would pass +0x8000'
    uis = [k['ui_id'] for k in kinds if k['ui_id'] is not None]
    assert len(set(uis)) == len(uis), 'duplicate ui ids'
    for u in uis:
        assert 59 <= u <= 199, 'ui id %d: 59-199 (positional database ids)' % u
    return (cap, kinds)

def mgr_layout(cap):
    out, at = ({}, MGR_SIZE)
    for st, es, name in MGR_ARRAYS:
        out[name] = (st, at)
        at = at + cap * es + 3 & ~3
    return (out, at)

class Build:

    def __init__(self, img):
        self.img = img
        self.words = {}
        self.what = {}
        self.inplace = []
        self.pc = CAVE

    def put(self, addr, word, what, orig=None):
        assert addr not in self.words, 'patched twice: 0x%08X' % addr
        if orig is not None:
            want = one(addr, orig) if isinstance(orig, str) else orig
            got = self.img.w(addr)
            assert got == want, '0x%08X is 0x%08X, expected 0x%08X (%s): not the base this was made for' % (addr, got, want, orig)
        self.words[addr] = word & 4294967295
        self.what[addr] = what
        if addr < CAVE:
            self.inplace.append(addr)

    def asm(self, addr, text, orig=None):
        self.put(addr, one(addr, text), text, orig)

    def alloc(self, n, align=4):
        self.pc = self.pc + align - 1 & ~(align - 1)
        a = self.pc
        self.pc += n
        assert self.pc <= LIMIT, 'cave full'
        return a

    def data(self, addr, blob, what='data'):
        blob = bytes(blob) + b'\x00' * (-len(blob) % 4)
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
        return sorted((a for a in self.inplace if a in rel))

def resolved(a, line):
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
    cmp_, reg, shape, table = SWITCHES[name]
    w = img.w(cmp_)
    assert w == one(cmp_, 'cmplwi r%d, 0x40' % reg), name
    bgt = cmp_ + (8 if shape == 'r0li' else 4)
    default = branch_target(bgt, img.w(bgt))
    targets = []
    for k in range(OLD_N):
        e = table + 4 * k
        assert img.w(e) >> 26 == 18 and (not img.w(e) & 3), '%s table entry %d is not a b' % (name, k)
        targets.append(branch_target(e, img.w(e)))
    return (targets, default)

def copy_load_case(img, src, bkind, kind, at, lay):
    eq_b, eq_k = (EQ_ARRAY + 4 * bkind, EQ_ARRAY + 4 * kind)
    vl_new, vl50_new = (lay['vl'][1], lay['vl50'][1])
    out, notes = ([], [])
    pre = Asm(at)
    pre.asm('mr r3, r29\nli r4, %d\nbl 0x%08X' % (bkind, VL_LOAD))
    for line, w in zip(pre.items, pre.words()):
        out.append(w)
        notes.append(line)
    n = {'eq': 0, 'vl': 0, 'vladdi': 0, 'vl50': 0, 'bl': 0}
    a = src
    while True:
        w = img.w(a)
        op, ra, d = (w >> 26, w >> 16 & 31, sx16(w))
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
            w = w & 4294901760 | eq_k
            n['eq'] += 1
            change = 'eq'
        elif op == 36 and ra == 29 and (d == 4380 + 4 * bkind):
            w = w & 4294901760 | vl_new + 4 * kind
            n['vl'] += 1
            change = 'vl'
        elif op == 14 and ra == 29 and (d == 4380):
            w = w & 4294901760 | vl_new
            n['vladdi'] += 1
            change = 'vladdi'
        elif op == 36 and d == 5940:
            w = w & 4294901760 | vl50_new
            n['vl50'] += 1
            change = 'vl50'
        out.append(w)
        notes.append(('copy', a, change))
        a += 4
        if a == VL_TAIL:
            out.append(b_word(at + 4 * len(out), VL_TAIL))
            notes.append(('copy', a - 4, 'fallthrough'))
            break
        assert len(out) < 64, 'load case 0x%08X too long' % src
    assert n == {'eq': 3, 'vl': 1, 'vladdi': 1, 'vl50': 1, 'bl': 6}, 'load case 0x%08X: %r' % (src, n)
    return (out, notes)

def copy_unload_case(img, src, bkind, kind, at):
    eq_b, eq_k = (EQ_ARRAY + 4 * bkind, EQ_ARRAY + 4 * kind)
    body = []
    a = src
    while True:
        w = img.w(a)
        if w >> 26 == 18 and (not w & 1):
            assert branch_target(a, w) == VL_UNLOAD_TAIL, 'unload case 0x%08X' % a
            break
        body.append((a, w))
        a += 4
        if a == VL_UNLOAD_TAIL:
            break
        assert len(body) < 32, 'unload case 0x%08X too long' % src
    rel = at + 4 * len(body)
    out, notes = ([], [])
    n = {'eq': 0, 'bl': 0, 'bc': 0}
    for a, w in body:
        op, d = (w >> 26, sx16(w))
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
            w = w & 4294901760 | eq_k
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
    return (out, notes)

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
        assert r['name'] not in names and r['vl'] not in [img.cstr(img.w(TABLES['vl'][0] + 4 * k)) for k in range(OLD_N)], 'name %s is taken' % r['name']
    info = {'capacity': cap, 'count': count, 'kinds': kinds, 'names': names}
    lay, end = mgr_layout(cap)
    info['mgr_layout'], info['mgr_size'] = (lay, end)
    for a in MGR_ALLOC:
        B.asm(a, 'li r3, %d' % end, 'li r3, 0x%X' % MGR_SIZE)
    for a, t in MGR_LOOPS:
        B.asm(a, t % cap, t % OLD_N)
    ram = json.load(open(RAM_CACHE))
    for a, w0, arr, ins in ram['sites']:
        a, w0 = (int(a, 16), int(w0, 16))
        if a == VL_UNLOAD_STORE:
            continue
        st, nst = lay[arr]
        v = sx16(w0) + nst - st
        assert -32768 <= v < 32768
        B.put(a, w0 & 4294901760 | v & 65535, ('ram', arr, ins), w0)
    info['ram_sites'] = len(ram['sites'])
    for a, t in EQ_ALLOC:
        B.asm(a, t % (EQ_ARRAY + 4 * cap), t % 1060)
    ai = Asm(AI_GUARD)
    ai.asm('\n        beq g280                    # (was beq 0x02751B28)\n        cmplwi r10, 0x41            # rec+0x384 [kind] += 1\n        bge 0x02751B3C\n        slwi r0, r10, 2\n        addi r5, r8, 0x384\n        b inc\ng280:   cmplwi r10, 0x41            # rec+0x280 [kind] += 1\n        bge 0x02751B3C\n        slwi r0, r10, 2\n        addi r5, r8, 0x280\ninc:    lwzx r4, r5, r0\n        addi r4, r4, 1\n        stwx r4, r5, r0\n        b 0x02751B3C                # lwz r6, 0x1C(r30); the shared continuation\n        nop\n    ')
    ai_orig = Asm(AI_GUARD)
    ai_orig.asm('\n        beq 0x02751B28\n        slwi r0, r10, 2\n        addi r5, r8, 0x384\n        lwzx r4, r5, r0\n        addi r4, r4, 1\n        stwx r4, r5, r0\n        lwz r6, 0x1C(r30)\n        cmplwi r6, 0x23B\n        blt 0x02752098\n        b 0x02751B48\n        slwi r0, r10, 2\n        addi r5, r8, 0x280\n        lwzx r4, r5, r0\n        addi r4, r4, 1\n        stwx r4, r5, r0\n        lwz r6, 0x1C(r30)\n    ')
    ow = ai_orig.words()
    assert ai.pc == AI_GUARD + 60 and len(ow) == 16
    for i, (line, w) in enumerate(zip(ai.items, ai.words())):
        B.put(AI_GUARD + 4 * i, w, resolved(ai, line), ow[i])
    assert img.w(AI_GUARD + 60) == ow[15]
    strings = {}
    sblob = bytearray()

    def string(s):
        if s not in strings:
            strings[s] = len(sblob)
            sblob.extend(s.encode('ascii') + b'\x00')
        return s
    string('')
    for r in kinds:
        for s in (r['name'], r['cap'], r['vl'], r['ui_name']):
            string(s)
    sblob.extend(b'\x00' * (-len(sblob) % 4))
    s_at = B.alloc(len(sblob))
    B.data(s_at, sblob, 'strings')
    sptr = {s: s_at + o for s, o in strings.items()}
    info['strings'] = sptr
    by_kind = {r['kind']: r for r in kinds}
    tables = {}
    for name, (addr, es, readers) in TABLES.items():
        size = cap * es
        at = B.alloc(size + -size % 4, 4)
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
        B.asm(a, t % (cap - 1), t % 64)
    info['tables'] = tables
    uis = [r for r in kinds if r['ui_id'] is not None]
    rows = [(img.w(CHR_TABLE + 8 * i), img.w(CHR_TABLE + 8 * i + 4)) for i in range(CHR_COUNT)]
    assert rows[0][0] == 4294967295 and rows[1] == (0, rows[1][1]), 'unexpected character-name table'
    used = {i for i, _ in rows}
    rows[0] = (4294967295, sptr[''])
    for r in uis:
        assert r['ui_id'] not in used, "ui id %d is the game's" % r['ui_id']
        rows.append((r['ui_id'], sptr[r['ui_name']]))
    chr_at = B.alloc(8 * len(rows))
    B.data(chr_at, b''.join((struct.pack('>II', i, p) for i, p in rows)), 'table chr')
    for site, orig, new in CHR_READER:
        B.asm(site, new.format(ha='0x%X' % ha(chr_at), lo='%d' % slo(chr_at)), orig)
    B.asm(CHR_COUNT_SITE, 'li r4, %d' % len(rows), 'li r4, 0x%X' % CHR_COUNT)
    n_sel = RANDOM_SELECT_COUNT + len(uis)
    assert n_sel <= 96, 'the random-select set holds 96 database entries'
    B.asm(RANDOM_SELECT, 'li r23, %d' % n_sel, 'li r23, 0x%X' % RANDOM_SELECT_COUNT)
    info['chr_table'], info['chr_count'] = (chr_at, len(rows))
    n_ui = len(uis)
    assert sorted((r['ui_id'] for r in uis)) == list(range(FIRST_UI, FIRST_UI + n_ui)), 'ui ids consecutive from 59'
    if n_ui:
        recs = B.alloc(SAVE_RECORD_SIZE * n_ui, 8)
        B.data(recs, bytes(SAVE_RECORD_SIZE * n_ui), 'data: save records of the new characters (RAM only)')
        hook = B.alloc(28 * 4)
        sr = B.code(hook, "\n        lwz r12, 4(r3)                  # the records' count\n        cmplwi r12, %(old)d\n        bne sr_plain                    # not the 82 character records: as the game\n        cmplwi r4, %(first)d\n        blt sr_plain\n        cmplwi r4, %(end)d\n        bge sr_moved\n        addi r4, r4, -%(first)d         # a new character: its own record\n        mulli r4, r4, %(size)d\n        lis r12, 0x%(rh)X\n        addi r12, r12, %(rl)d\n        add r4, r12, r4\n        b sr_make\nsr_moved:\n        addi r4, r4, -%(n)d             # a vanilla entry moved down by the inserted ones\nsr_plain:                               # the game's own: index < count, else its null-record path\n        cmplw r4, r12\n        bge sr_none\n        mulli r0, r4, %(size)d\n        lwz r12, 0(r3)\n        add r4, r12, r0\nsr_make:\n        addi r3, r1, 0xC\n        lis r12, 0x%(mh)X\n        addi r12, r12, %(ml)d\n        mtctr r12                       # (out of a branch's reach)\n        bctr\nsr_none:\n        lis r12, 0x%(nh)X\n        addi r12, r12, %(nl)d\n        mtctr r12\n        bctr" % dict(old=SAVE_RECORDS, first=FIRST_UI, end=FIRST_UI + n_ui, n=n_ui, size=SAVE_RECORD_SIZE, rh=ha(recs), rl=slo(recs), mh=ha(SAVE_RECORD_MAKE), ml=slo(SAVE_RECORD_MAKE), nh=ha(SAVE_RECORD_NONE), nl=slo(SAVE_RECORD_NONE)))
        assert len(sr.words()) == 28
        for i, (txt, orig) in enumerate([('lis r12, 0x%X' % ha(hook), 'lwz r12, 4(r3)'), ('addi r12, r12, %d' % slo(hook), 'cmplw r4, r12'), ('mtctr r12', None), ('bctr', None)]):
            B.asm(SAVE_RECORD_HOOK + 4 * i, txt, orig)
        assert B.img.w(SAVE_RECORD_MAKE) == b_word(SAVE_RECORD_MAKE, 44380904, True)
        info['save_records'] = (hook, recs, n_ui)
    for a, orig, new, which in IMMEDIATES:
        v = {'count': count, 'cap': cap, 'cap-1': cap - 1}[which]
        B.asm(a, new % v, orig)
    sw = {name: switch_targets(img, name) for name in SWITCHES}
    articles = {}
    if any((r.get('weapons') for r in json.load(open(spec_path))['kinds'])):
        import weapon_expand
        articles = weapon_expand.article_lists(spec_path, rpx)
    info['article_lists'] = articles
    for r in kinds:
        dsrc = sw['descriptor'][0][r['dkind']]
        g = branch_target(dsrc, img.w(dsrc))
        assert img.w(dsrc) & 1 and img.w(g + 8) == 1317011488
        dbase = ((img.w(g) & 65535) << 16) + sx16(img.w(g + 4))
        assert img.w(dbase) == r['dkind'], 'descriptor of 0x%X' % r['dkind']
        minfo = img.w(dbase + 4)
        main, mcount = (img.w(minfo), img.w(minfo + 4))
        d_at = B.alloc(DESC_SIZE, 8)
        m_at = B.alloc(MINFO_SIZE, 8)
        t_at = B.alloc(8 * mcount, 8)
        desc = bytearray(img.blob(dbase, DESC_SIZE))
        struct.pack_into('>III', desc, 0, r['kind'], m_at, articles.get(r['kind'], img.w(dbase + 8)))
        struct.pack_into('>I', desc, 28, 0)
        mi = bytearray(img.blob(minfo, MINFO_SIZE))
        struct.pack_into('>I', mi, 0, t_at)
        B.data(d_at, desc, 'descriptor 0x%X' % r['kind'])
        B.data(m_at, mi, 'motion info 0x%X' % r['kind'])
        tbl = bytearray(img.blob(main, 8 * mcount))
        for i, m in r['motions'].items():
            assert i < mcount, 'motion 0x%X: the base has %d' % (i, mcount)
            if m.get('anim'):
                struct.pack_into('>I', tbl, 8 * i, zlib.crc32(m['anim'].encode(), 4294967295))
            if m.get('flags') is not None:
                struct.pack_into('>I', tbl, 8 * i + 4, num(m['flags']))
        B.data(t_at, bytes(tbl), 'motion table 0x%X' % r['kind'])
        r.update(desc=d_at, minfo=m_at, mtable=t_at, mcount=mcount, base_desc=dbase)
    for r in kinds:
        at = B.alloc(6 * 4)
        B.code(at, "\n            lis r3, 0x%X\n            addi r3, r3, %d\n            lwz r0, 0xC(r1)                 # the getter's epilogue (as the game's cases)\n            mtlr r0\n            addi r1, r1, 8\n            blr" % (ha(r['desc']), slo(r['desc'])))
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
    tv = ''
    for r in kinds:
        if not r.get('tail_vector'):
            continue
        assert r['bkind'] in TAIL_EXTRA_KINDS, '%s: tail_vector on a base without one' % r['name']
        count, data, arr = tail_block(img, r['bkind'])
        k = r['kind']
        tv += "\n        cmplwi r31, 0x%(k)X               # kind 0x%(k)X: its base's %(arr)s vector (count +0x%(c)X, data +0x%(d)X)\n        bne tv_%(k)x\n        lwz r3, 0x2574(r29)\n        lwz r4, 0x%(eq)X(r3)\n        lwz r5, 0x%(c)X(r4)\n        cmpwi r5, 0\n        ble tv_%(k)x\n        lwz r6, 0x%(d)X(r4)\n        stw r6, 0x%(dst)X(r29)\ntv_%(k)x:" % dict(k=k, arr=arr, c=count, d=data, eq=EQ_ARRAY + 4 * k, dst=lay[arr][1] + 4 * k)
        info.setdefault('tail_vectors', []).append((k, arr, count, data))
    hook_a = B.alloc((7 + 9 * len(info.get('tail_vectors', []))) * 4)
    B.code(hook_a, '\n        cmplwi r31, 0x41\n        bge ha_new\n        add r11, r29, r27               # mgr + 4 * kind (r7 / r11 are written next anyway)\n        lwz r7, 0x111C(r11)\n        stw r7, %d(r11)\nha_new:%s\nha_done:\n        lwz r7, 0xC(r10)\n        b 0x%08X' % (lay['vl'][1], tv, VL_TAIL + 4))
    B.put(VL_TAIL, b_word(VL_TAIL, hook_a), 'b 0x%08X' % hook_a, 'lwz r7, 0xC(r10)')
    hook_b = B.alloc(5 * 4)
    B.code(hook_b, '\n        stw r29, %d(r12)\n        cmplwi r31, 0x41\n        bge hb_done\n        stw r29, 0x111C(r12)\nhb_done:\n        b 0x%08X' % (lay['vl'][1], VL_UNLOAD_STORE + 4))
    B.put(VL_UNLOAD_STORE, b_word(VL_UNLOAD_STORE, hook_b), 'b 0x%08X' % hook_b, 'stw r29, 0x111C(r12)')
    info['hooks'] = (hook_a, hook_b)
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
        B.data(at, b''.join((struct.pack('>I', e) for e in entries)), 'switch ' + name)
        info['switch_tables'][name] = (at, default)
        B.asm(cmp_, 'cmplwi r%d, %d' % (reg, cap - 1), 'cmplwi r%d, 0x40' % reg)
        if shape in ('r0', 'r0li'):
            o = cmp_ + (4 if shape == 'r0' else 8)
            hi, tbl_lo, add = (o + 4, o + 12, o + 16)
            B.asm(hi, 'lis r0, 0x%X' % ha(at), 'lis r0, 0x%X' % ha(table))
            B.asm(tbl_lo, 'addic r0, r0, %d' % slo(at), 'addic r0, r0, %d' % slo(table))
            B.asm(add, 'lwzx r0, r%d, r0' % reg, 'add r0, r%d, r0' % reg)
            assert img.w(o + 8) == one(o + 8, 'slwi r%d, r%d, 2' % (reg, reg))
            assert img.w(o + 20) == one(o + 20, 'mtctr r0') and img.w(o + 24) == 1317012512
        else:
            o = cmp_ + 4
            assert img.w(o + 4) == one(o + 4, 'slwi r11, r11, 2')
            B.asm(o + 8, 'addis r12, r11, 0x%X' % ha(at), 'addis r12, r11, 0x%X' % ha(table))
            B.asm(o + 12, 'lwz r12, %d(r12)' % slo(at), 'addi r12, r12, %d' % slo(table))
            assert img.w(o + 16) == one(o + 16, 'mtctr r12') and img.w(o + 20) == 1317012512
    info['sound_tables'] = {}
    for name, (addr, (hi_at, hi), (lo_at, lo), (cmp_at, cmp_), old) in SOUND_NAME_TABLES.items():
        n = sound_record(name, cap - 1) + 1
        ptrs = [img.w(addr + 4 * i) for i in range(old)] + [sptr['']] * (n - old)
        for r in kinds:
            ptrs[sound_record(name, r['kind'])] = sptr[r['cap']]
        at = B.alloc(4 * n)
        B.data(at, b''.join((struct.pack('>I', v) for v in ptrs)), 'table sound names ' + name)
        reg = hi.split()[1]
        B.asm(hi_at, 'lis %s 0x%X' % (reg, ha(at)), hi)
        B.asm(lo_at, 'addi %s %s %d' % (reg, reg, slo(at)), lo)
        B.asm(cmp_at, cmp_ % n, cmp_ % old)
        info['sound_tables'][name] = (at, n)
    info['cave_end'] = B.pc
    return (B, info)

def args(B):
    out = ['grow:0x%08X' % (B.pc + 4095 & ~4095)]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B.words.items())]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, RELOC_DUMMY) for a in B.reloc_args()]
    return out
