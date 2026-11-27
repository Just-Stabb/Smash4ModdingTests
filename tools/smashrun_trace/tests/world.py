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
ARM_BX_LR = struct.pack('<I', 0xE12FFF1E)
THUMB_BX_LR = struct.pack('<H', 0x4770)


def demangled(names):
    import s3ds_unpack as U
    return dict(zip(names, U.demangle(names)))


class World:
    def __init__(s, dump, kinds=('kuribo',)):
        s.dump = dump
        s.m = F.Machine()
        m = s.m
        m.map(0x00100000, 0x00B80000)              # code.bin text / rodata / data / bss (stubs and singletons)
        m.map(CRS_ADDR, 0x00100000)
        for name, (b, d, bs) in CRO_BASES.items():
            p = os.path.join(dump, 'cro', name + '.cro')
            if os.path.exists(p):
                sz = os.path.getsize(p)
                m.map(b, sz)
                m.map(d, 0x20000)
                m.map(bs, 0x10000)
        m.map(0, 0x10000)                          # null-pointer chains of the stubbed framework land here
        m.map(F.HEAP, 0x00200000)
        m.map(F.STACK_TOP - 0x00100000, 0x00100000)
        m.map(F.RET_MAGIC & ~0xFFF, 0x1000)
        m.write(F.RET_MAGIC, ARM_BX_LR)
        m.enable_vfp()
        crs_x = open(os.path.join(dump, 'static.crs'), 'rb').read()
        s.crs = croload.load_crs(m, crs_x, CRS_ADDR)
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
        for name, (b, d, bs) in CRO_BASES.items():
            p = os.path.join(dump, 'cro', name + '.cro')
            if os.path.exists(p):
                x = open(p, 'rb').read()
                lm = croload.load_cro(m, x, b, d, bs, [s.crs] + s.cros, s.unresolved)
                s.cros.append(lm)
        croload.link(m, s.crs, s.cros)
        s.ef = s.cros[0]
        s.specials()
        s.next_alloc_value = None

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
