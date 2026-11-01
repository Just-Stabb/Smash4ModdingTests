#!/usr/bin/env python3
"""eft2's load-time pass over an emitter's data, run from Ultimate's own code (main.bin 13.0.4) in an
ARM64 emulator (unicorn), so the shaders get the constant buffer the game gives them.

  python3 tools/eft2_resolve.py PORT SET EMITTER     the words the pass changed

The resolver (main.bin 0x8B480, called once per emitter resource from 0x9AB08; x0 the resource, its +0x10
the emitter data) rewrites the EMTR binary in place: a constant colour / alpha written into its key table,
the key tables padded to 8 keys (the last key repeated, its time + 1, + 2 ...), each texture slot's UV
repeat from the repeat byte (two tables), the UV scroll / rotation / scale of a slot that doesn't animate
zeroed (scale 1), rotate_init / rand / add zeroed on is_rotate's off axes, fluctuation and shape fields,
and the shader flag words at +0x50 / +0x54 (0x8C660). Then it copies the first 0x750 bytes into the
GPU's buffer (memcpy at 0x8C204): the shaders' sysEmitterStaticUniformBlock (c9).

Calls out of the pass (texture lookups 0xAF810 / 0x9B3F0, the GPU allocator 0x319B0, memcpy, cache
flushes) return 0 here: a flipbook's "texture array" mode (pattern type 5) then keeps the file's cell
count."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RESOLVE = 0x8B480
STATIC_BLOCK = 0x750         # bytes copied to the GPU (c9)
STUBS = (0xAF810, 0x9B3F0, 0x319B0, 0x319D0, 0x319E0, 0x39BFB30, 0x39BFCF0)
RES, DATA, AUX, STACK, STOP = 0x70000000, 0x71000000, 0x72000000, 0x73000000, 0x7FFF0000
_image = {}


def main_bin():
    import port_sources
    p = os.environ.get('ULT_EXEFS') or (port_sources.load().roots('ult_exefs') or [None])[0]
    if not p or not os.path.exists(p):
        raise SystemExit('no main.bin (port_sources.json "ult_exefs" or $ULT_EXEFS)')
    if p not in _image:
        _image[p] = open(p, 'rb').read()
    return _image[p]


def resolve(raw):
    """the emitter data (EMTR binary, bytes) after eft2's load-time pass"""
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
    from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_LR, UC_ARM64_REG_SP, \
        UC_ARM64_REG_PC
    img = main_bin()
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    size = (len(img) + 0xFFFF) & ~0xFFFF
    uc.mem_map(0, size)
    uc.mem_write(0, img)
    for base in (RES, DATA, AUX, STACK):
        uc.mem_map(base, 0x100000)
    uc.mem_map(STOP, 0x1000)
    uc.mem_write(DATA, bytes(raw))
    uc.mem_write(RES + 0x10, struct.pack('<Q', DATA))

    def unmapped(u, access, addr, sz, value, data):
        u.mem_map(addr & ~0xFFF, 0x1000)          # anything else the pass touches reads as 0
        return True
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, unmapped)

    def code(u, addr, sz, data):
        if addr == STOP:
            u.emu_stop()
        elif addr in STUBS:
            u.reg_write(UC_ARM64_REG_X0, 0)
            u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))
    for a in STUBS + (STOP,):
        uc.hook_add(UC_HOOK_CODE, code, begin=a, end=a)
    uc.reg_write(UC_ARM64_REG_X0, RES)
    uc.reg_write(UC_ARM64_REG_X1, AUX)
    uc.reg_write(UC_ARM64_REG_SP, STACK + 0x80000)
    uc.reg_write(UC_ARM64_REG_LR, STOP)
    uc.emu_start(RESOLVE, STOP, count=2000000)
    return bytes(uc.mem_read(DATA, len(raw)))


def static_block(e):
    """an emitter's c9 (vfxb read_emitter's dict, with '_raw')"""
    if '_resolved' not in e:
        e['_resolved'] = resolve(e['_raw'])
    return e['_resolved'][:STATIC_BLOCK]


def main():
    import vfxb
    import port_sources
    name, st, emn = sys.argv[1:4]
    path = name if os.path.exists(name) else port_sources.load().eff(name)
    eff = vfxb.Eff(path)
    e = [x for x in eff.emitters(eff.sets.index(st)) if x['name'] == emn][0]
    new = resolve(e['_raw'])
    a, b = struct.unpack('<%dI' % (len(new) // 4), e['_raw'][:len(new) // 4 * 4]), struct.unpack('<%dI' % (len(new) // 4), new[:len(new) // 4 * 4])
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            fx, fy = struct.unpack('<f', struct.pack('<I', x))[0], struct.unpack('<f', struct.pack('<I', y))[0]
            print('+0x%03x  %08x -> %08x   (%g -> %g)' % (4 * i, x, y, fx, fy))


if __name__ == '__main__':
    main()
