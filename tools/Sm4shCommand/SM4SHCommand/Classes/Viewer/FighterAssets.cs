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
        public Dictionary<int, Texture> Textures = new Dictionary<int, Texture>();
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
            LoadModel(a, cdir);
            string pac = Path.Combine(root, "motion", "body", "main.pac");
            if (File.Exists(pac))
                a.Animations = Pac.Load(pac);
            a.MapScripts();
            a.MapModScripts();
            return a;
        }

        static void LoadModel(FighterAssets a, string cdir)
        {
            a.ModelPath = cdir;
            a.Skeleton = Skeleton.Load(Path.Combine(cdir, "model.vbn"));
            a.Model = NudModel.Load(Path.Combine(cdir, "model.nud"));
            foreach (var m in a.Model.Meshes)
                m.Visible = !HiddenByDefault(m.Name);
            try { a.Textures = Nut.Load(Path.Combine(cdir, "model.nut")); }
            catch (Exception) { }
            foreach (var m in a.Model.Meshes)
                foreach (var p in m.Polys)
                {
                    Texture t;
                    if (p.UV != null && a.Textures.TryGetValue(p.TextureHash, out t)) p.Texture = t;
                    float[] st;     // the texture's UV scale and offset
                    if (p.UV != null && p.Props.TryGetValue("NU_colorSamplerUV", out st) && st.Length >= 4 &&
                        (st[0] != 1 || st[1] != 1 || st[2] != 0 || st[3] != 0))
                        for (int i = 0; i + 1 < p.UV.Length; i += 2)
                        {
                            p.UV[i] = p.UV[i] * st[0] + st[2];
                            p.UV[i + 1] = p.UV[i + 1] * st[1] + st[3];
                        }
                }
        }

        // ---- mods' scripts (Runtime.ViewerAnims, from ModAnimNames.txt): their animation from another
        //      motion folder (loaded with all its animations), and a held model shown while it plays
        readonly Dictionary<string, Tuple<string, string>> heldFor = new Dictionary<string, Tuple<string, string>>(StringComparer.OrdinalIgnoreCase);
        readonly Dictionary<string, FighterAssets> held = new Dictionary<string, FighterAssets>(StringComparer.OrdinalIgnoreCase);

        void MapModScripts()
        {
            var folders = new Dictionary<string, Dictionary<string, byte[]>>(StringComparer.OrdinalIgnoreCase);
            foreach (var kv in Runtime.ViewerAnims)
            {
                var v = kv.Value;
                Dictionary<string, byte[]> anims;
                if (!folders.TryGetValue(v.Folder, out anims))
                {
                    string pac = Path.Combine(Root, "motion", v.Folder, "main.pac");
                    anims = null;
                    try { if (File.Exists(pac)) anims = Pac.Load(pac); } catch (Exception) { }
                    folders[v.Folder] = anims;
                    if (anims != null)
                        foreach (var e in anims)
                            if (!Animations.ContainsKey(e.Key)) Animations[e.Key] = e.Value;
                }
                if (anims == null || !anims.ContainsKey(v.File)) continue;
                byScript[kv.Key] = v.File;
                if (!string.IsNullOrEmpty(v.Held) && !string.IsNullOrEmpty(v.Bone))
                    heldFor[v.File] = Tuple.Create(v.Held, v.Bone);
            }
        }

        /// <summary>The held model shown while an animation plays (model/NAME/c00 of this fighter)
        /// and the bone (index in this skeleton) it's on, or null.</summary>
        public Tuple<FighterAssets, int> HeldFor(string anim)
        {
            Tuple<string, string> h;
            if (anim == null || !heldFor.TryGetValue(anim, out h)) return null;
            int bone = Skeleton.Bones.FindIndex(b => b.Name == h.Item2);
            if (bone < 0) return null;
            FighterAssets m;
            if (!held.TryGetValue(h.Item1, out m))
            {
                m = null;
                try
                {
                    string dir = Path.Combine(Root, "model", h.Item1);
                    string cdir = Directory.Exists(dir) ? Directory.GetDirectories(dir).OrderBy(x => x)
                        .FirstOrDefault(x => File.Exists(Path.Combine(x, "model.nud"))) : null;
                    if (cdir != null)
                    {
                        m = new FighterAssets { Root = Root, Name = h.Item1 };
                        LoadModel(m, cdir);
                    }
                }
                catch (Exception) { m = null; }
                held[h.Item1] = m;
            }
            return m == null ? null : Tuple.Create(m, bone);
        }

        /// <summary>Expression variants of the face / eyes / body (shown instead of the normal mesh by
        /// expression scripts) start hidden; the viewer's mesh list can show them.</summary>
        static bool HiddenByDefault(string mesh)
        {
            string[] words = { "blink", "halfblink", "ouch", "talk", "capture", "furafura", "sorori", "steppose",
                               "pattern", "damagefly", "heavyouch", "bodybig2", "openmouth", "smile", "shout", "fura",
                               "eye2", "eye3", "eye4", "_attack_", "kirby_attack", "nohat", "_down_", "_cliff_", "_bound_", "_final_",
                               "_escape_", "_ottotto_", "_result_", "_heavyouch_", "facenmhalf", "facenmopen" };
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

        /// <summary>The script hashes that play an animation file: its own name first, then the
        /// names scripts use for it (AttackS4S -> AttackS4, AttackS4S_C2, ..).</summary>
        public List<uint> ScriptsFor(string file)
        {
            var o = new List<uint>();
            if (file == null) return o;
            var m = Regex.Match(file, @"(.*)([A-Z])([0-9][0-9])(.*)\.omo$");
            if (m.Success) o.Add(Crc(m.Groups[4].Value));
            foreach (var kv in byScript)
                if (kv.Value == file && !o.Contains(kv.Key)) o.Add(kv.Key);
            return o;
        }

        /// <summary>The first animation whose name (without prefix) is one of names, or null.</summary>
        public string FindAnimation(params string[] names)
        {
            foreach (var n in names)
            {
                string f;
                if (byScript.TryGetValue(Crc(n), out f)) return f;
            }
            return null;
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
