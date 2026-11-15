using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace Sm4shCommand.Viewer
{
    /// <summary>An effect an effect script (effect.bin) starts: where (bone, offset, rotation, size), what (its ID), its
    /// colour / alpha / rate / scale (the call's own, then LAST_EFFECT_SET_*), and when (game frames of the script's
    /// timeline). The viewer works out its place from the bone: on its spawn frame for a one-shot effect (it stays in
    /// the world), every frame for a following one (EFFECT_FOLLOW and the like).</summary>
    public class EffectData
    {
        public int Index;                   // the n-th effect the script started (one entry per start)
        public uint Id, IdLeft;             // the effect ID (0xBBBBnnnn: bank, entry); IdLeft: a _FLIP call's left-facing one
        public bool HasLeft;
        public uint WorkVar;                // a _WORK call's ID comes from this variable (Id 0: not known here)
        public string Command, Line;
        public int Bone;
        public bool World;                  // EFFECT_GLOBAL / EM_EFFECT_*: no bone (the viewer puts it at the model's origin)
        public float X, Y, Z, RX, RY, RZ, Size = 1;
        public float R = 1, G = 1, B = 1, A = 1, Rate = 1, SX = 1, SY = 1, SZ = 1;
        public bool HasColor, HasAlpha, HasScale;
        // v1.6.2: the colour and alpha as the game applies them: the commands' 0-255 colours / 255 and percent alphas / 100
        // (Events.cfg: "divided by 255" / "handler divides by 100"); LAST_PARTICLE_SET_COLOR's multipliers on top
        public float CR = 1, CG = 1, CB = 1, CA = 1, PR = 1, PG = 1, PB = 1;
        public bool HasParticleColor;
        public void SetColour255() { CR = R / 255; CG = G / 255; CB = B / 255; }
        public bool Follow;
        public int Terminate;               // the call's Terminate parameter (as written)
        public int StartFrame, EndFrame = -1;   // game frames (1-based); EndFrame -1: still on
        public float SpawnAnimFrame;        // the animation frame it was started on (a one-shot's place)
        public int DetachFrame = -1;        // EFFECT_DETACH_KIND: from this frame it stays where it was
        public float DetachAnimFrame;
        public string EndReason = "";
        public EffectData Clone() { return (EffectData)MemberwiseClone(); }

        /// <summary>The effect's ID for a facing: a _FLIP call's GFXLeft when facing left.</summary>
        public uint IdFor(bool left) { return left && HasLeft ? IdLeft : Id; }
    }

    /// <summary>A sword trail (Sword_Glow / Sword_Trace / AFTER_IMAGE...): the blade between two points, one on each
    /// bone, every frame from its start to Terminate_Sword_Glow (+ its fade).</summary>
    public class TrailData
    {
        public int Index;
        public string Command, Line;
        public int Bone1, Bone2, Blur, Fade;
        public float X1, Y1, Z1, X2, Y2, Z2;
        public uint Graphic;
        public int Texture1, Texture2;      // v1.6.0: the trail texture ids (TrailNames; 0 none, -1 from a variable)
        public int Shader = 1;              // v1.6.0: the trail shader (effect_trail.nsh: 1, 2, 3; docs/native-notes.md)
        public int StartFrame, EndFrame = -1;
        public TrailData Clone() { return (TrailData)MemberwiseClone(); }
    }

    /// <summary>Screen / light effects (tints, flashes, lights, wind): listed, not drawn.</summary>
    public class ScreenEvent
    {
        public int Frame;
        public string Text;
    }

    /// <summary>
    /// A fighter's effect banks for the viewer: an effect ID 0xBBBBnnnn is entry nnnn of bank 0xBBBB (docs/efc-format.md:
    /// 0x100 common, 0x300 + kind the fighter's, 0x400 + kind its Final Smash's). Each fighter bank is
    /// fighter/NAME/effect/NAME/NAME.010d0000.efc + .ptcl: the .efc entry names the .ptcl's emitter set (1-based) and an
    /// effect model; the set's name is the effect's name. Common effects are named from the tooltips (gfx.txt, the MSC
    /// Note Sheet's Global GFX list). The .ptcl is read whole (Level 2 decodes its emitters from it).
    /// </summary>
    public class EffectLibrary
    {
        // fighter kinds (tools/fighter_param.py KINDS, tools/extra_kinds.json): kind -> folder name
        public static readonly string[] Kinds = {
            "miifighter", "miiswordsman", "miigunner", "mario", "donkey", "link", "samus", "yoshi", "kirby", "fox",
            "pikachu", "luigi", "captain", "ness", "peach", "koopa", "zelda", "sheik", "marth", "gamewatch", "ganon",
            "falco", "wario", "metaknight", "pit", "szerosuit", "pikmin", "diddy", "dedede", "ike", "lucario", "robot",
            "toonlink", "lizardon", "sonic", "purin", "mariod", "lucina", "pitb", "rosetta", "wiifit", "littlemac",
            "murabito", "palutena", "reflet", "duckhunt", "koopajr", "shulk", "gekkouga", "pacman", "rockman",
            "mewtwo", "ryu", "lucas", "roy", "cloud", "bayonetta", "kamui", "koopag", "warioman", "littlemacg",
            "lucariom", "miienemyf", "miienemys", "miienemyg", "supamario", "edge", "gaogaen", "pickel", "brave", "pzenigame" };

        public class Bank
        {
            public int Id;
            public string Folder, Name;
            public EfcFile Efc;
            public PtclFile Ptcl;
        }

        readonly string fighterRoot, fighterName;
        readonly Dictionary<int, Bank> banks = new Dictionary<int, Bank>();
        public Func<uint, string> CommonName;     // common effect names (the viewer: the tooltips)

        public EffectLibrary(string fighterRoot)
        {
            this.fighterRoot = fighterRoot;
            fighterName = fighterRoot != null ? Path.GetFileName(fighterRoot) : null;
        }

        /// <summary>The folder name a bank is under: Kinds[bank - 0x300] (or "Fin" + it for 0x400 +).</summary>
        static string BankFolder(int bank)
        {
            int cat = bank >> 8, kind = bank & 0xFF;
            if ((cat != 3 && cat != 4) || kind >= Kinds.Length) return null;
            return (cat == 4 ? "Fin" : "") + Kinds[kind];
        }

        /// <summary>The bank's files: under this fighter's effect folder, else a sibling fighter's (Kirby's copies use
        /// the copied fighter's bank: fighter/kirby/../brave/effect/brave). Null when not found.</summary>
        public Bank GetBank(int id)
        {
            Bank b;
            if (banks.TryGetValue(id, out b)) return b;
            b = null;
            if (id == CommonBank)
            {
                // v1.6.1: the common bank, from the game's effect/common folder (CommonFolder)
                b = LoadBank(id, CommonFolder, "common");
                banks[id] = b;
                return b;
            }
            string folder = BankFolder(id);
            var tries = new List<Tuple<string, string>>();       // (fighter folder, bank folder)
            if (folder != null && fighterRoot != null)
            {
                string owner = (id >> 8) == 4 ? folder.Substring(3) : folder;
                tries.Add(Tuple.Create(fighterRoot, folder));
                string parent = Path.GetDirectoryName(fighterRoot);
                if (parent != null) tries.Add(Tuple.Create(Path.Combine(parent, owner), folder));
            }
            // a port keeps its base fighter's bank number (Hero over Robin: 0x32C) in its own folder's files: the
            // fighter's own bank for a 0x3xx / 0x4xx bank no folder above has
            if (fighterRoot != null && ((id >> 8) == 3 || (id >> 8) == 4))
                tries.Add(Tuple.Create(fighterRoot, ((id >> 8) == 4 ? "Fin" : "") + fighterName));
            {
                foreach (var tr in tries)
                {
                    string root = tr.Item1;
                    folder = tr.Item2;
                    string dir = Path.Combine(Path.Combine(root, "effect"), folder);
                    string efc = Path.Combine(dir, folder + ".010d0000.efc");
                    if (!File.Exists(efc)) continue;
                    b = new Bank { Id = id, Folder = dir, Name = folder };
                    try { b.Efc = new EfcFile(File.ReadAllBytes(efc)); } catch (Exception) { b.Efc = null; }
                    string ptcl = Path.Combine(dir, folder + ".010d0000.ptcl");
                    try { if (File.Exists(ptcl)) b.Ptcl = new PtclFile(File.ReadAllBytes(ptcl)); } catch (Exception) { b.Ptcl = null; }
                    break;
                }
            }
            banks[id] = b;
            return b;
        }

        // ---- v1.6.1: the common effects (bank 0x100: ids 0x01000000 +) ---------------------------------------------------
        public const int CommonBank = 0x100;
        public const string CommonEfc = "common.010d0000.efc";
        string commonFolder;

        /// <summary>The folder with the common bank (common.010d0000.efc / .ptcl / model / trail): the game's
        /// data/effect/common. Setting it forgets what was loaded from the old one.</summary>
        public string CommonFolder
        {
            get { return commonFolder; }
            set
            {
                if (string.Equals(commonFolder, value, StringComparison.OrdinalIgnoreCase)) return;
                commonFolder = value;
                banks.Remove(CommonBank);
                assets.Clear();
                trailTextures.Clear();
                trailDirs = null;
            }
        }

        /// <summary>A folder that holds the common bank: the folder itself, its effect/common, or its common subfolder;
        /// null when none does.</summary>
        public static string CommonFolderIn(string dir)
        {
            if (string.IsNullOrEmpty(dir)) return null;
            foreach (var d in new[] { dir, Path.Combine(Path.Combine(dir, "effect"), "common"), Path.Combine(dir, "common"),
                                      Path.Combine(Path.Combine(Path.Combine(dir, "data"), "effect"), "common") })
                try { if (File.Exists(Path.Combine(d, CommonEfc))) return d; } catch (Exception) { }
            return null;
        }

        /// <summary>The common bank for a fighter folder: as the game lays its files out, data/effect/common next to
        /// data/fighter (fighter/NAME/../../effect/common), looked for in every folder above the fighter's (a dump's
        /// content/patch/data, a mod's own data folder, ...); null when none has it.</summary>
        public static string FindCommonFolder(string fighterRoot)
        {
            string d = fighterRoot;
            for (int up = 0; up < 8 && !string.IsNullOrEmpty(d); up++)
            {
                d = Path.GetDirectoryName(d);
                var f = CommonFolderIn(d);
                if (f != null) return f;
            }
            return null;
        }

        static Bank LoadBank(int id, string dir, string name)
        {
            if (string.IsNullOrEmpty(dir)) return null;
            string efc = Path.Combine(dir, name + ".010d0000.efc");
            if (!File.Exists(efc)) return null;
            var b = new Bank { Id = id, Folder = dir, Name = name };
            try { b.Efc = new EfcFile(File.ReadAllBytes(efc)); } catch (Exception) { b.Efc = null; }
            string ptcl = Path.Combine(dir, name + ".010d0000.ptcl");
            try { if (File.Exists(ptcl)) b.Ptcl = new PtclFile(File.ReadAllBytes(ptcl)); } catch (Exception) { b.Ptcl = null; }
            return b;
        }

        /// <summary>"name" for an effect ID: the .ptcl set (and the model, when the entry has one), the common effect's
        /// tooltip name, or "" when not known.</summary>
        public string Name(uint id)
        {
            int bank = (int)(id >> 16), entry = (int)(id & 0xFFFF);
            string common = bank == CommonBank && CommonName != null ? CommonName(id) ?? "" : "";
            var b = GetBank(bank);
            if (b == null || b.Efc == null || entry >= b.Efc.Entries.Count) return common;
            var e = b.Efc.Entries[entry];
            var parts = new List<string>();
            if (e.Set > 0 && b.Ptcl != null && e.Set - 1 < b.Ptcl.Sets.Count) parts.Add(b.Ptcl.Sets[(int)e.Set - 1].Name);
            if (e.Model > 0 && e.Model - 1 < b.Efc.Models.Count) parts.Add("model " + b.Efc.Models[(int)e.Model - 1]);
            string own = string.Join(" + ", parts.ToArray());
            if (common.Length > 0) return own.Length > 0 ? common + " (" + own + ")" : common;
            return own;
        }

        /// <summary>How long a one-shot effect plays, in frames: the latest emitter's end (start + emission (one-time
        /// emitters) + particle life) of its .ptcl set, and (v1.6.0) its effect model's animation length (model.omo /
        /// .mta frames) when it has one; null when the set never stops by itself, the entry has neither, or the files
        /// aren't there.</summary>
        public int? Lifetime(uint id)
        {
            int bank = (int)(id >> 16), entry = (int)(id & 0xFFFF);
            var b = GetBank(bank);
            if (b == null || b.Efc == null || entry >= b.Efc.Entries.Count) return null;
            var en = b.Efc.Entries[entry];
            int set = (int)en.Set - 1;
            int? life = null;
            if (set >= 0)
            {
                if (b.Ptcl == null || set >= b.Ptcl.Sets.Count) return null;
                life = b.Ptcl.Sets[set].Lifetime();
                if (!life.HasValue) return null;
            }
            var model = en.Model > 0 ? ModelFor(b, (int)en.Model) : null;
            if (model != null && model.Frames > 0) life = Math.Max(life ?? 0, model.Frames);
            return life;
        }

        // ---- v1.6.0 (Level 2): what an effect draws ----------------------------------------------------------------

        readonly Dictionary<uint, EffectAssets> assets = new Dictionary<uint, EffectAssets>();
        readonly Dictionary<string, EffectModel> models = new Dictionary<string, EffectModel>(StringComparer.OrdinalIgnoreCase);

        /// <summary>The effect model an entry names (model/&lt;name&gt;/ in the bank's folder), loaded once; null when it
        /// isn't there.</summary>
        public EffectModel ModelFor(Bank b, int model)
        {
            if (b == null || b.Efc == null || model <= 0 || model > b.Efc.Models.Count) return null;
            string dir = Path.Combine(Path.Combine(b.Folder, "model"), b.Efc.Models[model - 1]);
            EffectModel m;
            if (models.TryGetValue(dir, out m)) return m;
            try { m = EffectModel.Load(dir); } catch (Exception) { m = null; }
            models[dir] = m;
            return m;
        }

        /// <summary>An effect id's emitters (its .ptcl set's, read once) and model; null for common effects (their bank
        /// isn't in the fighter's folder) and when the files aren't there.</summary>
        public EffectAssets AssetsFor(uint id)
        {
            EffectAssets a;
            if (assets.TryGetValue(id, out a)) return a;
            a = null;
            int bank = (int)(id >> 16), entry = (int)(id & 0xFFFF);
            var b = GetBank(bank);
            if (b != null && b.Efc != null && entry < b.Efc.Entries.Count)
            {
                var en = b.Efc.Entries[entry];
                a = new EffectAssets();
                int set = (int)en.Set - 1;
                if (set >= 0 && b.Ptcl != null && set < b.Ptcl.Sets.Count)
                {
                    a.SetName = b.Ptcl.Sets[set].Name;
                    foreach (var e in b.Ptcl.Sets[set].Emitters)
                    {
                        EmitterDef d;
                        try { d = e.Def; } catch (Exception) { d = null; }
                        if (d != null) a.Emitters.Add(d);
                    }
                }
                if (en.Model > 0) a.Model = ModelFor(b, (int)en.Model);
                if (a.Emitters.Count == 0 && a.Model == null) a = null;
            }
            assets[id] = a;
            return a;
        }

        readonly Dictionary<string, Texture> trailTextures = new Dictionary<string, Texture>(StringComparer.OrdinalIgnoreCase);
        List<string> trailDirs;

        /// <summary>A sword trail texture by id (TrailNames): "&lt;name&gt;.nut" in this fighter's effect/*/trail folders,
        /// else in the other fighters' next to it (the game looks among every loaded trail texture); null when not found.</summary>
        public Texture TrailTexture(int id)
        {
            string name = TrailNames.Name(id);
            if (name == null) return null;
            Texture t;
            if (trailTextures.TryGetValue(name, out t)) return t;
            t = null;
            if (trailDirs == null)
            {
                trailDirs = new List<string>();
                if (commonFolder != null && Directory.Exists(Path.Combine(commonFolder, "trail")))
                    trailDirs.Add(Path.Combine(commonFolder, "trail"));     // (the common trails: TexCommonHammerTrace ...)
                var roots = new List<string>();
                if (fighterRoot != null) roots.Add(fighterRoot);
                string parent = fighterRoot != null ? Path.GetDirectoryName(fighterRoot) : null;
                try
                {
                    if (parent != null && Directory.Exists(parent))
                        roots.AddRange(Directory.GetDirectories(parent).Where(x => !string.Equals(x, fighterRoot, StringComparison.OrdinalIgnoreCase)).OrderBy(x => x));
                }
                catch (Exception) { }
                foreach (var r in roots)
                {
                    string fx = Path.Combine(r, "effect");
                    try
                    {
                        if (!Directory.Exists(fx)) continue;
                        foreach (var bdir in Directory.GetDirectories(fx).OrderBy(x => x))
                        {
                            string tr = Path.Combine(bdir, "trail");
                            if (Directory.Exists(tr)) trailDirs.Add(tr);
                        }
                    }
                    catch (Exception) { }
                }
            }
            foreach (var dir in trailDirs)
            {
                string f = Path.Combine(dir, name + ".nut");
                if (!File.Exists(f)) continue;
                try { t = Nut.Load(f).Values.FirstOrDefault(); } catch (Exception) { t = null; }
                if (t != null) break;
            }
            trailTextures[name] = t;
            return t;
        }
    }

    /// <summary>A .efc (EFCF; tools/efc.py, docs/efc-format.md).</summary>
    public class EfcFile
    {
        public class Entry { public uint Flags, Set, Model; public int MeshFirst, MeshCount; }
        public List<Entry> Entries = new List<Entry>();
        public List<string> Models = new List<string>(), MeshNames = new List<string>();

        public EfcFile(byte[] d)
        {
            if (d.Length < 16 || d[0] != 'E' || d[1] != 'F' || d[2] != 'C' || d[3] != 'F')
                throw new InvalidDataException("not an EFCF file");
            int variant = BE.U16(d, 4), n = BE.U16(d, 8), m = BE.U16(d, 0xA), x = BE.U16(d, 0xC);
            for (int i = 0; i < n; i++)
            {
                int o = 16 + 16 * i;
                Entries.Add(new Entry { Flags = BE.U32(d, o), Set = BE.U32(d, o + 4), Model = BE.U32(d, o + 8),
                                        MeshFirst = BE.U16(d, o + 12), MeshCount = BE.U16(d, o + 14) });
            }
            int p = 16 + 16 * n + 4 * x + (variant == 1 ? 2 * m : 0);
            for (int i = 0; i < m + x && p < d.Length; i++)
            {
                int e = p;
                while (e < d.Length && d[e] != 0) e++;
                string s = Encoding.ASCII.GetString(d, p, e - p);
                if (i < m) Models.Add(s); else MeshNames.Add(s);
                p = e + 1;
            }
        }
    }

    /// <summary>
    /// A .ptcl (EFTF version 0x42, NintendoWare for Cafe eft; tools/ptcl.py, docs/ptcl-format.md): the emitter sets and
    /// their emitters' raw data (offsets as ptcl.py's FIELDS), the texture / name / key-animation tables. Level 1 reads
    /// names and timing; the rest is kept for Level 2 (particles).
    /// </summary>
    public class PtclFile
    {
        public byte[] Data;
        public int NamePos, TexPos, TexSize, ShaderPos, ShaderSize, KeyAnimPos, KeyAnimSize, PrimPos, PrimSize;
        // v1.6.0: decoded textures (by their place in the texture table) and the emitters' particle definitions
        internal readonly Dictionary<long, Texture> TextureCache = new Dictionary<long, Texture>();
        public List<EmitterSet> Sets = new List<EmitterSet>();

        public class Emitter
        {
            public int Pos, Size;
            public string Name;
            public PtclFile File;
            public int I(int off) { return BE.I32(File.Data, Pos + off); }
            public float F(int off) { return BE.F32(File.Data, Pos + off); }
            public byte U8(int off) { return File.Data[Pos + off]; }
            // ptcl.py FIELDS (Level 1 uses the timing ones)
            public bool OneTime { get { return U8(0x2FF) != 0; } }
            public int StartFrame { get { return I(0x448); } }
            public int EmitStart { get { return I(0x44C); } }
            public int EndFrame { get { return I(0x450); } }
            public int Life { get { return I(0x4B0); } }
            public int LifeRandom { get { return I(0x4B4); } }
            public int BlendType { get { return I(0x324); } }
            public int ParticleType { get { return I(0x4BC); } }
            public float EmitRate { get { return F(0x444); } }
            EmitterDef def;
            /// <summary>v1.6.0: the emitter's particle definition (Particles.cs), read once.</summary>
            public EmitterDef Def { get { return def ?? (def = EmitterDef.Read(this)); } }
        }

        public class EmitterSet
        {
            public string Name;
            public int Index;
            public List<Emitter> Emitters = new List<Emitter>();

            /// <summary>Frames until the set's last particle is gone: max over its emitters of start + emission end
            /// (one-time emitters) + particle life (+ its random part); null when an emitter never stops emitting or
            /// its particles live forever.</summary>
            public int? Lifetime()
            {
                int best = 0;
                foreach (var e in Emitters)
                {
                    if (!e.OneTime || e.EndFrame >= 0x7FFFFFF || e.Life >= 0x7FFFFFF) return null;
                    long t = (long)Math.Max(0, e.StartFrame) + Math.Max(0, e.EmitStart) + Math.Max(0, e.EndFrame) +
                             Math.Max(0, e.Life) + Math.Max(0, e.LifeRandom);
                    best = (int)Math.Max(best, Math.Min(t, 100000));
                }
                return Emitters.Count > 0 ? (int?)best : null;
            }
        }

        public PtclFile(byte[] d)
        {
            if (d.Length < 0x48 || d[0] != 'E' || d[1] != 'F' || d[2] != 'T' || d[3] != 'F')
                throw new InvalidDataException("not an EFTF file");
            Data = d;
            int nsets = BE.I32(d, 8);
            NamePos = BE.I32(d, 0x10); TexPos = BE.I32(d, 0x14); TexSize = BE.I32(d, 0x18);
            ShaderPos = BE.I32(d, 0x1C); ShaderSize = BE.I32(d, 0x20);
            KeyAnimPos = BE.I32(d, 0x24); KeyAnimSize = BE.I32(d, 0x28); PrimPos = BE.I32(d, 0x2C); PrimSize = BE.I32(d, 0x30);
            for (int i = 0; i < nsets && 0x48 + 0x1C * i + 0x1C <= d.Length; i++)
            {
                int o = 0x48 + 0x1C * i;
                var s = new EmitterSet { Name = NameAt(BE.I32(d, o + 8)), Index = i };
                int n = BE.I32(d, o + 0x10), tbl = BE.I32(d, o + 0x14);
                for (int k = 0; k < n && tbl + 0x10 * k + 4 <= d.Length; k++)
                {
                    int pos = BE.I32(d, tbl + 0x10 * k);
                    if (pos <= 0 || pos + 0x8BC > d.Length) continue;
                    int size = BE.I32(d, pos) == 1 && pos + 0x8D4 <= d.Length ? BE.I32(d, pos + 0x8D0) : 0x8BC;
                    var em = new Emitter { Pos = pos, Size = size, File = this };
                    em.Name = NameAt(BE.I32(d, pos + 0x38));
                    s.Emitters.Add(em);
                }
                Sets.Add(s);
            }
        }

        public string NameAt(int pos)
        {
            int p = NamePos + pos;
            if (pos < 0 || p >= Data.Length) return "";
            int e = p;
            while (e < Data.Length && Data[e] != 0) e++;
            return Encoding.ASCII.GetString(Data, p, e - p);
        }
    }

    /// <summary>The facing rule the Super God Fist / Core Breaker ports learned in game (tools/xv2_smash_fx.py
    /// facing_check): an effect on bone 0 (TopN) may only sit at a height / ahead (no X offset) and turn about Y by 0 or
    /// 180; on any other bone no offset and no turn. Other calls looked different facing left in game (God Fist v6:
    /// "mirrored vertically depending on facing"). Returns why, or "" when it keeps the rule.</summary>
    public static class FacingRule
    {
        static bool Zero(float v) { return Math.Abs(v) < 1e-4f; }

        public static string Check(EffectData e)
        {
            if (e.World) return "";
            var ic = CultureInfo.InvariantCulture;
            if (e.Bone == 0)
            {
                float ry = ((e.RY % 360) + 360) % 360;
                var why = new List<string>();
                if (!Zero(e.X)) why.Add("X offset " + e.X.ToString("0.##", ic));
                if (!Zero(e.RX)) why.Add("X turn " + e.RX.ToString("0.##", ic));
                if (!Zero(e.RZ)) why.Add("Z turn " + e.RZ.ToString("0.##", ic));
                if (!Zero(ry) && !Zero(ry - 180) && !Zero(ry - 360)) why.Add("Y turn " + e.RY.ToString("0.##", ic));
                return why.Count > 0 ? "bone 0 with " + string.Join(", ", why.ToArray()) : "";
            }
            if (!Zero(e.X) || !Zero(e.Y) || !Zero(e.Z) || !Zero(e.RX) || !Zero(e.RY) || !Zero(e.RZ))
                return "a body bone with an offset / turn";
            return "";
        }
    }
}
