using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace Sm4shCommand.Sound
{
    /// <summary>One sound of the list: a label of a soundlabeltable row (Id) and the tone it reaches, or a tone no label
    /// reaches (Id null: no ACMD id plays it).</summary>
    public class SoundEntry
    {
        public uint? Id;
        public int Row = -1, Label = -1;
        public Tone Tone;               // null when the label points past the bank's tones
        public Nus3Bank Bank;
        public string Kind = "";        // se, se c01, vc, cheer, se_common, Kirby copy, common ...
        public string AliasSet;         // the alias file (fighter folder name or "common")
        public string Note = "";

        public string IdText { get { return Id.HasValue ? string.Format(CultureInfo.InvariantCulture, "0x{0:X8}", Id.Value) : "-"; } }
        public string Name { get { return Tone != null ? (Tone.Name.Length > 0 ? Tone.Name : "(" + Tone.Kind.ToString().ToLowerInvariant() + " slot)") : "(no tone " + Note + ")"; } }
        public string Alias
        {
            get { return Id.HasValue ? SoundAliases.Get(AliasSet, Id.Value) : ""; }
            set { if (Id.HasValue) SoundAliases.Set(AliasSet, Id.Value, value); }
        }
        public bool Playable { get { return Tone != null && Tone.HasAudio && Tone.Codec == "IDSP"; } }
    }

    /// <summary>A list of sounds from some banks through the label table (a fighter's banks, or a common bank).</summary>
    public class SoundSet
    {
        public readonly List<Nus3Bank> Banks = new List<Nus3Bank>();
        public readonly List<SoundEntry> Entries = new List<SoundEntry>();
        public readonly List<string> Notes = new List<string>();
        public readonly Dictionary<Nus3Bank, string> Kinds = new Dictionary<Nus3Bank, string>();
        public readonly Dictionary<Nus3Bank, int> RowOfBank = new Dictionary<Nus3Bank, int>();

        static readonly Regex BankRe = new Regex(@"^snd_(se|vc)_([A-Za-z0-9]+?)(_common)?(_ouen)?(?:_c(\d\d))?\.nus3bank$", RegexOptions.IgnoreCase);

        /// <summary>A fighter bank's kind from its file name (snd_se_Gekkouga_c01 -> "se c01"), with a sort key.</summary>
        public static string KindOf(string file, out int order)
        {
            file = Path.GetFileName(file);
            if (file.StartsWith("snd_se_vc_Kirby_copy_", StringComparison.OrdinalIgnoreCase)) { order = 600; return "Kirby copy"; }
            var m = BankRe.Match(file);
            if (!m.Success) { order = 900; return Path.GetFileNameWithoutExtension(file); }
            int nn = m.Groups[5].Success ? int.Parse(m.Groups[5].Value, CultureInfo.InvariantCulture) : 0;
            string k;
            if (m.Groups[1].Value.Equals("se", StringComparison.OrdinalIgnoreCase))
            {
                k = m.Groups[3].Success ? "se_common" : "se";
                order = (m.Groups[3].Success ? 200 : 0) + nn;
            }
            else
            {
                k = m.Groups[4].Success ? "cheer" : "vc";
                order = (m.Groups[4].Success ? 500 : 300) + nn;
            }
            return nn > 0 ? k + " c" + nn.ToString("00", CultureInfo.InvariantCulture) : k;
        }

        /// <summary>
        /// The entries of these banks. A bank's row is its BINF id's; a port's own id (46000+, tools/sound_bank_ids.py)
        /// has no row, the game plays it through its alias (the old id's row: Viewer/SoundBanks.txt, from
        /// reference/port_sound_ids.json); a costume bank (_cNN) with no row of its own uses its main bank's, as the game's
        /// costume banks share the main bank's ids.
        /// </summary>
        public static SoundSet Build(IList<Nus3Bank> banks, SoundLabelTable table, string aliasSet, IDictionary<uint, uint> bankAliases,
                                     Func<Nus3Bank, string> kindOf)
        {
            var set = new SoundSet();
            foreach (var b in banks) { set.Banks.Add(b); set.Kinds[b] = kindOf(b); }
            foreach (var b in banks)
            {
                string kind = set.Kinds[b];
                int row = table != null ? table.RowOf(b.Id) : -1;
                string how = row >= 0 ? string.Format(CultureInfo.InvariantCulture, "row 0x{0:X} (its BINF id {1})", row, b.Id) : null;
                uint alias;
                if (row < 0 && table != null && bankAliases != null && bankAliases.TryGetValue(b.Id, out alias) && table.RowOf(alias) >= 0)
                {
                    row = table.RowOf(alias);
                    how = string.Format(CultureInfo.InvariantCulture, "row 0x{0:X}: its BINF id {1} is a port's own id, played through its alias {2}'s row (Viewer\\SoundBanks.txt)", row, b.Id, alias);
                }
                if (row < 0 && table != null && kind.Contains(" c"))
                {
                    string mainKind = kind.Substring(0, kind.IndexOf(" c", StringComparison.Ordinal));
                    var main = banks.FirstOrDefault(x => set.Kinds[x] == mainKind);
                    int mr;
                    if (main != null && set.RowOfBank.TryGetValue(main, out mr) && mr >= 0)
                    {
                        row = mr;
                        how = string.Format(CultureInfo.InvariantCulture, "row 0x{0:X}: the main {1} bank's (its BINF id {2} has no row; a costume bank shares the main bank's ids)", row, mainKind, b.Id);
                    }
                }
                set.RowOfBank[b] = row;
                set.Notes.Add(Path.GetFileName(b.Path) + " (BINF " + b.Name + ", id " + b.Id + ", " + b.Tones.Count + " tones): " +
                              (how ?? (table == null ? "no soundlabeltable.bin: no ids" : "no row in soundlabeltable.bin: the game can't play it")));
                var reached = new bool[b.Tones.Count];
                if (row >= 0)
                {
                    var labels = table.Labels(row);
                    for (int i = 0; i < labels.Length; i++)
                    {
                        int t = labels[i];
                        if (t < 0) continue;
                        var e = new SoundEntry { Id = SoundLabelTable.SoundId(row, i), Row = row, Label = i, Bank = b, Kind = kind, AliasSet = aliasSet };
                        if (t < b.Tones.Count) { e.Tone = b.Tones[t]; reached[t] = true; }
                        else e.Note = string.Format(CultureInfo.InvariantCulture, "{0}: past the bank's {1}", t, b.Tones.Count);
                        set.Entries.Add(e);
                    }
                }
                for (int t = 0; t < b.Tones.Count; t++)
                    if (!reached[t] && b.Tones[t].Kind != ToneKind.Empty)
                        set.Entries.Add(new SoundEntry { Tone = b.Tones[t], Bank = b, Kind = kind, AliasSet = aliasSet, Note = "no label: no id plays it" });
            }
            return set;
        }
    }

    /// <summary>
    /// A fighter's sounds (v1.7.32): its fighter/NAME/sound/*.nus3bank (se, the costume banks, vc, cheer, Kirby copy),
    /// sound/config/soundlabeltable.bin and the common bank sound/se/snd_se_joucyu.nus3bank (row 0), found as the game
    /// lays them out: data/sound next to data/fighter, in a folder above the fighter's (a dump's data, a mod's
    /// INSTALL_TO_data), else in the game data folder picked in the viewer (a mod folder without sound/config or the
    /// common bank). The mod's own label table wins over the picked one.
    /// </summary>
    public class FighterSounds
    {
        public string Root, Name, SoundFolder, TablePath, CommonBankPath, CommonFolder;
        public SoundLabelTable Table;
        public SoundSet Fighter, Common;
        public Nus3Bank CommonBank;
        public readonly List<string> Notes = new List<string>();
        public const string CommonBankFile = "snd_se_joucyu.nus3bank";

        /// <summary>fighter/NAME for a path inside it (a script, the animcmd folder ...), else null.</summary>
        public static string FindFighterRoot(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            string dir;
            try { dir = File.Exists(path) ? Path.GetDirectoryName(path) : path; }
            catch (Exception) { return null; }
            for (int i = 0; i < 8 && !string.IsNullOrEmpty(dir); i++)
            {
                var parent = Path.GetDirectoryName(dir);
                if (parent != null && Path.GetFileName(parent).Equals("fighter", StringComparison.OrdinalIgnoreCase)) return dir;
                try
                {
                    var snd = Path.Combine(dir, "sound");
                    if (Directory.Exists(snd) && Directory.GetFiles(snd, "*.nus3bank").Length > 0) return dir;
                }
                catch (Exception) { }
                dir = parent;
            }
            return null;
        }

        /// <summary>A file of the game's data (rel = sound/config/soundlabeltable.bin ...) in a folder above start, or in
        /// the picked folder (it, its data, or the folders above it if the sound or config folder was picked).</summary>
        public static string FindData(string start, string rel, string picked, out bool fromPicked)
        {
            fromPicked = false;
            string d = start;
            for (int up = 0; up < 10 && !string.IsNullOrEmpty(d); up++)
            {
                foreach (var c in new[] { Path.Combine(d, rel), Path.Combine(Path.Combine(d, "data"), rel) })
                    try { if (File.Exists(c)) return c; } catch (Exception) { }
                d = Path.GetDirectoryName(d);
            }
            if (!string.IsNullOrEmpty(picked))
            {
                d = picked;
                for (int up = 0; up < 3 && !string.IsNullOrEmpty(d); up++)
                {
                    foreach (var c in new[] { Path.Combine(d, rel), Path.Combine(Path.Combine(d, "data"), rel), Path.Combine(d, Path.GetFileName(rel)) })
                        try { if (File.Exists(c)) { fromPicked = true; return c; } } catch (Exception) { }
                    d = Path.GetDirectoryName(d);
                }
            }
            return null;
        }

        static string Rel(params string[] p) { return string.Join(Path.DirectorySeparatorChar.ToString(), p); }

        /// <summary>Port banks' own ids -> the ids their rows use (Viewer/SoundBanks.txt: "46192 = 2028").</summary>
        public static Dictionary<uint, uint> LoadBankAliases(string path)
        {
            var d = new Dictionary<uint, uint>();
            try
            {
                if (path != null && File.Exists(path))
                    foreach (var raw in File.ReadAllLines(path))
                    {
                        var line = raw;
                        int c = line.IndexOf('#');
                        if (c >= 0) line = line.Substring(0, c);
                        int eq = line.IndexOf('=');
                        uint a, b;
                        if (eq > 0 && SoundAliases.TryParseId(line.Substring(0, eq), out a) && SoundAliases.TryParseId(line.Substring(eq + 1), out b))
                            d[a] = b;
                    }
            }
            catch (Exception) { }
            return d;
        }

        public static string BankAliasesPath
        {
            get { try { return Path.Combine(Path.Combine(System.Windows.Forms.Application.StartupPath, "Viewer"), "SoundBanks.txt"); } catch (Exception) { return null; } }
        }

        /// <summary>Loads a fighter folder's sounds. picked: the game data folder chosen in the viewer (or null).</summary>
        public static FighterSounds Load(string root, string picked, IDictionary<uint, uint> bankAliases = null)
        {
            var fs = new FighterSounds { Root = root, Name = Path.GetFileName(root).ToLowerInvariant() };
            fs.SoundFolder = Path.Combine(root, "sound");
            bool fromPicked;
            fs.TablePath = FindData(root, Rel("sound", "config", "soundlabeltable.bin"), picked, out fromPicked);
            if (fs.TablePath != null)
            {
                try
                {
                    fs.Table = SoundLabelTable.Load(fs.TablePath);
                    fs.Notes.Add("soundlabeltable.bin: " + fs.TablePath + (fromPicked ? " (the picked game data folder)" : "") +
                                 " (" + fs.Table.Rows.Count + " rows)");
                }
                catch (Exception ex) { fs.Notes.Add("soundlabeltable.bin: " + fs.TablePath + ": " + ex.Message); }
            }
            else
                fs.Notes.Add("No sound/config/soundlabeltable.bin above the fighter's folder or in the picked game data folder: no sound ids (pick the game's data folder with Game data..).");
            if (bankAliases == null) bankAliases = LoadBankAliases(BankAliasesPath);
            var banks = new List<Nus3Bank>();
            if (Directory.Exists(fs.SoundFolder))
            {
                foreach (var f in Directory.GetFiles(fs.SoundFolder, "*.nus3bank"))
                {
                    try { banks.Add(Nus3Bank.Load(f)); }
                    catch (Exception ex) { fs.Notes.Add(Path.GetFileName(f) + ": " + ex.Message); }
                }
            }
            else
                fs.Notes.Add("No sound folder: " + fs.SoundFolder);
            banks = banks.OrderBy(b => { int o; SoundSet.KindOf(b.Path, out o); return o; }).ThenBy(b => Path.GetFileName(b.Path), StringComparer.OrdinalIgnoreCase).ToList();
            fs.Fighter = SoundSet.Build(banks, fs.Table, fs.Name, bankAliases, b => { int o; return SoundSet.KindOf(b.Path, out o); });
            fs.CommonBankPath = FindData(root, Rel("sound", "se", CommonBankFile), picked, out fromPicked);
            if (fs.CommonBankPath != null)
            {
                fs.CommonFolder = Path.GetDirectoryName(fs.CommonBankPath);
                fs.LoadCommon(fs.CommonBankPath);
            }
            else
                fs.Notes.Add("No sound/se/" + CommonBankFile + " (the common sounds) above the fighter's folder or in the picked game data folder.");
            return fs;
        }

        /// <summary>The common tab's bank: snd_se_joucyu (row 0, the one fighters' scripts play) or another sound/se bank.</summary>
        public void LoadCommon(string bankPath)
        {
            try
            {
                CommonBank = Nus3Bank.Load(bankPath);
                Common = SoundSet.Build(new[] { CommonBank }, Table, SoundAliases.CommonSet, null,
                                        b => Path.GetFileName(b.Path).Equals(CommonBankFile, StringComparison.OrdinalIgnoreCase) ? "common" : Path.GetFileNameWithoutExtension(b.Path));
            }
            catch (Exception ex)
            {
                Common = new SoundSet();
                Common.Notes.Add(Path.GetFileName(bankPath) + ": " + ex.Message);
            }
        }

        /// <summary>The other banks of the common bank's folder (sound/se: items, stages' common, menus ...), for the
        /// common tab's bank list.</summary>
        public List<string> OtherCommonBanks()
        {
            try
            {
                return CommonFolder == null ? new List<string>() : Directory.GetFiles(CommonFolder, "*.nus3bank")
                    .OrderBy(f => Path.GetFileName(f).Equals(CommonBankFile, StringComparison.OrdinalIgnoreCase) ? 0 : 1)
                    .ThenBy(f => f, StringComparer.OrdinalIgnoreCase).ToList();
            }
            catch (Exception) { return new List<string>(); }
        }

        /// <summary>Every entry of the fighter's and the common banks with this id.</summary>
        public IEnumerable<SoundEntry> ById(uint id)
        {
            foreach (var s in new[] { Fighter, Common })
                if (s != null)
                    foreach (var e in s.Entries)
                        if (e.Id == id) yield return e;
        }
    }

    /// <summary>
    /// The script editor's tooltip on a sound id (v1.7.32): the tone it plays (name, bank, length, volume) and your
    /// alias, from the open fighter's banks (loaded the first time a sound id is hovered, or the viewer's).
    /// </summary>
    public static class SoundTips
    {
        static readonly HashSet<string> Params = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            { "SFX", "Se", "Se1", "Se2", "SoundID", "SoundIDFlip", "Sequence", "Voice1", "Voice2" };

        /// <summary>The path opened in the main window (the fighter whose banks the tooltips use).</summary>
        public static string OpenedPath;
        /// <summary>The game data folder picked in the viewer (Settings: SoundDataFolder).</summary>
        public static string PickedData;
        static FighterSounds current;
        static string triedRoot;

        public static FighterSounds Current
        {
            get { return current; }
            set { current = value; triedRoot = value != null ? value.Root : null; }
        }

        public static bool IsSoundParam(string command, string param)
        {
            if (param != null && Params.Contains(param)) return true;
            return command != null && param == null && (command.IndexOf("Sound", StringComparison.OrdinalIgnoreCase) >= 0);
        }

        static FighterSounds Ensure()
        {
            string root = FighterSounds.FindFighterRoot(OpenedPath);
            if (root == null) return current;
            if (current != null && string.Equals(current.Root, root, StringComparison.OrdinalIgnoreCase)) return current;
            if (string.Equals(triedRoot, root, StringComparison.OrdinalIgnoreCase)) return current;
            triedRoot = root;
            try { current = FighterSounds.Load(root, PickedData); } catch (Exception) { }
            return current;
        }

        /// <summary>The tooltip's lines for a sound id ("" when nothing is known).</summary>
        public static string Describe(uint id)
        {
            var sb = new StringBuilder();
            if ((id & 0x80000000) != 0)
            {
                sb.AppendFormat(CultureInfo.InvariantCulture, "Voice sequence: set 0x{0:X}, sequence {1} (the fighter's soundseq_<Name>.sqb: one of several voice clips at random; " +
                                "Low_Voice_Clip / PLAY_FLY_VOICE play these). Not a tone: the Sound Effect Viewer lists tones.", (id >> 16) & 0x7FFF, id & 0xFFFF);
                return sb.ToString();
            }
            var fs = Ensure();
            string set;
            string alias = SoundAliases.Find(id, fs != null ? fs.Name : null, out set);
            var found = fs != null ? fs.ById(id).ToList() : new List<SoundEntry>();
            if (found.Count > 0)
            {
                var e = found.First(x => x.Tone != null && x.Tone.HasAudio || x == found.Last());
                sb.AppendFormat(CultureInfo.InvariantCulture, "Sound 0x{0:X8}: {1}", id, e.Name);
                var kinds = found.Select(x => x.Kind).Distinct().ToList();
                sb.AppendFormat(CultureInfo.InvariantCulture, "\n{0} ({1}), row 0x{2:X}, label {3}", kinds.Count > 3 ? string.Join(", ", kinds.Take(3)) + " ..." : string.Join(", ", kinds),
                                Path.GetFileName(e.Bank.Path), e.Row, e.Label);
                if (e.Tone != null)
                {
                    sb.AppendFormat(CultureInfo.InvariantCulture, ", tone {0}", e.Tone.Index);
                    if (e.Tone.HasAudio)
                        sb.AppendFormat(CultureInfo.InvariantCulture, "\n{0:0.00} s, {1}, {2} Hz{3}, volume {4:+0.0;-0.0;0.0} dB", e.Tone.Seconds,
                                        e.Tone.Channels == 1 ? "mono" : e.Tone.Channels + " channels", e.Tone.SampleRate, e.Tone.Loops ? ", loops" : "", e.Tone.VolumeDb);
                }
            }
            else if (fs != null && fs.Table != null)
            {
                uint bank;
                int tone = fs.Table.ToneOf(id, out bank);
                int row = SoundLabelTable.RowOfId(id);
                if (row < fs.Table.Rows.Count && bank != SoundLabelTable.EmptyBank)
                    sb.AppendFormat(CultureInfo.InvariantCulture, "Sound 0x{0:X8}: row 0x{1:X} (bank id {2}), label {3}{4}", id, row, bank, SoundLabelTable.LabelOfId(id),
                                    tone >= 0 ? ", tone " + tone + " (a bank the open fighter doesn't have)" : ": no tone (silent in game)");
                else if (row < fs.Table.Rows.Count)
                    sb.AppendFormat(CultureInfo.InvariantCulture, "Sound 0x{0:X8}: row 0x{1:X} is empty (silent in game)", id, row);
            }
            if (alias.Length > 0)
                sb.Append(sb.Length > 0 ? "\n" : "").Append("Alias: ").Append(alias).Append(set != null && fs != null && set != fs.Name && set != SoundAliases.CommonSet ? " (" + set + "'s)" : "");
            return sb.ToString();
        }
    }
}
