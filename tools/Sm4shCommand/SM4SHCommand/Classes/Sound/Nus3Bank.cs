using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>What a TONE entry holds.</summary>
    public enum ToneKind
    {
        /// <summary>A sound: a data block (its word 8) pointing at audio in PACK.</summary>
        Audio,
        /// <summary>An unused slot (the 12-byte stubs vanilla banks have between their tones), or a data block with no audio.</summary>
        Empty,
        /// <summary>A container (+4 = 0x7F: the game picks one of other tones; snd_se_joucyu's futtobi_meteor_).</summary>
        Container,
        /// <summary>Something this reader doesn't know (kept as it is).</summary>
        Unknown,
    }

    /// <summary>
    /// One TONE entry of a nus3bank (v1.7.32, the Sound Effect Viewer; written for part 2's tone adding too).
    /// Entry layout (little-endian): 12 bytes (flags), a name-length byte, the name (NUL-terminated), padding to 4,
    /// 4 zero bytes, then the data block: u32 8, u32 PACK offset, u32 size, f32 volume (dB), ... and at the end the
    /// rate / channels / samples / loop fields (their place varies between entries: the audio's own header, IDSP, is
    /// read instead). The entry's bytes are kept (Entry): Build writes them back unchanged unless changed here.
    /// </summary>
    public class Tone
    {
        public Nus3Bank Bank;
        public int Index;               // in TONE (what soundlabeltable labels point at)
        public string Name = "";        // snd_se_Gekkouga_IceBoom; "" for an empty slot
        public ToneKind Kind;
        public byte[] Entry;            // the TONE entry as stored
        public int DataBlock = -1;      // offset of the data block (u32 8) in Entry, -1 when none
        public uint DataOffset, DataSize;   // the audio in PACK
        public string Codec = "";       // "IDSP" (Namco's DSP-ADPCM wrapper: every tone seen so far), else the magic
        public int Channels, SampleRate, Samples, LoopStart, LoopEnd;
        public bool Loops;

        public double Seconds { get { return SampleRate > 0 ? Samples / (double)SampleRate : 0; } }

        /// <summary>The tone's volume in dB (the data block's +12: what the game plays it at; vanilla -20 .. +6).</summary>
        public float VolumeDb
        {
            get { return DataBlock >= 0 && DataBlock + 16 <= Entry.Length ? BitConverter.ToSingle(Entry, DataBlock + 12) : 0f; }
            set
            {
                if (DataBlock < 0 || DataBlock + 16 > Entry.Length) throw new InvalidOperationException("tone " + Index + " has no data block");
                var b = BitConverter.GetBytes(value);
                if (!BitConverter.IsLittleEndian) Array.Reverse(b);
                Array.Copy(b, 0, Entry, DataBlock + 12, 4);
            }
        }

        public bool HasAudio { get { return Kind == ToneKind.Audio && DataSize > 0; } }

        public override string ToString() { return Index + ": " + (Name.Length > 0 ? Name : "(" + Kind.ToString().ToLowerInvariant() + ")"); }

        /// <summary>Reads one TONE entry (bytes from the bank: checked, never trusted).</summary>
        public static Tone Parse(byte[] e, int index)
        {
            var t = new Tone { Index = index, Entry = e, Kind = ToneKind.Empty };
            if (e.Length < 0x10)
                return t;                           // the 12-byte stubs (00000000 01000000 ff000000)
            int nl = e[0x0C];
            if (0x0D + nl > e.Length)
            {
                t.Kind = ToneKind.Unknown;
                return t;
            }
            t.Name = nl > 0 ? Encoding.ASCII.GetString(e, 0x0D, Math.Max(0, nl - 1)).TrimEnd('\0') : "";
            if (e[4] == 0x7F)
            {
                t.Kind = ToneKind.Container;
                return t;
            }
            int q = ((0x0D + nl + 3) & ~3) + 4;
            if (q + 16 > e.Length || Nus3Bank.U32(e, q) != 8)
            {
                t.Kind = ToneKind.Unknown;
                return t;
            }
            t.DataBlock = q;
            t.DataOffset = Nus3Bank.U32(e, q + 4);
            t.DataSize = Nus3Bank.U32(e, q + 8);
            t.Kind = t.DataSize > 0 ? ToneKind.Audio : ToneKind.Empty;
            return t;
        }

        /// <summary>Fills Codec, Channels ... from the start of the tone's audio (its IDSP header).</summary>
        internal void ReadHeader(byte[] h)
        {
            if (h.Length < 4) return;
            Codec = Encoding.ASCII.GetString(h, 0, 4);
            if (Codec == "IDSP" && h.Length >= 0x30)
            {
                var info = Idsp.Header(h);
                if (info != null)
                {
                    Channels = info.Channels; SampleRate = info.SampleRate; Samples = info.Samples;
                    LoopStart = info.LoopStart; LoopEnd = info.LoopEnd; Loops = info.Loops;
                }
            }
            else if (!IsPrintable(Codec))
                Codec = BitConverter.ToString(h, 0, 4).Replace("-", "");
        }

        static bool IsPrintable(string s)
        {
            foreach (char c in s) if (c < 0x20 || c > 0x7E) return false;
            return true;
        }
    }

    /// <summary>
    /// A Smash 4 (Wii U) sound bank, .nus3bank (v1.7.32). 'NUS3', u32 size, 'BANKTOC ', u32 toc size, u32 section count,
    /// (name, size) per section, then the sections (name, size, body): PROP, BINF (the bank's name and id: the id
    /// soundlabeltable.bin rows name), GRP, DTON, TONE (u32 count, (offset, size) per entry, the entries), JUNK, PACK
    /// (the audio, Namco IDSP = DSP-ADPCM). All little-endian but the audio's own headers (big-endian).
    /// Loads everything but PACK, which is read from the file when a tone is played (or the bank rebuilt), so a big
    /// bank (snd_se_joucyu, 10 MB) opens fast. Build() writes the bank back from this model (byte-identical when nothing
    /// changed: checked on vanilla and modded banks), the base part 2 adds tones on.
    /// </summary>
    public class Nus3Bank
    {
        public string Path;
        public string Name = "";                    // BINF's name (snd_se_Gekkouga)
        public uint Id;                             // BINF's id (2058)
        public readonly List<Tone> Tones = new List<Tone>();
        // the sections in file order: name and body (PACK's body null: on disk at packOffset)
        public readonly List<KeyValuePair<string, byte[]>> Sections = new List<KeyValuePair<string, byte[]>>();
        long packOffset = -1;
        uint packSize;
        int binfIdAt = -1;                          // the id word's offset in BINF's body

        public long PackOffset { get { return packOffset; } }
        public uint PackSize { get { return packSize; } }

        internal static uint U32(byte[] b, int at)
        {
            return (uint)(b[at] | b[at + 1] << 8 | b[at + 2] << 16 | b[at + 3] << 24);
        }

        internal static void Put32(byte[] b, int at, uint v)
        {
            b[at] = (byte)v; b[at + 1] = (byte)(v >> 8); b[at + 2] = (byte)(v >> 16); b[at + 3] = (byte)(v >> 24);
        }

        static byte[] ReadExactly(Stream s, long at, int n)
        {
            s.Position = at;
            var b = new byte[n];
            int got = 0;
            while (got < n)
            {
                int r = s.Read(b, got, n - got);
                if (r <= 0) throw new InvalidDataException("the file ends early");
                got += r;
            }
            return b;
        }

        public static Nus3Bank Load(string path)
        {
            using (var s = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                return Load(s, path);
        }

        public static Nus3Bank Load(Stream s, string path)
        {
            var bank = new Nus3Bank { Path = path };
            long len = s.Length;
            if (len < 24) throw new InvalidDataException("not a nus3bank (too small)");
            var head = ReadExactly(s, 0, 24);
            if (Encoding.ASCII.GetString(head, 0, 4) != "NUS3" || Encoding.ASCII.GetString(head, 8, 8) != "BANKTOC ")
                throw new InvalidDataException("not a nus3bank (no NUS3 / BANKTOC)");
            uint count = U32(head, 20);
            if (count == 0 || count > 64) throw new InvalidDataException("bad section count " + count);
            var toc = ReadExactly(s, 24, (int)(8 * count));
            long q = 24 + 8 * count;
            for (int i = 0; i < count; i++)
            {
                string nm = Encoding.ASCII.GetString(toc, 8 * i, 4);
                uint size = U32(toc, 8 * i + 4);
                if (q + 8 + size > len) throw new InvalidDataException("section " + nm + " runs past the file's end");
                if (nm == "PACK")
                {
                    bank.packOffset = q + 8;
                    bank.packSize = size;
                    bank.Sections.Add(new KeyValuePair<string, byte[]>(nm, null));
                }
                else
                {
                    if (size > 64 << 20) throw new InvalidDataException("section " + nm + " too big");
                    bank.Sections.Add(new KeyValuePair<string, byte[]>(nm, ReadExactly(s, q + 8, (int)size)));
                }
                q += 8 + size;
            }
            foreach (var sec in bank.Sections)
            {
                if (sec.Key == "BINF") bank.ReadBinf(sec.Value);
                else if (sec.Key == "TONE") bank.ReadTones(sec.Value);
            }
            if (bank.packOffset >= 0)
                foreach (var t in bank.Tones)
                    if (t.HasAudio && t.DataOffset + (long)t.DataSize <= bank.packSize)
                        t.ReadHeader(ReadExactly(s, bank.packOffset + t.DataOffset, (int)Math.Min(t.DataSize, 0x40 + 0x60 * 2)));
                    else if (t.HasAudio)
                        t.Codec = "(past PACK)";
            return bank;
        }

        void ReadBinf(byte[] b)
        {
            if (b.Length < 9) return;
            int n = b[8];
            if (9 + n > b.Length) return;
            Name = Encoding.ASCII.GetString(b, 9, Math.Max(0, n - 1)).TrimEnd('\0');
            int at = (9 + n + 3) & ~3;
            if (at + 4 <= b.Length)
            {
                binfIdAt = at;
                Id = U32(b, at);
            }
        }

        void ReadTones(byte[] t)
        {
            if (t.Length < 4) return;
            uint n = U32(t, 0);
            if (4 + 8L * n > t.Length) throw new InvalidDataException("TONE table runs past its section");
            for (int i = 0; i < n; i++)
            {
                uint o = U32(t, 4 + 8 * i), sz = U32(t, 8 + 8 * i);
                if (o + (long)sz > t.Length) throw new InvalidDataException("tone " + i + " runs past TONE");
                var e = new byte[sz];
                Array.Copy(t, o, e, 0, sz);
                var tone = Tone.Parse(e, i);
                tone.Bank = this;
                Tones.Add(tone);
            }
        }

        /// <summary>The tone's audio (its IDSP file), read from the bank's file.</summary>
        public byte[] ReadAudio(Tone t)
        {
            if (!t.HasAudio) return null;
            if (packOffset < 0 || t.DataOffset + (long)t.DataSize > packSize)
                throw new InvalidDataException(t.Name + ": its audio isn't inside PACK");
            using (var s = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                return ReadExactly(s, packOffset + t.DataOffset, (int)t.DataSize);
        }

        /// <summary>PACK as on disk.</summary>
        public byte[] ReadPack()
        {
            if (packOffset < 0) return new byte[0];
            using (var s = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                return ReadExactly(s, packOffset, (int)packSize);
        }

        /// <summary>The TONE section from Tones (count, offset / size table, the entries back to back: the game's
        /// layout).</summary>
        public byte[] BuildTone()
        {
            int n = Tones.Count, total = 4 + 8 * n;
            foreach (var t in Tones) total += t.Entry.Length;
            var b = new byte[total];
            Put32(b, 0, (uint)n);
            int at = 4 + 8 * n;
            for (int i = 0; i < n; i++)
            {
                var e = Tones[i].Entry;
                Put32(b, 4 + 8 * i, (uint)at);
                Put32(b, 8 + 8 * i, (uint)e.Length);
                Array.Copy(e, 0, b, at, e.Length);
                at += e.Length;
            }
            return b;
        }

        /// <summary>The whole bank from this model: BINF with Id, TONE from Tones, PACK from the file unless given (part 2
        /// passes the PACK with its new audio appended).</summary>
        public byte[] Build(byte[] pack = null)
        {
            var bodies = new List<KeyValuePair<string, byte[]>>();
            foreach (var sec in Sections)
            {
                byte[] body = sec.Value;
                if (sec.Key == "TONE") body = BuildTone();
                else if (sec.Key == "PACK") body = pack ?? ReadPack();
                else if (sec.Key == "BINF" && binfIdAt >= 0)
                {
                    body = (byte[])body.Clone();
                    Put32(body, binfIdAt, Id);
                }
                bodies.Add(new KeyValuePair<string, byte[]>(sec.Key, body));
            }
            var ms = new MemoryStream();
            var w = new BinaryWriter(ms);
            w.Write(Encoding.ASCII.GetBytes("NUS3"));
            w.Write(0u);                                    // the size, below
            w.Write(Encoding.ASCII.GetBytes("BANKTOC "));
            w.Write((uint)(4 + 8 * bodies.Count));
            w.Write((uint)bodies.Count);
            foreach (var b in bodies) { w.Write(Encoding.ASCII.GetBytes(b.Key)); w.Write((uint)b.Value.Length); }
            foreach (var b in bodies) { w.Write(Encoding.ASCII.GetBytes(b.Key)); w.Write((uint)b.Value.Length); w.Write(b.Value); }
            w.Flush();
            var outb = ms.ToArray();
            Put32(outb, 4, (uint)(outb.Length - 8));
            return outb;
        }
    }
}
