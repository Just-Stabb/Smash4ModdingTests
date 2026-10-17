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

        // ------------------------------------------------------------ script names
        //
        // Scripts are stored by the CRC32 of their (lower-case) animation name. AnimNames.txt, next
        // to the exe, lists names to recognise: one animation name per line (hashed at startup), or
        // "0xHASH = label" for a label of your own (for hashes whose real name isn't known).
        // Parse Animations and Set Name add to it, so names only have to be found once.

        public static readonly Dictionary<uint, string> AnimNames = new Dictionary<uint, string>();
        public static string AnimNamesPath { get { return Path.Combine(Application.StartupPath, "AnimNames.txt"); } }

        public static void LoadAnimNames()
        {
            AnimNames.Clear();
            if (!File.Exists(AnimNamesPath))
                return;
            foreach (var raw in File.ReadAllLines(AnimNamesPath))
            {
                var line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("//") || line.StartsWith("#"))
                    continue;
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
