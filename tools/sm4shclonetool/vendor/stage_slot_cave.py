"""New stage slots: stage kinds past the game's 128 (0x80 + 2i normal, 0x81 + 2i Omega) and stage-select cosmetic
ids from 0x38: the stage-kind table, the cosmetic name table, the counts and the page-2 checks. Some addresses
were first found by Manifold (Fitz Null, zlib licence, https://gitlab.com/fitz.lol/manifold).

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch
from ppcasm import Asm, ha
RPX = None
CAVE = 79151104
LIMIT = 79155200
KIND_TABLE, KIND_COUNT = (269605212, 128)
COSMETIC_TABLE, COSMETIC_COUNT = (271827200, 79)
DEFAULT = ['NewStage01:0x38']
RELOC_DUMMY = 79151096
TABLE_SITES = [47316368, 47316372, 47316384, 47316392, 47316496, 47316504, 43244772, 43244780]
FIRST_DLC, COSMETIC_DLC = (48, 8)
DLC_UNLOCK = 51024492
NEEDS_DLC = 51023224
HAS_DLC = 51023448

def slo(v):
    v &= 65535
    return v - 65536 if v & 32768 else v

def stages(args):
    out = []
    for i, a in enumerate(args or DEFAULT):
        name, _, cos = a.partition(':')
        out.append((name, int(cos, 0) if cos else 56 + i))
    return out

def build(new, rpx=RPX):
    d, _s, _e, secs = rpx_patch.load(rpx)
    cache = {}
    read = lambda a: rpx_patch.read_u32(d, secs, a, cache)
    kinds = [(read(KIND_TABLE + 8 * k), read(KIND_TABLE + 8 * k + 4)) for k in range(KIND_COUNT)]
    cosm = [(read(COSMETIC_TABLE + 8 * k), read(COSMETIC_TABLE + 8 * k + 4)) for k in range(COSMETIC_COUNT)]
    assert kinds[0][1] == 0 and kinds[47][1] == 1, 'unexpected stage-kind table'
    used = {c for c, _ in cosm}
    for name, cos in new:
        assert cos not in used, "cosmetic id 0x%X is the game's" % cos
    count = KIND_COUNT + 2 * len(new)
    kt = CAVE
    ct = kt + 8 * count
    strings = ct + 8 * (COSMETIC_COUNT + len(new))
    blob = bytearray()
    ptr = {}
    for name, _ in new:
        ptr[name] = strings + len(blob)
        blob += name.encode('ascii') + b'\x00'
    blob += b'\x00' * (-len(blob) % 4)
    words = []
    for p, v in kinds:
        words += [p, v]
    for name, _ in new:
        words += [ptr[name], 0, ptr[name], 1]
    for c, p in cosm:
        words += [c, p]
    for name, cos in new:
        words += [cos, ptr[name]]
    words += list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= LIMIT, 'stage slot cave too big'

    def one(addr, text):
        a = Asm(addr)
        a.asm(text)
        return [(addr + 4 * i, w) for i, w in enumerate(a.words())]
    patches = []
    patches += one(47316516, 'li r3, %d' % count)
    patches += one(47316352, 'cmplwi r3, %d' % count)
    patches += one(47316368, 'addis r12, r11, 0x%X' % ha(kt))
    patches += one(47316372, 'lwz r0, %d(r12)' % slo(kt))
    patches += one(47316384, 'lis r10, 0x%X' % ha(kt))
    patches += one(47316392, 'addi r10, r10, %d' % slo(kt))
    patches += one(47316496, 'lis r12, 0x%X' % ha(kt + 4))
    patches += one(47316504, 'addi r12, r12, %d' % slo(kt + 4))
    patches += one(50415392, 'cmplwi r31, %d' % count)
    patches += one(43244772, 'lis r3, 0x%X' % ha(ct))
    patches += one(43244776, 'li r4, %d' % (COSMETIC_COUNT + len(new)))
    patches += one(43244780, 'addi r3, r3, %d' % slo(ct))
    patches += one(DLC_UNLOCK, '\n        addi r12, r28, -%d\n        cmplwi r12, %d\n        addi r31, r12, 9\n        blt 0x%08X' % (FIRST_DLC, COSMETIC_DLC, DLC_UNLOCK + 72))
    code = CAVE + 4 * len(words)
    a = Asm(code)
    a.asm('\n        cmplwi r4, %d\n        blt dlc\n        li r3, 0\n        blr\ndlc:    mflr r0\n        b 0x%08X' % (FIRST_DLC + COSMETIC_DLC, NEEDS_DLC + 4))
    words += a.words()
    patches += one(NEEDS_DLC, 'b 0x%08X' % code)
    code = CAVE + 4 * len(words)
    a = Asm(code)
    a.asm('\n        cmplwi r4, %d\n        blt has\n        cmplwi r4, 0xC7\n        bgt has\n        li r3, 1\n        blr\nhas:    mflr r0\n        b 0x%08X' % (FIRST_DLC + COSMETIC_DLC, HAS_DLC + 4))
    words += a.words()
    patches += one(HAS_DLC, 'b 0x%08X' % code)
    assert CAVE + 4 * len(words) <= LIMIT, 'stage slot cave too big'
    return (words, patches, count)
GROUPS = {'kinds': [47316516, 47316352, 47316368, 47316372, 47316384, 47316392, 47316496, 47316504, 50415392], 'names': [43244772, 43244776, 43244780], 'dlc': [DLC_UNLOCK + 4 * i for i in range(4)] + [NEEDS_DLC, HAS_DLC]}
