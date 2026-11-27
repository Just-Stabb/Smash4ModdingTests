"""Builds the fake Azahar's memory from the dump: static.crs + enemy_fs.cro (+ main_field.cro) loaded as the RO
service would, code.bin's exports as stubs, a Goomba instance with its accessor / modules, the EnemyParamAccessor
singleton holding the Goomba's params (the values of reference/smashrun_enemy_specs/kuribo.json), a gimmick object
with RTTI for the object dump, and the scenario of calls.

Paths: S3DS_DUMP env var or --dump: a folder with static.crs and cro/<module>.cro (the base game's, from cro.sarc:
tools/s3ds_unpack.py cros). The base game's modules go with the map enemy_fs_base.json.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(TOOL, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import croload                    # noqa: E402
import fake_azahar as F           # noqa: E402

CRS_ADDR = 0x08400000
CRO_BASES = {'enemy_fs': (0x0A3C1000, 0x0A600000, 0x0A640000), 'main_field': (0x0A700000, 0x0A780000, 0x0A7C0000)}
# the layout the user's Azahar log suggests: code.bin (or code) mapped 0x00100000-0x01100000, the heap
# 0x08000000-0x08600000 without CROs, the main thread's stack just below 0x10000000, the modules in the linear heap
LAYOUTS = {
    'classic': {'crs': CRS_ADDR, 'cros': CRO_BASES, 'code_end': 0x00C80000, 'extra': []},
    'azahar': {'crs': 0x14200000, 'cros': {'enemy_fs': (0x14A3C000, 0x14C00000, 0x14C40000),
                                           'main_field': (0x14D00000, 0x14D80000, 0x14DC0000)},
               'code_end': 0x01100000, 'extra': [(0x08000000, 0x00600000), (0x0FFFC000, 0x4000)]},
    # the worst plausible case for the fallback scan: a 64 MB linear heap mapped in one piece, the modules 40 MB in
    'azahar_full': {'crs': 0x16800000, 'cros': {'enemy_fs': (0x16A3C000, 0x16C00000, 0x16C40000),
                                                'main_field': (0x16D00000, 0x16D80000, 0x16DC0000)},
                    'code_end': 0x01100000, 'extra': [(0x08000000, 0x00600000), (0x0FFFC000, 0x4000),
                                                      (0x14000000, 0x04000000)]},
}
ARM_BX_LR = struct.pack('<I', 0xE12FFF1E)
THUMB_BX_LR = struct.pack('<H', 0x4770)


def demangled(names):
    import s3ds_unpack as U
    return dict(zip(names, U.demangle(names)))


class World:
    def __init__(s, dump, kinds=('kuribo',), layout='classic'):
        s.dump = dump
        s.layout = L = LAYOUTS[layout]
        s.crs_addr = L['crs']
        s.cro_bases = L['cros']
        s.m = F.Machine()
        m = s.m
        m.map(0x00100000, L['code_end'] - 0x00100000)   # code.bin text / rodata / data / bss (stubs and singletons)
        for lo, n in L['extra']:
            m.map(lo, n)
        mp = lambda a, n: None if m.mapped(a, n) else m.map(a, n)
        mp(s.crs_addr, 0x00100000)
        for name, (b, d, bs) in s.cro_bases.items():
            p = os.path.join(dump, 'cro', name + '.cro')
            if os.path.exists(p):
                sz = os.path.getsize(p)
                mp(b, sz)
                mp(d, 0x20000)
                mp(bs, 0x10000)
        m.map(0, 0x10000)                          # null-pointer chains of the stubbed framework land here
        m.map(F.HEAP, 0x00200000)
        m.map(F.STACK_TOP - 0x00100000, 0x00100000)
        m.map(F.RET_MAGIC & ~0xFFF, 0x1000)
        m.write(F.RET_MAGIC, ARM_BX_LR)
        m.enable_vfp()
        crs_x = open(os.path.join(dump, 'static.crs'), 'rb').read()
        s.crs = croload.load_crs(m, crs_x, s.crs_addr)
        s.dem = demangled(list(s.crs.exports))
        s.by_dem = {}
        for mang, d in s.dem.items():
            s.by_dem.setdefault(d, s.crs.exports[mang])
        # every code.bin function a stub
        s.unresolved = m.alloc(16)
        m.write(s.unresolved, ARM_BX_LR)
        for mang, a in s.crs.exports.items():
            if 0x00100000 <= a < 0x00A83000:
                m.write(a & ~1, THUMB_BX_LR if a & 1 else ARM_BX_LR)
        s.cros = []
        for name, (b, d, bs) in s.cro_bases.items():
            p = os.path.join(dump, 'cro', name + '.cro')
            if os.path.exists(p):
                x = open(p, 'rb').read()
                lm = croload.load_cro(m, x, b, d, bs, [s.crs] + s.cros, s.unresolved)
                s.cros.append(lm)
        croload.link(m, s.crs, s.cros)
        s.ef = s.cros[0]
        s.specials()
        s.next_alloc_value = None

    def bl_return(s, mod, near=0):
        """a return address in the module's text: the word after an ARM BL at or after `near`"""
        lm = [c for c in s.cros if c.name == mod][0]
        x = open(os.path.join(s.dump, 'cro', mod + '.cro'), 'rb').read()
        o = max(0x180, near)
        while True:
            w = struct.unpack_from('<I', x, o)[0]
            if w >> 24 == 0xEB:
                return lm.base + o + 4
            o += 4

    def threads(s, with_cro_thread=True):
        """halted-at-connect registers as Azahar showed them (thread 1: PC / LR in code.bin, SP 0x0FFFFE28 when the
        layout maps that stack), plus a game thread whose LR returns into enemy_fs and whose stack holds a heap
        pointer and a return address into main_field. Returns the server's {thread id: regs} for the others."""
        m = s.m
        sp1 = 0x0FFFFE28 if m.mapped(0x0FFFFE28, 4) else F.STACK_TOP - 0x2000
        m.set_reg(15, 0x001720A8)
        m.set_reg(14, 0x00147908)
        m.set_reg(13, sp1)
        m.write(sp1, struct.pack('<4I', 0x00147908, 0x00100004, 0, 0x08000100))
        if not with_cro_thread:
            return {}
        sp2 = m.alloc(0x800)
        words = [0x0C000040, 0, s.bl_return('main_field', 0x2000), 0x00200000, 0x08001000]
        m.write(sp2, struct.pack('<%dI' % len(words), *words))
        return {'2': {15: 0x00180000, 14: s.bl_return('enemy_fs', 0x33000), 13: sp2}}

    def addr(s, dem):
        return s.by_dem[dem]

    # ------------------------------------------------------------------ code.bin behaviour the scenario needs
    def specials(s):
        m = s.m
        sp = m.specials

        def op_new(mm):
            n = mm.reg(0)
            mm.set_reg(0, mm.alloc(max(n, 0x400)))
        for d in ('operator new(unsigned int, std::nothrow_t const&)', 'operator new(unsigned int)'):
            if d in s.by_dem:
                sp[s.by_dem[d] & ~1] = op_new

        def beh_ctor(mm):
            this = mm.reg(0)
            mm.w32(this + 4, mm.reg(1))
            mm.w32(this + 0xC, mm.reg(2))
            mm.w32(this + 0x10, mm.reg(3))
        sp[s.addr('app::Behavior::Behavior(app::EnemyModuleAccessor&, int, int)') & ~1] = beh_ctor

        def rr_int(mm):
            mm.set_reg(0, 42)
        sp[s.addr('app::Behavior::random_range(int, int)') & ~1] = rr_int

        def rr_f(mm):
            mm.set_sreg_f(0, 0.25)
        sp[s.addr('app::Behavior::random_range(float, float)') & ~1] = rr_f

        def randi(mm):
            mm.set_reg(0, 7)
        sp[s.addr('app::GameManager::randi(unsigned int)') & ~1] = randi

        def calls(name):
            def f(mm):
                mm.calls.append(name)
            return f
        for d in ('app::Behavior::play_se(unsigned int, bool)', 'app::EnemyKineticModuleImpl::change_kinetic(int)',
                  'app::Behavior::change_motion_state(int, float, float, bool, float)'):
            a = s.by_dem.get(d)
            if a and (a & ~1) not in sp:
                sp[a & ~1] = calls(d)

    # ------------------------------------------------------------------ objects
    def universal(s):
        """a module object: every word points at a vtable whose every entry is a `bx lr` stub"""
        m = s.m
        if not hasattr(s, '_stub'):
            s._stub = m.alloc(16)
            m.write(s._stub, ARM_BX_LR)
            s._vt = m.alloc(0x400, struct.pack('<I', s._stub))
        return m.alloc(0x400, struct.pack('<I', s._vt))

    def accessor(s, mods, pos=(10.0, 2.5, 0.0), lr=1.0):
        """an EnemyModuleAccessor: every module slot a universal object; Posture (+0x14 position, +0x60 lr) and the
        movement energy chain [[[[KineticEnergy]+8]+0]+4] real; mods: {name: accessor offset} (the map's)"""
        m = s.m
        acc = m.alloc(0x3200)
        for off in range(0x2F80, 0x3100, 4):
            m.w32(acc + off, s.universal())
        post = m.alloc(0x100)
        m.write(post + 0x14, struct.pack('<3f', *pos))
        m.write(post + 0x60, struct.pack('<f', lr))
        m.w32(acc + mods['Posture'], post)
        e3 = m.alloc(0x80)
        e2 = m.alloc(0x10)
        m.w32(e2 + 4, e3)
        e1 = m.alloc(0x10)
        m.w32(e1, e2)
        ke = m.alloc(0x40)
        m.w32(ke + 8, e1)
        m.w32(acc + mods['KineticEnergy'], ke)
        s.energy = e3
        s.posture = post
        return acc

    def param_accessor(s, kinds):
        """lib::Singleton<EnemyParamAccessor>::instance_ -> {+0x38 gl entries, +0x60 + 4 kind -> param object}"""
        m = s.m
        root = os.path.join(ROOT, 'reference', 'smashrun_enemy_specs')
        acc = m.alloc(0x1000)
        gl = m.alloc(0x228 * 4)
        for i in range(4):
            m.write(gl + 0x228 * i + 0x11C, struct.pack('<f', 0.09))   # gl gravity-like (the notice hop divides by it)
        m.w32(acc + 0x38, gl)
        s.params = {}
        for kind, idx in kinds.items():
            sp = json.load(open(os.path.join(root, kind + '.json')))
            obj = m.alloc(0x200)
            for mem in sp['params']['members']:
                if mem['type'] != 'array':
                    continue
                vals = mem['values']
                data = m.alloc(max(1, len(vals)) * mem['elem_size'])
                for e, row in enumerate(vals):
                    for off, wd, v in zip(mem['offsets'], mem['widths'], row):
                        if wd != 4:
                            continue
                        b = struct.pack('<f', v) if isinstance(v, float) else struct.pack('<i', v)
                        m.write(data + e * mem['elem_size'] + off, b)
                m.w32(obj + mem['offset'] + 8, len(vals))
                m.w32(obj + mem['offset'] + 0xC, data)
            m.w32(acc + 0x60 + 4 * idx, obj)
            s.params[kind] = sp['params']['members']
        slot = s.addr('lib::Singleton<app::EnemyParamAccessor>::instance_')
        m.w32(slot, acc)
        return acc

    def gimmick_object(s, cls='GconEventDoor'):
        """an object with an armcc RTTI chain: [obj] = vtable, [vtable - 4] = typeinfo, [typeinfo + 4] = name"""
        m = s.m
        name = m.alloc(64)
        nm = ('N3app%d%sE' % (len(cls), cls)).encode() + b'\0'
        m.write(name, nm)
        ti = m.alloc(16)
        m.w32(ti + 4, name)
        vt = m.alloc(0x40)
        m.w32(vt, ti)
        obj = m.alloc(0x100)
        m.w32(obj, vt + 4)
        m.write(obj + 0x20, struct.pack('<3f', 100.0, -20.0, 0.0))
        lst = m.alloc(0x40)
        m.w32(lst + 8, obj)
        slot = s.addr('app::InstanceList<app::GimmickControllerBase>::s_instance_')
        m.w32(slot, lst)
        return obj
