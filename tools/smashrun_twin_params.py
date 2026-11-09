#!/usr/bin/env python3
"""The Smash Run twins' own params in the layout their Wii U AI reads (docs/smash-run-port.md "Step 2k").

Smash Run's Zima / Lethinium (plasmawisp) / Darios / Stalfos run their Master Fortress twins' Wii U AI (step 2a);
the AI reads a param object of the twin's class, parsed from a vl file in the twin's sm layout. This writes, for each
kind, param/enemy/fs/enemy_param_vl_<kind>.bin: the 3DS values (the converted fs vl file) in the twin's sm layout
(the Wii U file's token sequence), field by field; smashrun_walker_cave.py's k2_twins parses it with the twin's own
parser on a Smash Run stage. The layouts were compared token by token (type and group); they match except:
  zima        G0: the 3DS entry has a 5th word (u32 90) the Wii U reader has no field for: dropped;
              G5: the Wii U's inline struct has 6 more words after the 3DS's 7 (0.1, 5, 6, 9, 2, 20): the twin's kept
  darios      G5: 6 more Wii U words after the area table (0.1, 5, 5, 8, 2, 20): the twin's kept
  stalfos     G9: 6 more Wii U words after the 3-float array (0.1, 5, 5, 8, 2, 20): the twin's kept
  plasmawisp  G5: 8 more Wii U words after the 3DS's 53rd (0.1, 5, 6, 9, 2, 20, 90, 120): the twin's kept, the 3DS's
              last 3 (8, 8, 1.2) after them
Every other word is the 3DS's (the types are the same in both files at every kept position: checked).

  python3 tools/smashrun_twin_params.py FS_DIR SM_DIR OUT_DIR      (FS_DIR: the converted 3DS param/enemy/fs, SM_DIR:
                                                                    the Wii U param/enemy/sm; writes OUT_DIR/<files>)
  python3 tools/smashrun_twin_params.py --diff FS_DIR SM_DIR        (the fields whose values change)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fighter_param_vl as V  # noqa: E402

TWINS = (('zima', 'mczakozima'), ('plasmawisp', 'mczakoplasmawisp'), ('darios', 'mczakodarios'),
         ('stalfos', 'mczakostalfos'))
# per kind, per group: the Wii U group's tokens as a list of ('3', i) = the 3DS group's token i, ('3g', (g, i)) = the
# 3DS group g's token i, ('U', j) = the
# Wii U's token j (no 3DS counterpart); groups not listed map 1:1
EDITS = {
    'zima': {0: [('3', 0), ('3', 1), ('3', 2), ('3', 3)],
             5: [('3', i) for i in range(19)] + [('U', j) for j in range(19, 25)]},
    'darios': {5: [('3', i) for i in range(12)] + [('U', j) for j in range(12, 18)]},
    'stalfos': {9: [('3', i) for i in range(3)] + [('U', j) for j in range(3, 9)]},
    # step 2l: Wii U word 59 (object +0x134, 90) is the twin's search cool-down after its level-2 attack (the Wii U
    # sets +0x1E0 = it with change_state(8) at 0x026D0EA0; the 3DS 0x89134 leaves +0x1E0 = search_interval(1), set
    # just before at 0x8904C): it takes the 3DS's search_interval(1) (P1 entry 1's interval, G1 word 8), so the
    # Wii U's store writes the 3DS's value (docs/smash-run-port.md "Step 2l")
    'plasmawisp': {5: [('3', i) for i in range(53)] + [('U', j) for j in range(53, 59)] + [('3g', (1, 8))] +
                   [('U', 60)] + [('3', i) for i in range(53, 56)]},
}


def groups(data):
    """[(count or None, [tokens])] of a vl file"""
    _h, toks = V.tokenize(data)
    out = []
    for t in toks:
        if isinstance(t, tuple):
            out.append([t[1], []])
        else:
            if not out:
                out.append([None, []])
            out[-1][1].append(t)
    return out


def remap(kind, fs_data, sm_data):
    """the kind's file in the twin's layout; (bytes, [(group, index, wii u value, 3DS value)] changed)"""
    g3, gu = groups(fs_data), groups(sm_data)
    assert len(g3) == len(gu), kind
    out = bytearray(sm_data[:8])
    changed = []
    for gi, ((n3, t3), (nu, tu)) in enumerate(zip(g3, gu)):
        assert n3 == nu, (kind, gi, n3, nu)
        plan = EDITS.get(kind, {}).get(gi) or [('3', i) for i in range(len(t3))]
        assert len(plan) == len(tu), (kind, gi, len(plan), len(tu))
        if nu is not None:
            out += b'\x20' + struct.pack('>I', nu)
        for j, (src, i) in enumerate(plan):
            tok = t3[i] if src == '3' else tu[i] if src == 'U' else g3[i[0]][1][i[1]]
            assert tok.t == tu[j].t, (kind, gi, j, tok.t, tu[j].t)
            if tok.raw != tu[j].raw:
                changed.append((gi, j, tu[j].text(), tok.text()))
            out += bytes([tok.t]) + tok.raw
    # the result must tokenise to the Wii U file's exact type / group sequence
    _h, a = V.tokenize(bytes(out))
    _h, b = V.tokenize(sm_data)
    sig = lambda ts: [('G', x[1]) if isinstance(x, tuple) else x.t for x in ts]  # noqa: E731
    assert sig(a) == sig(b), kind
    return bytes(out), changed


def main():
    args = sys.argv[1:]
    diff = '--diff' in args
    args = [a for a in args if a != '--diff']
    if len(args) != (2 if diff else 3):
        sys.exit(__doc__)
    fs, sm = args[0], args[1]
    for kind, twin in TWINS:
        f3 = open(os.path.join(fs, 'enemy_param_vl_%s.bin' % kind), 'rb').read()
        fu = open(os.path.join(sm, 'enemy_param_vl_%s.bin' % twin), 'rb').read()
        data, changed = remap(kind, f3, fu)
        if diff:
            print('%s (%s): %d words take the 3DS value' % (kind, twin, len(changed)))
            for gi, j, u, t in changed:
                print('  G%d word %d: %s -> %s' % (gi, j, u, t))
        else:
            os.makedirs(args[2], exist_ok=True)
            with open(os.path.join(args[2], 'enemy_param_vl_%s.bin' % kind), 'wb') as f:
                f.write(data)
            print('enemy_param_vl_%s.bin: %d bytes (%s layout), %d words from the 3DS differ from the twin\'s'
                  % (kind, len(data), twin, len(changed)))


if __name__ == '__main__':
    main()
