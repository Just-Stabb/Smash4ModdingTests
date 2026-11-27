using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using SALT.Moveset.AnimCMD;

namespace Sm4shCommand.Sound
{
    /// <summary>Merge sound mods' settings (v1.7.34).</summary>
    public class MergeOptions
    {
        /// <summary>When two mods change the same thing (a label, a tone's volume, a tone, a file): false keeps the first
        /// mod's (the list's order), true takes the later mod's.</summary>
        public bool LaterWins;
        /// <summary>Also take the rows a mod changed without shipping a bank that plays them (off: the base's rows stay and
        /// the mod is reported as made from another base).</summary>
        public bool TakeUnbankedRows;
        /// <summary>Rewrite the mods' ACMD scripts whose sound ids changed (only the sound commands' id parameters).</summary>
        public bool RewriteScripts = true;
        /// <summary>Also copy every other file of the mods into the output (a complete install folder).</summary>
        public bool CopyOtherFiles;
    }

    /// <summary>A bank of a mod (v1.7.34): where it is (its path under the data folder, as the game's), its fighter, the
    /// row it plays from in the mod's table.</summary>
    public class ModBank
    {
        public SoundMod Mod;
        public string Rel;                  // fighter/kamui/sound/snd_se_Kamui.nus3bank
        public string Fighter = "";         // kamui ("" outside fighter/)
        public string Kind = "";
        public Nus3Bank Bank;
        public int Row = -1;
        byte[] pack;

        public byte[] Pack { get { return pack ?? (pack = Bank.ReadPack()); } }
        public int Count { get { return Bank.Tones.Count; } }

        public byte[] Audio(int i)
        {
            var t = Bank.Tones[i];
            if (!t.HasAudio || t.DataOffset + (long)t.DataSize > Pack.Length) return null;
            var b = new byte[t.DataSize];
            Array.Copy(Pack, t.DataOffset, b, 0, b.Length);
            return b;
        }

        public override string ToString() { return Rel; }
    }

    /// <summary>
    /// One sound mod for the merge (v1.7.34): a folder or a .zip laid out as the game's data somewhere inside
    /// (INSTALL_TO_data, content/patch/data, data, or the folder itself): its sound/config/soundlabeltable.bin, its banks
    /// (every .nus3bank under it: fighter/NAME/sound/..., sound/se/...), its scripts and its Aliases/sounds/*.txt files.
    /// </summary>
    public class SoundMod
    {
        public string Source, Name, Root, DataRoot, TablePath;
        public SoundLabelTable Table;
        public readonly List<ModBank> Banks = new List<ModBank>();
        public readonly List<string> AliasFiles = new List<string>();
        public readonly List<string> Notes = new List<string>();
        public bool Unzipped;

        static string TableRel { get { return Path.Combine(Path.Combine("sound", "config"), "soundlabeltable.bin"); } }

        /// <summary>The folder laid out as the game's data inside root: the shallowest one with sound/config/
        /// soundlabeltable.bin, else the shallowest with fighter/NAME/sound/*.nus3bank; null when none.</summary>
        public static string FindDataRoot(string root)
        {
            var queue = new Queue<KeyValuePair<string, int>>();
            queue.Enqueue(new KeyValuePair<string, int>(root, 0));
            string fighterRoot = null;
            while (queue.Count > 0)
            {
                var d = queue.Dequeue();
                try
                {
                    if (File.Exists(Path.Combine(d.Key, TableRel))) return d.Key;
                    if (fighterRoot == null)
                    {
                        var f = Path.Combine(d.Key, "fighter");
                        if (Directory.Exists(f) && Directory.GetDirectories(f).Any(x => Directory.Exists(Path.Combine(x, "sound")) && Directory.GetFiles(Path.Combine(x, "sound"), "*.nus3bank").Length > 0))
                            fighterRoot = d.Key;
                    }
                    if (d.Value < 6)
                        foreach (var sub in Directory.GetDirectories(d.Key).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
                            queue.Enqueue(new KeyValuePair<string, int>(sub, d.Value + 1));
                }
                catch (Exception) { }
            }
            if (fighterRoot != null) return fighterRoot;
            // a fighter folder itself (fighter/NAME) or the fighter folder (fighter)
            if (Path.GetFileName(root).Equals("fighter", StringComparison.OrdinalIgnoreCase)) return Path.GetDirectoryName(root);
            var parent = Path.GetDirectoryName(root);
            if (parent != null && Path.GetFileName(parent).Equals("fighter", StringComparison.OrdinalIgnoreCase)) return Path.GetDirectoryName(parent);
            return null;
        }

        public static string RelOf(string root, string path)
        {
            string r = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            string p = Path.GetFullPath(path);
            return p.Substring(r.Length + 1).Replace('\\', '/');
        }

        public static SoundMod Open(string source, string tempRoot, SoundLabelTable baseTable, IDictionary<uint, uint> bankAliases)
        {
            var m = new SoundMod { Source = source };
            string trimmed = source.TrimEnd('\\', '/');
            m.Name = File.Exists(trimmed) ? Path.GetFileNameWithoutExtension(trimmed) : Path.GetFileName(trimmed);
            if (File.Exists(trimmed) && trimmed.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
            {
                m.Root = Path.Combine(tempRoot, Guid.NewGuid().ToString("N").Substring(0, 8) + "_" + SafeName(m.Name));
                MiniZip.Extract(trimmed, m.Root);
                m.Unzipped = true;
                m.Notes.Add("unzipped to a temporary folder (deleted after the merge)");
            }
            else if (Directory.Exists(trimmed)) m.Root = trimmed;
            else throw new FileNotFoundException("No such folder or .zip: " + source);
            m.DataRoot = FindDataRoot(m.Root);
            if (m.DataRoot == null) throw new InvalidDataException(m.Name + ": no sound/config/soundlabeltable.bin and no fighter/NAME/sound/*.nus3bank in it: not a sound mod laid out as the game's data.");
            var tp = Path.Combine(m.DataRoot, TableRel);
            if (File.Exists(tp))
            {
                m.TablePath = tp;
                m.Table = SoundLabelTable.Load(tp);
            }
            else m.Notes.Add("no soundlabeltable.bin of its own (its banks play from the base's rows)");
            var table = m.Table ?? baseTable;
            var byFighter = new Dictionary<string, List<ModBank>>(StringComparer.OrdinalIgnoreCase);
            foreach (var f in Directory.GetFiles(m.DataRoot, "*.nus3bank", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            {
                Nus3Bank b;
                try { b = Nus3Bank.Load(f); }
                catch (Exception ex) { m.Notes.Add(RelOf(m.DataRoot, f) + ": not read (" + ex.Message + ")"); continue; }
                var mb = new ModBank { Mod = m, Rel = RelOf(m.DataRoot, f), Bank = b };
                var parts = mb.Rel.Split('/');
                if (parts.Length >= 4 && parts[0].Equals("fighter", StringComparison.OrdinalIgnoreCase) && parts[2].Equals("sound", StringComparison.OrdinalIgnoreCase))
                    mb.Fighter = parts[1].ToLowerInvariant();
                m.Banks.Add(mb);
                List<ModBank> l;
                if (!byFighter.TryGetValue(mb.Fighter, out l)) byFighter[mb.Fighter] = l = new List<ModBank>();
                l.Add(mb);
            }
            // the rows: as the viewer finds them (BINF id; a port's own id through its alias, Viewer/SoundBanks.txt; a
            // costume bank through its main bank's)
            foreach (var kv in byFighter)
            {
                if (kv.Key.Length > 0)
                {
                    var set = SoundSet.Build(kv.Value.Select(x => x.Bank).ToList(), table, kv.Key, bankAliases, b => { int o; return SoundSet.KindOf(b.Path, out o); });
                    foreach (var mb in kv.Value) { mb.Row = set.RowOfBank[mb.Bank]; mb.Kind = set.Kinds[mb.Bank]; }
                }
                else
                    foreach (var mb in kv.Value)
                    {
                        mb.Row = table != null ? table.RowOf(mb.Bank.Id) : -1;
                        uint alias;
                        if (mb.Row < 0 && table != null && bankAliases != null && bankAliases.TryGetValue(mb.Bank.Id, out alias)) mb.Row = table.RowOf(alias);
                        mb.Kind = Path.GetFileNameWithoutExtension(mb.Rel);
                    }
            }
            try
            {
                foreach (var d in Directory.GetDirectories(m.Root, "sounds", SearchOption.AllDirectories))
                    if (Path.GetFileName(Path.GetDirectoryName(d)).Equals("Aliases", StringComparison.OrdinalIgnoreCase))
                        m.AliasFiles.AddRange(Directory.GetFiles(d, "*.txt").OrderBy(x => x, StringComparer.OrdinalIgnoreCase));
            }
            catch (Exception) { }
            if (m.Table == null && m.Banks.Count == 0) throw new InvalidDataException(m.Name + ": no sound files in it.");
            return m;
        }

        static string SafeName(string s)
        {
            var sb = new StringBuilder();
            foreach (char c in s) sb.Append(char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_');
            return sb.Length > 0 ? sb.ToString() : "mod";
        }
    }

    /// <summary>A sound id that changed in the merge (the later mod's new sounds moved after the earlier mod's).</summary>
    public class SoundIdRemap
    {
        public string Mod, Fighter, Tone;
        public uint Old, New;
        public override string ToString() { return string.Format(CultureInfo.InvariantCulture, "0x{0:X8} -> 0x{1:X8}", Old, New); }
    }

    /// <summary>What a merge did (or would do: a dry run writes nothing).</summary>
    public class MergeResult
    {
        public readonly List<string> Errors = new List<string>(), Warnings = new List<string>(), Conflicts = new List<string>();
        public readonly List<string> RowLines = new List<string>(), BankLines = new List<string>(), ScriptLines = new List<string>(), AliasLines = new List<string>(), CheckLines = new List<string>();
        public readonly List<SoundIdRemap> Remaps = new List<SoundIdRemap>();
        public readonly List<SoundMod> Mods = new List<SoundMod>();
        /// <summary>The rows taken from a mod (row -> the mods it came from, in order).</summary>
        public readonly SortedDictionary<int, List<string>> RowsFrom = new SortedDictionary<int, List<string>>();
        public readonly List<string> MergedBanks = new List<string>();
        public readonly List<string> RewrittenScripts = new List<string>();
        public readonly List<string> Written = new List<string>();
        public string BaseTablePath, OutDir, Report = "";
        public byte[] Table;
        public bool DryRun;
        public bool Ok { get { return Errors.Count == 0; } }
    }

    /// <summary>
    /// Merge sound mods (v1.7.34, the Sound Effect Viewer's Merge sound mods..; SM4SHCommand.exe --merge-sounds). The game
    /// has ONE sound/config/soundlabeltable.bin, so two sound mods each shipping their own (User 1's Corrin row extended,
    /// User 2's King Dedede row extended) overwrite each other: whichever is installed last wins and the other's new ids
    /// point nowhere. Their banks (fighter/kamui/sound/..., fighter/dedede/sound/...) don't clash.
    ///
    /// The merge compares each mod's table with the base (the game's current soundlabeltable.bin, from the Game data
    /// folder) row by row: a row one mod changed takes that mod's row; rows nobody changed stay the base's byte for byte;
    /// different fighters' rows never mix. The fallback, the same row changed by several mods (two users both added
    /// sounds to the same fighter): the later mod's new tones (past the base's) are appended to the earlier mod's bank (and
    /// to the costume banks on that row, at the same tone indexes, as the Sound Adder does), its new labels go after the
    /// earlier mod's, so its new sounds' ids change: the remap list (old -> new) and, optionally, its ACMD scripts rewritten
    /// (only sound commands' id parameters, patched in place; the rest of each file byte for byte). Volume edits / replaced
    /// tones of existing tones: taken from whichever mod changed them; changed by both, differently: a conflict, reported,
    /// the first mod's kept (or the later's: MergeOptions.LaterWins). Banks are only ever merged with the same file of
    /// another mod (fighter/NAME/sound/FILE): no fighter gets another fighter's sounds.
    ///
    /// Edge cases: a mod that re-pointed existing labels (taken; both re-pointing one label differently: a conflict); a row
    /// grown and re-pointed; port banks on their own 46000+ ids (their alias rows, Viewer/SoundBanks.txt); two mods giving
    /// the same empty row to different banks (the later moved to another empty row, all its ids remapped); a mod made from
    /// another base (rows changed with no bank of the mod on them: reported, the base's kept unless TakeUnbankedRows).
    /// Nothing is written in place: Run(outDir) writes a new folder (the table, the merged / copied banks, the rewritten
    /// scripts, the merged Aliases/sounds files, MERGE_REPORT.txt).
    /// </summary>
    public class SoundMerger
    {
        public readonly MergeOptions Options;
        public readonly List<string> Sources = new List<string>();
        public string BaseTablePath;
        public IDictionary<uint, uint> BankAliases;
        public string Version = "";

        SoundLabelTable baseTable;
        byte[] baseBytes;
        string baseDataRoot;
        MergeResult res;
        readonly Dictionary<int, RowState> rows = new Dictionary<int, RowState>();
        readonly Dictionary<string, BankWork> work = new Dictionary<string, BankWork>(StringComparer.OrdinalIgnoreCase);
        readonly Dictionary<string, ModBank> baseBanks = new Dictionary<string, ModBank>(StringComparer.OrdinalIgnoreCase);
        readonly Dictionary<SoundMod, Dictionary<uint, uint>> remaps = new Dictionary<SoundMod, Dictionary<uint, uint>>();
        readonly List<IdCheck> idChecks = new List<IdCheck>();
        readonly HashSet<int> claimedRows = new HashSet<int>();

        public SoundMerger(string baseTablePath, IEnumerable<string> sources, MergeOptions options, IDictionary<uint, uint> bankAliases)
        {
            BaseTablePath = baseTablePath;
            Sources.AddRange(sources);
            Options = options ?? new MergeOptions();
            BankAliases = bankAliases;
        }

        class RowState
        {
            public uint BankId;
            public List<int> Labels;
            public List<string> SetBy;          // per label: the mod that set it (null: the base's)
            public readonly List<string> Mods = new List<string>();
            public readonly List<string> Lines = new List<string>();
        }

        class IdCheck
        {
            public SoundMod Mod;
            public int Row, Label, ModTone;
            public bool NewTone;            // one of the mod's new tones (its audio checked too; else its name)
            public uint Old, New;
            public List<ModBank> Banks;
        }

        class Op
        {
            public int Keep = -1, F = -1, Tbase;
            public List<int> New = new List<int>();
        }

        // ------------------------------------------------------------------ the banks being built

        class BankWork
        {
            public string Rel;
            public ModBank First;
            public readonly List<byte[]> Entries = new List<byte[]>();
            public readonly List<byte[]> Audios = new List<byte[]>();
            public byte[] Pack0;
            public readonly MemoryStream Extra = new MemoryStream();
            public bool Changed;
            public int FirstAppended = int.MaxValue;
            public readonly Dictionary<int, string> SetBy = new Dictionary<int, string>();
            public readonly List<string> Lines = new List<string>();
            public readonly List<string> Mods = new List<string>();
            public int Count { get { return Entries.Count; } }

            public static BankWork From(ModBank b, int keep)
            {
                var w = new BankWork { Rel = b.Rel, First = b, Pack0 = b.Pack };
                keep = Math.Min(keep, b.Count);
                for (int i = 0; i < keep; i++) { w.Entries.Add((byte[])b.Bank.Tones[i].Entry.Clone()); w.Audios.Add(b.Audio(i)); }
                if (keep < b.Count) w.Changed = true;
                w.Mods.Add(b.Mod.Name);
                return w;
            }

            public void Pad(int n, byte[] stub)
            {
                while (Count < n) { Entries.Add((byte[])stub.Clone()); Audios.Add(null); Changed = true; }
            }

            long PutAudio(byte[] audio)
            {
                while ((Pack0.Length + Extra.Length) % 16 != 0) Extra.WriteByte(0);
                long at = Pack0.Length + Extra.Length;
                Extra.Write(audio, 0, audio.Length);
                return at;
            }

            byte[] Point(byte[] entry, byte[] audio)
            {
                var e = (byte[])entry.Clone();
                var t = Tone.Parse(e, 0);
                if (audio != null && t.DataBlock >= 0) Nus3Bank.Put32(e, t.DataBlock + 4, (uint)PutAudio(audio));
                return e;
            }

            public int Append(byte[] entry, byte[] audio)
            {
                Entries.Add(Point(entry, audio));
                Audios.Add(audio);
                Changed = true;
                FirstAppended = Math.Min(FirstAppended, Count - 1);
                return Count - 1;
            }

            public void Replace(int i, byte[] entry, byte[] audio)
            {
                Entries[i] = Point(entry, audio);
                Audios[i] = audio;
                Changed = true;
            }

            public void SetVolume(int i, float db)
            {
                var t = Tone.Parse(Entries[i], i);
                t.VolumeDb = db;            // (writes into Entries[i])
                Changed = true;
            }

            public byte[] Build()
            {
                var tones = new List<Tone>();
                for (int i = 0; i < Count; i++) tones.Add(Tone.Parse(Entries[i], i));
                byte[] pack;
                bool appended = Extra.Length > 0;
                if (appended)
                {
                    var ms = new MemoryStream();
                    ms.Write(Pack0, 0, Pack0.Length);
                    var x = Extra.ToArray();
                    ms.Write(x, 0, x.Length);
                    while (ms.Length % 16 != 0) ms.WriteByte(0);
                    pack = ms.ToArray();
                }
                else pack = Pack0;
                return First.Bank.Build(tones, pack, appended);
            }
        }

        static readonly byte[] EmptyStub = { 0, 0, 0, 0, 1, 0, 0, 0, 0xFF, 0, 0, 0 };

        static byte[] StubOf(Nus3Bank b)
        {
            var s = b.Tones.FirstOrDefault(t => t.Entry.Length == 12 && t.Kind == ToneKind.Empty);
            return s != null ? (byte[])s.Entry.Clone() : (byte[])EmptyStub.Clone();
        }

        static bool SameBytes(byte[] a, byte[] b)
        {
            if (a == null || b == null) return a == b;
            if (a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
            return true;
        }

        /// <summary>Two tones the same: their audio and their TONE entries (but the PACK offset, which depends on the bank's
        /// layout; and the volume float when ignoreVolume).</summary>
        static bool SameTone(byte[] ea, byte[] aa, byte[] eb, byte[] ab, bool ignoreVolume)
        {
            if (!SameBytes(aa, ab) || ea.Length != eb.Length) return false;
            int q = Tone.Parse(ea, 0).DataBlock;
            if (q != Tone.Parse(eb, 0).DataBlock) return false;
            for (int i = 0; i < ea.Length; i++)
            {
                if (q >= 0 && i >= q + 4 && i < q + 8) continue;
                if (ignoreVolume && q >= 0 && i >= q + 12 && i < q + 16) continue;
                if (ea[i] != eb[i]) return false;
            }
            return true;
        }

        static float Vol(byte[] e) { return Tone.Parse(e, 0).VolumeDb; }
        static string ToneName(byte[] e) { var t = Tone.Parse(e, 0); return t.Name.Length > 0 ? t.Name : "(" + t.Kind.ToString().ToLowerInvariant() + ")"; }
        static string Hex(uint v) { return string.Format(CultureInfo.InvariantCulture, "0x{0:X8}", v); }
        static string RowHex(int r) { return string.Format(CultureInfo.InvariantCulture, "0x{0:X}", r); }
        static string Db(float v) { return v.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture) + " dB"; }

        ModBank BaseBank(string rel)
        {
            ModBank b;
            if (baseBanks.TryGetValue(rel, out b)) return b;
            b = null;
            if (baseDataRoot != null)
            {
                var p = Path.Combine(baseDataRoot, rel.Replace('/', Path.DirectorySeparatorChar));
                try { if (File.Exists(p)) b = new ModBank { Rel = rel, Bank = Nus3Bank.Load(p), Mod = new SoundMod { Name = "the base" } }; }
                catch (Exception) { }
            }
            baseBanks[rel] = b;
            return b;
        }

        int[] BaseLabels(int r) { return r < baseTable.Rows.Count ? baseTable.Labels(r) : new int[0]; }
        uint BaseBankId(int r) { return r < baseTable.Rows.Count ? baseTable.Rows[r].BankId : SoundLabelTable.EmptyBank; }

        static int[] LabelsOf(SoundLabelTable t, int r) { return t != null && r < t.Rows.Count ? t.Labels(r) : new int[0]; }
        static uint BankIdOf(SoundLabelTable t, int r) { return t != null && r < t.Rows.Count ? t.Rows[r].BankId : SoundLabelTable.EmptyBank; }

        string RowName(int r, uint bankId)
        {
            var names = new List<string>();
            foreach (var m in res.Mods) foreach (var b in m.Banks) if (b.Row == r && !names.Contains(b.Bank.Name)) names.Add(b.Bank.Name);
            return RowHex(r) + " (bank id " + (bankId == SoundLabelTable.EmptyBank ? "-1: empty" : bankId.ToString(CultureInfo.InvariantCulture)) + (names.Count > 0 ? ", " + string.Join(", ", names.ToArray()) : "") + ")";
        }

        // ------------------------------------------------------------------ the merge

        /// <summary>Merges; outDir null: a dry run (nothing written). Never writes into a mod or the base.</summary>
        public MergeResult Run(string outDir)
        {
            res = new MergeResult { BaseTablePath = BaseTablePath, OutDir = outDir, DryRun = outDir == null };
            string temp = Path.Combine(Path.GetTempPath(), "sm4sh_merge_" + Guid.NewGuid().ToString("N").Substring(0, 8));
            try
            {
                if (BaseTablePath == null || !File.Exists(BaseTablePath)) { res.Errors.Add("No base soundlabeltable.bin (pick the game's data folder: Game data..)."); return res; }
                baseBytes = File.ReadAllBytes(BaseTablePath);
                baseTable = SoundLabelTable.Parse(baseBytes);
                var cfg = Path.GetDirectoryName(BaseTablePath);
                var snd = cfg != null ? Path.GetDirectoryName(cfg) : null;
                baseDataRoot = snd != null ? Path.GetDirectoryName(snd) : null;
                if (Sources.Count < 2) res.Errors.Add("Pick two or more mods to merge.");
                foreach (var s in Sources)
                {
                    try { res.Mods.Add(SoundMod.Open(s, temp, baseTable, BankAliases)); }
                    catch (Exception ex) { res.Errors.Add(ex.Message); }
                }
                for (int i = 0; i < res.Mods.Count; i++)
                    for (int j = i + 1; j < res.Mods.Count; j++)
                        if (string.Equals(Path.GetFullPath(res.Mods[i].DataRoot), Path.GetFullPath(res.Mods[j].DataRoot), StringComparison.OrdinalIgnoreCase))
                            res.Errors.Add(res.Mods[i].Name + " is given twice.");
                if (!res.Ok) return res;
                if (outDir != null) CheckOutDir(outDir);
                if (!res.Ok) return res;
                // every row some mod's table has in use: never given to a moved row
                foreach (var m in res.Mods)
                    if (m.Table != null)
                        for (int r = 0; r < m.Table.Rows.Count; r++) if (!m.Table.Rows[r].Empty) claimedRows.Add(r);
                for (int r = 0; r < baseTable.Rows.Count; r++) if (!baseTable.Rows[r].Empty) claimedRows.Add(r);
                foreach (var m in res.Mods) MergeMod(m);
                if (!res.Ok) return res;
                var files = BuildOutputs();
                if (!res.Ok) return res;
                if (outDir != null) Write(outDir, files);
                return res;
            }
            catch (Exception ex)
            {
                res.Errors.Add("The merge stopped: " + ex.Message);
                return res;
            }
            finally
            {
                try { if (Directory.Exists(temp)) Directory.Delete(temp, true); } catch (Exception) { }
                res.Report = BuildReport();
                if (outDir != null && res.Ok)
                    try { File.WriteAllText(Path.Combine(outDir, "MERGE_REPORT.txt"), res.Report); res.Written.Add(Path.Combine(outDir, "MERGE_REPORT.txt")); }
                    catch (Exception ex) { res.Errors.Add("MERGE_REPORT.txt: " + ex.Message); }
            }
        }

        static bool Inside(string path, string dir)
        {
            if (dir == null) return false;
            string p = Path.GetFullPath(path).TrimEnd('\\', '/') + Path.DirectorySeparatorChar, d = Path.GetFullPath(dir).TrimEnd('\\', '/') + Path.DirectorySeparatorChar;
            return p.StartsWith(d, StringComparison.OrdinalIgnoreCase);
        }

        void CheckOutDir(string outDir)
        {
            if (Directory.Exists(outDir) && Directory.GetFileSystemEntries(outDir).Length > 0)
                res.Errors.Add("The output folder isn't empty: " + outDir + " (the merge writes a new folder; pick an empty or new one).");
            foreach (var m in res.Mods)
                if (!m.Unzipped && (Inside(outDir, m.Root) || Inside(m.Root, outDir)))
                    res.Errors.Add("The output folder can't be inside a mod's folder (or hold one): " + m.Root);
            if (baseDataRoot != null && (Inside(outDir, baseDataRoot) || Inside(baseDataRoot, outDir)))
                res.Errors.Add("The output folder can't be inside the base's data folder (or hold it): " + baseDataRoot);
        }

        Dictionary<uint, uint> RemapOf(SoundMod m)
        {
            Dictionary<uint, uint> d;
            if (!remaps.TryGetValue(m, out d)) remaps[m] = d = new Dictionary<uint, uint>();
            return d;
        }

        void MergeMod(SoundMod m)
        {
            var ops = new Dictionary<ModBank, Op>();
            if (m.Table != null)
            {
                if (!SameBytes(m.Table.Head, baseTable.Head))
                    res.Warnings.Add(m.Name + ": its soundlabeltable.bin's header (version) isn't the base's.");
                if (m.Table.Rows.Count != baseTable.Rows.Count)
                    res.Warnings.Add(string.Format(CultureInfo.InvariantCulture, "{0}: its table has {1} rows, the base {2}.", m.Name, m.Table.Rows.Count, baseTable.Rows.Count));
                var banked = new HashSet<int>(m.Banks.Where(b => b.Row >= 0).Select(b => b.Row));
                var changed = new List<int>();
                var unbanked = new List<int>();
                int n = Math.Max(baseTable.Rows.Count, m.Table.Rows.Count);
                for (int r = 0; r < n; r++)
                {
                    if (BankIdOf(m.Table, r) == BaseBankId(r) && LabelsOf(m.Table, r).SequenceEqual(BaseLabels(r))) continue;
                    if (banked.Contains(r)) changed.Add(r); else unbanked.Add(r);
                }
                if (unbanked.Count > 0)
                {
                    res.Warnings.Add(string.Format(CultureInfo.InvariantCulture,
                        "{0}: {1} row(s) differ from the base with no bank of the mod on them ({2}{3}): it was probably made from another soundlabeltable.bin than the base (another game version or another mod's). {4}",
                        m.Name, unbanked.Count, string.Join(", ", unbanked.Take(8).Select(RowHex).ToArray()), unbanked.Count > 8 ? " ..." : "",
                        Options.TakeUnbankedRows ? "Taken anyway (\"take rows without the mod's banks\" is on)." : "The base's rows are kept for them (only the rows its banks play from are taken)."));
                    if (Options.TakeUnbankedRows) changed.AddRange(unbanked);
                }
                foreach (var r in changed.OrderBy(x => x)) MergeRow(m, r, ops);
            }
            foreach (var b in m.Banks)
            {
                Op op;
                BankWork w;
                work.TryGetValue(b.Rel, out w);
                if (ops.TryGetValue(b, out op))
                {
                    if (w == null)
                    {
                        w = BankWork.From(b, op.Keep >= 0 ? op.Keep : b.Count);
                        work[b.Rel] = w;
                        BaseDiffInfo(w, b);
                    }
                    else
                    {
                        if (!w.Mods.Contains(m.Name)) w.Mods.Add(m.Name);
                        Diffs(w, b, Math.Min(op.Tbase, b.Count));
                    }
                    if (op.New.Count > 0)
                    {
                        w.Pad(op.F, StubOf(b.Bank));
                        int first = w.Count;
                        foreach (var t in op.New)
                        {
                            if (t < b.Count) w.Append(b.Bank.Tones[t].Entry, b.Audio(t));
                            else { w.Append(StubOf(b.Bank), null); res.Warnings.Add(b.Rel + " (" + m.Name + "): a label points at tone " + t + ", past its " + b.Count + " tones (an empty slot put there)."); }
                        }
                        if (!w.Mods.Contains(m.Name)) w.Mods.Add(m.Name);
                        w.Lines.Add(string.Format(CultureInfo.InvariantCulture, "{0}'s {1} new tone(s) appended as tones {2} - {3} ({4}){5}", m.Name, op.New.Count, first, w.Count - 1,
                            string.Join(", ", op.New.Select(t => t < b.Count ? ToneName(b.Bank.Tones[t].Entry) + " (its " + t + ")" : "-").ToArray()),
                            op.Keep >= 0 ? string.Format(CultureInfo.InvariantCulture, "; the bank is {0}'s first {1} tones", m.Name, op.Keep) : ""));
                    }
                }
                else if (w == null)
                {
                    work[b.Rel] = w = BankWork.From(b, b.Count);
                    BaseDiffInfo(w, b);
                }
                else
                {
                    if (!w.Mods.Contains(m.Name)) w.Mods.Add(m.Name);
                    int k0 = b.Row >= 0 ? BaseLabels(b.Row).Where(t => t >= 0).DefaultIfEmpty(-1).Max() + 1 : 0;
                    int tb = TbaseOf(b, w, k0);
                    Diffs(w, b, Math.Min(tb, b.Count));
                    if (b.Count > tb && b.Count > w.Count)
                        w.Lines.Add(string.Format(CultureInfo.InvariantCulture, "{0}'s tones {1} - {2} (past the ones the mods share) not taken: no label of a row it changed reaches them", m.Name, tb, b.Count - 1));
                }
            }
        }

        /// <summary>The tones of the bank both copies have from the base: the base's copy's count when the base folder has
        /// the bank, else the shared prefix (tones equal but their volume) from k0 (the base row's labels reach every tone
        /// below it).</summary>
        int TbaseOf(ModBank b, BankWork w, int k0)
        {
            var bb = BaseBank(b.Rel);
            if (bb != null) return bb.Count;
            int i = Math.Min(k0, Math.Min(w.Count, b.Count));
            while (i < w.Count && i < b.Count && SameTone(w.Entries[i], w.Audios[i], b.Bank.Tones[i].Entry, b.Audio(i), true)) i++;
            return Math.Max(i, k0);
        }

        /// <summary>The report's lines for what the first copy of a bank changed against the base's copy (when known).</summary>
        void BaseDiffInfo(BankWork w, ModBank b)
        {
            var bb = BaseBank(b.Rel);
            if (bb == null) return;
            int vol = 0, rep = 0;
            for (int i = 0; i < Math.Min(bb.Count, w.Count); i++)
            {
                if (SameTone(w.Entries[i], w.Audios[i], bb.Bank.Tones[i].Entry, bb.Audio(i), false)) continue;
                w.SetBy[i] = b.Mod.Name;
                if (SameTone(w.Entries[i], w.Audios[i], bb.Bank.Tones[i].Entry, bb.Audio(i), true)) vol++; else rep++;
            }
            if (vol + rep > 0) w.Lines.Add(string.Format(CultureInfo.InvariantCulture, "{0} changed {1} tone volume(s) and {2} tone(s) of the base's", b.Mod.Name, vol, rep));
        }

        /// <summary>The existing tones (below upto) of the later mod's copy against the bank so far: a volume edit or a
        /// replaced tone taken from whichever mod changed it; both changed it, differently: a conflict.</summary>
        void Diffs(BankWork w, ModBank b, int upto)
        {
            var bb = BaseBank(b.Rel);
            string m = b.Mod.Name;
            int n = Math.Min(upto, Math.Min(w.Count, b.Count));
            for (int i = 0; i < n; i++)
            {
                byte[] e1 = w.Entries[i], a1 = w.Audios[i], e2 = b.Bank.Tones[i].Entry, a2 = b.Audio(i);
                if (SameTone(e1, a1, e2, a2, false)) continue;
                bool volOnly = SameTone(e1, a1, e2, a2, true);
                string name = ToneName(e2);
                string who;
                if (!w.SetBy.TryGetValue(i, out who)) who = w.First.Mod.Name;
                Action take = () =>
                {
                    if (volOnly) w.SetVolume(i, Vol(e2)); else w.Replace(i, e2, a2);
                    w.SetBy[i] = m;
                };
                if (bb != null && i < bb.Count)
                {
                    byte[] eb = bb.Bank.Tones[i].Entry, ab = bb.Audio(i);
                    if (SameTone(e2, a2, eb, ab, false)) continue;          // the later mod left it as the base has it
                    if (SameTone(e1, a1, eb, ab, false))
                    {
                        take();
                        w.Lines.Add(string.Format(CultureInfo.InvariantCulture, "tone {0} ({1}): {2}'s {3}", i, name, m, volOnly ? "volume " + Db(Vol(e2)) + " (the base's " + Db(Vol(eb)) + ")" : "replaced tone"));
                        continue;
                    }
                }
                string what = volOnly ? string.Format(CultureInfo.InvariantCulture, "volume: {0} has {1}, {2} has {3}", who, Db(Vol(e1)), m, Db(Vol(e2)))
                                      : string.Format(CultureInfo.InvariantCulture, "the tone itself (audio / entry) differs between {0} and {1}", who, m);
                string ctx = bb != null ? (bb.Count > i ? " (the base: " + Db(Vol(bb.Bank.Tones[i].Entry)) + ")" : "") : " (the base folder has no copy of the bank to tell which mod changed it)";
                if (Options.LaterWins) take();
                res.Conflicts.Add(string.Format(CultureInfo.InvariantCulture, "{0} tone {1} ({2}): {3}{4}: took {5}'s.", b.Rel, i, name, what, ctx, Options.LaterWins ? m : who));
            }
        }

        int FreeRow(int notFrom)
        {
            for (int r = baseTable.Rows.Count - 1; r > 0; r--)
                if (baseTable.Rows[r].Empty && !claimedRows.Contains(r) && !rows.ContainsKey(r)) return r;
            return -1;
        }

        void MergeRow(SoundMod m, int r, Dictionary<ModBank, Op> ops)
        {
            var bl = BaseLabels(r);
            int n0 = bl.Length;
            var ml = LabelsOf(m.Table, r);
            uint mBank = BankIdOf(m.Table, r);
            var mb = m.Banks.Where(b => b.Row == r).ToList();
            RowState st;
            rows.TryGetValue(r, out st);
            if (mBank == SoundLabelTable.EmptyBank)
            {
                res.Warnings.Add(m.Name + ": row " + RowName(r, BaseBankId(r)) + " is emptied in its table: not taken (the base's / the other mods' kept).");
                return;
            }
            if (st != null && st.Mods.Count > 0 && st.BankId != mBank)
            {
                // two mods gave this row to different banks (both took an empty row for a new bank): the later one moves
                int r2 = FreeRow(r);
                if (r2 < 0) { res.Errors.Add(m.Name + ": row " + RowHex(r) + " is another mod's bank's and no empty row is left to move its bank " + mBank + " to."); return; }
                var st2 = new RowState { BankId = mBank, Labels = ml.ToList(), SetBy = ml.Select(x => m.Name).ToList() };
                st2.Mods.Add(m.Name);
                rows[r2] = st2;
                claimedRows.Add(r2);
                var rm = RemapOf(m);
                for (int l = 0; l < ml.Length; l++)
                {
                    uint o = SoundLabelTable.SoundId(r, l), nn = SoundLabelTable.SoundId(r2, l);
                    rm[o] = nn;
                    res.Remaps.Add(new SoundIdRemap { Mod = m.Name, Fighter = mb.Count > 0 ? mb[0].Fighter : "", Old = o, New = nn, Tone = mb.Count > 0 && ml[l] >= 0 && ml[l] < mb[0].Count ? ToneName(mb[0].Bank.Tones[ml[l]].Entry) : "" });
                    if (ml[l] >= 0) idChecks.Add(new IdCheck { Mod = m, Row = r2, Label = l, ModTone = ml[l], Old = o, New = nn, Banks = mb, NewTone = false });
                }
                foreach (var b in mb) b.Row = r2;
                st2.Lines.Add(string.Format(CultureInfo.InvariantCulture, "{0}: moved here from row {1} (that row is {2}'s bank {3}'s; {0}'s bank {4} is its own): its {5} labels, every id remapped",
                                            m.Name, RowHex(r), st.Mods[0], st.BankId, mBank, ml.Length));
                res.Warnings.Add(string.Format(CultureInfo.InvariantCulture, "{0} and {1} both give row {2} to a bank of their own ({3} and {4}): {1}'s moved to the empty row {5}, all its ids on it remapped.",
                                               st.Mods[0], m.Name, RowHex(r), st.BankId, mBank, RowHex(r2)));
                return;
            }
            if (st == null)
            {
                st = new RowState { BankId = BaseBankId(r), Labels = bl.ToList(), SetBy = bl.Select(x => (string)null).ToList() };
                rows[r] = st;
            }
            if (st.BankId != mBank)
            {
                st.Lines.Add(m.Name + ": the row's bank id " + (st.BankId == SoundLabelTable.EmptyBank ? "(empty)" : st.BankId.ToString(CultureInfo.InvariantCulture)) + " -> " + mBank);
                st.BankId = mBank;
            }
            bool fallback = st.Mods.Count > 0;
            st.Mods.Add(m.Name);

            // the tones: the mod's banks on the row that another mod's copy is already in get its new tones appended
            int k0 = bl.Where(t => t >= 0).DefaultIfEmpty(-1).Max() + 1;
            var overl = mb.Where(b => work.ContainsKey(b.Rel)).ToList();
            int tb = k0;
            var tbOf = new Dictionary<ModBank, int>();
            foreach (var b in overl) { tbOf[b] = TbaseOf(b, work[b.Rel], k0); tb = Math.Max(tb, tbOf[b]); }
            var setIdx = Enumerable.Range(0, ml.Length).Where(i => i >= n0 || ml[i] != bl[i]).ToList();
            var newTones = setIdx.Select(i => ml[i]).Where(t => t >= tb).Distinct().OrderBy(t => t).ToList();
            var map = new Dictionary<int, int>();
            if (overl.Count > 0)
            {
                if (newTones.Count > 0)
                {
                    int F = 0;
                    foreach (var b in mb) F = Math.Max(F, work.ContainsKey(b.Rel) ? work[b.Rel].Count : Math.Min(newTones[0], b.Count));
                    for (int j = 0; j < newTones.Count; j++) map[newTones[j]] = F + j;
                    foreach (var b in mb) ops[b] = new Op { Keep = work.ContainsKey(b.Rel) ? -1 : Math.Min(newTones[0], b.Count), F = F, New = newTones, Tbase = tbOf.ContainsKey(b) ? tbOf[b] : tb };
                }
                else foreach (var b in overl) ops[b] = new Op { Tbase = tbOf[b] };
            }
            Func<int, int> mapT = t => map.ContainsKey(t) ? map[t] : t;
            var rmap = RemapOf(m);
            int edits = 0, appended = 0, lost = 0;
            var ids = new List<string>();
            for (int i = 0; i < Math.Max(n0, ml.Length); i++)
            {
                if (i < n0)
                {
                    if (i >= ml.Length) { res.Warnings.Add(string.Format(CultureInfo.InvariantCulture, "{0}: row {1} is shorter than the base's ({2} labels, the base {3}): the missing labels are kept.", m.Name, RowHex(r), ml.Length, n0)); break; }
                    if (ml[i] == bl[i]) continue;
                    int nv = mapT(ml[i]);
                    if (st.SetBy[i] != null && st.Labels[i] != nv)
                    {
                        res.Conflicts.Add(string.Format(CultureInfo.InvariantCulture, "row {0} label {1} ({2}): {3} points it at tone {4}, {5} at tone {6} (the base: {7}): took {8}'s.",
                                                        RowHex(r), i, Hex(SoundLabelTable.SoundId(r, i)), st.SetBy[i], st.Labels[i], m.Name, nv, bl[i], Options.LaterWins ? m.Name : st.SetBy[i]));
                        if (!Options.LaterWins) { lost++; continue; }
                    }
                    st.Labels[i] = nv;
                    st.SetBy[i] = m.Name;
                    edits++;
                    if (nv >= 0) idChecks.Add(new IdCheck { Mod = m, Row = r, Label = i, ModTone = ml[i], Old = SoundLabelTable.SoundId(r, i), New = SoundLabelTable.SoundId(r, i), Banks = mb, NewTone = ml[i] >= tb });
                }
                else
                {
                    int nl = st.Labels.Count;
                    if (nl >= SoundAdder.MaxLabels) { res.Errors.Add(string.Format(CultureInfo.InvariantCulture, "row {0} is full (65536 labels): {1}'s labels from {2} don't fit.", RowHex(r), m.Name, i)); return; }
                    st.Labels.Add(mapT(ml[i]));
                    st.SetBy.Add(m.Name);
                    appended++;
                    uint o = SoundLabelTable.SoundId(r, i), nn = SoundLabelTable.SoundId(r, nl);
                    if (nl != i)
                    {
                        rmap[o] = nn;
                        res.Remaps.Add(new SoundIdRemap { Mod = m.Name, Fighter = mb.Count > 0 ? mb[0].Fighter : "", Old = o, New = nn, Tone = mb.Count > 0 && ml[i] >= 0 && ml[i] < mb[0].Count ? ToneName(mb[0].Bank.Tones[ml[i]].Entry) : "" });
                    }
                    ids.Add(Hex(nn));
                    if (ml[i] >= 0) idChecks.Add(new IdCheck { Mod = m, Row = r, Label = nl, ModTone = ml[i], Old = o, New = nn, Banks = mb, NewTone = ml[i] >= tb });
                }
            }
            string how = !fallback ? "taken from " + m.Name : m.Name + " merged in (the row was " + string.Join(" + ", st.Mods.Take(st.Mods.Count - 1).ToArray()) + "'s too: the fallback)";
            var parts = new List<string>();
            if (appended > 0) parts.Add(string.Format(CultureInfo.InvariantCulture, "+{0} label(s) {1} - {2} (ids {3} - {4})", appended, st.Labels.Count - appended, st.Labels.Count - 1, ids.First(), ids.Last()));
            if (edits > 0) parts.Add(edits + " existing label(s) re-pointed");
            if (lost > 0) parts.Add(lost + " re-pointed label(s) not taken (conflicts)");
            if (map.Count > 0) parts.Add(string.Format(CultureInfo.InvariantCulture, "its new tones {0} -> {1}", string.Join(",", map.Keys.Select(x => x.ToString(CultureInfo.InvariantCulture)).ToArray()), string.Join(",", map.Values.Select(x => x.ToString(CultureInfo.InvariantCulture)).ToArray())));
            if (fallback && appended > 0 && rmap.Count > 0) parts.Add("its new ids remapped (below)");
            if (mb.Select(b => b.Fighter).Distinct().Count() > 0 && fallback)
            {
                var others = res.Mods.Where(x => x != m && st.Mods.Contains(x.Name)).SelectMany(x => x.Banks.Where(b => b.Row == r)).Select(b => b.Fighter).Distinct().ToList();
                var mine = mb.Select(b => b.Fighter).Distinct().ToList();
                if (others.Any(f => !mine.Contains(f)))
                    parts.Add("the row is shared by fighters " + string.Join(", ", others.Union(mine).ToArray()) + " (a port's alias row): their new labels don't overlap, each fighter's banks stay its own");
            }
            st.Lines.Add(how + (parts.Count > 0 ? ": " + string.Join("; ", parts.ToArray()) : ""));
        }

        // ------------------------------------------------------------------ outputs

        class OutFile
        {
            public byte[] Data;
            public string CopyFrom, Mod, What;
        }

        Dictionary<string, OutFile> BuildOutputs()
        {
            var files = new Dictionary<string, OutFile>(StringComparer.OrdinalIgnoreCase);
            // the table: the base's, the merged rows' new label lists appended to its pool
            var t = SoundLabelTable.Parse(baseBytes);
            foreach (var kv in rows.OrderBy(x => x.Key))
            {
                int r = kv.Key;
                var st = kv.Value;
                if (st.BankId == BaseBankId(r) && st.Labels.SequenceEqual(BaseLabels(r))) continue;
                t.SetRow(r, st.BankId, st.Labels);
                res.RowsFrom[r] = st.Mods.ToList();
                res.RowLines.Add("row " + RowName(r, st.BankId) + ": " + BaseLabels(r).Length + " -> " + st.Labels.Count + " labels");
                foreach (var l in st.Lines) res.RowLines.Add("    " + l);
            }
            res.Table = t.Build();
            // every other row the base's, byte for byte; the base's label words in place
            var back = SoundLabelTable.Parse(res.Table);
            int same = 0;
            for (int r = 0; r < baseTable.Rows.Count; r++)
                if (!res.RowsFrom.ContainsKey(r))
                {
                    if (back.Rows[r].BankId == baseTable.Rows[r].BankId && back.Rows[r].Count == baseTable.Rows[r].Count && back.Rows[r].Offset == baseTable.Rows[r].Offset && back.Rows[r].Zero == baseTable.Rows[r].Zero) same++;
                    else res.Errors.Add("soundlabeltable.bin: row " + RowHex(r) + " changed (it shouldn't)");
                }
            int pool = 16 + 16 * baseTable.Rows.Count;
            bool poolKept = back.Rows.Count == baseTable.Rows.Count && res.Table.Length >= baseBytes.Length && SameBytes(res.Table.Skip(pool).Take(baseBytes.Length - pool).ToArray(), baseBytes.Skip(pool).ToArray());
            res.CheckLines.Add(string.Format(CultureInfo.InvariantCulture, "soundlabeltable.bin: {0} row(s) from the mods; the other {1} rows the base's byte for byte{2}", res.RowsFrom.Count, same,
                poolKept ? ", the base's label words in place" : back.Rows.Count != baseTable.Rows.Count ? " (rows added: " + baseTable.Rows.Count + " -> " + back.Rows.Count + ")" : ""));
            files["sound/config/soundlabeltable.bin"] = new OutFile { Data = res.Table, What = "table" };

            // the banks
            var built = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
            foreach (var w in work.Values.OrderBy(x => x.Rel, StringComparer.OrdinalIgnoreCase))
            {
                if (!w.Changed)
                {
                    files[w.Rel] = new OutFile { CopyFrom = w.First.Bank.Path, Mod = w.First.Mod.Name, What = "bank" };
                    res.BankLines.Add(w.Rel + ": " + w.First.Mod.Name + "'s, copied unchanged" + (w.Mods.Count > 1 ? " (" + string.Join(", ", w.Mods.Skip(1).ToArray()) + "'s copy the same or nothing taken from it)" : ""));
                    foreach (var l in w.Lines) res.BankLines.Add("    " + l);
                    continue;
                }
                byte[] data = w.Build();
                built[w.Rel] = data;
                var probs = BankCheck.Validate(data, w.FirstAppended, w.FirstAppended != int.MaxValue);
                foreach (var p in probs) res.Errors.Add(w.Rel + ": " + p);
                var rb = Nus3Bank.Load(new MemoryStream(data), w.Rel);
                bool ok = rb.Tones.Count == w.Count && rb.Id == w.First.Bank.Id;
                for (int i = 0; ok && i < w.Count; i++)
                {
                    var tt = rb.Tones[i];
                    if (!SameBytes(tt.Entry, w.Entries[i])) ok = false;
                    else if (w.Audios[i] != null)
                    {
                        var a = new byte[tt.DataSize];
                        Array.Copy(data, rb.PackOffset + tt.DataOffset, a, 0, a.Length);
                        if (!SameBytes(a, w.Audios[i])) ok = false;
                    }
                }
                if (!ok) res.Errors.Add(w.Rel + ": the merged bank doesn't read back as built");
                files[w.Rel] = new OutFile { Data = data, Mod = string.Join("+", w.Mods.ToArray()), What = "bank" };
                res.MergedBanks.Add(w.Rel);
                res.BankLines.Add(string.Format(CultureInfo.InvariantCulture, "{0}: merged ({1}): {2} -> {3} tones; {4}", w.Rel, string.Join(" + ", w.Mods.ToArray()), w.First.Count, w.Count,
                                                probs.Count == 0 ? "layout checked (BankCheck), read back" : probs.Count + " layout problem(s)"));
                foreach (var l in w.Lines) res.BankLines.Add("    " + l);
            }

            // every id a mod set reaches its own tone in the merged table and banks
            int checkedIds = 0, bad = 0;
            var cache = new Dictionary<string, Nus3Bank>(StringComparer.OrdinalIgnoreCase);
            Func<string, Nus3Bank> merged = rel =>
            {
                Nus3Bank nb;
                if (cache.TryGetValue(rel, out nb)) return nb;
                OutFile f;
                if (!files.TryGetValue(rel, out f)) return null;
                nb = f.Data != null ? Nus3Bank.Load(new MemoryStream(f.Data), rel) : Nus3Bank.Load(f.CopyFrom);
                cache[rel] = nb;
                return nb;
            };
            foreach (var c in idChecks)
            {
                uint bank;
                int t2 = back.ToneOf(c.New, out bank);
                foreach (var b in c.Banks)
                {
                    checkedIds++;
                    var nb = merged(b.Rel);
                    string why = null;
                    if (nb == null) why = "its bank isn't in the output";
                    else if (t2 < 0 || t2 >= nb.Tones.Count) why = "it reaches tone " + t2 + ", not in the merged bank";
                    else if (c.ModTone < b.Count)
                    {
                        var want = b.Bank.Tones[c.ModTone];
                        var got = nb.Tones[t2];
                        byte[] wa = b.Audio(c.ModTone), ga = null;
                        if (got.HasAudio)
                        {
                            byte[] src = built.ContainsKey(b.Rel) ? built[b.Rel] : null;
                            if (src != null) { ga = new byte[got.DataSize]; Array.Copy(src, nb.PackOffset + got.DataOffset, ga, 0, ga.Length); }
                            else ga = nb.ReadAudio(got);
                        }
                        if (want.Name != got.Name || (c.NewTone && !SameBytes(wa, ga))) why = "it reaches " + got.Name + ", not " + want.Name;
                    }
                    if (why != null) { bad++; res.Errors.Add(string.Format(CultureInfo.InvariantCulture, "{0}'s {1} (now {2}) in {3}: {4}", c.Mod.Name, Hex(c.Old), Hex(c.New), b.Rel, why)); }
                }
            }
            res.CheckLines.Add(string.Format(CultureInfo.InvariantCulture, "{0} id / bank pair(s) the mods set checked in the merged table and banks: {1}", checkedIds, bad == 0 ? "each reaches its own tone (name and audio)" : bad + " wrong"));

            // the scripts: the remapped mods' rewritten; an ACMD file several mods ship, merged script by script
            var rewritten = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);     // mod name + "|" + rel
            foreach (var m in res.Mods)
            {
                var rm = RemapOf(m);
                if (rm.Count > 0 && Options.RewriteScripts) RewriteScripts(m, rm, rewritten);
                else if (rm.Count > 0)
                    res.Warnings.Add(m.Name + ": " + rm.Count + " of its sound ids changed and its scripts weren't rewritten (\"rewrite scripts\" is off): they still play the old ids. Change them by hand (the remap list).");
                if (rm.Count > 0) ScanMsc(m, rm);
            }
            var handled = MergeAcmdFiles(files, rewritten);
            // the other files
            if (Options.CopyOtherFiles)
                foreach (var m in res.Mods)
                    foreach (var f in Directory.GetFiles(m.DataRoot, "*", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
                    {
                        string rel = SoundMod.RelOf(m.DataRoot, f);
                        if (rel.Equals("sound/config/soundlabeltable.bin", StringComparison.OrdinalIgnoreCase) || rel.EndsWith(".nus3bank", StringComparison.OrdinalIgnoreCase) || handled.Contains(rel)) continue;
                        OutFile have;
                        if (files.TryGetValue(rel, out have))
                        {
                            if (have.Mod == m.Name) continue;              // its own rewritten script
                            byte[] a = have.Data ?? File.ReadAllBytes(have.CopyFrom), b = File.ReadAllBytes(f);
                            if (SameBytes(a, b)) continue;
                            res.Conflicts.Add(string.Format(CultureInfo.InvariantCulture, "{0}: {1} and {2} both ship it, different: took {3}'s.", rel, have.Mod, m.Name, Options.LaterWins ? m.Name : have.Mod));
                            if (!Options.LaterWins) continue;
                        }
                        files[rel] = new OutFile { CopyFrom = f, Mod = m.Name, What = "file" };
                    }
            MergeAliases(files);
            return files;
        }

        static IEnumerable<string> AcmdFiles(SoundMod m)
        {
            var fighter = Path.Combine(m.DataRoot, "fighter");
            if (!Directory.Exists(fighter)) yield break;
            foreach (var f in Directory.GetFiles(fighter, "*.bin", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            {
                if (!SoundMod.RelOf(m.DataRoot, f).Contains("/script/animcmd/")) continue;
                bool acmd = false;
                try { using (var s = File.OpenRead(f)) { var h = new byte[4]; acmd = s.Read(h, 0, 4) == 4 && Encoding.ASCII.GetString(h) == "ACMD"; } } catch (Exception) { }
                if (acmd) yield return f;
            }
        }

        /// <summary>The ACMD files to write: a remapped mod's rewritten ones; one several mods ship (differently) merged
        /// script by script (a script only one mod changed from the base's copy, when the base folder has the file, is
        /// that mod's; scripts in one mod only are taken; two mods' different scripts of one hash: a conflict). Returns
        /// the files handled (the other files' copy skips them).</summary>
        HashSet<string> MergeAcmdFiles(Dictionary<string, OutFile> files, Dictionary<string, byte[]> rewritten)
        {
            var handled = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var byRel = new SortedDictionary<string, List<KeyValuePair<SoundMod, string>>>(StringComparer.OrdinalIgnoreCase);
            foreach (var m in res.Mods)
                foreach (var f in AcmdFiles(m))
                {
                    string rel = SoundMod.RelOf(m.DataRoot, f);
                    List<KeyValuePair<SoundMod, string>> l;
                    if (!byRel.TryGetValue(rel, out l)) byRel[rel] = l = new List<KeyValuePair<SoundMod, string>>();
                    l.Add(new KeyValuePair<SoundMod, string>(m, f));
                }
            string tmp = Path.Combine(Path.GetTempPath(), "sm4sh_acmd_" + Guid.NewGuid().ToString("N").Substring(0, 8));
            Directory.CreateDirectory(tmp);
            try
            {
                foreach (var kv in byRel)
                {
                    string rel = kv.Key;
                    var versions = kv.Value.Select(x =>
                    {
                        byte[] d;
                        bool rw = rewritten.TryGetValue(x.Key.Name + "|" + rel, out d);
                        return new { Mod = x.Key, Data = rw ? d : File.ReadAllBytes(x.Value), Rewritten = rw, Path = x.Value };
                    }).ToList();
                    bool anyRewritten = versions.Any(v => v.Rewritten);
                    if (versions.Count == 1 || versions.All(v => SameBytes(v.Data, versions[0].Data)))
                    {
                        if (anyRewritten || Options.CopyOtherFiles)
                        {
                            var v = versions.FirstOrDefault(x => x.Rewritten) ?? versions[0];
                            files[rel] = new OutFile { Data = v.Rewritten ? v.Data : null, CopyFrom = v.Rewritten ? null : v.Path, Mod = v.Mod.Name, What = "script" };
                            handled.Add(rel);
                        }
                        continue;
                    }
                    // several mods ship it, differently: script by script
                    handled.Add(rel);
                    byte[] baseData = null;
                    if (baseDataRoot != null)
                    {
                        var bp = Path.Combine(baseDataRoot, rel.Replace('/', Path.DirectorySeparatorChar));
                        try { if (File.Exists(bp)) baseData = File.ReadAllBytes(bp); } catch (Exception) { }
                    }
                    Dictionary<uint, AcmdSoundIds.Raw> baseScripts = null;
                    try { if (baseData != null) baseScripts = AcmdSoundIds.Scripts(baseData, tmp); } catch (Exception) { baseScripts = null; }
                    var parsed = new List<KeyValuePair<string, Dictionary<uint, AcmdSoundIds.Raw>>>();
                    bool bad = false;
                    foreach (var v in versions)
                    {
                        try { parsed.Add(new KeyValuePair<string, Dictionary<uint, AcmdSoundIds.Raw>>(v.Mod.Name, AcmdSoundIds.Scripts(v.Data, tmp))); }
                        catch (Exception ex) { res.Warnings.Add(rel + " (" + v.Mod.Name + "): not read as ACMD (" + ex.Message + ")"); bad = true; }
                    }
                    if (bad || versions.Any(v => v.Data[4] != versions[0].Data[4]))
                    {
                        var v = Options.LaterWins ? versions.Last() : versions.First();
                        res.Conflicts.Add(rel + ": " + string.Join(", ", versions.Select(x => x.Mod.Name).ToArray()) + " ship it, differently, and it can't be merged script by script: took " + v.Mod.Name + "'s whole file.");
                        files[rel] = new OutFile { Data = v.Data, Mod = v.Mod.Name, What = "script" };
                        continue;
                    }
                    var keys = new SortedSet<uint>(parsed.SelectMany(x => x.Value.Keys));
                    var chosen = new SortedDictionary<uint, AcmdSoundIds.Raw>();
                    var from = new Dictionary<string, int>();
                    int conflicts = 0;
                    foreach (var crc in keys)
                    {
                        AcmdSoundIds.Raw pick = null, b = null;
                        string by = null;
                        if (baseScripts != null) baseScripts.TryGetValue(crc, out b);
                        if (b != null) pick = b;
                        foreach (var p in parsed)
                        {
                            AcmdSoundIds.Raw r;
                            if (!p.Value.TryGetValue(crc, out r)) continue;
                            if (b != null && SameBytes(r.Bytes, b.Bytes)) continue;        // this mod left it as the base has it
                            if (by == null) { pick = r; by = p.Key; continue; }
                            if (SameBytes(r.Bytes, pick.Bytes)) continue;
                            conflicts++;
                            res.Conflicts.Add(string.Format(CultureInfo.InvariantCulture, "{0} script 0x{1:X8}: {2} and {3} both changed it, differently{4}: took {5}'s.", rel, crc, by, p.Key,
                                                            baseScripts == null ? " (the base folder has no copy of the file to tell which changed it)" : "", Options.LaterWins ? p.Key : by));
                            if (Options.LaterWins) { pick = r; by = p.Key; }
                        }
                        if (pick == null) continue;
                        chosen[crc] = pick;
                        string k = by ?? "the base";
                        from[k] = (from.ContainsKey(k) ? from[k] : 0) + 1;
                    }
                    var data = AcmdSoundIds.Build(versions[0].Data, chosen);
                    var back = AcmdSoundIds.Scripts(data, tmp);
                    if (back.Count != chosen.Count || chosen.Any(c => !back.ContainsKey(c.Key) || !SameBytes(back[c.Key].Bytes, c.Value.Bytes)))
                    {
                        res.Errors.Add(rel + ": the script-by-script merge doesn't read back");
                        continue;
                    }
                    files[rel] = new OutFile { Data = data, Mod = string.Join("+", versions.Select(x => x.Mod.Name).ToArray()), What = "script" };
                    res.ScriptLines.Add(string.Format(CultureInfo.InvariantCulture, "{0}: shipped by {1}: merged script by script ({2} scripts: {3}){4}{5}", rel, string.Join(", ", versions.Select(x => x.Mod.Name + (x.Rewritten ? " (rewritten)" : "")).ToArray()),
                        chosen.Count, string.Join(", ", from.Select(x => x.Value + " " + x.Key + "'s").ToArray()), baseScripts != null ? ", against the base's copy" : ", no base copy of the file",
                        conflicts > 0 ? "; " + conflicts + " conflict(s)" : ""));
                }
            }
            finally { try { Directory.Delete(tmp, true); } catch (Exception) { } }
            return handled;
        }

        void RewriteScripts(SoundMod m, Dictionary<uint, uint> rm, Dictionary<string, byte[]> rewritten)
        {
            var fighter = Path.Combine(m.DataRoot, "fighter");
            if (!Directory.Exists(fighter)) return;
            string tmp = Path.Combine(Path.GetTempPath(), "sm4sh_acmd_" + Guid.NewGuid().ToString("N").Substring(0, 8));
            Directory.CreateDirectory(tmp);
            try
            {
                foreach (var f in Directory.GetFiles(fighter, "*.bin", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
                {
                    string rel = SoundMod.RelOf(m.DataRoot, f);
                    if (!rel.Contains("/script/animcmd/")) continue;
                    var data = File.ReadAllBytes(f);
                    if (data.Length < 16 || Encoding.ASCII.GetString(data, 0, 4) != "ACMD") continue;
                    AcmdSoundIds.Result r;
                    try { r = AcmdSoundIds.Rewrite(data, rm, tmp); }
                    catch (Exception ex) { res.Warnings.Add(rel + " (" + m.Name + "): not read as ACMD (" + ex.Message + "): not rewritten; check it for the remapped ids by hand."); continue; }
                    foreach (var p in r.Problems) res.Warnings.Add(rel + " (" + m.Name + "): " + p);
                    if (r.Count == 0 || r.Data == null) continue;
                    rewritten[m.Name + "|" + rel] = r.Data;
                    res.RewrittenScripts.Add(rel);
                    res.ScriptLines.Add(string.Format(CultureInfo.InvariantCulture, "{0} ({1}): {2} sound id(s) rewritten{3}", rel, m.Name, r.Count, r.RoundTrip ? "; every changed script decompiles and compiles back to its bytes" : ""));
                    foreach (var c in r.Changes) res.ScriptLines.Add("    " + c);
                }
            }
            finally { try { Directory.Delete(tmp, true); } catch (Exception) { } }
        }

        void ScanMsc(SoundMod m, Dictionary<uint, uint> rm)
        {
            var fighter = Path.Combine(m.DataRoot, "fighter");
            if (!Directory.Exists(fighter)) return;
            foreach (var f in Directory.GetFiles(fighter, "*.mscsb", SearchOption.AllDirectories))
            {
                var d = File.ReadAllBytes(f);
                var found = new SortedSet<uint>();
                for (int i = 0; i + 4 <= d.Length; i++)
                {
                    uint le = (uint)(d[i] | d[i + 1] << 8 | d[i + 2] << 16 | d[i + 3] << 24), be = (uint)(d[i] << 24 | d[i + 1] << 16 | d[i + 2] << 8 | d[i + 3]);
                    if (rm.ContainsKey(le)) found.Add(le);
                    if (rm.ContainsKey(be)) found.Add(be);
                }
                if (found.Count > 0)
                    res.Warnings.Add(string.Format(CultureInfo.InvariantCulture, "{0} ({1}): MSC holds {2} (remapped ids, or the same numbers by chance): MSC isn't rewritten, change them by hand if they are its sounds.",
                                                   SoundMod.RelOf(m.DataRoot, f), m.Name, string.Join(", ", found.Select(Hex).ToArray())));
            }
        }

        void MergeAliases(Dictionary<string, OutFile> files)
        {
            var sets = new SortedDictionary<string, Dictionary<uint, string>>(StringComparer.OrdinalIgnoreCase);
            var from = new Dictionary<string, Dictionary<uint, string>>(StringComparer.OrdinalIgnoreCase);
            foreach (var m in res.Mods)
            {
                var rm = RemapOf(m);
                foreach (var f in m.AliasFiles)
                {
                    string set = Path.GetFileNameWithoutExtension(f);
                    Dictionary<uint, string> d, who;
                    if (!sets.TryGetValue(set, out d)) { sets[set] = d = new Dictionary<uint, string>(); from[set] = new Dictionary<uint, string>(); }
                    who = from[set];
                    int n = 0, moved = 0;
                    var clashes = new List<string>();
                    foreach (var kv in SoundAliases.ReadFile(f))
                    {
                        uint id = kv.Key, nid;
                        if (rm.TryGetValue(id, out nid)) { id = nid; moved++; }
                        string have;
                        if (d.TryGetValue(id, out have) && have != kv.Value)
                        {
                            clashes.Add(string.Format(CultureInfo.InvariantCulture, "    {0} {1}: {2} \"{3}\", {4} \"{5}\": took {6}'s", set + ".txt", Hex(id), who[id], have, m.Name, kv.Value, Options.LaterWins ? m.Name : who[id]));
                            if (!Options.LaterWins) continue;
                        }
                        d[id] = kv.Value;
                        who[id] = m.Name;
                        n++;
                    }
                    res.AliasLines.Add(string.Format(CultureInfo.InvariantCulture, "{0}: {1}.txt, {2} alias(es){3}", m.Name, set, n, moved > 0 ? ", " + moved + " on remapped ids (moved to the new ids)" : ""));
                    res.AliasLines.AddRange(clashes);
                }
            }
            foreach (var kv in sets)
            {
                var path = "Aliases/sounds/" + kv.Key + ".txt";
                var tmp = Path.GetTempFileName();
                try { SoundAliases.WriteFile(tmp, kv.Key, kv.Value); files[path] = new OutFile { Data = File.ReadAllBytes(tmp), What = "aliases" }; }
                finally { File.Delete(tmp); }
            }
        }

        void Write(string outDir, Dictionary<string, OutFile> files)
        {
            Directory.CreateDirectory(outDir);
            foreach (var kv in files.OrderBy(x => x.Key, StringComparer.OrdinalIgnoreCase))
            {
                string p = Path.Combine(outDir, kv.Key.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(p));
                if (kv.Value.Data != null) File.WriteAllBytes(p, kv.Value.Data);
                else File.Copy(kv.Value.CopyFrom, p, false);
                res.Written.Add(p);
            }
            // read back
            int ok = 0;
            foreach (var kv in files)
            {
                string p = Path.Combine(outDir, kv.Key.Replace('/', Path.DirectorySeparatorChar));
                var want = kv.Value.Data ?? File.ReadAllBytes(kv.Value.CopyFrom);
                if (SameBytes(File.ReadAllBytes(p), want)) ok++; else res.Errors.Add(p + " didn't read back as written");
            }
            if (!SoundLabelTable.Load(Path.Combine(Path.Combine(Path.Combine(outDir, "sound"), "config"), "soundlabeltable.bin")).Build().SequenceEqual(res.Table))
                res.Errors.Add("the written soundlabeltable.bin doesn't parse back to itself");
            res.CheckLines.Add(string.Format(CultureInfo.InvariantCulture, "{0} file(s) written to {1}, each read back byte for byte ({2} ok)", files.Count, outDir, ok));
        }

        // ------------------------------------------------------------------ the report

        string BuildReport()
        {
            var sb = new StringBuilder();
            Action<string> L = s => sb.Append(s).Append("\r\n");
            L("Sound mod merge" + (Version.Length > 0 ? " (Sm4shCommand " + Version + ")" : "") + ", " + DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + (res.DryRun ? "  [check only: nothing written]" : ""));
            L("");
            L("Base: " + res.BaseTablePath + (baseTable != null ? " (" + baseTable.Rows.Count + " rows)" : ""));
            L("Mods, in order (" + (Options.LaterWins ? "a later mod wins a conflict" : "the first mod wins a conflict") + "):");
            for (int i = 0; i < res.Mods.Count; i++)
            {
                var m = res.Mods[i];
                L(string.Format(CultureInfo.InvariantCulture, "  {0}. {1}: {2}", i + 1, m.Name, m.Source));
                L("     data folder " + m.DataRoot + "; " + (m.Table != null ? "its own soundlabeltable.bin" : "no soundlabeltable.bin") + "; " + m.Banks.Count + " bank(s)" +
                  (m.Banks.Count > 0 ? ": " + string.Join(", ", m.Banks.Select(b => b.Rel + (b.Row >= 0 ? " (row " + RowHex(b.Row) + ")" : " (no row)")).ToArray()) : ""));
                foreach (var n in m.Notes) L("     " + n);
            }
            if (res.OutDir != null) L("Output: " + res.OutDir);
            L("");
            if (res.Errors.Count > 0)
            {
                L("== ERRORS (nothing written)");
                foreach (var e in res.Errors) L("  " + e);
                L("");
            }
            L("== Rows (soundlabeltable.bin)");
            if (res.RowLines.Count == 0) L("  (none changed)");
            foreach (var l in res.RowLines) L("  " + l);
            L("  Every other row: the base's, byte for byte.");
            L("");
            L("== Banks");
            if (res.BankLines.Count == 0) L("  (none)");
            foreach (var l in res.BankLines) L("  " + l);
            L("");
            L("== Sound id remaps (old -> new): put the new ids in the mod's scripts");
            if (res.Remaps.Count == 0) L("  (none: every mod's ids are as it made them)");
            foreach (var g in res.Remaps.GroupBy(x => x.Mod))
            {
                L("  " + g.Key + ":");
                foreach (var x in g) L(string.Format(CultureInfo.InvariantCulture, "    {0} -> {1}   {2}{3}", Hex(x.Old), Hex(x.New), x.Fighter, x.Tone.Length > 0 ? " " + x.Tone : ""));
            }
            L("");
            L("== Scripts rewritten");
            if (res.ScriptLines.Count == 0) L(res.Remaps.Count == 0 ? "  (none needed)" : Options.RewriteScripts ? "  (none of the mods' ACMD scripts uses a remapped id)" : "  (off)");
            foreach (var l in res.ScriptLines) L("  " + l);
            L("");
            L("== Aliases (Aliases/sounds)");
            if (res.AliasLines.Count == 0) L("  (no Aliases/sounds files in the mods)");
            foreach (var l in res.AliasLines) L("  " + l);
            L("");
            L("== Conflicts");
            if (res.Conflicts.Count == 0) L("  (none)");
            foreach (var l in res.Conflicts) L("  " + l);
            L("");
            L("== Warnings");
            if (res.Warnings.Count == 0) L("  (none)");
            foreach (var l in res.Warnings) L("  " + l);
            L("");
            L("== Checks");
            foreach (var l in res.CheckLines) L("  " + l);
            L("");
            L("Install: the mods as they are, then this folder over them (its sound/config/soundlabeltable.bin, banks and scripts");
            L("replace theirs). Copy Aliases/sounds/*.txt next to Sm4shCommand.exe (Aliases\\sounds) to see the names in the viewer.");
            return sb.ToString();
        }
    }

    /// <summary>
    /// Sound ids in ACMD files (v1.7.34, Merge sound mods): the file read with SALT's ACMDFile (Sm4shCommand's reader), each
    /// command's place walked from its script's offset (the reader's own order and sizes), and only the id parameters of
    /// the Sound commands (Events.cfg's Category Sound: Sound_Effect SFX, Transient_Sound_Effect, Stop_Sound_Effect,
    /// PLAY_SE_REMAIN Se, PLAY_STEP_FLIPPABLE SoundID / SoundIDFlip, ...) whose value is in the remap patched in place:
    /// every other byte of the file stays. Checked: the patched file read again (the same commands, the old parameters but
    /// the patched ones), and each changed script decompiled to text and compiled back to the same bytes.
    /// </summary>
    public static class AcmdSoundIds
    {
        public static readonly HashSet<string> Params = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            { "SFX", "Se", "Se1", "Se2", "SoundID", "SoundIDFlip", "Voice1", "Voice2" };

        public class Result
        {
            public byte[] Data;
            public int Count;
            public bool RoundTrip = true;
            public readonly List<string> Changes = new List<string>(), Problems = new List<string>();
        }

        /// <summary>A script's bytes as in its file (its commands, to its Script_End) and its command count.</summary>
        public class Raw
        {
            public byte[] Bytes;
            public int Commands;
        }

        /// <summary>Every script of an ACMD file, as its bytes (read with ACMDFile: its commands' sizes).</summary>
        public static Dictionary<uint, Raw> Scripts(byte[] data, string tmpDir)
        {
            bool big = data[4] == 0;
            Func<int, uint> W = at => big ? (uint)(data[at] << 24 | data[at + 1] << 16 | data[at + 2] << 8 | data[at + 3]) : (uint)(data[at] | data[at + 1] << 8 | data[at + 2] << 16 | data[at + 3] << 24);
            var f = Read(data, tmpDir);
            var d = new Dictionary<uint, Raw>();
            int n = (int)W(8);
            for (int i = 0; i < n; i++)
            {
                uint crc = W(0x10 + 8 * i);
                int pos = (int)W(0x14 + 8 * i);
                var sc = (ACMDScript)f.Scripts[crc];
                int size = sc.Commands.Cast<ACMDCommand>().Sum(c => c.Size);
                if (pos + size > data.Length) throw new InvalidDataException(string.Format(CultureInfo.InvariantCulture, "script 0x{0:X8} runs past the file", crc));
                var b = new byte[size];
                Array.Copy(data, pos, b, 0, size);
                d[crc] = new Raw { Bytes = b, Commands = sc.Count };
            }
            return d;
        }

        /// <summary>An ACMD file of these scripts (in hash order, as SALT writes them), its header ("ACMD", version) as
        /// the template's.</summary>
        public static byte[] Build(byte[] template, IDictionary<uint, Raw> scripts)
        {
            bool big = template[4] == 0;
            Action<List<byte>, uint> P = (l, v) =>
            {
                if (big) { l.Add((byte)(v >> 24)); l.Add((byte)(v >> 16)); l.Add((byte)(v >> 8)); l.Add((byte)v); }
                else { l.Add((byte)v); l.Add((byte)(v >> 8)); l.Add((byte)(v >> 16)); l.Add((byte)(v >> 24)); }
            };
            var keys = scripts.Keys.OrderBy(k => k).ToList();
            var o = new List<byte>(template.Take(8));
            P(o, (uint)keys.Count);
            P(o, (uint)keys.Sum(k => scripts[k].Commands));
            int at = 0x10 + 8 * keys.Count;
            foreach (var k in keys) { P(o, k); P(o, (uint)at); at += scripts[k].Bytes.Length; }
            foreach (var k in keys) o.AddRange(scripts[k].Bytes);
            return o.ToArray();
        }

        public static bool IsSoundParam(ACMDCommand c, int i)
        {
            if (ACMD_INFO.GetCategory(c.Ident) != "Sound") return false;
            string[] syn;
            try { syn = c.ParamSyntax; } catch (Exception) { return false; }
            return i < syn.Length && Params.Contains(syn[i].Trim());
        }

        static ACMDFile Read(byte[] data, string tmpDir)
        {
            string p = Path.Combine(tmpDir, Guid.NewGuid().ToString("N") + ".bin");
            File.WriteAllBytes(p, data);
            var map = FileMap.FromFile(p, FileMapProtect.Read);
            try { return new ACMDFile(new DataSource(map)); }
            finally
            {
                map.Dispose();
                try { File.Delete(p); } catch (Exception) { }
            }
        }

        static byte[] ScriptBytes(ACMDScript s, System.IO.Endianness e)
        {
            return s.Commands.Cast<ACMDCommand>().SelectMany(c => c.GetBytes(e)).ToArray();
        }

        public static Result Rewrite(byte[] data, IDictionary<uint, uint> remap, string tmpDir)
        {
            var r = new Result();
            bool big = data[4] == 0;
            Func<byte[], int, uint> W = (d, at) => big ? (uint)(d[at] << 24 | d[at + 1] << 16 | d[at + 2] << 8 | d[at + 3]) : (uint)(d[at] | d[at + 1] << 8 | d[at + 2] << 16 | d[at + 3] << 24);
            Action<byte[], int, uint> P = (d, at, v) =>
            {
                if (big) { d[at] = (byte)(v >> 24); d[at + 1] = (byte)(v >> 16); d[at + 2] = (byte)(v >> 8); d[at + 3] = (byte)v; }
                else { d[at] = (byte)v; d[at + 1] = (byte)(v >> 8); d[at + 2] = (byte)(v >> 16); d[at + 3] = (byte)(v >> 24); }
            };
            var f = Read(data, tmpDir);
            var outb = (byte[])data.Clone();
            var patched = new Dictionary<int, uint>();      // word offset -> new value
            var changedScripts = new HashSet<uint>();
            int n = (int)W(data, 8);
            for (int i = 0; i < n; i++)
            {
                uint crc = W(data, 0x10 + 8 * i);
                int pos = (int)W(data, 0x14 + 8 * i);
                if (!f.Scripts.ContainsKey(crc)) { r.Problems.Add(string.Format(CultureInfo.InvariantCulture, "script 0x{0:X8} not read", crc)); continue; }
                var sc = (ACMDScript)f.Scripts[crc];
                foreach (ACMDCommand c in sc.Commands)
                {
                    if (pos + c.Size > data.Length || W(data, pos) != c.Ident)
                    {
                        r.Problems.Add(string.Format(CultureInfo.InvariantCulture, "script 0x{0:X8}: its commands don't line up with the file at 0x{1:X}: not rewritten", crc, pos));
                        r.Data = null;
                        r.Count = 0;
                        return r;
                    }
                    var spec = c.ParamSpecifiers;
                    for (int p = 0; p < spec.Length && p < c.Parameters.Count; p++)
                    {
                        if (spec[p] != 0 || !IsSoundParam(c, p)) continue;
                        uint v = (uint)Convert.ToInt32(c.Parameters[p]), nv;
                        int at = pos + 4 + 4 * p;
                        if (W(data, at) != v || !remap.TryGetValue(v, out nv) || patched.ContainsKey(at)) continue;
                        P(outb, at, nv);
                        patched[at] = nv;
                        changedScripts.Add(crc);
                        r.Changes.Add(string.Format(CultureInfo.InvariantCulture, "script 0x{0:X8} +0x{1:X}: {2}({3}=0x{4:X}) -> 0x{5:X}", crc, pos - (int)W(data, 0x14 + 8 * i), c.Name, c.ParamSyntax[p].Trim(), v, nv));
                    }
                    pos += c.Size;
                }
            }
            r.Count = patched.Count;
            if (r.Count == 0) return r;
            // read again: the same scripts and commands; the parameters the same but the patched ones
            var g = Read(outb, tmpDir);
            bool same = g.Scripts.Count == f.Scripts.Count;
            foreach (var key in f.Scripts.Keys)
            {
                if (!same) break;
                if (!g.Scripts.ContainsKey(key)) { same = false; break; }
                var a = ((ACMDScript)f.Scripts[key]).Commands.Cast<ACMDCommand>().ToList();
                var b = ((ACMDScript)g.Scripts[key]).Commands.Cast<ACMDCommand>().ToList();
                if (a.Count != b.Count) { same = false; break; }
                for (int k = 0; k < a.Count && same; k++)
                {
                    if (a[k].Ident != b[k].Ident || a[k].Parameters.Count != b[k].Parameters.Count) { same = false; break; }
                    for (int p = 0; p < a[k].Parameters.Count; p++)
                    {
                        var pa = ACMDCommand.ParamWord(a[k].Parameters[p]);
                        var pb = ACMDCommand.ParamWord(b[k].Parameters[p]);
                        if (pa != pb && !(remap.ContainsKey(pa) && remap[pa] == pb)) { same = false; break; }
                    }
                }
            }
            if (!same) { r.Problems.Add("the rewritten file doesn't read back as the original but its sound ids: not rewritten"); r.Data = null; r.Count = 0; return r; }
            var endian = big ? System.IO.Endianness.Big : System.IO.Endianness.Little;
            foreach (var key in changedScripts)
            {
                var s = (ACMDScript)g.Scripts[key];
                try
                {
                    var s2 = new ACMDScript(key);
                    s2.Serialize(s.Deserialize());
                    if (!SameBytes(ScriptBytes(s2, endian), ScriptBytes(s, endian)))
                    {
                        r.RoundTrip = false;
                        r.Problems.Add(string.Format(CultureInfo.InvariantCulture, "script 0x{0:X8}: its text doesn't compile back to the same bytes (as upstream for some else-if chains); its ids were patched in place, the rest of it kept byte for byte", key));
                    }
                }
                catch (Exception ex) { r.RoundTrip = false; r.Problems.Add(string.Format(CultureInfo.InvariantCulture, "script 0x{0:X8}: its text doesn't compile ({1}); patched in place", key, ex.Message)); }
            }
            r.Data = outb;
            return r;
        }

        static bool SameBytes(byte[] a, byte[] b)
        {
            if (a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
            return true;
        }
    }

    /// <summary>A small .zip reader (v1.7.34, mods given as zips): stored and deflated entries (DeflateStream), no Zip64
    /// or encryption; names that would land outside the folder (absolute, "..") are refused.</summary>
    public static class MiniZip
    {
        static uint U32(byte[] b, long at) { return (uint)(b[at] | b[at + 1] << 8 | b[at + 2] << 16 | b[at + 3] << 24); }
        static int U16(byte[] b, long at) { return b[at] | b[at + 1] << 8; }

        public static List<string> Extract(string zip, string dir)
        {
            var names = new List<string>();
            var d = File.ReadAllBytes(zip);
            long eocd = -1;
            for (long i = d.Length - 22; i >= Math.Max(0, d.Length - 22 - 0x10000); i--)
                if (U32(d, i) == 0x06054B50) { eocd = i; break; }
            if (eocd < 0) throw new InvalidDataException(Path.GetFileName(zip) + ": not a zip (no end of central directory)");
            int count = U16(d, eocd + 10);
            long cd = U32(d, eocd + 16);
            if (cd == 0xFFFFFFFF || count == 0xFFFF) throw new InvalidDataException(Path.GetFileName(zip) + ": Zip64 isn't read: unzip it and give the folder");
            string full = Path.GetFullPath(dir).TrimEnd('\\', '/') + Path.DirectorySeparatorChar;
            for (int k = 0; k < count; k++)
            {
                if (cd + 46 > d.Length || U32(d, cd) != 0x02014B50) throw new InvalidDataException(Path.GetFileName(zip) + ": a bad central directory");
                int flags = U16(d, cd + 8), method = U16(d, cd + 10);
                uint csize = U32(d, cd + 20), usize = U32(d, cd + 24);
                int nl = U16(d, cd + 28), xl = U16(d, cd + 30), cl = U16(d, cd + 32);
                long local = U32(d, cd + 42);
                bool utf8 = (flags & 0x800) != 0;
                Encoding enc = Encoding.UTF8;
                if (!utf8) try { enc = Encoding.GetEncoding(437); } catch (Exception) { }
                string name = enc.GetString(d, (int)cd + 46, nl).Replace('\\', '/');
                cd += 46 + nl + xl + cl;
                if (name.EndsWith("/")) continue;
                if ((flags & 1) != 0) throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + " is encrypted");
                if (name.StartsWith("/") || name.Contains(":") || name.Split('/').Any(x => x == "..")) throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + " would be written outside the folder");
                string outPath = Path.GetFullPath(Path.Combine(dir, name.Replace('/', Path.DirectorySeparatorChar)));
                if (!outPath.StartsWith(full, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + " would be written outside the folder");
                if (U32(d, local) != 0x04034B50) throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + ": a bad local header");
                long at = local + 30 + U16(d, local + 26) + U16(d, local + 28);
                if (at + csize > d.Length) throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + " runs past the file");
                Directory.CreateDirectory(Path.GetDirectoryName(outPath));
                byte[] data;
                if (method == 0) { data = new byte[csize]; Array.Copy(d, at, data, 0, csize); }
                else if (method == 8)
                {
                    data = new byte[usize];
                    using (var z = new DeflateStream(new MemoryStream(d, (int)at, (int)csize), CompressionMode.Decompress))
                    {
                        int got = 0;
                        while (got < data.Length) { int r = z.Read(data, got, data.Length - got); if (r <= 0) break; got += r; }
                        if (got != data.Length) throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + " is short");
                    }
                }
                else throw new InvalidDataException(Path.GetFileName(zip) + ": " + name + ": compression method " + method + " isn't read (only stored / deflate): unzip it and give the folder");
                File.WriteAllBytes(outPath, data);
                names.Add(name);
            }
            return names;
        }
    }
}
