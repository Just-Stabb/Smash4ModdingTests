using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.GUI;

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// v1.6.1: where the Hitbox Viewer's scripts come from, the same way for the game script (hitboxes) and the effect
    /// script (effects): a fighter's script folder (script/animcmd/body); a kind's file ("game", "effect") is the one open
    /// in the main window when it is in that folder, else the file on disk there (read again when it changes on disk).
    /// The open tab's editor for a kind: its "game" / "effect" sub-tab, or in single-file mode the tab's one editor when
    /// the open file is of that kind (an effect.bin opened alone gives its effects, the game script from game.bin next
    /// to it).
    /// </summary>
    public class ViewerScripts
    {
        public readonly string Folder;
        readonly Func<IEnumerable<KeyValuePair<string, IScriptCollection>>> open;
        readonly Dictionary<string, Tuple<DateTime, ACMDFile>> disk = new Dictionary<string, Tuple<DateTime, ACMDFile>>(StringComparer.OrdinalIgnoreCase);

        public ViewerScripts(string folder, Func<IEnumerable<KeyValuePair<string, IScriptCollection>>> openFiles)
        {
            Folder = folder;
            open = openFiles;
        }

        /// <summary>A script file's kind: its name without extension, lower case ("game", "effect", ...).</summary>
        public static string Kind(string path) { return (Path.GetFileNameWithoutExtension(path) ?? "").ToLowerInvariant(); }

        /// <summary>The folder the viewer shows: the open game.bin's, else any open ACMD file's (effect / sound /
        /// expression.bin opened alone); null when none is open.</summary>
        public static string FolderFor(IEnumerable<KeyValuePair<string, IScriptCollection>> files)
        {
            var acmd = files.Where(x => x.Value is ACMDFile).ToList();
            var game = acmd.FirstOrDefault(x => Kind(x.Key) == "game");
            if (game.Value != null) return Path.GetDirectoryName(game.Key);
            var any = acmd.FirstOrDefault();
            return any.Value != null ? Path.GetDirectoryName(any.Key) : null;
        }

        /// <summary>The kind's file: open in the main window (in this folder), else on disk here; null when neither.</summary>
        public ACMDFile File(string kind)
        {
            foreach (var f in open())
                if (f.Value is ACMDFile && Kind(f.Key) == kind &&
                    string.Equals(Path.GetDirectoryName(f.Key), Folder, StringComparison.OrdinalIgnoreCase))
                    return (ACMDFile)f.Value;
            string path = Path.Combine(Folder ?? "", kind + ".bin");
            try
            {
                if (!System.IO.File.Exists(path)) return null;
                var t = System.IO.File.GetLastWriteTimeUtc(path);
                Tuple<DateTime, ACMDFile> c;
                if (!disk.TryGetValue(path, out c) || c.Item1 != t)
                {
                    // read from a copy: the file stays free for the main window to save over (SALT maps the file it reads)
                    string copy = Path.GetTempFileName();
                    System.IO.File.Copy(path, copy, true);
                    c = Tuple.Create(t, new ACMDFile(new DataSource(FileMap.FromFile(copy, FileMapProtect.Read))));
                    disk[path] = c;
                }
                return c.Item2;
            }
            catch (Exception) { return null; }
        }

        /// <summary>The kind file's saved script for a hash (null when it has none).</summary>
        public IList<ICommand> Get(string kind, uint crc)
        {
            var f = File(kind);
            IScript s;
            return f != null && f.Scripts.TryGetValue(crc, out s) && s is ACMDScript ? ((ACMDScript)s).Commands : null;
        }

        public Func<uint, IList<ICommand>> Getter(string kind) { return crc => Get(kind, crc); }

        /// <summary>A tab's editor for a kind: its sub-tab of that name, or (singleFileKind: the kind of the one file open
        /// in single-file mode, else null) its only editor when the open file is of that kind. Null when it has none.</summary>
        public static ITS_EDITOR EditorFor(CodeEditor page, string kind, string singleFileKind)
        {
            if (page == null) return null;
            string tab = EditorTab(page.Editors.Select(x => x.Parent != null ? x.Parent.Text : "").ToList(), kind, singleFileKind);
            var ed = tab != null ? page.EditorFor(tab) : null;
            return ed != null && ed.Script is ACMDScript ? ed : null;
        }

        /// <summary>The rule itself (for tests): which of a tab's sub-tabs (named by file: "game", "effect", ..., or
        /// "Script" for the one file open in single-file mode) holds the kind's script; null when none.</summary>
        public static string EditorTab(IList<string> tabs, string kind, string singleFileKind)
        {
            if (tabs.Contains(kind)) return kind;
            if (singleFileKind == kind && tabs.Contains("Script")) return "Script";
            return null;
        }
    }
}
