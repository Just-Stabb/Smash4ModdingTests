#!/usr/bin/env python3
"""eft's emitterStaticUniformBlock (a vertex program's CB2) for a ptcl emitter, built by Smash 4's own code
(cross_f.rpx 0x04A5AA00) run in a PowerPC emulator (unicorn).

  python3 tools/eft_static.py PTCL SET EMITTER       the block's named uniforms (from the program's header)

0x04A5AA00 (r3 the block, r4 the emitter data, r5 a shader-parameter object or 0): clears 0x500 bytes,
fills the three texture slots' UV blocks (shtAnim0-2, 0x04A5A6AC from the emitter's 0x4D4 + 0x7C x slot)
and the two flipbooks (ptnAnm0-1, 0x04A5A858), uboFlag's bits, rotBasis (0x4C4) and the rest of the
emitter's animation constants, then swaps every word to little-endian for the GPU and flushes the cache.
Its calls out (memset 0x04B7ECA8, the flush 0x04B7EC78) are done here."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BUILD = 0x04A5AA00
SIZE = 0x500
MEMSET, FLUSH = 0x04B7ECA8, 0x04B7EC78
BLOCK, DATA, STACK, STOP = 0x60000000, 0x61000000, 0x62000000, 0x6FFF0000
_img = {}


def rpx():
    import port_sources
    import kind_expand
    p = os.environ.get('S4_RPX') or (port_sources.load().roots('s4_rpx') or [None])[0]
    if not p or not os.path.exists(p):
        raise SystemExit("no cross_f.rpx (port_sources.json \"s4_rpx\" or $S4_RPX)")
    if p not in _img:
        _img[p] = kind_expand.Image(p)
    return _img[p]


def build(emitter):
    """the block (bytes, little-endian words as the GPU reads them) for a ptcl emitter's data"""
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
    from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_LR, \
        UC_PPC_REG_PC, UC_PPC_REG_MSR
    img = rpx()
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    spans = sorted((base & ~0xFFF, (base + len(data) + 0xFFF) & ~0xFFF) for base, data in img.mem)
    merged = []
    for lo, hi in spans:                      # sections share pages: map the merged page ranges
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    for lo, hi in merged:
        uc.mem_map(lo, hi - lo)
    for base, data in img.mem:
        uc.mem_write(base, data)
    for b in (BLOCK, DATA, STACK):
        uc.mem_map(b, 0x10000)
    uc.mem_map(STOP, 0x1000)
    uc.mem_write(DATA, bytes(emitter))

    def unmapped(u, access, addr, sz, value, data):
        u.mem_map(addr & ~0xFFF, 0x1000)
        return True
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, unmapped)

    def code(u, addr, sz, data):
        if addr == STOP:
            u.emu_stop()
            return
        if addr == MEMSET:
            dst, val, n = u.reg_read(UC_PPC_REG_3), u.reg_read(UC_PPC_REG_4), u.reg_read(UC_PPC_REG_5)
            u.mem_write(dst, bytes([val & 0xFF]) * n)
        u.reg_write(UC_PPC_REG_PC, u.reg_read(UC_PPC_REG_LR))
    for a in (MEMSET, FLUSH, STOP):
        uc.hook_add(UC_HOOK_CODE, code, begin=a, end=a)
    uc.reg_write(UC_PPC_REG_MSR, uc.reg_read(UC_PPC_REG_MSR) | 0x2000)       # floating point on
    uc.reg_write(UC_PPC_REG_3, BLOCK)
    uc.reg_write(UC_PPC_REG_4, DATA)
    uc.reg_write(UC_PPC_REG_5, 0)
    uc.reg_write(UC_PPC_REG_1, STACK + 0x8000)
    uc.reg_write(UC_PPC_REG_LR, STOP)
    uc.emu_start(BUILD, STOP, count=200000)
    return bytes(uc.mem_read(BLOCK, SIZE))


def named(block, header):
    """{uniform name: values} of a block (eft_vertex.vertex_header's uniforms of block 0 = CB2)"""
    import numpy as np
    w = np.frombuffer(block, '<f4')
    return {n: w[off:off + 4] for n, _t, _c, off, blk in header['uniforms'] if blk == 0 and off + 4 <= len(w)}


def main():
    import ptcl
    import eft_vertex
    path, st, emn = sys.argv[1:4]
    p = ptcl.Ptcl(open(path, 'rb').read())
    si = [i for i in range(len(p.sets)) if p.set_name(i) == st][0]
    em = [x['data'] for x in p.sets[si]['emitters'] if p.emitter_name(x['data']) == emn][0]
    blk = build(em)
    h = eft_vertex.vertex_header(p.shader_binary(p.field(em, 'shader_index')))
    for n, v in sorted(named(blk, h).items(), key=lambda kv: [u[3] for u in h['uniforms'] if u[0] == kv[0]][0]):
        print('%-24s %s' % (n, ' '.join('%g' % x for x in v)))


if __name__ == '__main__':
    main()
