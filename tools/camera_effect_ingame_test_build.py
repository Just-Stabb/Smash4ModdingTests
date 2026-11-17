#!/usr/bin/env python3
"""TEST_ONLY files for Effect_Camera (camera_effects v2: one test per taunt), built on the user's own Dr. Mario
(every other script and effect kept as it is):

  python3 tools/camera_effect_ingame_test_build.py MARIOD_DIR COMMON_EFFECT_DIR OUT_DIR

MARIOD_DIR: the fighter/mariod folder (script/animcmd/body/{game,effect}.bin, effect/mariod/mariod.010d0000.{efc,ptcl}).
COMMON_EFFECT_DIR: effect/common (common.010d0000.{efc,ptcl}: the black quad's emitter is copied from it).
OUT_DIR gets script/animcmd/body/{game,effect}.bin and effect/mariod/mariod.010d0000.{efc,ptcl}.

Why v2 (v1's test, user: "a massive white flash, I can't see anything else"): v1 used common 0x1000042 for "stars"
(the tooltip's MSC-sheet label "Multiple white stars flashing"), but efc entry 0x42 is PtcCommonThunder: five ADDITIVE
emitters, white / orange flashes 8 - 40 units wide (a particle's scale is its quad's full width, the quad -0.5..0.5,
cross_f 0x04A66B9C), looping. At Mode 1 Size 0.08 its 40-unit flare was 40 x 0.08 / 2 = 1.6 screen heights wide over
the top-right corner for 120 frames: the screen blown out to white. The command's maths was right (the matrix scale
0.6 = 0.08 x 20 x tan(0.358)); the effect and its size were wrong. v1's Timer swirl at Size 0.12 was 1.2 screen heights
(its additive parts black, its alpha parts a dark swirl) and the ice smoke at Size 1 / Z 30 a whole screen of faint
white smoke.

v2's test (user, Dr. Mario): up "a massive white flash during the freeze", side "stars relative to Dr. Mario
instead of the top right corner", down "seems to work". The clip: the white is Stage_Freeze's (frames 20-139 exactly its
120 frames, cut in one frame; the black quad, killed then, faded out as a small dark blob over frames 140-144), the
stars world-fixed far from the camera. v3 splits every case (camera_effects v3, both facings marked):
  AppealHiR  game: Stage_Freeze(1, 120)   the new default (the update stopped, the stage not told): no white expected
  AppealHiL  game: Stage_Freeze(2, 120)   the game's full stop (v2's): the white expected
  AppealLwL  game: Stage_Freeze(3, 120)   the Final Smashes' stop (full stop + their effect class hidden / paused)
  AppealSR   effect: the dizzy stars 0x100002C, Mode 1 X 1.4 Y 0.7 Z 20 Size 0.08, Frames 90 (top-right corner)
  AppealSL   effect: the black quad DARK_QUAD (CamFxDarkQuad, alpha-blended, one 2-unit particle), Mode 1 Size 2,
             black 60 %, Frames 120, unslowed (the whole screen darker)
  AppealLwR  effect: the ice smoke 0x100003F, Mode 0 Z 30 Size 0.25 (a quarter of the screen, centred, fades by itself)
No effect taunt has a Stage_Freeze; no freeze taunt an effect.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import efc as EFC  # noqa: E402
import ptcl as PT  # noqa: E402

BANK = 0x324                    # Dr. Mario's bank (0x300 + kind 0x24)
QUAD_SRC = ('PtcCommonSuperscopeBullet', 'RayGunShotFlash2_Copy1')
QUAD_SET = 'CamFxDarkQuad'
QUAD_WIDTH = 2.0
STARS, SMOKE = 0x100002C, 0x100003F
FREEZE_FRAMES = 120


def cmd(name, **kw):
    """an ACMD command by its Sm4shCommand name, its parameters by name (acmd_info.json's syntax, all given)"""
    hit = [(k, v) for k, v in acmd.INFO.items() if v['name'] == name]
    assert len(hit) == 1, name
    ident, info = hit[0]
    syn = info['syntax']
    assert sorted(syn) == sorted(kw), (name, syn, sorted(kw))
    return acmd.Command(ident, [kw[s] for s in syn])


def camfx(graphic, x, y, z, size, mode, frames, flags=0):
    return cmd('Effect_Camera', Graphic=graphic, X=x, Y=y, Z=z, XRot=0.0, YRot=0.0, ZRot=0.0, Size=size, Mode=mode,
               Frames=frames, Flags=flags)


def scripts(quad_id):
    """v3: each case alone on its own taunt (no Stage_Freeze with any effect); three Stage_Freeze taunts alone"""
    end = cmd('Script_End')

    def freeze(on):
        return [cmd('FRAME', Frames=2.0), cmd('Stage_Freeze', On=on, Frames=FREEZE_FRAMES), end]
    stars = [cmd('FRAME', Frames=2.0), camfx(STARS, 1.4, 0.7, 20.0, 0.08, 1, 90), end]
    quad = [cmd('FRAME', Frames=2.0), camfx(quad_id, 0.0, 0.0, 20.0, 2.0, 1, 120, 1),
            cmd('LAST_EFFECT_SET_COLOR', Red=0.0, Green=0.0, Blue=0.0), cmd('LAST_EFFECT_SET_ALPHA', Alpha=60.0), end]
    smoke = [cmd('FRAME', Frames=2.0), camfx(SMOKE, 0.0, 0.0, 30.0, 0.25, 0, 0), end]
    game = {'AppealHiR': freeze(1), 'AppealHiL': freeze(2), 'AppealLwL': freeze(3)}
    effect = {'AppealSR': stars, 'AppealSL': quad, 'AppealLwR': smoke,      # the freeze taunts: no effect at all
              'AppealHiR': [end], 'AppealHiL': [end], 'AppealLwL': [end]}
    return game, effect


def dark_quad(bank, common):
    """the black quad's emitter, from the common bank's RayGunShotFlash2_Copy1 (its shader / texture imported)"""
    si = common.find_set(QUAD_SRC[0])
    k = [common.emitter_name(e['data']) for e in common.sets[si]['emitters']].index(QUAD_SRC[1])
    em = bank.import_emitter(common, si, k)
    sf = bank.set_field
    assert bank.field(em, 'blend_type') == 0 and bank.field(em, 'particle_type') == 0
    assert struct.unpack_from('>I', em, 0x314)[0] == 1          # colour 0 x texture, alpha = texture alpha (R R R 1: 1)
    assert bank.texres(em, 0)['comp_sel'] == 5                    # R R R 1
    struct.pack_into('>B', em, 0x2FF, 1)                          # one-time: one particle, then nothing
    sf(em, 'start_frame', 0)
    sf(em, 'emit_start', 0)
    sf(em, 'end_frame', 1)
    sf(em, 'emit_rate', 1.0)
    sf(em, 'emit_interval', 0)
    sf(em, 'emit_interval_random', 0)
    sf(em, 'ptcl_life', 0x7FFFFFFF)                               # lives until the set fades
    sf(em, 'ptcl_life_random', 0)
    struct.pack_into('>f', em, 0x82C, 0.125)                      # the fade (Frames / Terminate): 8 frames
    struct.pack_into('>B', em, 0x2F9, 1)                          # no emission while fading
    sf(em, 'volume_type', 0)
    sf(em, 'volume_radius', [0.0, 0.0, 0.0])
    for name in ('figure_velocity', 'init_velocity_random', 'emitter_velocity', 'air_resistance'):
        sf(em, name, 0.0 if name != 'air_resistance' else 1.0)
    sf(em, 'gravity', [0.0, 0.0, 0.0])
    sf(em, 'alpha_init', 1.0)
    sf(em, 'alpha_diff21', 0.0)
    sf(em, 'alpha_diff32', 0.0)
    sf(em, 'scale_random', [0.0, 0.0])
    sf(em, 'scale', [QUAD_WIDTH, QUAD_WIDTH])
    sf(em, 'scale_init_ratio', [1.0, 1.0])
    sf(em, 'scale_diff21', [0.0, 0.0])
    sf(em, 'scale_diff32', [0.0, 0.0])
    for name in ('rotation_init', 'rotation_random', 'rotation_velocity', 'rotation_velocity_random'):
        sf(em, name, [0.0, 0.0, 0.0])
    sf(em, 'color0_type', 0)
    sf(em, 'color0_keys', [1.0] * 32)
    sf(em, 'color_scale', 1.0)
    sf(em, 'camera_offset', 0.0)
    struct.pack_into('>I', em, 0x310, 0)                          # follows the set
    bank.set_emitter_srt(em)
    return em


def main():
    mdir, cdir, out = sys.argv[1:4]
    body, edir = os.path.join(mdir, 'script/animcmd/body'), os.path.join(mdir, 'effect/mariod')
    common = PT.Ptcl(open(os.path.join(cdir, 'common.010d0000.ptcl'), 'rb').read())
    bank = PT.Ptcl(open(os.path.join(edir, 'mariod.010d0000.ptcl'), 'rb').read())
    efc = EFC.Efc(open(os.path.join(edir, 'mariod.010d0000.efc'), 'rb').read())
    n_sets = len(bank.sets)
    si = bank.new_set(QUAD_SET, [dark_quad(bank, common)], ['CamFxDarkQuad1'])
    entry = efc.add(si + 1)
    quad_id = (BANK << 16) | entry
    errs = bank.validate()
    assert not errs, errs
    os.makedirs(os.path.join(out, 'effect/mariod'), exist_ok=True)
    os.makedirs(os.path.join(out, 'script/animcmd/body'), exist_ok=True)
    data = bank.build()
    open(os.path.join(out, 'effect/mariod/mariod.010d0000.ptcl'), 'wb').write(data)
    open(os.path.join(out, 'effect/mariod/mariod.010d0000.efc'), 'wb').write(efc.build())
    back = PT.Ptcl(data)
    assert len(back.sets) == n_sets + 1 and back.set_name(si) == QUAD_SET and not back.validate()
    old = PT.Ptcl(open(os.path.join(edir, 'mariod.010d0000.ptcl'), 'rb').read())
    for i in range(n_sets):            # every earlier set's emitters byte for byte (bar the moved data offsets)
        assert [len(e['data'] or b'') for e in back.sets[i]['emitters']] == \
               [len(e['data'] or b'') for e in old.sets[i]['emitters']]
    print('bank: %d sets (+1 %s), efc entry %d: Graphic 0x%X' % (len(back.sets), QUAD_SET, entry, quad_id))
    game_s, fx_s = scripts(quad_id)
    for fn, add in (('game.bin', game_s), ('effect.bin', fx_s)):
        f = acmd.ACMDFile.load(os.path.join(body, fn))
        n = len(f.scripts)
        for name, sc in add.items():
            f.scripts[acmd.crc(name)] = sc
        f.save(os.path.join(out, 'script/animcmd/body', fn))
        b = acmd.ACMDFile.load(os.path.join(out, 'script/animcmd/body', fn))
        for name, sc in add.items():
            assert [str(c) for c in b.scripts[acmd.crc(name)]] == [str(c) for c in sc]
        print('%s: %d scripts (+%d new), set: %s' % (fn, len(b.scripts), len(b.scripts) - n, ', '.join(add)))
        for name in sorted(add):
            print('  %s:\n%s' % (name, acmd.fmt_script(b.scripts[acmd.crc(name)], '    ')))


if __name__ == '__main__':
    main()
