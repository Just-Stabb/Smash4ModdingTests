"""The KAME_* values tools/supamario_kame_build.py put into fighters/supamario/weapons/kamehameha.c for test 30 /
fighters_latest (read back from that kamehameha.mscsb; compiling the source with them gives it back byte for
byte), so the projectile's MSC can be rebuilt without the XV2 package: Supamario fix 85 adds KAME_CREEP.

  python3 -c "import supamario_kame_values"   (tools/ on the path; VALS)
"""
VALS = {'KAME_FINISH': '33', 'KAME_DISSOLVE': '33', 'KAME_SEG_EVERY': '2', 'KAME_SEG_FIRST': '4', 'KAME_MAX': '165',
        'KAME_FX_OFF': '\n'.join('    EffectModule(0x2723, %s, 0x1, 0x1);' % e for e in
                                 ('0x3410021', '0x341001e', '0x3410026', '0x3410027', '0x3410028')),
        'KAME_SPEED_1': '5.0f', 'KAME_SPEED_2': '5.5f', 'KAME_SPEED_3': '6.0f',
        'KAME_LIFE_1': '48', 'KAME_LIFE_2': '58', 'KAME_LIFE_3': '67',
        'KAME_HOLD_1': '20', 'KAME_HOLD_2': '30', 'KAME_HOLD_3': '45',
        'KAME_DIS_1': '0x3410029', 'KAME_DIS_2': '0x341002a', 'KAME_DIS_3': '0x341002b',
        'KAME_SEG_1': '0x3410026', 'KAME_SEG_2': '0x3410027', 'KAME_SEG_3': '0x3410028'}
