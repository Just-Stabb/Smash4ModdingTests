#!/usr/bin/env python3
"""Greninja's added sounds (skeleton v1.5, fighters/gekkouga/README.md "Skeleton v1.5"): the Running Skeleton's, the
user's clips (tools/fighter_own_bank.py's route: Namco IDSP DSP-ADPCM one-shots, 48000 Hz mono, peak -0.5 dBFS, a TONE
entry copied from his Special_L01 one-shot) appended to his own se bank (snd_se_Gekkouga, id 2058: kept) and to his
soundlabeltable row (bank 2058's: row 1896 = 0x768, sound ids 0x0768xxxx; its labels list extended, the other rows as
they are).

  python3 -I tools/gekkouga_sound.py VANILLA_FIGHTER SOUNDLABELTABLE SND_DIR OUT
      VANILLA_FIGHTER  his fighter/gekkouga (sound/snd_se_Gekkouga.nus3bank)
      SOUNDLABELTABLE  the user's current sound/config/soundlabeltable.bin
      SND_DIR          the user's clips (SOUNDS' files)
      OUT              gets fighter/gekkouga/sound/snd_se_Gekkouga.nus3bank, sound/config/soundlabeltable.bin

Each clip: leading / trailing silence trimmed (under -45 dBFS), mono 48 kHz, its peak -0.5 dBFS (the route's), then the
TONE's volume (dB) per SOUNDS. Prints each sound id, label and length (frames at 60 fps).
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fighter_own_bank as FB  # noqa: E402
import minecraft_music as mm  # noqa: E402

NAME = 'Gekkouga'
BANK_ID = 2058
# (label name, file, TONE volume dB): their order is their labels' (his row's label count onwards)
SOUNDS = (('SkSpawn1', 'spawn_ding.mp3', 0.0),
          ('SkSpawn2', 'spawn_running.mp3', 0.0),
          ('SkVoice1', 'idle_rahhh.mp3', -3.0),      # its voices a little under the rest (they repeat while it runs)
          ('SkVoice2', 'idle_voice2.mp3', -3.0),
          ('SkDeath', 'death_drybones.mp3', 0.0),
          ('SkBoom', 'explode_deltarune.mp3', 0.0))   # at full (the route's peak): as loud as his own hits
SILENCE_DB = -45


def trimmed(path, tmp):
    """the clip with its leading / trailing silence removed (ffmpeg silenceremove both ends), as a wav"""
    out = os.path.join(tmp, os.path.basename(path) + '.wav')
    f = 'silenceremove=start_periods=1:start_threshold=%ddB:detection=peak,areverse,' \
        'silenceremove=start_periods=1:start_threshold=%ddB:detection=peak,areverse' % (SILENCE_DB, SILENCE_DB)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-af', f, out], check=True)
    return out


def build(van_fighter, table_path, snd_dir, out):
    """{label name: (sound id, frames at 60 fps)}"""
    bank_path = os.path.join(van_fighter, 'sound', 'snd_se_%s.nus3bank' % NAME)
    data = open(bank_path, 'rb').read()
    name, bid = FB.binf(data)
    assert (name, bid) == ('snd_se_' + NAME, BANK_ID), (name, bid)
    table = FB.Table(open(table_path, 'rb').read())
    row = table.row_of(BANK_ID)
    old = table.tones(row)
    exe = mm.dspenc()
    sounds, lens = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for label, f, vol in SOUNDS:
            pcm = FB.load_audio(trimmed(os.path.join(snd_dir, f), tmp))
            sounds.append((label, FB.idsp_oneshot(exe, pcm), vol))
            lens[label] = len(pcm) * 60 / FB.RATE
    os.remove(exe)
    bank, first = FB.build_bank(data, NAME, BANK_ID, sounds)
    table.set_row(row, old + list(range(first, first + len(sounds))))
    od = os.path.join(out, 'fighter', 'gekkouga', 'sound')
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, os.path.basename(bank_path)), 'wb').write(bank)
    oc = os.path.join(out, 'sound', 'config')
    os.makedirs(oc, exist_ok=True)
    open(os.path.join(oc, 'soundlabeltable.bin'), 'wb').write(table.data())
    return {label: (row << 16 | (len(old) + k), lens[label]) for k, (label, _f, _v) in enumerate(SOUNDS)}


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) != 4:
        sys.exit(__doc__)
    for k, (sid, n) in build(*a).items():
        print('0x%08X %-10s %.1f frames' % (sid, k, n))
