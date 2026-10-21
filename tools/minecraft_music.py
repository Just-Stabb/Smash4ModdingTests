#!/usr/bin/env python3
"""Minecraft World's music (Smash Ultimate's bgmpickel playlist) for Smash 4's NewStage01.

  python3 tools/minecraft_music.py AUDIO TEMPLATE CONFIG PARAM MSBT OUT

AUDIO     Ultimate's bgm_mc0*.nus3audio (stream:/sound/bgm)
TEMPLATE  a Smash 4 BGM bank to copy the layout from (sound/bgm/snd_bgm_CRS02_Senjyou.nus3bank)
CONFIG    Smash 4's sound/config (bgm_property.mpb, bgm_mymusic.mmb)
PARAM     Smash 4's param folder (ui/ui_sound_db.bin)
MSBT      the game's unmodified ui/message/sound.msbt
OUT       gets sound/bgm/snd_bgm_MC0*.nus3bank, sound/config/{bgm_property.mpb,bgm_mymusic.mmb},
          param/ui/ui_sound_db.bin, ui/message/sound.msbt

New songs are added the way Sm4shMusic adds them (nothing replaced):
- a BGM id per track (free bgm_property.mpb slots, Sm4shMusic's choice: the lowest), its entry
  naming the file (vanilla entries leave the name empty and the game uses its own table);
- a sound per track (ui_sound_db.bin ids 600+, label SOUND<id + 1>, in the Sound Test) with its
  title / Sound Test title / source / staff / copyright texts in sound.msbt (MsndN_ / MsndN2_ /
  MsndS_ / MsndW_ / MsndO_), Ultimate's own texts;
- NewStage01's song list (ui_sound_db.bin, cosmetic id 0x38) set to them, in Ultimate's order;
- a My Music group (bgm_mymusic.mmb) named NewStage01, with Ultimate's odds (incidence 10000 /
  5000 / 2500 -> rarity 100 / 50 / 25). The game finds a stage's group by the stage-kind name, but
  takes the group names from its own 94-name table (0x1041CE18) unless 0x02A7BA48 (a stub that
  returns 0) says otherwise; RPX_PATCH makes it read them from each group's 0x20-byte name field
  instead (empty in vanilla), so this file names every group.

Audio: Ultimate's Opus streams decoded (nus3audio_opus.py) and encoded to DSP-ADPCM (tools/dspadpcm,
built here with cc) in an IDSP, Smash 4's BGM format: 47999 Hz like every Smash 4 BGM, Ultimate's
loop points.
"""
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402
import nus3audio_opus  # noqa: E402
import s4param  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = 'NewStage01'
STAGE_COSMETIC = 0x38
RATE = 47999                    # every Smash 4 BGM's (0xBB7F)
VOLUME = 4.6                    # TONE volume: Battlefield's; the tracks are as loud as its (-14 dB RMS)
FIRST_SOUND = 600               # after the game's 600 (0-599)
BINF_ID = 6200                  # bank ids: unique per bank, the game's go up to 6136
RPX_PATCH = '0x0311CE50=0x38600001'     # bl 0x02A7BA48 -> li r3, 1: group names from bgm_mymusic.mmb

MYMUSIC_NAMES = [
    'BattleField_f', 'BattleFieldL_f', 'End_f', 'MarioU', 'Galaxy', 'XDolpic', 'MarioKart', 'XKart',
    'XMansion', 'DKReturns', '64Jungle', 'Skyward', 'XOldin', 'DxShrine', 'Metroid', 'XNorfair',
    'XFzero', 'YoshiU', 'DxYorster', 'Cave', 'XHalberd', 'Assault', 'XStarfox', 'Kalos', 'XStadium',
    'DxOnett', 'Colloseum_f', 'XEmblem', 'Gw3', 'Angeland', 'XPalutena', 'Gamer', 'PikminU',
    'Village2', 'XVillage', 'WiiFit', 'PunchOut', 'PunchOut2', 'XenoBlade', 'DuckHunt', 'XDonkey',
    'Wrecking', 'Pilotwings', 'Wufu', 'Windyhill', 'Wily', 'Pacland', 'Event_Map', 'Order_CrazySide',
    'Order_CrazySide_Success', 'Order_Reward_Get', 'Order_Reward_Lost', 'Order_MasterSide',
    'Allstar_f', 'OptionSound', 'OnlineTraining_f', 'SimpleIntroScene', 'SimpleResultScene_Lose',
    'SimpleResultScene', 'SimpleResultScene_Final', 'SimpleResultScene_Failure',
    'SimpleRootmapScene', 'Playable_roll_f', 'Bomb_f', 'BombResult_f', 'Tournament_Result',
    'Tournament_Table', 'Tournament_Table_Watching', 'FigShopScene', 'Rush_f', 'EndingFigGetScene',
    'FigListScene', 'Homerun_f', 'Menu', 'AlbumScene', 'World_Boss_YellowDevil', 'World_Boss_Face',
    'World_Boss_Ridley', 'World_Map', 'World_Map_5Turns', 'World_Map_Battle', 'Battlefieldk_f',
    'VSResult', 'Tournament_Entry', 'Tournament_FighterSelect', 'Miiverse', 'StreetFighter_f',
    'Pupupuland64_f', 'PeachCastle64_f', 'Hyrule64_f', 'XPirates_f', 'MarioMaker_f', 'Midgar_f',
    'Umbra_f']

# Sound Test mix icon (Sm4shMusic's SoundMixType): 0 original, 3 new remix
ORIGINAL, NEW_REMIX = 0, 3
ARR = 'Composition Copyright Mojang AB\nArrangement Copyright Nintendo'

# Ultimate's playlist order (order0); file, bank title, title, source, staff, copyright, rarity, mix
TRACKS = [
    ('bgm_mc04_mcd_halland_dalarna', 'MC04_HallandDalarna', 'Halland / Dalarna', 'Minecraft Dungeons',
     'Arrangement Supervisor: ACE (TOMOri Kudo / CHiCO)',
     'Composition: Mojang AB\nArrangement: SEKAI WALKER Producers LLC.\n' + ARR, 100, NEW_REMIX),
    ('bgm_mc03_mce_earth', 'MC03_Earth', 'Earth', 'Minecraft Earth',
     'Arrangement Supervisor: Mitsuhiro Kitadani',
     'Composition: Mojang AB\nArrangement: BANDAI NAMCO Studios Inc.\n' + ARR, 50, NEW_REMIX),
    ('bgm_mc06_mc_clockworkcrafter', 'MC06_ClockworkCrafter', 'Clockwork Crafter', 'Minecraft',
     '', 'Composition and arrangement Copyright Mojang AB', 25, ORIGINAL),
    ('bgm_mc02_mc_toysonatear', 'MC02_ToysOnATear', 'Toys on a Tear', 'Minecraft',
     'Arrangement Supervisor: Yuzo Koshiro',
     'Composition: Mojang AB\nArrangement: Ancient-corp.\n' + ARR, 25, NEW_REMIX),
    ('bgm_mc07_mc_danceoftheblocks', 'MC07_DanceOfTheBlocks', 'Dance of the Blocks', 'Minecraft',
     'Arrangement Supervisor: Yoko Shimomura',
     'Composition: Mojang AB\nArrangement: Midiplex Co., Ltd.\n' + ARR, 25, NEW_REMIX),
    ('bgm_mc01_mc_glide', 'MC01_Glide', 'Glide', 'Minecraft',
     'Arrangement Supervisor: Hiroki Hashimoto',
     'Composition: Mojang AB\nArrangement: BANDAI NAMCO Studios Inc.\n' + ARR, 25, NEW_REMIX),
    ('bgm_mc05_mcd_thearchillager', 'MC05_TheArchIllager', 'The Arch-Illager', 'Minecraft Dungeons',
     'Arrangement: Motoi Sakuraba', 'Composition: Mojang AB\n' + ARR, 25, NEW_REMIX),
]


# ---------------------------------------------------------------- audio

def dspenc():
    exe = os.path.join(tempfile.gettempdir(), 'dspenc_%d' % os.getpid())
    src = os.path.join(HERE, 'dspadpcm')
    subprocess.run(['cc', '-O2', '-o', exe, os.path.join(src, 'dspenc.c'), os.path.join(src, 'grok.c'),
                    '-lm'], check=True)
    return exe


def encode(exe, mono, loop):
    """(coefs, ps, loop_ps, loop_yn1, loop_yn2, adpcm frames)"""
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, 'in.s16'), os.path.join(tmp, 'out.bin')
        mono.astype('<i2').tofile(src)
        subprocess.run([exe, src, dst, str(loop)], check=True)
        d = open(dst, 'rb').read()
    return d[:32], d[32:34], d[34:36], d[36:38], d[38:40], d[40:]


def nibble(sample):
    return sample // 14 * 16 + 2 + sample % 14


def idsp(exe, pcm, loop_start, loop_end):
    """Namco IDSP (big-endian): header 0x40, a 0x60-byte DSP header per channel, then the channels'
    ADPCM interleaved every 0x10 bytes"""
    n, ch = pcm.shape
    frames = (n + 13) // 14
    frames += frames & 1                    # whole 0x10-byte interleave blocks
    size = frames * 8
    heads, data = b'', []
    for c in range(ch):
        coefs, ps, loop_ps, yn1, yn2, adpcm = encode(exe, pcm[:, c], loop_start)
        data.append(adpcm.ljust(size, b'\0'))
        h = struct.pack('>IIIHHIII', n, size * 2, RATE, 1, 0, nibble(loop_start), nibble(loop_end), 2)
        h += coefs + struct.pack('>H', 0) + ps + b'\0\0\0\0' + loop_ps + yn1 + yn2
        heads += h.ljust(0x60, b'\0')
    body = np.stack([np.frombuffer(d, np.uint8).reshape(-1, 0x10) for d in data], 1).tobytes()
    head = struct.pack('>4sI10I', b'IDSP', 0, ch, RATE, n, loop_start, loop_end, 0x10, 0x40, 0x60,
                       0x40 + 0x60 * ch, size).ljust(0x40, b'\0')
    return head + heads + body


# ---------------------------------------------------------------- banks

def sections(d):
    assert d[:4] == b'NUS3' and d[8:16] == b'BANKTOC '
    count = struct.unpack('<I', d[20:24])[0]
    q = 24 + count * 8
    out = []
    for i in range(count):
        name, size = struct.unpack('<4sI', d[24 + i * 8:32 + i * 8])
        out.append([name, d[q + 8:q + 8 + size]])
        q += 8 + size
    return out


def bank(template, title, binf_id, pack, n, loop_start, loop_end, channels):
    secs = sections(template)
    for s in secs:
        if s[0] == b'BINF':
            name = ('snd_bgm_' + title).encode() + b'\0'
            b = struct.pack('<II', 0, 3) + bytes([len(name)]) + name
            s[1] = b.ljust((len(b) + 3) & ~3, b'\0') + struct.pack('<I', binf_id)
        elif s[0] == b'TONE':
            t = s[1]
            old = t[0x18]
            rest = t[(0x19 + old + 3) & ~3:]        # 12 bytes, pack size, volume, ..., stream info
            name = title.encode() + b'\0'
            e = t[0x0C:0x18] + bytes([len(name)]) + name
            e = e.ljust((0x0C + len(e) + 3 & ~3) - 0x0C, b'\0') + rest
            e = bytearray(e)
            o = len(e) - len(rest) + 12
            e[o:o + 8] = struct.pack('<If', len(pack), VOLUME)
            e[-0x20:-0x08] = struct.pack('<6I', RATE, channels, n, loop_start, loop_end, 1)
            s[1] = struct.pack('<III', 1, 0x0C, len(e)) + bytes(e)
        elif s[0] == b'PACK':
            s[1] = pack
    toc = b''.join(struct.pack('<4sI', nm, len(b)) for nm, b in secs)
    body = b'BANKTOC ' + struct.pack('<II', 4 + len(toc), len(secs)) + toc
    body += b''.join(nm + struct.pack('<I', len(b)) + b for nm, b in secs)
    return b'NUS3' + struct.pack('<I', len(body)) + body


# ---------------------------------------------------------------- config

def property_file(data, new):
    """new: [(bgm id, title, (14 ints))]"""
    count = struct.unpack('<I', data[8:12])[0]
    offs = list(struct.unpack('<%dI' % count, data[12:12 + 4 * count]))
    base = 12 + 4 * count
    entries = {i: data[base + o:base + o + 0x74] for i, o in enumerate(offs) if o != 0xFFFFFFFF}
    for i, title, vals in new:
        assert i not in entries
        entries[i] = title.encode().ljust(0x3C, b'\0') + struct.pack('<14i', *vals)
    count = max(count, max(entries) + 1)
    table, body = [], b''
    for i in range(count):
        if i in entries:
            table.append(len(body))
            body += entries[i]
        else:
            table.append(0xFFFFFFFF)
    return data[:8] + struct.pack('<I%dI' % count, count, *table) + body


def free_bgm_ids(data, n):
    count = struct.unpack('<I', data[8:12])[0]
    offs = struct.unpack('<%dI' % count, data[12:12 + 4 * count])
    return [i for i in range(1, count) if offs[i] == 0xFFFFFFFF][:n]


def mymusic_file(data, group):
    """every group named (MYMUSIC_NAMES), plus group = (name, [(bgm id, rarity)])"""
    count = struct.unpack('<I', data[8:12])[0]
    assert count == len(MYMUSIC_NAMES)
    offs = struct.unpack('<%dI' % count, data[12:12 + 4 * count])
    base = 12 + 4 * count
    groups = []
    for i, o in enumerate(offs):
        assert data[base + o:base + o + 0x20] == b'\0' * 0x20
        n = struct.unpack('<I', data[base + o + 0x20:base + o + 0x24])[0]
        groups.append((MYMUSIC_NAMES[i], data[base + o + 0x20:base + o + 0x24 + n * 0x3C]))
    name, songs = group
    body = struct.pack('<I', len(songs))
    for k, (bgm, rarity) in enumerate(songs):
        body += struct.pack('<ihhihhi4i', bgm, k + 1, -1, rarity, -1, 0, 0, 0, 0, 0, 0).ljust(0x3C, b'\0')
    groups.append((name, body))
    table, out = [], b''
    for name, g in groups:
        table.append(len(out))
        out += name.encode().ljust(0x20, b'\0') + g
    return data[:8] + struct.pack('<I%dI' % len(groups), len(groups), *table) + out


def sound_db(data, songs):
    """songs: [(sound id, bgm id, mix)]; adds the sounds and sets NewStage01's list to them"""
    items = s4param.parse(data)
    groups = [it for it in items if isinstance(it, list) and it[0] == 'group']
    stages, sounds = groups[0], groups[2]
    battlefield = next(e for e in sounds[2] if e[0][1] == 0)
    for sid, bgm, mix in songs:
        assert all(e[0][1] != sid for e in sounds[2])
        e = list(battlefield)
        e[0] = (5, sid)
        e[1] = (5, bgm)
        e[13] = (5, mix)
        e[25] = (8, b'SOUND%d' % (sid + 1))
        e[26] = (6, 999)                    # Sound Test / stage creation order: Sm4shMusic's
        e[27] = (6, 999)
        sounds[2].append(e)
    sounds[1] = len(sounds[2])
    st = next(e for e in stages[2] if e[0][1] == STAGE_COSMETIC)
    ids = [sid for sid, _, _ in songs]
    st[1] = (st[1][0], len(ids))
    for k in range(2, len(st)):
        st[k] = (st[k][0], ids[k - 2] if k - 2 < len(ids) else 0xFFFFFFFF)
    return s4param.build(items, data[:8])


# ---------------------------------------------------------------- main

def main():
    if len(sys.argv) != 7:
        sys.exit(__doc__)
    audio, template, config, param, msbt_path, out = sys.argv[1:]
    template = open(template, 'rb').read()
    mpb = open(os.path.join(config, 'bgm_property.mpb'), 'rb').read()
    mmb = open(os.path.join(config, 'bgm_mymusic.mmb'), 'rb').read()
    sdb = open(os.path.join(param, 'ui', 'ui_sound_db.bin'), 'rb').read()
    text = msbt.Msbt(open(msbt_path, 'rb').read())
    for d in ('sound/bgm', 'sound/config', 'param/ui', 'ui/message'):
        os.makedirs(os.path.join(out, d), exist_ok=True)

    exe = dspenc()
    bgm_ids = free_bgm_ids(mpb, len(TRACKS))
    props, songs, group = [], [], []
    for k, (src, title, name, source, staff, copyright, rarity, mix) in enumerate(TRACKS):
        pcm, rate, ls, le = nus3audio_opus.decode(os.path.join(audio, src + '.nus3audio'))
        assert rate == 48000 and pcm.shape[1] == 2
        n = len(pcm)
        pack = idsp(exe, pcm, ls, le)
        open(os.path.join(out, 'sound', 'bgm', 'snd_bgm_%s.nus3bank' % title), 'wb').write(
            bank(template, title, BINF_ID + k, pack, n, ls, le, pcm.shape[1]))
        ms = lambda s: s * 1000 // RATE  # noqa: E731
        bgm, sid = bgm_ids[k], FIRST_SOUND + k
        props.append((bgm, title, (1, -1, 400, -1, -1, -1, -1, -1, ms(ls), ms(le), ls, le, ms(n), n)))
        songs.append((sid, bgm, mix))
        group.append((bgm, rarity))
        label = 'SOUND%d' % (sid + 1)
        for pre, t in (('MsndN_', name), ('MsndN2_', name), ('MsndS_', source), ('MsndW_', staff),
                       ('MsndO_', copyright)):
            text.set(pre + label, t)
        print('%-22s bgm %4d  sound %d (%s)  %.1f s, loop %d-%d' % (title, bgm, sid, label, n / rate, ls, le))
    os.unlink(exe)

    open(os.path.join(out, 'sound', 'config', 'bgm_property.mpb'), 'wb').write(property_file(mpb, props))
    open(os.path.join(out, 'sound', 'config', 'bgm_mymusic.mmb'), 'wb').write(mymusic_file(mmb, (STAGE, group)))
    open(os.path.join(out, 'param', 'ui', 'ui_sound_db.bin'), 'wb').write(sound_db(sdb, songs))
    open(os.path.join(out, 'ui', 'message', 'sound.msbt'), 'wb').write(text.build())
    print('RPX patch:', RPX_PATCH)


if __name__ == '__main__':
    main()
