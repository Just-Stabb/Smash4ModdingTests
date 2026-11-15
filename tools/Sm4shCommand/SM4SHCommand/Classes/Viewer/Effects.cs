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

        /// <summary>"name" for an effect ID: the .ptcl set (and the model, when the entry has one), the common effect's
        /// tooltip name, or "" when not known.</summary>
        public string Name(uint id)
        {
            int bank = (int)(id >> 16), entry = (int)(id & 0xFFFF);
            if (bank == 0x100)
                return CommonName != null ? CommonName(id) ?? "" : "";
            var b = GetBank(bank);
            if (b == null || b.Efc == null || entry >= b.Efc.Entries.Count) return "";
            var e = b.Efc.Entries[entry];
            var parts = new List<string>();
            if (e.Set > 0 && b.Ptcl != null && e.Set - 1 < b.Ptcl.Sets.Count) parts.Add(b.Ptcl.Sets[(int)e.Set - 1].Name);
            if (e.Model > 0 && e.Model - 1 < b.Efc.Models.Count) parts.Add("model " + b.Efc.Models[(int)e.Model - 1]);
            return string.Join(" + ", parts.ToArray());
        }

        /// <summary>How long a one-shot effect plays, in frames: the latest emitter's end (start + emission (one-time
        /// emitters) + particle life) of its .ptcl set; null when the set never stops by itself, has no emitters, or the
        /// files aren't there.</summary>
        public int? Lifetime(uint id)
        {
            int bank = (int)(id >> 16), entry = (int)(id & 0xFFFF);
            var b = bank == 0x100 ? null : GetBank(bank);
            if (b == null || b.Efc == null || b.Ptcl == null || entry >= b.Efc.Entries.Count) return null;
            int set = (int)b.Efc.Entries[entry].Set - 1;
            if (set < 0 || set >= b.Ptcl.Sets.Count) return null;
            return b.Ptcl.Sets[set].Lifetime();
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
        public int NamePos, TexPos, TexSize, KeyAnimPos, KeyAnimSize, PrimPos, PrimSize;
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
        }

        public class EmitterSet
        {
            public string Name;
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
            KeyAnimPos = BE.I32(d, 0x24); KeyAnimSize = BE.I32(d, 0x28); PrimPos = BE.I32(d, 0x2C); PrimSize = BE.I32(d, 0x30);
            for (int i = 0; i < nsets && 0x48 + 0x1C * i + 0x1C <= d.Length; i++)
            {
                int o = 0x48 + 0x1C * i;
                var s = new EmitterSet { Name = NameAt(BE.I32(d, o + 8)) };
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
