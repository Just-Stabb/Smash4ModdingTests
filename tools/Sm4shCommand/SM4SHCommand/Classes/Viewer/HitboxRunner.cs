using System;
using System.Collections.Generic;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;

namespace Sm4shCommand.Viewer
{
    /// <summary>A hitbox as an ACMD command creates it.</summary>
    public class HitboxData
    {
        public int Id, Part, Bone, Angle, KBG, WBKB, BKB, Effect, ShieldDamage, Line;
        public float Damage, Size, X, Y, Z, X2, Y2, Z2, Hitlag = 1, SDI = 1;
        public bool Extended, Windbox, Special;
        public string Command;
        public string Script = "game";      // (v1.7.2) the script that made it: game, effect, sound or expression
        // Extra_Special_Hitbox / Extra_Extended_Special_Hitbox's six extras (docs/acmd-extra-commands.md):
        // multipliers of 0 or less are x1, frames of 0 are "computed"
        public bool HasExtras;
        public float HitstunMul, HitstopMul, SelfHitstopMul, DIMul;
        public int HitstopFrames, SelfHitstopFrames;
        // fields that take a variable (exe_v43): "Angle=STICK_ANGLE|FOLLOW = 0" (the value used here: the script's
        // last SET_FLOAT of it, else a stand-in)
        public string VarsText = "";

        public HitboxData Clone() { return (HitboxData)MemberwiseClone(); }

        /// <summary>Electric hitboxes (effect 3) add hitlag and hitstun.</summary>
        public bool Electric { get { return Effect == 3; } }

        static float Mul(float m) { return m > 0 ? m : 1; }
        public float HitstunMultiplier { get { return HasExtras ? Mul(HitstunMul) : 1; } }
        public float HitstopMultiplier { get { return HasExtras ? Mul(HitstopMul) : 1; } }
        public float SelfHitstopMultiplier { get { return HasExtras ? Mul(SelfHitstopMul) : 1; } }
        public float DIMultiplier { get { return HasExtras ? Mul(DIMul) : 1; } }

        /// <summary>The extras that change anything, for the list ("" when none).</summary>
        public string ExtrasText
        {
            get
            {
                if (!HasExtras) return "";
                var ic = System.Globalization.CultureInfo.InvariantCulture;
                var o = new List<string>();
                if (HitstunMultiplier != 1) o.Add("hitstun x" + HitstunMultiplier.ToString("0.###", ic));
                if (HitstopFrames > 0) o.Add("hitstop " + HitstopFrames + "f");
                else if (HitstopMultiplier != 1) o.Add("hitstop x" + HitstopMultiplier.ToString("0.###", ic));
                if (SelfHitstopFrames > 0) o.Add("self hitstop " + SelfHitstopFrames + "f");
                else if (SelfHitstopMultiplier != 1) o.Add("self hitstop x" + SelfHitstopMultiplier.ToString("0.###", ic));
                if (DIMultiplier != 1) o.Add("DI x" + DIMultiplier.ToString("0.###", ic));
                if (VarsText.Length > 0) o.Add(VarsText);
                return string.Join(", ", o.ToArray());
            }
        }
    }

    /// <summary>A SET_FLOAT the script does to a variable (e.g. LASTHIT_HITSTUN_MUL), and on which game frame.</summary>
    public class VarWrite
    {
        public int GameFrame;
        public uint Variable;
        public float Value;
    }

    /// <summary>The script's state on one in-game frame.</summary>
    public class FrameState
    {
        public int GameFrame;
        public float AnimFrame;          // the animation frame shown on this game frame
        public List<HitboxData> Hitboxes = new List<HitboxData>();
        public bool Intangible, Invincible, SuperArmor;
        public List<VarWrite> Writes = new List<VarWrite>();   // SET_FLOATs done on this frame
        public double Speed = 1;                                // the animation frames this game frame moved on
        // the effect script's, on the same timeline (v1.5.0): the effects on now, the sword trails, the screen
        // events of this frame
        public List<EffectData> Effects = new List<EffectData>();
        public List<TrailData> Trails = new List<TrailData>();
        public List<ScreenEvent> Screen = new List<ScreenEvent>();
        // v1.6.2: the body colour overlay on this frame (r g b a, 0-1; null: none; OverlayLight: a flash light, added) and
        // the visibility groups' states (Model_Changer & co.)
        public float[] Overlay;
        public bool OverlayLight;
        public VisState Vis = new VisState();
    }

    /// <summary>v1.6.2: a script's visibility state: each group's state (Model_Changer / VIS_SET_DEFAULT ...), the defaults
    /// it set, the whole model's visibility (Visibility; null: as is), the frame each last changed and the commands.</summary>
    public class VisState
    {
        public Dictionary<int, int> Groups = new Dictionary<int, int>(), Defaults = new Dictionary<int, int>(), Changed = new Dictionary<int, int>();
        public bool? Whole;
        public List<ScreenEvent> Events = new List<ScreenEvent>();
        public VisState Clone()
        {
            return new VisState { Groups = new Dictionary<int, int>(Groups), Defaults = new Dictionary<int, int>(Defaults),
                                  Changed = new Dictionary<int, int>(Changed), Whole = Whole, Events = new List<ScreenEvent>(Events) };
        }

        /// <summary>Two scripts' states (the game script's and the expression script's) as one: per group the one changed
        /// last.</summary>
        public static VisState Merge(VisState a, VisState b)
        {
            if (a == null) return b; if (b == null) return a;
            var o = a.Clone();
            foreach (var kv in b.Changed)
            {
                int ca;
                if (o.Changed.TryGetValue(kv.Key, out ca) && ca > kv.Value) continue;
                o.Changed[kv.Key] = kv.Value;
                if (kv.Key == -1) o.Whole = b.Whole;
                else if (b.Groups.ContainsKey(kv.Key)) o.Groups[kv.Key] = b.Groups[kv.Key];
                else o.Groups.Remove(kv.Key);
            }
            foreach (var kv in b.Defaults) o.Defaults[kv.Key] = kv.Value;
            o.Events.AddRange(b.Events);
            return o;
        }
    }

    /// <summary>v1.6.2: the body colour overlay over time: set at once, or changed over a transition (Change_Overlay).</summary>
    public class OverlayState
    {
        float[] from, to;
        int start, frames;
        public bool Light;

        public void Set(int frame, float[] c, int transition)
        {
            var now = At(frame);
            from = transition > 0 ? (now ?? (c == null ? null : new[] { c[0], c[1], c[2], 0f })) : c;
            to = c; start = frame; frames = transition;
        }

        public float[] At(int frame)
        {
            if (to == null && (frames <= 0 || from == null)) return null;
            if (frames <= 0 || frame >= start + frames || from == null) return to == null ? null : (float[])to.Clone();
            float t = Math.Max(0, Math.Min(1, (frame - start) / (float)frames));
            var a = from; var b = to ?? new[] { from[0], from[1], from[2], 0f };
            return new[] { a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t };
        }
    }

    /// <summary>
    /// Runs a game (ACMD) script frame by frame the way the game times it, following Smash Forge's
    /// ACMDScript.cs (MIT): FRAME / WAIT timers in animation frames, Set_Frame_Duration and
    /// Frame_Speed_Multiplier, hitbox creation / deletion / changes, loops, subroutines (JUMP / CALL)
    /// and if blocks (conditions it can't know are taken as <see cref="ConditionsTrue"/>).
    /// </summary>
    public class HitboxRunner
    {
        public bool ConditionsTrue = true;
        public bool UseFrameSpeed = true;
        public Func<uint, IList<ICommand>> GetScript;
        /// <summary>v1.5.0, the effect script: the game script's per-frame speeds (FrameState.Speed), so it runs on the
        /// game script's timeline (its Set_Frame_Duration changes the motion's rate, which every script follows).</summary>
        public double[] SpeedSchedule;
        /// <summary>A one-shot effect's play time in frames: &gt; 0 that long, 0 not known (DefaultLife), -1 never ends by
        /// itself (on until terminated).</summary>
        public Func<uint, int> OneShotLife;
        public int DefaultLife = 20;
        /// <summary>(v1.7.2) The script this runner runs ("game" for the one Run is given): the hitboxes / effects it makes
        /// carry it.</summary>
        public string Kind = "game";

        /// <summary>(v1.7.2) One of the move's other scripts: its kind (effect, sound, expression), its commands and where
        /// its CALL / JUMP targets come from (its own file).</summary>
        public class ScriptSource
        {
            public string Kind;
            public IList<ICommand> Commands;
            public Func<uint, IList<ICommand>> GetScript;
        }

        /// <summary>
        /// (v1.7.2) The move's other scripts, run with the one Run is given, as the game runs them: every frame each of the
        /// motion's four ACMD scripts (game, effect, sound, expression, in that order) goes on from where it stopped, each
        /// with its own frame cursor (FRAME / WAIT timers, loops, If / Else blocks, CALLs, Thread_Start), all on the
        /// motion's frame rate (Set_Frame_Duration / Frame_Speed_Multiplier / the rate variable, from whichever script sets
        /// it); any command works in any of them, so a hitbox, a body state, an effect, a trail, an overlay or a
        /// visibility command in the effect / sound / expression script is the move's as much as one in game.bin (they share
        /// the hitboxes, the variables, the effects and the body state). Up to v1.7.1 the viewer took hitboxes from the game
        /// script only and effects from the effect script only (the game script's were dropped when the move had an effect
        /// script, the sound script's never run).
        /// </summary>
        public List<ScriptSource> Others = new List<ScriptSource>();
        readonly List<HitboxRunner> parallel = new List<HitboxRunner>();
        bool isParallel;
        double frameSpeedNow = 1;       // the motion's rate this game frame (the parallel scripts' step)

        const uint ASYNC = 0x42ACFE7D, SYNC = 0x4B7B6E51, FRAME_DURATION = 0x7172A764, FRAME_DURATION2 = 0xB2E91D0C,
            FRAME_MUL = 0xA546845C, CALL1 = 0x9126EBA2, CALL2 = 0xFA1BC28A, HITBOX = 0xB738EABD,
            EXT_HITBOX = 0x2988D50F, SPECIAL = 0x14FCC7E4, EXT_SPECIAL = 0x7075DC5A, COLLATERAL = 0xCC7CC705,
            EXTRA_SPECIAL = 0x974EA5BE, EXTRA_EXT_SPECIAL = 0x5C8A67C9,
            EXT_COLLATERAL = 0xED67D5DA, CLEAR = 0x9245E1A8, DELETE = 0xFF379EB6, DEACTIVATE_LAST = 0x7698BB42,
            SIZE = 0x684264C9, DAMAGE = 0xDFA4517A, MOVE = 0x1AFDA8E6, SET_LOOP = 0x0EB375E3, GOTO = 0x38A3EC78,
            BODY = 0xF0D25BDA, SET_FLOAT = 0x1E3AB92A, ANIM_RATE = 0x0F000098, ARMOR = 0x2A25155D, TRUE = 0xA5BD4F32, ELSE = 0x895B9275, FALSE = 0x870CF021, END = 0x5766F889,
            THREAD_START = 0x4C0DBE48, THREAD_STOP = 0x1B492AD1;

        IList<ICommand> script;
        readonly List<IList<ICommand>> subscripts = new List<IList<ICommand>>();
        readonly Stack<int[]> states = new Stack<int[]>();
        int index, loopStart, loopIterations, skipWords;
        double currentFrame, animFrame, frameSpeed, syncFrames, rate;
        int gameFrame;
        List<VarWrite> writes = new List<VarWrite>();
        Dictionary<uint, float> varValues = new Dictionary<uint, float>();   // SET_FLOATs so far (threads share them)
        // v1.6.2: the body overlay and the visibility groups as the script sets them (threads share the root's)
        OverlayState overlay = new OverlayState();
        VisState vis = new VisState();
        // what a variable in an Extra hitbox is drawn with when the script doesn't SET_FLOAT it first
        static readonly float[] VarStandIn = { 10, 0, 100, 0, 40, 4 };
        double Speed
        {
            get
            {
                if (isParallel) return root.frameSpeedNow;      // (v1.7.2) the motion's rate this frame, as the game script's
                var sched = (root ?? this).SpeedSchedule;
                int g = (root ?? this).gameFrame - 1;
                if (sched != null && !isThread && g >= 0 && g < sched.Length) return sched[g];
                return frameSpeed * rate;     // the move's frame speed x the animation rate variable
            }
        }
        bool incrementFrame;
        SortedDictionary<int, HitboxData> hitboxes = new SortedDictionary<int, HitboxData>();
        bool intangible, invincible, armor;

        // Thread_Start(Offset, ID, Flags){ ... } (docs/acmd-extra-commands.md): the block runs on its own, from the
        // game frame after Thread_Start, one frame per game frame (FRAME counted from 0 there), sharing the
        // hitboxes, while the script goes on past it. Thread_Stop(ID) / (-1) stops them.
        class ScriptThread
        {
            public int Id, StartFrame;
            public HitboxRunner Runner;
            public bool First = true;
        }
        readonly List<ScriptThread> threads = new List<ScriptThread>();
        HitboxRunner root;
        bool isThread;

        void StartThread(int id, IList<ICommand> block)
        {
            var r = root ?? this;
            r.threads.RemoveAll(x => x.Id == id);
            var th = new HitboxRunner { ConditionsTrue = ConditionsTrue, UseFrameSpeed = false, GetScript = GetScript, Kind = Kind };
            th.isThread = true;
            th.root = r;
            th.hitboxes = r.hitboxes;
            th.varValues = r.varValues;
            th.overlay = r.overlay;
            th.vis = r.vis;
            th.fx = r.fx;
            th.script = block;
            th.frameSpeed = 1; th.rate = 1; th.syncFrames = -1;
            r.threads.Add(new ScriptThread { Id = id, StartFrame = r.gameFrame, Runner = th });
        }

        /// <summary>One game frame of every thread started before this frame; ended ones are dropped.</summary>
        void StepThreads()
        {
            foreach (var th in threads.ToArray())
            {
                if (th.StartFrame >= gameFrame || !threads.Contains(th))
                    continue;
                var r = th.Runner;
                if (th.First) { r.currentFrame = 0; th.First = false; }
                else r.currentFrame += 1;
                r.gameFrame = gameFrame;
                r.writes = writes;
                bool i0 = r.intangible, v0 = r.invincible, a0 = r.armor;
                r.ProcessFrame();
                if (r.intangible != i0) intangible = r.intangible;
                if (r.invincible != v0) invincible = r.invincible;
                if (r.armor != a0) armor = r.armor;
                if (r.index >= r.script.Count && r.subscripts.Count == 0)
                    threads.Remove(th);
            }
        }

        /// <summary>The block after a Thread_Start at index: its commands up to blockWords words, without the
        /// Script_End that ends it.</summary>
        static List<ICommand> ThreadBlock(IList<ICommand> list, int index, int blockWords)
        {
            var o = new List<ICommand>();
            int words = 0;
            for (int i = index + 1; i < list.Count && words < blockWords; i++)
            {
                var c = list[i] as ACMDCommand;
                int w = c != null ? c.Parameters.Count + 1 : 1;
                words += w;
                if (c != null && c.Ident == END && words >= blockWords)
                    break;
                o.Add(list[i]);
            }
            return o;
        }

        /// <summary>Runs the script for frames game frames (one FrameState each).</summary>
        public List<FrameState> Run(IList<ICommand> commands, int frames)
        {
            script = commands;
            subscripts.Clear(); states.Clear(); hitboxes.Clear(); threads.Clear(); varValues.Clear();
            fx = new EffectState();
            overlay = new OverlayState();
            vis = new VisState();
            index = 0; loopStart = 0; loopIterations = 0; skipWords = 0;
            currentFrame = 0; animFrame = 0; frameSpeed = 1; syncFrames = -1; rate = 1;
            incrementFrame = true;
            intangible = invincible = armor = false;
            // (v1.7.2) the other scripts: their own cursors, the shared state
            parallel.Clear();
            foreach (var o in Others)
            {
                if (o == null || o.Commands == null) continue;
                var pr = new HitboxRunner { ConditionsTrue = ConditionsTrue, UseFrameSpeed = UseFrameSpeed, GetScript = o.GetScript, Kind = o.Kind };
                pr.isParallel = true;
                pr.root = this;
                pr.hitboxes = hitboxes;
                pr.varValues = varValues;
                pr.overlay = overlay;
                pr.vis = vis;
                pr.fx = fx;
                pr.script = o.Commands;
                pr.frameSpeed = 1; pr.rate = 1; pr.syncFrames = -1;
                pr.incrementFrame = true;
                parallel.Add(pr);
            }
            var outList = new List<FrameState>();
            int guard = 0;
            for (int game = 0; game < frames; game++)
            {
                gameFrame = game + 1;
                writes = new List<VarWrite>();
                fx.Screen = new List<ScreenEvent>();
                double speedNow = Speed;
                frameSpeedNow = speedNow;
                if (incrementFrame)
                    currentFrame += Speed;
                animFrame += Speed;
                bool keep = true;
                while (keep && guard++ < 100000)
                {
                    keep = false;
                    ProcessFrame();
                    if (currentFrame < 1)     // the game's first-frame handling (Forge)
                    {
                        currentFrame += Speed;
                        if (currentFrame > 1)
                            incrementFrame = false;
                        else
                        {
                            incrementFrame = true;
                            keep = true;
                        }
                    }
                    else
                        incrementFrame = true;
                }
                foreach (var pr in parallel)
                    StepParallel(pr, ref guard);
                StepThreads();
                var st = new FrameState
                {
                    GameFrame = game + 1,
                    AnimFrame = (float)(animFrame - 1),
                    Intangible = intangible, Invincible = invincible, SuperArmor = armor, Writes = writes,
                    Speed = speedNow, Screen = fx.Screen,
                    Overlay = overlay.At(game + 1), OverlayLight = overlay.Light, Vis = vis.Clone(),
                };
                foreach (var h in hitboxes.Values)
                    st.Hitboxes.Add(h.Clone());
                ExpireEffects();
                // a trail shows to its end and its fade after it (Terminate_Sword_Glow's FadeTime)
                fx.Trails.RemoveAll(t => t.EndFrame >= 0 && gameFrame >= t.EndFrame + t.Fade);
                foreach (var e in fx.Live)
                    st.Effects.Add(e.Clone());
                foreach (var t in fx.Trails)
                    st.Trails.Add(t.Clone());
                outList.Add(st);
            }
            return outList;
        }

        /// <summary>(v1.7.2) One game frame of another of the move's scripts: its cursor moved on by the motion's rate
        /// (the game script's frame start rate, frameSpeedNow) and its commands run up to its next timer, with the game's
        /// first-frame handling (as Run does for the game script); its body state changes become the move's.</summary>
        void StepParallel(HitboxRunner pr, ref int guard)
        {
            pr.gameFrame = gameFrame;
            pr.writes = writes;
            pr.intangible = intangible; pr.invincible = invincible; pr.armor = armor;     // the move's body state so far
            bool ib = pr.intangible, vb = pr.invincible, ab = pr.armor;
            if (pr.incrementFrame)
                pr.currentFrame += frameSpeedNow;
            pr.animFrame = animFrame;
            bool keep = true;
            while (keep && guard++ < 100000)
            {
                keep = false;
                pr.ProcessFrame();
                if (pr.currentFrame < 1)
                {
                    pr.currentFrame += frameSpeedNow;
                    if (pr.currentFrame > 1)
                        pr.incrementFrame = false;
                    else
                    {
                        pr.incrementFrame = true;
                        keep = true;
                    }
                }
                else
                    pr.incrementFrame = true;
            }
            if (pr.intangible != ib) intangible = pr.intangible;
            if (pr.invincible != vb) invincible = pr.invincible;
            if (pr.armor != ab) armor = pr.armor;
        }

        IList<ICommand> Current { get { return subscripts.Count > 0 ? subscripts[subscripts.Count - 1] : script; } }

        void ProcessFrame()
        {
            int guard = 0;
            while (guard++ < 10000)
            {
                var list = Current;
                if (index >= list.Count)
                {
                    if (subscripts.Count == 0)
                        return;
                    var s = states.Pop();
                    index = s[0]; loopStart = s[1]; loopIterations = s[2];
                    subscripts.RemoveAt(subscripts.Count - 1);
                    index++;
                    continue;
                }
                if (!Process(list[index]))
                    return;
                index++;
            }
        }

        /// <summary>An Extra hitbox's fields that hold a variable: the value it would give (the script's last SET_FLOAT
        /// of it, else a stand-in), converted as the game does, facing right (ACMDCommand.HitboxVarValue).</summary>
        void HitboxVars(ACMDCommand cmd, IList<object> p, HitboxData h)
        {
            var ic = System.Globalization.CultureInfo.InvariantCulture;
            var o = new List<string>();
            for (int k = 0; k < ACMDCommand.HitboxVarCount; k++)
            {
                int i = ACMDCommand.HitboxVarFirst + k;
                if (i >= p.Count) break;
                uint w = ACMDCommand.ParamWord(p[i]);
                if (!ACMDCommand.IsHitboxVarWord(w)) continue;
                uint id = w & ~ACMDCommand.HitboxVarFlagMask;
                float v;
                bool known = varValues.TryGetValue(id & 0x0FFFFFFF, out v);
                if (!known) v = VarStandIn[k];
                float x = ACMDCommand.HitboxVarValue(k, w, v);
                switch (k)
                {
                    case 0: h.Damage = x; break;
                    case 1: h.Angle = (int)x; break;
                    case 2: h.KBG = (int)x; break;
                    case 3: h.WBKB = (int)x; break;
                    case 4: h.BKB = (int)x; break;
                    case 5: h.Size = x; break;
                }
                o.Add(string.Format(ic, "{0}={1} {2} {3}", ACMDCommand.HitboxVarFields[k], ACMDCommand.FormatHitboxVar(w),
                    known ? "=" : "drawn as", x.ToString("0.###", ic)));
            }
            h.VarsText = string.Join(", ", o.ToArray());
        }

        static int I(object o)
        {
            if (o is FighterVariable) return (int)((FighterVariable)o).Raw;
            try { return Convert.ToInt32(o); } catch { return 0; }
        }
        static float F(object o)
        {
            if (o is int || o is uint)      // an int parameter: a number, or float bits (> 0xFFFF)
            {
                int v = unchecked((int)Convert.ToInt64(o));
                return Math.Abs(v) <= 0xFFFF ? v : BitConverter.ToSingle(BitConverter.GetBytes(v), 0);
            }
            try { return Convert.ToSingle(o); } catch { return 0; }
        }
        static int ParamIndex(ACMDCommand c, string name, int fallback)
        {
            try
            {
                var syn = c.ParamSyntax;
                for (int i = 0; i < syn.Length; i++)
                    if (syn[i].Trim().Equals(name, StringComparison.OrdinalIgnoreCase))
                        return i;
            }
            catch { }
            return fallback;
        }

        bool Process(ICommand icmd)
        {
            var cmd = icmd as ACMDCommand;
            if (cmd == null)
                return true;
            var p = cmd.Parameters;
            if (skipWords > 0)     // inside a true / false block that isn't taken
            {
                skipWords -= p.Count + 1;
                return true;
            }
            switch (cmd.Ident)
            {
                case ASYNC:
                    {
                        double on = F(p[0]);
                        return Math.Abs(currentFrame - on) < 0.001 || currentFrame > on;
                    }
                case SYNC:
                    {
                        if (syncFrames < 0) syncFrames = 0;
                        else syncFrames += Speed;
                        double left = F(p[0]) - syncFrames;     // not rounded: WAIT(0.2) still takes a frame
                        if (Math.Abs(left) > 0.001 && left > 0)
                            return false;
                        syncFrames = -1;
                        return true;
                    }
                case FRAME_DURATION:
                case FRAME_DURATION2:
                    // (v1.7.2) from any of the move's scripts: the motion's rate, which every script follows (from the
                    // next frame on)
                    if (UseFrameSpeed && F(p[0]) != 0) (isParallel ? root : this).frameSpeed = 1 / F(p[0]);
                    break;
                case FRAME_MUL:
                    if (UseFrameSpeed) (isParallel ? root : this).frameSpeed = F(p[0]);
                    break;
                case CALL1:
                case CALL2:
                    {
                        var sub = GetScript != null ? GetScript((uint)I(p[0])) : null;
                        if (sub != null && subscripts.Count < 16)
                        {
                            states.Push(new[] { index, loopStart, loopIterations });
                            subscripts.Add(sub);
                            index = -1; loopStart = 0; loopIterations = 0;
                        }
                        break;
                    }
                case HITBOX: case EXT_HITBOX: case SPECIAL: case EXT_SPECIAL: case COLLATERAL: case EXT_COLLATERAL:
                case EXTRA_SPECIAL: case EXTRA_EXT_SPECIAL:
                    {
                        if (p.Count < 12) break;
                        bool extra = cmd.Ident == EXTRA_SPECIAL || cmd.Ident == EXTRA_EXT_SPECIAL;
                        bool special = extra || cmd.Ident == SPECIAL || cmd.Ident == EXT_SPECIAL;
                        bool extended = cmd.Ident == EXT_HITBOX || cmd.Ident == EXT_COLLATERAL || cmd.Ident == EXT_SPECIAL ||
                                        cmd.Ident == EXTRA_EXT_SPECIAL;
                        var h = new HitboxData
                        {
                            Command = cmd.Name, Script = Kind, Id = I(p[0]), Part = I(p[1]), Bone = I(p[2]), Damage = F(p[3]),
                            Angle = I(p[4]), KBG = I(p[5]), WBKB = I(p[6]), BKB = I(p[7]), Size = F(p[8]),
                            X = F(p[9]), Y = F(p[10]), Z = F(p[11]), Special = special,
                        };
                        int e = ParamIndex(cmd, "Effect", 12), hl = ParamIndex(cmd, "Hitlag", 14), sdi = ParamIndex(cmd, "SDI", 15),
                            sd = ParamIndex(cmd, "ShieldDamage", 18);
                        if (e < p.Count) h.Effect = I(p[e]);
                        if (hl < p.Count) h.Hitlag = F(p[hl]);
                        if (sdi < p.Count) h.SDI = F(p[sdi]);
                        if (sd < p.Count) h.ShieldDamage = I(p[sd]);
                        int flinchless = ParamIndex(cmd, "Flinchless", 39);
                        if (special && flinchless < p.Count && I(p[flinchless]) == 1) h.Windbox = true;
                        if (extended)
                        {
                            int x2 = ParamIndex(cmd, "X2", cmd.Ident == EXT_SPECIAL || cmd.Ident == EXTRA_EXT_SPECIAL ? 40 : 24);
                            if (p.Count > x2 + 2)
                            {
                                h.Extended = true;
                                h.X2 = F(p[x2]); h.Y2 = F(p[x2 + 1]); h.Z2 = F(p[x2 + 2]);
                            }
                        }
                        if (extra)
                        {
                            // the six extras end the command (Special_Hitbox's 41 / Extended_Special_Hitbox's 43, then these)
                            int first = cmd.Ident == EXTRA_EXT_SPECIAL ? 43 : 41;
                            Func<string, int, int> at = (n, k) => ParamIndex(cmd, n, first + k);
                            int a = at("HitstunMul", 0), b = at("HitstopMul", 1), c = at("HitstopFrames", 2), d = at("SelfHitstopMul", 3),
                                f = at("SelfHitstopFrames", 4), g = at("DIMul", 5);
                            if (Math.Max(Math.Max(Math.Max(a, b), Math.Max(c, d)), Math.Max(f, g)) < p.Count)
                            {
                                h.HasExtras = true;
                                h.HitstunMul = F(p[a]); h.HitstopMul = F(p[b]); h.HitstopFrames = (int)F(p[c]);
                                h.SelfHitstopMul = F(p[d]); h.SelfHitstopFrames = (int)F(p[f]); h.DIMul = F(p[g]);
                            }
                        }
                        if (extra)
                            HitboxVars(cmd, p, h);
                        hitboxes[h.Id] = h;
                        break;
                    }
                case CLEAR:
                    hitboxes.Clear();
                    break;
                case DELETE:
                    hitboxes.Remove(I(p[0]));
                    break;
                case DEACTIVATE_LAST:
                    if (hitboxes.Count > 0) hitboxes.Remove(hitboxes.Keys.Max());
                    break;
                case SIZE:
                    {
                        HitboxData h;
                        if (hitboxes.TryGetValue(I(p[0]), out h)) h.Size = F(p[1]);
                        break;
                    }
                case DAMAGE:
                    {
                        HitboxData h;
                        if (hitboxes.TryGetValue(I(p[0]), out h)) h.Damage = F(p[1]);
                        break;
                    }
                case MOVE:
                    {
                        HitboxData h;
                        if (hitboxes.TryGetValue(I(p[0]), out h) && p.Count >= 5)
                        {
                            h.Bone = I(p[1]); h.X = F(p[2]); h.Y = F(p[3]); h.Z = F(p[4]);
                        }
                        break;
                    }
                case SET_LOOP:
                    loopIterations = I(p[0]) - 1;
                    loopStart = index;
                    break;
                case GOTO:
                    if (loopIterations > 0 && loopIterations < 1000)
                    {
                        index = loopStart;
                        loopIterations--;
                    }
                    break;
                case BODY:
                    {
                        int s = I(p[0]);
                        intangible = s == 2 || s == 3;
                        invincible = s == 1;
                        break;
                    }
                case ARMOR:
                    armor = I(p[0]) == 1;
                    break;
                case TRUE:
                    if (!ConditionsTrue)
                    {
                        skipWords = I(p[0]) - 4;
                        if (skipWords == 0) skipWords = 1;
                    }
                    break;
                case ELSE:      // the else of a True block (Smash Forge's FALSE); some scripts use False there
                case FALSE:
                    if (ConditionsTrue)
                    {
                        skipWords = I(p[0]) - 2;
                        if (skipWords == 0) skipWords = 1;
                    }
                    break;
                case SET_FLOAT:
                    if (p.Count >= 2)
                    {
                        uint v = (uint)I(p[1]);
                        float val = F(p[0]);
                        writes.Add(new VarWrite { GameFrame = gameFrame, Variable = v, Value = val });
                        varValues[v & 0x0FFFFFFF] = val;
                        if (v == ANIM_RATE && UseFrameSpeed && val > 0) (isParallel ? root : this).rate = val;
                    }
                    break;
                case THREAD_START:
                    if (p.Count >= 2)
                    {
                        int blockWords = I(p[0]) - (p.Count + 1);
                        StartThread(I(p[1]), ThreadBlock(Current, index, blockWords));
                        skipWords = blockWords;       // the script jumps over the block
                    }
                    break;
                case THREAD_STOP:
                    if (p.Count >= 1)
                    {
                        var r = root ?? this;
                        int id = I(p[0]);
                        r.threads.RemoveAll(x => id == -1 || x.Id == id);
                    }
                    break;
                case END:
                    break;
                default:
                    EffectCommand(cmd, p);
                    break;
            }
            return true;
        }

        // ---- the effect script's commands (v1.5.0): effects, sword trails, screen events ------------------------------
        class EffectState
        {
            public List<EffectData> Live = new List<EffectData>();
            public List<EffectData> All = new List<EffectData>();
            public List<TrailData> Trails = new List<TrailData>();
            public List<TrailData> AllTrails = new List<TrailData>();
            public List<ScreenEvent> Screen = new List<ScreenEvent>();
            public List<ScreenEvent> AllScreen = new List<ScreenEvent>();
            public EffectData Last;
        }
        EffectState fx = new EffectState();

        /// <summary>Every effect the last Run started (one entry each, with its end), every trail, every screen event.</summary>
        public List<EffectData> AllEffects { get { return fx.All; } }
        public List<TrailData> AllTrails { get { return fx.AllTrails; } }
        public List<ScreenEvent> AllScreen { get { return fx.AllScreen; } }

        enum FxKind { None, Spawn, Off, OffAll, OffLast, Detach, Last, Trail, TrailOff, Screen, Note, Overlay, Vis }

        /// <summary>What an effect command does and where its parameters are, from its name and its parameters' names
        /// (Events.cfg's syntax, from the ACMD events sheet: no fixed positions guessed).</summary>
        class FxCmd
        {
            public FxKind Kind;
            public bool Follow, World, Flip, Light, Particle;
            public bool Camera;         // v1.7.6: Effect_Camera
            public int Mode = -1, Frames = -1;
            public string Op;           // v1.6.2: an overlay / visibility command's operation
            public int G = -1, GL = -1, Work = -1, Bone = -1, BoneHash = -1, X = -1, Y = -1, Z = -1, RX = -1, RY = -1,
                RZ = -1, Size = -1, Term = -1, R = -1, Gr = -1, B = -1, Alpha = -1, Rate = -1, Fade = -1,
                B1 = -1, B2 = -1, Blur = -1, T1 = -1, T2 = -1, T1W = -1, T2W = -1, Shader = -1;
        }
        static readonly Dictionary<uint, FxCmd> fxCmds = new Dictionary<uint, FxCmd>();
        static readonly HashSet<string> followNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
            // the conventional names of the developers' EFFECT_FOLLOW* (the ACMD events sheet)
            "External_Graphic", "External_Graphic_Effect2", "Graphic_Effect4", "Graphic_Effect5", "Graphic_Effect6" };
        static readonly HashSet<string> screenNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
            "Screen_Tint", "Screen_Tint2", "Limited_Screen_Tint", "End_Screen_Tint", "Color_Overlay", "FLASH_NO_STOP",
            "FLASH_OFF", "Flash_Light_Effect", "Change_Flash_Light_Color", "LIGHT_AXIS", "LIGHT_AXIS_FRM", "LIGHT_OFF",
            "SET_LIGHT_LENGTH", "SET_LIGHT_RADIUS", "EFFECT_LIGHT_END", "Aesthetic_Wind_Effect", "Aesthetic_Wind_Effect2",
            "Aesthetic_Wind_Effect3", "Terminate_Wind_Effect", "Pause_Graphic_Effect_Animation", "EFFECT_RESUME",
            "EFFECT_REQ_LINE_CIRCLE", "EFFECT_REQ_LINE_CIRCLE_OFFSET", "EFFECT_REMOVE_LINE_CIRCLE", "EFFECT_SYNC_SCALE",
            "EFFECT_OFF_KIND_WORK", "EFFECT_DETACH_KIND_WORK", "EFFECT_CONTINUAL_OFF", "LAST_EFFECT_SET_DISABLE_SYSTEM_SLOW",
            "LAST_EFFECT_SET_OFFSET_TO_CAMERA_FLAT", "LAST_EFFECT_SET_RATE_WORK", "LAST_EFFECT_SET_SCALE_W" };

        static FxCmd Describe(ACMDCommand c)
        {
            FxCmd d;
            if (fxCmds.TryGetValue(c.Ident, out d)) return d;
            d = new FxCmd();
            string n = c.Name ?? "";
            string[] syn;
            try { syn = c.ParamSyntax.Select(x => x.Trim()).ToArray(); } catch { syn = new string[0]; }
            Func<string[], int> at = names =>
            {
                for (int i = 0; i < syn.Length; i++)
                    foreach (var nm in names)
                        if (syn[i].Equals(nm, StringComparison.OrdinalIgnoreCase)) return i;
                return -1;
            };
            string up = n.ToUpperInvariant();
            // v1.6.2: the body colour overlays / flashes (drawn on the fighter) and the visibility commands (meshes, the
            // whole model) on the timeline
            if (n == "Color_Overlay" || n == "Change_Overlay" || n == "Terminate_Overlays" || n == "FLASH_NO_STOP" ||
                n == "FLASH_OFF" || n == "Flash_Light_Effect" || n == "Change_Flash_Light_Color")
            {
                d.Kind = FxKind.Overlay;
                d.Op = n;
                d.R = at(new[] { "Red" }); d.Gr = at(new[] { "Green" }); d.B = at(new[] { "Blue" }); d.Alpha = at(new[] { "Alpha" });
                d.Fade = at(new[] { "Transition", "TransitionFrames" });
            }
            else if (n == "Model_Changer" || n == "VIS_SET_DEFAULT" || n == "VIS_BACK_DEFAULT" || n == "VIS_RESET_DEFAULT" || n == "Visibility")
            {
                d.Kind = FxKind.Vis;
                d.Op = n;
                d.X = at(new[] { "ChangerID", "Group" }); d.Y = at(new[] { "ChangerState", "State" });
            }
            else if (n == "Effect_Camera")
            {
                // v1.7.6 (exe_v46z_camfx): an effect attached to the camera: drawn in front of the viewer's view
                d.Kind = FxKind.Spawn;
                d.Camera = true;
                d.World = true;
                d.G = at(new[] { "Graphic" });
                d.X = at(new[] { "X" }); d.Y = at(new[] { "Y" }); d.Z = at(new[] { "Z" });
                d.RX = at(new[] { "XRot" }); d.RY = at(new[] { "YRot" }); d.RZ = at(new[] { "ZRot" });
                d.Size = at(new[] { "Size" });
                d.Mode = at(new[] { "Mode" }); d.Frames = at(new[] { "Frames" });
            }
            else if (screenNames.Contains(n))
                d.Kind = FxKind.Screen;
            else if (n == "Terminate_Graphic_Effect" || n == "EFFECT_REMOVE_COMMON")
            {
                d.Kind = FxKind.Off;
                d.G = at(new[] { "Graphic", "CommonEffectId" });
            }
            else if (n == "EFFECT_OFF" || n == "EFFECT_REMOVE_ATTR")
                d.Kind = FxKind.OffAll;
            else if (n == "EFFECT_OFF_HANDLE")
                d.Kind = FxKind.OffLast;
            else if (n == "EFFECT_DETACH_KIND")
            {
                d.Kind = FxKind.Detach;
                d.G = at(new[] { "Graphic" });
            }
            else if (up.StartsWith("LAST_EFFECT_SET_") || up == "LAST_PARTICLE_SET_COLOR")
            {
                d.Kind = FxKind.Last;
                d.Particle = up == "LAST_PARTICLE_SET_COLOR";
                d.R = at(new[] { "Red", "R" }); d.Gr = at(new[] { "Green", "G" }); d.B = at(new[] { "Blue", "B" });
                d.Alpha = at(new[] { "Alpha" }); d.Rate = at(new[] { "Rate" });
                d.X = at(new[] { "ScaleX" }); d.Y = at(new[] { "ScaleY" }); d.Z = at(new[] { "ScaleZ" });
            }
            else if (n == "Terminate_Sword_Glow")
            {
                d.Kind = FxKind.TrailOff;
                d.Fade = at(new[] { "FadeTime" });
            }
            else if (at(new[] { "Bone1" }) >= 0 && at(new[] { "Bone2" }) >= 0)
            {
                d.Kind = FxKind.Trail;
                d.B1 = at(new[] { "Bone1" }); d.B2 = at(new[] { "Bone2" });
                d.Blur = at(new[] { "BlurLength", "BlurLen" });
                d.G = at(new[] { "Graphic", "Effect" });
                d.T1 = at(new[] { "Texture", "Texture1" }); d.T2 = at(new[] { "Texture2" });
                d.T1W = at(new[] { "TextureWork", "Texture1Work" }); d.T2W = at(new[] { "Texture2Work" });
                d.Shader = at(new[] { "Shader" });
            }
            else
            {
                d.G = at(new[] { "Graphic", "GFXRight", "Effect", "EffectR" });
                d.Work = at(new[] { "GraphicWork" });
                d.Bone = at(new[] { "Bone" });
                d.BoneHash = at(new[] { "BoneNameHash" });
                bool world = up.StartsWith("EFFECT_GLOBAL") || up.StartsWith("EM_EFFECT");
                // (v1.7.2) sound commands (Sound_Effect, Stop_Sound_Effect, ...: the sound script runs now) aren't effects
                bool named = (up.Contains("EFFECT") || up.Contains("GRAPHIC")) && !up.Contains("SOUND");
                if (named && (d.G == 0 || d.Work == 0) && (d.Bone >= 0 || d.BoneHash >= 0 || world))
                {
                    d.Kind = FxKind.Spawn;
                    d.World = world;
                    d.Follow = followNames.Contains(n) || up.Contains("FOLLOW") || up.Contains("FLW");
                    d.GL = at(new[] { "GFXLeft", "EffectL" });
                    d.Flip = d.GL >= 0;
                    d.X = at(new[] { "X" }); d.Y = at(new[] { "Y" }); d.Z = at(new[] { "Z" });
                    d.RX = at(new[] { "XRot", "RotX" }); d.RY = at(new[] { "YRot", "RotY" }); d.RZ = at(new[] { "ZRot", "RotZ" });
                    d.Size = at(new[] { "Size", "Scale" });
                    d.Term = at(new[] { "Terminate" });
                    d.R = at(new[] { "Red" }); d.Gr = at(new[] { "Green" }); d.B = at(new[] { "Blue" });
                    d.Alpha = at(new[] { "Alpha" });
                    d.Light = at(new[] { "LightIntensity" }) >= 0;   // EFFECT_LIGHT / _FOLLOW_LIGHT: a light's colour
                    d.Rate = at(new[] { "Rate" });          // v1.6.1: a spawn with its own rate (EFFECT_FLW_POS_STRENGTH)
                }
                else if (named && (up.Contains("EFFECT") || up.Contains("TRACE")))
                    d.Kind = FxKind.Note;
            }
            fxCmds[c.Ident] = d;
            return d;
        }

        static string Text(ACMDCommand c)
        {
            try { return c.ToString(); } catch { return c.Name; }
        }

        void EffectCommand(ACMDCommand cmd, IList<object> p)
        {
            var d = Describe(cmd);
            if (d.Kind == FxKind.None) return;
            Func<int, float, float> fl = (i, def) => i >= 0 && i < p.Count ? F(p[i]) : def;
            Func<int, int> it = i => i >= 0 && i < p.Count ? I(p[i]) : 0;
            var r = root ?? this;
            var fs = r.fx;
            switch (d.Kind)
            {
                case FxKind.Spawn:
                    {
                        var e = new EffectData
                        {
                            Index = fs.All.Count, Command = cmd.Name, Line = Text(cmd), Script = Kind, World = d.World, Follow = d.Follow,
                            Id = d.G >= 0 ? (uint)it(d.G) : 0, WorkVar = d.Work >= 0 ? (uint)it(d.Work) : 0,
                            Bone = d.Bone >= 0 ? it(d.Bone) : 0,
                            X = fl(d.X, 0), Y = fl(d.Y, 0), Z = fl(d.Z, 0), RX = fl(d.RX, 0), RY = fl(d.RY, 0), RZ = fl(d.RZ, 0),
                            Size = fl(d.Size, 1), Terminate = it(d.Term),
                            StartFrame = r.gameFrame, SpawnAnimFrame = (float)(r.animFrame - 1),
                        };
                        if (d.Camera)
                        {
                            e.Camera = true;
                            e.CamMode = d.Mode >= 0 ? it(d.Mode) : 0;
                            if (e.CamMode < 0 || e.CamMode > 2) e.CamMode = 0;
                            e.CamFrames = d.Frames >= 0 ? Math.Max(0, it(d.Frames)) : 0;
                        }
                        if (d.Work >= 0) e.Id = 0;
                        if (d.BoneHash >= 0) e.Bone = -1;
                        if (d.Flip) { e.HasLeft = true; e.IdLeft = (uint)it(d.GL); }
                        if (d.R >= 0 && !d.Light) { e.HasColor = true; e.R = fl(d.R, 1); e.G = fl(d.Gr, 1); e.B = fl(d.B, 1); e.SetColour255(); }
                        if (d.Alpha >= 0) { e.HasAlpha = true; e.A = fl(d.Alpha, 1); e.CA = e.A / 100; }
                        if (d.Rate >= 0) e.Rate = fl(d.Rate, 1);
                        fs.Live.Add(e);
                        fs.All.Add(e);
                        fs.Last = e;
                        break;
                    }
                case FxKind.Off:
                    {
                        uint id = (uint)it(d.G);
                        foreach (var e in fs.Live.Where(x => x.Id == id || (x.HasLeft && x.IdLeft == id)).ToList())
                            End(e, "terminated (" + cmd.Name + ")");
                        break;
                    }
                case FxKind.OffAll:
                    foreach (var e in fs.Live.ToList()) End(e, "terminated (" + cmd.Name + ")");
                    break;
                case FxKind.OffLast:
                    if (fs.Last != null && fs.Live.Contains(fs.Last)) End(fs.Last, "terminated (" + cmd.Name + ")");
                    break;
                case FxKind.Detach:
                    {
                        uint id = (uint)it(d.G);
                        foreach (var e in fs.Live.Where(x => x.Id == id && x.Follow && x.DetachFrame < 0))
                        {
                            e.DetachFrame = r.gameFrame;
                            e.DetachAnimFrame = (float)(r.animFrame - 1);
                        }
                        break;
                    }
                case FxKind.Last:
                    {
                        var e = fs.Last;
                        if (e == null) break;
                        if (d.R >= 0 && d.Particle)
                        {
                            // LAST_PARTICLE_SET_COLOR: multipliers as they are (0-1.5), on top of the effect's colour
                            e.HasParticleColor = true; e.PR = fl(d.R, 1); e.PG = fl(d.Gr, 1); e.PB = fl(d.B, 1);
                        }
                        else if (d.R >= 0) { e.HasColor = true; e.R = fl(d.R, 1); e.G = fl(d.Gr, 1); e.B = fl(d.B, 1); e.SetColour255(); }
                        if (d.Alpha >= 0) { e.HasAlpha = true; e.A = fl(d.Alpha, 1); e.CA = e.A / 100; }
                        if (d.Rate >= 0) e.Rate = fl(d.Rate, 1);
                        if (d.X >= 0) { e.HasScale = true; e.SX = fl(d.X, 1); e.SY = fl(d.Y, 1); e.SZ = fl(d.Z, 1); }
                        break;
                    }
                case FxKind.Trail:
                    {
                        var t = new TrailData
                        {
                            Index = fs.AllTrails.Count, Command = cmd.Name, Line = Text(cmd), Script = Kind,
                            Bone1 = it(d.B1), X1 = fl(d.B1 + 1, 0), Y1 = fl(d.B1 + 2, 0), Z1 = fl(d.B1 + 3, 0),
                            Bone2 = it(d.B2), X2 = fl(d.B2 + 1, 0), Y2 = fl(d.B2 + 2, 0), Z2 = fl(d.B2 + 3, 0),
                            Blur = it(d.Blur), Graphic = d.G >= 0 ? (uint)it(d.G) : 0, StartFrame = r.gameFrame,
                            Texture1 = d.T1 >= 0 ? it(d.T1) : d.T1W >= 0 ? -1 : 0, Texture2 = d.T2 >= 0 ? it(d.T2) : d.T2W >= 0 ? -1 : 0,
                            Shader = d.Shader >= 0 ? it(d.Shader) : 1,
                        };
                        foreach (var o in fs.Trails.Where(x => x.EndFrame < 0)) o.EndFrame = r.gameFrame;   // one at a time
                        fs.Trails.Add(t);
                        fs.AllTrails.Add(t);
                        break;
                    }
                case FxKind.TrailOff:
                    foreach (var t in fs.Trails.Where(x => x.EndFrame < 0))
                    {
                        t.EndFrame = r.gameFrame;
                        t.Fade = Math.Max(0, it(d.Fade));
                    }
                    break;
                case FxKind.Overlay:
                    {
                        var ov = r.overlay;
                        string op = d.Op;
                        if (op == "Terminate_Overlays" || op == "FLASH_OFF")
                            ov.Set(r.gameFrame, null, 0);
                        else
                        {
                            var c = new[] { fl(d.R, 255) / 255, fl(d.Gr, 255) / 255, fl(d.B, 255) / 255, fl(d.Alpha, 255) / 255 };
                            bool change = op == "Change_Overlay" || op == "Change_Flash_Light_Color";
                            bool light = op == "Flash_Light_Effect" || op == "Change_Flash_Light_Color";
                            ov.Light = light;
                            ov.Set(r.gameFrame, c, change ? Math.Max(0, it(d.Fade)) : 0);
                        }
                        var ev = new ScreenEvent { Frame = r.gameFrame, Text = Text(cmd) };
                        fs.Screen.Add(ev);
                        fs.AllScreen.Add(ev);
                        break;
                    }
                case FxKind.Vis:
                    {
                        var vs = r.vis;
                        int g = it(d.X), st2 = d.Y >= 0 ? it(d.Y) : 0;
                        switch (d.Op)
                        {
                            case "Model_Changer": vs.Groups[g] = st2; break;
                            case "VIS_SET_DEFAULT": vs.Defaults[g] = st2; vs.Groups[g] = st2; break;
                            case "VIS_BACK_DEFAULT":
                                if (vs.Defaults.ContainsKey(g)) vs.Groups[g] = vs.Defaults[g]; else vs.Groups.Remove(g);
                                break;
                            case "VIS_RESET_DEFAULT": vs.Defaults.Remove(g); vs.Groups.Remove(g); break;
                            case "Visibility": vs.Whole = st2 != 0; break;
                        }
                        vs.Changed[d.Op == "Visibility" ? -1 : g] = r.gameFrame;
                        vs.Events.Add(new ScreenEvent { Frame = r.gameFrame, Text = Text(cmd) });
                        break;
                    }
                case FxKind.Screen:
                case FxKind.Note:
                    {
                        var ev = new ScreenEvent { Frame = r.gameFrame, Text = Text(cmd) };
                        fs.Screen.Add(ev);
                        fs.AllScreen.Add(ev);
                        break;
                    }
            }
        }

        void End(EffectData e, string why)
        {
            var fs = (root ?? this).fx;
            e.EndFrame = (root ?? this).gameFrame;
            e.EndReason = why;
            fs.Live.Remove(e);
        }

        /// <summary>v1.6.1: game frames an effect of `life` frames of its own plays at `rate` (eft's step x the rate; a rate
        /// under 1/16 taken as 1/16, as the game's trail tick floors its step).</summary>
        public static int RatedLife(int life, float rate)
        {
            if (life <= 0 || Math.Abs(rate - 1) < 1e-6f) return life;
            return Math.Max(1, (int)Math.Ceiling(life / Math.Max(1 / 16f, rate) - 1e-4));
        }

        /// <summary>One-shot effects whose play time is over end (after this frame is shown, so a 1-frame one shows).</summary>
        void ExpireEffects()
        {
            foreach (var e in fx.Live.ToList())
            {
                // v1.7.6: Effect_Camera's Frames (the game fades it out after them)
                if (e.Camera && e.CamFrames > 0 && gameFrame >= e.StartFrame + e.CamFrames - 1)
                {
                    fx.Live.Remove(e);
                    e.EndFrame = gameFrame + 1;
                    e.EndReason = "Effect_Camera's Frames (" + e.CamFrames + ")";
                    continue;
                }
                if (e.Follow && e.DetachFrame < 0) continue;
                int life = OneShotLife != null ? OneShotLife(e.Id) : 0;
                if (life < 0) continue;
                if (life == 0) life = DefaultLife;
                // v1.6.1: the effect plays at its rate (LAST_EFFECT_SET_RATE: the emitter set's step x the rate), so its
                // frames of play last life / rate game frames
                life = RatedLife(life, e.Rate);
                int from = e.DetachFrame >= 0 ? e.DetachFrame : e.StartFrame;
                if (gameFrame >= from + life - 1)
                {
                    fx.Live.Remove(e);
                    e.EndFrame = gameFrame + 1;
                    e.EndReason = (OneShotLife != null && OneShotLife(e.Id) > 0 ? "its particles' life" : "(life not known: " + DefaultLife + " frames)") +
                                  (Math.Abs(e.Rate - 1) > 1e-6f ? string.Format(System.Globalization.CultureInfo.InvariantCulture, " at rate {0:0.###}", e.Rate) : "");
                }
            }
        }
    }
}
