"""Custom moves: a new character id owns its base character's custom moves (the owned-move index functions map the
new id to the base's).

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import argparse
import json
import os
import struct
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm, ha
import rpx_patch
CAVE = 79155200
LIMIT = 79159296
FIRST_NEW_ID = 59
OWN_INDEX = 44356620
OWN_ORIG = [2087459705, 945881087, 1300365344, 946667519, 1317011488]
LINEAR = 43279464
LINEAR_ORIG = [1418463167, 1418393534, 1418454590, 1082261516, 945881087, 1317011488, 965541887, 491388931, 1435239998, 493551628, 2106221076, 2087412244, 1317011488]
CHR_TABLE, CHR_COUNT = (271826536, 83)
SPEC = None
RPX = None

def slo(v):
    v &= 65535
    return v - 65536 if v & 32768 else v

class Img:

    def __init__(self, path):
        d, _o, _e, secs = rpx_patch.load(path)
        self.mem = [(s[3], bytes(rpx_patch.section_data(d, s))) for s in secs if s[1] == 1 and s[3] and s[5]]

    def blob(self, a, n):
        for base, data in self.mem:
            if base <= a and a + n <= base + len(data):
                return data[a - base:a - base + n]
        raise KeyError('0x%08X' % a)

    def w(self, a):
        return struct.unpack('>I', self.blob(a, 4))[0]

    def cstr(self, a):
        out = b''
        while self.blob(a + len(out), 1) != b'\x00':
            out += self.blob(a + len(out), 1)
        return out.decode('latin1')

def base_ids(spec_path, img):
    spec = json.load(open(spec_path))
    names = {}
    for i in range(1, CHR_COUNT):
        cid, p = (img.w(CHR_TABLE + 8 * i), img.w(CHR_TABLE + 8 * i + 4))
        names.setdefault(img.cstr(p).lower(), cid)
    out = {}
    for r in spec['kinds']:
        ui = r.get('ui') or {}
        if ui.get('id') is None:
            continue
        b = ui.get('base_id')
        if b is None:
            b = names.get(r['base'].lower())
            assert b is not None, 'no UI id for base %s (give ui.base_id)' % r['base']
        out[int(str(ui['id']), 0)] = int(str(b), 0)
    return out

def build(spec_path=SPEC, rpx=RPX):
    img = Img(rpx)
    for i, w in enumerate(OWN_ORIG):
        assert img.w(OWN_INDEX + 4 * i) == w, 'unexpected code at 0x%08X' % (OWN_INDEX + 4 * i)
    for i, w in enumerate(LINEAR_ORIG):
        assert img.w(LINEAR + 4 * i) == w, 'unexpected code at 0x%08X' % (LINEAR + 4 * i)
    m = base_ids(spec_path, img)
    assert m and min(m) >= FIRST_NEW_ID
    n = max(m) - FIRST_NEW_ID + 1
    table = bytes((m.get(FIRST_NEW_ID + i, 0) for i in range(n)))
    table += b'\x00' * (-len(table) % 4)

    def remap(tag):
        return '\n        addi r9, r3, -%(first)d\n        cmplwi r9, %(n)d\n        bge %(tag)s\n        lis r10, tbl@ha\n        addi r10, r10, tbl@l\n        add r9, r10, r9\n        lbz r9, 0(r9)\n        cmpwi r9, 0\n        beq %(tag)s\n        mr r3, r9\n%(tag)s:' % dict(first=FIRST_NEW_ID, n=n, tag=tag)
    a = Asm(CAVE)
    a.asm('\nown_index:                      # 0x02A4D40C: id -> bitfield row (id - 1), 0 -> -1\n        cmpwi r3, 0\n        beq none\n' + remap('own_mapped') + '\n        addi r3, r3, -1\n        blr\nnone:   li r3, -1\n        blr\nlinear:                         # 0x02946468: (db, skill id r4) -> linear index, variant 0 -> -1\n        clrlwi. r12, r4, 30\n        bne have\n        li r3, -1\n        blr\nhave:   rlwinm r3, r4, 28, 24, 31\n        addi r3, r3, 1\n' + remap('lin_mapped') + '\n        addi r11, r3, -1\n        clrlwi r11, r11, 24\n        rlwinm r10, r4, 30, 30, 31\n        addi r12, r12, -1\n        mulli r10, r10, 3\n        clrlwi r12, r12, 24\n        mulli r11, r11, 12\n        add r12, r10, r12\n        add r3, r11, r12\n        blr\ntbl:\n')
    for i in range(0, len(table), 4):
        a.asm('.word 0x%08X' % struct.unpack('>I', table[i:i + 4])[0])
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT

    def jump(to):
        j = Asm(0)
        j.asm('lis r12, 0x%X\naddi r12, r12, %d\nmtctr r12\nbctr' % (ha(to), slo(to)))
        return j.words()
    patches = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for site, lab in ((OWN_INDEX, 'own_index'), (LINEAR, 'linear')):
        for i, w in enumerate(jump(a.labels[lab])):
            patches[site + 4 * i] = w
    return (patches, a.labels, m)
