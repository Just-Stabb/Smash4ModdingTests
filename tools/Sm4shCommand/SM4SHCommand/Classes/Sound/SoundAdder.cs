using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>One sound waiting to be added (v1.7.33, the Sound Adder): the file, the settings, and once prepared the
    /// 48 kHz 16-bit PCM and its IDSP; once planned its label, sound id and tone index.</summary>
    public class PendingSound
    {
        public string Source;                   // the audio file
        public string ToneName = "";            // snd_se_Gekkouga_IceBoom2
        public string Alias = "";
        public float VolumeDb;                  // the TONE volume (dB)
        public bool Trim = true;                // leading / trailing silence
        public double TrimDb = -45;             // the silence threshold (dBFS, peak)
        public bool Normalize = true;           // peak to -0.5 dBFS (tools/fighter_own_bank.py's)
        public bool Loop;                       // loops (whole clip) in game: hold with Transient_Sound_Effect

        public PcmAudio Input;                  // as read (kept: changing the settings doesn't read the file again)
        public short[] Pcm;                     // what is encoded: BankRate, Channels
        public int Channels, Rate = AudioImport.BankRate;
        public byte[] Idsp;
        public string How = "", Error;
        string preparedKey;

        // the plan (SoundAdder.Plan)
        public int Label = -1, ToneIndex = -1;
        public uint Id;
        public Tone Tone;                       // its TONE entry in the target bank, with the audio in memory
        public SoundEntry Entry;                // its row in the viewer's list

        public int Samples { get { return Pcm != null && Channels > 0 ? Pcm.Length / Channels : 0; } }
        public double Seconds { get { return Samples / (double)Rate; } }

        string Key() { return string.Format(CultureInfo.InvariantCulture, "{0}|{1}|{2}|{3}|{4}", Source, Trim, TrimDb, Normalize, Loop); }

        /// <summary>Reads (once), trims, resamples, normalises and encodes, when a setting that changes the audio changed.</summary>
        public void Prepare()
        {
            if (Idsp != null && preparedKey == Key()) return;
            Error = null;
            if (Input == null) Input = AudioImport.Read(Source);
            var a = Input;
            How = a.How;
            if (Trim)
            {
                int before = a.Frames;
                a = AudioImport.TrimSilence(a, TrimDb);
                if (a.Frames < before) How += string.Format(CultureInfo.InvariantCulture, ", {0:0.000} s of silence trimmed", (before - a.Frames) / (double)a.Rate);
            }
            if (a.Frames == 0) throw new InvalidDataException(Path.GetFileName(Source) + ": nothing above " + TrimDb.ToString("0", CultureInfo.InvariantCulture) + " dBFS (all silence?)");
            if (a.Rate != AudioImport.BankRate)
            {
                a = AudioImport.Resample(a, AudioImport.BankRate);
                How += ", resampled " + Input.Rate + " -> " + AudioImport.BankRate + " Hz";
            }
            Channels = a.Channels;
            Rate = AudioImport.BankRate;
            Pcm = AudioImport.ToPcm16(a, Normalize);
            if (Normalize) How += ", peak -0.5 dBFS";
            Idsp = IdspWriter.Encode(Pcm, Channels, Rate, Loop);
            How += ", DSP-ADPCM " + (Channels == 1 ? "mono" : "stereo") + (Loop ? ", loops" : ", one-shot");
            preparedKey = Key();
        }

        /// <summary>The name a file gets: the bank's prefix (its BINF name: snd_se_Gekkouga_) and the file's name.</summary>
        public static string DefaultName(Nus3Bank bank, string file)
        {
            var sb = new StringBuilder();
            string f = file ?? "";
            int slash = Math.Max(f.LastIndexOf('\\'), f.LastIndexOf('/'));     // (a Windows path read anywhere)
            foreach (char c in Path.GetFileNameWithoutExtension(slash >= 0 ? f.Substring(slash + 1) : f))
                sb.Append(c < 128 && (char.IsLetterOrDigit(c) || c == '_') ? c : '_');
            string n = sb.ToString().Trim('_');
            if (n.Length == 0) n = "New";
            return (bank != null && bank.Name.Length > 0 ? bank.Name : "snd_se") + "_" + n;
        }
    }

    /// <summary>
    /// The Sound Adder (v1.7.33): new tones for one of the fighter's banks and their ids, and volume changes on its existing
    /// tones; built, checked and written as the game's own banks are.
    ///
    /// Ids: a new tone gets the next label of the row its bank plays from (its BINF id's row; a port's own id's alias row,
    /// Viewer/SoundBanks.txt; a costume bank's main bank's row): label = the row's label count + k, id = row &lt;&lt; 16 |
    /// label, checked against every id in use in the whole soundlabeltable (every fighter, the common row 0, the ports'
    /// alias rows): a label past the row's count isn't one. Labels are the id's low 16 bits (cross_f.rpx 0x0311EEC4:
    /// clrlwi r5, r4, 16; 0x0311EDC4 only checks label &lt; the row's count), so a row holds at most 65536 labels.
    ///
    /// Tones: the TONE entry is a copy of a one-shot of the same bank (its _Special_L01 when it has one, as
    /// tools/fighter_own_bank.py, else its first mono one-shot; a stereo sound copies a stereo one-shot when the bank has
    /// one) with its name, PACK offset / size, volume and the tail's rate / channels / samples / loop set; the audio is
    /// appended to PACK at a 0x10 boundary (vanilla banks pack tones back to back, every offset a multiple of 0x10).
    /// JUNK is sized so PACK's body starts at a multiple of 0x10, as in every vanilla bank read (snd_se_Gekkouga,
    /// snd_vc_Gekkouga(_ouen), snd_se_joucyu, snd_se_item, snd_se_Kirby).
    ///
    /// Costume banks (snd_se_NAME_cNN): a player in costume NN loads that bank instead of the main one and plays the
    /// same ids from it (the same row: its own id aliased to the main's, or the main's id), so a label's tone index has
    /// to name the same sound in each. The new tones go into the main bank and, at the same tone index, into each costume
    /// bank of the same kind on the same row (AlsoCostumes, on by default); a bank with fewer tones is padded with empty
    /// 12-byte stubs (vanilla's unused slots) so the index is new in all of them.
    /// </summary>
    public class SoundAdder
    {
        public const int MaxLabels = 0x10000;
        public readonly FighterSounds Sounds;
        public Nus3Bank Target;
        public bool AlsoCostumes = true;
        public readonly List<PendingSound> Pending = new List<PendingSound>();
        /// <summary>Existing tones whose volume was changed: the tone and its volume as loaded.</summary>
        public readonly Dictionary<Tone, float> VolumeEdits = new Dictionary<Tone, float>();
        public readonly List<string> PlanErrors = new List<string>();
        public readonly List<string> PlanNotes = new List<string>();
        HashSet<uint> used;                     // the table's ids in use (once per table)
        SoundLabelTable usedOf;

        public SoundAdder(FighterSounds sounds, Nus3Bank target = null)
        {
            Sounds = sounds;
            Target = target ?? (sounds != null ? DefaultTarget(sounds) : null);
        }

        public static Nus3Bank DefaultTarget(FighterSounds s)
        {
            return s.Fighter.Banks.FirstOrDefault(b => s.Fighter.Kinds[b] == "se") ?? s.Fighter.Banks.FirstOrDefault();
        }

        public bool HasChanges { get { return Pending.Count > 0 || VolumeEdits.Count > 0; } }

        public int Row { get { int r; return Target != null && Sounds.Fighter.RowOfBank.TryGetValue(Target, out r) ? r : -1; } }

        string KindOf(Nus3Bank b) { string k; return Sounds.Fighter.Kinds.TryGetValue(b, out k) ? k : ""; }

        /// <summary>The costume banks that play the target's row (the target being a main bank: se, vc, se_common).</summary>
        public List<Nus3Bank> Costumes()
        {
            var list = new List<Nus3Bank>();
            if (Target == null || !AlsoCostumes) return list;
            string kind = KindOf(Target);
            if (kind.Contains(" c")) return list;
            int row = Row;
            foreach (var b in Sounds.Fighter.Banks)
            {
                if (b == Target) continue;
                string k = KindOf(b);
                int r;
                if (k.StartsWith(kind + " c", StringComparison.Ordinal) && Sounds.Fighter.RowOfBank.TryGetValue(b, out r) && r == row)
                    list.Add(b);
            }
            return list;
        }

        /// <summary>The banks the new tones go into: the target, then its costume banks.</summary>
        public List<Nus3Bank> AddBanks()
        {
            var l = new List<Nus3Bank>();
            if (Target != null) l.Add(Target);
            l.AddRange(Costumes());
            return l;
        }

        /// <summary>The other banks known to play the same row (a port's base fighter's and other ports' on the same alias,
        /// Viewer/SoundBanks.txt): the new labels are new ids for them too (nothing plays them).</summary>
        public List<string> RowSharers(IDictionary<uint, uint> aliases)
        {
            var l = new List<string>();
            if (Target == null || Row < 0 || Sounds.Table == null) return l;
            uint rowBank = Sounds.Table.Rows[Row].BankId;
            if (rowBank != Target.Id) l.Add("bank id " + rowBank + " (the row's own: the base fighter's bank)");
            if (aliases != null)
                foreach (var kv in aliases)
                    if (kv.Value == rowBank && kv.Key != Target.Id && !Sounds.Fighter.Banks.Any(b => b.Id == kv.Key))
                        l.Add("bank id " + kv.Key + " (a port's, through its alias " + kv.Value + ")");
            return l;
        }

        // ---------------------------------------------------------------- templates, entries

        static uint U32(byte[] b, int at) { return Nus3Bank.U32(b, at); }

        /// <summary>The tail's six words (rate, channels, samples, loop start, loop end, loop flag) are at entry end - 0x20.</summary>
        static bool TailMatches(Tone t)
        {
            var e = t.Entry;
            if (e.Length < t.DataBlock + 0x30) return false;
            int at = e.Length - 0x20;
            return U32(e, at) == (uint)t.SampleRate && U32(e, at + 4) == (uint)t.Channels && U32(e, at + 8) == (uint)t.Samples &&
                   U32(e, at + 0x14) == 0;
        }

        /// <summary>The one-shot a new tone's TONE entry is copied from (see the class notes), null when the bank has none.</summary>
        public static Tone Template(Nus3Bank bank, int channels)
        {
            var oneShots = bank.Tones.Where(t => t.HasAudio && t.Codec == "IDSP" && !t.Loops && TailMatches(t)).ToList();
            Func<IEnumerable<Tone>, Tone> pick = ts => ts.FirstOrDefault(t => t.Name.EndsWith("_Special_L01", StringComparison.OrdinalIgnoreCase)) ?? ts.FirstOrDefault();
            if (channels == 2)
            {
                var st = pick(oneShots.Where(t => t.Channels == 2));
                if (st != null) return st;
            }
            return pick(oneShots.Where(t => t.Channels == 1)) ?? pick(oneShots);
        }

        /// <summary>A TONE entry from a template: its first 12 bytes, the name, the template's 4 bytes before its data
        /// block and the data block with the PACK offset / size, volume and the tail set.</summary>
        public static byte[] MakeEntry(Tone template, string name, uint packOffset, uint size, float volumeDb, int rate, int channels, int samples, bool loop)
        {
            var e = template.Entry;
            int q = template.DataBlock;
            var nm = Encoding.ASCII.GetBytes(name + "\0");
            if (nm.Length > 255) throw new ArgumentException("the tone name is longer than 254 characters");
            int head = 0x0D + nm.Length;
            int q2 = ((head + 3) & ~3) + 4;
            var o = new byte[q2 + (e.Length - q)];
            Array.Copy(e, 0, o, 0, 0x0C);
            o[0x0C] = (byte)nm.Length;
            Array.Copy(nm, 0, o, 0x0D, nm.Length);
            Array.Copy(e, q - 4, o, q2 - 4, 4);
            Array.Copy(e, q, o, q2, e.Length - q);
            Nus3Bank.Put32(o, q2 + 4, packOffset);
            Nus3Bank.Put32(o, q2 + 8, size);
            var v = BitConverter.GetBytes(volumeDb);
            if (!BitConverter.IsLittleEndian) Array.Reverse(v);
            Array.Copy(v, 0, o, q2 + 12, 4);
            int t = o.Length - 0x20;
            Nus3Bank.Put32(o, t, (uint)rate);
            Nus3Bank.Put32(o, t + 4, (uint)channels);
            Nus3Bank.Put32(o, t + 8, (uint)samples);
            Nus3Bank.Put32(o, t + 12, 0);
            Nus3Bank.Put32(o, t + 16, loop ? (uint)(samples - 1) : 0);
            Nus3Bank.Put32(o, t + 20, loop ? 1u : 0);
            return o;
        }

        static readonly byte[] EmptyStub = { 0, 0, 0, 0, 1, 0, 0, 0, 0xFF, 0, 0, 0 };

        static byte[] StubOf(Nus3Bank b)
        {
            var s = b.Tones.FirstOrDefault(t => t.Entry.Length == 12 && t.Kind == ToneKind.Empty);
            return s != null ? (byte[])s.Entry.Clone() : (byte[])EmptyStub.Clone();
        }

        static uint Align16(long n) { return (uint)((n + 15) & ~15L); }

        // ---------------------------------------------------------------- the plan

        /// <summary>The tone index the k-th new sound gets in every add bank: past the largest of their tone counts.</summary>
        public int FirstToneIndex { get { return AddBanks().Count == 0 ? 0 : AddBanks().Max(b => b.Tones.Count); } }

        /// <summary>Prepares every sound and gives each its label, id, tone index and its pending TONE entry (in the target).
        /// PlanErrors holds what stops the save (no row, a full row, a clash, a bad name ...).</summary>
        public void Plan()
        {
            PlanErrors.Clear();
            PlanNotes.Clear();
            if (Target == null) { PlanErrors.Add("No bank picked."); return; }
            if (Sounds.Table == null) { PlanErrors.Add("No sound/config/soundlabeltable.bin: pick the game's data folder (Game data..)."); return; }
            int row = Row;
            if (row < 0) { PlanErrors.Add(Path.GetFileName(Target.Path) + " has no row in soundlabeltable.bin (its BINF id " + Target.Id + " has none and no alias): the game can't play it."); return; }
            int count = Sounds.Table.Labels(row).Length;
            int free = MaxLabels - count;
            if (Pending.Count > free)
                PlanErrors.Add(string.Format(CultureInfo.InvariantCulture, "Row 0x{0:X} is full: {1} labels, room for {2} more (a sound id's label is its low 16 bits: 65536 a row), {3} asked.", row, count, free, Pending.Count));
            if (usedOf != Sounds.Table) { used = Sounds.Table.UsedIds(); usedOf = Sounds.Table; }
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var b in AddBanks()) foreach (var t in b.Tones) if (t.Name.Length > 0) names.Add(t.Name);
            int first = FirstToneIndex;
            uint pack = Align16(Target.PackSize);
            for (int k = 0; k < Pending.Count; k++)
            {
                var p = Pending[k];
                p.Label = count + k;
                p.ToneIndex = first + k;
                p.Id = SoundLabelTable.SoundId(row, p.Label);
                p.Tone = null;
                try { p.Prepare(); }
                catch (Exception ex) { p.Error = ex.Message; PlanErrors.Add(Path.GetFileName(p.Source) + ": " + ex.Message); continue; }
                if (p.Label >= MaxLabels) { p.Error = "no label left on the row"; continue; }
                if (used.Contains(p.Id)) PlanErrors.Add(string.Format(CultureInfo.InvariantCulture, "0x{0:X8} is already in use (can't happen: a label past the row's count).", p.Id));
                string err = NameProblem(p.ToneName);
                if (err == null && !names.Add(p.ToneName)) err = "another tone is named " + p.ToneName;
                if (err != null) { p.Error = err; PlanErrors.Add(p.ToneName + ": " + err); }
                var tpl = Template(Target, p.Channels);
                if (tpl == null) { PlanErrors.Add(Path.GetFileName(Target.Path) + " has no one-shot tone to copy a TONE entry from."); return; }
                var entry = MakeEntry(tpl, p.ToneName.Length > 0 ? p.ToneName : "x", pack, (uint)p.Idsp.Length, p.VolumeDb, p.Rate, p.Channels, p.Samples, p.Loop);
                var tone = Tone.Parse(entry, p.ToneIndex);
                tone.Bank = Target;
                tone.PendingAudio = p.Idsp;
                tone.ReadHeader(p.Idsp);
                p.Tone = tone;
                pack = Align16(pack + p.Idsp.Length);
            }
            foreach (var c in Costumes())
                PlanNotes.Add(Path.GetFileName(c.Path) + " (a costume bank on the same row) gets the same tones at the same indexes" +
                              (c.Tones.Count < first ? string.Format(CultureInfo.InvariantCulture, " (padded from {0} to {1} tones with empty slots)", c.Tones.Count, first) : ""));
            if (Target.Tones.Count < first)
                PlanNotes.Add(string.Format(CultureInfo.InvariantCulture, "{0} is padded from {1} to {2} tones with empty slots (a costume bank has more), so the new tones' indexes are new in every bank.",
                                            Path.GetFileName(Target.Path), Target.Tones.Count, first));
        }

        /// <summary>Why a tone name can't be used (null: it can): ASCII letters, digits and _, 1-254 characters.</summary>
        public static string NameProblem(string name)
        {
            if (string.IsNullOrEmpty(name)) return "no name";
            if (name.Length > 254) return "longer than 254 characters";
            foreach (char c in name)
                if (!(c < 128 && (char.IsLetterOrDigit(c) || c == '_'))) return "use letters, digits and _ only ('" + c + "')";
            return null;
        }

        /// <summary>The pending sounds as list entries (new / unsaved), after Plan.</summary>
        public List<SoundEntry> PendingEntries()
        {
            var l = new List<SoundEntry>();
            string kind = Target != null ? KindOf(Target) : "";
            foreach (var p in Pending)
            {
                if (p.Entry == null) p.Entry = new SoundEntry();
                var e = p.Entry;
                e.Pending = p;
                e.Bank = Target;
                e.Kind = kind;
                e.AliasSet = Sounds.Name;
                e.Tone = p.Tone;
                e.Row = Row;
                e.Label = p.Label;
                e.Id = p.Tone != null && p.Label >= 0 && p.Label < MaxLabels ? p.Id : (uint?)null;
                e.Note = p.Error != null ? "new: " + p.Error : "new / unsaved" + (Costumes().Count > 0 ? " (+ " + Costumes().Count + " costume bank" + (Costumes().Count > 1 ? "s" : "") + ")" : "");
                l.Add(e);
            }
            return l;
        }

        /// <summary>A volume change on an existing tone (only its float changes when saved).</summary>
        public void SetVolume(Tone t, float db)
        {
            if (t.PendingAudio != null)
            {
                var p = Pending.FirstOrDefault(x => x.Tone == t);
                if (p != null) p.VolumeDb = db;
                t.VolumeDb = db;
                return;
            }
            if (!VolumeEdits.ContainsKey(t)) VolumeEdits[t] = t.VolumeDb;
            t.VolumeDb = db;
            if (t.VolumeDb == VolumeEdits[t] && BitConverter.GetBytes(db).SequenceEqual(BitConverter.GetBytes(VolumeEdits[t]))) VolumeEdits.Remove(t);
        }

        /// <summary>Back to the loaded state: no pending sounds, the volumes as loaded.</summary>
        public void Discard()
        {
            foreach (var kv in VolumeEdits) kv.Key.VolumeDb = kv.Value;
            VolumeEdits.Clear();
            Pending.Clear();
        }

        // ---------------------------------------------------------------- building

        public class Output
        {
            public readonly Dictionary<Nus3Bank, byte[]> Banks = new Dictionary<Nus3Bank, byte[]>();
            public byte[] Table;                    // null when the table doesn't change (volume edits only)
            public readonly List<string> Problems = new List<string>();
            public readonly List<string> Checks = new List<string>();
            public bool Ok { get { return Problems.Count == 0; } }
        }

        /// <summary>The new banks and table, in memory, checked (BankCheck, and against the originals: every old byte kept but
        /// the volume floats changed, the other label rows byte for byte).</summary>
        public Output Build()
        {
            var o = new Output();
            if (Pending.Count > 0)
            {
                Plan();
                if (PlanErrors.Count > 0) { o.Problems.AddRange(PlanErrors); return o; }
            }
            var banks = new List<Nus3Bank>();
            if (Pending.Count > 0) banks.AddRange(AddBanks());
            foreach (var t in VolumeEdits.Keys) if (!banks.Contains(t.Bank)) banks.Add(t.Bank);
            int first = FirstToneIndex;
            foreach (var b in banks)
            {
                bool adds = Pending.Count > 0 && AddBanks().Contains(b);
                byte[] data;
                if (!adds) data = b.Build();
                else
                {
                    var tones = new List<Tone>(b.Tones);
                    var stub = StubOf(b);
                    while (tones.Count < first) { var s = Tone.Parse((byte[])stub.Clone(), tones.Count); s.Bank = b; tones.Add(s); }
                    var pack = b.ReadPack();
                    var ms = new MemoryStream();
                    ms.Write(pack, 0, pack.Length);
                    foreach (var p in Pending)
                    {
                        while (ms.Length % 16 != 0) ms.WriteByte(0);
                        long off = ms.Length;
                        ms.Write(p.Idsp, 0, p.Idsp.Length);
                        var tpl = Template(b, p.Channels) ?? Template(Target, p.Channels);
                        var e = MakeEntry(tpl, p.ToneName, (uint)off, (uint)p.Idsp.Length, p.VolumeDb, p.Rate, p.Channels, p.Samples, p.Loop);
                        var nt = Tone.Parse(e, tones.Count);
                        nt.Bank = b;
                        tones.Add(nt);
                    }
                    while (ms.Length % 16 != 0) ms.WriteByte(0);
                    data = b.Build(tones, ms.ToArray(), true);
                }
                o.Banks[b] = data;
                var probs = BankCheck.Validate(data, adds ? b.Tones.Count : int.MaxValue, adds);
                foreach (var pr in probs) o.Problems.Add(Path.GetFileName(b.Path) + ": " + pr);
                foreach (var pr in BankCheck.CompareWithOriginal(b, data, adds ? Pending.Count + Math.Max(0, first - b.Tones.Count) : 0, VolumeEdits.Keys.Where(t => t.Bank == b)))
                    o.Problems.Add(Path.GetFileName(b.Path) + ": " + pr);
                if (adds)
                {
                    // read back from the bytes: the new tones there, decoding to the PCM encoded
                    var back = Nus3Bank.Load(new MemoryStream(data), b.Path);
                    for (int k = 0; k < Pending.Count; k++)
                    {
                        var t = back.Tones[first + k];
                        var p = Pending[k];
                        if (t.Name != p.ToneName || !t.HasAudio || t.Codec != "IDSP" || t.Samples != p.Samples || t.Channels != p.Channels || t.Loops != p.Loop || t.VolumeDb != p.VolumeDb)
                            o.Problems.Add(Path.GetFileName(b.Path) + ": tone " + (first + k) + " doesn't read back as " + p.ToneName);
                        else
                        {
                            var bytes = new byte[t.DataSize];
                            Array.Copy(data, back.PackOffset + t.DataOffset, bytes, 0, bytes.Length);
                            if (!bytes.SequenceEqual(p.Idsp)) o.Problems.Add(Path.GetFileName(b.Path) + ": tone " + (first + k) + "'s audio isn't the encoded one");
                        }
                    }
                }
                o.Checks.Add(Path.GetFileName(b.Path) + ": " + (adds ? Pending.Count + " tone(s) added (tones " + first + " - " + (first + Pending.Count - 1) + "), " : "") +
                             VolumeEdits.Keys.Count(t => t.Bank == b) + " volume change(s); " + data.Length + " bytes; " + (probs.Count == 0 ? "layout checked" : probs.Count + " problem(s)"));
            }
            if (Pending.Count > 0)
            {
                var old = Sounds.Table.Build();
                var t = SoundLabelTable.Parse(old);
                var labels = t.Labels(Row).ToList();
                foreach (var p in Pending) labels.Add(p.ToneIndex);
                t.SetLabels(Row, labels);
                o.Table = t.Build();
                foreach (var pr in BankCheck.CompareTables(old, o.Table, Row, Pending.Select(p => p.ToneIndex).ToList())) o.Problems.Add("soundlabeltable.bin: " + pr);
                o.Checks.Add(string.Format(CultureInfo.InvariantCulture, "soundlabeltable.bin: row 0x{0:X} {1} -> {2} labels (ids 0x{3:X8} - 0x{4:X8}); the other {5} rows byte for byte", Row,
                                           labels.Count - Pending.Count, labels.Count, Pending[0].Id, Pending[Pending.Count - 1].Id, t.Rows.Count - 1));
            }
            return o;
        }

        // ---------------------------------------------------------------- saving

        public class Saved
        {
            public readonly List<string> Written = new List<string>();
            public readonly List<string> Backups = new List<string>();
            public string FighterRoot;          // where the viewer reloads from
            public Output Output;
        }

        /// <summary>The data folder of a fighter folder (data/fighter/NAME -> data).</summary>
        public static string DataRootOf(string fighterRoot)
        {
            var parent = Path.GetDirectoryName(fighterRoot);
            if (parent != null && Path.GetFileName(parent).Equals("fighter", StringComparison.OrdinalIgnoreCase))
                return Path.GetDirectoryName(parent) ?? parent;
            return parent ?? fighterRoot;
        }

        public static string Stamp() { return DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture); }

        static void WriteWithBackup(string path, byte[] data, string stamp, Saved s)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            if (File.Exists(path))
            {
                string bak = path + "." + stamp + ".bak";
                File.Copy(path, bak, true);
                s.Backups.Add(bak);
            }
            string tmp = path + ".writing";
            File.WriteAllBytes(tmp, data);
            if (File.Exists(path)) File.Delete(path);
            File.Move(tmp, path);
            s.Written.Add(path);
        }

        /// <summary>
        /// Writes the banks and the table. outRoot null: in place (the fighter's sound folder; the table where it was
        /// found when it is the mod's own, above the fighter's folder, else as the mod's own: DATA/sound/config next to
        /// DATA/fighter); else under outRoot as the game lays it out (outRoot/fighter/NAME/sound/..., outRoot/sound/config/
        /// soundlabeltable.bin), ready to install. Every file replaced is backed up first (FILE.yyyyMMdd-HHmmss.bak). The
        /// written files are read back and checked; the aliases of the new sounds go to Aliases/sounds/FIGHTER.txt.
        /// </summary>
        public Saved Save(string outRoot)
        {
            var o = Build();
            if (!o.Ok) throw new InvalidDataException("Not saved:\n" + string.Join("\n", o.Problems.ToArray()));
            var s = new Saved { Output = o };
            string stamp = Stamp();
            string fighterOut = outRoot == null ? Sounds.Root : Path.Combine(Path.Combine(outRoot, "fighter"), Path.GetFileName(Sounds.Root));
            foreach (var kv in o.Banks)
                WriteWithBackup(Path.Combine(Path.Combine(fighterOut, "sound"), Path.GetFileName(kv.Key.Path)), kv.Value, stamp, s);
            if (o.Table != null)
            {
                string tablePath;
                if (outRoot != null) tablePath = Path.Combine(Path.Combine(Path.Combine(outRoot, "sound"), "config"), "soundlabeltable.bin");
                else if (Sounds.TablePath != null && !Sounds.TableFromPicked) tablePath = Sounds.TablePath;
                else tablePath = Path.Combine(Path.Combine(Path.Combine(DataRootOf(Sounds.Root), "sound"), "config"), "soundlabeltable.bin");
                WriteWithBackup(tablePath, o.Table, stamp, s);
            }
            // read back
            foreach (var path in s.Written)
            {
                if (path.EndsWith(".nus3bank", StringComparison.OrdinalIgnoreCase))
                {
                    var b = Nus3Bank.Load(path);
                    var want = o.Banks.First(kv => Path.GetFileName(kv.Key.Path).Equals(Path.GetFileName(path), StringComparison.OrdinalIgnoreCase));
                    if (!File.ReadAllBytes(path).SequenceEqual(want.Value) || b.Id != want.Key.Id) throw new IOException(path + " didn't read back as written");
                }
                else if (!SoundLabelTable.Load(path).Build().SequenceEqual(o.Table)) throw new IOException(path + " didn't read back as written");
            }
            // a new id's alias is the one given (an old line for the id, left from another copy of the bank, goes)
            foreach (var p in Pending)
                SoundAliases.Set(Sounds.Name, p.Id, p.Alias ?? "");
            s.FighterRoot = fighterOut;
            VolumeEdits.Clear();
            Pending.Clear();
            return s;
        }
    }

    /// <summary>
    /// The layout rules a written bank is checked against (v1.7.33), the ones the game's own banks follow and
    /// tools/gekkouga_sound.py / fighter_own_bank.py write: 'NUS3' + the size of the rest; 'BANKTOC ', its size (4 + 8 x
    /// count), the section count and each section's (name, size) as in the section's own header; the sections back to
    /// back to the file's end, each body at a multiple of 4, in vanilla's order (PROP BINF GRP DTON TONE JUNK PACK, or with
    /// MARK after TONE: vanilla snd_se_SZerosuit, Master's port; MARK doesn't hold a tone count and is kept); BINF's
    /// name and id; TONE: the tone count, the (offset, size) table with the entries back to back after it, each a multiple
    /// of 4 bytes; every tone's audio inside PACK at a multiple of 0x10, an IDSP file whose size is its header's (0x40 +
    /// 0x60 x channels + channels x the data size) and, for the new tones (from 'strictFrom'), the TONE tail's rate /
    /// channels / samples / loop the IDSP's; JUNK zeros; PACK's body at a multiple of 0x10 and its size too.
    /// </summary>
    public static class BankCheck
    {
        static readonly string[] Order = { "PROP", "BINF", "GRP ", "DTON", "TONE", "JUNK", "PACK" };
        static readonly string[] OrderMark = { "PROP", "BINF", "GRP ", "DTON", "TONE", "MARK", "JUNK", "PACK" };   // vanilla snd_se_SZerosuit's

        static int BE32(byte[] b, long at) { return b[at] << 24 | b[at + 1] << 16 | b[at + 2] << 8 | b[at + 3]; }

        /// <summary>The problems (none: it passes). vanillaLayout: also vanilla's section order and PACK at a multiple of
        /// 0x10 (a bank tones were added to; a volume change keeps the bank's layout as it was). Tones from strictFrom
        /// (the new ones) get every check; the others only "inside PACK".</summary>
        public static List<string> Validate(byte[] d, int strictFrom = int.MaxValue, bool vanillaLayout = true)
        {
            var p = new List<string>();
            if (d.Length < 24 || Encoding.ASCII.GetString(d, 0, 4) != "NUS3" || Encoding.ASCII.GetString(d, 8, 8) != "BANKTOC ") { p.Add("no NUS3 / BANKTOC header"); return p; }
            if (Nus3Bank.U32(d, 4) != d.Length - 8) p.Add("NUS3 size " + Nus3Bank.U32(d, 4) + " != file size - 8 (" + (d.Length - 8) + ")");
            uint n = Nus3Bank.U32(d, 20);
            if (Nus3Bank.U32(d, 16) != 4 + 8 * n) p.Add("BANKTOC size != 4 + 8 x " + n);
            long q = 24 + 8 * n;
            var at = new Dictionary<string, long>();
            var size = new Dictionary<string, uint>();
            var names = new List<string>();
            for (int i = 0; i < n; i++)
            {
                string nm = Encoding.ASCII.GetString(d, 24 + 8 * i, 4);
                uint sz = Nus3Bank.U32(d, 28 + 8 * i);
                if (q + 8 > d.Length) { p.Add("section " + nm + " past the end"); return p; }
                if (Encoding.ASCII.GetString(d, (int)q, 4) != nm || Nus3Bank.U32(d, (int)q + 4) != sz) p.Add("section " + i + ": its header isn't BANKTOC's (" + nm + ", " + sz + ")");
                if ((q + 8) % 4 != 0) p.Add("section " + nm + "'s body at 0x" + (q + 8).ToString("X") + ", not a multiple of 4");
                at[nm] = q + 8;
                size[nm] = sz;
                names.Add(nm);
                q += 8 + sz;
            }
            if (q != d.Length) p.Add("the sections end at 0x" + q.ToString("X") + ", the file at 0x" + d.Length.ToString("X"));
            string got = string.Join(",", names.ToArray());
            if (vanillaLayout && got != string.Join(",", Order) && got != string.Join(",", OrderMark))
                p.Add("sections " + got + " (vanilla: " + string.Join(",", Order) + ", or with MARK after TONE)");
            if (!at.ContainsKey("TONE") || !at.ContainsKey("PACK") || !at.ContainsKey("BINF")) { p.Add("no BINF / TONE / PACK"); return p; }
            long pack = at["PACK"];
            uint packSize = size["PACK"];
            if (vanillaLayout && pack % 16 != 0) p.Add("PACK's body at 0x" + pack.ToString("X") + ", not a multiple of 0x10 (vanilla banks' always are)");
            if (vanillaLayout && packSize % 16 != 0) p.Add("PACK's size " + packSize + " not a multiple of 0x10");
            if (at.ContainsKey("JUNK"))
                for (long i = at["JUNK"]; i < at["JUNK"] + size["JUNK"]; i++) if (d[i] != 0) { p.Add("JUNK isn't zeros"); break; }
            // BINF
            long bf = at["BINF"];
            int bl = d[bf + 8];
            if (9 + bl + 4 > size["BINF"] || d[bf + 8 + bl] != 0) p.Add("BINF's name");
            // TONE
            long t = at["TONE"];
            uint ts = size["TONE"];
            uint count = Nus3Bank.U32(d, (int)t);
            if (4 + 8L * count > ts) { p.Add("TONE: count " + count + " doesn't fit"); return p; }
            long next = 4 + 8L * count;
            for (int i = 0; i < count; i++)
            {
                uint o = Nus3Bank.U32(d, (int)(t + 4 + 8 * i)), sz = Nus3Bank.U32(d, (int)(t + 8 + 8 * i));
                if (o != next) p.Add("TONE: entry " + i + " at " + o + ", not right after the one before (" + next + ")");
                if (sz % 4 != 0) p.Add("TONE: entry " + i + "'s size " + sz + " isn't a multiple of 4");
                next = o + sz;
                if (o + (long)sz > ts) { p.Add("TONE: entry " + i + " runs past TONE"); return p; }
                var e = new byte[sz];
                Array.Copy(d, t + o, e, 0, sz);
                var tone = Tone.Parse(e, i);
                if (!tone.HasAudio) continue;
                if (tone.DataOffset + (long)tone.DataSize > packSize) { p.Add("tone " + i + " (" + tone.Name + "): its audio runs past PACK"); continue; }
                if (i < strictFrom) continue;
                if (tone.DataOffset % 16 != 0) p.Add("tone " + i + " (" + tone.Name + "): its audio at PACK + 0x" + tone.DataOffset.ToString("X") + ", not a multiple of 0x10");
                long a = pack + tone.DataOffset;
                if (Encoding.ASCII.GetString(d, (int)a, 4) != "IDSP") { p.Add("tone " + i + ": not IDSP audio"); continue; }
                int ch = BE32(d, a + 8), rate = BE32(d, a + 12), smp = BE32(d, a + 16), doff = BE32(d, a + 0x28), per = BE32(d, a + 0x2C);
                if (doff != 0x40 + 0x60 * ch || (long)doff + (long)per * ch != tone.DataSize)
                    p.Add("tone " + i + " (" + tone.Name + "): its IDSP's size (0x40 + 0x60 x " + ch + " + " + ch + " x " + per + ") isn't its TONE size " + tone.DataSize);
                int frames = (smp + 13) / 14;
                if (per != (frames + (frames & 1)) * 8) p.Add("tone " + i + " (" + tone.Name + "): " + per + " bytes of frames for " + smp + " samples (vanilla: an even frame count)");
                {
                    int tl = e.Length - 0x20;
                    bool loops = (d[a + 0x40 + 0x0C] << 8 | d[a + 0x40 + 0x0D]) != 0;
                    if (Nus3Bank.U32(e, tl) != rate || Nus3Bank.U32(e, tl + 4) != ch || Nus3Bank.U32(e, tl + 8) != smp || Nus3Bank.U32(e, tl + 20) != (loops ? 1u : 0))
                        p.Add("tone " + i + " (" + tone.Name + "): the TONE tail (rate, channels, samples, loop) isn't the audio's");
                    if (ch < 1 || ch > 2 || rate != AudioImport.BankRate) p.Add("tone " + i + ": " + ch + " channels at " + rate + " Hz");
                }
            }
            if (next != ts) p.Add("TONE: the entries end at " + next + ", TONE at " + ts);
            return p;
        }

        static Dictionary<string, KeyValuePair<long, uint>> SectionsOf(byte[] d)
        {
            var r = new Dictionary<string, KeyValuePair<long, uint>>();
            uint n = Nus3Bank.U32(d, 20);
            long q = 24 + 8 * n;
            for (int i = 0; i < n; i++)
            {
                string nm = Encoding.ASCII.GetString(d, 24 + 8 * i, 4);
                uint sz = Nus3Bank.U32(d, 28 + 8 * i);
                r[nm] = new KeyValuePair<long, uint>(q + 8, sz);
                q += 8 + sz;
            }
            return r;
        }

        static bool Same(byte[] a, long ao, byte[] b, long bo, long n)
        {
            for (long i = 0; i < n; i++) if (a[ao + i] != b[bo + i]) return false;
            return true;
        }

        /// <summary>What the new bytes keep of the bank as on disk: PROP, BINF, GRP, DTON unchanged; the old tones'
        /// entries unchanged but the edited volume floats (and only them); 'added' more tones; the old PACK at its start.</summary>
        public static List<string> CompareWithOriginal(Nus3Bank bank, byte[] nd, int added, IEnumerable<Tone> volumeEdits)
        {
            var p = new List<string>();
            byte[] od;
            using (var f = new FileStream(bank.Path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) { od = new byte[f.Length]; int got = 0; while (got < od.Length) got += f.Read(od, got, od.Length - got); }
            var os = SectionsOf(od);
            var ns = SectionsOf(nd);
            foreach (var nm in os.Keys)
                if (nm != "TONE" && nm != "JUNK" && nm != "PACK" && (!ns.ContainsKey(nm) || os[nm].Value != ns[nm].Value || !Same(od, os[nm].Key, nd, ns[nm].Key, os[nm].Value)))
                    p.Add(nm.Trim() + " changed");
            if (string.Join(",", os.Keys.ToArray()) != string.Join(",", ns.Keys.ToArray())) p.Add("the sections changed");
            long ot = os["TONE"].Key, nt = ns["TONE"].Key;
            uint oc = Nus3Bank.U32(od, (int)ot), nc = Nus3Bank.U32(nd, (int)nt);
            if (nc != oc + added) p.Add("TONE: " + nc + " tones, want " + oc + " + " + added);
            var edited = new HashSet<int>(volumeEdits.Select(x => x.Index));
            for (int i = 0; i < Math.Min(oc, nc); i++)
            {
                uint oo = Nus3Bank.U32(od, (int)(ot + 4 + 8 * i)), osz = Nus3Bank.U32(od, (int)(ot + 8 + 8 * i));
                uint no = Nus3Bank.U32(nd, (int)(nt + 4 + 8 * i)), nsz = Nus3Bank.U32(nd, (int)(nt + 8 + 8 * i));
                if (osz != nsz) { p.Add("tone " + i + "'s entry changed size"); continue; }
                if (Same(od, ot + oo, nd, nt + no, osz)) continue;
                var t = bank.Tones[i];
                bool onlyVolume = edited.Contains(i) && t.DataBlock >= 0;
                for (int k = 0; k < osz && onlyVolume; k++)
                    if (od[ot + oo + k] != nd[nt + no + k] && (k < t.DataBlock + 12 || k >= t.DataBlock + 16)) onlyVolume = false;
                if (!onlyVolume) p.Add("tone " + i + " (" + t.Name + ")'s entry changed" + (edited.Contains(i) ? " beyond its volume" : ""));
            }
            long op = os["PACK"].Key, np = ns["PACK"].Key;
            uint opl = os["PACK"].Value, npl = ns["PACK"].Value;
            if (npl < opl || !Same(od, op, nd, np, opl)) p.Add("the old PACK isn't kept at PACK's start");
            if (added == 0 && npl != opl) p.Add("PACK changed size");
            return p;
        }

        /// <summary>The new table against the old: the same rows but 'row' (its labels: the old ones, then 'added'), the old
        /// label words in place (the row's new list appended at the pool's end).</summary>
        public static List<string> CompareTables(byte[] od, byte[] nd, int row, IList<int> added)
        {
            var p = new List<string>();
            var o = SoundLabelTable.Parse(od);
            var n = SoundLabelTable.Parse(nd);
            if (o.Rows.Count != n.Rows.Count) { p.Add("row count changed"); return p; }
            if (!Same(od, 0, nd, 0, 16)) p.Add("the header changed");
            for (int r = 0; r < o.Rows.Count; r++)
                if (r != row && !Same(od, 16 + 16 * r, nd, 16 + 16 * r, 16)) p.Add("row " + r + " changed");
            long po = 16 + 16 * o.Rows.Count;
            if (nd.Length < od.Length || !Same(od, po, nd, po, od.Length - po)) p.Add("the old label words moved");
            var ol = o.Labels(row);
            var nl = n.Labels(row);
            if (nl.Length != ol.Length + added.Count || !nl.Take(ol.Length).SequenceEqual(ol) || !nl.Skip(ol.Length).SequenceEqual(added))
                p.Add("row " + row + "'s labels aren't the old ones + the new");
            var used = o.UsedIds();
            for (int k = 0; k < added.Count; k++)
                if (used.Contains(SoundLabelTable.SoundId(row, ol.Length + k))) p.Add("an id clashes");
            return p;
        }
    }
}
