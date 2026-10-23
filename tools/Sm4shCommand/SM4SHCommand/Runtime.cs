using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Sm4shCommand.Classes;
using System.IO;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using System.ComponentModel;
using System.Windows.Forms;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace Sm4shCommand
{
    static unsafe class Runtime
    {
        public static AcmdMain Instance { get { return _instance; } }
        private static readonly AcmdMain _instance = new AcmdMain();

        // An explicit static constructor makes the main window get created on first use of Runtime
        // (in Program.Main, after the error handlers are set up), not whenever .NET decides to run the
        // field initializers early (before Main's first line, on .NET Framework).
        static Runtime() { }

        // ------------------------------------------------------------ script names
        //
        // Scripts are stored by the CRC32 of their (lower-case) animation name. AnimNames.txt, next
        // to the exe, lists names to recognise: one animation name per line (hashed at startup), or
        // "0xHASH = label" for a label of your own (for hashes whose real name isn't known).
        // Parse Animations and Set Name add to it, so names only have to be found once.
        // ModAnimNames.txt (same format, shipped with each version, never written to) names the
        // scripts the mods add (e.g. Kirby's Marth-copy sword slots); it's read first, so a label
        // of your own in AnimNames.txt for the same hash still wins.

        public static readonly Dictionary<uint, string> AnimNames = new Dictionary<uint, string>();

        /// <summary>The Hitbox Viewer's animation for a mod's script ("Name -> folder/File.omo [+ held@Bone]"
        /// lines in the name files): the motion folder's animation it plays, and a held model shown on
        /// a bone while it does (e.g. Kirby's Marth-copy sword on LHaveN).</summary>
        public class ViewerAnim
        {
            public string Folder, File, Held, Bone;
        }
        public static readonly Dictionary<uint, ViewerAnim> ViewerAnims = new Dictionary<uint, ViewerAnim>();
        public static string AnimNamesPath { get { return Path.Combine(Application.StartupPath, "AnimNames.txt"); } }
        public static string ModAnimNamesPath { get { return Path.Combine(Application.StartupPath, "ModAnimNames.txt"); } }

        public static void LoadAnimNames()
        {
            AnimNames.Clear();
            ViewerAnims.Clear();
            LoadAnimNameFile(ModAnimNamesPath);
            LoadAnimNameFile(AnimNamesPath);
        }

        static void LoadAnimNameFile(string path)
        {
            if (!File.Exists(path))
                return;
            foreach (var raw in File.ReadAllLines(path))
            {
                var line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("//") || line.StartsWith("#"))
                    continue;
                int arrow = line.IndexOf("->", StringComparison.Ordinal);
                if (arrow > 0)
                {
                    var name = line.Substring(0, arrow).Trim();
                    var rest = line.Substring(arrow + 2).Trim();
                    var held = "";
                    int plus = rest.IndexOf('+');
                    if (plus >= 0) { held = rest.Substring(plus + 1).Trim(); rest = rest.Substring(0, plus).Trim(); }
                    int slash = rest.LastIndexOf('/');
                    int at = held.IndexOf('@');
                    uint h = Crc32.Compute(name.ToLower());
                    if (!AnimNames.ContainsKey(h)) AnimNames[h] = name;
                    ViewerAnims[h] = new ViewerAnim
                    {
                        Folder = slash > 0 ? rest.Substring(0, slash) : "body", File = rest.Substring(slash + 1),
                        Held = at > 0 ? held.Substring(0, at) : null, Bone = at > 0 ? held.Substring(at + 1) : null,
                    };
                    continue;
                }
                int eq = line.IndexOf('=');
                if (eq > 0 && line.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                {
                    uint crc;
                    if (uint.TryParse(line.Substring(2, eq - 2).Trim(), System.Globalization.NumberStyles.HexNumber, null, out crc))
                        AnimNames[crc] = line.Substring(eq + 1).Trim();
                }
                else
                {
                    uint crc = Crc32.Compute(line.ToLower());
                    if (!AnimNames.ContainsKey(crc))
                        AnimNames[crc] = line;
                }
            }
        }

        // ---------------------------------------------------------------- settings
        //
        // Sm4shCommand.ini, next to the exe: "key = value" per line, written when a setting changes.

        static Dictionary<string, string> _settings;
        public static string SettingsPath { get { return Path.Combine(Application.StartupPath, "Sm4shCommand.ini"); } }

        static Dictionary<string, string> Settings
        {
            get
            {
                if (_settings != null)
                    return _settings;
                _settings = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                try
                {
                    if (File.Exists(SettingsPath))
                        foreach (var raw in File.ReadAllLines(SettingsPath))
                        {
                            int eq = raw.IndexOf('=');
                            if (eq > 0 && !raw.TrimStart().StartsWith("#"))
                                _settings[raw.Substring(0, eq).Trim()] = raw.Substring(eq + 1).Trim();
                        }
                }
                catch (Exception) { }
                return _settings;
            }
        }

        public static bool GetSetting(string key, bool fallback)
        {
            string v;
            return Settings.TryGetValue(key, out v) ? v == "1" || v.Equals("true", StringComparison.OrdinalIgnoreCase) : fallback;
        }

        public static string GetSettingText(string key, string fallback)
        {
            string v;
            return Settings.TryGetValue(key, out v) ? v : fallback;
        }

        public static void SetSettingText(string key, string value)
        {
            Settings[key] = value;
            try { File.WriteAllLines(SettingsPath, Settings.Select(x => $"{x.Key} = {x.Value}").ToArray()); }
            catch (Exception) { }
        }

        public static void SetSetting(string key, bool value)
        {
            Settings[key] = value ? "true" : "false";
            try { File.WriteAllLines(SettingsPath, Settings.Select(x => $"{x.Key} = {x.Value}").ToArray()); }
            catch (Exception) { } // read-only folder: the setting lasts until the app closes
        }

        /// <summary>
        /// The fighter's animation folder for an opened file or folder: the nearest "motion" folder
        /// next to it or next to one of its parents (data/fighter/NAME/motion for
        /// data/fighter/NAME/script/animcmd/body/game.bin). Null if there isn't one.
        /// </summary>
        public static string FindMotionFolder(string path)
        {
            try
            {
                var dir = Directory.Exists(path) ? new DirectoryInfo(path) : new FileInfo(path).Directory;
                for (int i = 0; dir != null && i < 6; i++, dir = dir.Parent)
                {
                    if (dir.Name.Equals("motion", StringComparison.OrdinalIgnoreCase))
                        return dir.FullName;
                    var m = Path.Combine(dir.FullName, "motion");
                    if (Directory.Exists(m))
                        return m;
                }
            }
            catch (Exception) { }
            return null;
        }

        /// <summary>
        /// Adds names to AnimNames.txt (and the loaded list). A name whose CRC32 isn't
        /// <paramref name="crc"/> is stored as a label: "0xHASH = name".
        /// </summary>
        public static void SaveAnimName(uint crc, string name)
        {
            name = name.Trim();
            if (name.Length == 0)
                return;
            bool real = Crc32.Compute(name.ToLower()) == crc;
            AnimNames[crc] = name;
            File.AppendAllText(AnimNamesPath, (real ? name : $"0x{crc:X8} = {name}") + Environment.NewLine);
        }

        public static void SaveAnimNames(Dictionary<uint, string> names)
        {
            var lines = new List<string>();
            foreach (var pair in names)
            {
                string known;
                if (AnimNames.TryGetValue(pair.Key, out known) && known == pair.Value)
                    continue;
                AnimNames[pair.Key] = pair.Value;
                lines.Add(pair.Value);
            }
            if (lines.Count > 0)
                File.AppendAllLines(AnimNamesPath, lines);
        }

        /// <summary>
        /// The animation name of a script hash if it's known, else the hash as 8 hex digits.
        /// </summary>
        public static string ScriptLabel(uint crc)
        {
            if (crc == 0)
                return "(empty)"; // unused motion.mtable slot
            string name;
            return AnimNames.TryGetValue(crc, out name) ? name : crc.ToString("X8");
        }

        /// <summary>
        /// Reads Events.cfg (command definitions) on top of SALT's built-in ones. Logs problems.
        /// </summary>
        public static void LoadCommandDefinitions()
        {
            var path = Path.Combine(Application.StartupPath, "Events.cfg");
            if (!File.Exists(path))
                return;
            var errors = new List<string>();
            int count = ACMD_INFO.OverrideInfo(path, errors);
            LogMessage($"Events.cfg: {count} command definitions loaded.");
            foreach (var e in errors)
                LogMessage("  " + e);
        }

        public static void GetCommandInfo(string path)
        {
            using (StreamReader stream = new StreamReader(path))
            {
                List<string> raw = stream.ReadToEnd().Split('\n').Select(x => x.Trim('\r')).ToList();
                raw.RemoveAll(x => String.IsNullOrEmpty(x) || String.IsNullOrWhiteSpace(x) || x.Contains("//"));

                for (int i = 0; i < raw.Count; i += 5)
                {
                    var crc = uint.Parse(raw[i], System.Globalization.NumberStyles.HexNumber);
                    var Name = raw[i + 1];

                    string[] paramList = raw[i + 2].Split(',').Where(x => x != "NONE").ToArray();
                    string[] paramSyntax = raw[i + 3].Split(',').Where(x => x != "NONE").ToArray();
                    LogMessage($"{Name}");
                    ACMD_INFO.SetCMDInfo(crc, paramList.Length + 1, Name, paramList.Select(x => int.Parse(x)).ToArray(), paramSyntax);

                }
            }
        }
        public static Dictionary<uint, string> ParseAnimations(string motionFolder)
        {
            var dict = new Dictionary<uint, string>();
            var files = Directory.EnumerateFiles(motionFolder, "*.*", SearchOption.AllDirectories).
                Where(x => x.EndsWith(".pac", StringComparison.InvariantCultureIgnoreCase) ||
                x.EndsWith(".bch", StringComparison.InvariantCultureIgnoreCase)).Select(x => x);
            foreach (var path in files)
                ParseAnim(path, ref dict);
            return dict;
        }
        public static void ParseAnim(string path, ref Dictionary<uint, string> dict)
        {
            if (path.EndsWith(".pac"))
            {
                byte[] filebytes = File.ReadAllBytes(path);
                int count = (int)Util.GetWord(filebytes, 8, Endianness.Big);

                for (int i = 0; i < count; i++)
                {
                    uint off = (uint)Util.GetWord(filebytes, 0x10 + (i * 4), Endianness.Big);
                    string FileName = Util.GetString(filebytes, off, Endianness.Big);
                    string AnimName = Regex.Match(FileName, @"(.*)([A-Z])([0-9][0-9])(.*)\.omo").Groups[4].ToString();
                    if (string.IsNullOrEmpty(AnimName))
                        continue;

                    AddAnimHash(AnimName, ref dict);
                    AddAnimHash(AnimName + "_C2", ref dict);
                    AddAnimHash(AnimName + "_C3", ref dict);
                    AddAnimHash(AnimName + "L", ref dict);
                    AddAnimHash(AnimName + "R", ref dict);


                    if (AnimName.EndsWith("s4s", StringComparison.InvariantCultureIgnoreCase) ||
                       AnimName.EndsWith("s3s", StringComparison.InvariantCultureIgnoreCase))
                        AddAnimHash(AnimName.Substring(0, AnimName.Length - 1), ref dict);
                }
            }
            else if (path.EndsWith(".bch"))
            {
                using (var stream = File.Open(path, FileMode.Open, FileAccess.Read))
                using (var reader = new BinaryReader(stream))
                {
                    stream.Seek(0xC, SeekOrigin.Begin);
                    int off = reader.ReadInt32();
                    stream.Seek(off, SeekOrigin.Begin);

                    while (reader.PeekChar() != '\0')
                    {
                        var tmp = reader.ReadStringNT();
                        string AnimName = Regex.Match(tmp, @"(.*)([A-Z])([0-9][0-9])(.*)").Groups[4].ToString();
                        if (string.IsNullOrEmpty(AnimName))
                        {
                            continue;
                        }

                        AddAnimHash(AnimName, ref dict);
                        AddAnimHash(AnimName + "_C2", ref dict);
                        AddAnimHash(AnimName + "_C3", ref dict);
                        AddAnimHash(AnimName + "L", ref dict);
                        AddAnimHash(AnimName + "R", ref dict);


                        if (AnimName.EndsWith("s4s", StringComparison.InvariantCultureIgnoreCase) ||
                           AnimName.EndsWith("s3s", StringComparison.InvariantCultureIgnoreCase))
                            AddAnimHash(AnimName.Substring(0, AnimName.Length - 1), ref dict);
                    }
                }
            }
        }
        public static void AddAnimHash(string name, ref Dictionary<uint, string> dict)
        {
            uint crc = Crc32.Compute(name.ToLower());
            if (dict.ContainsValue(name) || dict.ContainsKey(crc))
                return;

            dict.Add(crc, name);
        }
        public static Endianness WorkingEndian { get { return _workingEndian; } set { _workingEndian = value; } }
        private static Endianness _workingEndian;

        public static void LogMessage(string message)
        {
            Instance.Invoke(
                new MethodInvoker(
                    delegate { Instance.richTextBox1.AppendText($">   {message}\n"); }));
        }
    }
}
