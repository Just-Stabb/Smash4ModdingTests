#!/usr/bin/env python3
"""Test fixture: a vanilla-like data folder for the tests, mostly symbolic links to the dumps it was built from.

  python3 tools/sm4shclonetool/tests/make_fixtures.py OUT_DIR VPARAM VUI VFIGHTER SOUND_CONFIG

OUT_DIR/data/
  param/                 -> VPARAM (the game's param folder, vanilla)
  ui/message/            -> VUI/message (vanilla melee.msbt)
  ui/replace/chr/        -> VUI/replace/chr (the vanilla portraits the dump has: Zero Suit Samus's, name plates)
  ui/replace/stage/      synthetic stage icons for BattleField_f (stage_10 / stage_00 / stage_30, BC3, made here:
                         no stage icons were in the dumps)
  fighter/fox/           -> VFIGHTER/fox (effect/ and model/body/c00/model.vbn: all the dump has of Fox)
  fighter/szerosuit/     -> VFIGHTER/szerosuit with model/ cut to body/c00 and the articles (disk space)
  stage/melee|end/BattleField_f/   synthetic (a few small files named like the stage's: no stage folders in the dumps)
  sound/config/          SOUND_CONFIG's bgm_fighter.fbb / commonsoundtable.csb cut to the game's record counts
                         (58 / 62: a modded copy's first records, the vanilla ones)
OUT_DIR/png/             test portraits / icons (PNG)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import textures as T  # noqa: E402


def link(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.lexists(dst):
        os.symlink(os.path.abspath(src), dst)


def link_tree(src, dst, skip=lambda rel: False):
    for root, _ds, fs in os.walk(src):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, src)
            if not skip(rel):
                link(p, os.path.join(dst, rel))


def png(path, text, size, colour):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', size, colour + (255,))
    d = ImageDraw.Draw(im)
    d.ellipse((size[0] * 0.1, size[1] * 0.1, size[0] * 0.9, size[1] * 0.9), outline=(255, 255, 255, 255),
              width=max(2, size[0] // 24))
    d.text((size[0] * 0.18, size[1] * 0.42), text, fill=(255, 255, 255, 255))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def synth_chara_lm(path, counts, layout):
    """a minimal Lumen file with the face-layout sprite tools/chara_layout.py reads: frame num_NNN for each count,
    face_001..face_NNN placed by layout(n) -> [(x, y, scale)] (the CSS layouts the tool reads)"""
    syms = [''] + ['num_%03d' % c for c in counts] + ['face_%03d' % i for i in range(1, max(counts) + 1)]
    sid = {n: i for i, n in enumerate(syms)}
    body = struct.pack('>I', len(syms))
    for n in syms:
        b = n.encode()
        body += struct.pack('>I', len(b)) + b + b'\0' * (((len(b) + 4) & ~3) - len(b))
    tags = [(0xF001, body)]
    xf = []
    frames = []
    for fi, c in enumerate(counts):
        places = []
        for i, (x, y, sc) in enumerate(layout(c), 1):
            xf.append((sc, 0.0, 0.0, sc, x, y))
            places.append(struct.pack('>8I', 1, 0, 0, sid['face_%03d' % i], 1 << 16, i << 16, 0, len(xf) - 1))
        frames.append((fi, c, places))
    tags.append((0xF003, struct.pack('>I', len(xf)) + b''.join(struct.pack('>6f', *m) for m in xf)))
    tags.append((0xF103, struct.pack('>I', 0)))
    tags.append((0x27, struct.pack('>4I', 0, 0, 0, 0)))
    for fi, c, places in frames:
        tags.append((0x2B, struct.pack('>2I', sid['num_%03d' % c], fi)))
        tags.append((0x01, struct.pack('>2I', fi, len(places))))
        tags += [(0x04, p) for p in places]
    tags.append((0xFF00, b''))
    out = b''.join(struct.pack('>II', t, len(b) // 4) + b for t, b in tags)
    head = bytearray(0x40)
    head[:4] = b'LMB\0'
    struct.pack_into('>I', head, 0x1C, 0x40 + len(out))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(bytes(head) + out)


def main():
    out, vparam, vui, vfighter, sconf = sys.argv[1:6]
    data = os.path.join(out, 'data')
    link(vparam, os.path.join(data, 'param'))
    link(os.path.join(vui, 'message'), os.path.join(data, 'ui', 'message'))
    link(os.path.join(vui, 'replace', 'chr'), os.path.join(data, 'ui', 'replace', 'chr'))
    link_tree(os.path.join(vfighter, 'fox'), os.path.join(data, 'fighter', 'fox'))
    link_tree(os.path.join(vfighter, 'szerosuit'), os.path.join(data, 'fighter', 'szerosuit'),
              lambda rel: rel.startswith('model/body/') and not rel.startswith('model/body/c00/'))
    # synthetic stage
    for v in ('melee', 'end'):
        d = os.path.join(data, 'stage', v, 'BattleField_f')
        for rel, blob in (('param/BattleField_f_param.bin', b'PARAM' * 8), ('model/stage/model.nud', b'NUD' * 16),
                          ('collision/BattleField_f.lvd', b'LVD' * 16)):
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(blob)
    pngs = os.path.join(out, 'png')
    for st, size, tid in (('stage_10', (128, 64), 0x28000999), ('stage_00', (256, 128), 0x28000998),
                          ('stage_30', (128, 128), 0x28000997)):
        p = os.path.join(pngs, 'bf_%s.png' % st)
        png(p, 'Battlefield', size, (40, 90, 160))
        dst = os.path.join(data, 'ui', 'replace', 'stage', st, '%s_BattleField_f.nut' % st)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(T.new_nut(p, tid))
    # sound config cut to the game's counts
    sd = os.path.join(data, 'sound', 'config')
    os.makedirs(sd, exist_ok=True)
    d = open(os.path.join(sconf, 'bgm_fighter.fbb'), 'rb').read()
    open(os.path.join(sd, 'bgm_fighter.fbb'), 'wb').write(d[:8] + struct.pack('<I', 0x3A) + d[0xC:0xC + 0x14 * 0x3A])
    c = open(os.path.join(sconf, 'commonsoundtable.csb'), 'rb').read()
    nval = struct.unpack_from('<H', c, 8)[0]
    size = 0x10 + 4 * nval
    open(os.path.join(sd, 'commonsoundtable.csb'), 'wb').write(c[:10] + struct.pack('<H', 62) + c[0xC:0xC + size * 62])
    # test portraits
    for st, size in (('chr_00', (128, 128)), ('chr_10', (128, 128)), ('chr_11', (256, 256)), ('chr_13', (128, 64)),
                     ('stock_90', (64, 64))):
        for nn in ('01', '02'):
            png(os.path.join(pngs, 'fox_%s_%s.png' % (st, nn)), 'FOXCLONE', size, (170, 70, 30) if nn == '01'
                else (30, 120, 60))
    png(os.path.join(pngs, 'clone_stage_10.png'), 'CLONE FIELD', (128, 64), (150, 40, 120))
    # a custom UI: the dumps' modded portraits (CUSTOM_CHR, optional 6th argument) and a honeycomb CSS layout
    # (tools/chara_layout.py's user5 rows) for 13-112 entries
    if len(sys.argv) > 6:
        cui = os.path.join(out, 'custom_ui')
        link(sys.argv[6], os.path.join(cui, 'replace', 'chr'))
        link(os.path.join(vui, 'message'), os.path.join(cui, 'message'))
        import importlib.util                 # the research repository's chara_layout (its honeycomb styles)
        spec = importlib.util.spec_from_file_location(
            'research_chara_layout', os.path.join(os.path.dirname(os.path.dirname(HERE)), 'chara_layout.py'))
        cl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cl)
        synth_chara_lm(os.path.join(cui, 'lumen', 'chara', 'chara.lm'), list(range(13, 113)), cl.user5)
    print('fixtures in', out)


if __name__ == '__main__':
    main()
