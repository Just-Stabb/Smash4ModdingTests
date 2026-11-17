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
    /// state: default.mta's frame 0 (else the Wait1 file's, else the first file's).
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
            // (v1.6.3: the model's own default.mta first, as the game's neutral state)
            var wait = v.byMotion.Keys.FirstOrDefault(k => k.Equals("default.mta", StringComparison.OrdinalIgnoreCase)) ??
                       v.byMotion.Keys.FirstOrDefault(k => k.EndsWith("Wait1.mta", StringComparison.OrdinalIgnoreCase)) ?? v.byMotion.Keys.FirstOrDefault();
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
    /// A group with lines hides the meshes it lists under other states than its current one, and shows those of its
    /// current state unless the motion's visibility animation hides them (v1.6.3). v1.6.3: also each fighter's defaults,
    /// <c>fighter hide: mesh</c> / <c>fighter show: mesh</c>, below the groups and the visibility animations; the
    /// user's own (VisUser.txt, written by the Model parts tab's right-click menu) over the shipped ones.
    /// </summary>
    public class VisGroups
    {
        public class Group { public Dictionary<int, List<string>> States = new Dictionary<int, List<string>>(); public int? Default; }
        public readonly Dictionary<string, Dictionary<int, Group>> Fighters = new Dictionary<string, Dictionary<int, Group>>(StringComparer.OrdinalIgnoreCase);
        /// <summary>v1.6.3: a fighter's meshes hidden / shown by default (<c>fighter hide: mesh, mesh</c> /
        /// <c>fighter show: mesh</c>): fighter -> mesh name or beginning -> shown, and where the line came from.</summary>
        public readonly Dictionary<string, Dictionary<string, bool>> Defaults = new Dictionary<string, Dictionary<string, bool>>(StringComparer.OrdinalIgnoreCase);
        public readonly Dictionary<string, Dictionary<string, bool>> UserDefaults = new Dictionary<string, Dictionary<string, bool>>(StringComparer.OrdinalIgnoreCase);
        /// <summary>The user's file (VisUser.txt next to the program: the Model parts tab's "by default" choices).</summary>
        public string UserPath;

        public static VisGroups Load(string path, string userPath = null)
        {
            var g = new VisGroups { UserPath = userPath };
            if (path != null && File.Exists(path)) foreach (var raw in File.ReadAllLines(path)) g.AddLine(raw);
            if (userPath != null && File.Exists(userPath))
                try { foreach (var raw in File.ReadAllLines(userPath)) g.AddLine(raw, true); } catch (Exception) { }
            return g;
        }

        public void AddLine(string raw, bool user = false)
        {
            string line = raw.Split(new[] { "//" }, StringSplitOptions.None)[0].Trim();
            int colon = line.IndexOf(':');
            if (colon < 0) return;
            var head = line.Substring(0, colon).Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            string rest = line.Substring(colon + 1).Trim();
            var list = rest.Split(',').Select(x => x.Trim()).Where(x => x.Length > 0).ToList();
            if (head.Length == 2 && (head[1].Equals("hide", StringComparison.OrdinalIgnoreCase) || head[1].Equals("show", StringComparison.OrdinalIgnoreCase)))
            {
                var all = user ? UserDefaults : Defaults;
                Dictionary<string, bool> d;
                if (!all.TryGetValue(head[0], out d)) all[head[0]] = d = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
                foreach (var m in list) d[m] = head[1].Equals("show", StringComparison.OrdinalIgnoreCase);
                return;
            }
            if (head.Length != 3 || user) return;
            int group;
            if (!int.TryParse(head[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out group)) return;
            Dictionary<int, Group> f;
            if (!Fighters.TryGetValue(head[0], out f)) Fighters[head[0]] = f = new Dictionary<int, Group>();
            Group gr;
            if (!f.TryGetValue(group, out gr)) f[group] = gr = new Group();
            int state;
            if (head[2].Equals("default", StringComparison.OrdinalIgnoreCase))
            {
                if (int.TryParse(rest, NumberStyles.Integer, CultureInfo.InvariantCulture, out state)) gr.Default = state;
                return;
            }
            if (!int.TryParse(head[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out state)) return;
            gr.States[state] = list;
        }

        static bool Matches(string mesh, string pattern) { return mesh.StartsWith(pattern, StringComparison.OrdinalIgnoreCase); }

        /// <summary>
        /// What a group of this fighter says about a mesh: true, its state (the script's, else the group's default)
        /// lists it (shown, unless the motion's visibility animation hides it); false, the group lists it under other
        /// states only (hidden); null, no group lists it or none has a state yet. why: the group and state.
        /// </summary>
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

        /// <summary>A fighter's default for a mesh (VisUser.txt's over VisGroups.txt's; the longest matching name), or
        /// null.</summary>
        public bool? DefaultFor(string fighter, string mesh, out string why)
        {
            why = null;
            foreach (var src in new[] { UserDefaults, Defaults })
            {
                Dictionary<string, bool> d;
                if (fighter == null || !src.TryGetValue(fighter, out d)) continue;
                var best = d.Where(kv => Matches(mesh, kv.Key)).OrderByDescending(kv => kv.Key.Length).Select(kv => (KeyValuePair<string, bool>?)kv).FirstOrDefault();
                if (best == null) continue;
                why = (best.Value.Value ? "visible" : "hidden") + " by default (" + (src == UserDefaults ? "your choice, VisUser.txt" : "VisGroups.txt") + ")";
                return best.Value.Value;
            }
            return null;
        }

        /// <summary>v1.6.3: saves the user's default for a mesh (true visible, false hidden, null: back to the shipped
        /// rules) in VisUser.txt, keeping the file's other lines. Returns false when it can't be written.</summary>
        public bool SetUserDefault(string fighter, string mesh, bool? shown)
        {
            Dictionary<string, bool> d;
            if (!UserDefaults.TryGetValue(fighter, out d)) UserDefaults[fighter] = d = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
            if (shown.HasValue) d[mesh] = shown.Value; else d.Remove(mesh);
            if (UserPath == null) return false;
            try
            {
                var lines = new List<string> {
                    "// Sm4shCommand Hitbox Viewer: your Model parts defaults (right-click a part: \"Hidden by default for this",
                    "// fighter\" / \"Visible by default\" / \"Follow the script / default\"). Same format as VisGroups.txt's",
                    "// defaults: fighter hide: mesh, mesh / fighter show: mesh (mesh names or their beginnings). These win over",
                    "// VisGroups.txt's defaults; a script's visibility group still shows / hides the mesh on its frames." };
                foreach (var f in UserDefaults.OrderBy(x => x.Key, StringComparer.OrdinalIgnoreCase))
                {
                    var hide = f.Value.Where(x => !x.Value).Select(x => x.Key).OrderBy(x => x).ToList();
                    var show = f.Value.Where(x => x.Value).Select(x => x.Key).OrderBy(x => x).ToList();
                    if (hide.Count > 0) lines.Add(f.Key + " hide: " + string.Join(", ", hide.ToArray()));
                    if (show.Count > 0) lines.Add(f.Key + " show: " + string.Join(", ", show.ToArray()));
                }
                File.WriteAllLines(UserPath, lines.ToArray());
                return true;
            }
            catch (Exception) { return false; }
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
        // (v1.6.3: Apply's order: your choice now; a group hiding the mesh; the motion's visibility animation; a group
        // showing it; the fighter's defaults, yours (VisUser.txt) over VisGroups.txt's; the name rule)
        /// <summary>Sets every mesh's Visible and Why for this frame. user: mesh name -> shown (the parts tab's
        /// overrides).</summary>
        public static void Apply(FighterAssets a, string animFile, float frame, VisState vis, VisGroups groups,
                                 IDictionary<string, bool> user)
        {
            if (a == null || a.Model == null) return;
            var anim = a.MaterialVis != null ? a.MaterialVis.At(animFile, frame) : new Dictionary<string, bool>();
            int index = -1;
            foreach (var m in a.Model.Meshes)
            {
                bool v;
                string why = "";
                index++;
                bool? mv = vis != null ? vis.MeshOverride(m.Name, index) : null;
                if (user != null && user.TryGetValue(m.Name, out v)) why = "your choice (now)";
                else if (mv.HasValue) { v = mv.Value; why = (v ? "shown" : "hidden") + " by Mesh_Visibility (script)"; }
                else
                {
                    // v1.6.3: a group whose state lists the mesh lets the motion's visibility animation decide, then
                    // shows it (it used to show it over the animation); a group listing it under other states hides it
                    string gwhy = null, dwhy = null;
                    var g = groups != null ? groups.Decide(a.Name, m.Name, vis, out gwhy) : null;
                    var d = groups != null ? groups.DefaultFor(a.Name, m.Name, out dwhy) : null;
                    if (g == false) { v = false; why = gwhy; }
                    else if (anim.TryGetValue(MaterialVis.VisName(m.Name), out v))
                        why = "visibility animation (material_anime)";
                    else if (g == true) { v = true; why = gwhy; }
                    else if (d.HasValue) { v = d.Value; why = dwhy; }
                    else { v = m.DefaultVisible; why = v ? "default" : "default (expression variant)"; }
                }
                m.Visible = v;
                m.Why = why;
            }
        }
    }
}

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// v1.6.3: the Model parts tab's right-click menu. "Show / Hide now": this session's choice (gone when the program
    /// closes). "Hidden / Visible by default for this fighter": saved in VisUser.txt (next to the program) as the
    /// fighter's default, so the script's groups still show / hide it on their frames; it clears the "now" choice.
    /// "Follow the script / default": takes both away. "Isolate": shows only the picked meshes now.
    /// Held-model meshes ("held: ...") take the "now" choices only.
    /// </summary>
    public static class PartsMenu
    {
        public static void Now(IDictionary<string, bool> user, IEnumerable<string> meshes, bool shown)
        {
            foreach (var m in meshes) user[m] = shown;
        }

        /// <summary>Returns false when VisUser.txt couldn't be written (the choice still holds this session).</summary>
        public static bool Default(VisGroups groups, IDictionary<string, bool> user, string fighter, IEnumerable<string> meshes, bool? shown)
        {
            bool ok = true;
            foreach (var m in meshes)
            {
                user.Remove(m);
                if (m.StartsWith("held: ", StringComparison.Ordinal) || fighter == null) continue;
                ok &= groups.SetUserDefault(fighter, m, shown);
            }
            return ok;
        }

        public static void Isolate(IDictionary<string, bool> user, IEnumerable<string> all, IList<string> keep)
        {
            foreach (var m in all) user[m] = keep.Contains(m);
        }
    }
}
