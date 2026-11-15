using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Linq;
using System.Windows.Forms;

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// Draws the fighter (skinned to an animation frame, a small z-buffered software renderer, so
    /// no graphics driver is needed) and the frame's hitboxes. Drag: rotate, right-drag: pan,
    /// wheel: zoom, double-click: reset to the game's side view.
    /// </summary>
    /// <summary>The target fighter: its model, posed, standing at (Z, Y) and facing left.</summary>
    public class EnemyFigure
    {
        public FighterAssets Assets;
        public Omo Animation;
        public float Frame, Z, Y;
    }

    public class Viewport : Control
    {
        public FighterAssets Assets;
        public Omo Animation;
        public float AnimFrame;
        public FrameState Frame;
        public int SelectedHitbox = -1;
        public bool ShowModel = true, ShowAngles = true, ShowBones, ShowTextures = true;
        public EnemyFigure Enemy;           // the fighter being hit, or null
        public string EnemyStatus;          // its hitlag / hitstun state, shown in the corner
        public float[] TrajectoryOrigin;    // where the trajectory starts (x, y, z); null: at the hitbox
        public List<float[]> Trajectory;    // forward / up from the selected hitbox (calculator)
        // v1.5.0: the effect script's effects (Frame.Effects / Trails): markers at their bone + offset, turned and
        // sized as the call says, coloured by its colour; trails as the blade's line with a fading history
        public bool ShowEffects = true, ShowEffectLabels = true, ShowTrails = true;
        public bool Flip;                   // the scene turned round (the fighter facing left), as the game turns it
        public int SelectedEffect = -1;     // EffectData.Index
        public Func<EffectData, string> EffectLabel;
        public List<float> TrailFrames = new List<float>();   // animation frames of the game frames before this one
                                                              // (newest first), for the trails' history

        float yaw, pitch, zoom = 9f, panX, panY;
        Point dragFrom;
        MouseButtons dragButton;
        Mat4[] world;
        Skinned attacker, enemy;

        public static readonly Color[] HitboxColors = {
            Color.FromArgb(255, 40, 40), Color.FromArgb(255, 150, 20), Color.FromArgb(240, 220, 0),
            Color.FromArgb(40, 200, 60), Color.FromArgb(0, 200, 220), Color.FromArgb(50, 90, 255),
            Color.FromArgb(170, 60, 230), Color.FromArgb(255, 80, 200) };

        public Viewport()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint |
                     ControlStyles.ResizeRedraw, true);
            BackColor = Color.FromArgb(232, 236, 242);
            ResetView();
        }

        public void ResetView()
        {
            yaw = 0; pitch = 0; zoom = FitZoom(); panX = 0; panY = 0;
            viewMoved = false;
            Invalidate();
        }

        bool viewMoved;

        /// <summary>A zoom that shows the fighter about a third of the view's height (room for its hitboxes).</summary>
        float FitZoom()
        {
            float top = 10;
            if (Assets != null)
                foreach (var m in Assets.Skeleton.World(null, 0))
                    top = Math.Max(top, m.M[7]);
            return Height > 0 ? Math.Max(1f, Math.Min(80f, Height * 0.2f / top)) : 9f;
        }

        protected override void OnSizeChanged(EventArgs e)
        {
            base.OnSizeChanged(e);
            if (!viewMoved) ResetView();
        }

        // camera: screen right = model +Z (the fighter faces right), up = +Y, depth = +X (away)
        void Axes(out float[] right, out float[] up, out float[] fwd)
        {
            double y = yaw + (Flip ? Math.PI : 0);    // facing left: the game turns the fighter (and all it does) round
            double cy = Math.Cos(y), sy = Math.Sin(y), cp = Math.Cos(pitch), sp = Math.Sin(pitch);
            right = new[] { (float)sy, 0f, (float)cy };
            fwd = new[] { (float)(cy * cp), (float)sp, (float)(-sy * cp) };
            up = new[] { (float)(-cy * sp), (float)cp, (float)(sy * sp) };
        }

        PointF Project(float[] p, float[] r, float[] u, out float depth)
        {
            depth = 0;
            float x = p[0] * r[0] + p[1] * r[1] + p[2] * r[2];
            float y = p[0] * u[0] + p[1] * u[1] + p[2] * u[2];
            return new PointF(Width / 2f + panX + x * zoom, Height * 0.72f + panY - y * zoom);
        }

        /// <summary>A held model drawn on the fighter's bone HeldBone (e.g. Kirby's Marth-copy sword), or null.</summary>
        public FighterAssets Held;
        public int HeldBone = -1;
        Skinned held;

        public void Recompute()
        {
            world = Assets != null ? Assets.Skeleton.World(Animation, AnimFrame) : null;
            attacker = null;
            held = null;
            if (Assets != null && ShowModel)
                attacker = Skin(Assets, world, 0, 0, false);
            if (Assets != null && ShowModel && Held != null && HeldBone >= 0 && HeldBone < world.Length)
                held = Skin(Held, Held.Skeleton.Attached(world[HeldBone]), 0, 0, false);
            enemy = null;
            if (Enemy != null && Enemy.Assets != null)
                enemy = Skin(Enemy.Assets, Enemy.Assets.Skeleton.World(Enemy.Animation, Enemy.Frame), Enemy.Z, Enemy.Y, true);
            Invalidate();
        }

        /// <summary>A model's vertices skinned to world matrices, then moved to (z, y) (turned to face
        /// left when faceLeft).</summary>
        class Skinned
        {
            public FighterAssets Assets;
            public float[] Pos;
            public int[] PolyStart;
        }

        static Skinned Skin(FighterAssets assets, Mat4[] world, float z0, float y0, bool faceLeft)
        {
            int n = 0;
            var starts = new List<int>();
            foreach (var m in assets.Model.Meshes)
                foreach (var p in m.Polys) { starts.Add(n); n += p.Pos.Length; }
            var s = new Skinned { Assets = assets, Pos = new float[n], PolyStart = starts.ToArray() };
            var skel = assets.Skeleton;
            var skin = new Mat4[world.Length];
            for (int i = 0; i < world.Length; i++) skin[i] = world[i] * skel.InverseBind[i];
            int k = 0;
            foreach (var m in assets.Model.Meshes)
                foreach (var p in m.Polys)
                {
                    int vc = p.Pos.Length / 3, b = s.PolyStart[k++];
                    for (int v = 0; v < vc; v++)
                    {
                        float x = p.Pos[v * 3], y = p.Pos[v * 3 + 1], z = p.Pos[v * 3 + 2], ox = 0, oy = 0, oz = 0, wsum = 0;
                        for (int j = 0; j < 4; j++)
                        {
                            float w = p.Weights[v * 4 + j];
                            int bi = p.Bones[v * 4 + j];
                            if (w <= 0 || bi < 0 || bi >= skin.Length) continue;
                            var M = skin[bi].M;
                            ox += w * (M[0] * x + M[1] * y + M[2] * z + M[3]);
                            oy += w * (M[4] * x + M[5] * y + M[6] * z + M[7]);
                            oz += w * (M[8] * x + M[9] * y + M[10] * z + M[11]);
                            wsum += w;
                        }
                        if (wsum <= 0) { ox = x; oy = y; oz = z; }
                        else if (Math.Abs(wsum - 1) > 1e-3) { ox /= wsum; oy /= wsum; oz /= wsum; }
                        if (faceLeft) { ox = -ox; oz = -oz; }     // turned around the vertical axis
                        s.Pos[b + v * 3] = ox; s.Pos[b + v * 3 + 1] = oy + y0; s.Pos[b + v * 3 + 2] = oz + z0;
                    }
                }
            return s;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            int w = Math.Max(1, Width), h = Math.Max(1, Height);
            float[] r, u, f;
            Axes(out r, out u, out f);
            using (var bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb))
            {
                var pix = new int[w * h];
                int bg = BackColor.ToArgb();
                for (int i = 0; i < pix.Length; i++) pix[i] = bg;
                var zbuf = new float[w * h];
                for (int i = 0; i < zbuf.Length; i++) zbuf[i] = float.MaxValue;
                if (attacker != null) Rasterize(attacker, pix, zbuf, w, h, r, u, f);
                if (held != null) Rasterize(held, pix, zbuf, w, h, r, u, f);
                if (enemy != null) Rasterize(enemy, pix, zbuf, w, h, r, u, f);
                var data = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
                Marshal.Copy(pix, 0, data.Scan0, pix.Length);
                bmp.UnlockBits(data);
                using (var g = Graphics.FromImage(bmp))
                {
                    g.SmoothingMode = SmoothingMode.AntiAlias;
                    DrawGround(g, r, u);
                    if (ShowBones && world != null) DrawBones(g, r, u);
                    DrawHitboxes(g, r, u);
                    if (ShowTrails) DrawTrails(g, r, u);
                    if (ShowEffects) DrawEffects(g, r, u);
                    DrawTrajectory(g, r, u);
                    DrawStatus(g);
                }
                e.Graphics.DrawImageUnscaled(bmp, 0, 0);
            }
        }

        void Rasterize(Skinned s, int[] pix, float[] zbuf, int w, int h, float[] r, float[] u, float[] f)
        {
            float cx = w / 2f + panX, cy = h * 0.72f + panY;
            int k = 0;
            var tv = new float[6];
            foreach (var m in s.Assets.Model.Meshes)
            {
                int tint = (m.Name.GetHashCode() & 0x1F) - 16;
                foreach (var p in m.Polys)
                {
                    int b = s.PolyStart[k++];
                    if (!m.Visible) continue;
                    var tex = ShowTextures ? p.Texture : null;
                    var t = p.Tris;
                    float[] P = s.Pos;
                    for (int i = 0; i + 2 < t.Length; i += 3)
                    {
                        int a0 = b + t[i] * 3, a1 = b + t[i + 1] * 3, a2 = b + t[i + 2] * 3;
                        // view space
                        float x0 = P[a0] * r[0] + P[a0 + 1] * r[1] + P[a0 + 2] * r[2], y0 = P[a0] * u[0] + P[a0 + 1] * u[1] + P[a0 + 2] * u[2], z0 = P[a0] * f[0] + P[a0 + 1] * f[1] + P[a0 + 2] * f[2];
                        float x1 = P[a1] * r[0] + P[a1 + 1] * r[1] + P[a1 + 2] * r[2], y1 = P[a1] * u[0] + P[a1 + 1] * u[1] + P[a1 + 2] * u[2], z1 = P[a1] * f[0] + P[a1 + 1] * f[1] + P[a1 + 2] * f[2];
                        float x2 = P[a2] * r[0] + P[a2 + 1] * r[1] + P[a2 + 2] * r[2], y2 = P[a2] * u[0] + P[a2 + 1] * u[1] + P[a2 + 2] * u[2], z2 = P[a2] * f[0] + P[a2 + 1] * f[1] + P[a2 + 2] * f[2];
                        // flat shading from the normal (both faces lit: NUD winding isn't consistent)
                        float ux = x1 - x0, uy = y1 - y0, uz = z1 - z0, vx = x2 - x0, vy = y2 - y0, vz = z2 - z0;
                        float nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
                        float nl = (float)Math.Sqrt(nx * nx + ny * ny + nz * nz);
                        if (nl < 1e-9f) continue;
                        float light = Math.Abs(-0.3f * nx + 0.55f * ny - 0.78f * nz) / nl;
                        // brighter than plain diffuse: the game's lights and soft lighting lift the textures
                        float shade = 0.75f + 0.55f * light;
                        if (tex != null)
                        {
                            int i0 = t[i] * 2, i1 = t[i + 1] * 2, i2 = t[i + 2] * 2;
                            tv[0] = p.UV[i0]; tv[1] = p.UV[i0 + 1]; tv[2] = p.UV[i1]; tv[3] = p.UV[i1 + 1]; tv[4] = p.UV[i2]; tv[5] = p.UV[i2 + 1];
                            Tri(pix, zbuf, w, h, cx + x0 * zoom, cy - y0 * zoom, z0, cx + x1 * zoom, cy - y1 * zoom, z1,
                                cx + x2 * zoom, cy - y2 * zoom, z2, 0, shade, tex, tv, p.AlphaTest || tex.HasAlpha);
                        }
                        else
                        {
                            int cr = Clamp((int)((196 + tint) * shade)), cg = Clamp((int)((188 + tint / 2) * shade)), cb = Clamp((int)((178 - tint) * shade));
                            int col = unchecked((int)0xFF000000) | cr << 16 | cg << 8 | cb;
                            Tri(pix, zbuf, w, h, cx + x0 * zoom, cy - y0 * zoom, z0, cx + x1 * zoom, cy - y1 * zoom, z1,
                                cx + x2 * zoom, cy - y2 * zoom, z2, col, 1, null, null, false);
                        }
                    }
                }
            }
        }

        static int Clamp(int v) { return v < 0 ? 0 : v > 255 ? 255 : v; }

        /// <summary>One triangle into the z-buffer: a flat color, or the texture (affine UVs: the view
        /// is orthographic) times the shade. Texels with little alpha are left out (alpha test).</summary>
        static void Tri(int[] pix, float[] zb, int w, int h, float ax, float ay, float az, float bx, float by, float bz,
                        float cx, float cy, float cz, int col, float shade, Texture tex, float[] uv, bool alphaTest)
        {
            int minX = Math.Max(0, (int)Math.Floor(Math.Min(ax, Math.Min(bx, cx))));
            int maxX = Math.Min(w - 1, (int)Math.Ceiling(Math.Max(ax, Math.Max(bx, cx))));
            int minY = Math.Max(0, (int)Math.Floor(Math.Min(ay, Math.Min(by, cy))));
            int maxY = Math.Min(h - 1, (int)Math.Ceiling(Math.Max(ay, Math.Max(by, cy))));
            if (minX > maxX || minY > maxY) return;
            float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
            if (Math.Abs(area) < 1e-6f) return;
            float inv = 1 / area;
            int sh = (int)(shade * 256);
            for (int y = minY; y <= maxY; y++)
            {
                float py = y + 0.5f;
                for (int x = minX; x <= maxX; x++)
                {
                    float px = x + 0.5f;
                    float w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) * inv;
                    float w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) * inv;
                    float w2 = 1 - w0 - w1;
                    if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                    float z = w0 * az + w1 * bz + w2 * cz;
                    int i = y * w + x;
                    if (z >= zb[i]) continue;
                    if (tex != null)
                    {
                        int c = tex.Sample(w0 * uv[0] + w1 * uv[2] + w2 * uv[4], w0 * uv[1] + w1 * uv[3] + w2 * uv[5]);
                        if (alphaTest && (uint)c >> 24 < 128) continue;
                        int rr = (c >> 16 & 255) * sh >> 8, gg = (c >> 8 & 255) * sh >> 8, bb = (c & 255) * sh >> 8;
                        pix[i] = unchecked((int)0xFF000000) | Math.Min(255, rr) << 16 | Math.Min(255, gg) << 8 | Math.Min(255, bb);
                    }
                    else
                        pix[i] = col;
                    zb[i] = z;
                }
            }
        }

        void DrawGround(Graphics g, float[] r, float[] u)
        {
            float d;
            var a = Project(new[] { 0f, 0f, -60f }, r, u, out d);
            var b = Project(new[] { 0f, 0f, 60f }, r, u, out d);
            using (var pen = new Pen(Color.FromArgb(150, 120, 130, 150), 2))
                g.DrawLine(pen, a, b);
        }

        void DrawBones(Graphics g, float[] r, float[] u)
        {
            var bones = Assets.Skeleton.Bones;
            using (var pen = new Pen(Color.FromArgb(200, 30, 30, 30), 1))
                for (int i = 0; i < bones.Count; i++)
                {
                    int pa = bones[i].Parent;
                    if (pa < 0 || pa >= bones.Count) continue;
                    float d;
                    var a = Project(world[pa].Transform(0, 0, 0), r, u, out d);
                    var b = Project(world[i].Transform(0, 0, 0), r, u, out d);
                    g.DrawLine(pen, a, b);
                }
        }

        /// <summary>Where a hitbox is in model space: its offset from its bone (scale left out, as the
        /// game and Smash Forge do), and the second end of an extended (capsule) one.</summary>
        public bool HitboxEnds(HitboxData hb, out float[] a, out float[] b)
        {
            a = b = null;
            if (world == null) return false;
            int bi = Assets.Skeleton.ScriptBone(hb.Bone);
            var m = world[bi].ClearScale();
            a = m.Transform(hb.X, hb.Y, hb.Z);
            b = hb.Extended ? m.Transform(hb.X2, hb.Y2, hb.Z2) : a;
            return true;
        }

        void DrawHitboxes(Graphics g, float[] r, float[] u)
        {
            if (Frame == null) return;
            foreach (var hb in Frame.Hitboxes)
            {
                float[] a, b;
                if (!HitboxEnds(hb, out a, out b)) continue;
                float d;
                var pa = Project(a, r, u, out d);
                var pb = Project(b, r, u, out d);
                float rad = Math.Max(1.5f, hb.Size * zoom);
                var col = hb.Windbox ? Color.FromArgb(255, 255, 255) : HitboxColors[((hb.Id % 8) + 8) % 8];
                using (var path = new GraphicsPath())
                {
                    path.AddEllipse(pa.X - rad, pa.Y - rad, rad * 2, rad * 2);
                    if (hb.Extended)
                    {
                        path.AddEllipse(pb.X - rad, pb.Y - rad, rad * 2, rad * 2);
                        float dx = pb.X - pa.X, dy = pb.Y - pa.Y, l = (float)Math.Sqrt(dx * dx + dy * dy);
                        if (l > 0.01f)
                        {
                            float nx = -dy / l * rad, ny = dx / l * rad;
                            path.AddPolygon(new[] { new PointF(pa.X + nx, pa.Y + ny), new PointF(pb.X + nx, pb.Y + ny),
                                                    new PointF(pb.X - nx, pb.Y - ny), new PointF(pa.X - nx, pa.Y - ny) });
                        }
                    }
                    path.FillMode = FillMode.Winding;
                    using (var br = new SolidBrush(Color.FromArgb(hb.Id == SelectedHitbox ? 150 : 95, col)))
                        g.FillPath(br, path);
                    using (var pen = new Pen(Color.FromArgb(hb.Id == SelectedHitbox ? 255 : 170, Darker(col)), hb.Id == SelectedHitbox ? 2.5f : 1f))
                        g.DrawPath(pen, path);
                }
                if (ShowAngles)
                {
                    float len = rad + 10;
                    if (hb.Angle == 361)
                        g.DrawString("S", Font, Brushes.Black, pa.X - 4, pa.Y - 6);
                    else
                    {
                        // the angle is in the fighter's facing plane: forward = model +Z, up = +Y
                        double ang = hb.Angle * Math.PI / 180;
                        var tip = Project(new[] { a[0], a[1] + (float)Math.Sin(ang) * len / zoom, a[2] + (float)Math.Cos(ang) * len / zoom }, r, u, out d);
                        using (var pen = new Pen(Color.Black, 1.5f) { EndCap = LineCap.ArrowAnchor })
                            g.DrawLine(pen, pa, tip);
                    }
                }
            }
        }

        static Color Darker(Color c) { return Color.FromArgb(c.R * 6 / 10, c.G * 6 / 10, c.B * 6 / 10); }

        // ---- effects (v1.5.0) ---------------------------------------------------------------------------------------
        readonly Dictionary<float, Mat4[]> worldAt = new Dictionary<float, Mat4[]>();
        Omo worldAnim;

        /// <summary>The skeleton on an animation frame (cached per frame while the animation is the same).</summary>
        Mat4[] WorldAt(float frame)
        {
            if (Assets == null) return null;
            if (Animation != null && Animation.Frames > 0) frame = Math.Max(0, Math.Min(frame, Animation.Frames - 1));
            else frame = 0;
            if (worldAnim != Animation) { worldAt.Clear(); worldAnim = Animation; }
            Mat4[] w;
            if (!worldAt.TryGetValue(frame, out w))
            {
                if (worldAt.Count > 400) worldAt.Clear();
                w = Assets.Skeleton.World(Animation, frame);
                worldAt[frame] = w;
            }
            return w;
        }

        /// <summary>An effect's frame in model space: its bone (on its spawn frame for a one-shot effect, now for a
        /// following one; scale left out, as for hitboxes), then its offset and its turn (degrees, X then Y then Z as the
        /// VBN's; the game's order for effects isn't confirmed). Null when its bone isn't known.</summary>
        public Mat4 EffectMatrix(EffectData e)
        {
            var local = Mat4.TRS(new[] { e.X, e.Y, e.Z },
                Mat4.EulerToQuat(e.RX * (float)Math.PI / 180, e.RY * (float)Math.PI / 180, e.RZ * (float)Math.PI / 180),
                new[] { 1f, 1f, 1f });
            if (e.World) return local;
            float at = e.DetachFrame >= 0 ? e.DetachAnimFrame : e.Follow ? AnimFrame : e.SpawnAnimFrame;
            var w = WorldAt(at);
            if (w == null || e.Bone < 0) return null;
            int bi = Assets.Skeleton.ScriptBone(e.Bone);
            if (bi < 0 || bi >= w.Length) return null;
            return w[bi].ClearScale() * local;
        }

        /// <summary>The colour an effect is drawn with: its set colour (scaled into 0-255 when over 1), else grey-blue.</summary>
        public static Color EffectColor(EffectData e)
        {
            if (!e.HasColor) return Color.FromArgb(70, 110, 200);
            float m = Math.Max(1, Math.Max(e.R, Math.Max(e.G, e.B)));
            Func<float, int> c = v => Math.Max(0, Math.Min(255, (int)(v / m * 255)));
            return Color.FromArgb(c(e.R), c(e.G), c(e.B));
        }

        void DrawEffects(Graphics g, float[] r, float[] u)
        {
            if (Frame == null || Frame.Effects == null) return;
            float d;
            var labels = new List<RectangleF>();          // placed so far: a label overlapping one goes below it
            foreach (var e in Frame.Effects)
            {
                var m = EffectMatrix(e);
                if (m == null) continue;
                bool sel = e.Index == SelectedEffect;
                var col = EffectColor(e);
                float size = Math.Max(0.05f, e.Size * (e.HasScale ? Math.Max(e.SX, Math.Max(e.SY, e.SZ)) : 1));
                var o = Project(m.Transform(0, 0, 0), r, u, out d);
                float rad = Math.Max(3, 2f * size * zoom);
                int a = (int)(Math.Max(0.15f, Math.Min(1, e.A)) * (sel ? 120 : 70));
                using (var br = new SolidBrush(Color.FromArgb(a, col)))
                    g.FillEllipse(br, o.X - rad, o.Y - rad, rad * 2, rad * 2);
                using (var pen = new Pen(Color.FromArgb(sel ? 255 : 200, Darker(col)), sel ? 2.5f : 1.2f))
                {
                    if (!e.Follow || e.DetachFrame >= 0) pen.DashStyle = DashStyle.Dash;     // one-shot: dashed
                    g.DrawEllipse(pen, o.X - rad, o.Y - rad, rad * 2, rad * 2);
                }
                // its axes: X red, Y green, Z (its forward) blue
                float len = Math.Max(1.5f, 2f * size);
                var axes = new[] { Tuple.Create(new[] { len, 0f, 0f }, Color.FromArgb(220, 40, 40)),
                                   Tuple.Create(new[] { 0f, len, 0f }, Color.FromArgb(30, 170, 30)),
                                   Tuple.Create(new[] { 0f, 0f, len }, Color.FromArgb(40, 70, 230)) };
                foreach (var ax in axes)
                    using (var pen = new Pen(ax.Item2, 1.5f) { EndCap = LineCap.ArrowAnchor })
                        g.DrawLine(pen, o, Project(m.Transform(ax.Item1[0], ax.Item1[1], ax.Item1[2]), r, u, out d));
                if (ShowEffectLabels)
                {
                    string label = EffectLabel != null ? EffectLabel(e) : "0x" + e.IdFor(Flip).ToString("X");
                    if (Flip && FacingRule.Check(e).Length > 0) label = "! " + label;
                    var sz = g.MeasureString(label, Font);
                    var at = new RectangleF(o.X + rad * 0.7f + 2, o.Y - rad * 0.7f - 12, sz.Width, sz.Height);
                    for (int k = 0; k < 40 && labels.Any(x => x.IntersectsWith(at)); k++) at.Y += sz.Height;
                    labels.Add(at);
                    using (var br = new SolidBrush(Color.FromArgb(230, Darker(Darker(col)))))
                        g.DrawString(label, Font, br, at.X, at.Y);
                }
            }
        }

        /// <summary>A trail's two points in model space on an animation frame (bone 1 + offset 1, bone 2 + offset 2).</summary>
        bool TrailPoints(TrailData t, float frame, out float[] a, out float[] b)
        {
            a = b = null;
            var w = WorldAt(frame);
            if (w == null) return false;
            int b1 = Assets.Skeleton.ScriptBone(t.Bone1), b2 = Assets.Skeleton.ScriptBone(t.Bone2);
            if (b1 < 0 || b1 >= w.Length || b2 < 0 || b2 >= w.Length) return false;
            a = w[b1].ClearScale().Transform(t.X1, t.Y1, t.Z1);
            b = w[b2].ClearScale().Transform(t.X2, t.Y2, t.Z2);
            return true;
        }

        void DrawTrails(Graphics g, float[] r, float[] u)
        {
            if (Frame == null || Frame.Trails == null) return;
            float d;
            foreach (var t in Frame.Trails)
            {
                float[] a, b;
                bool fading = t.EndFrame >= 0 && Frame.GameFrame >= t.EndFrame;
                // the history: the blade on the frames before, back to the trail's start (BlurLength of them, at
                // least 4, at most 12), fading out
                int n = Math.Min(Math.Max(4, Math.Min(t.Blur, 12)), Math.Max(0, Frame.GameFrame - t.StartFrame));
                var pts = new List<PointF[]>();
                if (!fading && TrailPoints(t, AnimFrame, out a, out b))
                    pts.Add(new[] { Project(a, r, u, out d), Project(b, r, u, out d) });
                for (int k = 0; k < n && k < TrailFrames.Count; k++)
                    if (TrailPoints(t, TrailFrames[k], out a, out b))
                        pts.Add(new[] { Project(a, r, u, out d), Project(b, r, u, out d) });
                for (int k = 0; k + 1 < pts.Count; k++)
                {
                    int alpha = Math.Max(10, 120 - 110 * k / Math.Max(1, pts.Count - 1));
                    using (var br = new SolidBrush(Color.FromArgb(alpha, 255, 200, 60)))
                        g.FillPolygon(br, new[] { pts[k][0], pts[k][1], pts[k + 1][1], pts[k + 1][0] });
                }
                if (pts.Count > 0 && !fading)
                    using (var pen = new Pen(Color.FromArgb(230, 200, 120, 0), 2.5f))
                        g.DrawLine(pen, pts[0][0], pts[0][1]);
            }
        }

        void DrawTrajectory(Graphics g, float[] r, float[] u)
        {
            if (Trajectory == null || Trajectory.Count < 2 || Frame == null) return;
            float[] a = TrajectoryOrigin, b;
            if (a == null)
            {
                var hb = Frame.Hitboxes.Find(x => x.Id == SelectedHitbox);
                if (hb == null || !HitboxEnds(hb, out a, out b)) return;
            }
            var pts = new List<PointF>();
            float d;
            foreach (var p in Trajectory)
                pts.Add(Project(new[] { a[0], a[1] + p[1], a[2] + p[0] }, r, u, out d));
            using (var pen = new Pen(Color.FromArgb(200, 20, 20, 120), 1.5f) { DashStyle = DashStyle.Dash })
                g.DrawLines(pen, pts.ToArray());
        }

        void DrawStatus(Graphics g)
        {
            if (EnemyStatus != null)
                g.DrawString(EnemyStatus, Font, Brushes.DarkRed, 6, 22);
            if (Frame == null) return;
            var parts = new List<string>();
            if (Frame.Intangible) parts.Add("intangible");
            if (Frame.Invincible) parts.Add("invincible");
            if (Frame.SuperArmor) parts.Add("super armor");
            if (parts.Count > 0)
                g.DrawString(string.Join(", ", parts.ToArray()), Font, Brushes.DarkBlue, 6, 6);
            if (Flip)
                g.DrawString("Facing left (turned round). ! = an effect call the God Fist / Core Breaker ports found looks different facing left",
                             Font, Brushes.DarkMagenta, 6, Height - 18);
            if (Frame.Screen != null && Frame.Screen.Count > 0)
                g.DrawString("Screen: " + string.Join("; ", Frame.Screen.Select(x => x.Text).ToArray()), Font, Brushes.DarkGreen, 6, 38);
        }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            dragFrom = e.Location;
            dragButton = e.Button;
            Focus();
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            if (dragButton == MouseButtons.None) return;
            viewMoved = true;
            int dx = e.X - dragFrom.X, dy = e.Y - dragFrom.Y;
            dragFrom = e.Location;
            if (dragButton == MouseButtons.Left)
            {
                yaw += dx * 0.01f;
                pitch = Math.Max(-1.5f, Math.Min(1.5f, pitch + dy * 0.01f));
            }
            else { panX += dx; panY += dy; }
            Invalidate();
        }

        protected override void OnMouseUp(MouseEventArgs e) { dragButton = MouseButtons.None; }

        protected override void OnMouseWheel(MouseEventArgs e)
        {
            viewMoved = true;
            zoom = Math.Max(1f, Math.Min(80f, zoom * (e.Delta > 0 ? 1.15f : 1 / 1.15f)));
            Invalidate();
        }

        protected override void OnMouseDoubleClick(MouseEventArgs e) { ResetView(); }
    }
}
