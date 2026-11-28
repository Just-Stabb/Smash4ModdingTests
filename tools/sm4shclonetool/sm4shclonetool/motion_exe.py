"""(2.0) New motion kinds for a fighter (vanilla or a clone): the executable side of the motion importer (importer.py
writes the files).

What a motion kind is (traced on the game's v288 executable):
- Each fighter kind has a static descriptor (the descriptor switch 0x02E43148, getter 0x02E4313C) whose +4 is its motion
  info {main table, count, part list, part count, ...}: the main table has 8 bytes a motion {animation hash, flags}
  (hash = zlib.crc32(.omo name, 0xFFFFFFFF), the pack loader's key), the part list {table, part id} pairs, a part table
  4 bytes a motion (the hand / prop animation played with the main one; 0 = none).
- The count is read in two places only: 0x02EA9008 (called once per kind by 0x02EA9064, the run-time table getter)
  copies vl group 1 (6 bytes a motion: byte 1 -> the entry's byte +4, byte 0 -> flag 0x80) into the main table, for
  `count` motions, and stores the table at descriptor +0x1C; and 0x0275BAB0 (the AI's attack_data check) returns it.
- Nothing bounds the motion index where it is used: every MotionModule access (0x02C5B000-0x02C66000, 28 sites) reads
  [module +0x1C] + 8 x motion, checking only motion != -1; the script lookup 0x02E42518 reads motion.mtable[motion]
  unbounded; MSC / ACMD pass any int. So a motion past the count reads whatever follows the fighter's table in .data:
  the game can't play a new motion without the executable's table growing. With no executable change the only way is
  to replace an existing motion's animation (keep its file name) or scripts.
- The AI's attack_data (ATKD) index has 0x611 slots (0x02DFC8CC): motions past 0x610 are never picked by a CPU.

The patch (per fighter with imported motions, in the "imports" part of the tool's code space):
- a new main table: the fighter's own entries (the game's, or for a clone the copy kind_expand makes: the same bytes)
  then one entry per imported motion {hash of its .omo, flags} (flags: the low half of the motion it was copied from,
  or 0; the high byte comes from vl group 1 at run time, as for every motion);
- a new part list, each part table copied and extended (an imported motion's part animation hash, or 0);
- the motion info's +0 / +4 / +8: in place in .data for a vanilla fighter (its relocations at +0 / +8 are moved to dead
  words of the old tables, in .data: the patched rpx's loader then writes the old addresses there, where nothing reads
  them), in the clone's own motion info (kind_expand's copy in the kinds part) for a clone.
The tables are written at run time by 0x02EA9008 (as the clones' own tables already are): the code space must be
writable (Cemu; the Aroma plugin's memory, see the README's "not confirmed").
"""
from . import _paths  # noqa: F401

DESC_GETTER = 0x02E4313C
PART_IDS = {'rhand': 3, 'lhand': 4, 'face': 5}        # docs: 3 rhand, 4 lhand, 5 face, 6 <name>pt1, 7 <name>sw1 / pt2
ATKD_SLOTS = 0x611


def part_id(tag):
    t = tag.lower()
    if t in PART_IDS:
        return PART_IDS[t]
    return 6 if t.endswith('pt1') else 7


def motion_records(reg):
    """{fighter name: [record]} of the imported motions (the registry's imports)"""
    return {k: v for k, v in ((reg or {}).get('imports') or {}).get('motions', {}).items() if v}


def size_for(reg, read=None):
    """bytes the part needs (an upper bound: 0x800 motions a fighter, 8 parts)"""
    n = 0
    for _f, recs in motion_records(reg).items():
        m = 0x800 + len(recs)
        n += 8 * m + 8 * 8 + 8 * 4 * m + 0x40
    return (n + 0xFFF) & ~0xFFF


def vanilla_descriptor(read, kind):
    """the static descriptor of a vanilla kind (the game's descriptor switch: case -> bl getter -> lis / addi r3)"""
    import kind_expand as K
    _c, _r, _s, table = K.SWITCHES['descriptor']
    e = table + 4 * kind
    case = K.branch_target(e, read(e))
    g = K.branch_target(case, read(case))
    return ((read(g) & 0xFFFF) << 16) + K.sx16(read(g + 4)) & 0xFFFFFFFF


def build(read, reg, kind_of, clone_minfo, lo, hi, has_reloc):
    """{address: word}, [relocation sites], {override addresses}, info. read: the vanilla view; kind_of(name): its kind;
    clone_minfo: {clone kind: (its motion info address in the cave, its base's descriptor)} (kind_expand's);
    has_reloc(addr): a relocation targets the word."""
    words, relocs, override = {}, [], set()
    info = {'fighters': {}}
    pc = lo

    def alloc(n):
        nonlocal pc
        at = (pc + 7) & ~7
        pc = at + n
        assert pc <= hi, 'the imports part is full'
        return at

    def put(a, w):
        assert a not in words, 'motion tables: 0x%08X twice' % a
        words[a] = w & 0xFFFFFFFF
    for name, recs in sorted(motion_records(reg).items(), key=lambda kv: kind_of(kv[0])):
        kind = kind_of(name)
        if kind < 0x41:
            desc = vanilla_descriptor(read, kind)
            assert read(desc) == kind, '%s: no descriptor of kind 0x%X at 0x%08X' % (name, kind, desc)
            minfo = read(desc + 4)
            src = minfo
            vanilla = True
        else:
            minfo, base_desc = clone_minfo[kind]
            src = read(base_desc + 4)                  # the base's motion info: kind_expand's copy has its bytes
            vanilla = False
        main, count, parts, nparts = (read(src + 4 * i) for i in range(4))
        for i, r in enumerate(recs):
            assert r['index'] == count + i, '%s: imported motion %s is 0x%X, the table has 0x%X motions' % (
                name, r['name'], r['index'], count + i)
        n = count + len(recs)
        t_at = alloc(8 * n)
        for i in range(count):
            put(t_at + 8 * i, read(main + 8 * i))
            put(t_at + 8 * i + 4, read(main + 8 * i + 4))
        for i, r in enumerate(recs):
            fl = r.get('flags')
            if fl is None:
                cf = r.get('flags_from')
                fl = (read(main + 8 * cf + 4) & 0x00FFFFFF & ~0x80) if cf is not None and 0 <= cf < count else 0
            put(t_at + 8 * (count + i), r['hash'])
            put(t_at + 8 * (count + i) + 4, fl)
        p_at = alloc(8 * max(nparts, 1))
        ptabs = []
        for p in range(nparts):
            tbl, pid = read(parts + 8 * p), read(parts + 8 * p + 4)
            if tbl:
                pt = alloc(4 * n)
                for i in range(count):
                    put(pt + 4 * i, read(tbl + 4 * i))
                for i, r in enumerate(recs):
                    h = next((v for tag, v in (r.get('part_hashes') or {}).items() if part_id(tag) == pid), 0)
                    put(pt + 4 * (count + i), h)
                tbl = pt
            ptabs.append((tbl, pid))
            put(p_at + 8 * p, tbl)
            put(p_at + 8 * p + 4, pid)
        # a vanilla fighter's motion info is in .data: the relocations of its +0 / +8 stay in .data (an ADDR32 entry of
        # .rela.data can't name a word of another section), parked on a word nothing reads once the motion info
        # points elsewhere: the old main table's first hash, the old part list's first part id (neither has a
        # relocation of its own); the loader writes the old address there, harmlessly (weapon_expand's Kirby copy
        # header does the same)
        dead = {0: main, 8: parts + 4}
        for off, v in ((0, t_at), (4, n), (8, p_at if nparts else parts)):
            put(minfo + off, v)
            if vanilla and has_reloc(minfo + off):
                assert not has_reloc(dead[off]), 'motion tables: 0x%08X has a relocation' % dead[off]
                relocs.append((minfo + off, dead[off]))
            if not vanilla:
                override.add(minfo + off)
        info['fighters'][name] = {'kind': kind, 'minfo': minfo, 'table': t_at, 'count': count, 'new': len(recs),
                                  'parts': p_at, 'nparts': nparts, 'vanilla': vanilla}
    info['end'] = pc
    return words, relocs, override, info
