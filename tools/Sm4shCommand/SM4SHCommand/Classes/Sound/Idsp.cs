using System;
using System.IO;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>Decoded audio: 16-bit PCM, channels interleaved.</summary>
    public class AudioClip
    {
        public short[] Pcm;
        public int Channels, SampleRate, Samples, LoopStart, LoopEnd;   // loop points in samples, LoopEnd inclusive
        public bool Loops;
    }

    /// <summary>
    /// Namco IDSP, the audio of every Smash 4 (Wii U) tone (v1.7.32): DSP-ADPCM (the GameCube / Wii DSP's codec) with a
    /// big-endian header. 0x00 'IDSP', 0x04 0, 0x08 channels, 0x0C rate, 0x10 samples, 0x14 loop start, 0x18 loop end
    /// (samples, inclusive), 0x1C interleave (0x10), 0x20 header size (0x40), 0x24 channel header size (0x60), 0x28 data
    /// offset (0x40 + 0x60 x channels), 0x2C data size per channel; then per channel the standard DSP header (samples,
    /// nibbles, rate, u16 loop flag, u16 format, loop start / end / current nibble, the 16 coefficients at +0x1C,
    /// gain, ps, yn1, yn2 at +0x40, loop ps / yn1 / yn2); then the channels' 8-byte frames (a header byte: predictor
    /// &lt;&lt; 4 | scale exponent, then 14 4-bit samples), interleaved every 0x10 bytes. The layout tools/fighter_own_bank.py
    /// and tools/minecraft_music.py write (tools/dspadpcm encodes); decoded as the DSP does (vgmstream's formula).
    /// </summary>
    public static class Idsp
    {
        public class Info
        {
            public int Channels, SampleRate, Samples, LoopStart, LoopEnd, Interleave, HeaderSize, ChannelHeaderSize, DataOffset, DataSize;
            public bool Loops;
        }

        static int BE32(byte[] b, int at) { return b[at] << 24 | b[at + 1] << 16 | b[at + 2] << 8 | b[at + 3]; }
        static short BE16(byte[] b, int at) { return (short)(b[at] << 8 | b[at + 1]); }

        /// <summary>The header (null when it isn't a usable IDSP header).</summary>
        public static Info Header(byte[] b)
        {
            if (b.Length < 0x30 || Encoding.ASCII.GetString(b, 0, 4) != "IDSP") return null;
            var i = new Info
            {
                Channels = BE32(b, 0x08), SampleRate = BE32(b, 0x0C), Samples = BE32(b, 0x10), LoopStart = BE32(b, 0x14),
                LoopEnd = BE32(b, 0x18), Interleave = BE32(b, 0x1C), HeaderSize = BE32(b, 0x20), ChannelHeaderSize = BE32(b, 0x24),
                DataOffset = BE32(b, 0x28), DataSize = BE32(b, 0x2C),
            };
            if (i.Channels < 1 || i.Channels > 8 || i.SampleRate <= 0 || i.SampleRate > 192000 || i.Samples < 0) return null;
            if (i.HeaderSize <= 0) i.HeaderSize = 0x40;
            if (i.ChannelHeaderSize <= 0) i.ChannelHeaderSize = 0x60;
            // the loop flag is the DSP header's (+0x0C of the first channel's); a one-shot has 0 (its IDSP loop end may be 0 or n - 1)
            int ch0 = i.HeaderSize;
            i.Loops = b.Length >= ch0 + 0x0E ? BE16(b, ch0 + 0x0C) != 0 : i.LoopEnd > 0;
            if (i.LoopEnd >= i.Samples) i.LoopEnd = i.Samples - 1;
            if (i.LoopStart < 0 || i.LoopStart > i.LoopEnd) { i.LoopStart = 0; if (i.Loops) i.LoopEnd = i.Samples - 1; }
            return i;
        }

        /// <summary>Decodes a tone's IDSP file.</summary>
        public static AudioClip Decode(byte[] b)
        {
            var h = Header(b);
            if (h == null) throw new InvalidDataException("not an IDSP file");
            int ch = h.Channels, n = h.Samples;
            if (h.HeaderSize + (long)h.ChannelHeaderSize * ch > b.Length) throw new InvalidDataException("IDSP: the channel headers run past the file");
            if ((long)n * ch > 64 << 20) throw new InvalidDataException("IDSP: too long");
            int il = h.Interleave > 0 ? h.Interleave : 8;
            var pcm = new short[(long)n * ch];
            int frames = (n + 13) / 14;
            for (int c = 0; c < ch; c++)
            {
                int hd = h.HeaderSize + h.ChannelHeaderSize * c;
                var coef = new int[16];
                for (int k = 0; k < 16; k++) coef[k] = BE16(b, hd + 0x1C + 2 * k);
                int hist1 = hd + 0x44 <= b.Length ? BE16(b, hd + 0x40) : 0, hist2 = hd + 0x44 <= b.Length ? BE16(b, hd + 0x42) : 0;
                for (int f = 0; f < frames; f++)
                {
                    long pos = (long)f * 8;
                    long at = ch == 1 ? h.DataOffset + pos : h.DataOffset + pos / il * il * ch + (long)c * il + pos % il;
                    if (at + 8 > b.Length) break;               // a cut file: the rest stays silent
                    int ps = b[at], pred = (ps >> 4) & 7, scale = 1 << (ps & 0xF);
                    int c1 = coef[pred * 2], c2 = coef[pred * 2 + 1];
                    for (int k = 0; k < 14; k++)
                    {
                        int s = f * 14 + k;
                        if (s >= n) break;
                        int bt = b[at + 1 + k / 2];
                        int nib = (k & 1) == 0 ? bt >> 4 : bt & 0xF;
                        if (nib >= 8) nib -= 16;
                        long v = ((long)nib * scale << 11) + 1024 + (long)c1 * hist1 + (long)c2 * hist2;
                        v >>= 11;
                        if (v > 32767) v = 32767; else if (v < -32768) v = -32768;
                        hist2 = hist1;
                        hist1 = (int)v;
                        pcm[(long)s * ch + c] = (short)v;
                    }
                }
            }
            return new AudioClip { Pcm = pcm, Channels = ch, SampleRate = h.SampleRate, Samples = n, LoopStart = h.LoopStart, LoopEnd = h.LoopEnd, Loops = h.Loops };
        }

        /// <summary>
        /// The PCM a preview plays: the clip at gainDb (clipped), and, when it loops and loopSeconds &gt; 0, its loop
        /// (LoopStart .. LoopEnd) repeated after the intro until about that long (the game holds a looping tone until
        /// it is stopped: Transient_Sound_Effect / Stop_Sound_Effect).
        /// </summary>
        public static short[] Preview(AudioClip a, double gainDb, double loopSeconds)
        {
            int ch = a.Channels;
            long frames = a.Samples;
            bool loop = a.Loops && loopSeconds > 0 && a.LoopEnd > a.LoopStart;
            long body = loop ? a.LoopEnd - a.LoopStart + 1 : 0;
            long want = loop ? Math.Max(a.LoopEnd + 1, (long)(loopSeconds * a.SampleRate)) : frames;
            int reps = loop ? (int)Math.Max(1, (want - (a.LoopEnd + 1) + body - 1) / body) : 0;
            long total = loop ? a.LoopEnd + 1 + reps * body : frames;
            var o = new short[total * ch];
            double g = Math.Pow(10, gainDb / 20);
            for (long s = 0; s < total; s++)
            {
                long src = s <= (loop ? a.LoopEnd : frames - 1) ? s : a.LoopStart + (s - a.LoopEnd - 1) % body;
                for (int c = 0; c < ch; c++)
                {
                    double v = a.Pcm[src * ch + c] * g;
                    o[s * ch + c] = (short)(v > 32767 ? 32767 : v < -32768 ? -32768 : Math.Round(v));
                }
            }
            return o;
        }

        /// <summary>A 16-bit PCM WAV file (what System.Media.SoundPlayer plays from memory).</summary>
        public static byte[] Wav(short[] pcm, int channels, int rate)
        {
            var ms = new MemoryStream();
            var w = new BinaryWriter(ms);
            int data = pcm.Length * 2;
            w.Write(Encoding.ASCII.GetBytes("RIFF")); w.Write(36 + data); w.Write(Encoding.ASCII.GetBytes("WAVE"));
            w.Write(Encoding.ASCII.GetBytes("fmt ")); w.Write(16); w.Write((short)1); w.Write((short)channels);
            w.Write(rate); w.Write(rate * channels * 2); w.Write((short)(channels * 2)); w.Write((short)16);
            w.Write(Encoding.ASCII.GetBytes("data")); w.Write(data);
            foreach (var s in pcm) w.Write(s);
            w.Flush();
            return ms.ToArray();
        }
    }
}
