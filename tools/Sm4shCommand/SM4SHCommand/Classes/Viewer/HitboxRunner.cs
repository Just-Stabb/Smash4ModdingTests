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
        // Extra_Special_Hitbox / Extra_Extended_Special_Hitbox's six extras (docs/acmd-extra-commands.md):
        // multipliers of 0 or less are x1, frames of 0 are "computed"
        public bool HasExtras;
        public float HitstunMul, HitstopMul, SelfHitstopMul, DIMul;
        public int HitstopFrames, SelfHitstopFrames;

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

        const uint ASYNC = 0x42ACFE7D, SYNC = 0x4B7B6E51, FRAME_DURATION = 0x7172A764, FRAME_DURATION2 = 0xB2E91D0C,
            FRAME_MUL = 0xA546845C, CALL1 = 0x9126EBA2, CALL2 = 0xFA1BC28A, HITBOX = 0xB738EABD,
            EXT_HITBOX = 0x2988D50F, SPECIAL = 0x14FCC7E4, EXT_SPECIAL = 0x7075DC5A, COLLATERAL = 0xCC7CC705,
            EXTRA_SPECIAL = 0x974EA5BE, EXTRA_EXT_SPECIAL = 0x5C8A67C9,
            EXT_COLLATERAL = 0xED67D5DA, CLEAR = 0x9245E1A8, DELETE = 0xFF379EB6, DEACTIVATE_LAST = 0x7698BB42,
            SIZE = 0x684264C9, DAMAGE = 0xDFA4517A, MOVE = 0x1AFDA8E6, SET_LOOP = 0x0EB375E3, GOTO = 0x38A3EC78,
            BODY = 0xF0D25BDA, SET_FLOAT = 0x1E3AB92A, ANIM_RATE = 0x0F000098, ARMOR = 0x2A25155D, TRUE = 0xA5BD4F32, ELSE = 0x895B9275, FALSE = 0x870CF021, END = 0x5766F889;

        IList<ICommand> script;
        readonly List<IList<ICommand>> subscripts = new List<IList<ICommand>>();
        readonly Stack<int[]> states = new Stack<int[]>();
        int index, loopStart, loopIterations, skipWords;
        double currentFrame, animFrame, frameSpeed, syncFrames, rate;
        int gameFrame;
        List<VarWrite> writes = new List<VarWrite>();
        double Speed { get { return frameSpeed * rate; } }   // the move's frame speed x the animation rate variable
        bool incrementFrame;
        readonly SortedDictionary<int, HitboxData> hitboxes = new SortedDictionary<int, HitboxData>();
        bool intangible, invincible, armor;

        /// <summary>Runs the script for frames game frames (one FrameState each).</summary>
        public List<FrameState> Run(IList<ICommand> commands, int frames)
        {
            script = commands;
            subscripts.Clear(); states.Clear(); hitboxes.Clear();
            index = 0; loopStart = 0; loopIterations = 0; skipWords = 0;
            currentFrame = 0; animFrame = 0; frameSpeed = 1; syncFrames = -1; rate = 1;
            incrementFrame = true;
            intangible = invincible = armor = false;
            var outList = new List<FrameState>();
            int guard = 0;
            for (int game = 0; game < frames; game++)
            {
                gameFrame = game + 1;
                writes = new List<VarWrite>();
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
                var st = new FrameState
                {
                    GameFrame = game + 1,
                    AnimFrame = (float)(animFrame - 1),
                    Intangible = intangible, Invincible = invincible, SuperArmor = armor, Writes = writes,
                };
                foreach (var h in hitboxes.Values)
                    st.Hitboxes.Add(h.Clone());
                outList.Add(st);
            }
            return outList;
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
                    if (UseFrameSpeed && F(p[0]) != 0) frameSpeed = 1 / F(p[0]);
                    break;
                case FRAME_MUL:
                    if (UseFrameSpeed) frameSpeed = F(p[0]);
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
                            Command = cmd.Name, Id = I(p[0]), Part = I(p[1]), Bone = I(p[2]), Damage = F(p[3]),
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
                        if (v == ANIM_RATE && UseFrameSpeed && val > 0) rate = val;
                    }
                    break;
                case END:
                    break;
            }
            return true;
        }
    }
}
