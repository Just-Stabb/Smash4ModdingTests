using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// A fighter's model, skeleton and body animations, found from a script's path
    /// (fighter/NAME/script/animcmd/body/game.bin -> fighter/NAME/model, motion).
    /// </summary>
    public class FighterAssets
    {
        public string Root, Name, ModelPath;
        public Skeleton Skeleton;
        public NudModel Model;
        public Dictionary<string, byte[]> Animations = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
        readonly Dictionary<uint, string> byScript = new Dictionary<uint, string>();
        readonly Dictionary<string, Omo> loaded = new Dictionary<string, Omo>();

        /// <summary>The fighter folder (with model and motion) at or above path, or null.</summary>
        public static string FindRoot(string path)
        {
            var dir = File.Exists(path) ? Path.GetDirectoryName(path) : path;
            for (int i = 0; i < 6 && !string.IsNullOrEmpty(dir); i++)
            {
                if (Directory.Exists(Path.Combine(dir, "model")) && Directory.Exists(Path.Combine(dir, "motion")))
                    return dir;
                dir = Path.GetDirectoryName(dir);
            }
            return null;
        }

        public static FighterAssets Load(string root, string costume = "c00")
        {
            var a = new FighterAssets { Root = root, Name = Path.GetFileName(root) };
            string body = Path.Combine(root, "model", "body");
            string cdir = Path.Combine(body, costume);
            if (!File.Exists(Path.Combine(cdir, "model.nud")) && Directory.Exists(body))
                cdir = Directory.GetDirectories(body).OrderBy(x => x).FirstOrDefault(x => File.Exists(Path.Combine(x, "model.nud"))) ?? cdir;
            a.ModelPath = cdir;
            a.Skeleton = Skeleton.Load(Path.Combine(cdir, "model.vbn"));
            a.Model = NudModel.Load(Path.Combine(cdir, "model.nud"));
            foreach (var m in a.Model.Meshes)
                m.Visible = !HiddenByDefault(m.Name);
            string pac = Path.Combine(root, "motion", "body", "main.pac");
            if (File.Exists(pac))
                a.Animations = Pac.Load(pac);
            a.MapScripts();
            return a;
        }

        /// <summary>Expression variants of the face / eyes / body (shown instead of the normal mesh by
        /// expression scripts) start hidden; the viewer's mesh list can show them.</summary>
        static bool HiddenByDefault(string mesh)
        {
            string[] words = { "blink", "halfblink", "ouch", "talk", "capture", "furafura", "sorori", "steppose",
                               "pattern", "damagefly", "heavyouch", "bodybig2", "openmouth", "smile", "shout", "fura",
                               "eye2", "eye3", "eye4", "_attack_", "kirby_attack" };
            string n = mesh.ToLowerInvariant();
            return words.Any(w => n.Contains(w));
        }

        static uint Crc(string s) { return System.Security.Cryptography.Crc32.Compute(s.ToLowerInvariant()); }

        /// <summary>Which animation a script hash plays: the file name without its prefix and motion code
        /// (FitKirbyBodyMainC03AttackS4S.omo -> AttackS4S), plus the names scripts use for some of them
        /// (as Smash Forge / Sm4shCommand's Parse Animations do).</summary>
        void MapScripts()
        {
            var alias = new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                { "AttackS4S", new[] { "AttackS4" } }, { "AttackS3S", new[] { "AttackS3" } },
                { "AttackS3Ss", new[] { "AttackS3s" } }, { "AttackS3Sw", new[] { "AttackS3w" } },
                { "AttackEnd", new[] { "Attack100End" } }, { "SpecialHi1", new[] { "SpecialHi" } },
                { "SpecialAirHi1", new[] { "SpecialAirHi" } }, { "AttackS4Charge", new[] { "AttackS4Hold" } },
            };
            foreach (var file in Animations.Keys.OrderBy(x => x))
            {
                var m = Regex.Match(file, @"(.*)([A-Z])([0-9][0-9])(.*)\.omo$");
                if (!m.Success) continue;
                string anim = m.Groups[4].Value;
                Add(Crc(anim), file, true);
                string[] more;
                if (alias.TryGetValue(anim, out more))
                    foreach (var x in more) Add(Crc(x), file, false);
                foreach (var suffix in new[] { "_C2", "_C3", "L", "R" })
                    Add(Crc(anim + suffix), file, false);
            }
        }

        void Add(uint crc, string file, bool exact)
        {
            if (exact || !byScript.ContainsKey(crc))
                byScript[crc] = file;
        }

        public string AnimationFor(uint scriptCrc)
        {
            string f;
            return byScript.TryGetValue(scriptCrc, out f) ? f : null;
        }

        public IEnumerable<string> AnimationNames { get { return Animations.Keys.OrderBy(x => x); } }

        public Omo GetAnimation(string file)
        {
            if (file == null) return null;
            Omo o;
            if (loaded.TryGetValue(file, out o)) return o;
            byte[] d;
            if (!Animations.TryGetValue(file, out d)) return null;
            try { o = new Omo(d); } catch (InvalidDataException) { o = null; }
            loaded[file] = o;
            return o;
        }
    }
}
