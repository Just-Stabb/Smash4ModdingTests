using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;

namespace Sm4shCommand
{
    /// <summary>
    /// v1.7.2: a fighter's (or an article's) four ACMD files as the main window holds them in fighter mode (path -> file):
    /// a motion's script added to one of them, or taken out, and the files written back. A motion's script in a file is
    /// keyed by the motion's hash (the CRC32 of its lower-case name), as the game and every other script are. A file the
    /// folder hasn't got is made (an empty ACMD file in the endianness of the folder's other files) and written on save.
    /// </summary>
    public static class ScriptFileSet
    {
        /// <summary>The four ACMD files of a motion, in the order the game runs them.</summary>
        public static readonly string[] Kinds = { "game", "effect", "sound", "expression" };

        /// <summary>The kind's file (KIND.bin, in folder or whichever open file has that name), or null (path: where it goes).</summary>
        public static ACMDFile Find(IDictionary<string, IScriptCollection> files, string folder, string kind, out string path)
        {
            path = folder != null ? Path.Combine(folder, kind + ".bin") : null;
            foreach (var pair in files)
                if (pair.Value is ACMDFile && string.Equals(Path.GetFileNameWithoutExtension(pair.Key), kind, StringComparison.OrdinalIgnoreCase))
                {
                    path = pair.Key;
                    return (ACMDFile)pair.Value;
                }
            return null;
        }

        /// <summary>Whether the kind's file has the motion's script.</summary>
        public static bool Has(IDictionary<string, IScriptCollection> files, string folder, uint crc, string kind)
        {
            string path;
            var f = Find(files, folder, kind, out path);
            return f != null && f.Scripts.ContainsKey(crc);
        }

        /// <summary>A new empty script (Script_End) for the motion in the kind's file; the file made (and put in files) when
        /// missing, in the given endianness. Returns the file's path; made: whether the file is new.</summary>
        public static string Add(IDictionary<string, IScriptCollection> files, string folder, uint crc, string kind, Endianness endian, out bool made)
        {
            string path;
            var f = Find(files, folder, kind, out path);
            made = f == null;
            if (made)
            {
                if (path == null) throw new InvalidOperationException("no folder for a new " + kind + ".bin");
                f = new ACMDFile { Endian = endian };
                files.Add(path, f);
            }
            if (!f.Scripts.ContainsKey(crc))
                f.Scripts.Add(crc, ACMDScript.CreateEmpty(crc));
            return path;
        }

        /// <summary>Takes the motion's script out of the kind's file (the file stays). False when it had none.</summary>
        public static bool Remove(IDictionary<string, IScriptCollection> files, string folder, uint crc, string kind)
        {
            string path;
            var f = Find(files, folder, kind, out path);
            return f != null && f.Scripts.Remove(crc);
        }

        /// <summary>The endianness of the open ACMD files (the first one's), else big (Wii U).</summary>
        public static Endianness EndianOf(IDictionary<string, IScriptCollection> files, Endianness fallback)
        {
            var f = files.Values.OfType<ACMDFile>().FirstOrDefault();
            return f != null ? f.Endian : fallback;
        }
    }
}
