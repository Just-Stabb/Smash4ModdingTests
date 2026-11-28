#!/usr/bin/env python3
"""The executable patch as data (1.5, patchset.py): the Aroma plugin's patch file and the Cemu graphic pack, checked
against the patched rpx and run in the existing emulations.

  python3 tools/sm4shclonetool/tests/patchset_test.py PATCHED.rpx VANILLA.rpx WORK [PICKS]

PATCHED: an executable the tool patched (run_all's build 3); VANILLA: the executable it was patched from.
Checks:
- export: from VANILLA with PATCHED's registry; the same patch set from PATCHED itself (its vanilla view);
- the patch set applied at the tool's own base without veneers = PATCHED's memory image byte for byte (the code
  section, every data section), but for the marker block; its game words = the words PATCHED's marker records;
- the plugin file: read back = the patch set; its cave with the veneers undone = the rpx's cave;
- relocated (as the plugin places it, 0x00908000) and as Cemu evaluates the graphic pack (a 256-aligned cave at
  0x01800100): the hook emulations of extras_test.py (results call, sound aliases, Kirby's grant / resources / names /
  voice bound / copy scripts / copy bank) and random_select_test.py (refill, pick, remove, count, helper, stage
  refill), and the custom-move map 0x02A4D40C, all as on PATCHED; every game -> cave branch absolute, every veneer
  reaching its target;
- the plugin's own C code (aroma/src/patch_core.c, compiled for this PC with plugin_host.c): the same game words and
  cave bytes as patchset.apply; it refuses (and writes nothing) on a changed word, a damaged file, another title,
  another update version, a cave out of reach;
- the Cemu files parsed by a strict parser of Cemu's patches.txt (Cemuhook) syntax and expression rules (labels,
  ha() / lo(), 8 MB cave-relative addresses, module addresses inside its sections), rules.txt's [Definition];
  moduleMatches = Cemu's checksum of the vanilla file;
- ppcflow's register decoder against capstone on the game's code (when capstone is installed).
"""
import contextlib
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import patchset as PS  # noqa: E402
from sm4shclonetool import ppcflow as FL  # noqa: E402
from sm4shclonetool import clone_extras as CE  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402

FAILS = []
PLUGIN_BASE = 0x00908000            # where the plugin's buffer could be (Aroma's plugin area), = LINK mod 0x10000
CEMU_BASE = 0x01800100              # a Cemu code cave (256-aligned, from 0x01800000), not = LINK mod 0x10000


def check(what, got, want=True):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    if not ok:
        FAILS.append(what)
    return ok


class Overlay:
    """an executable's memory with words replaced and an extra block (the cave), for the emulations"""

    def __init__(self, vanilla, words, base, blob, reg):
        self.v = Rpx(vanilla)
        self.secs = self.v.secs
        self.words = dict(words)
        self.base, self.blob, self.reg = base, bytes(blob), reg

    def memory(self):
        out = {}
        for a, b in self.v.memory().items():
            b = bytearray(b)
            for w, v in self.words.items():
                if a <= w < a + len(b):
                    struct.pack_into('>I', b, w - a, v)
            out[a] = bytes(b)
        out[self.base] = self.blob
        return out

    def r32(self, a):
        if a in self.words:
            return self.words[a]
        if self.base <= a < self.base + len(self.blob):
            return struct.unpack_from('>I', self.blob, a - self.base)[0]
        return self.v.r32(a)


def plugin_image(ps, vanilla, base):
    """patchset.apply at base on the vanilla image: (game words, cave bytes)"""
    img = PS.Image(Rpx(vanilla))
    words = PS.apply(ps, img.read, img.write, base)
    cave = b''.join(struct.pack('>I', img.extra[base + i]) for i in range(0, ps.size, 4))
    return words, cave


# ---------------------------------------------------------------- the emulations on an overlay
def emulate(name, overlay, patched, vanilla, reg, picks):
    """extras_test.py / random_select_test.py and the custom-move map on the overlay; [failed check names]"""
    import extras_test as ET
    import random_select_test as RT
    real_find = X.find_marker
    real_rpx = (ET.Rpx, RT.Rpx)

    def find(x):
        if isinstance(x, Overlay):
            return x.base, {'registry': x.reg}
        return real_find(x)

    def rpx(path):
        return overlay if path == 'OVERLAY' else Rpx(path)

    def labels(m, v):
        lay = X.layout(PS.LINK, reg)
        _w, info = CE.build(v.w, reg['fighters'], R.KINDS.index, *lay['extras'])
        return {k: a - PS.LINK + overlay.base for k, a in info['labels'].items()}
    out = []
    X.find_marker = find
    ET.Rpx = RT.Rpx = rpx
    ml = ET.m_labels
    ET.m_labels = labels
    try:
        for mod, argv in ((ET, ['extras_test.py', 'OVERLAY', vanilla]), (RT, ['random_select_test.py', 'OVERLAY', str(picks)])):
            del mod.FAILS[:]
            buf = io.StringIO()
            sys.argv = argv
            with contextlib.redirect_stdout(buf):
                try:
                    mod.main()
                except SystemExit:
                    pass
            text = buf.getvalue()
            oks = sum(1 for x in text.splitlines() if x.startswith('ok'))
            check('%s: %s on the relocated image: %d ok, 0 failed' % (name, argv[0], oks),
                  ([x for x in text.splitlines() if x.startswith('FAIL')][:3], oks > 10), ([], True))
            out += list(mod.FAILS)
        # the custom-move map (run_all's customs_check), as on the patched rpx
        mo, mp = ET.M('OVERLAY'), ET.M(patched)

        def ids(m):
            got = []
            for i in range(64):
                m.run(0x02A4D40C, ET.RET, {3: i})
                got.append(m.r(3))
            return got
        check('%s: the custom-move map 0x02A4D40C, ids 0-63 = the patched rpx\'s' % name, ids(mo), ids(mp))
    finally:
        X.find_marker = real_find
        ET.Rpx, RT.Rpx = real_rpx
        ET.m_labels = ml
    return out


# ---------------------------------------------------------------- a strict Cemu patches.txt / rules.txt reader
class CemuError(Exception):
    pass


def cemu_eval(expr, syms):
    """Cemu's ExpressionParser on what the tool writes: numbers, symbols, + - * / and parentheses, ha() / hi() / lo()"""
    toks = re.findall(r'0[xX][0-9A-Fa-f]+|\d+|[A-Za-z_$][A-Za-z0-9_.$]*|[()+\-*/]|\S', expr)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def atom():
        t = take()
        if t is None:
            raise CemuError('expression ends early: %r' % expr)
        if t == '(':
            v = add()
            if take() != ')':
                raise CemuError('parentheses mismatch: %r' % expr)
            return v
        if t == '-':
            return -atom()
        if re.match(r'0[xX]', t):
            return int(t, 16)
        if t.isdigit():
            return int(t)
        if re.match(r'[A-Za-z_$]', t):
            if peek() == '(':
                take()
                v = add()
                if take() != ')':
                    raise CemuError('parentheses mismatch: %r' % expr)
                v &= 0xFFFFFFFF
                f = t.lower()
                if f in ('ha', 'ha16'):
                    return ((v >> 16) + ((v >> 15) & 1)) & 0xFFFF
                if f in ('hi', 'hi16'):
                    return (v >> 16) & 0xFFFF
                if f in ('lo', 'lo16'):
                    return v & 0xFFFF
                raise CemuError('unknown function %s' % t)
            if t not in syms:
                raise CemuError('unknown symbol %s' % t)
            return syms[t]
        raise CemuError('unexpected %r in %r' % (t, expr))

    def mul():
        v = atom()
        while peek() in ('*', '/'):
            op = take()
            r = atom()
            v = v * r if op == '*' else v // r
        return v

    def add():
        v = mul()
        while peek() in ('+', '-'):
            op = take()
            r = mul()
            v = v + r if op == '+' else v - r
        return v
    if '@' in expr:
        raise CemuError('the tool writes no @ modifiers (their meaning changed in Cemu 2.7): %r' % expr)
    v = add()
    if pos[0] != len(toks):
        raise CemuError('trailing tokens in %r' % expr)
    if not 0 <= v < 1 << 32:
        raise CemuError('%r = %d is not a 32-bit value' % (expr, v))
    return v


def cemu_parse(text, cave_base, sections):
    """patches.txt (Cemuhook format, as Cemu's ParseCemuhookPatchesTxtInternal reads it) -> (group, moduleMatches,
    {address: word} with the cave at cave_base, cave size). sections: [(lo, hi)] of the module's loaded sections."""
    group, matches, syms, entries = None, [], {}, []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw
        for c in ';#':
            if c in line:
                line = line[:line.index(c)]
        line = line.strip()
        if not line:
            continue
        if line.startswith('['):
            if not line.endswith(']') or group is not None:
                raise CemuError('line %d: a second group or a bad group line' % n)
            group = line[1:-1]
            continue
        if group is None:
            raise CemuError('line %d: outside a group' % n)
        m = re.match(r'(?i)moduleMatches\s*=\s*(.*)$', line)
        if m:
            for v in m.group(1).split(','):
                if not re.match(r'\s*0x[0-9A-Fa-f]{1,8}\s*$', v):
                    raise CemuError('line %d: moduleMatches value %r' % (n, v))
                matches.append(int(v, 16))
            continue
        m = re.match(r'0[xX]([0-9A-Fa-f]{1,8})\s*=\s*(.*)$', line)
        if m:
            addr, ins = int(m.group(1), 16), m.group(2).strip()
            d = re.match(r'(?i)\.int\s+(.+)$', ins)
            if not d or ',' in d.group(1):
                raise CemuError('line %d: only ".int <one expression>" is written: %r' % (n, ins))
            entries.append((n, addr, d.group(1)))
            continue
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$', line)
        if m:
            v = cemu_eval(m.group(2), {})
            syms[m.group(1)] = cave_base + v if v <= 8 * 1024 * 1024 else v     # _relocateAddress
            continue
        raise CemuError('line %d: invalid syntax %r' % (n, line))
    if group is None or not matches:
        raise CemuError('no group / no moduleMatches')
    words, size = {}, 0
    for n, addr, expr in entries:
        if addr <= 8 * 1024 * 1024:
            at = cave_base + addr
            size = max(size, addr + 4)
        elif any(lo <= addr and addr + 4 <= hi for lo, hi in sections):
            at = addr
        else:
            raise CemuError('line %d: 0x%08X is neither in the code cave nor in a section of the module' % (n, addr))
        if addr & 3:
            raise CemuError('line %d: unaligned word' % n)
        if at in words:
            raise CemuError('line %d: 0x%08X written twice' % (n, at))
        words[at] = cemu_eval(expr, syms)
    return group, matches, words, size


def rules_parse(text):
    if not text.startswith('[Definition]'):
        raise CemuError('rules.txt must start with [Definition]')
    kv = {}
    for line in text.split('\n')[1:]:
        if line.strip():
            k, _, v = line.partition('=')
            kv[k.strip()] = v.strip()
    for k in ('titleIds', 'name', 'path', 'version'):
        if k not in kv:
            raise CemuError('rules.txt has no %s' % k)
    tids = [int(t, 16) for t in kv['titleIds'].split(',')]
    if not kv['path'].startswith('"') or int(kv['version']) < 3:
        raise CemuError('rules.txt path / version')
    return tids, kv


# ---------------------------------------------------------------- the plugin's C code on this PC
def host_harness(work):
    exe = os.path.join(work, 'plugin_host')
    src = [os.path.join(HERE, 'plugin_host.c'), os.path.join(TOOL, 'aroma', 'src', 'patch_core.c')]
    cc = shutil.which('gcc') or shutil.which('cc')
    if not cc:
        return None
    r = subprocess.run([cc, '-O2', '-Wall', '-Wextra', '-Werror', '-o', exe] + src, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr)
        return False
    return exe


def run_host(exe, work, patch_bytes, memwords, cave_addr, tid, ver):
    pf, mf, cf = (os.path.join(work, n) for n in ('h.patch', 'h.mem', 'h.cave'))
    open(pf, 'wb').write(patch_bytes)
    open(mf, 'wb').write(b''.join(struct.pack('>II', a, w) for a, w in sorted(memwords.items())))
    r = subprocess.run([exe, pf, mf, '0x%X' % cave_addr, '0x%X' % tid, str(ver), cf], capture_output=True, text=True)
    out = {'w': []}
    for line in r.stdout.splitlines():
        k, _, v = line.partition(' ')
        if k == 'w':
            a, w = v.split()
            out['w'].append((int(a, 16), int(w, 16)))
        else:
            out[k] = v
    out['cave'] = open(cf, 'rb').read() if os.path.exists(cf) else b''
    for p in (pf, mf, cf):
        if os.path.exists(p):
            os.unlink(p)
    return out


# ---------------------------------------------------------------- ppcflow against capstone
def decoder_check(vanilla):
    try:
        import capstone
    except ImportError:
        print('     (capstone not installed: the decoder cross-check is skipped)')
        return
    import random
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    md.detail = True
    x = Rpx(vanilla)
    i = x.text_index()
    base, dat = x.secs[i][3], bytes(x.data(i))
    random.seed(5)
    stores = re.compile(r'^(st|stfs|stfd|psq_st|cmp|tw|dcb|icbi|mtcrf|mtspr|mtlr|mtctr|mtxer)')
    bad, n, unknown = [], 0, 0
    for o in random.sample(range(len(dat) // 4), 60000):
        a = base + 4 * o
        w = struct.unpack_from('>I', dat, 4 * o)[0]
        ins = list(md.disasm(dat[4 * o:4 * o + 4], a))
        if not ins:
            continue
        c = ins[0]
        mine = FL.decode(w, a)
        if mine[0] == 'unknown':
            unknown += 1
            continue
        if mine[0] not in ('op',) or c.mnemonic.startswith(('b', 'sc', 'rfi')) or w >> 26 in (4, 56, 57, 60, 61):
            continue                    # (opcodes 4, 56, 57, 60, 61: the Espresso's paired singles, which capstone reads as VSX)
        regs = []
        for op in c.operands:
            if op.type == 1:
                regs.append(c.reg_name(op.reg))
            elif op.type == 3 and op.mem.base and c.reg_name(op.mem.base):
                regs.append(('mem', c.reg_name(op.mem.base)))
        names = [r if isinstance(r, str) else r[1] for r in regs if r]
        imp_r = {c.reg_name(r) for r in c.regs_read} & FL.ALL
        imp_w = {c.reg_name(r) for r in c.regs_write} & FL.ALL
        gpr = [r for r in names if r in FL.ALL]
        mn = c.mnemonic.rstrip('.')
        if stores.match(mn):
            want_r, want_w = set(gpr), set()
            if re.match(r'^st.*u', mn) or re.match(r'^(stfsu|stfdu|psq_stu)', mn):
                want_w = {names[-1]} if mn.endswith('x') is False else {gpr[1]}
            if mn == 'stmw':
                want_r = {'r%d' % k for k in range(int(gpr[0][1:]), 32)} | set(gpr[1:])
        elif mn.startswith(('l', 'psq_l')) and mn not in ('li', 'lis'):
            dest = gpr[0] if not mn.startswith(('lf', 'psq_l')) else None
            want_r = set(gpr[1:]) if dest else set(gpr)
            want_w = {dest} if dest else set()
            if re.match(r'^l.*u', mn) and mn not in ('lmw',):
                want_w |= {gpr[1] if dest else gpr[0]}
            if mn == 'lmw':
                want_w = {'r%d' % k for k in range(int(gpr[0][1:]), 32)}
        elif mn in ('li', 'lis'):
            want_r, want_w = set(), {gpr[0]}
        elif mn in ('mflr', 'mfctr', 'mfcr', 'mftb', 'mfxer', 'mfspr'):
            want_r, want_w = set(), {gpr[0]}
        elif mn.startswith(('f', 'ps_', 'mtfsf', 'mffs', 'cr', 'mcrf', 'isync', 'sync', 'eieio', 'nop')):
            continue
        else:
            want_r, want_w = set(gpr[1:]), {gpr[0]} if gpr else set()
            if mn in ('rlwimi', 'insrwi', 'inslwi'):
                want_r.add(gpr[0])
            if mn in ('addi', 'addis') and len(c.operands) == 3 and c.operands[1].type == 2:
                want_r = set()
        want_r |= imp_r
        want_w |= imp_w
        mr, mw = set(mine[1]), set(mine[2])
        n += 1
        if (mr, mw) != (want_r, want_w) and (mr | {'r0'}, mw) != (want_r | {'r0'}, want_w):
            bad.append('%08X %s %s: %s / %s, capstone %s / %s' % (a, c.mnemonic, c.op_str, sorted(mr), sorted(mw),
                                                                 sorted(want_r), sorted(want_w)))
    check('ppcflow.decode: the registers read / written of %d sampled game instructions = capstone\'s operands '
          '(%d unknown to it, treated as reading everything)' % (n, unknown), bad[:4], [])


def main():
    patched, vanilla, work = sys.argv[1:4]
    picks = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
    os.makedirs(work, exist_ok=True)
    base, rec = X.find_marker(Rpx(patched))
    reg = rec['registry']

    # ---------------------------------------------------------------- export
    ps = PS.export(vanilla, reg, log=lambda s: print('     ' + s), work=work)
    ps2 = PS.export(patched, reg, log=lambda s: None, work=work)
    check('the patch set from the patched rpx (its vanilla view) = the one from the vanilla rpx',
          (ps2.sites == ps.sites, ps2.blob == ps.blob, ps2.cave_relocs == ps.cave_relocs), (True, True, True))
    check('its game words are the words the patched rpx\'s marker records (%d), with the same originals'
          % len(rec['orig']), {'0x%08X' % s['addr']: s['orig'] for s in ps.sites}, rec['orig'])

    # ---------------------------------------------------------------- byte for byte at the link base
    v, p = Rpx(vanilla), Rpx(patched)
    vm, pm = v.memory(), p.memory()
    sites = {s['addr']: s['new'] for s in ps.sites}
    diff, extra = [], 0
    for a, blob in pm.items():
        img = bytearray(vm.get(a, b''))
        img += bytes(len(blob) - len(img))
        for w, val in sites.items():
            if a <= w < a + len(blob):
                struct.pack_into('>I', img, w - a, val)
        if a <= PS.LINK < a + len(blob):
            o = PS.LINK - a
            img[o:o + len(ps.blob_link)] = ps.blob_link
            lo, hi = o, o + 0x4000                             # the marker block: the rpx's own
            img[lo:hi] = blob[lo:hi]
            extra = len(blob) - o
        if bytes(img) != blob:
            diff.append(hex(a))
    check('the patch set applied at 0x%08X (no veneers) = the patched rpx\'s memory image byte for byte (every '
          'section; the code space %d bytes, the cave %d of them; but for the marker block)' % (PS.LINK, extra,
                                                                                        len(ps.blob_link)), diff, [])
    check('the patched rpx changes no section the patch set doesn\'t know of', sorted(pm) == sorted(vm), True)

    # ---------------------------------------------------------------- the plugin file
    pb = PS.plugin_bytes(ps)
    rp = PS.read_plugin(pb)
    check('the plugin file (%d bytes) reads back: its words, cave relocations, cave, titles, v288' % len(pb),
          ([(s['addr'], s['orig'], s['new'], s['kind']) for s in rp.sites] ==
           [(s['addr'], s['orig'], s['new'], s['kind']) for s in ps.sites], rp.cave_relocs == ps.cave_relocs,
           rp.blob == ps.blob, list(rp.titles) == list(PS.TITLE_IDS), rp.version), (True, True, True, True, 288))
    bad = bytearray(pb)
    bad[100] ^= 1
    try:
        PS.read_plugin(bytes(bad))
        crc = False
    except PS.PatchError:
        crc = True
    check('a damaged plugin file is refused (CRC)', crc, True)
    # undo the veneers: every branch to a veneer, re-made to the veneer's target at the link base
    vt = {at: (t, r) for at, t, r in ps.veneers}
    und = bytearray(rp.blob[:len(ps.blob_link)])
    nb = 0
    for o in range(0, len(und), 4):
        w = struct.unpack_from('>I', und, o)[0]
        if w >> 26 == 18 and not w & 2:
            t = FL.decode(w, o)[3][0] & 0xFFFFFFFF
            if t in vt:
                struct.pack_into('>I', und, o, PS._b(PS.LINK + o, vt[t][0], w & 1))
                nb += 1
    check('the plugin file\'s cave with its %d veneered branches made direct again = the rpx\'s cave (%d veneers)'
          % (nb, len(ps.veneers)), bytes(und) == ps.blob_link, True)
    good = all(struct.unpack_from('>4I', rp.blob, at) == (0x3C000000 | (int(r[1:]) << 21) | (t >> 16),
                                                          0x60000000 | (int(r[1:]) * 0x210000) | (t & 0xFFFF),
                                                          0x7C0903A6 | (int(r[1:]) << 21), 0x4E800420)
               for at, t, r in ps.veneers)
    check('every veneer is lis / ori / mtctr / bctr to its target, its register dead there (ppcflow)', good, True)

    # ---------------------------------------------------------------- relocated: the plugin's placement
    words, cave = plugin_image(ps, vanilla, PLUGIN_BASE)
    rel = [s for s in ps.sites if s['kind'] == PS.K_REL24]
    absb = all(words[s['addr']] & 2 and (words[s['addr']] & 0x3FFFFFC) - PLUGIN_BASE ==
               (FL.decode(s['new'], s['addr'])[3][0] - PS.LINK) for s in rel)
    check('relocated to 0x%08X: the %d game -> cave branches are absolute (ba / bla) to the same cave offsets'
          % (PLUGIN_BASE, len(rel)), absb, True)
    ov = Overlay(vanilla, words, PLUGIN_BASE, cave, reg)
    emulate('plugin (0x%08X)' % PLUGIN_BASE, ov, patched, vanilla, reg, picks)

    # ---------------------------------------------------------------- the C code
    exe = host_harness(work)
    if exe is None:
        print('     (no C compiler: the plugin code check is skipped)')
    else:
        check('the plugin\'s patch_core.c builds on this PC (-Wall -Wextra -Werror)', bool(exe), True)
        mem = {s['addr']: v.r32(s['addr']) for s in ps.sites}
        tid = PS.TITLE_IDS[0]
        h = run_host(exe, work, pb, mem, PLUGIN_BASE - 0x8000, tid, 288)
        check('the plugin\'s C code at a buffer at 0x%08X: the cave at 0x%08X, the same %d game words (in order) and '
              'cave bytes as patchset.apply (%s)' % (PLUGIN_BASE - 0x8000, PLUGIN_BASE, len(words), h.get('msg')),
              (h.get('rc'), int(h.get('base', '0'), 16), h['w'] == [(s['addr'], words[s['addr']]) for s in ps.sites],
               h['cave'] == cave), ('0', PLUGIN_BASE, True, True))
        h2 = run_host(exe, work, pb, mem, 0x00A01234, tid, -1)
        w2, c2 = plugin_image(ps, vanilla, 0x00A08000)
        check('... a buffer at 0x00A01234 (unaligned): the cave at 0x00A08000, as patchset.apply there; update version '
              'unknown (-1): accepted', (h2.get('rc'), int(h2.get('base', '0'), 16),
                                         h2['w'] == [(s['addr'], w2[s['addr']]) for s in ps.sites], h2['cave'] == c2),
              ('0', 0x00A08000, True, True))
        m3 = dict(mem)
        m3[ps.sites[5]['addr']] ^= 4
        cases = [('a word of the game changed (another mod)', run_host(exe, work, pb, m3, PLUGIN_BASE, tid, 288), '6'),
                 ('a damaged file', run_host(exe, work, bytes(bad), mem, PLUGIN_BASE, tid, 288), '1'),
                 ('another title (Mario Kart 8)', run_host(exe, work, pb, mem, PLUGIN_BASE, 0x000500001010EC00, 288), '3'),
                 ('update v272', run_host(exe, work, pb, mem, PLUGIN_BASE, tid, 272), '4'),
                 ('a buffer past 0x02000000 (no absolute branch reaches it)',
                  run_host(exe, work, pb, mem, 0x02100000, tid, 288), '5')]
        for what, r, code in cases:
            check('the plugin\'s C code refuses %s (rc %s: %s) and writes nothing' % (what, r.get('rc'), r.get('msg')),
                  (r.get('rc'), r['w']), (code, []))

    # ---------------------------------------------------------------- Cemu
    text, multi = PS.cemu_patches(ps, [PS.V288_CEMU_HASH])
    rules = PS.cemu_rules(ps, 'Sm4shCloneTool_Clones')
    gd = os.path.join(work, 'graphicPacks', 'Sm4shCloneTool_Clones')
    os.makedirs(gd, exist_ok=True)
    open(os.path.join(gd, 'patches.txt'), 'w').write(text)
    open(os.path.join(gd, 'rules.txt'), 'w').write(rules)
    secs = [(a, a + len(b)) for a, b in vm.items()]
    try:
        group, matches, cw, csize = cemu_parse(text, CEMU_BASE, secs)
        tids, kv = rules_parse(rules)
        parsed = True
    except CemuError as e:
        print('     ' + str(e))
        parsed = False
    check('the Cemu patches.txt (%d lines) and rules.txt parse (Cemuhook format: one group, moduleMatches, '
          '_cave, .int lines with + / ha() / lo() expressions only)' % text.count('\n'), parsed, True)
    if parsed:
        h = PS.cemu_hash(vanilla) if Rpx(vanilla).image_digest() == X.V288_IMAGE else PS.V288_CEMU_HASH
        check('moduleMatches = Cemu\'s checksum of the v288 executable (0x%08X; computed from the file as Cemu\'s '
              'RPLLoader does)' % PS.V288_CEMU_HASH, matches, [h])
        check('rules.txt: the three regions\' title ids, version 6', (tids, kv['version']), (list(PS.TITLE_IDS), '6'))
        check('the Cemu cave\'s size (its last word) covers the cave and its veneers (%d bytes)' % ps.size, csize,
              ps.written[-1] + 4)
        check('no high half is shared by low halves in different 256-byte blocks (the cave works at any 256-aligned '
              'address Cemu gives)', multi, False)
        cwords = {a: w for a, w in cw.items() if not CEMU_BASE <= a < CEMU_BASE + csize}
        cblob = bytearray(ps.size)
        for a, w in cw.items():
            if CEMU_BASE <= a < CEMU_BASE + csize:
                struct.pack_into('>I', cblob, a - CEMU_BASE, w)
        # at a base = LINK (mod 0x10000) the graphic pack and the plugin give the same image
        _grp, _m, mw, msize = cemu_parse(text, PLUGIN_BASE, secs)
        same_w = {a: w for a, w in mw.items() if not PLUGIN_BASE <= a < PLUGIN_BASE + msize} == words
        mblob = bytearray(ps.size)
        for a, w in mw.items():
            if PLUGIN_BASE <= a < PLUGIN_BASE + msize:
                struct.pack_into('>I', mblob, a - PLUGIN_BASE, w)
        written = set(ps.written)
        same_c = all(mblob[o:o + 4] == cave[o:o + 4] for o in written)
        check('the graphic pack evaluated at 0x%08X = the plugin\'s image there (every game word, every written cave '
              'word)' % PLUGIN_BASE, (same_w, same_c), (True, True))
        ovc = Overlay(vanilla, cwords, CEMU_BASE, bytes(cblob), reg)
        emulate('Cemu (0x%08X)' % CEMU_BASE, ovc, patched, vanilla, reg, picks)

    decoder_check(vanilla)
    print('\n%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
