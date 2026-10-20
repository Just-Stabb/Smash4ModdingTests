using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
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
            Trajectory(res, angle, Math.Abs(hx), Math.Abs(vy), t, h.Electric);
            return res;
        }

        static double Deg(double rad)
        {
            double d = rad * 180 / Math.PI;
            return d < 0 ? d + 360 : d;
        }

        /// <summary>Distance class without a stage: the launch decays, gravity and fall speed act.
        /// Also the hitstun-cancel frames (HitstunCancel).</summary>
        static void Trajectory(KnockbackResult res, double angle, double lx, double ly, FighterAttributes t, bool electric)
        {
            double c = Math.Cos(angle * Math.PI / 180), sn = Math.Sin(angle * Math.PI / 180);
            double vx = c < 0 ? -lx : lx, vy = sn < 0 ? -ly : ly;
            double dx = DECAY * c, dy = DECAY * sn;
            double x = 0, y = 0, g = 0;
            res.Path.Add(new[] { 0f, 0f });
            int limit = res.Hitstun < 200 ? res.Hitstun + 20 : 200;
            res.AirdodgeCancel = res.AerialCancel = res.Hitstun + 1;
            bool ad = false, ae = false;
            int ec = electric ? 1 : 0;
            for (int i = 0; i < limit; i++)
            {
                double cy = Math.Max(g, -t.FallSpeed);
                x += vx; y += vy + cy;
                res.Path.Add(new[] { (float)x, (float)y });
                if (vx != 0) { double dir = Math.Sign(vx); vx -= dx; if (Math.Sign(vx) != dir) vx = 0; }
                if (vy != 0) { double dir = Math.Sign(vy); vy -= dy; if (Math.Sign(vy) != dir) vy = 0; }
                g -= t.Gravity;
                if (i < res.Hitstun)
                {
                    double l = Math.Sqrt(vx * vx + vy * vy);
                    if (l < 2.5 && !ad) { ad = true; res.AirdodgeCancel = Math.Max(i + 2, 40 + 1 + ec); }
                    if (l < 2 && !ae) { ae = true; res.AerialCancel = Math.Max(i + 2, 45 + 1 + ec); }
                }
            }
            if (res.AirdodgeCancel > res.Hitstun) res.AirdodgeCancel = res.Hitstun + 1;
            if (res.AerialCancel > res.Hitstun) res.AerialCancel = res.Hitstun + 1;
        }
    }
}
