#!/usr/bin/env python3
"""Greninja's added sounds (skeleton v1.5, fighters/gekkouga/README.md "Skeleton v1.5"): the Running Skeleton's, the
user's clips (tools/fighter_own_bank.py's route: Namco IDSP DSP-ADPCM one-shots, 48000 Hz mono, peak -0.5 dBFS, a TONE
entry copied from his Special_L01 one-shot) appended to his own se bank (snd_se_Gekkouga, id 2058: kept) and to his
soundlabeltable row (bank 2058's: row 1896 = 0x768, sound ids 0x0768xxxx; its labels list extended, the other rows as
they are).

  python3 -I tools/gekkouga_sound.py VANILLA_FIGHTER SOUNDLABELTABLE SND_DIR OUT [--ice=CLIP]
      VANILLA_FIGHTER  his fighter/gekkouga (sound/snd_se_Gekkouga.nus3bank)
      SOUNDLABELTABLE  the user's current sound/config/soundlabeltable.bin
      SND_DIR          the user's clips (SOUNDS' files)
      OUT              gets fighter/gekkouga/sound/snd_se_Gekkouga.nus3bank, sound/config/soundlabeltable.bin

Each clip: leading / trailing silence trimmed (under -45 dBFS), mono 48 kHz, its peak -0.5 dBFS (the route's), then the
TONE's volume (dB) per SOUNDS. Prints each sound id, label and length (frames at 60 fps).

--ice=CLIP (usmash spike v2 / trail dim v1, README "Ice detonation sound"): the ice detonation's fuse and boom (the user's
creeper_explosion.mp3) as label 97 (IceBoom, 0x07680061) after the six, placed so its boom's onset (boom_onset: 1 ms
windows) comes ICE_SND_LEAD frames after its start (the executable asks for it on the ice hit that arms the countdown; the
blast lands that many frames later): with the 156-frame countdown the whole clip fits (its clicks and fuse hiss), so it is
padded with silence in front (ice_cut; a clip with more before its boom would be cut, faded in over 5 ms), at its own
speed and pitch, its trailing silence trimmed.
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
ICE_SOUND = ('IceBoom', 'creeper_explosion.mp3', 4.0)   # label 97; TONE +4 dB: peak-normalised as the rest, its boom is a
                                  # sharp crack (its loudest 400 ms -12.2 dB RMS) where the skeleton's SkBoom (which the ice
                                  # blast played until now) is a dense blast (-5.9 dB): +4 dB brings it near (-8.2 dB) inside
                                  # the game's own TONE range (vanilla se banks: up to +6.2 dB, Master's; his own up to +2)
ICE_FADE_IN = 0.005               # seconds: no click at the cut (mid-hiss)
ONSET_WIN = 0.001                 # boom_onset's windows (1 ms)
ONSET_SMOOTH = 0.010               # the boom: the first 10 ms (moving RMS) within ONSET_LOUD_DB of the clip's loudest 10 ms
ONSET_LOUD_DB = 6.0               # (the hiss's loudest 10 ms are ~-12 dBFS, the boom's ~-3 at the source's level) ...
ONSET_RISE_DB = 6.0               # ... its onset: walking back from there over 1 ms windows, the first of the rise (6 dB
                                  # over the median of the 100 ms before it)


def boom_onset(x, rate):
    """seconds: the boom's onset in a mono clip x (floats): the first 1 ms window of the rise into the first 10 ms within
    ONSET_LOUD_DB of the clip's loudest 10 ms"""
    import numpy as np
    w = int(round(rate * ONSET_WIN))
    n = len(x) // w
    p = (np.asarray(x[:n * w], np.float64).reshape(n, w) ** 2).mean(1)
    e = 10 * np.log10(np.maximum(p, 1e-12))
    m = int(round(ONSET_SMOOTH / ONSET_WIN))
    c = np.cumsum(np.r_[0.0, p])
    s = 10 * np.log10(np.maximum((c[m:] - c[:-m]) / m, 1e-12))   # s[k]: windows k .. k + m - 1
    loud = int(np.argmax(s >= s.max() - ONSET_LOUD_DB))
    base = float(np.median(e[max(0, loud - 100):max(1, loud - 5)]))
    k = loud + int(np.argmax(e[loud:loud + m] >= base + ONSET_RISE_DB))
    while k > 0 and e[k - 1] >= base + ONSET_RISE_DB:
        k -= 1
    return k * ONSET_WIN


def ice_cut(path, tmp):
    """the ice clip as a wav: its boom's onset ICE_SND_LEAD frames from its start (start = onset - that: < 0 pads that much
    silence in front, > 0 cuts there and fades in over ICE_FADE_IN), its trailing silence trimmed; (wav, onset in the
    source, start)"""
    import numpy as np
    import gekkouga_clone_cave as C
    raw = os.path.join(tmp, 'ice.f32')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(FB.RATE), '-f', 'f32le', raw], check=True)
    on = boom_onset(np.fromfile(raw, '<f4'), FB.RATE)
    start = on - C.ICE_SND_LEAD / 60.0
    out = os.path.join(tmp, 'ice.wav')
    head = ('atrim=start=%.6f,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=%g' % (start, ICE_FADE_IN) if start > 0 else
            'adelay=delays=%dS:all=1' % int(round(-start * FB.RATE)))
    f = head + ',areverse,silenceremove=start_periods=1:start_threshold=%ddB:detection=peak,areverse' % SILENCE_DB
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(FB.RATE), '-ac', '1', '-i', raw, '-af', f,
                    '-c:a', 'pcm_s16le', out], check=True)
    return out, on, start


def trimmed(path, tmp):
    """the clip with its leading / trailing silence removed (ffmpeg silenceremove both ends), as a wav"""
    out = os.path.join(tmp, os.path.basename(path) + '.wav')
    f = 'silenceremove=start_periods=1:start_threshold=%ddB:detection=peak,areverse,' \
        'silenceremove=start_periods=1:start_threshold=%ddB:detection=peak,areverse' % (SILENCE_DB, SILENCE_DB)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-af', f, out], check=True)
    return out


def build(van_fighter, table_path, snd_dir, out, ice=None):
    """{label name: (sound id, frames at 60 fps)}; ice: the ice detonation's clip (ICE_SOUND, label 97) or None"""
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
        if ice:
            label, _f, vol = ICE_SOUND
            pcm = FB.load_audio(ice_cut(ice, tmp)[0])
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
    return {label: (row << 16 | (len(old) + k), lens[label]) for k, (label, _f, _v) in
            enumerate(SOUNDS + ((ICE_SOUND,) if ice else ()))}


if __name__ == '__main__':
    ice = next((x[6:] for x in sys.argv[1:] if x.startswith('--ice=')), None)
    a = [x for x in sys.argv[1:] if not x.startswith('--ice=')]
    if len(a) != 4:
        sys.exit(__doc__)
    for k, (sid, n) in build(*a, ice=ice).items():
        print('0x%08X %-10s %.1f frames' % (sid, k, n))
