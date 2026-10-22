#!/usr/bin/env python3
"""Dump the executable's fighter-kind tables (research for a new fighter slot, docs/new-fighter-slot.md).

  python3 tools/fighter_kind_tables.py [RPX] [--kind K] [--ui PARAMDIR] [--scan] [--vtables]

RPX defaults to build/cave_fix_s4/cross_f.rpx. Prints, per fighter kind (0x00-0x40):
- the three name tables (lower 0x102FF484, Capitalised 0x102FF588, vl param 0x10353DB4);
- where each kind switch sends it (the jump tables bounded by `cmplwi kind, 0x40`):
  specializer getter 0x02E669F0 (-> static singleton), kind descriptor getter 0x02E4313C,
  vl param load 0x02EA6BC4 / unload 0x02EA5D64 (with the parsed-struct field and param-manager slot
  each case writes), AI 0x02E02440 and 0x0275B440;
- the per-kind byte / halfword tables (special param block sizes 0x1012F638 / 0x1012F6BC..,
  sound class 0x100D21D8).
Also the UI character-id -> name table (0x1033BE68, read by 0x0293DCCC).

--kind K      only that kind, in detail (case code addresses, descriptor words)
--ui DIR      also dump DIR/ui/ui_character_db.bin (chr id, kind, series, costumes, flags)
--scan        list every jump table in .text bounded by 0x39-0x41 (candidate kind switches)
--vtables     find each specializer singleton's vtable (reads .rela.text; slower)
--plan SLOT:BASE[:name[:Cap]]
              print (untested) rpx_patch.py arguments for the "reused slot" plan of
              docs/new-fighter-slot.md: kind SLOT (e.g. 0x3E, a Fighting Mii Team kind) renamed in
              place and its specializer / descriptor / AI cases and per-kind size tables pointed at
              BASE's. The vl param load / unload cases (which write per-kind fixed fields) and the
              inline Mii-enemy checks are listed, not patched: they need a code cave / review.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch  # noqa: E402

RPX = os.path.join(HERE, '..', 'build', 'cave_fix_s4', 'cross_f.rpx')
NKINDS = 0x41
NAMES_LOWER, NAMES_CAP, NAMES_VL = 0x102FF484, 0x102FF588, 0x10353DB4
CHR_NAMES_FN = 0x0293DCCC          # lis r3 / li r4,count / addi r3 -> {u32 id, char *name} table
# (name, cmplwi address, jump table address, how a case is followed)
SWITCHES = [
    ('specializer', 0x02E669F0, 0x02E66A10, 'b-b'),      # case: b getter; getter: lis r3/addi r3; blr
    ('descriptor', 0x02E43148, 0x02E43168, 'b-bl'),      # case: bl getter; default: abort 0x04ADC364
    ('vl_load', 0x02EA6C94, 0x02EA6CB4, 'b'),            # FighterParamManager: parse + slot
    ('vl_unload', 0x02EA5DA0, 0x02EA5DC4, 'b'),
    ('ai_a', 0x02E02458, 0x02E02474, 'b'),               # per-kind AI on [ai+0x18]
    ('ai_b', 0x0275B44C, 0x0275B46C, 'b'),
]
BYTE_TABLES = [('spN', 0x1012F6BC), ('spS', 0x1012F700), ('spHi', 0x1012F744), ('spLw', 0x1012F788)]
HALF_TABLE = ('sp16', 0x1012F638)   # u16 per kind, 0x02EA90E0
SND_CLASS = 0x100D21D8              # u32 per kind (0-3), 0x02AB8CB0


class Rpx:
    def __init__(self, path):
        self.d, _o, _e, self.secs = rpx_patch.load(path)
        self.cache = {}
        self.mem = []
        for i, s in enumerate(self.secs):
            if s[1] == 1 and s[3] and s[5]:
                self.mem.append((s[3], rpx_patch.section_data(self.d, s)))

    def find(self, a):
        for base, data in self.mem:
            if base <= a < base + len(data):
                return base, data
        return None, None

    def u32(self, a):
        base, data = self.find(a)
        if data is None:
            return None
        return struct.unpack('>I', data[a - base:a - base + 4])[0]

    def u16(self, a):
        base, data = self.find(a)
        return struct.unpack('>H', data[a - base:a - base + 2])[0]

    def u8(self, a):
        base, data = self.find(a)
        return data[a - base]

    def cstr(self, a):
        base, data = self.find(a or 0)
        if data is None:
            return None
        o = a - base
        e = data.find(b'\0', o)
        return data[o:e].decode('latin1')

    def text(self):
        for base, data in self.mem:
            if base == 0x02000020 or (base <= 0x02000020 < base + len(data)):
                return base, data
        return self.mem[0]


def branch_target(rpx, a):
    w = rpx.u32(a)
    if w is None or (w >> 26) != 18:
        return None
    off = w & 0x3FFFFFC
    if off & 0x2000000:
        off -= 0x4000000
    return a + off


def lis_addi(rpx, a):
    """value of `lis rD,hi ; addi/addic rD,rD,lo` at a (None otherwise)"""
    w1, w2 = rpx.u32(a), rpx.u32(a + 4)
    if (w1 >> 26) == 15 and ((w1 >> 16) & 31) == 0 and (w2 >> 26) in (12, 14):
        lo = w2 & 0xFFFF
        lo = lo - 0x10000 if lo & 0x8000 else lo
        return (((w1 & 0xFFFF) << 16) + lo) & 0xFFFFFFFF
    return None


def follow(rpx, table, kind, how):
    case = branch_target(rpx, table + 4 * kind)
    if case is None:
        return None, None
    if how == 'b':
        return case, None
    if how in ('b-b', 'b-bl'):
        getter = branch_target(rpx, case)
        return case, (getter, lis_addi(rpx, getter) if getter else None)
    return case, None


def vl_case_slots(rpx, case, store_base):
    """(struct field written as `stw r3,D(r30)`, param-manager word written in 0x111C..0x1220)"""
    field = slot = None
    for i in range(48):
        a = case + 4 * i
        w = rpx.u32(a)
        op, ra, d = w >> 26, (w >> 16) & 31, w & 0xFFFF
        if op == 36 and ra == 30 and field is None and d < 0x1000:
            field = d
        if op == 36 and ra == store_base and 0x111C <= d < 0x1220:
            slot = d
        if op == 32 and ra == 7 and d < 0x1000 and field is None and store_base == 30:
            field = d
        if (op == 18 and not (w & 1)) and i > 2:      # b tail
            break
    return field, slot


def kind_rows(rpx):
    rows = []
    for k in range(NKINDS):
        r = {'kind': k,
             'name': rpx.cstr(rpx.u32(NAMES_LOWER + 4 * k)),
             'cap': rpx.cstr(rpx.u32(NAMES_CAP + 4 * k)),
             'vl': rpx.cstr(rpx.u32(NAMES_VL + 4 * k))}
        for name, _cmp, table, how in SWITCHES:
            case, extra = follow(rpx, table, k, how)
            r[name] = case
            if extra:
                r[name + '_getter'], r[name + '_obj'] = extra
        r['vl_field'], r['vl_slot'] = vl_case_slots(rpx, r['vl_load'], 29)
        r['vl_unload_field'], _ = vl_case_slots(rpx, r['vl_unload'], 30)
        for name, t in BYTE_TABLES:
            r[name] = rpx.u8(t + k)
        r[HALF_TABLE[0]] = rpx.u16(HALF_TABLE[1] + 2 * k)
        r['snd_class'] = rpx.u32(SND_CLASS + 4 * k)
        rows.append(r)
    return rows


def chr_names(rpx):
    t = lis_addi_split(rpx, CHR_NAMES_FN)
    out = []
    for i in range(t[1]):
        cid = rpx.u32(t[0] + 8 * i)
        out.append((cid - (1 << 32) if cid & 0x80000000 else cid, rpx.cstr(rpx.u32(t[0] + 8 * i + 4))))
    return t, out


def lis_addi_split(rpx, fn):
    """0x0293DCCC: mr r5,r3 / lis r3,hi / li r4,count / addi r3,r3,lo / b 0x0293E92C"""
    w_lis, w_li, w_addi = rpx.u32(fn + 4), rpx.u32(fn + 8), rpx.u32(fn + 12)
    lo = w_addi & 0xFFFF
    lo = lo - 0x10000 if lo & 0x8000 else lo
    return ((((w_lis & 0xFFFF) << 16) + lo) & 0xFFFFFFFF, w_li & 0xFFFF)


def h(v):
    return '-' if v is None else '0x%08X' % v


def print_table(rows):
    print('kind name          Cap           vl param file              specializer obj  descriptor   '
          'vl case     field slot   ai_a        ai_b        sp16 N   S   Hi  Lw  snd')
    for r in rows:
        print('0x%02X %-13s %-13s %-26s %s %s %s 0x%03X 0x%04X %s %s %4d %3d %3d %3d %3d %d' % (
            r['kind'], r['name'], r['cap'], r['vl'], h(r.get('specializer_obj')),
            h(r.get('descriptor_obj')), h(r['vl_load']), r['vl_field'] or 0, r['vl_slot'] or 0,
            h(r['ai_a']), h(r['ai_b']), r['sp16'], r['spN'], r['spS'], r['spHi'], r['spLw'],
            r['snd_class']))


def print_kind(rpx, r):
    for k, v in r.items():
        print('%-22s %s' % (k, h(v) if isinstance(v, int) and v > 0xFFFF else v))
    d = r.get('descriptor_obj')
    if d:
        print('descriptor words:', ' '.join(h(rpx.u32(d + 4 * i)) for i in range(16)))


def scan(rpx):
    base, data = rpx.text()
    n = len(data) // 4
    words = struct.unpack('>%dI' % n, data[:n * 4])
    for i in range(n - 10):
        w = words[i]
        if (w >> 26) == 10 and 0x39 <= (w & 0xFFFF) <= 0x41:
            for j in range(i + 1, i + 9):
                if words[j] == 0x4E800420:
                    print('0x%08X cmplwi r%d, 0x%X  -> bctr 0x%08X' % (base + 4 * i, (w >> 16) & 31,
                                                                     w & 0xFFFF, base + 4 * j))
                    break


def relocations(rpx):
    """[(r_offset, type, target)] from the RPX's .rela sections (symbol value + addend)"""
    d, secs = rpx.d, rpx.secs
    symtab = next(i for i, s in enumerate(secs) if s[1] == 2)
    sym = rpx_patch.section_data(d, secs[symtab])
    vals = [struct.unpack('>I', sym[o + 4:o + 8])[0] for o in range(0, len(sym), 16)]
    out = []
    for s in secs:
        if s[1] != 4:
            continue
        rel = rpx_patch.section_data(d, s)
        for o in range(0, len(rel), 12):
            off, info, add = struct.unpack('>IIi', rel[o:o + 12])
            out.append((off, info & 0xFF, (vals[info >> 8] + add) & 0xFFFFFFFF))
    return out


def vtables(rpx, rows):
    lo_at = {}
    for off, typ, val in relocations(rpx):
        if typ == 4:
            lo_at[off - 2] = val
    by_val = {}
    for a, v in lo_at.items():
        by_val.setdefault(v, []).append(a)
    for r in rows:
        obj = r.get('specializer_obj')
        vt = None
        for a in by_val.get(obj, []):
            w = rpx.u32(a)
            if (w >> 26) != 36:
                continue
            rs = (w >> 21) & 31
            for k in range(1, 12):
                x = rpx.u32(a - 4 * k)
                if (x >> 26) in (12, 13, 14) and ((x >> 21) & 31) == rs and (a - 4 * k) in lo_at:
                    vt = lo_at[a - 4 * k]
                    break
            if vt:
                break
        r['specializer_vtable'] = vt
        print('0x%02X %-13s singleton %s vtable %s' % (r['kind'], r['name'], h(obj), h(vt)))


def word_patches(rpx, addr, newbytes, room):
    """aligned 32-bit rpx_patch args writing newbytes at addr, zero-filling up to addr+room"""
    assert len(newbytes) <= room, 'does not fit (%d > %d bytes)' % (len(newbytes), room)
    buf = bytes(newbytes) + b'\0' * (room - len(newbytes))
    out = []
    start = addr & ~3
    end = (addr + room + 3) & ~3
    for a in range(start, end, 4):
        old = struct.pack('>I', rpx.u32(a))
        w = bytearray(old)
        for i in range(4):
            if addr <= a + i < addr + room:
                w[i] = buf[a + i - addr]
        if bytes(w) != old:
            out.append('0x%08X=0x%08X' % (a, struct.unpack('>I', bytes(w))[0]))
    return out


def string_room(rpx, a):
    """bytes available for a NUL-terminated replacement at a (the string and its padding)"""
    n = len(rpx.cstr(a)) + 1
    while (a + n) % 4 and rpx.u8(a + n) == 0:
        n += 1
    return n


# inline "is a Fighting Mii Team kind" checks (0x3E-0x40) found besides the two helpers; review by hand
MII_ENEMY_SITES = [0x02542FD4, 0x0265FC74, 0x026F4ACC, 0x026F4B50, 0x0270EDCC, 0x027294C8, 0x02A65928,
                   0x02DE6A98, 0x02DEA014, 0x02FE3FC4]
IS_MII = 0x02E694AC          # (kind, include_enemy): 0-2, or 0x3E-0x40 when include_enemy (addi -0x3E at +0x20)
IS_MII_ENEMY = 0x02E694E8    # 0x3E / 0x3F / 0x40 (cmpwi r3, k at +0, +8, +0x10)
COPY_GRANT_BOUND = 0x02EFCDC8  # Kirby copy_grant: cmplwi r28, 0x3A (kinds >= 0x3A never copied)


def plan(rpx, rows, spec):
    parts = spec.split(':')
    slot, base = int(parts[0], 0), int(parts[1], 0)
    s, b = rows[slot], rows[base]
    args = []
    print('# slot 0x%02X (%s) -> clone of 0x%02X (%s)' % (slot, s['name'], base, b['name']))
    if len(parts) > 2:
        lower = parts[2].encode()
        cap = (parts[3] if len(parts) > 3 else parts[2][:1].upper() + parts[2][1:]).encode()
        for table, new in ((NAMES_LOWER, lower), (NAMES_CAP, cap), (NAMES_VL, b'fighter_param_vl_' + lower)):
            a = rpx.u32(table + 4 * slot)
            args += word_patches(rpx, a, new + b'\0', string_room(rpx, a))
        print('# names: %s / %s / fighter_param_vl_%s (in place; each string has one reference)' % (
            lower.decode(), cap.decode(), lower.decode()))
    for name, _cmp, table, _how in SWITCHES:
        if name.startswith('vl_'):
            continue
        entry = table + 4 * slot
        args.append('0x%08X=0x%08X' % (entry, 0x48000000 | ((b[name] - entry) & 0x3FFFFFC)))
    for name, t in BYTE_TABLES:
        args += word_patches(rpx, t + slot, bytes([b[name]]), 1)
    args += word_patches(rpx, HALF_TABLE[1] + 2 * slot, struct.pack('>H', b['sp16']), 2)
    args.append('0x%08X=0x%08X' % (SND_CLASS + 4 * slot, b['snd_class']))
    print(' '.join(args))
    print('# still to do (cave / review):')
    print('#  vl_load  case 0x%08X: copy %s\'s case 0x%08X, but its stores to [mgr+0x2574]+0x%X and mgr+0x%X'
          ' must become +0x%X and +0x%X (and load kind 0x%02X too: %s\'s native code reads mgr+0x%X)' % (
              s['vl_load'], b['name'], b['vl_load'], b['vl_field'], b['vl_slot'], s['vl_field'], s['vl_slot'],
              base, b['name'], b['vl_slot']))
    print('#  vl_unload case 0x%08X: same with %s\'s 0x%08X (field +0x%X -> +0x%X)' % (
        s['vl_unload'], b['name'], b['vl_unload'], b['vl_unload_field'] or 0, s['vl_unload_field'] or 0))
    if 0x3E <= slot <= 0x40:
        print('#  Mii-enemy checks: helpers 0x%08X (isMii, enemy range at +0x20) and 0x%08X (isMiiEnemy);'
              ' inline sites %s' % (IS_MII, IS_MII_ENEMY, ' '.join('0x%08X' % a for a in MII_ENEMY_SITES)))
    if slot >= 0x3A:
        print('#  Kirby: copy_grant refuses kinds >= 0x3A (0x%08X); the copy setup switch 0x02EFC940 stops at'
              ' 0x33' % COPY_GRANT_BOUND)


def ui_db(path):
    import s4param
    items = s4param.parse(open(path, 'rb').read())
    g = next(x for x in items if isinstance(x, list))
    print('\nui_character_db.bin: %d entries (RAM 0x4C each; ids <= 0xC7 are looked up by position)' % len(g[2]))
    print('idx  id  shown series kind costumes mii dlc  sort13 sort14 sort15  f16')
    for i, e in enumerate(g[2]):
        v = [x for _t, x in e]
        kind = v[6] if v[6] != 0xFFFFFFFF else -1
        f16 = v[16] if v[16] != 0xFFFFFFFF else -1
        print('%3d %4d  %d     %3d   %3d  %3d      %d   %d   %4d   %4d   %4d   %3d' % (
            i, v[0], v[2], v[4], kind, v[7], v[9], v[10], v[13], v[14], v[15], f16))


def main():
    args = sys.argv[1:]
    path = RPX
    if args and not args[0].startswith('--'):
        path = args.pop(0)
    rpx = Rpx(path)
    rows = kind_rows(rpx)
    if '--plan' in args:
        plan(rpx, rows, args[args.index('--plan') + 1])
        return
    if '--kind' in args:
        k = int(args[args.index('--kind') + 1], 0)
        print_kind(rpx, rows[k])
    else:
        print_table(rows)
        (t, n), names = chr_names(rpx)
        print('\nUI character id -> name table 0x%08X, %d entries (0x0293DCCC):' % (t, n))
        print(' '.join('%d:%s' % x for x in names))
    if '--vtables' in args:
        vtables(rpx, rows)
    if '--scan' in args:
        scan(rpx)
    if '--ui' in args:
        ui_db(os.path.join(args[args.index('--ui') + 1], 'ui', 'ui_character_db.bin'))


if __name__ == '__main__':
    main()
