using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace Sm4shCommand.Viewer
{
    /// <summary>A fighter's attributes the calculator needs (Viewer\Fighters.txt).</summary>
    public class FighterAttributes
    {
        public string Name;
        public float Weight = 100, Gravity = 0.08f, FallSpeed = 1.5f, FastFall = 2.4f, Traction = 0.05f;
        public override string ToString() { return Name; }

        public static List<FighterAttributes> Load()
        {
            var list = new List<FighterAttributes>();
            string path = Path.Combine(Application.StartupPath, "Viewer", "Fighters.txt");
            if (File.Exists(path))
            {
                foreach (var raw in File.ReadAllLines(path))
                {
                    var line = raw.Trim();
                    if (line.Length == 0 || line.StartsWith("#")) continue;
                    var f = line.Split('\t');
                    if (f.Length < 6) continue;
                    try
                    {
                        Func<string, float> p = s => float.Parse(s, NumberStyles.Float, CultureInfo.InvariantCulture);
                        list.Add(new FighterAttributes
                        {
                            Name = f[0], Weight = p(f[1]), Gravity = p(f[2]), FallSpeed = p(f[3]), FastFall = p(f[4]), Traction = p(f[5])
                        });
                    }
                    catch (FormatException) { }
                }
            }
            if (list.Count == 0)
                list.Add(new FighterAttributes { Name = "Weight 100" });
            return list;
        }
    }

    /// <summary>What the calculator is asked.</summary>
    public class KnockbackInput
    {
        public HitboxData Hitbox;
        public FighterAttributes Target;
        public float TargetPercent;         // before the hit
        public float AttackerPercent;       // rage
        public int StaleCount;              // times in the stale queue (the most recent ones), 0-9
        public float ChargeFrames;          // smash charge
        public bool Crouching;              // crouch cancel: x0.85 knockback, x0.67 hitlag
        public bool TargetAerial;
        public float KbMultiplier = 1;      // other knockback multipliers
        public float LaunchRate = 1;
        public bool UseDI;
        public float DIAngle;               // stick angle in degrees, full tilt
    }

    /// <summary>The calculator's results.</summary>
    public class KnockbackResult
    {
        public float Damage, StaleMultiplier, TargetPercentAfter, KB, Angle, LaunchSpeed, LaunchSpeedX, LaunchSpeedY;
        public int Hitstun, Faf, AttackerHitlag, TargetHitlag, ShieldStun, ShieldHitlag, AirdodgeCancel, AerialCancel;
        public bool Tumble, Spike;
        // after the script's own changes (ScriptModifiers.Apply); the same as above when it has none
        public int FinalHitstun, FinalTargetHitlag, FinalAttackerHitlag, FinalAirdodgeCancel, FinalAerialCancel;
        internal double PathAngle, PathX, PathY;   // what the trajectory was made from (Retime redoes it)
        internal FighterAttributes PathTarget;
        internal bool PathElectric;
        public List<int[]> TargetStops = new List<int[]>();  // extra hitstop during hitstun: {frame of hitstun, frames}
        public List<string> ScriptNotes = new List<string>();
        public List<float[]> Path = new List<float[]>();   // trajectory (x forward, y), one point a frame
    }

    /// <summary>
    /// Smash 4 knockback / hitstun formulas, ported from Sm4sh-Calculator by rubendal (MIT,
    /// https://github.com/rubendal/Sm4sh-Calculator: js/formulas.js, js/global.js Knockback / Distance).
    /// </summary>
    public static class KnockbackCalc
    {
        const double DI = 0.17, LSI_MAX = 1.095, LSI_MIN = 0.92, DECAY = 0.051, GRAV_MULT = 5, GRAV_CONST = 0.075,
            HITSTUN = 0.4, LAUNCH = 0.03, TUMBLE = 32;

        static readonly double[] Stale = { 0.08, 0.07594, 0.06782, 0.06028, 0.05274, 0.04462, 0.03766, 0.02954, 0.022 };

        public static double StaleNegation(int count)
        {
            if (count <= 0) return 1.05;      // a fresh move
            double s = 1;
            for (int i = 0; i < Math.Min(count, Stale.Length); i++) s -= Stale[i];
            return s;
        }

        public static double Rage(double percent)
        {
            if (percent <= 35) return 1;
            if (percent >= 150) return 1.15;
            return 1 + (percent - 35) * 0.15 / 115;
        }

        public static int Hitstun(double kb, bool windbox, bool electric)
        {
            if (windbox) return 0;
            int h = (int)Math.Floor(kb * HITSTUN) - 1;
            if (kb * HITSTUN >= TUMBLE) h++;
            if (electric) h++;
            return Math.Max(0, h);
        }

        public static double SakuraiAngle(double kb, bool aerial)
        {
            if (aerial) return 0.79 * 180 / Math.PI;
            if (kb < 60) return 0;
            if (kb >= 88) return 40;
            return Math.Min((kb - 60) / 28 * 40 + 1, 40);
        }

        public static int Hitlag(double damage, double mult, bool electric, double crouch)
        {
            int h = (int)Math.Floor((damage * 0.3846154 + 5) * (electric ? 1.5 : 1) * mult * crouch) - 1;
            return Math.Max(0, Math.Min(30, h));
        }

        public static KnockbackResult Calculate(KnockbackInput inp)
        {
            var h = inp.Hitbox;
            var t = inp.Target ?? new FighterAttributes();
            var res = new KnockbackResult();
            double baseDamage = h.Damage * (1 + inp.ChargeFrames / 150.0);
            double s = StaleNegation(inp.StaleCount);
            double damage = baseDamage;
            double r = inp.KbMultiplier * (inp.Crouching ? 0.85 : 1);
            double kb;
            if (h.WBKB == 0)
            {
                double p = inp.TargetPercent;
                kb = ((((p + damage * s) / 10 + ((p + damage * s) * baseDamage * (1 - (1 - s) * 0.3)) / 20) * 1.4 * (200.0 / (t.Weight + 100)) + 18)
                      * (h.KBG / 100.0) + h.BKB) * r * Rage(inp.AttackerPercent);
            }
            else
                kb = ((((1 + h.WBKB / 2.0) * (200.0 / (t.Weight + 100)) * 1.4) + 18) * (h.KBG / 100.0) + h.BKB) * r * Rage(inp.AttackerPercent);
            res.StaleMultiplier = (float)s;
            res.Damage = (float)(damage * s);
            res.TargetPercentAfter = (float)(inp.TargetPercent + damage * s);

            // Knockback class (global.js)
            kb *= inp.LaunchRate;
            bool aerial = inp.TargetAerial, windbox = h.Windbox;
            double angle = h.Angle == 361 ? SakuraiAngle(kb, aerial) : h.Angle;
            bool tumble = false;
            if (angle != 0 && angle != 180) tumble = kb >= 80 && !windbox;
            if ((angle == 0 || angle == 180) && aerial) tumble = kb >= 80 && !windbox;
            double gravBoost = tumble ? GRAV_MULT * (t.Gravity - GRAV_CONST) : 0;
            double ls = kb * LAUNCH;
            double hx = ls * Math.Cos(angle * Math.PI / 180), vy = ls * Math.Sin(angle * Math.PI / 180) + gravBoost;
            if ((angle == 0 || angle == 180) && !aerial)
                hx = Math.Max(-17, Math.Min(hx, 17));
            else
            {
                hx = Math.Max(-100, Math.Min(hx, 100));
                angle = Deg(Math.Atan2(vy, hx));
            }
            vy = Math.Max(-100, Math.Min(vy, 10));
            if (windbox && !aerial) vy = 0;
            bool diAble = tumble && Math.Abs(Math.Atan2(vy, hx)) >= DI;
            if (diAble && inp.UseDI)
            {
                double total = Math.Sqrt(hx * hx + vy * vy);
                double sx = Math.Cos(inp.DIAngle * Math.PI / 180), sy = Math.Sin(inp.DIAngle * Math.PI / 180);
                bool check = sy * hx - sx * vy < 0;
                double variation = Math.Abs(sx * vy - sy * hx) / Math.Max(total, 1e-6);
                double a = Math.Atan2(vy, hx) + (check ? -1 : 1) * DI * variation;
                angle = Deg(a);
                double lsi = 1;
                if (!(angle > 65 && angle < 115) && !(angle > 245 && angle < 295))
                    lsi = sy >= 0 ? 1 + (LSI_MAX - 1) * sy : 1 - (1 - LSI_MIN) * -sy;
                total *= lsi;
                hx = Math.Max(-100, Math.Min(total * Math.Cos(angle * Math.PI / 180), 100));
                vy = Math.Max(-100, Math.Min(total * Math.Sin(angle * Math.PI / 180), 10));
            }
            res.KB = (float)kb;
            res.Angle = (float)angle;
            res.Tumble = tumble;
            res.Spike = angle >= 230 && angle <= 310;
            res.LaunchSpeed = (float)ls;
            res.LaunchSpeedX = (float)Math.Abs(hx);
            res.LaunchSpeedY = (float)Math.Abs(vy);
            res.Hitstun = Hitstun(kb / inp.LaunchRate, windbox, h.Electric);
            res.Faf = res.Hitstun == 0 ? 0 : res.Hitstun + 1;
            res.AttackerHitlag = Hitlag(res.Damage, h.Hitlag, h.Electric, 1);
            res.TargetHitlag = Hitlag(res.Damage, h.Hitlag, h.Electric, inp.Crouching ? 0.67 : 1);
            res.ShieldStun = (int)Math.Floor(res.Damage * 0.58 + 3) - 1;
            double shl = h.Hitlag > 1 ? Math.Max(1, h.Hitlag * 0.8) : h.Hitlag;
            res.ShieldHitlag = Hitlag(res.Damage, shl, h.Electric, 1);
            res.PathAngle = angle; res.PathX = Math.Abs(hx); res.PathY = Math.Abs(vy); res.PathTarget = t; res.PathElectric = h.Electric;
            int ad, ae;
            res.Path = Trajectory(res.Hitstun, angle, Math.Abs(hx), Math.Abs(vy), t, h.Electric, out ad, out ae);
            res.AirdodgeCancel = res.FinalAirdodgeCancel = ad;
            res.AerialCancel = res.FinalAerialCancel = ae;
            res.FinalHitstun = res.Hitstun;
            res.FinalTargetHitlag = res.TargetHitlag;
            res.FinalAttackerHitlag = res.AttackerHitlag;
            return res;
        }

        static double Deg(double rad)
        {
            double d = rad * 180 / Math.PI;
            return d < 0 ? d + 360 : d;
        }

        /// <summary>Distance class without a stage: the launch decays, gravity and fall speed act.
        /// Also the hitstun-cancel frames (HitstunCancel): airdodge once the launch speed is under 2.5
        /// (not before frame 40), aerials under 2 (not before 45), never later than the end of hitstun.</summary>
        static List<float[]> Trajectory(int hitstun, double angle, double lx, double ly, FighterAttributes t, bool electric,
                                        out int airdodge, out int aerial)
        {
            var path = new List<float[]>();
            double c = Math.Cos(angle * Math.PI / 180), sn = Math.Sin(angle * Math.PI / 180);
            double vx = c < 0 ? -lx : lx, vy = sn < 0 ? -ly : ly;
            double dx = DECAY * c, dy = DECAY * sn;
            double x = 0, y = 0, g = 0;
            path.Add(new[] { 0f, 0f });
            int limit = hitstun < 300 ? hitstun + 20 : 320;
            airdodge = aerial = hitstun + 1;
            bool ad = false, ae = false;
            int ec = electric ? 1 : 0;
            for (int i = 0; i < limit; i++)
            {
                double cy = Math.Max(g, -t.FallSpeed);
                x += vx; y += vy + cy;
                path.Add(new[] { (float)x, (float)y });
                if (vx != 0) { double dir = Math.Sign(vx); vx -= dx; if (Math.Sign(vx) != dir) vx = 0; }
                if (vy != 0) { double dir = Math.Sign(vy); vy -= dy; if (Math.Sign(vy) != dir) vy = 0; }
                g -= t.Gravity;
                if (i < hitstun)
                {
                    double l = Math.Sqrt(vx * vx + vy * vy);
                    if (l < 2.5 && !ad) { ad = true; airdodge = Math.Max(i + 2, 40 + 1 + ec); }
                    if (l < 2 && !ae) { ae = true; aerial = Math.Max(i + 2, 45 + 1 + ec); }
                }
            }
            if (airdodge > hitstun) airdodge = hitstun + 1;
            if (aerial > hitstun) aerial = hitstun + 1;
            return path;
        }

        /// <summary>The trajectory and hitstun-cancel frames again for the hitstun the script left
        /// (FinalHitstun), counting the frames the target is frozen in hitstop during it.</summary>
        public static void Retime(KnockbackResult r)
        {
            if (r.PathTarget == null) return;
            int ad, ae;
            r.Path = Trajectory(r.FinalHitstun, r.PathAngle, r.PathX, r.PathY, r.PathTarget, r.PathElectric, out ad, out ae);
            r.FinalAirdodgeCancel = ad + FrozenBefore(r, ad);
            r.FinalAerialCancel = ae + FrozenBefore(r, ae);
        }

        /// <summary>Hitstop frames (TargetStops) that come before hitstun frame n.</summary>
        public static int FrozenBefore(KnockbackResult r, int n)
        {
            int f = 0;
            foreach (var s in r.TargetStops)
                if (s[0] < n + f) f += s[1];
            return f;
        }
    }

    /// <summary>
    /// The attacking script's SET_FLOATs to the combat variables (tools/position_vars_cave.py,
    /// docs/position-variables.md "Hitstun, hitstop and the last fighter hit") applied to a hit: the
    /// target is the nearest opponent (0x0F000048-4F) and the last fighter hit (0x0F000050-57),
    /// self is 0x0F000040-47. Frames are counted in real time: the script stands still during the
    /// attacker's hitlag, so a script frame after the hit is that many frames later.
    /// </summary>
    public static class ScriptModifiers
    {
        const uint SELF = 0x0F000040, OPP = 0x0F000048, LASTHIT = 0x0F000050;
        const int HITSTUN = 0, HITSTUN_MUL = 2, HITSTOP_SHAKE = 3, HITSTOP = 4;

        public static void Apply(KnockbackResult r, int hitFrame, IEnumerable<VarWrite> writes)
        {
            int attackerLag = r.AttackerHitlag, targetLag = r.TargetHitlag;
            // the target's hitstun runs from launch (hit + its hitlag) to stunEnd; real frames
            int launch = hitFrame + targetLag, stunEnd = launch + r.Hitstun;
            double rememberedMul = 1;
            int selfExtra = 0;
            foreach (var w in writes)
            {
                uint v = w.Variable;
                bool target = v >= OPP && v < OPP + 8 || v >= LASTHIT && v < LASTHIT + 8, self = v >= SELF && v < SELF + 8;
                if (!target && !self) continue;
                int q = (int)(v & 7);
                bool after = w.GameFrame > hitFrame;
                int real = after ? w.GameFrame + attackerLag + selfExtra : w.GameFrame;
                string who = v >= LASTHIT && v < LASTHIT + 8 ? "LASTHIT" : v >= OPP && v < OPP + 8 ? "OPP" : "SELF";
                string at = string.Format(CultureInfo.InvariantCulture, "frame {0}: {1}", w.GameFrame, who);
                if (self)
                {
                    if ((q == HITSTOP || q == HITSTOP_SHAKE) && w.Value > 0 && w.GameFrame >= hitFrame)
                    {
                        // attacker hitstop from that frame: on the hit frame it replaces the hit's hitlag
                        if (w.GameFrame == hitFrame) { attackerLag = (int)w.Value; r.ScriptNotes.Add(Note(at, "_HITSTOP", w.Value, "attacker hitlag " + attackerLag)); }
                        else { selfExtra += (int)w.Value; r.ScriptNotes.Add(Note(at, "_HITSTOP", w.Value, "attacker stops " + (int)w.Value + " more frames")); }
                    }
                    continue;
                }
                switch (q)
                {
                    case HITSTUN_MUL:
                        if (!after && who == "LASTHIT")
                        {
                            rememberedMul *= w.Value;   // remembered for the move's hits that land afterwards
                            r.ScriptNotes.Add(Note(at, "_HITSTUN_MUL", w.Value, "hitstun x" + Fmt(w.Value)));
                        }
                        else if (after && real < stunEnd)
                        {
                            int from = Math.Max(real, launch), left = stunEnd - from;
                            stunEnd = from + (int)Math.Round(left * w.Value);
                            if (who == "LASTHIT") rememberedMul = 1;   // already applied to this hit
                            r.ScriptNotes.Add(Note(at, "_HITSTUN_MUL", w.Value, "hitstun left x" + Fmt(w.Value)));
                        }
                        break;
                    case HITSTUN:
                        if (after && real < stunEnd)
                        {
                            int from = Math.Max(real, launch);
                            stunEnd = from + (int)w.Value;
                            r.ScriptNotes.Add(Note(at, "_HITSTUN", w.Value, (int)w.Value + " frames of hitstun left"));
                        }
                        break;
                    case HITSTOP:
                    case HITSTOP_SHAKE:
                        if (w.GameFrame >= hitFrame && w.Value > 0)
                        {
                            int n = (int)w.Value, from = w.GameFrame == hitFrame ? hitFrame : real;
                            if (from <= launch)
                            {   // during the hit's own hitlag: it ends n frames from now
                                int newLaunch = from + n;
                                stunEnd += newLaunch - launch;
                                launch = newLaunch;
                                targetLag = launch - hitFrame;
                            }
                            else if (from < stunEnd)
                            {   // frozen in the middle of hitstun
                                r.TargetStops.Add(new[] { from - launch, n });
                                stunEnd += n;
                            }
                            r.ScriptNotes.Add(Note(at, q == HITSTOP ? "_HITSTOP" : "_HITSTOP_SHAKE", w.Value, "target hitstop " + n));
                        }
                        break;
                }
            }
            if (rememberedMul != 1)
            {
                int stun = stunEnd - launch;
                stunEnd = launch + (int)Math.Round(stun * rememberedMul);
            }
            r.FinalTargetHitlag = targetLag;
            r.FinalAttackerHitlag = attackerLag;
            r.FinalHitstun = Math.Max(0, stunEnd - launch - r.TargetStops.Sum(x => x[1]));
        }

        static string Fmt(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }
        static string Note(string at, string name, float v, string what)
        {
            return string.Format(CultureInfo.InvariantCulture, "{0}{1} = {2}: {3}", at, name, Fmt(v), what);
        }
    }
}
