#!/usr/bin/env python3
"""Tests Corrin's trail texture ids (tools/kamui_trail_cave.py, tools/kamui_trail_build.py, Sm4shCommand v1.7.31).

  python3 tools/kamui_trail_cave_test.py BASE.rpx WORK_DIR [--sm4shcommand RUN_DIR]

BASE.rpx: an executable with tools/trail_table_cave.py's table (ids 1 - 271), e.g. exe_v46z_ui10, or a release that has
  272 / 273 already (exe_v46z_gkb21+, gekkouga_clone_cave.py's ktrail): then applying it must change no byte.
WORK_DIR: scratch space (the patched executable is written there, about 22 MB, and removed).
--sm4shcommand RUN_DIR: a built Sm4shCommand (SM4SHCommand.exe, SALT.dll, Events.cfg, Tooltips): compiles
  tools/Sm4shCommand/trail_textures_test.cs there (TtTest.exe) and runs it.

Checks:
- the executable: kamui_trail_cave.py over BASE gives a table whose ids 1 - 271 are BASE's names and 272 / 273 are
  TexKamuiSwordTraceCyan / Add; the game's own lookup (the trail set-up's lis / slwi / addi / lwzx at 0x032F53A4 -
  0x032F53B8, run in unicorn) reads those names for ids 1, 240, 271, 272, 273; nothing else in the file changes but
  the table's words in [0x04B9B000, 0x04B9C000) (weapon_expand_append.py's space from 0x04B9C000 untouched);
  re-applying it over its own output, or folding KAMUI_TRAILS into trail_table_cave.NEW_TRAILS, gives the same words;
- Sm4shCommand's names (TrailNames.cs) are BASE's 259 then the ports' and Corrin's, as kamui_trail_cave.names();
  Tooltips/trails.txt (make_tooltips.py) names 272 / 273, Corrin's own entries with a warning about the executable;
- the textures in fighters/kamui/effect/kamui/trail: kamui_trail_build.py's output from fighters/kamui/trail_src/
  cyan_v1.png, byte for byte; NTP3 128 x 128, one mip, texture id 0, DXT5 / DXT1 (her vanilla pair's layout), the
  picture's colours (a light cyan, opaque at the blade's end, transparent at the tail's).
"""
import os
import struct
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kamui_trail_build as KB  # noqa: E402
import kamui_trail_cave as KT  # noqa: E402
import nut  # noqa: E402
import rpx_patch  # noqa: E402
import trail_table_cave as T  # noqa: E402

FAILS = []
TRAIL_DIR = os.path.join(REPO, 'fighters', 'kamui', 'effect', 'kamui', 'trail')
SRC = os.path.join(REPO, 'fighters', 'kamui', 'trail_src', 'cyan_v1.png')
S4C = os.path.join(HERE, 'Sm4shCommand')


def check(what, ok, detail=''):
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': ' + str(detail)))
    if not ok:
        FAILS.append(what)


class Exe:
    def __init__(self, path):
        self.d, _shoff, _ent, self.secs = rpx_patch.load(path)
        self.cache = {}

    def u32(self, a):
        return rpx_patch.read_u32(self.d, self.secs, a, self.cache)

    def bytes(self, a, n):
        return b''.join(self.u32(a + 4 * i).to_bytes(4, 'big') for i in range((n + 3) // 4))[:n]

    def cstr(self, a):
        out = b''
        while True:
            w = self.u32(a & ~3).to_bytes(4, 'big')
            for i in range(a & 3, 4):
                if w[i] == 0:
                    return out.decode('ascii', 'replace')
                out += bytes([w[i]])
            a = (a & ~3) + 4

    def sections(self):
        return [bytes(rpx_patch.section_data(self.d, s)) if s[5] else b'' for s in self.secs]


def lookup(exe, ids):
    """the names the game's own set-up code reads for texture ids: its instructions 0x032F53A4 - 0x032F53B8 (lis r25 /
    slwi r6, r0, 2 / lis r26 / addi r25 / addi r26 / lwzx r5, r6, r25) run in unicorn with r0 = the id"""
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_5
    code = 0x032F5000
    lis, addi = exe.u32(0x032F53A4), exe.u32(0x032F53B0)
    base = ((lis & 0xFFFF) << 16) + ((addi & 0xFFFF) ^ 0x8000) - 0x8000
    page = base & ~0xFFF
    out = {}
    for i in ids:
        uc = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
        uc.mem_map(code, 0x1000)
        uc.mem_write(code, exe.bytes(code, 0x1000))
        if page != code:
            uc.mem_map(page, 0x2000)
            uc.mem_write(page, exe.bytes(page, 0x2000))
        uc.reg_write(UC_PPC_REG_0, i)
        uc.emu_start(0x032F53A4, 0x032F53BC)
        out[i] = exe.cstr(uc.reg_read(UC_PPC_REG_5))
    return out


def test_exe(base_rpx, work):
    os.makedirs(work, exist_ok=True)
    out_rpx = os.path.join(work, 'kamui_trail_test.rpx')
    check('ids: TexKamuiSwordTraceCyan 272, TexKamuiSwordTraceCyanAdd 273',
          (KT.trail_id('TexKamuiSwordTraceCyan'), KT.trail_id('TexKamuiSwordTraceCyanAdd')) == (272, 273))
    base = Exe(base_rpx)
    check('base: has trail_table_cave.py\'s table (lis / addi -> 0x04B9AFFC)',
          (base.u32(T.LIS), base.u32(T.ADDI)) == (0x3F2004BA, 0x3B39AFFC), (hex(base.u32(T.LIS)), hex(base.u32(T.ADDI))))
    base_names = [base.cstr(base.u32(T.CAVE + 4 * i)) for i in range(T.OLD_N + len(T.NEW_TRAILS))]
    check('base: 271 names, the last TexMasterSwordTraceAdd', base_names[-1] == 'TexMasterSwordTraceAdd', base_names[-3:])
    patches = KT.build(base_rpx)
    argv = KT.args(patches)
    r = subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), base_rpx, out_rpx] + argv,
                       capture_output=True, text=True)
    check('rpx_patch.py applies it', r.returncode == 0, r.stderr[-500:])
    try:
        new = Exe(out_rpx)
        names = [new.cstr(new.u32(T.CAVE + 4 * i)) for i in range(T.OLD_N + len(KT.names()))]
        check('ids 1 - 271: the base\'s names', names[:len(base_names)] == base_names)
        check('ids 272 / 273: the new names', names[len(base_names):] == ['TexKamuiSwordTraceCyan', 'TexKamuiSwordTraceCyanAdd'],
              names[len(base_names):])
        got = lookup(new, [1, 240, 241, 271, 272, 273])
        check('the game\'s lookup code: 1 / 240 / 241 / 271 / 272 / 273', got == {
            1: 'TexLinkSwordTrace', 240: 'TexKamuiSwordTrace', 241: 'TexKamuiSwordTraceAdd', 271: 'TexMasterSwordTraceAdd',
            272: 'TexKamuiSwordTraceCyan', 273: 'TexKamuiSwordTraceCyanAdd'}, got)
        got0 = lookup(base, [240, 271])
        check('... the same code on the base: 240 / 271 as before', got0 == {240: 'TexKamuiSwordTrace',
                                                                              271: 'TexMasterSwordTraceAdd'}, got0)
        end = max(patches)
        check('the table + strings end below 0x04B9C000 (weapon_expand_append.py\'s space)', end < T.GROW, hex(end))
        a, b = base.sections(), new.sections()
        w272 = base.u32(T.CAVE + 4 * 271)          # (past a 271-name table: its strings' first bytes)
        if T.CAVE <= w272 < T.GROW and base.cstr(w272) == 'TexKamuiSwordTraceCyan':
            # a release that has it already (exe_v46z_gkb21+: gekkouga_clone_cave.py's ktrail): nothing to add
            check('the base has ids 272 / 273 already (gkb21+): applying it changes no byte',
                  open(base_rpx, 'rb').read() == open(out_rpx, 'rb').read())
        else:
            # (.bss has no data in the file; the CRC table changes with the code section's CRC: its word 4 x index)
            kinds = [s[1] for s in base.secs]
            changed = [i for i in range(len(a)) if a[i] != b[i] and kinds[i] not in (8, rpx_patch.SHT_RPL_CRCS)]
            text = [i for i, s in enumerate(base.secs) if s[3] <= T.CAVE < s[3] + len(a[i] or b'')]
            check('only the code section changes', changed == text, (changed, text))
            crcs = kinds.index(rpx_patch.SHT_RPL_CRCS)
            cw = [k for k in range(0, len(a[crcs]), 4) if a[crcs][k:k + 4] != b[crcs][k:k + 4]]
            check('... and its CRC (the CRC table\'s only change)', cw == [4 * t for t in text], cw)
            if changed == text and text:
                i = text[0]
                addr0 = base.secs[i][3]
                x, y = np.frombuffer(a[i], np.uint8), np.frombuffer(b[i][:len(a[i])], np.uint8)
                diff = np.nonzero(x != y)[0]
                lo, hi = (addr0 + diff.min(), addr0 + diff.max()) if len(diff) else (0, 0)
                check('... only bytes in [0x04B9B000, 0x04B9C000) (lis / addi unchanged)',
                      len(b[i]) == len(a[i]) and T.CAVE <= lo and hi < T.GROW, (hex(lo), hex(hi), len(a[i]), len(b[i])))
                old_end = T.CAVE + 4 * (T.OLD_N + len(T.NEW_TRAILS)) + sum(len(n) + 1 for n in T.NEW_TRAILS)
                tail = x[old_end - addr0:T.GROW - addr0]
                check('... the words it takes past the old table were zero', not tail.any())
        import import_call_check
        bad = import_call_check.direct_import_calls(base_rpx, patches)
        check('import_call_check: no word is a call to an import', bad == [], bad)
        check('re-applied over its own output: the same words', KT.build(out_rpx) == patches)
        saved = T.NEW_TRAILS
        T.NEW_TRAILS = saved + KT.KAMUI_TRAILS
        try:
            check('folded into trail_table_cave.NEW_TRAILS: the same words, ids and arguments',
                  T.build(base_rpx) == patches and KT.trail_id('TexKamuiSwordTraceCyan') == 272 and
                  T.args(T.build(base_rpx)) == argv)
        finally:
            T.NEW_TRAILS = saved
        return base_names
    finally:
        if os.path.exists(out_rpx):
            os.remove(out_rpx)


def test_sm4shcommand(base_names):
    import re
    text = open(os.path.join(S4C, 'SM4SHCommand', 'Classes', 'Viewer', 'TrailNames.cs'), encoding='utf-8-sig').read()
    body = text[text.index('Names = {'):text.index('};', text.index('Names = {'))]
    names = re.findall(r'"([^"]+)"', body)
    check('TrailNames.cs: the base\'s 271 then 272 / 273', names == base_names + KT.KAMUI_TRAILS, (len(names), names[-4:]))
    check('TrailNames.cs: kamui_trail_cave.names() after the game\'s 259', names[T.OLD_N:] == KT.names())
    tips = open(os.path.join(S4C, 'SM4SHCommand', 'Tooltips', 'trails.txt'), encoding='utf-8').read()
    check('Tooltips/trails.txt: 0x110 / 0x111 named', '0x00000110 = TexKamuiSwordTraceCyan |' in tips and
          '0x00000111 = TexKamuiSwordTraceCyanAdd |' in tips)
    kam = tips[tips.index('[fighter kamui]'):]
    check('Tooltips/trails.txt: Corrin\'s own entries (240 / 241, 272 / 273 with the executable they need)',
          '0x000000F0 = TexKamuiSwordTrace |' in kam and 'NEW (v1.7.31)' in kam and 'kamui_trail_cave.py\'s table' in kam)
    check('Tooltips / help: name the executable that has 272 / 273 (exe_v46z_gkb21 or later)',
          'Needs cross_f.rpx exe_v46z_gkb21 or later' in kam and 'exe_v46z_gkb21 or later' in
          open(os.path.join(S4C, 'SM4SHCommand', 'Events.cfg'), encoding='utf-8').read())
    cfg = open(os.path.join(S4C, 'SM4SHCommand', 'Events.cfg'), encoding='utf-8').read()
    check('Events.cfg: Sword_Glow\'s help and cyan example (make_events_cfg.py)',
          'Help: ## Texture ids (changed in v1.7.31: 272 / 273 are new)' in cfg and
          'Example: Sword_Glow(Texture1=272, Texture2=273' in cfg)


def test_textures():
    trail, add = KB.textures(KB.load(SRC))
    for name, data in (('TexKamuiSwordTraceCyan', trail), ('TexKamuiSwordTraceCyanAdd', add)):
        path = os.path.join(TRAIL_DIR, name + '.nut')
        check('%s.nut: kamui_trail_build.py\'s output from cyan_v1.png' % name,
              os.path.exists(path) and open(path, 'rb').read() == data)
    t = nut.read_ntp3(trail)
    a = nut.read_ntp3(add)
    check('trail: NTP3, one texture, id 0, DXT5, 128 x 128, one mip', (len(t), t[0][0], t[0][1], t[0][2].shape) ==
          (1, 0, 2, (128, 128, 4)) and trail[0x21] == 1 and len(trail) == 0x60 + 0x4000)
    check('Add: NTP3, one texture, id 0, DXT1, 128 x 128, one mip', (len(a), a[0][0], a[0][1], a[0][2].shape) ==
          (1, 0, 0, (128, 128, 4)) and add[0x21] == 1 and len(add) == 0x60 + 0x2000)
    img = t[0][2].astype(int)
    check('trail: transparent at the tail end (left), opaque at the blade (right)',
          img[:, :4, 3].max() < 40 and img[:, 96:, 3].min() > 240, (img[:, :4, 3].max(), img[:, 96:, 3].min()))
    mid = img[64, 110, :3]
    check('trail: light cyan at the blade (blue >= green > red)', mid[2] >= mid[1] > mid[0] and mid[2] > 200, mid)
    ad = a[0][2].astype(int)
    check('Add: the same hue, dimmer (gain %.1f), opaque' % KB.ADD_GAIN,
          ad[..., 3].min() == 255 and ad[64, 110, 2] < img[64, 110, 2] * 0.45 and ad[64, 110, 2] > 30, ad[64, 110])
    return img


def test_tt(run_dir, img):
    import shutil
    import tempfile
    mono = '/usr/lib/mono/4.5'
    exe = os.path.join(run_dir, 'TtTest.exe')
    r = subprocess.run(['dotnet', '/usr/lib/dotnet/sdk/8.0.134/Roslyn/bincore/csc.dll', '-nologo', '-out:' + exe,
                        '-nostdlib', '-r:' + os.path.join(run_dir, 'SALT.dll'), '-r:' + os.path.join(run_dir, 'SM4SHCommand.exe')] +
                       ['-r:%s/%s.dll' % (mono, n) for n in ('mscorlib', 'System', 'System.Core', 'System.Windows.Forms',
                                                             'System.Drawing', 'System.Data')] +
                       [os.path.join(S4C, 'trail_textures_test.cs')], capture_output=True, text=True)
    check('trail_textures_test.cs compiles', r.returncode == 0, (r.stdout + r.stderr)[-800:])
    if r.returncode:
        return
    tmp = tempfile.mkdtemp()
    try:
        root = os.path.join(tmp, 'fighter', 'kamui')
        os.makedirs(os.path.join(root, 'effect', 'kamui'))
        shutil.copytree(TRAIL_DIR, os.path.join(root, 'effect', 'kamui', 'trail'))
        x, y = 100, 64
        px = img[y, x]
        argb = '%02X%02X%02X%02X' % (px[3], px[0], px[1], px[2])
        r = subprocess.run(['mono', 'TtTest.exe', 'Events.cfg', root, str(x), str(y), argb], cwd=run_dir,
                           capture_output=True, text=True)
        print(r.stdout.rstrip())
        check('TtTest (Sm4shCommand): 0 failures', r.returncode == 0, r.stderr[-500:])
    finally:
        shutil.rmtree(tmp)


def main():
    argv = sys.argv[1:]
    run_dir = None
    if '--sm4shcommand' in argv:
        k = argv.index('--sm4shcommand')
        run_dir = argv[k + 1]
        argv = argv[:k] + argv[k + 2:]
    args = argv
    if len(args) != 2:
        sys.exit(__doc__)
    base_names = test_exe(args[0], args[1])
    test_sm4shcommand(base_names)
    img = test_textures()
    if run_dir:
        test_tt(run_dir, img)
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
