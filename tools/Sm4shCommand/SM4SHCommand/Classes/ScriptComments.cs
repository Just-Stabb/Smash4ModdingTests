using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;

namespace Sm4shCommand.Classes
{
    /// <summary>
    /// Comments in ACMD scripts. The game's .bin files have no room for them, so a script's text is
    /// kept, comments and all, in "FILE.comments" next to the .bin (e.g. game.bin.comments), written
    /// on save for every script that has a comment:
    ///
    ///     ==== 0x8376AD51 ====
    ///     FRAME(Frames=10)
    ///     // sweetspot
    ///     Hitbox(...)   // strong hit
    ///
    /// When a script is opened its saved text is shown if it still compiles to the same commands;
    /// if the .bin was changed elsewhere, the comments are put back on the lines that still match.
    /// </summary>
    public static class ScriptComments
    {
        const string Header = "// Comments for the ACMD scripts in the .bin file of the same name (Sm4shCommand).";

        // Commented text per script (not per hash: a fighter's game/effect/sound/expression scripts
        // share hashes).
        static readonly ConditionalWeakTable<IScript, StrongBox<string>> Texts = new ConditionalWeakTable<IScript, StrongBox<string>>();

        public static string PathFor(string binPath) { return binPath + ".comments"; }

        public static bool HasComments(string text)
        {
            return text != null && (text.Contains("//") || text.Contains("/*"));
        }

        /// <summary>Remembers an editor's text for its script (only kept if it has comments).</summary>
        public static void Remember(IScript script, string text)
        {
            if (!(script is ACMDScript))
                return;
            Texts.Remove(script);
            if (HasComments(text))
                Texts.Add(script, new StrongBox<string>(text.Replace("\r\n", "\n")));
        }

        /// <summary>The text to show for a script: the saved commented text when there is one.</summary>
        public static string TextFor(IScript script)
        {
            string plain = script.Deserialize();
            StrongBox<string> saved;
            if (!(script is ACMDScript) || !Texts.TryGetValue(script, out saved))
                return plain;
            try
            {
                if (SameCommands((ACMDScript)script, saved.Value))
                    return saved.Value.Replace("\n", Environment.NewLine);
            }
            catch (Exception) { } // the saved text no longer compiles (definitions changed): merge
            return Merge(saved.Value, plain);
        }

        static bool SameCommands(ACMDScript script, string text)
        {
            var copy = new ACMDScript(script.AnimationCRC);
            copy.Serialize(text);
            return copy.GetBytes(System.IO.Endianness.Big).SequenceEqual(script.GetBytes(System.IO.Endianness.Big));
        }

        // ---------------------------------------------------------------- files

        public static void Load(string binPath, IScriptCollection file)
        {
            string path = PathFor(binPath);
            if (file == null || !File.Exists(path))
                return;
            uint crc = 0;
            bool have = false;
            var sb = new StringBuilder();
            Action flush = () =>
            {
                IScript s;
                if (have && file.Scripts.TryGetValue(crc, out s))
                    Remember(s, sb.ToString().TrimEnd('\n'));
                sb.Clear();
            };
            foreach (var raw in File.ReadAllLines(path))
            {
                var line = raw.TrimEnd('\r');
                var t = line.Trim();
                if (t.StartsWith("==== 0x") && t.EndsWith("===="))
                {
                    flush();
                    have = uint.TryParse(t.Substring(7, t.Length - 11).Trim(), System.Globalization.NumberStyles.HexNumber, null, out crc);
                }
                else if (have)
                    sb.Append(line).Append('\n');
            }
            flush();
        }

        /// <summary>Writes FILE.comments for the scripts with comments (deletes it when none have).</summary>
        public static void Save(string binPath, IScriptCollection file)
        {
            if (file == null)
                return;
            var sb = new StringBuilder();
            foreach (var pair in file.Scripts)
            {
                StrongBox<string> text;
                if (Texts.TryGetValue(pair.Value, out text))
                    sb.Append($"==== 0x{pair.Key:X8} ====\n").Append(text.Value.TrimEnd('\n')).Append("\n\n");
            }
            string path = PathFor(binPath);
            if (sb.Length == 0)
            {
                if (File.Exists(path))
                    File.Delete(path);
                return;
            }
            File.WriteAllText(path, (Header + "\n\n" + sb).Replace("\n", Environment.NewLine));
        }

        // ---------------------------------------------------------------- merging

        class Line
        {
            public string Code;          // without comments, or null for a comment-only line
            public string Trailing;      // "// ..." after the code
            public List<string> Before = new List<string>();  // comment lines just above it
        }

        /// <summary>Puts the comments of the saved text onto the matching lines of the new text.</summary>
        static string Merge(string saved, string plain)
        {
            var old = Parse(saved);
            var now = plain.Replace("\r\n", "\n").Split('\n');
            var oldKeys = old.Where(l => l.Code != null).Select(l => Key(l.Code)).ToList();
            var oldLines = old.Where(l => l.Code != null).ToList();
            var nowKeys = now.Select(l => Key(l.Trim())).ToList();

            // longest common subsequence of the code lines
            int n = oldKeys.Count, m = nowKeys.Count;
            var lcs = new int[n + 1, m + 1];
            for (int i = n - 1; i >= 0; i--)
                for (int j = m - 1; j >= 0; j--)
                    lcs[i, j] = oldKeys[i] == nowKeys[j] && oldKeys[i].Length > 0
                        ? lcs[i + 1, j + 1] + 1 : Math.Max(lcs[i + 1, j], lcs[i, j + 1]);
            var match = new int[n];
            for (int i = 0, j = 0; i < n; )
            {
                if (j < m && oldKeys[i] == nowKeys[j] && oldKeys[i].Length > 0) { match[i] = j; i++; j++; }
                else if (j < m && lcs[i, j + 1] >= lcs[i + 1, j]) j++;
                else { match[i] = -1; i++; }
            }

            var before = new Dictionary<int, List<string>>();
            var trailing = new Dictionary<int, string>();
            var pending = new List<string>();
            for (int i = 0; i < n; i++)
            {
                pending.AddRange(oldLines[i].Before);
                if (match[i] < 0)
                {
                    if (oldLines[i].Trailing != null)       // its line is gone: keep the comment above the next one
                        pending.Add(oldLines[i].Trailing);
                    continue;
                }
                if (pending.Count > 0)
                {
                    before[match[i]] = new List<string>(pending);
                    pending.Clear();
                }
                if (oldLines[i].Trailing != null)
                    trailing[match[i]] = oldLines[i].Trailing;
            }
            pending.AddRange(old.Where(l => l.Code == null).SelectMany(l => l.Before)); // comments after the last line

            var sb = new StringBuilder();
            for (int j = 0; j < m; j++)
            {
                string indent = now[j].Substring(0, now[j].Length - now[j].TrimStart().Length);
                List<string> b;
                if (before.TryGetValue(j, out b))
                    foreach (var c in b)
                        sb.Append(indent).Append(c).Append('\n');
                sb.Append(now[j]);
                string t;
                if (trailing.TryGetValue(j, out t))
                    sb.Append(' ').Append(t);
                sb.Append('\n');
            }
            foreach (var c in pending)
                sb.Append(c).Append('\n');
            return sb.ToString().TrimEnd('\n').Replace("\n", Environment.NewLine);
        }

        /// <summary>Code lines with the comments around them. A last entry with Code == null holds
        /// comments after the last code line.</summary>
        static List<Line> Parse(string text)
        {
            var result = new List<Line>();
            var cur = new Line();
            bool inBlock = false;
            foreach (var raw in text.Replace("\r\n", "\n").Split('\n'))
            {
                string line = raw.Trim();
                if (inBlock || line.StartsWith("/*"))
                {
                    cur.Before.Add(line);
                    if (line.Contains("*/")) inBlock = false;
                    else inBlock = true;
                    continue;
                }
                if (line.StartsWith("//"))
                {
                    cur.Before.Add(line);
                    continue;
                }
                if (line.Length == 0)
                    continue;
                int c = line.IndexOf("//", StringComparison.Ordinal);
                cur.Code = (c >= 0 ? line.Substring(0, c) : line).Trim();
                cur.Trailing = c >= 0 ? line.Substring(c).Trim() : null;
                result.Add(cur);
                cur = new Line();
            }
            if (cur.Before.Count > 0)
                result.Add(cur);
            return result;
        }

        /// <summary>Compares lines by what they compile to, so 0x169 and 361 are the same line.</summary>
        static string Key(string code)
        {
            if (code.Length == 0)
                return "";
            try
            {
                var cmd = ACMDCompiler.CompileSingleCommand(code);
                return BitConverter.ToString(cmd.GetBytes(System.IO.Endianness.Big));
            }
            catch (Exception)
            {
                return new string(code.Where(ch => !char.IsWhiteSpace(ch)).ToArray());
            }
        }
    }
}
