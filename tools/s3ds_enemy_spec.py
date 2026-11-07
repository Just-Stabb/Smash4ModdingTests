#!/usr/bin/env python3
"""Smash Run enemy behaviour specs, read from the 3DS code (enemy_fs.cro) and data (docs/smash-run-enemies/).

  python3 tools/s3ds_enemy_spec.py --cro ENEMY_FS_CRO --params PARAM_FS_DIR --enemy-root S3DS_ENEMY_ROOT
                                   [--out-json DIR] [--out-md DIR] [KIND ...]

  ENEMY_FS_CRO      the update's enemy_fs.cro (cro.sarc, tools/s3ds_unpack.py cros)
  PARAM_FS_DIR      param/enemy/fs/ (enemy_param_vl_<kind>.bin)
  S3DS_ENEMY_ROOT   enemy/ of the 3DS dump: <kind>/motion/body/main.bch (motion names, frames),
                    <kind>/model/body/c00/normal.vmt (mesh names), <kind>/animcmd/{attack,effect,sound}.bin
  --out-json DIR    default reference/smashrun_enemy_specs (<kind>.json)
  --out-md DIR      default docs/smash-run-enemies (<kind>.md)
  KIND              default: the 80 Smash Run kinds (0x00 killer .. 0x4F killercannon)

What it does (schema: docs/smash-run-enemies/README.md):
- CRO: named exports (BehaviorX::create, motion_data_set_x), named imports (the framework: app::Behavior::*,
  module Impl calls) reached through the CRO's veneers (`ldr pc, [pc, #-4]` + import slot), internal relocations.
- Kind -> behaviour: export app::Behavior<Kind>::create; its tail branch is the constructor (Behavior ctor,
  set_motion_label, set_damage_motion_label); vtable from the class's typeinfo; state table from vtable slot 72
  (change_state: literal = table, 24 bytes a state = {enter, update, exit} ARM PMFs {fn, adj}).
- Kind -> params: the FieldSmash param accessor's loader (EnemyParamAccessorInstanceFieldSmash vtable slot 4) has
  a 0x50-case switch on the kind; case K resets the param object at block+X; the static constructor builds the 80
  objects in order (ParameterArrayBase(elem size, read fn) per vl group, 0x14 bytes each); each read fn calls
  lib::read_format_v3 with a nibble format (bits 0-1 width 1/2/4 bytes, bits 2-3 count-1, class 3 = end). The slot
  [EnemyParamAccessor+0x60+4*kind] is the object: group i's entry count at +0x14*i+8, data at +0x14*i+0xC.
- Every function reachable from a state (and the vtable overrides, create / ctor) is decoded into a CFG and run
  through a small symbolic ARM interpreter: registers, VFP registers, stack slots and flags hold constants or
  provenance strings (this.f16c, mod.Ground, P2[0].power = 1, ret3:is_end ...). Calls are listed in order per
  basic block with their arguments resolved by the demangled signature (float args in s0.., others in r0..r3 then
  stack), vtable calls by slot name, the branch conditions rendered from the last compare, and each block's guard
  (the conditions that hold on every acyclic path to it).
- Per state a summary: motions (index -> name), kinetic / ground attach, change_state targets with guards, attacks
  (the framework's default set_attack_data(state) arms every entry of param group 2 whose state field = the state;
  explicit create_attack_data / AttackModule calls), effects, sounds, articles / enemies / items spawned,
  visibility, param reads (group / entry / field, with the value).
- ACMD (little-endian 3DS) per motion through the motion data set's hashsets.
Anything this can't resolve stays as a provenance string; the hand-read conclusions are in the .md files.
"""
import argparse
import json
import os
import re
import struct
import subprocess
import sys
import zlib

import capstone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Wii U / 3DS enemy kind table (Wii U names 0x1041A22C), 0x00-0x4F = the Smash Run kinds
KINDS = ['killer', 'kuribo', 'tac', 'patapata', 'galthunder', 'galice', 'galfire', 'peahat', 'gordo', 'kihunter',
         'monoeye', 'heiho', 'mettaur', 'shotzo', 'zima', 'tikibuzz', 'ghost', 'ghos', 'plasmawisp', 'waddledee',
         'critter', 'octorock', 'togemet', 'korokorobomb', 'mite', 'waddledoo', 'furiijio', 'dafune', 'brontoburt',
         'darios', 'dogars', 'churine', 'pooka', 'pokkuri', 'magnumkiller', 'dekakuribo', 'hammerbros', 'keronpa',
         'reo', 'mahva', 'shandera', 'redead', 'starman', 'bokkuncannon', 'kamek', 'bubble', 'eggrobo', 'zully',
         'stalfos', 'bokkun', 'bacula', 'deathpod', 'flage', 'dosudosu', 'bokkunmage', 'cucco', 'shinigami',
         'koshinigami', 'wanwanpile', 'wanwan', 'deathskull', 'chappy', 'metroid', 'totsukotsu', 'whitebear',
         'darknut', 'meganta', 'orne', 'bonkers', 'devilcar', 'popperam', 'propellerheiho', 'cake', 'mimicco',
         'ohganemochi', 'shiroiobake', 'generator', 'jugem', 'togezo', 'killercannon']

# 3DS Behavior / BehaviorImpl vtable slots (4 bytes each). Names from code.bin's BehaviorImpl vtable (static.crs
# names), the imports in the kinds' vtables, and the Wii U research (Wii U slot k = 3DS k+1 for k <= 27,
# k >= 29 equal: sr4/step2_research.md); "?" = role inferred.
SLOTS = {
    0: 'dtor', 1: 'dtor_delete', 2: 'slot2', 3: 'slot3', 4: 'update(AiInput*)', 5: 'update_on_skip',
    6: 'get_viewout_type', 7: 'notify_attack_hit_7?', 8: 'notify_attack_hit_8?', 9: 'notify_attack_hit_9?',
    11: 'notify_on_damage', 13: 'capture_motion?', 21: 'notify_on_tread? (stomped)',
    54: 'on_state_changed? (resets counters)', 55: 'every_frame?', 14: 'notify_on_capture_inner', 16: 'notify_on_common_thrown',
    17: 'notify_on_capture_cut', 28: 'notify_on_remove', 37: 'get_turn_type', 38: 'is_flip_model?', 39: 'is_down',
    40: 'initialize', 41: 'start', 42: 'initialize_after', 43: 'update_hp', 44: 'damage_turn',
    45: 'set_attack_data(state)', 46: 'set_attack_power', 47: 'has_alt_attack_state?', 48: 'alt_attack_state?',
    49: 'set_lr', 50: 'reverse_lr', 51: 'sync_lr_and_direction', 52: 'center_node', 53: 'clung_node',
    63: 'on_change_state?', 64: 'state_after_damage_ground', 65: 'state_after_damage_air',
    66: 'state_after_damage_default', 67: 'death_state', 71: 'notify_on_death', 72: 'change_state',
    73: 'change_state_interrupt', 74: 'change_state_base_call', 75: 'change_state_interrupt_base_call',
}
# EnemyModuleAccessor module offsets (3DS: acc + 0x3000 + X; Wii U = 3DS + 0x80 where known)
MODULES = {0x3040: 'Ai', 0x3048: 'Attack', 0x3054: 'Damage', 0x3058: 'Effect', 0x305c: 'Ground', 0x3068: 'Kinetic',
           0x306c: 'BehaviorModule', 0x3070: 'Motion', 0x3098: 'Model', 0x309c: 'Posture', 0x30b0: 'KineticEnergy'}
BEHAVIOR_FIELDS = {0: 'vt', 4: 'acc', 8: 'state', 0xc: 'kind', 0x10: 'var', 0x14: 'move_x', 0x18: 'move_y'}
# EnemyParamVL::InnerEnemyAttackParam (42 words; create_attack_data 0x7B2A1C -> AttackData)
ATTACK_FIELDS = {0: 'state', 1: 'id', 2: 'part', 3: 'node', 4: 'power', 5: 'angle', 6: 'kbg', 7: 'fkb', 8: 'bkb',
                 9: 'size', 10: 'x', 11: 'y', 12: 'z'}
ATTACK_DST = {13: 0x63, 14: 0x50, 15: 0x54, 16: 0x58, 17: 0x66, 18: 0x67, 19: 0x78, 20: 0x64, 21: 0x65, 22: 0x60,
              23: 0x6c, 24: 0x75, 25: 0x5e, 26: 0x61, 27: 0x62, 28: 0x68, 29: 0x69, 30: 0x6a, 31: 0x6b, 32: 0x7c,
              33: 0x6d, 34: 0x6e, 35: 0x6f, 36: 0x70, 37: 0x71, 38: 0x72, 39: 0x73, 40: 0x74, 41: 0x77}
REG_ALIAS = {'sb': 'r9', 'sl': 'r10', 'fp': 'r11', 'ip': 'r12'}
CC = ('eq', 'ne', 'hs', 'lo', 'mi', 'pl', 'vs', 'vc', 'hi', 'ls', 'ge', 'lt', 'gt', 'le', 'cs', 'cc')
INV = {'eq': 'ne', 'ne': 'eq', 'hs': 'lo', 'cs': 'lo', 'lo': 'hs', 'cc': 'hs', 'mi': 'pl', 'pl': 'mi', 'vs': 'vc',
       'vc': 'vs', 'hi': 'ls', 'ls': 'hi', 'ge': 'lt', 'lt': 'ge', 'gt': 'le', 'le': 'gt'}
IOP = {'eq': '==', 'ne': '!=', 'hs': '>=u', 'cs': '>=u', 'lo': '<u', 'cc': '<u', 'hi': '>u', 'ls': '<=u',
       'ge': '>=', 'lt': '<', 'gt': '>', 'le': '<=', 'mi': '<0', 'pl': '>=0', 'vs': 'overflow', 'vc': 'no-overflow'}
FOP = {'eq': '==', 'ne': '!=', 'hs': '>=', 'cs': '>=', 'lo': '<', 'cc': '<', 'hi': '>', 'ls': '<=', 'ge': '>=',
       'lt': '<', 'gt': '>', 'le': '<=', 'mi': '<', 'pl': '>=', 'vs': 'unordered', 'vc': 'ordered'}


def demangle(names):
    if not names:
        return []
    r = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True).stdout.split('\n')
    return r[:len(names)]


def fbits(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xffffffff))[0]


def fmtf(f):
    if f != f:
        return 'nan'
    return ('%.6g' % f)


# ------------------------------------------------------------------------------------------------ CRO
class Cro:
    def __init__(s, path):
        x = s.x = open(path, 'rb').read()
        t = lambda a: struct.unpack_from('<II', x, a)
        so, sn = t(0xC8)
        s.segs = [struct.unpack_from('<III', x, so + 12 * i) for i in range(sn)]
        so_ = lambda v: s.segs[v & 0xF][0] + (v >> 4)
        eo, en = t(0xD0)
        s.exp = {}
        for i in range(en):
            no, v = struct.unpack_from('<II', x, eo + 8 * i)
            s.exp[so_(v)] = s.cs(no)
        io, inn = t(0x100)
        s.imp = {}
        for i in range(inn):
            no, bo = struct.unpack_from('<II', x, io + 8 * i)
            nm = s.cs(no)
            p = bo
            while True:
                tgt, typ, last, u1, u2, add = struct.unpack_from('<IBBBBI', x, p)
                s.imp[so_(tgt)] = (nm, typ, add)
                if last:
                    break
                p += 12
        ro, rn = t(0x128)
        s.rel = {}
        for i in range(rn):
            tgt, typ, seg, u1, u2, add = struct.unpack_from('<IBBBBI', x, ro + 12 * i)
            s.rel[so_(tgt)] = (typ, s.segs[seg][0] + add)
        names = sorted(set(n for n, _t, _a in s.imp.values()) | set(s.exp.values()))
        s.dem = dict(zip(names, demangle(names)))
        s.exp_by_name = {s.dem[n]: a for a, n in s.exp.items()}
        s.code_lo, s.code_hi = s.segs[0][0], s.segs[0][0] + s.segs[0][1]
        # veneers: ldr pc, [pc, #-4] ; import word
        s.stubs = {}
        for a in range(s.code_lo, min(s.code_hi, 0x2000), 4):
            pass
        for a in s.imp:
            if s.code_lo <= a - 4 < s.code_hi and struct.unpack_from('<I', x, a - 4)[0] == 0xe51ff004:
                s.stubs[a - 4] = s.dem[s.imp[a][0]] + ('+%x' % s.imp[a][2] if s.imp[a][2] else '')
        # function entries: exports, data-segment relocations into code, bl targets
        s.fentries = set(a for a in s.exp if s.code_lo <= a < s.code_hi)
        for a, (_t, v) in s.rel.items():
            if not (s.code_lo <= a < s.code_hi) and s.code_lo <= v < s.code_hi:
                s.fentries.add(v)
        for a in range(s.code_lo, s.code_hi, 4):
            w = struct.unpack_from('<I', x, a)[0]
            if (w >> 24) & 0xf == 0xb and (w >> 28) != 0xf:
                off = w & 0xffffff
                if off & 0x800000:
                    off -= 1 << 24
                tt = a + 8 + off * 4
                if s.code_lo <= tt < s.code_hi:
                    s.fentries.add(tt)

    def cs(s, o):
        return s.x[o:s.x.index(b'\0', o)].decode('latin1')

    def u32(s, a):
        if a in s.rel:
            return s.rel[a][1]
        return struct.unpack_from('<I', s.x, a)[0]

    def word(s, a):
        """('imp', name) / ('ptr', addr) / ('c', value) of a data word"""
        if a in s.imp:
            return ('imp', s.dem[s.imp[a][0]])
        if a in s.rel:
            return ('ptr', s.rel[a][1])
        return ('c', struct.unpack_from('<I', s.x, a)[0])

    def name_at(s, a):
        if a in s.stubs:
            return s.stubs[a]
        if a in s.exp:
            return s.dem[s.exp[a]]
        return None


# ------------------------------------------------------------------------------------------------ values
# A value: ('c', int) constant, ('f', float) float constant, ('s', base, off) symbolic: base is a provenance string
# ('?' unknown), off a constant byte offset.
U = ('s', '?', 0)


def C(v):
    return ('c', v & 0xffffffff)


def Sy(base, off=0):
    return ('s', base, off)


def is_c(v):
    return v[0] == 'c'


def sval(v):
    """signed int of a constant"""
    x = v[1]
    return x - (1 << 32) if x & 0x80000000 else x


def eval_index(expr, var):
    """byte offset of a param index expression for a variation (only this.var and constants allowed)"""
    e = expr.replace('this.var', str(var))
    if not re.fullmatch(r'[0-9a-fx()+\-*<> ]+', e):
        return None
    try:
        return int(eval(e, {'__builtins__': {}}))
    except Exception:
        return None


def nonnull(v):
    """pointers the code null-checks that are never null in game: param slot / arrays, modules, accessor"""
    return v[0] == 's' and v[2] == 0 and (v[1].startswith('parr:') or v[1] in ('slot', 'PA', 'acc', 'GL') or
                                          v[1].startswith('slot(') or (v[1].startswith('mod.') and
                                                                       '.' not in v[1][4:]))


def rnd(v, maxlen=120):
    if v[0] == 'c':
        x = sval(v)
        s = str(x) if -4096 < x < 4096 else hex(v[1])
        return s
    if v[0] == 'f':
        return fmtf(v[1])
    b, o = v[1], v[2]
    s = b if not o else '%s%s0x%x' % (b, '+' if o > 0 else '-', abs(o))
    if len(s) > maxlen:
        s = s[:maxlen - 3] + '...'
    return s


# ------------------------------------------------------------------------------------------------ operand parsing
RL = re.compile(r'\{([^}]*)\}')


def reg(r):
    r = r.strip()
    return REG_ALIAS.get(r, r)


def parse_mem(s):
    """'[r0, #0x14]!' / '[r0], #4' / '[r1, r3, lsl #3]' / '[pc, #-0x10]' -> dict"""
    m = re.match(r'\[([^\]]*)\](!?)(?:, (.*))?$', s.strip())
    if not m:
        return None
    inner = [p.strip() for p in m.group(1).split(',')]
    d = {'base': reg(inner[0]), 'imm': 0, 'index': None, 'shift': 0, 'sub': False, 'wb': bool(m.group(2)),
         'post': None}
    rest = inner[1:]
    if rest:
        if rest[0].startswith('#'):
            d['imm'] = int(rest[0][1:], 0)
        else:
            r0 = rest[0]
            if r0.startswith('-'):
                d['sub'] = True
                r0 = r0[1:]
            d['index'] = reg(r0)
            if len(rest) > 1:
                mm = re.match(r'lsl #(\d+|0x[0-9a-f]+)', rest[1])
                if mm:
                    d['shift'] = int(mm.group(1), 0)
                else:
                    d['index'] = None
                    d['bad'] = True
    if m.group(3):
        p = m.group(3).strip()
        if p.startswith('#'):
            d['post'] = int(p[1:], 0)
        else:
            d['post'] = 'reg'
    return d


# ------------------------------------------------------------------------------------------------ CFG
class Block:
    def __init__(s, a):
        s.a = a
        s.insns = []
        s.succ = []          # (addr, edge kind, cc or None)
        s.term = None


class FuncCFG:
    def __init__(s, A, entry, maxn=6000):
        s.A, s.entry = A, entry
        c = A.cro
        reach = {}
        leaders = {entry}
        work = [entry]
        s.bad = False
        while work:
            a = work.pop()
            while True:
                if a in reach or not (c.code_lo <= a < c.code_hi) or len(reach) > maxn:
                    break
                ins = A.decode(a)
                if ins is None:
                    s.bad = True
                    break
                reach[a] = ins
                fl = A.flow(ins, entry)
                for t in fl['targets']:
                    if t not in leaders:
                        leaders.add(t)
                    work.append(t)
                if fl['ends']:
                    if fl.get('fall'):
                        leaders.add(a + 4)
                        work.append(a + 4)
                    break
                if fl.get('split'):
                    leaders.add(a + 4)
                a += 4
        s.insns = reach
        s.blocks = {}
        for l in sorted(leaders):
            if l not in reach:
                continue
            b = Block(l)
            a = l
            while a in reach:
                ins = reach[a]
                b.insns.append(ins)
                fl = A.flow(ins, entry)
                if fl['ends'] or fl.get('split'):
                    for t in fl['targets']:
                        b.succ.append((t, fl.get('kind'), fl.get('cc')))
                    if fl.get('fall') or fl.get('split'):
                        b.succ.append((a + 4, 'fall', INV.get(fl.get('cc')) if fl.get('cc') else None))
                    b.term = fl
                    break
                if a + 4 in leaders:
                    b.succ.append((a + 4, 'fall', None))
                    b.term = {'kind': 'fall'}
                    break
                a += 4
            s.blocks[l] = b
        # reverse post order
        seen, order = set(), []

        def dfs(x):
            stack = [(x, iter([t for t, _k, _c in s.blocks[x].succ if t in s.blocks]))]
            seen.add(x)
            while stack:
                n, it = stack[-1]
                for t in it:
                    if t not in seen:
                        seen.add(t)
                        stack.append((t, iter([u for u, _k, _c in s.blocks[t].succ if u in s.blocks])))
                        break
                else:
                    order.append(n)
                    stack.pop()
        if entry in s.blocks:
            dfs(entry)
        s.rpo = order[::-1]
        s.pos = {b: i for i, b in enumerate(s.rpo)}
        s.preds = {b: [] for b in s.blocks}
        for b in s.blocks.values():
            for t, k, cc in b.succ:
                if t in s.preds:
                    s.preds[t].append((b.a, k, cc))


# ------------------------------------------------------------------------------------------------ analyser
class State:
    def __init__(s):
        s.r = {}
        s.f = {}         # flags
        s.stk = {}
        s.dirty = set()

    def copy(s):
        n = State()
        n.r = dict(s.r)
        n.f = s.f
        n.stk = dict(s.stk)
        n.dirty = set(s.dirty)
        return n


def meet(states):
    if len(states) == 1:
        return states[0].copy()
    n = State()
    keys = set().union(*[set(x.r) for x in states])
    for k in keys:
        vs = [x.r.get(k, U) for x in states]
        n.r[k] = vs[0] if all(v == vs[0] for v in vs) else Sy('phi(%s)' % k)
    sk = set().union(*[set(x.stk) for x in states])
    for k in sk:
        vs = [x.stk.get(k, U) for x in states]
        if all(v == vs[0] for v in vs):
            n.stk[k] = vs[0]
    n.f = states[0].f if all(x.f == states[0].f for x in states) else ('?',)
    n.dirty = set().union(*[x.dirty for x in states])
    return n


def split_args(sig):
    m = re.search(r'\((.*)\)( const)?$', sig)
    if not m:
        return None
    s = m.group(1)
    if s in ('', 'void'):
        return []
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '<(':
            depth += 1
        elif ch in '>)':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    out.append(cur.strip())
    return out


def short_name(sig):
    n = sig.split('(')[0]
    n = n.replace('app::', '').replace('lib::', '')
    return n


class Analyzer:
    def __init__(s, cro, kind_ctx):
        s.cro = cro
        s.k = kind_ctx              # dict: kind, vt slots, param layout ...
        s.md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        s.cache = {}
        s.funcs = {}
        s.callcount = 0

    def decode(s, a):
        if a in s.cache:
            return s.cache[a]
        r = None
        for ins in s.md.disasm(s.cro.x[a:a + 4], a):
            r = (a, ins.mnemonic, ins.op_str)
        s.cache[a] = r
        return r

    @staticmethod
    def cc_of(mn):
        """(base mnemonic, condition) for ARM mnemonics like 'ldrlo', 'bleq', 'movgt', 'vmrseq'"""
        if mn in ('bls', 'bhs', 'bhi', 'blo', 'bne', 'beq', 'bmi', 'bpl', 'bge', 'blt', 'bgt', 'ble', 'bcs', 'bcc',
                  'bvs', 'bvc'):
            return 'b', mn[1:]
        for cc in CC:
            if mn.endswith(cc) and len(mn) > 2:
                base = mn[:-2]
                if base in ('', 'l', 't', 'te'):
                    continue
                if mn in ('teq', 'vcmpe', 'vnmle', 'smlal', 'umlal', 'vsel', 'vmla', 'vfnmls', 'bic', 'vcvtne',
                          'mls', 'smull', 'umull', 'mul', 'sbc', 'rsc', 'ldc', 'stc', 'svc', 'cdp'):
                    continue
                if base.endswith('.'):
                    continue
                return base, cc
        if '.' in mn:
            head, tail = mn.split('.', 1)
            for cc in CC:
                if head.endswith(cc) and len(head) > 3 and head[:-2] in ('vmov', 'vldr', 'vstr', 'vcmp', 'vcmpe',
                                                                          'vadd', 'vsub', 'vmul', 'vdiv', 'vcvt',
                                                                          'vneg', 'vabs', 'vsqrt'):
                    return head[:-2] + '.' + tail, cc
        return mn, None

    def is_tail_target(s, t, entry):
        c = s.cro
        if t in c.stubs:
            return True
        if t in c.fentries and t != entry:
            return True
        if t < entry:
            return True
        return False

    def flow(s, ins, entry):
        a, mn, op = ins
        base, cc = s.cc_of(mn)
        d = {'targets': [], 'ends': False}
        if a in s.cro.stubs and a != entry:      # fell through into a veneer: a tail call
            d.update(kind='tail', tail=a, ends=True)
            return d
        if base == 'b' and op.startswith('#'):
            t = int(op[1:], 16)
            prev = s.decode(a - 4) if a > entry else None
            epi = prev is not None and cc is None and (prev[1] == 'pop' and 'pc' not in prev[2] or
                                                       prev[1] == 'vpop' or
                                                       (prev[1] == 'add' and prev[2].startswith('sp, sp')) or
                                                       (prev[1] == 'ldr' and prev[2].startswith('lr, [sp]')))
            if s.is_tail_target(t, entry) or epi:
                d.update(kind='tail', tail=t, ends=cc is None, split=cc is not None, cc=cc)
                return d
            if cc:
                d.update(kind='cjump', targets=[t], ends=True, fall=True, cc=cc)
            else:
                d.update(kind='jump', targets=[t], ends=True)
            return d
        if base == 'bx':
            if op == 'lr':
                d.update(kind='ret', ends=cc is None, split=cc is not None, cc=cc)
            else:
                d.update(kind='itail', ends=cc is None, split=cc is not None, cc=cc)
            return d
        if base in ('pop', 'ldm', 'ldmia') and 'pc' in op:
            d.update(kind='ret', ends=cc is None, split=cc is not None, cc=cc)
            return d
        if base == 'ldr' and op.startswith('pc, [sp]'):
            d.update(kind='ret', ends=cc is None, split=cc is not None, cc=cc)
            return d
        if base == 'mov' and op == 'pc, lr':
            d.update(kind='ret', ends=cc is None, split=cc is not None, cc=cc)
            return d
        m = re.match(r'pc, \[pc, (\w+), lsl #2\]', op)
        if base == 'ldr' and m:
            n = s.switch_count(a)
            ts = []
            for i in range(n):
                v = s.cro.u32(a + 8 + 4 * i)
                ts.append(v)
            d.update(kind='switch', targets=ts, ends=True, fall=cc is not None, cc=cc, sw=m.group(1), table=ts)
            return d
        m = re.match(r'pc, pc, (\w+), lsl #2', op)
        if base == 'add' and m:
            n = s.switch_count(a)
            ts = [a + 8 + 4 * i for i in range(n)]
            d.update(kind='switch', targets=ts, ends=True, fall=cc is not None, cc=cc, sw=m.group(1), table=ts)
            return d
        if op.startswith('pc,') or ' pc}' in op or ', pc}' in op:
            if base not in ('push', 'stm', 'stmdb', 'str', 'cmp'):
                d.update(kind='itail', ends=True)
                return d
        return d

    def switch_count(s, a):
        for k in range(1, 6):
            p = s.decode(a - 4 * k)
            if p and p[1].startswith('cmp'):
                m = re.match(r'\w+, #(0x[0-9a-f]+|\d+)', p[2])
                if m:
                    return int(m.group(1), 0) + (1 if p[1] == 'cmp' or True else 0)
        return 0

    # ---------------------------------------------------------------- symbolic helpers
    def get(s, st, r):
        r = reg(r)
        if r == 'pc':
            return st.r.get('pc', U)
        if r.startswith('d') and r[1:].isdigit():
            n = int(r[1:])
            return st.r.get('s%d' % (2 * n), U)
        return st.r.get(r, U)

    def put(s, st, r, v):
        r = reg(r)
        if r.startswith('d') and r[1:].isdigit():
            n = int(r[1:])
            st.r['s%d' % (2 * n)] = v
            st.r['s%d' % (2 * n + 1)] = U
            st.dirty.add('s%d' % (2 * n))
            return
        st.r[r] = v
        st.dirty.add(r)

    def add(s, a, b):
        if a[0] == 'c' and b[0] == 'c':
            return C(a[1] + b[1])
        if a[0] == 'c':
            a, b = b, a
        if b[0] == 'c' and a[0] == 's':
            if a[1] == '?':
                return U
            return Sy(a[1], a[2] + sval(b))
        if a[0] == 's' and b[0] == 's':
            if a[1] == '?' or b[1] == '?':
                return U
            for x, y in ((a, b), (b, a)):
                if x[1] == 'PA' and y[1] in ('(this.kind<<2)',):
                    return Sy('PA[kind]', x[2] + y[2])
                if x[1] == 'PA':
                    return Sy('PA[expr]', x[2] + y[2])
                if x[1] == 'GL':
                    return Sy('GLE', x[2] + y[2])
                if x[1].startswith('parr:') and '[' not in x[1]:
                    return Sy('%s[%s]' % (x[1], rnd(y, 40)), x[2])
                if x[1] in ('sp',):
                    return Sy('sp[%s]' % rnd(y, 30), x[2])
                if x[1].startswith('data:') and '[' not in x[1]:
                    return Sy('%s[%s]' % (x[1], rnd(y, 40)), x[2])
            return Sy('(%s+%s)' % (rnd(a, 50), rnd(b, 50)))
        return U

    def shifted(s, v, kind, n):
        if n == 0:
            return v
        if v[0] == 'c':
            x = v[1]
            if kind == 'lsl':
                return C(x << n)
            if kind == 'lsr':
                return C(x >> n)
            if kind == 'asr':
                return C(sval(v) >> n)
            if kind == 'ror':
                return C((x >> n) | (x << (32 - n)))
        if v[0] == 's' and v[1] == '?':
            return U
        return Sy('(%s%s%d)' % (rnd(v, 50), {'lsl': '<<', 'lsr': '>>', 'asr': '>>', 'ror': 'ror'}[kind], n))

    def operand2(s, st, parts):
        """flexible second operand: '#imm' | 'rX' | 'rX, lsl #n' | 'rX, lsl rY'"""
        p0 = parts[0].strip()
        if p0.startswith('#'):
            return C(int(p0[1:], 0))
        v = s.get(st, p0)
        if len(parts) > 1:
            m = re.match(r'(lsl|lsr|asr|ror) #(0x[0-9a-f]+|\d+)', parts[1].strip())
            if m:
                return s.shifted(v, m.group(1), int(m.group(2), 0))
            if parts[1].strip() == 'rrx':
                return Sy('rrx(%s)' % rnd(v, 40))
            return Sy('(%s %s)' % (rnd(v, 40), parts[1].strip()))
        return v

    def load(s, addr, size=4, flt=False, ev=None):
        """value loaded from addr (a value)"""
        if addr[0] == 'c':
            a = addr[1]
            if s.cro.code_lo <= a < len(s.cro.x):
                return s.static(a, flt)
            return Sy('[0x%x]' % a)
        if addr[0] != 's' or addr[1] == '?':
            return U
        b, o = addr[1], addr[2]
        k = s.k
        if b == 'this':
            if o == 0xc and k.get('kind_index') is not None:
                return C(k['kind_index'])
            if o in BEHAVIOR_FIELDS:
                if o == 4:
                    return Sy('acc')
                return Sy('this.' + BEHAVIOR_FIELDS[o])
            return Sy('this.f%x' % o)
        if b == 'acc':
            if o in MODULES:
                return Sy('mod.' + MODULES[o])
            return Sy('acc.f%x' % o)
        if b == 'this.vt':
            return Sy('vfn:%d' % (o // 4))
        if b.startswith('mod.') and '.' not in b[4:]:
            if o == 0:
                return Sy(b + '.vt')
            return Sy('%s.f%x' % (b, o))
        if b.startswith('mod.') and b.endswith('.vt'):
            return Sy('mvfn:%s:%d' % (b[4:-3], o // 4))
        if b == '&lib::Singleton<app::EnemyParamAccessor>::instance_':
            return Sy('PA') if o == 0 else Sy('PA?%x' % o)
        if b == 'PA':
            if o == 0x38:
                return Sy('GL')
            if 0x60 <= o < 0x60 + 4 * 0x61 and (o - 0x60) % 4 == 0:
                kk = (o - 0x60) // 4
                return Sy('slot(%s)' % (KINDS[kk] if kk < len(KINDS) else hex(kk)))
            return Sy('PA.f%x' % o)
        if b == 'PA[kind]' and o == 0x60:
            return Sy('slot')
        if b == 'GLE':
            return Sy('gl.f%x' % o)
        if b == 'slot' or b.startswith('slot('):
            sk = k['kind'] if b == 'slot' else b[5:-1]
            P = k['params'].get(sk)
            tag = '' if sk == k['kind'] else sk + ':'
            for m in (P or {}).get('members', []):
                mo = m.get('offset')
                if mo is None:
                    continue
                if m['type'] == 'array' and o == mo + 0xC:
                    return Sy('parr:%s:%d' % (sk, m['index']))
                if m['type'] == 'array' and o == mo + 8:
                    if ev is not None:
                        ev.append({'op': 'param', 'ref': 'P%s%d.count' % (tag, m['index']),
                                   'value': len(m['values'])})
                    return Sy('P%s%d.count=%d' % (tag, m['index'], len(m['values'])))
                if m['type'] == 'struct' and mo <= o < mo + 4 * len(m['offsets']) and (o - mo) in m['offsets']:
                    fi = m['offsets'].index(o - mo)
                    val = m['values'][0][fi] if m['values'] and fi < len(m['values'][0]) else None
                    ref = 'P%sS%x.f%d' % (tag, mo, fi)
                    if ev is not None:
                        ev.append({'op': 'param', 'ref': ref, 'value': val})
                    return Sy('%s=%s' % (ref, fmtf(val) if isinstance(val, float) else val))
                if m['type'] not in ('array', 'struct', 'error') and o == mo:
                    val = m.get('value')
                    ref = 'P%s@0x%x' % (tag, mo)
                    if ev is not None:
                        ev.append({'op': 'param', 'ref': ref, 'value': val})
                    return Sy('%s=%s' % (ref, fmtf(val) if isinstance(val, float) else val))
            return Sy('%s.f%x' % (b, o))
        if b.startswith('parr:'):
            return s.param_field(b, o, flt, ev)
        if b.startswith('data:'):
            m = re.match(r'data:([0-9a-f]+)$', b)
            if m:
                return s.static(int(m.group(1), 16) + o, flt)
            return Sy('[%s+0x%x]' % (b, o))
        if b == 'sp' or b.startswith('sp['):
            return U
        return Sy('[%s]' % rnd(addr, 90))

    def A_param_count(s, kind, i):
        P = s.k['params'].get(kind)
        if not P or i >= len(P['groups']):
            return None
        return len(P['groups'][i]['values'])

    def param_field(s, b, o, flt, ev):
        m = re.match(r'parr:(\w+):(\d+)(?:\[(.*)\])?$', b)
        if not m:
            return Sy('[%s+0x%x]' % (b, o))
        kind, i, idx = m.group(1), int(m.group(2)), m.group(3)
        P = s.k['params'].get(kind)
        tag = '' if kind == s.k['kind'] else kind + ':'
        if not P or i >= len(P['groups']):
            return Sy('P%s%d[?]+0x%x' % (tag, i, o))
        g = P['groups'][i]
        es = g['elem_size']
        e, fo = divmod(o, es) if idx is None else (None, o % es)
        fi = g['offsets'].index(fo) if fo in g['offsets'] else None
        fname = g['names'][fi] if fi is not None and fi < len(g['names']) else ('f%d' % fi if fi is not None else
                                                                                '+0x%x' % fo)
        if idx is None:
            ref = 'P%s%d[%d].%s' % (tag, i, e, fname)
            vals = g['values']
            val = vals[e][fi] if e < len(vals) and fi is not None and fi < len(vals[e]) else None
        else:
            ref = 'P%s%d[%s].%s' % (tag, i, idx, fname)
            val = [vv[fi] if fi is not None and fi < len(vv) else None for vv in g['values']]
            byvar = {}
            for var in range(8):
                x = eval_index(idx, var)
                if x is None:
                    break
                e_ = (x + o) // es
                if 0 <= e_ < len(g['values']) and fi is not None and fi < len(g['values'][e_]):
                    byvar[var] = (e_, g['values'][e_][fi])
            if byvar:
                ref = 'P%s%d[%s].%s' % (tag, i, 'var->' + ','.join('%d:%d' % (v_, e_) for v_, (e_, _x) in
                                                                   sorted(byvar.items())), fname)
                val = {('var%d' % v_): x_ for v_, (_e, x_) in sorted(byvar.items())}
        if ev is not None:
            ev.append({'op': 'param', 'ref': ref, 'value': val})
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return Sy('%s=%s' % (ref, fmtf(val) if isinstance(val, float) else val))
        if isinstance(val, list):
            return Sy('%s=%s' % (ref, '/'.join(fmtf(x) if isinstance(x, float) else str(x) for x in val)))
        if isinstance(val, dict):
            return Sy('P%s%d[%s].%s=%s' % (tag, i, 'var*?' if not idx else 'var', fname, ' '.join(
                '%s:%s' % (k_[3:], fmtf(x) if isinstance(x, float) else x) for k_, x in val.items())))
        return Sy(ref)

    def static(s, a, flt=False):
        w = s.cro.word(a)
        if w[0] == 'imp':
            return Sy('&' + w[1])
        if w[0] == 'ptr':
            n = s.cro.name_at(w[1])
            return Sy('&' + n) if n else Sy('data:%x' % w[1])
        if flt:
            return ('f', fbits(w[1]))
        return C(w[1])

    def cond_eval(s, flags, cc):
        """True / False when the flags are constants, else None"""
        if cc is None:
            return True
        if not flags or flags[0] == '?':
            return None
        t = flags[0]
        if t in ('cmp', 'val') and nonnull(flags[1]) and (t == 'val' or flags[2] == C(0)):
            return {'eq': False, 'ne': True, 'hs': True, 'cs': True, 'lo': False, 'cc': False, 'hi': True,
                    'ls': False}.get(cc)
        if t in ('cmp', 'cmn') and is_c(flags[1]) and is_c(flags[2]):
            x, y = flags[1][1], flags[2][1]
            if t == 'cmn':
                y = (-y) & 0xffffffff
            sx, sy = (x - (1 << 32) if x & 0x80000000 else x), (y - (1 << 32) if y & 0x80000000 else y)
            r = (x - y) & 0xffffffff
            return {'eq': x == y, 'ne': x != y, 'hs': x >= y, 'cs': x >= y, 'lo': x < y, 'cc': x < y,
                    'hi': x > y, 'ls': x <= y, 'ge': sx >= sy, 'lt': sx < sy, 'gt': sx > sy, 'le': sx <= sy,
                    'mi': bool(r & 0x80000000), 'pl': not (r & 0x80000000)}.get(cc)
        if t == 'val' and is_c(flags[1]):
            x = flags[1][1]
            sx = x - (1 << 32) if x & 0x80000000 else x
            return {'eq': x == 0, 'ne': x != 0, 'mi': sx < 0, 'pl': sx >= 0, 'lt': sx < 0, 'ge': sx >= 0,
                    'gt': sx > 0, 'le': sx <= 0}.get(cc)
        if t == 'tst' and is_c(flags[1]) and is_c(flags[2]):
            x = flags[1][1] & flags[2][1]
            return {'eq': x == 0, 'ne': x != 0}.get(cc)
        if t == 'fcmp' and flags[1][0] == 'f' and flags[2][0] == 'f':
            x, y = flags[1][1], flags[2][1]
            return {'eq': x == y, 'ne': x != y, 'gt': x > y, 'ge': x >= y, 'lt': x < y, 'le': x <= y, 'hi': x > y,
                    'hs': x >= y, 'cs': x >= y, 'lo': x < y, 'cc': x < y, 'ls': x <= y, 'mi': x < y,
                    'pl': x >= y}.get(cc)
        if t == 'ccmp':
            px = s.cond_eval(flags[1], flags[2])
            if px is None:
                return None
            return s.cond_eval(flags[3] if px else flags[1], cc)
        return None

    def cond_text(s, flags, cc):
        if cc is None:
            return None
        if not flags or flags[0] == '?':
            return 'flags?%s' % cc
        t = flags[0]
        if t == 'cmp':
            a, b = flags[1], flags[2]
            if cc in ('mi', 'pl'):
                return '%s - %s %s' % (rnd(a), rnd(b), IOP[cc])
            op = IOP[cc]
            if is_c(b) and b[1] == 0 and op.endswith('u'):
                op = op[:-1]
            return '%s %s %s' % (rnd(a), op, rnd(b))
        if t == 'cmn':
            return '%s %s -(%s)' % (rnd(flags[1]), IOP[cc], rnd(flags[2]))
        if t == 'tst':
            if cc in ('eq', 'ne'):
                return '(%s & %s) %s 0' % (rnd(flags[1]), rnd(flags[2]), IOP[cc])
            return '(%s & %s) %s' % (rnd(flags[1]), rnd(flags[2]), IOP[cc])
        if t == 'teq':
            return '(%s ^ %s) %s 0' % (rnd(flags[1]), rnd(flags[2]), IOP.get(cc, cc))
        if t == 'val':     # movs / ands / subs ...: compare result with 0
            if cc in ('eq', 'ne'):
                return '%s %s 0' % (rnd(flags[1]), IOP[cc])
            if cc in ('mi', 'pl', 'lt', 'ge', 'gt', 'le'):
                return '%s %s 0' % (rnd(flags[1]), {'mi': '<', 'pl': '>=', 'lt': '<', 'ge': '>=', 'gt': '>',
                                                     'le': '<='}[cc])
            return '%s ?%s' % (rnd(flags[1]), cc)
        if t == 'fcmp':
            return '%s %s %s' % (rnd(flags[1]), FOP[cc], rnd(flags[2]))
        if t == 'fstat':
            return 'fpscr?%s' % cc
        if t == 'ccmp':          # conditional compare: prev, cc_executed, new
            prev, xcc, new = flags[1], flags[2], flags[3]
            p_x = s.cond_text(prev, xcc)
            p_y = s.cond_text(prev, cc)
            n_y = s.cond_text(new, cc)
            if xcc == INV.get(cc):        # e.g. cmp; cmpne; beq  -> prev==  || new==
                return '(%s) || (%s)' % (p_y, n_y)
            if xcc == cc:                 # cmp; cmpeq; beq -> prev== && new==
                return '(%s) && (%s)' % (p_y, n_y)
            return '((%s) ? (%s) : (%s))' % (p_x, n_y, p_y)
        return 'flags?%s' % cc

    # ---------------------------------------------------------------- function analysis
    def analyze(s, entry, depth=0):
        if entry in s.funcs:
            return s.funcs[entry]
        cfg = FuncCFG(s, entry)
        F = {'entry': entry, 'blocks': [], 'calls': set(), 'bad': cfg.bad}
        s.funcs[entry] = F
        out = {}
        guards = {}
        for ba in cfg.rpo:
            b = cfg.blocks[ba]
            ins_states = []
            gsets = []
            feasible_back = False
            for p, k, cc in cfg.preds[ba]:
                if p in out and out[p][1].get(ba) is False:
                    continue
                if cfg.pos.get(p, 1 << 30) >= cfg.pos[ba]:
                    feasible_back = True
                if cfg.pos.get(p, 1 << 30) < cfg.pos[ba] and p in out:
                    ins_states.append(out[p][0])
                    edge = out[p][1].get(ba)
                    if edge is True:
                        edge = None
                    g = set(guards.get(p, set()))
                    if edge:
                        g.add(edge)
                    gsets.append(g)
            if ba == entry:
                st = State()
                st.r = {'r0': Sy('this'), 'r1': Sy('arg1'), 'r2': Sy('arg2'), 'r3': Sy('arg3'), 'sp': Sy('sp'),
                        's0': Sy('farg0'), 's1': Sy('farg1'), 's2': Sy('farg2')}
                gs = set()
            elif ins_states:
                st = meet(ins_states)
                gs = set.intersection(*gsets) if gsets else set()
            elif not feasible_back:
                continue          # unreachable (every edge into it decided false)
            else:
                st = State()
                st.r = {'sp': Sy('sp')}
                gs = set()
            st.dirty = set()
            guards[ba] = gs
            evs, edges, term = s.run_block(b, st, F)
            out[ba] = (st, edges)
            F['blocks'].append({'addr': ba, 'guard': sorted(gs), 'events': evs, 'term': term})
        F['calls'] = sorted(F['calls'])
        return F

    def run_block(s, b, st, F):
        evs = []
        edges = {}
        term = None
        for ins in b.insns:
            a, mn, op = ins
            base, cc = s.cc_of(mn)
            known = s.cond_eval(st.f, cc) if cc else True
            cond = s.cond_text(st.f, cc) if cc and known is None else None
            last = ins is b.insns[-1]
            if known is False and not (last and b.term and b.term.get('kind') in ('cjump', 'switch', 'ret', 'tail',
                                                                                   'itail')):
                continue
            if known is True and cc:
                cc = None
            if last and b.term and b.term.get('kind') in ('jump', 'cjump', 'switch', 'ret', 'tail', 'itail'):
                k = b.term['kind']
                if k == 'jump':
                    term = {'type': 'goto', 'to': '%x' % b.term['targets'][0]}
                elif k == 'cjump':
                    t = b.term['targets'][0]
                    if known is True:
                        term = {'type': 'goto', 'to': '%x' % t, 'decided': True}
                        edges[t] = True
                        edges[a + 4] = False
                    elif known is False:
                        term = {'type': 'fall', 'to': '%x' % (a + 4), 'decided': True}
                        edges[t] = False
                        edges[a + 4] = True
                    else:
                        term = {'type': 'if', 'cond': cond, 'then': '%x' % t, 'else': '%x' % (a + 4)}
                        edges[t] = cond
                        edges[a + 4] = s.cond_text(st.f, INV[cc])
                elif k == 'switch':
                    sv = s.get(st, b.term['sw'])
                    term = {'type': 'switch', 'on': rnd(sv), 'cases': ['%x' % t for t in b.term['table']],
                            'default': '%x' % (a + 4) if b.term.get('fall') else None}
                    for i, t in enumerate(b.term['table']):
                        edges[t] = '%s == %d' % (rnd(sv), i)
                    if cc:
                        edges[a + 4] = s.cond_text(st.f, INV[cc])
                elif known is False:
                    term = {'type': 'fall', 'to': '%x' % (a + 4), 'decided': True}
                    edges[a + 4] = True
                elif k == 'ret':
                    if base in ('pop', 'ldm', 'ldmia', 'ldr'):
                        s.exec_insn(st, ins, base, cc, evs, F)
                    term = {'type': 'return', 'value': rnd(st.r.get('r0', U))}
                    if cc:
                        term['if'] = cond
                        edges[a + 4] = s.cond_text(st.f, INV[cc])
                elif k == 'tail':
                    t = b.term['tail']
                    s.do_call(st, t, evs, F, a, cond, tail=True)
                    term = {'type': 'tailcall', 'to': '%x' % t}
                    if cc:
                        term['if'] = cond
                        edges[a + 4] = s.cond_text(st.f, INV[cc])
                elif k == 'itail':
                    term = {'type': 'indirect_jump', 'op': '%s %s' % (mn, op)}
                    if base == 'bx' and op != 'lr':
                        s.do_icall(st, s.get(st, op), evs, F, a, cond)
                        term = {'type': 'tailcall', 'to': 'indirect'}
                    if cc:
                        term['if'] = cond
                        edges[a + 4] = s.cond_text(st.f, INV[cc])
                break
            s.exec_insn(st, ins, base, cc, evs, F, cond)
        if term is None:
            if b.succ:
                term = {'type': 'fall', 'to': '%x' % b.succ[0][0]}
            else:
                term = {'type': 'end'}
        return evs, edges, term

    def clobber_out(s, st, n):
        """a callee may write through any stack pointer it is given: forget those slots"""
        for r in ('r0', 'r1', 'r2', 'r3'):
            v = st.r.get(r, U)
            if v[0] == 's' and v[1] == 'sp':
                for k in list(st.stk):
                    if v[2] <= k < v[2] + 0x40:
                        st.stk[k] = Sy('out%d[+0x%x]' % (n, k - v[2]))
                st.stk[v[2]] = Sy('out%d[+0x0]' % n)

    def do_call(s, st, t, evs, F, a, cond, tail=False):
        c = s.cro
        s.callcount += 1
        n = s.callcount
        s.clobber_out(st, n)
        if t in c.stubs:
            sig = c.stubs[t]
            args = s.call_args(st, sig)
            if '(' not in sig:
                args = [rnd(s.get(st, 'r0')), rnd(s.get(st, 'r1'))]
            e = {'a': '%x' % a, 'op': 'call', 'fn': short_name(sig), 'args': args}
            if sig in READ_TYPES:
                e['sig'] = sig
            if cond:
                e['if'] = cond
            s.annotate(e, st)
            evs.append(e)
            F['calls'].add(short_name(sig))
            ret = Sy('ret%d:%s' % (n, short_name(sig).split('::')[-1]))
        else:
            args = [rnd(s.get(st, r)) for r in ('r0', 'r1', 'r2', 'r3') if r in st.dirty or r == 'r0'] + \
                   [rnd(st.r.get('s%d' % i, U)) for i in range(4) if 's%d' % i in st.dirty]
            nm = c.name_at(t)
            e = {'a': '%x' % a, 'op': 'lcall', 'target': '%x' % t, 'args': args, 'r1': rnd(s.get(st, 'r1'))}
            if nm:
                e['name'] = nm
            if cond:
                e['if'] = cond
            evs.append(e)
            F['calls'].add('L%x' % t)
            ret = Sy('ret%d:L%x' % (n, t))
        if tail:
            return
        for r in ('r0', 'r1', 'r2', 'r3', 'r12', 'lr') + tuple('s%d' % i for i in range(16)):
            st.r[r] = U
        st.r['r0'] = ret if not cond else Sy('(%s ? %s : old)' % (cond, ret[1]))
        st.r['s0'] = ret
        st.r['s1'] = Sy(ret[1] + '.s1')
        st.r['s2'] = Sy(ret[1] + '.s2')
        if t in c.stubs and c.stubs[t] in ('__aeabi_idivmod', '__aeabi_uidivmod'):
            st.r['r0'] = Sy('(%s / %s)' % (args[0], args[1]))
            st.r['r1'] = Sy('(%s %% %s)' % (args[0], args[1]))
        if t in c.stubs and c.stubs[t] in ('__aeabi_idiv', '__aeabi_uidiv'):
            st.r['r0'] = Sy('(%s / %s)' % (args[0], args[1]))
        st.dirty = set()
        st.f = ('?',)

    def do_icall(s, st, fv, evs, F, a, cond):
        s.callcount += 1
        n = s.callcount
        s.clobber_out(st, n)
        r0 = s.get(st, 'r0')
        args = [rnd(s.get(st, r)) for r in ('r1', 'r2', 'r3') if r in st.dirty and not (
            s.get(st, r)[0] == 's' and re.match(r'm?vfn:', s.get(st, r)[1]))] + \
               ['s%d=%s' % (i, rnd(st.r.get('s%d' % i, U))) for i in range(4) if 's%d' % i in st.dirty]
        e = {'a': '%x' % a}
        if fv[0] == 's' and fv[1].startswith('vfn:') and r0[0] == 's' and r0[1] == 'this':
            slot = int(fv[1][4:]) + fv[2] // 4
            e.update(op='vcall', slot=slot, name=SLOTS.get(slot, 'slot%d' % slot), args=args)
            ov = s.k['vt'].get(slot)
            if ov:
                e['impl'] = ov
            if slot in (72, 73, 74, 75) and is_c(s.get(st, 'r1')):
                e['state'] = sval(s.get(st, 'r1'))
            nm = 'ret%d:%s' % (n, SLOTS.get(slot, 'slot%d' % slot).split('(')[0])
        elif fv[0] == 's' and fv[1].startswith('mvfn:'):
            _, mod, sl = fv[1].split(':')
            slot = int(sl) + fv[2] // 4
            e.update(op='mcall', module=mod, slot=slot, args=args)
            nm = 'ret%d:%s.m%d' % (n, mod, slot)
        else:
            e.update(op='icall', fn=rnd(fv), obj=rnd(r0), args=args)
            nm = 'ret%d:icall' % n
        if cond:
            e['if'] = cond
        evs.append(e)
        for r in ('r0', 'r1', 'r2', 'r3', 'r12', 'lr') + tuple('s%d' % i for i in range(16)):
            st.r[r] = U
        st.r['r0'] = Sy(nm)
        st.r['s0'] = Sy(nm)
        st.dirty = set()
        st.f = ('?',)

    def call_args(s, st, sig):
        ps = split_args(sig)
        method = '::' in sig.split('(')[0] and not sig.startswith('lib::read') and \
            not re.match(r'(lib|nn|std)::', sig) and \
            not re.match(r'app::Behavior::(random_range|random_choice|success_by_|calc_angle|comp_angle)', sig)
        out = []
        spv = s.get(st, 'sp')
        ri, si, stk = (1 if method else 0), 0, (spv[2] if spv[0] == 's' and spv[1] == 'sp' else 0)
        if ps is None:
            return out
        for p in ps:
            if p in ('float',):
                if si < 16:
                    out.append(rnd(st.r.get('s%d' % si, U)))
                    si += 1
                else:
                    out.append('?')
            elif p == 'double':
                out.append('dbl')
            else:
                if ri < 4:
                    v = s.get(st, 'r%d' % ri)
                    ri += 1
                else:
                    v = st.stk.get(stk, U)
                    stk += 4
                out.append(rnd(v))
        return out

    def annotate(s, e, st):
        """resolve kind-specific constants in call args (motion index -> name)"""
        fn = e['fn']
        k = s.k
        if fn in ('Behavior::change_motion_state', 'Behavior::change_motion_state_script_only',
                  'Behavior::set_motion_no_restart') and e['args']:
            try:
                i = int(e['args'][0], 0)
                if 0 <= i < len(k['motions']):
                    e['motion'] = k['motions'][i].get('label') or k['motions'][i]['name']
            except ValueError:
                pass
        if fn == 'Behavior::set_mesh_visibility' and e['args']:
            try:
                i = int(e['args'][0], 0)
                if 0 <= i < len(k['meshes']):
                    e['mesh'] = k['meshes'][i]
            except ValueError:
                pass

    def exec_insn(s, st, ins, base, cc, evs, F, cond=None):
        a, mn, op = ins
        st.r['pc'] = C(a + 8)
        parts = [p.strip() for p in re.split(r',(?![^\[{]*[\]}])', op)] if op else []
        g = lambda r: s.get(st, r)

        def setr(r, v):
            if cc:
                old = s.get(st, r)
                if old != v:
                    v = Sy('(%s ? %s : %s)' % (cond, rnd(v, 40), rnd(old, 40)))
            s.put(st, r, v)
        b0 = base.rstrip('s') if base in ('movs', 'mvns', 'adds', 'subs', 'ands', 'orrs', 'rsbs', 'lsls', 'lsrs',
                                          'asrs', 'eors', 'bics') else base
        sets_flags = b0 != base
        if base in ('bl', 'blx') and op.startswith('#'):
            s.do_call(st, int(op[1:], 16), evs, F, a, cond)
            return
        if base == 'blx':
            s.do_icall(st, g(op), evs, F, a, cond)
            return
        if base in ('push', 'stmdb', 'vpush') or (base == 'stmdb' and op.startswith('sp!')):
            regs = RL.search(op).group(1).split(',')
            nregs = len(regs) * (2 if base == 'vpush' and regs[0].strip().startswith('d') else 1)
            sp = g('sp')
            st.r['sp'] = s.add(sp, C(-4 * nregs))
            return
        if base in ('pop', 'vpop'):
            regs = [reg(x) for x in RL.search(op).group(1).split(',')]
            nregs = len(regs) * (2 if base == 'vpop' and regs[0].startswith('d') else 1)
            st.r['sp'] = s.add(g('sp'), C(4 * nregs))
            for r in regs:
                if r not in ('pc', 'sp'):
                    st.r[r] = U if not r.startswith('d') else U
            return
        if b0 in ('mov', 'mvn'):
            v = s.operand2(st, parts[1:])
            if b0 == 'mvn':
                v = C(~v[1]) if is_c(v) else Sy('~%s' % rnd(v, 40))
            setr(parts[0], v)
            if sets_flags:
                st.f = ('val', v)
            return
        if base == 'movw':
            setr(parts[0], C(int(parts[1][1:], 0)))
            return
        if base == 'movt':
            v = g(parts[0])
            hi = int(parts[1][1:], 0)
            setr(parts[0], C((v[1] & 0xffff) | (hi << 16)) if is_c(v) else U)
            return
        if b0 in ('add', 'sub', 'rsb', 'and', 'orr', 'eor', 'bic', 'adc', 'sbc'):
            if len(parts) == 2:
                parts = [parts[0], parts[0], parts[1]]
            x = g(parts[1])
            y = s.operand2(st, parts[2:])
            if b0 == 'add':
                v = s.add(x, y)
            elif b0 == 'sub':
                v = s.add(x, C(-y[1])) if is_c(y) else (C(x[1] - y[1]) if is_c(x) and is_c(y) else
                                                         Sy('(%s-%s)' % (rnd(x, 40), rnd(y, 40))))
            elif b0 == 'rsb':
                v = C(y[1] - x[1]) if is_c(x) and is_c(y) else Sy('(%s-%s)' % (rnd(y, 40), rnd(x, 40)))
            elif is_c(x) and is_c(y):
                v = C({'and': x[1] & y[1], 'orr': x[1] | y[1], 'eor': x[1] ^ y[1], 'bic': x[1] & ~y[1],
                       'adc': x[1] + y[1], 'sbc': x[1] - y[1]}[b0])
            else:
                v = Sy('(%s %s %s)' % (rnd(x, 40), {'and': '&', 'orr': '|', 'eor': '^', 'bic': '&~', 'adc': '+c',
                                                     'sbc': '-c'}[b0], rnd(y, 40)))
            # a 'this' + kind<<2 style recognition
            if b0 == 'add' and v[0] == 's' and v[1].startswith('(this.kind<<2'):
                pass
            setr(parts[0], v)
            if sets_flags:
                st.f = ('val', v)
            return
        if b0 in ('lsl', 'lsr', 'asr', 'ror'):
            x = g(parts[1])
            if parts[2].startswith('#'):
                v = s.shifted(x, b0, int(parts[2][1:], 0))
            else:
                v = Sy('(%s %s %s)' % (rnd(x, 40), b0, rnd(g(parts[2]), 30)))
            setr(parts[0], v)
            if sets_flags:
                st.f = ('val', v)
            return
        if base in ('cmp', 'cmn', 'tst', 'teq'):
            x = g(parts[0])
            y = s.operand2(st, parts[1:])
            nf = (base, x, y)
            if cc:
                nf = ('ccmp', st.f, cc, nf)
            st.f = nf
            return
        if base in ('vcmp.f32', 'vcmpe.f32'):
            x = st.r.get(reg(parts[0]), U)
            if parts[1].startswith('#'):
                y = ('f', float(parts[1][1:]))
            else:
                y = st.r.get(reg(parts[1]), U)
            st.fp = ('fcmp', x, y)
            st.r['__fp'] = ('fcmp', x, y)
            return
        if base == 'vmrs':
            fp = st.r.get('__fp')
            nf = fp if fp else ('fstat',)
            if cc:
                nf = ('ccmp', st.f, cc, nf)
            st.f = nf
            return
        if base in ('ldr', 'ldrb', 'ldrh', 'ldrsb', 'ldrsh', 'ldrd', 'vldr'):
            md_ = parse_mem(','.join(parts[2:] if base == 'ldrd' else parts[1:]))
            if md_ is None:
                for r in parts[:2 if base == 'ldrd' else 1]:
                    setr(r, U)
                return
            if md_['base'] == 'pc':
                la = a + 8 + md_['imm']
                if base == 'vldr':
                    setr(parts[0], s.static(la, True))
                    return
                v = s.static(la)
                setr(parts[0], v)
                return
            bv = g(md_['base'])
            if md_['index']:
                iv = s.shifted(g(md_['index']), 'lsl', md_['shift'])
                addr = s.add(bv, iv if not md_['sub'] else Sy('-' + rnd(iv)))
            else:
                addr = s.add(bv, C(md_['imm'])) if md_['post'] is None else bv
            if bv[0] == 's' and bv[1] == 'sp' and addr[0] == 's' and addr[1] == 'sp':
                if base == 'ldrd':
                    setr(parts[0], st.stk.get(addr[2], U))
                    setr(parts[1], st.stk.get(addr[2] + 4, U))
                else:
                    setr(parts[0], st.stk.get(addr[2], U))
            else:
                if base == 'ldrd':
                    setr(parts[0], s.load(addr, 4, False, evs))
                    setr(parts[1], s.load(s.add(addr, C(4)), 4, False, evs))
                else:
                    setr(parts[0], s.load(addr, {'ldrb': 1, 'ldrsb': 1, 'ldrh': 2, 'ldrsh': 2}.get(base, 4),
                                          base == 'vldr', evs))
            if md_['wb']:
                s.put(st, md_['base'], addr)
            elif md_['post'] is not None:
                s.put(st, md_['base'], s.add(bv, C(md_['post'])) if isinstance(md_['post'], int) else U)
            return
        if base in ('str', 'strb', 'strh', 'strd', 'vstr'):
            md_ = parse_mem(','.join(parts[2:] if base == 'strd' else parts[1:]))
            if md_ is None or md_['base'] == 'pc':
                return
            bv = g(md_['base'])
            if md_['index']:
                addr = s.add(bv, s.shifted(g(md_['index']), 'lsl', md_['shift']))
            else:
                addr = s.add(bv, C(md_['imm'])) if md_['post'] is None else bv
            vals = [st.r.get(reg(parts[0]), U) if base == 'vstr' else g(parts[0])]
            if base == 'strd':
                vals.append(g(parts[1]))
            for i, v in enumerate(vals):
                ad = s.add(addr, C(4 * i))
                if ad[0] == 's' and ad[1] == 'sp':
                    st.stk[ad[2]] = v
                elif ad != U:
                    e = {'a': '%x' % a, 'op': 'store', 'addr': rnd(ad), 'val': rnd(v)}
                    if base in ('strb', 'strh'):
                        e['size'] = 1 if base == 'strb' else 2
                    if cond:
                        e['if'] = cond
                    evs.append(e)
            if md_['wb']:
                s.put(st, md_['base'], addr)
            elif md_['post'] is not None:
                s.put(st, md_['base'], s.add(bv, C(md_['post'])) if isinstance(md_['post'], int) else U)
            return
        if base in ('ldm', 'ldmia', 'vldmia', 'ldmib', 'ldmda', 'ldmdb'):
            rb = reg(parts[0].rstrip('!'))
            regs = [reg(x) for x in RL.search(op).group(1).split(',')]
            regs2 = []
            for r in regs:     # expand ranges like s0-s3 (capstone lists them explicitly)
                regs2.append(r)
            bv = g(rb)
            step = 4
            off = 0 if base in ('ldm', 'ldmia', 'vldmia') else (4 if base == 'ldmib' else 0)
            for i, r in enumerate(regs2):
                ad = s.add(bv, C(off + step * i))
                if ad[0] == 's' and ad[1] == 'sp':
                    v = st.stk.get(ad[2], U)
                else:
                    v = s.load(ad, 4, base == 'vldmia', evs)
                if r.startswith('d'):
                    s.put(st, r, v)
                else:
                    setr(r, v)
            if parts[0].endswith('!'):
                s.put(st, rb, s.add(bv, C(4 * len(regs2))))
            return
        if base in ('stm', 'stmia', 'vstmia', 'stmib'):
            rb = reg(parts[0].rstrip('!'))
            regs = [reg(x) for x in RL.search(op).group(1).split(',')]
            bv = g(rb)
            for i, r in enumerate(regs):
                v = st.r.get(r, U) if r.startswith('s') else g(r)
                ad = s.add(bv, C(4 * i))
                if ad[0] == 's' and ad[1] == 'sp':
                    st.stk[ad[2]] = v
                elif ad != U:
                    evs.append({'a': '%x' % a, 'op': 'store', 'addr': rnd(ad), 'val': rnd(v)})
            if parts[0].endswith('!'):
                s.put(st, rb, s.add(bv, C(4 * len(regs))))
            return
        if base.startswith('vmov'):
            d, src = reg(parts[0]), parts[1]
            if len(parts) == 3:        # vmov r0, r1, d0  / vmov d0, r0, r1
                for r in parts[:2]:
                    s.put(st, r, U)
                return
            if src.startswith('#'):
                v = ('f', float(src[1:]))
            else:
                v = st.r.get(reg(src), U) if not reg(src).startswith('r') else g(src)
                if v[0] == 'c' and d.startswith('s'):
                    v = ('f', fbits(v[1]))
                elif v[0] == 'f' and d.startswith('r'):
                    v = C(struct.unpack('<I', struct.pack('<f', v[1]))[0])
            setr(d, v)
            return
        if base.startswith('vcvt'):
            x = st.r.get(reg(parts[1]), U)
            if x[0] == 'c' and '.f32.s32' in base:
                v = ('f', float(sval(x)))
            elif x[0] == 'c' and '.f32.u32' in base:
                v = ('f', float(x[1]))
            elif x[0] == 'f' and ('.s32.f32' in base or '.u32.f32' in base):
                v = ('f', float(int(x[1])))     # kept as float-typed bits for readability
            else:
                v = x
            setr(parts[0], v)
            return
        if base.split('.')[0] in ('vadd', 'vsub', 'vmul', 'vdiv', 'vnmul', 'vmla', 'vmls', 'vfma', 'vfms'):
            bb = base.split('.')[0]
            if len(parts) == 2:
                parts = [parts[0], parts[0], parts[1]]
            x, y = st.r.get(reg(parts[1]), U), st.r.get(reg(parts[2]), U)
            if x[0] == 'f' and y[0] == 'f' and bb in ('vadd', 'vsub', 'vmul', 'vdiv'):
                try:
                    v = ('f', {'vadd': x[1] + y[1], 'vsub': x[1] - y[1], 'vmul': x[1] * y[1],
                               'vdiv': x[1] / y[1] if y[1] else float('nan')}[bb])
                except Exception:
                    v = U
            else:
                o = {'vadd': '+', 'vsub': '-', 'vmul': '*', 'vdiv': '/', 'vnmul': '*-', 'vmla': '+=*',
                     'vmls': '-=*', 'vfma': '+=*', 'vfms': '-=*'}[bb]
                if bb in ('vmla', 'vmls', 'vfma', 'vfms'):
                    acc = st.r.get(reg(parts[0]), U)
                    v = Sy('(%s %s %s*%s)' % (rnd(acc, 30), o[0], rnd(x, 30), rnd(y, 30)))
                else:
                    v = Sy('(%s %s %s)' % (rnd(x, 40), o, rnd(y, 40)))
            setr(parts[0], v)
            return
        if base.split('.')[0] in ('vneg', 'vabs', 'vsqrt'):
            bb = base.split('.')[0]
            x = st.r.get(reg(parts[1]), U)
            if x[0] == 'f':
                v = ('f', {'vneg': -x[1], 'vabs': abs(x[1]), 'vsqrt': abs(x[1]) ** 0.5}[bb])
            else:
                v = Sy('%s(%s)' % (bb[1:], rnd(x, 40)))
            setr(parts[0], v)
            return
        if base in ('sxtb', 'uxtb', 'sxth', 'uxth'):
            x = g(parts[1])
            if is_c(x):
                v = {'sxtb': C(((x[1] & 0xff) ^ 0x80) - 0x80), 'uxtb': C(x[1] & 0xff),
                     'sxth': C(((x[1] & 0xffff) ^ 0x8000) - 0x8000), 'uxth': C(x[1] & 0xffff)}[base]
            else:
                v = x
            setr(parts[0], v)
            return
        if base in ('mul', 'mla', 'muls', 'smull', 'umull', 'smulbb', 'smlal', 'umlal', 'mls'):
            if base in ('mul', 'muls') and len(parts) >= 3:
                x, y = g(parts[1]), g(parts[2])
                v = C(x[1] * y[1]) if is_c(x) and is_c(y) else Sy('(%s*%s)' % (rnd(x, 40), rnd(y, 40)))
                setr(parts[0], v)
            else:
                for r in parts[:2]:
                    if re.match(r'r\d+|sb|sl|fp|ip|lr', r):
                        setr(r, U)
            return
        if base in ('nop', 'pld', 'dmb', 'dsb', 'isb', 'clrex', 'svc', 'bkpt'):
            return
        # anything else: destination unknown
        if parts and re.match(r'^(r\d+|sb|sl|fp|ip|lr|s\d+|d\d+)$', parts[0]):
            setr(parts[0], Sy('%s(...)' % base))


# ------------------------------------------------------------------------------------------------ data readers
def vl_groups(path):
    import fighter_param_vl as V
    _h, toks = V.tokenize(open(path, 'rb').read())
    gs = []
    for t in toks:
        if isinstance(t, tuple):
            gs.append([t[1], []])
        else:
            gs[-1][1].append(t.value)
    out = []
    for n, vals in gs:
        per = len(vals) // n if n else 0
        out.append([vals[i * per:(i + 1) * per] for i in range(n)])
    return out


def param_layouts(A):
    """{kind: {'object': off, 'groups': [{'elem_size', 'format', 'offsets'}]}} from the FieldSmash accessor"""
    c = A.cro
    acc_vt = c.exp_by_name.get('app::EnemyParamAccessorInstanceFieldSmash::EnemyParamAccessorInstanceFieldSmash()')
    # ctor stores the vtable pointer: ldr r1, [pc, #x]
    vt = None
    for k in range(4):
        ins = A.decode(acc_vt + 4 * k)
        m = re.match(r'r1, \[pc, #(0x[0-9a-f]+|\d+)\]', ins[2])
        if ins[1] == 'ldr' and m:
            vt = c.u32(ins[0] + 8 + int(m.group(1), 0))
    loader = c.u32(vt + 16)       # slot 4
    builder = c.u32(vt + 8)       # slot 2: new + static ctor
    ctor_all = None
    for k in range(16):
        ins = A.decode(builder + 4 * k)
        if ins[1] == 'bl':
            t = int(ins[2][1:], 16)
            if t not in c.stubs:
                ctor_all = t
    # construction order: bl <param ctor> then add r4, r4, #size
    objs = []
    off = 0
    x = ctor_all
    pend = None
    while x < ctor_all + 0x2000:
        ins = A.decode(x)
        if ins is None:
            break
        if ins[1] == 'bl':
            t = int(ins[2][1:], 16)
            if t not in c.stubs:
                pend = t
        m = re.match(r'r4, r4, #(0x[0-9a-f]+|\d+)', ins[2])
        if ins[1] == 'add' and m and pend:
            objs.append((off, pend))
            off += int(m.group(1), 0)
            pend = None
        if ins[1] == 'pop' and 'pc' in ins[2]:
            if pend:
                objs.append((off, pend))
            break
        x += 4
    obj_ctor = dict(objs)
    # loader switch: cmp r5, #0x50; ldrlo pc, [pc, r5, lsl #2]
    cases = None
    for k in range(80):
        ins = A.decode(loader + 4 * k)
        if ins[1] == 'ldrlo' and ins[2].startswith('pc, [pc'):
            n = A.switch_count(ins[0])
            cases = [c.u32(ins[0] + 8 + 4 * i) for i in range(n)]
            break
    out = {}
    for kind_i, ca in enumerate(cases or []):
        if kind_i >= len(KINDS):
            break
        objoff = None
        y = ca
        acc_ = None
        for _ in range(60):
            ins = A.decode(y)
            if ins is None:
                break
            if ins[1] == 'ldr' and ins[2] == 'r0, [r4, #4]':
                acc_ = 0
            m = re.match(r'r0, r0, #(0x[0-9a-f]+|\d+)', ins[2])
            if ins[1] == 'add' and m and acc_ is not None:
                acc_ += int(m.group(1), 0)
            if ins[1] == 'str' and ins[2].startswith('r0, [') and acc_ is not None:
                objoff = acc_
                break
            if ins[1] == 'bl' and 'ParameterReceiver::reset' not in A.cro.stubs.get(int(ins[2][1:], 16), '') \
                    and A.cro.stubs.get(int(ins[2][1:], 16), '').startswith('lib::Resource::~'):
                pass
            y += 4
        ct = obj_ctor.get(objoff)
        groups, members, cb = [], [], None
        if ct:
            arrs, cb = array_bases(A, ct)
            byoff = {}
            for off, es, rf in arrs:
                f = read_format(A, rf)
                byoff[off] = (es, rf, f)
            items = reader_items(A, cb) if cb else []
            for typ, off, fmt in items:
                if typ == 'array' and off in byoff:
                    es, rf, f = byoff[off]
                    offs, o = [], 0
                    for w, n in f or []:
                        for _ in range(n):
                            offs.append(o)
                            o += w
                    g = {'type': 'array', 'offset': off, 'index': len(groups), 'elem_size': es,
                         'read_fn': '%x' % rf if rf else None, 'format': f, 'offsets': offs,
                         'widths': [w for w, n in (f or []) for _ in range(n)]}
                    groups.append(g)
                    members.append(g)
                elif typ == 'struct':
                    offs, o = [], 0
                    for w, n in fmt or []:
                        for _ in range(n):
                            offs.append(o)
                            o += w
                    members.append({'type': 'struct', 'offset': off, 'format': fmt, 'offsets': offs,
                                    'widths': [w for w, n in (fmt or []) for _ in range(n)]})
                else:
                    members.append({'type': typ, 'offset': off})
            if len(groups) != len(arrs):
                members.append({'type': 'error', 'note': 'reader reads %d of %d arrays' % (len(groups), len(arrs))})
        out[KINDS[kind_i]] = {'object': objoff, 'ctor': '%x' % ct if ct else None, 'reader': '%x' % cb if cb else None,
                              'groups': groups, 'members': members}
    return out


def vl_parse(path, members):
    """walk the vl tokens in the reader's order; fills 'values' (arrays: list of entries) / 'value'"""
    import fighter_param_vl as V
    _h, toks = V.tokenize(open(path, 'rb').read())
    i, errs = 0, []
    out = []
    for m in members:
        m = dict(m)
        if m['type'] == 'array':
            if i >= len(toks) or not isinstance(toks[i], tuple):
                errs.append('array at +0x%x: no group marker' % m['offset'])
                m['values'] = []
            else:
                n = toks[i][1]
                i += 1
                nf = len(m['offsets'])
                vals = []
                for e in range(n):
                    ent = []
                    for f in range(nf):
                        if i < len(toks) and not isinstance(toks[i], tuple):
                            ent.append(toks[i].value)
                            i += 1
                    vals.append(ent)
                m['values'] = vals
        elif m['type'] == 'struct':
            nf = len(m['offsets'])
            if i < len(toks) and isinstance(toks[i], tuple):
                i += 1
            ent = []
            for f in range(nf):
                if i < len(toks) and not isinstance(toks[i], tuple):
                    ent.append(toks[i].value)
                    i += 1
            m['values'] = [ent]
        elif m['type'] == 'error':
            pass
        else:
            if i < len(toks) and not isinstance(toks[i], tuple):
                m['value'] = toks[i].value
                i += 1
            else:
                errs.append('scalar at +0x%x: got a group marker' % (m['offset'] or 0))
        out.append(m)
    if i != len(toks):
        errs.append('%d of %d tokens read' % (i, len(toks)))
    return out, errs


READ_TYPES = {'lib::read(lib::BinaryReader&, lib::ParameterArrayBase&)': 'array',
              'lib::read(lib::BinaryReader&, float&)': 'float', 'lib::read(lib::BinaryReader&, int&)': 'int',
              'lib::read(lib::BinaryReader&, unsigned int&)': 'uint',
              'lib::read(lib::BinaryReader&, unsigned short&)': 'u16',
              'lib::read(lib::BinaryReader&, char&)': 'char', 'lib::read(lib::BinaryReader&, unsigned char&)': 'u8',
              'lib::read(lib::BinaryReader&, lib::ParameterString&)': 'str'}


def arg_off(txt):
    m = re.match(r'arg1(?:\+0x([0-9a-f]+))?$', txt or '')
    if not m:
        return None
    return int(m.group(1), 16) if m.group(1) else 0


def reader_items(A, fn, base=0, depth=0):
    """the read sequence of a param object's reader: [(kind, offset, format)]"""
    out = []
    if depth > 4:
        return out
    F = A.analyze(fn)
    for b in F['blocks']:
        for e in b['events']:
            if e['op'] == 'call':
                if e['fn'].startswith('read_format_v3'):
                    o = arg_off(e['args'][1]) if len(e['args']) > 1 else None
                    try:
                        fa = int(e['args'][2], 0)
                    except (ValueError, IndexError):
                        fa = None
                    out.append(('struct', None if o is None else base + o, decode_format(A.cro, fa) if fa else None))
                elif e.get('sig') in READ_TYPES:
                    o = arg_off(e['args'][1]) if len(e['args']) > 1 else None
                    out.append((READ_TYPES[e['sig']], None if o is None else base + o, None))
            elif e['op'] == 'lcall':
                o = arg_off(e.get('r1'))
                if o is not None:
                    out += reader_items(A, int(e['target'], 16), base + o, depth + 1)
    return out


def decode_format(c, fa):
    fs, i = [], 0
    while i < 256:
        b = c.x[fa + (i >> 1)] >> ((i & 1) * 4) & 0xf
        if b & 3 == 3:
            break
        fs.append((1 << (b & 3), (b >> 2) + 1))
        i += 1
    return fs


def array_bases(A, ctor):
    """([(offset, elem size, read fn)], receiver callback) from a param object's constructor"""
    c = A.cro
    out, regs = [], {}
    off = 0
    cb = None
    for k in range(256):
        ins = A.decode(ctor + 4 * k)
        if ins is None:
            break
        m = re.match(r'(r\d), \[pc, #(0x[0-9a-f]+|\d+)\]', ins[2])
        if ins[1] == 'ldr' and m:
            regs[m.group(1)] = c.u32(ins[0] + 8 + int(m.group(2), 0))
        m = re.match(r'(r\d), #(0x[0-9a-f]+|\d+)$', ins[2])
        if ins[1] == 'mov' and m:
            regs[m.group(1)] = int(m.group(2), 0)
        m = re.match(r'r0, r0, #(0x[0-9a-f]+|\d+)$', ins[2])
        if ins[1] == 'add' and m:
            off += int(m.group(1), 0)
        if ins[1] == 'stm' and 'r2' in ins[2]:
            cb = regs.get('r2')
        if ins[1] == 'bl':
            nm = c.stubs.get(int(ins[2][1:], 16), '')
            if 'ParameterArrayBase::ParameterArrayBase' in nm:
                out.append((off, regs.get('r1'), regs.get('r2')))
            if 'ParameterReceiver::reset' in nm:
                break
    return out, cb


def read_format(A, readfn):
    c = A.cro
    if not readfn:
        return None
    for k in range(16):
        ins = A.decode(readfn + 4 * k)
        if ins and ins[1].startswith('b') and ins[2].startswith('#'):
            t = int(ins[2][1:], 16)
            nm = c.stubs.get(t, '')
            if nm.startswith('lib::read(lib::BinaryReader&, '):
                return [({'char&)': 1, 'unsigned char&)': 1, 'unsigned short&)': 2}.get(nm.split(', ')[-1], 4), 1)]
            if not ins[1].startswith('bl'):
                continue
            if struct.unpack_from('<I', c.x, t)[0] == 0xe28f2000:
                fa = t + 8
                fs, i = [], 0
                while i < 256:
                    b = c.x[fa + (i >> 1)] >> ((i & 1) * 4) & 0xf
                    if b & 3 == 3:
                        break
                    fs.append((1 << (b & 3), (b >> 2) + 1))
                    i += 1
                return fs
            w = struct.unpack_from('<I', c.x, t)[0]
            if (w >> 24) == 0xea:            # b <stub>: a single scalar read
                off = w & 0xffffff
                if off & 0x800000:
                    off -= 1 << 24
                nm = c.stubs.get(t + 8 + off * 4, '')
                if nm.startswith('lib::read(lib::BinaryReader&, '):
                    return [({'char&)': 1, 'unsigned char&)': 1, 'unsigned short&)': 2}.get(nm.split(', ')[-1], 4),
                             1)]
    return None


def read_motion_set(c, kind):
    a = c.exp_by_name.get('app::motion_data_set_' + kind)
    if a is None:
        return None
    e, n = c.u32(a), c.u32(a + 4)
    ents = [(c.u32(e + 8 * i), c.u32(e + 8 * i + 4)) for i in range(n)]
    return {'addr': a, 'entries': ents}


def motion_names(root, kind):
    p = os.path.join(root, kind, 'motion', 'body', 'main.bch')
    if not os.path.exists(p):
        return {}
    import s3ds_model as M
    out = {}
    try:
        for an in M.Bch(open(p, 'rb').read()).skeletal_animations():
            out[an['name']] = {'frames': an['frames'], 'loop': an['loop']}
    except Exception as ex:      # noqa
        out['__error__'] = str(ex)
    return out


def joint_names(root, kind):
    """attack 'node' -> bone name: model.jtb (u16 count, count u16 bone indices) into the normal.bch skeleton"""
    d = os.path.join(root, kind, 'model', 'body', 'c00')
    try:
        j = open(os.path.join(d, 'model.jtb'), 'rb').read()
        n = struct.unpack_from('<H', j, 0)[0]
        idx = [struct.unpack_from('<H', j, 2 + 2 * i)[0] for i in range(min(n, (len(j) - 2) // 2))]
        import s3ds_model as M
        bones = [b['name'] for b in M.Bch(open(os.path.join(d, 'normal.bch'), 'rb').read()).models()[0]['bones']]
        return [bones[i] if i < len(bones) else None for i in idx]
    except Exception:
        return []


def vmt_names(root, kind):
    p = os.path.join(root, kind, 'model', 'body', 'c00', 'normal.vmt')
    if not os.path.exists(p):
        return []
    return [x.decode('latin1') for x in open(p, 'rb').read()[2:].split(b'\0') if x]


def acmd_le(path):
    """3DS (little-endian) ACMD -> {crc: [(name, [params])]}"""
    import acmd as AC
    d = open(path, 'rb').read()
    if d[:4] != b'ACMD':
        return {}
    count, = struct.unpack('<I', d[8:12])
    table = [struct.unpack('<II', d[0x10 + i * 8:0x18 + i * 8]) for i in range(count)]
    starts = sorted(set(o for _h, o in table)) + [len(d)]
    out = {}
    for h, off in table:
        bound = starts[starts.index(off) + 1]
        cmds, a = [], off
        while a + 4 <= bound:
            ident, = struct.unpack('<I', d[a:a + 4])
            if ident == AC.END:
                cmds.append(('Script_End', []))
                a += 4
                if a + 4 <= bound and struct.unpack('<I', d[a:a + 4])[0] in AC.INFO:
                    continue
                break
            info = AC.INFO.get(ident)
            if info is None:
                cmds.append(('unk_%08X' % ident, []))
                break
            ps = []
            fmt = info.get('format', [])
            for j in range(info['size'] - 1):
                raw = d[a + 4 + j * 4:a + 8 + j * 4]
                if j < len(fmt) and fmt[j] == 1:
                    ps.append(round(struct.unpack('<f', raw)[0], 6))
                else:
                    v = struct.unpack('<I', raw)[0]
                    ps.append(v - (1 << 32) if v & 0x80000000 and v > 0xffff0000 else v)
            cmds.append((info['name'], ps))
            a += info['size'] * 4
        out[h] = cmds
    return out


# ------------------------------------------------------------------------------------------------ per kind
def find_vtables(c, pat=rb'Behavior\w+?'):
    names = {}
    for m in re.finditer(rb'N3app(\d+)(' + pat + rb')E\0', c.x):
        names[m.start()] = m.group(2).decode()
    ti = {}
    for a, (_t, v) in c.rel.items():
        if v in names:
            ti[a - 4] = names[v]
    vt = {}
    for a, (_t, v) in c.rel.items():
        if v in ti and struct.unpack_from('<I', c.x, a - 4)[0] == 0 and a not in ti and a - 4 not in ti:
            vt[ti[v]] = a + 4
    return vt


def const_return(A, f):
    """N for 'mov r0, #N; bx lr', 'nop' for 'bx lr', else None"""
    i0 = A.decode(f)
    if i0 is None:
        return None
    if i0[1] == 'bx' and i0[2] == 'lr':
        return 'nop'
    i1 = A.decode(f + 4)
    m = re.match(r'r0, #(0x[0-9a-f]+|\d+)$', i0[2])
    if i0[1] in ('mov', 'mvn') and m and i1 and i1[1] == 'bx' and i1[2] == 'lr':
        v = int(m.group(1), 0)
        return v if i0[1] == 'mov' else ~v
    return None


def run_kind(c, kind, args, layouts, vts):
    idx = KINDS.index(kind)
    cls = None
    create = None
    for nm, a in c.exp_by_name.items():
        m = re.match(r'app::(Behavior\w+)::create\(app::EnemyModuleAccessor&, int, int\)$', nm)
        if m and m.group(1).lower() == 'behavior' + kind:
            cls, create = m.group(1), a
    spec = {'kind': kind, 'kind_index': '0x%02X' % idx, 'behavior_class': cls,
            'create': '%x' % create if create else None, 'notes': []}
    # params
    params_all = {}
    for k2 in KINDS:
        p2 = os.path.join(args.params, 'enemy_param_vl_%s.bin' % k2)
        if not (os.path.exists(p2) and k2 in layouts):
            continue
        if p2 not in VL_CACHE:
            VL_CACHE[p2] = vl_parse(p2, layouts[k2]['members'])
        members, errs = VL_CACHE[p2]
        groups = []
        for m in members:
            if m['type'] == 'array':
                names = ['f%d' % j for j in range(len(m['offsets']))]
                if m['index'] == 2 and m['elem_size'] == 0xa8:
                    for j, n in ATTACK_FIELDS.items():
                        names[j] = n
                elif m['index'] == 1 and m['elem_size'] == 0x1c:       # search params (Behavior::search_target)
                    names = ['search_type', 'interval', 'range_x?', 'range_y?', 'offset_x?', 'offset_y?', 'f6']
                elif m['elem_size'] == 0xa4 and len(names) == 41:      # weapon attack: no state field
                    for j, n in ATTACK_FIELDS.items():
                        if j:
                            names[j - 1] = n
                m['names'] = names
                groups.append(m)
        params_all[k2] = {'groups': groups, 'members': members, 'errors': errs}
    lay = layouts.get(kind, {})
    P = params_all.get(kind, {'groups': [], 'members': [], 'errors': ['no layout']})
    for e in P['errors']:
        spec['notes'].append('params: ' + e)
    spec['params'] = {'object_offset': lay.get('object'), 'ctor': lay.get('ctor'), 'reader': lay.get('reader'),
                      'members': [{k_: v for k_, v in m.items() if k_ not in ('read_fn',)} for m in P['members']]}
    # motions
    ms = read_motion_set(c, kind)
    anims = motion_names(args.enemy_root, kind)
    stems = {}
    for n in anims:
        stems[zlib.crc32(n.encode(), 0xFFFFFFFF) & 0xffffffff] = n
    motions = []
    if ms:
        for i, (h, fl) in enumerate(ms['entries']):
            nm = stems.get(h)
            m = {'index': i, 'name': nm.split('BodyMain')[-1] if nm and 'BodyMain' in nm else nm,
                 'anim': nm, 'hash': '%08x' % h, 'flags': '%x' % fl}
            if nm and nm in anims:
                m['frames'] = anims[nm]['frames']
                m['loop'] = anims[nm]['loop']
            m['label'] = m['name'] if m['name'] not in [x['name'] for x in motions] else \
                'motion%d(%s)' % (i, m['name'])
            motions.append(m)
    spec['motion_data_set'] = '%x' % ms['addr'] if ms else None
    spec['motions'] = motions
    spec['meshes'] = vmt_names(args.enemy_root, kind)
    vt_addr = vts.get(cls)
    ctx = {'kind': kind, 'params': params_all, 'motions': motions, 'meshes': spec['meshes'], 'vt': {}, 'kind_index': idx}
    A = Analyzer(c, ctx)
    vtab = {}
    if vt_addr:
        for k in range(80):
            w = c.word(vt_addr + 4 * k)
            if w[0] == 'imp':
                vtab[k] = {'name': SLOTS.get(k, 'slot%d' % k), 'impl': short_name(w[1]), 'shared': True}
            elif w[0] == 'ptr':
                if not (c.code_lo <= w[1] < c.code_hi):
                    break
                nm = c.name_at(w[1])
                e = {'name': SLOTS.get(k, 'slot%d' % k), 'fn': '%x' % w[1]}
                if nm:
                    e['impl'] = short_name(nm)
                cr = const_return(A, w[1])
                if cr is not None:
                    e['returns'] = cr
                vtab[k] = e
            else:
                if k > 2 and w[1] != 0:
                    break
                vtab[k] = {'name': SLOTS.get(k, 'slot%d' % k), 'fn': None}
        ctx['vt'] = {k: v.get('fn') or v.get('impl') for k, v in vtab.items()}
    spec['vtable'] = '%x' % vt_addr if vt_addr else None
    spec['vtable_slots'] = {str(k): v for k, v in vtab.items()}
    # state table: slot 72
    table = None
    if 72 in vtab and vtab[72].get('fn'):
        f = int(vtab[72]['fn'], 16)
        for k in range(12):
            ins = A.decode(f + 4 * k)
            m = re.match(r'r\d+, \[pc, #(0x[0-9a-f]+|\d+)\]', ins[2]) if ins else None
            if ins and ins[1] == 'ldr' and m:
                w = c.word(ins[0] + 8 + int(m.group(1), 0))
                if w[0] == 'ptr' and not (c.code_lo <= w[1] < c.code_hi):
                    table = w[1]
                    break
    spec['state_table'] = '%x' % table if table else None
    funcs = {}
    states = []
    if table:
        i = 0
        while i < 64:
            row = [c.word(table + 24 * i + 8 * j) for j in range(3)]
            ok = all(w[0] == 'ptr' and c.code_lo <= w[1] < c.code_hi or w == ('c', 0) for w in row)
            if not ok:
                break
            states.append({'id': i, 'enter': '%x' % row[0][1] if row[0][0] == 'ptr' else None,
                           'update': '%x' % row[1][1] if row[1][0] == 'ptr' else None,
                           'exit': '%x' % row[2][1] if row[2][0] == 'ptr' else None})
            i += 1
    # analyse: create, ctor, overridden slots, states
    todo = []
    if create:
        todo.append(create)
    for k, v in vtab.items():
        if v.get('fn') and 'returns' not in v and k not in (0, 1):
            todo.append(int(v['fn'], 16))
    for s_ in states:
        for r in ('enter', 'update', 'exit'):
            if s_[r]:
                todo.append(int(s_[r], 16))
    seen = set()
    depth = {t: 0 for t in todo}
    while todo:
        f = todo.pop(0)
        if f in seen:
            continue
        seen.add(f)
        F = A.analyze(f)
        for b in F['blocks']:
            for e in b['events']:
                if e['op'] == 'lcall':
                    t = int(e['target'], 16)
                    if t not in seen and depth.get(f, 0) < 4:
                        depth[t] = depth.get(f, 0) + 1
                        todo.append(t)
            if b['term'].get('type') == 'tailcall' and b['term'].get('to') not in (None, 'indirect'):
                t = int(b['term']['to'], 16)
                if t not in c.stubs and t not in seen and depth.get(f, 0) < 4:
                    depth[t] = depth.get(f, 0) + 1
                    todo.append(t)
    for f, F in A.funcs.items():
        funcs['%x' % f] = {'blocks': F['blocks'], 'calls': F['calls'], 'decode_error': F['bad']}
    spec['functions'] = funcs
    # ctor / labels
    spec['ctor'] = None
    if create:
        for b in A.funcs[create]['blocks']:
            if b['term']['type'] == 'tailcall':
                spec['ctor'] = b['term']['to']
        if spec['ctor'] and int(spec['ctor'], 16) in A.funcs:
            for b in A.funcs[int(spec['ctor'], 16)]['blocks']:
                for e in b['events']:
                    if e['op'] == 'call' and e['fn'] == 'Behavior::set_damage_motion_label':
                        spec['damage_motion_label'] = labels(e['args'], motions)
                    if e['op'] == 'call' and e['fn'] == 'Behavior::set_motion_label':
                        spec['motion_label'] = e['args']
                    if e['op'] == 'call' and e['fn'] == 'Behavior::Behavior':
                        spec['behavior_ctor_args'] = e['args']
        for b in A.funcs[create]['blocks']:
            for e in b['events']:
                if e['op'] == 'call' and e['fn'].startswith('operator new'):
                    spec['object_size'] = e['args'][0] if e['args'] else None
    # script hashsets: set_motion_label's table (12 bytes a motion: crc32 of name.init / name / name.exit)
    ml = spec.get('motion_label') or []
    if len(ml) > 1 and str(ml[1]).startswith('data:'):
        ha = int(ml[1][5:], 16)
        spec['motion_hashsets'] = '%x' % ha
        for m in motions:
            m['script_hashes'] = ['%08x' % c.u32(ha + 12 * m['index'] + 4 * j) for j in range(3)]
    # state summaries
    for s_ in states:
        s_['summary'] = summarize(A, s_, spec)
    spec['states'] = states
    spec['vtable_functions'] = vtable_summaries(A, spec)
    spec['helpers'] = helper_summaries(A, spec)
    spec['attacks'] = attack_list(spec)
    spec['joints'] = joint_names(args.enemy_root, kind)
    for a in spec['attacks']:
        n = a.get('node')
        if isinstance(n, int) and 0 <= n < len(spec['joints']):
            a['bone'] = spec['joints'][n]
    spec['acmd'] = acmd_for(args.enemy_root, kind, motions + [
        {'name': n.split('BodyMain')[-1]} for n in anims if 'BodyMain' in n and
        n.split('BodyMain')[-1] not in [m_.get('name') for m_ in motions]])
    spec['articles'] = articles_for(c, A, kind)
    return spec


WEAPON_VT = {}
WEAPON_SLOTS = {}


def articles_for(c, A, kind):
    """enemy_article_data_set_<kind> and the WeaponSpecializer_Enemy<Kind>* classes (their overridden slots)"""
    out = {'article_data_set': None, 'entries': [], 'weapons': {}}
    a = c.exp_by_name.get('app::enemy_article_data_set_' + kind)
    if a is not None:
        e, n = c.u32(a), c.u32(a + 4)
        out['article_data_set'] = '%x' % a
        out['entries'] = [[c.word(e + 16 * i + 4 * j)[1] if c.word(e + 16 * i + 4 * j)[0] == 'c' else
                           '%x' % c.word(e + 16 * i + 4 * j)[1] for j in range(4)] for i in range(n)]
    if not WEAPON_VT:
        WEAPON_VT.update(find_vtables(c, rb'WeaponSpecializer_Enemy\w+?'))
        for cls, vt in WEAPON_VT.items():
            for k in range(60):
                w = c.word(vt + 4 * k)
                if w[0] == 'imp':
                    WEAPON_SLOTS.setdefault(k, short_name(w[1]))
                elif w[0] != 'ptr' or not (c.code_lo <= w[1] < c.code_hi):
                    break
    for cls, vt in sorted(WEAPON_VT.items()):
        low = cls.lower()[len('weaponspecializer_enemy'):]
        best = max((k for k in KINDS if low.startswith(k)), key=len, default=None)
        if best != kind:
            continue
        w = {'class': cls, 'vtable': '%x' % vt, 'slots': {}}
        for k in range(60):
            x = c.word(vt + 4 * k)
            if x[0] == 'ptr' and c.code_lo <= x[1] < c.code_hi:
                A.analyze(x[1])
                w['slots'][str(k)] = {'name': WEAPON_SLOTS.get(k, 'slot%d' % k), 'fn': '%x' % x[1],
                                      'items': own_items(A, x[1])}
            elif x[0] != 'imp':
                break
        out['weapons'][low[len(best):]] = w
    return out


VL_CACHE = {}


def labels(args_, motions):
    out = []
    for a in args_:
        try:
            i = int(a, 0)
            out.append(motions[i]['name'] if 0 <= i < len(motions) else a)
        except (ValueError, TypeError):
            out.append(a)
    return out


CATS = [
    ('motion', ('Behavior::change_motion_state', 'Behavior::change_motion_state_script_only',
                'Behavior::set_motion_no_restart', 'MotionModuleImpl::', 'Behavior::change_script_state')),
    ('kinetic', ('EnemyKineticModuleImpl::', 'Behavior::set_kinetic', 'Behavior::clear_speed', 'Behavior::set_current_speed',
                 'Behavior::set_limit_speed', 'Behavior::reset_gravity', 'EnemyAerialModuleImpl::', 'Behavior::move',
                 'KineticModuleImpl::', 'EnemyGroundLineTraceModuleImpl::')),
    ('ground', ('GroundModuleImpl::', 'Behavior::check_', 'Behavior::is_exist_floor_under', 'Behavior::ray_check',
                'Behavior::get_height_from_ground', 'Behavior::is_falling', 'Behavior::set_rhombus')),
    ('target', ('Behavior::search', 'Behavior::get_nearest_target', 'Behavior::get_target', 'Behavior::check_turn_to',
                'EnemyAiModuleImpl::', 'Behavior::get_lr_to_nearest_target', 'Behavior::is_target',
                'Behavior::get_enemy_target_pos', 'Behavior::is_in_view_area', 'FighterManager::')),
    ('random', ('Behavior::success_by', 'Behavior::random_')),
    ('attack', ('AttackModuleImpl::', 'Behavior::set_attack', 'Behavior::create_attack_data', 'Behavior::hit_attack',
                'Behavior::set_attack_absolute_data', 'Behavior::bullet', 'Behavior::abort_bullet',
                'Behavior::enable_hit', 'Behavior::disable_hit', 'Behavior::invincible_hit', 'HitModuleImpl::',
                'Behavior::set_shield', 'Behavior::enable_tread', 'Behavior::disable_tread',
                'Behavior::enable_ground_damage', 'Behavior::disable_ground_damage', 'Behavior::delete_hit',
                'Behavior::ignore_damage', 'Behavior::invalid_ignore_damage', 'DamageModuleImpl::')),
    ('effect', ('Behavior::request_effect', 'Behavior::request_follow_effect', 'EffectModuleImpl::',
                'Behavior::remove_effect', 'Behavior::remove_all_continual_effect', 'Behavior::set_flash_color',
                'ColorBlendModuleImpl::', 'Behavior::request_quake', 'ShakeModuleImpl::', 'EffectModuleSimple::')),
    ('sound', ('Behavior::play_se', 'Behavior::stop_se', 'SoundModuleImpl::', 'SoundEnemyOrne::')),
    ('spawn', ('Behavior::generate_article', 'Behavior::create_enemy', 'Behavior::create_item', 'Behavior::reserve_enemy',
               'Behavior::create_reserved_enemy', 'ArticleModuleImpl::', 'EnemyManager::create_request',
               'EnemyGenerator::', 'ItemManager::', 'Behavior::create_dead_item', 'Behavior::is_generate_shoot')),
    ('visibility', ('Behavior::set_mesh_visibility', 'Behavior::set_visibility', 'ModelModulePartialImpl::',
                    'Behavior::enable_shadow', 'Behavior::disable_shadow', 'EffectModuleImpl::set_visible')),
    ('lr', ('Behavior::set_lr', 'Behavior::reverse_lr', 'Behavior::sync_lr', 'Behavior::damage_turn')),
    ('lifecycle', ('EnemyManager::remove_enemy_by_id', 'Behavior::set_death_flag', 'BehaviorImpl::notify_on_death',
                   'Behavior::notify_on_remove', 'EnemyManager::set_already_dead_flag', 'Behavior::update_hp',
                   'BehaviorImpl::change_common_state', 'Behavior::init_common_leave', 'Behavior::update_common_leave',
                   'Behavior::finalize_common_leave', 'EnemyManager::request_defeat_boss')),
]


def category(fn):
    for cat, pre in CATS:
        if any(fn.startswith(p) for p in pre):
            return cat
    return 'other'


def summarize(A, s_, spec):
    """per role: the function's own items (local calls as 'helper' items) and 'derived': the key items of the
    function and every helper it reaches (depth 5), each with the helper chain ('via')"""
    out = {}
    for role in ('enter', 'update', 'exit'):
        if not s_[role]:
            continue
        f = int(s_[role], 16)
        out[role] = own_items(A, f)
        out[role + '_derived'] = derived(A, f, [], [], 0)
    return out


KEY_CATS = ('state', 'motion', 'attack', 'visibility', 'spawn', 'effect', 'sound', 'lifecycle', 'kinetic', 'lr')


def own_items(A, f):
    items = []
    if f not in A.funcs:
        return items
    F = A.funcs[f]
    for b in F['blocks']:
        g = b['guard']
        for e in b['events']:
            it = None
            if e['op'] == 'call':
                it = {'cat': category(e['fn']), 'call': e['fn'], 'args': e['args']}
                for k in ('motion', 'mesh', 'if'):
                    if k in e:
                        it[k] = e[k]
            elif e['op'] == 'vcall':
                cat = 'state' if e['slot'] in (72, 73, 74, 75) else ('attack' if e['slot'] in (45, 46) else
                                                                     ('lr' if e['slot'] in (49, 50, 51) else 'vcall'))
                it = {'cat': cat, 'call': e['name'], 'slot': e['slot'], 'args': e['args']}
                for k in ('state', 'impl', 'if'):
                    if k in e:
                        it[k] = e[k]
            elif e['op'] == 'lcall':
                it = {'cat': 'helper', 'call': 'L' + e['target'], 'args': e['args']}
                if 'if' in e:
                    it['if'] = e['if']
            elif e['op'] == 'mcall':
                it = {'cat': 'kinetic' if e['module'] in ('KineticEnergy', 'Kinetic') else 'module',
                      'call': '%s.vslot%d' % (e['module'], e['slot']), 'args': e['args']}
            elif e['op'] == 'icall':
                it = {'cat': 'icall', 'call': e['fn'], 'args': e['args']}
            elif e['op'] == 'param':
                it = {'cat': 'param', 'ref': e['ref'], 'value': e['value']}
            elif e['op'] == 'store':
                ad = e['addr']
                cat = 'kinetic' if 'KineticEnergy' in ad else ('motion' if ad.startswith('mod.Motion') else
                                                               ('field' if ad.startswith('this+') else 'store'))
                it = {'cat': cat, 'store': ad, 'val': e['val']}
                if 'if' in e:
                    it['if'] = e['if']
            if it is None:
                continue
            if 'a' in e:
                it['at'] = e['a']
            if g and it['cat'] != 'param':
                it['guard'] = g
            items.append(it)
    return items


def derived(A, f, guard, via, depth):
    out = []
    if f not in A.funcs or depth > 5 or f in via:
        return out
    for it in own_items(A, f):
        if it['cat'] == 'helper':
            g2 = guard + it.get('guard', []) + ([it['if']] if 'if' in it else [])
            out += derived(A, int(it['call'][1:], 16), g2, via + [f], depth + 1)
        elif it['cat'] in KEY_CATS:
            d = dict(it)
            if guard:
                d['guard'] = guard + it.get('guard', [])
            if via:
                d['via'] = ['%x' % x for x in via[1:]] + ['%x' % f]
            out.append(d)
    return out


def helper_summaries(A, spec):
    roots = set()
    for s_ in spec['states']:
        for r in ('enter', 'update', 'exit'):
            if s_[r]:
                roots.add(int(s_[r], 16))
    for v in spec['vtable_slots'].values():
        if v.get('fn'):
            roots.add(int(v['fn'], 16))
    for k in ('create', 'ctor'):
        if spec.get(k):
            roots.add(int(spec[k], 16))
    out = {}
    for f in sorted(A.funcs):
        if f in roots:
            continue
        out['%x' % f] = own_items(A, f)
    return out


def vtable_summaries(A, spec):
    out = {}
    for k, v in spec['vtable_slots'].items():
        if v.get('fn') and int(v['fn'], 16) in A.funcs and 'returns' not in v:
            out[k] = {'name': v['name'], 'fn': v['fn'], 'items': own_items(A, int(v['fn'], 16))}
    return out


def attack_list(spec):
    """param group 2 entries (InnerEnemyAttackParam) = the attacks the default set_attack_data(state) arms"""
    out = []
    gs = [m for m in spec['params']['members'] if m['type'] == 'array']
    if len(gs) > 2 and gs[2]['elem_size'] == 0xa8:
        for e, v in enumerate(gs[2]['values']):
            d = {'entry': e}
            for j, n in ATTACK_FIELDS.items():
                if j < len(v):
                    d[n] = v[j]
            d['other'] = {('f%d->AttackData+0x%x' % (j, ATTACK_DST[j])): v[j] for j in ATTACK_DST if j < len(v)}
            out.append(d)
    return out


def acmd_for(root, kind, motions):
    out = {}
    names = {}
    for m in motions:
        if not m.get('name'):
            continue
        short = m['name'].lower()
        for suf, key in (('', 'main'), ('.init', 'init'), ('.exit', 'exit')):
            names[zlib.crc32((short + suf).encode()) & 0xffffffff] = (m['name'], key)
    for m in motions:          # the motion set's hashsets (aliases: several indices on one animation)
        for h, key in zip(m.get('script_hashes', []), ('init', 'main', 'exit')):
            h = int(h, 16)
            if h and h not in names:
                names[h] = (m.get('label') or m.get('name'), key)
    for typ in ('attack', 'effect', 'sound'):
        p = os.path.join(root, kind, 'animcmd', typ + '.bin')
        if not os.path.exists(p):
            continue
        for h, cmds in acmd_le(p).items():
            nm, key = names.get(h, ('0x%08x' % h, 'main'))
            out.setdefault(nm, {}).setdefault(typ, {})[key] = [[n] + ps for n, ps in cmds if n != 'Script_End']
    return out


# ------------------------------------------------------------------------------------------------ markdown
def md_kind(spec):
    L = []
    k = spec['kind']
    L.append('# %s (kind %s, %s)' % (k, spec['kind_index'], spec['behavior_class']))
    L.append('')
    L.append('Generated by `tools/s3ds_enemy_spec.py` from the 3DS enemy_fs.cro (update) and the fs params. '
             'Machine-readable: `reference/smashrun_enemy_specs/%s.json`. Hand-read notes, where there are any, are in '
             'the section "Reading" (from reference/smashrun_enemy_specs/hand_read.json). Schema and conventions: '
             'README.md.' % k)
    L.append('')
    hr = spec.get('hand_read')
    if hr:
        L.append('## Reading (hand-checked)')
        L.append('')
        L.append('From `reference/smashrun_enemy_specs/hand_read.json` (read from the listings below and their ARM).')
        L.append('')
        L.append('**%s** (%s). %s' % (k, hr.get('class', ''), hr.get('summary', '')))
        L.append('')
        if hr.get('variations'):
            L.append('- Variations: ' + hr['variations'])
        for key in ('targeting', 'kinetics', 'projectiles', 'death', 'meshes'):
            if hr.get(key):
                L.append('- %s: %s' % (key.capitalize(), hr[key]))
        L.append('')
        if hr.get('danger'):
            L.append('When it is dangerous:')
            L.append('')
            for d in hr['danger']:
                st = d.get('states')
                rest = ', '.join('%s %s' % (k_, json.dumps(v) if isinstance(v, (list, dict)) else v)
                                 for k_, v in d.items() if k_ not in ('states', 'source', 'note'))
                L.append('- states %s: %s%s%s' % (st, d.get('source', ''), ('; ' + rest) if rest else '',
                                                 ('. ' + d['note']) if d.get('note') else ''))
            L.append('')
        if hr.get('states'):
            L.append('States:')
            L.append('')
            for sid, txt in sorted(hr['states'].items(), key=lambda kv: int(kv[0])):
                L.append('- %s: %s' % (sid, txt))
            L.append('')
    L.append('## Overview')
    L.append('')
    L.append('- create 0x%s, ctor 0x%s, object size %s, vtable 0x%s, state table 0x%s, motion data set 0x%s' % (
        spec['create'], spec.get('ctor'), spec.get('object_size'), spec.get('vtable'), spec.get('state_table'),
        spec.get('motion_data_set')))
    if spec.get('damage_motion_label'):
        L.append('- damage motions (set_damage_motion_label): %s' % ', '.join(map(str, spec['damage_motion_label'])))
    vs = spec['vtable_slots']
    ret = {k_: v.get('returns') for k_, v in vs.items() if 'returns' in v}
    for sl in ('64', '65', '66', '67'):
        if sl in ret:
            L.append('- slot %s %s: %s' % (sl, SLOTS[int(sl)], ret[sl]))
    ov = ['%s %s 0x%s' % (k_, v['name'], v['fn']) for k_, v in vs.items() if v.get('fn') and 'returns' not in v
          and int(k_) > 1]
    L.append('- overridden slots: ' + '; '.join(ov))
    if spec['meshes']:
        L.append('- meshes (normal.vmt index: name): ' + ', '.join('%d %s' % (i, n) for i, n in
                                                                   enumerate(spec['meshes'])))
    for n in spec['notes']:
        L.append('- note: ' + n)
    L.append('')
    L.append('## Motions')
    L.append('')
    L.append('| idx | motion | frames | loop | flags |')
    L.append('|---|---|---|---|---|')
    for m in spec['motions']:
        L.append('| %d | %s | %s | %s | %s |' % (m['index'], m['name'], fmtf(m['frames']) if 'frames' in m else '',
                                                 m.get('loop', ''), m['flags']))
    L.append('')
    L.append('## Attack params (group 2, armed by set_attack_data(state) for entries with that state)')
    L.append('')
    sad = spec['vtable_slots'].get('45', {})
    if sad.get('fn'):
        L.append('**set_attack_data (slot 45) is overridden** (0x%s%s): the table below is not armed per state by the '
                 'framework; see the slot 45 entry under Vtable overrides.' % (
                     sad['fn'], ', an empty function: no attack is armed on state changes' if sad.get('returns') ==
                     'nop' else ''))
        L.append('')
    if spec['attacks']:
        L.append('| entry | state | id | part | node | power | angle | kbg | fkb | bkb | size | x | y | z | bone (jtb) |')
        L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for a in spec['attacks']:
            L.append('| ' + ' | '.join(str(a.get(n, '')) if not isinstance(a.get(n), float) else fmtf(a[n]) for n in
                                       ['entry'] + [ATTACK_FIELDS[j] for j in range(13)] + ['bone']) + ' |')
    L.append('')
    L.append('## Params')
    L.append('')
    fv = lambda x: fmtf(x) if isinstance(x, float) else str(x)
    for g in spec['params']['members']:
        if g['type'] == 'array':
            L.append('- P%d (slot+0x%x, elem 0x%x, %d entries): %s' % (g['index'], g['offset'], g['elem_size'],
                                                                    len(g['values']), ' / '.join(
                ' '.join(fv(x) for x in v) for v in g['values'])))
        elif g['type'] == 'struct':
            L.append('- struct at slot+0x%x: %s' % (g['offset'] or 0, ' '.join(fv(x) for x in g['values'][0])))
        elif g['type'] != 'error':
            L.append('- M+0x%x (%s) = %s' % (g['offset'] or 0, g['type'], fv(g.get('value'))))
    L.append('')
    L.append('## States')
    L.append('')
    sad = spec['vtable_slots'].get('45', {})
    L.append('Per state: the attack the framework arms on entry, then each function\'s items in code order '
             '(`[if ...]` = the conditions that hold on every path to the call, the last three shown; `[when ...]` '
             '= a conditional call), helper calls as `helper Lxxxx` (listed under Helpers), and the transitions '
             'and motions reached through helpers.')
    L.append('')
    for s_ in spec['states']:
        if not (s_['enter'] or s_['update'] or s_['exit']):
            L.append('### state %d: none' % s_['id'])
            L.append('')
            continue
        L.append('### state %d (enter %s, update %s, exit %s)' % (s_['id'], s_['enter'], s_['update'], s_['exit']))
        L.append('')
        atk = [a for a in spec['attacks'] if a.get('state') == s_['id']] if not sad.get('fn') else []
        if atk:
            L.append('- **attack armed on entry** (param group 2): ' + '; '.join(atk_text(a) for a in atk))
        mots = []
        for role in ('enter', 'update', 'exit'):
            for d in s_['summary'].get(role + '_derived', []):
                if d.get('motion') and d['motion'] not in mots:
                    mots.append(d['motion'])
        for m in mots:
            sc = spec['acmd'].get(m, {}).get('attack')
            if sc:
                L.append('- **ACMD hitboxes** of motion %s: %s' % (m, '; '.join(
                    '%s(%s)' % (c_[0], ', '.join(str(x) for x in c_[1:])) for c_ in sc.get('main', []))))
        for role in ('enter', 'update', 'exit'):
            items = s_['summary'].get(role)
            if not items:
                continue
            L.append('- %s:' % role)
            L += md_items(items, '  ')
            dv = [d for d in s_['summary'].get(role + '_derived', []) if d.get('via') and
                  d['cat'] in ('state', 'motion', 'attack', 'spawn', 'visibility', 'lifecycle')]
            if dv:
                L.append('  - through helpers: ' + '; '.join(short_item(d) + ' (via %s)' % '>'.join(d['via'])
                                                              for d in dv[:24]) + (' ...' if len(dv) > 24 else ''))
        L.append('')
    if spec.get('vtable_functions'):
        L.append('## Vtable overrides')
        L.append('')
        for k, v in sorted(spec['vtable_functions'].items(), key=lambda kv: int(kv[0])):
            its = [i for i in v['items'] if i['cat'] != 'param']
            if not its:
                continue
            L.append('- slot %s %s (0x%s):' % (k, v['name'], v['fn']))
            L += md_items(v['items'], '  ', limit=40)
        L.append('')
    if spec.get('helpers'):
        L.append('## Helpers')
        L.append('')
        for f, its in spec['helpers'].items():
            its2 = [i for i in its if i['cat'] != 'param']
            if not its2:
                continue
            L.append('- L%s:' % f)
            L += md_items(its, '  ', limit=40)
        L.append('')
    if spec['acmd']:
        L.append('## ACMD (3DS animcmd)')
        L.append('')
        for m, d in spec['acmd'].items():
            for typ, sc in d.items():
                for key, cmds in sc.items():
                    L.append('- %s %s%s: %s' % (m, typ, '' if key == 'main' else '.' + key, '; '.join(
                        '%s(%s)' % (c_[0], ', '.join(str(x) for x in c_[1:])) for c_ in cmds)))
        L.append('')
    return '\n'.join(L) + '\n'


def atk_text(a):
    f = lambda x: fmtf(x) if isinstance(x, float) else x
    return 'entry %d: power %s angle %s kbg %s fkb %s bkb %s size %s node %s%s offset (%s, %s, %s)' % (
        a['entry'], f(a.get('power')), f(a.get('angle')), f(a.get('kbg')), f(a.get('fkb')), f(a.get('bkb')),
        f(a.get('size')), f(a.get('node')), ' (%s)' % a['bone'] if a.get('bone') else '', f(a.get('x')),
        f(a.get('y')), f(a.get('z')))


def short_item(it):
    if it['cat'] == 'state':
        return '-> state %s' % it.get('state', '?')
    if it.get('motion'):
        return 'motion %s' % it['motion']
    if it.get('mesh'):
        return 'mesh %s=%s' % (it['mesh'], it['args'][1] if len(it['args']) > 1 else '?')
    if 'store' in it:
        return '%s = %s' % (it['store'], it['val'])
    return '%s(%s)' % (it.get('call'), ', '.join(map(str, it.get('args', []))))


def md_items(items, ind, limit=None):
    L = []
    prev = None
    n = 0
    for it in items:
        if it['cat'] == 'param':
            continue
        if it['cat'] == 'field' and not it.get('store', '').startswith('this+0x1'):
            continue
        g = (' [if ' + ' && '.join(it['guard'][-3:]) + ']') if it.get('guard') else ''
        if 'if' in it:
            g += ' [when %s]' % it['if']
        if 'store' in it:
            line = '%s- %s `%s = %s`%s' % (ind, it['cat'], it['store'], it['val'], g)
        else:
            extra = ''
            if it.get('motion'):
                extra = ' = ' + it['motion']
            if it.get('mesh'):
                extra = ' = ' + it['mesh']
            if 'state' in it:
                extra = ' -> state %s' % it['state']
            line = '%s- %s `%s(%s)`%s%s' % (ind, it['cat'], it['call'], ', '.join(map(str, it['args'])), extra, g)
        if line == prev:
            continue
        prev = line
        L.append(line)
        n += 1
        if limit and n >= limit:
            L.append(ind + '- ...')
            break
    return L


HAND_NOTES = {}


def dump_json(spec):
    """one top-level key a line group: states / functions one entry a line, the rest compact"""
    out = ['{']
    keys = list(spec)
    for i, k in enumerate(keys):
        v = spec[k]
        end = ',' if i < len(keys) - 1 else ''
        if isinstance(v, dict) and k in ('functions', 'helpers', 'vtable_functions', 'vtable_slots', 'acmd',
                                         'hand_read'):
            out.append(' %s: {' % json.dumps(k))
            ks = list(v)
            for j, kk in enumerate(ks):
                out.append('  %s: %s%s' % (json.dumps(kk), json.dumps(v[kk], separators=(',', ':')),
                                           ',' if j < len(ks) - 1 else ''))
            out.append(' }' + end)
        elif isinstance(v, list) and k in ('states', 'motions', 'attacks'):
            out.append(' %s: [' % json.dumps(k))
            for j, x in enumerate(v):
                out.append('  %s%s' % (json.dumps(x, separators=(',', ':')), ',' if j < len(v) - 1 else ''))
            out.append(' ]' + end)
        else:
            out.append(' %s: %s%s' % (json.dumps(k), json.dumps(v, separators=(',', ':')), end))
    out.append('}')
    return '\n'.join(out) + '\n'


def classify(spec):
    """rough tags from the calls the behaviour makes (README table; hand_read.class is the checked one)"""
    calls = set()
    for F in spec.get('functions', {}).values():
        calls.update(F['calls'])
    kin = set()
    for F in spec.get('functions', {}).values():
        for b in F['blocks']:
            for e in b['events']:
                if e.get('fn') == 'EnemyKineticModuleImpl::change_kinetic' and e['args']:
                    kin.add(e['args'][0])
    tags = []
    if any(c.startswith('EnemyGroundLineTraceModuleImpl') for c in calls):
        tags.append('crawler')
    elif any(c.startswith('EnemyAerialModuleImpl') for c in calls) and not ({'1', '3', '10'} & kin):
        tags.append('flyer')
    elif 'Behavior::move' in calls or {'1', '3', '10'} & kin:
        tags.append('walker')
    else:
        tags.append('stationary')
    if any(c.startswith('Behavior::generate_article') for c in calls):
        tags.append('shooter')
    if any(c.startswith('Behavior::create_enemy') or c.startswith('Behavior::create_reserved_enemy') or
           c.startswith('EnemyManager::create_request') for c in calls):
        tags.append('spawner')
    if any(c.startswith('LinkModuleImpl::link') for c in calls):
        tags.append('links')
    if spec.get('acmd') and any('attack' in v for v in spec['acmd'].values()):
        tags.append('acmd-hitboxes')
    if len(spec.get('states', [])) >= 20:
        tags.append('large')
    return tags


def load_hand_notes(path):
    if os.path.exists(path):
        return json.load(open(path))
    return {}


WIIU = {   # Wii U addresses of the same framework functions (docs/smash-run-port.md, step 2 research), where known
    'Behavior::change_motion_state': '0x02DB420C', 'Behavior::change_script_state': '0x02DB4184',
    'Behavior::set_motion_label': '0x02DB5B08', 'Behavior::set_damage_motion_label': '0x02DB5AD8',
    'Behavior::Behavior': '0x02DB2DF0', 'Behavior::get_viewout_type': '0x02DB34C8',
    'BehaviorImpl::notify_on_damage': '0x026A3564', 'BehaviorImpl::notify_on_capture_inner': '0x026A3D0C',
    'BehaviorImpl::notify_on_common_thrown': '0x026A4648', 'BehaviorImpl::notify_on_capture_cut': '0x026A46F4',
    'Behavior::notify_on_remove': '0x02DB40E4', 'Behavior::get_turn_type': '0x02DB46BC',
    'Behavior::is_down': '0x02DB4700', 'Behavior::update_hp': '0x02DB4D74', 'Behavior::damage_turn': '0x02DB4E84',
    'Behavior::set_attack_data': '0x02DB58B8', 'Behavior::set_attack_power': '0x02DB59EC',
    'Behavior::set_lr': '0x026A780C', 'Behavior::reverse_lr': '0x026A7A20',
    'Behavior::sync_lr_and_direction': '0x026A7BD8', 'Behavior::center_node': '0x026A7C70',
    'BehaviorImpl::clung_node': '0x026A451C', 'BehaviorImpl::change_state_base': '0x026A3A44',
    'BehaviorImpl::change_state_interrupt_base': '0x026A3AD4', 'Behavior::get_nearest_target': '0x026A7008',
    'Behavior::check_turn_to_target': '0x026A6984', 'Behavior::search_target': '0x026A70FC',
    'Behavior::search_interval': '0x026A706C', 'Behavior::play_se': '0x026A96EC',
    'Behavior::success_by_percent': '0x026A8618', 'Behavior::set_rhombus': '0x026A65BC',
    'EffectModuleImpl::req': '0x02C29D10', 'operator new': '0x03374578', 'Behavior::move': '0x026A66D0',
    'Behavior::check_wall': '0x026A68E4', 'Behavior::check_cliff_lr': '0x026A6D88',
    'GroundModuleImpl::set_attach_ground': '0x02C37C6C', 'GroundModuleImpl::is_touch': '0x02C38A24',
    'EnemyKineticModuleImpl::change_kinetic': '0x02DBE00C', 'Behavior::bullet': '0x02DB5158',
    'EnemyManager::remove_enemy_by_id': '0x02D9C0E0', 'Behavior::create_attack_data': '0x02DB572C',
    'AttackModuleImpl::set_attack': '0x02C086A8', 'AttackModuleImpl::clear_all': '0x02C08324',
    'Behavior::initialize_after': '0x02DB4AC8', 'Behavior::request_follow_effect': '0x026A9584 / 0x026A95F8',
    'MotionModuleImpl::change_motion': '0x02C5D730',
}


def write_readme(path, specs, symbols):
    """fills the generated sections of README.md (between <!-- generated:NAME --> markers)"""
    txt = open(path).read() if os.path.exists(path) else ''
    rows = ['| idx | kind | class | states | contact attacks (P2: state:power) | ACMD hitboxes | articles | '
            'set_attack_data | hand-read |', '|---|---|---|---|---|---|---|---|---|']
    for sp in specs:
        hr = sp.get('hand_read') or {}
        cls = hr.get('class') or '+'.join(sp.get('tags', [])) or '-'
        if not sp.get('behavior_class'):
            cls = 'no behaviour in enemy_fs.cro'
        atk = ', '.join('%s:%s' % (a.get('state'), a.get('power')) for a in sp.get('attacks', []))
        ac = ', '.join(m for m, v in sp.get('acmd', {}).items() if 'attack' in v)
        wp = ', '.join(sp.get('articles', {}).get('weapons', {}))
        sad = sp.get('vtable_slots', {}).get('45', {})
        sadt = 'default' if not sad.get('fn') else ('none (empty)' if sad.get('returns') == 'nop' else
                                                    'own 0x%s' % sad['fn'])
        if not sp.get('behavior_class'):
            sadt = '-'
        rows.append('| %s | [%s](%s.md) | %s | %d | %s | %s | %s | %s | %s |' % (
            sp['kind_index'], sp['kind'], sp['kind'], cls, len(sp.get('states', [])), atk or '-', ac or '-',
            wp or '-', sadt, 'yes' if hr else ''))
    used = {}
    for sp in specs:
        for F in sp.get('functions', {}).values():
            for c_ in F['calls']:
                if not c_.startswith('L'):
                    used[c_] = used.get(c_, 0) + 1
    sym = {}
    if symbols and os.path.exists(symbols):
        for l in open(symbols):
            a, n = l.split(' ', 1)
            sym.setdefault(short_name(n.strip()), []).append(a)
    frows = ['| function (enemy_fs import) | 3DS code.bin | Wii U | functions using it |', '|---|---|---|---|']
    for n in sorted(used, key=lambda x: (-used[x], x)):
        if n.startswith('__') or n.startswith('lib::') or n.startswith('std::') or n.startswith('nn::'):
            continue
        frows.append('| `%s` | %s | %s | %d |' % (n, ' / '.join('0x' + x for x in sym.get(n, [])[:2]) or '-',
                                                  WIIU.get(n, ''), used[n]))
    for name, body in (('kinds', '\n'.join(rows)), ('framework', '\n'.join(frows))):
        a_, b_ = '<!-- generated:%s -->' % name, '<!-- /generated:%s -->' % name
        if a_ in txt and b_ in txt:
            txt = txt[:txt.index(a_) + len(a_)] + '\n' + body + '\n' + txt[txt.index(b_):]
        else:
            txt += '\n%s\n%s\n%s\n' % (a_, body, b_)
    open(path, 'w').write(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cro', required=True)
    ap.add_argument('--params', required=True)
    ap.add_argument('--enemy-root', required=True)
    ap.add_argument('--out-json', default=os.path.join(HERE, '..', 'reference', 'smashrun_enemy_specs'))
    ap.add_argument('--out-md', default=os.path.join(HERE, '..', 'docs', 'smash-run-enemies'))
    ap.add_argument('--hand-read', default=os.path.join(HERE, '..', 'reference', 'smashrun_enemy_specs',
                                                        'hand_read.json'),
                    help='hand-read conclusions per kind, merged into the outputs as hand_read / Reading')
    ap.add_argument('--no-functions', action='store_true', help='leave the per-function block listings out')
    ap.add_argument('--symbols', help="static_symbols.txt (code.bin names, tools/s3ds_unpack.py symbols) for the "
                                      "README's framework table")
    ap.add_argument('--readme', action='store_true', help='also fill the generated tables of OUT_MD/README.md')
    ap.add_argument('kinds', nargs='*')
    args = ap.parse_args()
    HAND_NOTES.update(load_hand_notes(args.hand_read))
    c = Cro(args.cro)
    A0 = Analyzer(c, {'kind': None, 'params': {}, 'motions': [], 'meshes': [], 'vt': {}})
    layouts = param_layouts(A0)
    vts = find_vtables(c)
    os.makedirs(args.out_json, exist_ok=True)
    os.makedirs(args.out_md, exist_ok=True)
    done = []
    for kind in args.kinds or KINDS:
        spec = run_kind(c, kind, args, layouts, vts)
        spec['tags'] = classify(spec)
        if kind in HAND_NOTES:
            spec['hand_read'] = HAND_NOTES[kind]
        if args.no_functions:
            spec.pop('functions', None)
        with open(os.path.join(args.out_json, kind + '.json'), 'w') as f:
            f.write(dump_json(spec))
        with open(os.path.join(args.out_md, kind + '.md'), 'w') as f:
            f.write(md_kind(spec))
        print('%-16s states %2d motions %2d attacks %d funcs %d' % (kind, len(spec['states']), len(spec['motions']),
                                                                     len(spec['attacks']),
                                                                     len(spec.get('functions', {}))))
        if args.readme:
            done.append(spec)
    if args.readme:
        write_readme(os.path.join(args.out_md, 'README.md'), done, args.symbols)


if __name__ == '__main__':
    main()
