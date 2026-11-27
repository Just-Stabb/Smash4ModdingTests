using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>
    /// Your names for sounds (v1.7.32, the Sound Effect Viewer's Alias column): Aliases/sounds/FIGHTER.txt next to the
    /// exe (FIGHTER = the fighter's folder name, e.g. gekkouga), Aliases/sounds/common.txt for the common bank's sounds
    /// (row 0: every fighter's). One per line, "0x07680061 = Creeper boom"; lines starting with # are comments. The
    /// viewer writes them as you type; they show in the script editor's tooltip on a sound id. They are labels only (a
    /// script keeps the number). Variable aliases (Aliases/*.txt) don't read this folder.
    /// </summary>
    public static class SoundAliases
    {
        public const string CommonSet = "common";
        static string folder;
        public static string Folder
        {
            get { return folder ?? Path.Combine(Sm4shCommand.Classes.VariableAliases.Folder, "sounds"); }
            set { folder = value; cache.Clear(); }     // (the tests)
        }

        static readonly Dictionary<string, Dictionary<uint, string>> cache = new Dictionary<string, Dictionary<uint, string>>(StringComparer.OrdinalIgnoreCase);

        /// <summary>The file a set's aliases are in (set: a fighter folder name or "common").</summary>
        public static string FileFor(string set)
        {
            var sb = new StringBuilder();
            foreach (char c in (set ?? "").ToLowerInvariant())
                if (char.IsLetterOrDigit(c) || c == '_' || c == '-') sb.Append(c);
            return Path.Combine(Folder, (sb.Length > 0 ? sb.ToString() : "unknown") + ".txt");
        }

        public static Dictionary<uint, string> Of(string set)
        {
            Dictionary<uint, string> d;
            if (cache.TryGetValue(set ?? "", out d)) return d;
            d = new Dictionary<uint, string>();
            string path = FileFor(set);
            try
            {
                if (File.Exists(path))
                    foreach (var raw in File.ReadAllLines(path))
                    {
                        var line = raw.Trim();
                        if (line.Length == 0 || line.StartsWith("#") || line.StartsWith("//")) continue;
                        int eq = line.IndexOf('=');
                        uint id;
                        if (eq > 0 && TryParseId(line.Substring(0, eq).Trim(), out id))
                        {
                            var name = line.Substring(eq + 1).Trim();
                            if (name.Length > 0) d[id] = name;
                        }
                    }
            }
            catch (Exception) { }   // unreadable: no aliases
            cache[set ?? ""] = d;
            return d;
        }

        public static bool TryParseId(string s, out uint id)
        {
            s = s.Trim();
            if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                return uint.TryParse(s.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out id);
            return uint.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out id);
        }

        public static string Get(string set, uint id)
        {
            string a;
            return Of(set).TryGetValue(id, out a) ? a : "";
        }

        /// <summary>The alias of an id anywhere: the given set first, then common, then any other file (an id is the
        /// same sound in every fighter's scripts: Kirby's copies play their fighter's rows); set = where it was found.</summary>
        public static string Find(uint id, string prefer, out string set)
        {
            foreach (var s in new[] { prefer, CommonSet })
            {
                if (string.IsNullOrEmpty(s)) continue;
                var a = Get(s, id);
                if (a.Length > 0) { set = s; return a; }
            }
            try
            {
                if (Directory.Exists(Folder))
                    foreach (var f in Directory.GetFiles(Folder, "*.txt").OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
                    {
                        var s = Path.GetFileNameWithoutExtension(f);
                        var a = Get(s, id);
                        if (a.Length > 0) { set = s; return a; }
                    }
            }
            catch (Exception) { }
            set = null;
            return "";
        }

        /// <summary>Sets (or, empty, removes) an alias and writes the set's file.</summary>
        public static void Set(string set, uint id, string alias)
        {
            alias = (alias ?? "").Replace("\r", " ").Replace("\n", " ").Trim();
            var d = Of(set);
            if (alias.Length == 0) d.Remove(id); else d[id] = alias;
            Directory.CreateDirectory(Folder);
            var lines = new List<string>
            {
                "# Sound aliases for " + set + ": Sm4shCommand's Sound Effect Viewer (Tools > Sound Effect Viewer) writes this file",
                "# from its Alias column; you can edit it too. One per line: sound id = your name for it. Labels only: scripts keep",
                "# the number, the editor's tooltip on the id shows the name.",
            };
            foreach (var kv in d.OrderBy(x => x.Key))
                lines.Add(string.Format(CultureInfo.InvariantCulture, "0x{0:X8} = {1}", kv.Key, kv.Value));
            File.WriteAllLines(FileFor(set), lines.ToArray());
        }

        public static void Reload() { cache.Clear(); }
    }
}
