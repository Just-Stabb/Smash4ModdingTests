"""The data files of a new stage slot copied from a stage: stage-select / song database entries, names, icons (new
texture ids) and the renamed stage folders.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import argparse
import copy
import os
import shutil
import struct
import sys
import zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt
import s4param

def group(items):
    return next((it for it in items if isinstance(it, list) and it[0] == 'group'))

def entry_of(g, ident):
    return next((e for e in g[2] if e[0][1] == ident))

def setv(e, i, v):
    e[i] = (e[i][0], v)

def insert(g, pos, e):
    ids = [x[0][1] for x in g[2]]
    assert e[0][1] not in ids, 'id 0x%X is already in the database' % e[0][1]
    assert all((ids[k] == k for k in range(pos))), "positions before %d aren't ids 0..%d" % (pos, pos - 1)
    g[2].insert(pos, e)
    g[1] = len(g[2])

def stage_db(path, src, cos, kind, page):
    data = open(path, 'rb').read()
    items = s4param.parse(data)
    g = group(items)
    e = copy.deepcopy(entry_of(g, src))
    order = max((x[10][1] for x in g[2] if x[0][1] < 200)) + 1
    run = max((x[20][1] for x in g[2])) + 1
    setv(e, 0, cos)
    setv(e, 1, 1)
    setv(e, 3, 1 if page == 2 else 0)
    setv(e, 4, 1 if page == 2 else 0)
    for i in (6, 7):
        setv(e, i, kind)
    for i in (8, 9):
        setv(e, i, kind + 1)
    setv(e, 10, order)
    setv(e, 20, run)
    insert(g, cos, e)
    return (s4param.build(items, data[:8]), e)

def sound_db(path, src, cos):
    data = open(path, 'rb').read()
    items = s4param.parse(data)
    g = group(items)
    e = copy.deepcopy(entry_of(g, src))
    setv(e, 0, cos)
    insert(g, cos, e)
    return (s4param.build(items, data[:8]), e)
NEW_TEXTURE_IDS = 671153920

def texture_ids(data):
    out = []
    i = data.find(b'GIDX')
    while i >= 0:
        out.append((i + 8, struct.unpack('>I', data[i + 8:i + 12])[0]))
        i = data.find(b'GIDX', i + 4)
    return out

def used_texture_ids(ui_dir):
    used = set()
    for root, _dirs, files in os.walk(ui_dir):
        for f in files:
            if f.endswith('.nut'):
                used.update((t for _, t in texture_ids(open(os.path.join(root, f), 'rb').read())))
    return used

def with_texture_id(data, tex_id):
    data = bytearray(data)
    for off, _ in texture_ids(data):
        struct.pack_into('>I', data, off, tex_id)
    return bytes(data)

def copy_stage(src_dir, dst_dir, src, name):
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        os.makedirs(os.path.join(dst_dir, rel), exist_ok=True)
        for f in files:
            shutil.copyfile(os.path.join(root, f), os.path.join(dst_dir, rel, f.replace(src, name)))
MELEE_KINDS = ['BattleField_f', 'End_f', 'Galaxy', 'MarioU', 'MarioKart', 'Kalos', 'Skyward', 'DKReturns', 'Metroid', 'YoshiU', 'Cave', 'Village2', 'Assault', 'Colloseum_f', 'PikminU', 'Angeland', 'Gamer', 'DuckHunt', 'Wrecking', 'XenoBlade', 'PunchOut', 'PunchOut2', 'Wufu', 'Miiverse', 'WiiFit', 'Pilotwings', 'Windyhill', 'Pacland', 'Wily', 'Gw3', 'XDolpic', 'XKart', 'XStadium', 'XOldin', '64Jungle', 'XNorfair', 'DxYorster', 'XHalberd', 'XVillage', 'XStarfox', 'XEmblem', 'XPalutena', 'XFzero', 'DxOnett', 'XDonkey', 'DxShrine', 'XMansion']
