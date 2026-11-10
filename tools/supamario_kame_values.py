"""The KAME_* values tools/supamario_kame_build.py put into fighters/supamario/weapons/kamehameha.c for test 30 /
fighters_latest (read back from that kamehameha.mscsb; compiling the source with them gives it back byte for
byte), so the projectile's MSC can be rebuilt without the XV2 package: Supamario fix 85 adds KAME_CREEP.

  python3 -c "import supamario_kame_values"   (tools/ on the path; VALS; SUPAMARIO_FX: Supamario's own MSC)
"""
VALS = {'KAME_FINISH': '33', 'KAME_DISSOLVE': '33', 'KAME_SEG_EVERY': '2', 'KAME_SEG_FIRST': '4', 'KAME_MAX': '165',
        'KAME_FX_OFF': '\n'.join('    EffectModule(0x2723, %s, 0x1, 0x1);' % e for e in
                                 ('0x3410021', '0x341001e', '0x3410026', '0x3410027', '0x3410028')),
        'KAME_SPEED_1': '5.0f', 'KAME_SPEED_2': '5.5f', 'KAME_SPEED_3': '6.0f',
        'KAME_LIFE_1': '48', 'KAME_LIFE_2': '58', 'KAME_LIFE_3': '67',
        'KAME_HOLD_1': '20', 'KAME_HOLD_2': '30', 'KAME_HOLD_3': '45',
        'KAME_DIS_1': '0x3410029', 'KAME_DIS_2': '0x341002a', 'KAME_DIS_3': '0x341002b',
        'KAME_SEG_1': '0x3410026', 'KAME_SEG_2': '0x3410027', 'KAME_SEG_3': '0x3410028'}


# Supamario's MSC (fighters/supamario/supamario.c): the effect ids and the start effects the package build put in
# (read back from fix 85-90's supamario.mscsb: the source compiles with them to the same functions, msc_fingerprint
# 0 differ), so supamario.mscsb can be rebuilt without the XV2 package: supamario_kame_build.py --msc-only OUT.mscsb
# (universal mechanics, 2026-11-10)
SUPAMARIO_FX = {
    'KAME_FX_CRG': '0x03410019', 'KAME_FX_CRGON': '0x0341001A', 'KAME_FX_TSUBU': '0x0341001F',
    'KAME_N_START_FX': '\n'.join([
        '    if (kame_n_level() == 0)',
        '    {',
        '        EffectModule(0x2710, 0x341001b, 0, 0, 6.699999809265137f, 14.050000190734863f, 0, 180.0f, 0, 1.600000023841858f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410017, 0, 0, 6.699999809265137f, 12.774999618530273f, 0, 180.0f, 0, 1.600000023841858f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410018, 0, 0, 6.699999809265137f, 12.774999618530273f, 0, 180.0f, 0, 1.600000023841858f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410022, 0, 0, 6.699999809265137f, 14.050000190734863f, 0, 180.0f, 0, 0.44999998807907104f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x341001c, 0, 0, 6.699999809265137f, 11.5f, 0, 180.0f, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0x1);',
        '    }',
        '    else if (kame_n_level() == 0x1)',
        '    {',
        '        EffectModule(0x2710, 0x341001b, 0, 0, 6.699999809265137f, 15.75f, 0, 180.0f, 0, 1.7999999523162842f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410017, 0, 0, 6.699999809265137f, 13.625f, 0, 180.0f, 0, 2.0f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410018, 0, 0, 6.699999809265137f, 13.625f, 0, 180.0f, 0, 2.0f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410022, 0, 0, 6.699999809265137f, 15.75f, 0, 180.0f, 0, 0.5f, 0, 0, 0, 0, 0, 0, 0x1);',
        '    }',
        '    else if (kame_n_level() == 0x2)',
        '    {',
        '        EffectModule(0x2710, 0x341001b, 0, 0, 6.699999809265137f, 17.450000762939453f, 0, 180.0f, 0, 2.200000047683716f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410017, 0, 0, 6.699999809265137f, 14.475000381469727f, 0, 180.0f, 0, 2.0f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410018, 0, 0, 6.699999809265137f, 14.475000381469727f, 0, 180.0f, 0, 2.0f, 0, 0, 0, 0, 0, 0, 0x1);',
        '        EffectModule(0x2710, 0x3410022, 0, 0, 6.699999809265137f, 17.450000762939453f, 0, 180.0f, 0, 0.6000000238418579f, 0, 0, 0, 0, 0, 0, 0x1);',
        '    }',
    ]),
    'KAME_N_START_OFF': '\n'.join([
        '    EffectModule(0x2723, 0x341001b, 0x1, 0x1);',
        '    EffectModule(0x2723, 0x3410017, 0x1, 0x1);',
        '    EffectModule(0x2723, 0x3410018, 0x1, 0x1);',
        '    EffectModule(0x2723, 0x3410022, 0x1, 0x1);',
        '    EffectModule(0x2723, 0x341001c, 0x1, 0x1);',
    ])}
