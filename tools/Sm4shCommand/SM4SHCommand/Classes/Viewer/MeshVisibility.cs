using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// v1.6.2: which of a fighter's meshes the game shows on a motion's frame, from the model folder's own visibility
    /// animations: material_anime_face / _eye / _eyelid.pac (KCAP packs of MTA4 files, one per motion:
    /// FitMarioBodyMainC00AttackDash.mta), whose visibility tracks switch the _VIS_O_OBJ meshes key by key (Mario's
    /// FaceN / Ouch / Blink / Nohat ..., Kirby's eyes and big body, Pac-Man's ...). A motion without one keeps the neutral
    /// state: the Wait1 file's frame 0 (else the first file's).
    /// </summary>
    public class MaterialVis
    {
        class Track { public string Mesh; public int[] Frames; public bool[] On; }
        readonly Dictionary<string, List<Track>> byMotion = new Dictionary<string, List<Track>>(StringComparer.OrdinalIgnoreCase);
        public readonly Dictionary<string, bool> Baseline = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
        public readonly HashSet<string> Meshes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        public int Files;

        public static readonly string[] Packs = { "material_anime_face.pac", "material_anime_eye.pac", "material_anime_eyelid.pac" };

        public static MaterialVis Load(string modelDir)
        {
            var v = new MaterialVis();
            if (modelDir == null) return v;
            foreach (var name in Packs)
            {
                string path = Path.Combine(modelDir, name);
                if (!File.Exists(path)) continue;
                Dictionary<string, byte[]> files;
                try { files = Pac.Load(path); } catch (Exception) { continue; }
                foreach (var kv in files)
                {
                    if (!kv.Key.EndsWith(".mta", StringComparison.OrdinalIgnoreCase)) continue;
                    List<Track> tracks;
                    try { tracks = ReadVis(kv.Value); } catch (Exception) { continue; }
                    if (tracks.Count == 0) continue;
                    v.Files++;
                    List<Track> list;
                    if (!v.byMotion.TryGetValue(kv.Key, out list)) v.byMotion[kv.Key] = list = new List<Track>();
                    list.AddRange(tracks);
                    foreach (var t in tracks) v.Meshes.Add(t.Mesh);
                }
            }
            // the neutral state: Wait1's frame 0 (the first motion's when there's no Wait1)
            var wait = v.byMotion.Keys.FirstOrDefault(k => k.EndsWith("Wait1.mta", StringComparison.OrdinalIgnoreCase)) ?? v.byMotion.Keys.FirstOrDefault();
            if (wait != null)
                foreach (var t in v.byMotion[wait]) v.Baseline[t.Mesh] = t.On.Length > 0 && t.On[0];
            return v;
        }

        /// <summary>An MTA4's visibility tracks (tools/mta.py read: after the materials, a table of entry offsets; an entry:
        /// name offset, 0, data offset; data: frames - 1, u16 1, u16 key count, key offset; keys: u16 frame, u8 0 / 1, 0).</summary>
        static List<Track> ReadVis(byte[] d)
        {
            var o = new List<Track>();
            if (d.Length < 0x28 || Encoding.ASCII.GetString(d, 0, 4) != "MTA4") return o;
            int vc = BE.I32(d, 0x20), vo = BE.I32(d, 0x24);
            for (int i = 0; i < vc && vo + 4 * i + 4 <= d.Length; i++)
            {
                int e = BE.I32(d, vo + 4 * i);
                string name = BE.CStr(d, BE.I32(d, e));
                int dof = BE.I32(d, e + 8);
                int kc = BE.I16(d, dof + 6), ko = BE.I32(d, dof + 8);
                var t = new Track { Mesh = name, Frames = new int[Math.Max(0, kc)], On = new bool[Math.Max(0, kc)] };
                for (int k = 0; k < kc && ko + 4 * k + 3 <= d.Length; k++)
                {
                    t.Frames[k] = BE.I16(d, ko + 4 * k);
                    t.On[k] = d[ko + 4 * k + 2] != 0;
                }
                o.Add(t);
            }
            return o;
        }

        /// <summary>The meshes these animations switch, on an animation's frame: the neutral state, then the motion's own
        /// tracks (each the last key at or before the frame). animFile: the motion's .omo name (its .mta has the same).</summary>
        public Dictionary<string, bool> At(string animFile, float frame)
        {
            var o = new Dictionary<string, bool>(Baseline, StringComparer.OrdinalIgnoreCase);
            if (animFile == null) return o;
            List<Track> list;
            if (!byMotion.TryGetValue(Path.ChangeExtension(animFile, ".mta"), out list)) return o;
            foreach (var t in list)
            {
                if (t.Frames.Length == 0) continue;
                bool on = t.On[0];
                for (int k = 0; k < t.Frames.Length; k++)
                    if (t.Frames[k] <= frame + 1e-3f) on = t.On[k];
                o[t.Mesh] = on;
            }
            return o;
        }

        /// <summary>A NUD mesh's name as the visibility tracks name it: up to its _VIS_O_OBJ (the rest are draw flags:
        /// Reflet_Blink_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE is Reflet_Blink_VIS_O_OBJ).</summary>
        public static string VisName(string mesh)
        {
            int i = mesh.IndexOf("_VIS_O_OBJ", StringComparison.OrdinalIgnoreCase);
            return i >= 0 ? mesh.Substring(0, i + 10) : mesh;
        }
    }

    /// <summary>
    /// v1.6.2: the visibility groups' meshes (Model_Changer / VIS_SET_DEFAULT / VIS_BACK_DEFAULT group, state), from
    /// VisGroups.txt next to the exe. The game keeps them in its code (the VisibilityModule's table: per group, per state
    /// the meshes it shows), not in the fighter's files, so they're listed by hand: one line per state,
    /// <c>fighter group state: mesh, mesh</c> (mesh names or their beginnings, any case), and <c>fighter group default: state</c>.
    /// A group with lines shows the meshes of its current state and hides the others it lists.
    /// </summary>
    public class VisGroups
    {
        public class Group { public Dictionary<int, List<string>> States = new Dictionary<int, List<string>>(); public int? Default; }
        public readonly Dictionary<string, Dictionary<int, Group>> Fighters = new Dictionary<string, Dictionary<int, Group>>(StringComparer.OrdinalIgnoreCase);

        public static VisGroups Load(string path)
        {
            var g = new VisGroups();
            if (path == null || !File.Exists(path)) return g;
            foreach (var raw in File.ReadAllLines(path)) g.AddLine(raw);
            return g;
        }

        public void AddLine(string raw)
        {
            string line = raw.Split(new[] { "//" }, StringSplitOptions.None)[0].Trim();
            int colon = line.IndexOf(':');
            if (colon < 0) return;
            var head = line.Substring(0, colon).Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (head.Length != 3) return;
            int group;
            if (!int.TryParse(head[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out group)) return;
            Dictionary<int, Group> f;
            if (!Fighters.TryGetValue(head[0], out f)) Fighters[head[0]] = f = new Dictionary<int, Group>();
            Group gr;
            if (!f.TryGetValue(group, out gr)) f[group] = gr = new Group();
            string rest = line.Substring(colon + 1).Trim();
            int state;
            if (head[2].Equals("default", StringComparison.OrdinalIgnoreCase))
            {
                if (int.TryParse(rest, NumberStyles.Integer, CultureInfo.InvariantCulture, out state)) gr.Default = state;
                return;
            }
            if (!int.TryParse(head[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out state)) return;
            gr.States[state] = rest.Split(',').Select(x => x.Trim()).Where(x => x.Length > 0).ToList();
        }

        static bool Matches(string mesh, string pattern) { return mesh.StartsWith(pattern, StringComparison.OrdinalIgnoreCase); }

        /// <summary>Whether a group of this fighter decides a mesh: shown / hidden by its state (the script's, else the
        /// group's default; a group no script set and with no default decides nothing), and why. Null: no group lists it.</summary>
        public bool? Decide(string fighter, string mesh, VisState vis, out string why)
        {
            why = null;
            Dictionary<int, Group> f;
            if (fighter == null || !Fighters.TryGetValue(fighter, out f)) return null;
            foreach (var kv in f)
            {
                var gr = kv.Value;
                if (!gr.States.Values.Any(l => l.Any(p => Matches(mesh, p)))) continue;
                int state;
                if (vis != null && vis.Groups.TryGetValue(kv.Key, out state)) why = "group " + kv.Key + " state " + state + " (script)";
                else if (gr.Default.HasValue) { state = gr.Default.Value; why = "group " + kv.Key + " default " + state; }
                else continue;
                List<string> on;
                return gr.States.TryGetValue(state, out on) && on.Any(p => Matches(mesh, p));
            }
            return null;
        }
    }
}

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// v1.6.2: the meshes shown on a frame, by priority: the user's choice in the Model parts tab; a visibility group
    /// (VisGroups.txt) at the script's state; the model's visibility animation for the motion (MaterialVis); the name
    /// rule's default (expression variants hidden). The script's Visibility(State=0) hides the whole model.
    /// </summary>
    public static class ModelParts
    {
        /// <summary>Sets every mesh's Visible and Why for this frame. user: mesh name -> shown (the parts tab's
        /// overrides).</summary>
        public static void Apply(FighterAssets a, string animFile, float frame, VisState vis, VisGroups groups,
                                 IDictionary<string, bool> user)
        {
            if (a == null || a.Model == null) return;
            var anim = a.MaterialVis != null ? a.MaterialVis.At(animFile, frame) : new Dictionary<string, bool>();
            foreach (var m in a.Model.Meshes)
            {
                bool v;
                string why = "";
                if (user != null && user.TryGetValue(m.Name, out v)) why = "your choice";
                else
                {
                    var g = groups != null ? groups.Decide(a.Name, m.Name, vis, out why) : null;
                    if (g.HasValue) v = g.Value;
                    else if (anim.TryGetValue(MaterialVis.VisName(m.Name), out v))
                        why = "visibility animation (material_anime)";
                    else { v = m.DefaultVisible; why = v ? "default" : "default (expression variant)"; }
                }
                m.Visible = v;
                m.Why = why;
            }
        }
    }
}
