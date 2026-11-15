using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// v1.6.0 (Level 2): the effects drawn into the viewport's pixels: each effect's .ptcl particles (EffectSim, stepped
    /// from the effect's start to the shown frame), its effect model (animated from its spawn) and the sword trails as
    /// textured ribbons, blended (alpha / add / subtract) over the fighter, depth-tested against it. Level 1's markers
    /// stay as their own toggle (ShowEffects).
    /// </summary>
    public partial class Viewport
    {
        public bool ShowParticles = true;           // particles, effect models, textured trails
        public bool HighQuality;                    // bilinear textures, more particles
        public bool DarkBackground = true;          // additive effects show as they do in game (on a dark stage)
        public Func<uint, EffectAssets> GetEffectAssets;
        public Func<int, Texture> GetTrailTexture;
        public List<FrameState> History;            // every game frame of the run (index = game frame - 1)
        public string FxStats = "";
        public string MarkerOnlyHint = "";          // v1.6.1: why effects stay markers (no common bank found)

        readonly Dictionary<string, EffectSim> sims = new Dictionary<string, EffectSim>();

        public int CapPerEmitter { get { return HighQuality ? 600 : 150; } }
        public int MaxQuads { get { return HighQuality ? 8000 : 2500; } }

        /// <summary>Forget the simulated effects (a new run of the scripts, another quality).</summary>
        public void ResetEffects()
        {
            sims.Clear();
            Invalidate();
        }

        Color Background { get { return DarkBackground ? Color.FromArgb(34, 37, 46) : BackColor; } }

        /// <summary>A text colour that reads on the background (the dark one gets the lighter shade).</summary>
        Color Ink(Color dark)
        {
            if (!DarkBackground) return dark;
            return Color.FromArgb(dark.A, 255 - (255 - Math.Min(255, dark.R * 2 + 40)) / 2, 255 - (255 - Math.Min(255, dark.G * 2 + 40)) / 2,
                                  255 - (255 - Math.Min(255, dark.B * 2 + 40)) / 2);
        }

        /// <summary>The animation frame game frame g showed (the run's history), else the shown one.</summary>
        public float AnimFrameAt(int g)
        {
            if (History != null && g >= 1 && g <= History.Count) return Math.Max(0, History[g - 1].AnimFrame);
            return AnimFrame;
        }

        /// <summary>Where an effect is on game frame g (effect -> model space, no size): its bone on that frame while it
        /// follows, on its spawn frame for a one-shot, on its detach frame once detached.</summary>
        public Mat4 EffectMatrixAt(EffectData e, int g)
        {
            var local = Mat4.TRS(new[] { e.X, e.Y, e.Z },
                Mat4.EulerToQuat(e.RX * (float)Math.PI / 180, e.RY * (float)Math.PI / 180, e.RZ * (float)Math.PI / 180),
                new[] { 1f, 1f, 1f });
            if (e.World) return local;
            float at = e.DetachFrame >= 0 && g >= e.DetachFrame ? e.DetachAnimFrame : e.Follow ? AnimFrameAt(g) : e.SpawnAnimFrame;
            var w = WorldAt(at);
            if (w == null || e.Bone < 0) return null;
            int bi = Assets.Skeleton.ScriptBone(e.Bone);
            if (bi < 0 || bi >= w.Length) return null;
            return w[bi].ClearScale() * local;
        }

        /// <summary>The effect's simulation stepped to game frame g (made on first use; null when its id has nothing to
        /// draw: a common effect, or files not found).</summary>
        public EffectSim SimFor(EffectData e, int g)
        {
            if (GetEffectAssets == null) return null;
            uint id = e.IdFor(Flip);
            string key = e.Index + ":" + id.ToString("X") + ":" + CapPerEmitter;
            EffectSim s;
            if (!sims.TryGetValue(key, out s))
            {
                var a = id != 0 ? GetEffectAssets(id) : null;
                s = a != null ? new EffectSim(e, a, CapPerEmitter) : null;
                sims[key] = s;
            }
            if (s == null) return null;
            // the shown frame's copy of the call (its LAST_EFFECT_SET_* values, its detach)
            s.Effect.DetachFrame = e.DetachFrame;
            s.Effect.DetachAnimFrame = e.DetachAnimFrame;
            if (s.Effect.Rate != e.Rate) { s.Effect.Rate = e.Rate; s.Reset(); }     // (v1.6.1: its rate set after it)
            s.StepTo(g, k => EffectMatrixAt(s.Effect, k));
            return s;
        }

        /// <summary>A call's colour as the drawn effect takes it (v1.6.2, as the game: the colour commands' 0-255 values / 255,
        /// the alphas' percents / 100, LAST_PARTICLE_SET_COLOR's multipliers on top); it multiplies every emitter's colour
        /// (x the emitter's own colour x its particles') and the effect model's colour gain.</summary>
        public static void CallColour(EffectData e, out float r, out float g, out float b, out float a)
        {
            r = e.HasColor ? e.CR : 1; g = e.HasColor ? e.CG : 1; b = e.HasColor ? e.CB : 1;
            if (e.HasParticleColor) { r *= e.PR; g *= e.PG; b *= e.PB; }
            a = e.HasAlpha ? Math.Max(0, e.CA) : 1;
        }

        /// <summary>(v1.7.1) The fighter's own colour for an effect (common attack arcs / streaks), or null: the viewer sets it
        /// (EffectLibrary.FighterColour).</summary>
        public Func<uint, float[]> GetFighterColour;

        /// <summary>(v1.7.1) The fighter's colour for the call's effect, when the call sets none of its own: the game's
        /// EffectModule colours a request whose id is in its table (fighter_param 0x13C-0x147 for the common effects
        /// fighter_param_etc g14 lists, 0x8D / 0x92 / 0x8E / 0x90; set at 0x02E136EC, applied at 0x02C29F00 / 0x02C2AC44 /
        /// 0x02C2B524 as LAST_EFFECT_SET_COLOR's emitter-set colour, which a colour command after it replaces): Dr. Mario's
        /// and Mario's arcs (3, 0.7, 0.25), Pac-Man's streaks (2, 0.65, 0.55). Kept as the call's colour times the
        /// LAST_PARTICLE_SET_COLOR multipliers.</summary>
        void FighterColour(EffectData e, ref float r, ref float g, ref float b)
        {
            if (e.HasColor || GetFighterColour == null) return;
            var c = GetFighterColour(e.IdFor(Flip));
            if (c == null) return;
            r *= c[0]; g *= c[1]; b *= c[2];
        }

        /// <summary>A triangle list to draw: screen corners (x, y, depth), UVs, texture, colour, blend.</summary>
        class FxItem
        {
            public float Depth;
            public float[] S;           // x y z per vertex
            public int[] Idx;
            public float[] UV;          // u v per vertex
            public float[] VCol;        // r g b a per vertex, or null
            public Texture Tex;
            public float R, G, B, A;
            public float[] Col1;
            public int Blend, Combiner = 1;
            public Texture Mask;        // a particle's texture slot 1 (v1.6.1)
            public float MaskU = 1, MaskV = 1;
            public float[] T;           // a trail: t per vertex (0 at the blade, 1 at the tail end)
            public Texture Tex1;        // a trail's second texture
            public int Shader;          // a trail's shader (> 0: drawn by FxRaster.TrailTri)
            public float Fade = 1;
            public int Wrap = 0x11, MaskWrap = 0x11;    // (v1.7.1) U wrap | V wrap << 4: 0 mirror, 1 repeat, 2 clamp
        }

        static readonly float[] QuadPos = { -0.5f, 0.5f, 0, 0.5f, 0.5f, 0, 0.5f, -0.5f, 0, -0.5f, -0.5f, 0 };
        static readonly float[] QuadUV = { 0, 0, 1, 0, 1, 1, 0, 1 };
        static readonly int[] QuadIdx = { 0, 1, 2, 0, 2, 3 };
        static readonly float[] XZ = { 1, 0, 0, 0, 0, -1, 0, 1, 0 };          // a plate's Y onto the emitter's Z
        static readonly float[] XZT = { 1, 0, 0, 0, 0, 1, 0, -1, 0 };

        /// <summary>v1.6.2 (tests): an effect's particles on game frame g as the view would draw them: per particle its
        /// corners on screen (x, y, depth) and their UVs.</summary>
        public List<Tuple<float[], float[]>> EffectScreenQuads(EffectData e, int g)
        {
            var o = new List<Tuple<float[], float[]>>();
            int w = Math.Max(1, Width), h = Math.Max(1, Height);
            float[] r, u, f;
            Axes(out r, out u, out f);
            float cx = w / 2f + panX, cy = h * 0.72f + panY;
            var sim = SimFor(e, g);
            if (sim == null || sim.Call == null) return o;
            float cr, cg, cb, ca;
            CallColour(e, out cr, out cg, out cb, out ca);
            FighterColour(e, ref cr, ref cg, ref cb);
            foreach (var es in sim.Emitters)
            {
                if (es.D.Distortion || es.D.Tex == null) continue;       // (as drawn: v1.6.3)
                if (es.D.PType == 6)
                {
                    var it6 = StripeItem(sim, es, es.Live.AsEnumerable().Reverse().ToList(), null, sim.NextK - 1, r, u, f, cx, cy, cr, cg, cb, 1);
                    if (it6 != null) o.Add(Tuple.Create(it6.S, it6.UV));
                    continue;
                }
                foreach (var q in es.Live)
                {
                    var it = es.D.PType == 5 ? StripeItem(sim, es, null, q, sim.NextK - 1, r, u, f, cx, cy, cr, cg, cb, 1)
                                             : ParticleItem(sim, es, q, sim.NextK - 1, r, u, f, cx, cy, cr, cg, cb, 1);
                    if (it != null) o.Add(Tuple.Create(it.S, it.UV));
                }
            }
            return o;
        }

        /// <summary>v1.6.3 (tests): a mesh's vertices as drawn on this frame (skinned, billboard sprites turned to the
        /// camera), in model space; null when the mesh isn't found.</summary>
        public float[] MeshVertices(string mesh)
        {
            if (Assets == null) return null;
            float[] r, u, f;
            Axes(out r, out u, out f);
            var s = Skin(Assets, Assets.Skeleton.World(Animation, AnimFrame), 0, 0, false);
            FaceCamera(s, r, u, f);
            int k = 0;
            foreach (var m in Assets.Model.Meshes)
            {
                var o = new List<float>();
                foreach (var p in m.Polys)
                {
                    int b = s.PolyStart[k++];
                    for (int i = 0; i < p.Pos.Length; i++) o.Add(s.Pos[b + i]);
                }
                if (m.Name.StartsWith(mesh, StringComparison.OrdinalIgnoreCase)) return o.ToArray();
            }
            return null;
        }

        /// <summary>v1.6.3 (tests): the camera's axes (right, up, into the screen).</summary>
        public void CameraAxes(out float[] r, out float[] u, out float[] f) { Axes(out r, out u, out f); }

        /// <summary>v1.6.2 (tests): a model-space point on screen (x, y).</summary>
        public float[] ScreenOf(float[] p)
        {
            float[] r, u, f;
            Axes(out r, out u, out f);
            float d;
            var s = Project(p, r, u, out d);
            return new[] { s.X, s.Y };
        }

        /// <summary>Particles, effect models and trails into the pixels (after the opaque models).</summary>
        void DrawFx(int[] pix, float[] zb, int w, int h, float[] r, float[] u, float[] f)
        {
            FxStats = "";
            if (Frame == null || !ShowParticles) return;
            float cx = w / 2f + panX, cy = h * 0.72f + panY;
            int g = Frame.GameFrame;
            var items = new List<FxItem>();
            int particles = 0, models = 0, markerOnly = 0, quads = 0, capped = 0, untextured = 0;
            if (Frame.Effects != null)
                foreach (var e in Frame.Effects)
                {
                    var sim = SimFor(e, g);
                    if (sim == null || sim.Call == null) { markerOnly++; continue; }
                    float cr, cg, cb, ca;
                    CallColour(e, out cr, out cg, out cb, out ca);
                    FighterColour(e, ref cr, ref cg, ref cb);
                    if (sim.Assets.Model != null)
                    {
                        AddModel(sim, sim.ModelFrame(g), items, r, u, f, cx, cy, cr, cg, cb, ca);
                        models++;
                    }
                    foreach (var es in sim.Emitters)
                    {
                        particles += es.Live.Count;
                        if (es.Live.Count >= sim.Cap) capped++;
                        if (es.D.Distortion) continue;
                        // v1.6.3: an emitter whose texture can't be read isn't drawn (a quad with no texture is a solid
                        // block: Pac-Man's / Link's common effects drew translucent squares and bars)
                        if (es.D.Tex == null) { untextured++; continue; }
                        if (es.D.PType == 6)
                        {
                            // a complex stripe: one ribbon through the emitter's particles, newest first
                            var it6 = StripeItem(sim, es, es.Live.AsEnumerable().Reverse().ToList(), null, sim.NextK - 1, r, u, f, cx, cy, cr, cg, cb, ca);
                            if (it6 != null) { items.Add(it6); quads++; }
                            continue;
                        }
                        foreach (var q in es.Live)
                        {
                            if (quads >= MaxQuads) break;
                            var it = es.D.PType == 5 ? StripeItem(sim, es, null, q, sim.NextK - 1, r, u, f, cx, cy, cr, cg, cb, ca)
                                                     : ParticleItem(sim, es, q, sim.NextK - 1, r, u, f, cx, cy, cr, cg, cb, ca);
                            if (it != null) { items.Add(it); quads++; }
                        }
                    }
                }
            if (ShowTrails && Frame.Trails != null && GetTrailTexture != null)
                foreach (var t in Frame.Trails)
                    AddTrail(t, items, r, u, f, cx, cy);
            // far to near (alpha blending needs it; additive doesn't mind)
            items.Sort((a, b) => b.Depth.CompareTo(a.Depth));
            // HQ: full resolution, bilinear textures. Otherwise the effects are drawn at half resolution over a half-size
            // copy of the picture (its depth the nearest of each 2 x 2) and what they changed is added back, smoothed
            // (four times fewer pixels to fill: the big glows of an explosion stay quick)
            bool half = !HighQuality && items.Count > 0;
            int tw = w, th = h;
            int[] tp = pix, basePix = null;
            float[] tz = zb;
            float sc = 1;
            if (half)
            {
                tw = (w + 1) / 2; th = (h + 1) / 2; sc = 0.5f;
                tp = new int[tw * th]; tz = new float[tw * th];
                for (int y = 0; y < th; y++)
                    for (int x = 0; x < tw; x++)
                    {
                        int r0 = 0, g0 = 0, b0 = 0, n = 0;
                        float z = float.MaxValue;
                        for (int dy = 0; dy < 2; dy++)
                            for (int dx = 0; dx < 2; dx++)
                            {
                                int xx = 2 * x + dx, yy = 2 * y + dy;
                                if (xx >= w || yy >= h) continue;
                                int c = pix[yy * w + xx];
                                r0 += c >> 16 & 255; g0 += c >> 8 & 255; b0 += c & 255; n++;
                                z = Math.Min(z, zb[yy * w + xx]);
                            }
                        tp[y * tw + x] = unchecked((int)0xFF000000) | r0 / n << 16 | g0 / n << 8 | b0 / n;
                        tz[y * tw + x] = z;
                    }
                basePix = (int[])tp.Clone();
            }
            foreach (var it in items)
            {
                var S = it.S;
                if (half)
                {
                    S = (float[])S.Clone();
                    for (int i = 0; i + 2 < S.Length; i += 3) { S[i] *= sc; S[i + 1] *= sc; }
                }
                // bilinear on HQ, and whenever a texture is blown up past twice its size (else it shows its texels)
                bool bil = HighQuality;
                if (!bil && it.Tex != null)
                {
                    float x0 = float.MaxValue, x1 = float.MinValue, y0 = float.MaxValue, y1 = float.MinValue;
                    for (int i = 0; i + 2 < S.Length; i += 3)
                    {
                        x0 = Math.Min(x0, S[i]); x1 = Math.Max(x1, S[i]); y0 = Math.Min(y0, S[i + 1]); y1 = Math.Max(y1, S[i + 1]);
                    }
                    bil = Math.Max(x1 - x0, y1 - y0) > 2 * Math.Max(it.Tex.Width, it.Tex.Height);
                }
                var uv = new float[6];
                float[] vc = it.VCol != null ? new float[12] : null;
                for (int k = 0; k + 2 < it.Idx.Length; k += 3)
                {
                    int i0 = it.Idx[k], i1 = it.Idx[k + 1], i2 = it.Idx[k + 2];
                    if (it.Shader > 0)
                    {
                        FxRaster.TrailTri(tp, tz, tw, th, S[i0 * 3], S[i0 * 3 + 1], S[i0 * 3 + 2], S[i1 * 3], S[i1 * 3 + 1], S[i1 * 3 + 2],
                                          S[i2 * 3], S[i2 * 3 + 1], S[i2 * 3 + 2],
                                          new[] { it.UV[i0 * 2], it.UV[i0 * 2 + 1], it.UV[i1 * 2], it.UV[i1 * 2 + 1], it.UV[i2 * 2], it.UV[i2 * 2 + 1] },
                                          new[] { it.T[i0], it.T[i1], it.T[i2] }, it.Tex, it.Tex1, it.Shader, it.Fade, bil);
                        continue;
                    }
                    uv[0] = it.UV[i0 * 2]; uv[1] = it.UV[i0 * 2 + 1]; uv[2] = it.UV[i1 * 2]; uv[3] = it.UV[i1 * 2 + 1];
                    uv[4] = it.UV[i2 * 2]; uv[5] = it.UV[i2 * 2 + 1];
                    if (vc != null)
                        for (int c = 0; c < 4; c++) { vc[c] = it.VCol[i0 * 4 + c]; vc[4 + c] = it.VCol[i1 * 4 + c]; vc[8 + c] = it.VCol[i2 * 4 + c]; }
                    FxRaster.Tri(tp, tz, tw, th, S[i0 * 3], S[i0 * 3 + 1], S[i0 * 3 + 2], S[i1 * 3], S[i1 * 3 + 1], S[i1 * 3 + 2],
                                 S[i2 * 3], S[i2 * 3 + 1], S[i2 * 3 + 2], uv, it.Tex, bil, it.R, it.G, it.B, it.A, it.Col1, vc, it.Blend, it.Combiner,
                                 it.Mask, it.MaskU, it.MaskV, it.Wrap, it.MaskWrap);
                }
            }
            if (half) Upsample(pix, w, h, tp, basePix, tw, th);
            if (particles > 0 || models > 0 || markerOnly > 0)
                FxStats = particles + " particles" + (models > 0 ? ", " + models + " effect model" + (models > 1 ? "s" : "") : "") +
                          (markerOnly > 0 ? ", " + markerOnly + " effect" + (markerOnly > 1 ? "s" : "") + " marker only (files not found" + MarkerOnlyHint + ")" : "") +
                          (capped > 0 || quads >= MaxQuads ? " (capped: HQ for more)" : "") +
                          (untextured > 0 ? ", " + untextured + " emitter" + (untextured > 1 ? "s" : "") + " without a readable texture (not drawn)" : "");
        }

        /// <summary>Adds what the half-resolution pass changed (its pixels less the half-size picture it started from) to
        /// the full-size picture, bilinearly between the half-size pixels.</summary>
        static void Upsample(int[] pix, int w, int h, int[] fx, int[] basePix, int tw, int th)
        {
            int n = tw * th;
            var dr = new short[n]; var dg = new short[n]; var db = new short[n];
            bool any = false;
            for (int i = 0; i < n; i++)
            {
                int a = fx[i], b = basePix[i];
                if (a == b) continue;
                dr[i] = (short)((a >> 16 & 255) - (b >> 16 & 255)); dg[i] = (short)((a >> 8 & 255) - (b >> 8 & 255)); db[i] = (short)((a & 255) - (b & 255));
                any = true;
            }
            if (!any) return;
            for (int y = 0; y < h; y++)
            {
                float sy = Math.Max(0, (y - 0.5f) / 2);
                int y0 = Math.Min(th - 1, (int)sy), y1 = Math.Min(th - 1, y0 + 1);
                float fy = sy - (int)sy;
                for (int x = 0; x < w; x++)
                {
                    float sx = Math.Max(0, (x - 0.5f) / 2);
                    int x0 = Math.Min(tw - 1, (int)sx), x1 = Math.Min(tw - 1, x0 + 1);
                    float fx0 = sx - (int)sx;
                    int i00 = y0 * tw + x0, i10 = y0 * tw + x1, i01 = y1 * tw + x0, i11 = y1 * tw + x1;
                    if (dr[i00] == 0 && dg[i00] == 0 && db[i00] == 0 && dr[i11] == 0 && dg[i11] == 0 && db[i11] == 0 &&
                        dr[i10] == 0 && dg[i10] == 0 && db[i10] == 0 && dr[i01] == 0 && dg[i01] == 0 && db[i01] == 0) continue;
                    float w00 = (1 - fx0) * (1 - fy), w10 = fx0 * (1 - fy), w01 = (1 - fx0) * fy, w11 = fx0 * fy;
                    int c = pix[y * w + x];
                    int r = (c >> 16 & 255) + (int)Math.Round(dr[i00] * w00 + dr[i10] * w10 + dr[i01] * w01 + dr[i11] * w11);
                    int g = (c >> 8 & 255) + (int)Math.Round(dg[i00] * w00 + dg[i10] * w10 + dg[i01] * w01 + dg[i11] * w11);
                    int b = (c & 255) + (int)Math.Round(db[i00] * w00 + db[i10] * w10 + db[i01] * w01 + db[i11] * w11);
                    pix[y * w + x] = unchecked((int)0xFF000000) | Clamp(r) << 16 | Clamp(g) << 8 | Clamp(b);
                }
            }
        }

        /// <summary>
        /// v1.6.3: a stripe (eft's ribbon, particle type 5: through one particle's history of places; 6: through the
        /// emitter's particles, newest first) in screen space: its points smoothed (Catmull-Rom, the stripe's divisions
        /// between each two), its width the particle's scale X across it: facing the camera (stripe type 0), else along
        /// the emitter's Y axis of each point's frame (1 emitter matrix, 2 up-down); connect 2 starts it at the emitter;
        /// alpha from the stripe's start alpha (head) to its end alpha (tail); the texture's U across, V along.
        /// </summary>
        FxItem StripeItem(EffectSim sim, EmitterSim es, List<Particle> chain, Particle q, int k, float[] r, float[] u, float[] f,
                          float cx, float cy, float cr, float cg, float cb, float ca)
        {
            var D = es.D;
            var pts = new List<float[]>();
            var axes = new List<float[]>();
            var widths = new List<float>();
            Particle head = q;
            if (q != null)
            {
                if (q.Hist == null || q.Hist.Count < 2) return null;
                float w = StripeWidth(sim, D, q);
                for (int i = 0; i < q.Hist.Count; i++) { pts.Add(q.Hist[i]); axes.Add(q.HistAxis[i]); widths.Add(w); }
            }
            else
            {
                if (chain == null || chain.Count < 2) return null;
                head = chain[0];
                foreach (var c in chain)
                {
                    pts.Add(es.World(c));
                    axes.Add(es.LastM != null ? Fx.Norm(new[] { es.LastM[0, 1], es.LastM[1, 1], es.LastM[2, 1] }) : new[] { 0f, 1f, 0f });
                    widths.Add(StripeWidth(sim, D, c));
                }
            }
            if (D.StripeConnect == 2 && es.LastM != null)
            {
                pts.Insert(0, new[] { es.LastM[0, 3], es.LastM[1, 3], es.LastM[2, 3] });
                axes.Insert(0, axes[0]); widths.Insert(0, widths[0]);
            }
            // smoothed through the points
            var P = new List<float[]>(); var A = new List<float[]>(); var W = new List<float>();
            int div = Math.Max(1, D.StripeDivide);
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                var p0 = pts[Math.Max(0, i - 1)]; var p1 = pts[i]; var p2 = pts[i + 1]; var p3 = pts[Math.Min(pts.Count - 1, i + 2)];
                for (int s = 0; s < div; s++)
                {
                    float t = s / (float)div, t2 = t * t, t3 = t2 * t;
                    var pt = new float[3];
                    for (int c = 0; c < 3; c++)
                        pt[c] = 0.5f * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3);
                    P.Add(pt);
                    A.Add(axes[i]); W.Add(widths[i] + (widths[i + 1] - widths[i]) * t);
                }
            }
            P.Add(pts[pts.Count - 1]); A.Add(axes[axes.Count - 1]); W.Add(widths[widths.Count - 1]);
            int n = P.Count;
            if (n < 2) return null;
            float t0 = head.Age / (float)Math.Max(1, head.Life);
            float alpha = D.Alpha(Math.Min(1, t0)) * D.A(14, D.EmAlpha, k) * ca;
            if (alpha <= 0.002f) return null;
            var c0 = new float[3];
            D.Colour(0, Math.Min(1, t0), c0);
            var it = new FxItem
            {
                R = c0[0] * D.A(11, D.EmColor0[0], k) * cr, G = c0[1] * D.A(12, D.EmColor0[1], k) * cg,
                B = c0[2] * D.A(13, D.EmColor0[2], k) * cb, A = alpha, Tex = D.Tex,
                Blend = D.Blend == 1 ? FxRaster.Add : D.Blend == 2 ? FxRaster.Sub : FxRaster.Alpha, Combiner = D.Combiner,
                Mask = D.Tex1, MaskU = D.U1Scale / D.UScale, MaskV = D.V1Scale / D.VScale, Wrap = D.Wrap0, MaskWrap = D.Wrap1,
                S = new float[n * 2 * 3], UV = new float[n * 2 * 2], VCol = new float[n * 2 * 4],
            };
            if (D.Combiner == 2 || D.Combiner == 4)      // (v1.7.1: 4 too, 2 with the texture's own alpha: its colour 1 was black)
            {
                var c1 = new float[3];
                D.Colour(1, Math.Min(1, t0), c1);
                // (v1.7.1) the call's colour multiplies colour 1 too: eft's dynamic block takes the emitter set's colour x the
                // colour scale x each of the emitter's two colours (cross_f 0x04A65B2C: [0-2] x +0x218, [4-6] x +0x238)
                it.Col1 = new[] { c1[0] * D.A(19, D.EmColor1[0], k) * cr, c1[1] * D.A(20, D.EmColor1[1], k) * cg, c1[2] * D.A(21, D.EmColor1[2], k) * cb };
            }
            var toCam = new[] { -f[0], -f[1], -f[2] };
            float depth = 0;
            for (int i = 0; i < n; i++)
            {
                var dir = new float[3];
                var pa = P[Math.Max(0, i - 1)]; var pb = P[Math.Min(n - 1, i + 1)];
                for (int c = 0; c < 3; c++) dir[c] = pa[c] - pb[c];
                float[] across = D.StripeType == 0 ? Fx.Cross(dir, toCam) : A[i];
                if (Fx.Len(across) < 1e-6f) across = r;
                across = Fx.Norm(across);
                float half = W[i] / 2, v = i / (float)(n - 1);
                float sa = D.StripeStartAlpha + (D.StripeEndAlpha - D.StripeStartAlpha) * v;
                for (int e2 = 0; e2 < 2; e2++)
                {
                    float sgn = e2 == 0 ? -1 : 1;
                    float wx = P[i][0] + across[0] * half * sgn, wy = P[i][1] + across[1] * half * sgn, wz = P[i][2] + across[2] * half * sgn;
                    int o = (i * 2 + e2);
                    it.S[o * 3] = cx + (wx * r[0] + wy * r[1] + wz * r[2]) * zoom;
                    it.S[o * 3 + 1] = cy - (wx * u[0] + wy * u[1] + wz * u[2]) * zoom;
                    it.S[o * 3 + 2] = wx * f[0] + wy * f[1] + wz * f[2];
                    depth += it.S[o * 3 + 2];
                    it.UV[o * 2] = e2 * D.UScale; it.UV[o * 2 + 1] = v * D.VScale;
                    it.VCol[o * 4] = 1; it.VCol[o * 4 + 1] = 1; it.VCol[o * 4 + 2] = 1; it.VCol[o * 4 + 3] = Math.Max(0, sa);
                }
            }
            var idx = new List<int>();
            for (int i = 0; i + 1 < n; i++) { int a0 = i * 2, a1 = i * 2 + 1, b0 = i * 2 + 2, b1 = i * 2 + 3; idx.AddRange(new[] { a0, b0, b1, a0, b1, a1 }); }
            it.Idx = idx.ToArray();
            it.Depth = depth / (n * 2);
            return it;
        }

        float StripeWidth(EffectSim sim, EmitterDef D, Particle q)
        {
            float t = q.Age / (float)Math.Max(1, q.Life);
            return D.SizeX * D.SizeCurve(0, Math.Min(1, t)) * q.Sr * q.SaX * sim.CSize;
        }

        /// <summary>One particle as a quad (or its emitter's primitive) in screen space, or null when it's invisible.</summary>
        FxItem ParticleItem(EffectSim sim, EmitterSim es, Particle q, int k, float[] r, float[] u, float[] f, float cx, float cy,
                            float cr, float cg, float cb, float ca)
        {
            var D = es.D;
            // (v1.6.1) moved on by how far the effect's time is past its last step (a rate under 1, or a fractional one)
            float frac = sim.Frac, age = q.Age + frac;
            float t = Math.Min(1, age / (float)Math.Max(1, q.Life));
            float alpha = D.Alpha(t) * D.A(14, D.EmAlpha, k) * ca;
            if (alpha <= 0.002f) return null;
            float sx = D.SizeX * D.SizeCurve(0, t) * q.Sr * q.SaX * sim.CSize;
            float sy = D.SizeY * D.SizeCurve(1, t) * q.Sry * q.SaY * sim.CSize;
            if (Math.Abs(sx) < 1e-5f && Math.Abs(sy) < 1e-5f) return null;
            var c0 = new float[3];
            D.Colour(0, t, c0);
            var it = new FxItem
            {
                R = c0[0] * D.A(11, D.EmColor0[0], k) * cr, G = c0[1] * D.A(12, D.EmColor0[1], k) * cg,
                B = c0[2] * D.A(13, D.EmColor0[2], k) * cb, A = alpha, Tex = D.Tex,
                Blend = D.Blend == 1 ? FxRaster.Add : D.Blend == 2 ? FxRaster.Sub : FxRaster.Alpha, Combiner = D.Combiner,
                Mask = D.Tex1, MaskU = D.U1Scale / D.UScale, MaskV = D.V1Scale / D.VScale, Wrap = D.Wrap0, MaskWrap = D.Wrap1,
            };
            if (D.Combiner == 2 || D.Combiner == 4)      // (v1.7.1: 4 too, 2 with the texture's own alpha: its colour 1 was black)
            {
                var c1 = new float[3];
                D.Colour(1, t, c1);
                // (v1.7.1) the call's colour multiplies colour 1 too: eft's dynamic block takes the emitter set's colour x the
                // colour scale x each of the emitter's two colours (cross_f 0x04A65B2C: [0-2] x +0x218, [4-6] x +0x238)
                it.Col1 = new[] { c1[0] * D.A(19, D.EmColor1[0], k) * cr, c1[1] * D.A(20, D.EmColor1[1], k) * cg, c1[2] * D.A(21, D.EmColor1[2], k) * cb };
            }
            var call = es.LastM ?? sim.Call;       // a following particle: the live call x emitter matrix
            var callLin = Fx.Lin(call);
            var qp = frac > 0 ? new[] { q.P[0] + q.V[0] * frac, q.P[1] + q.V[1] * frac, q.P[2] + q.V[2] * frac } : q.P;
            float[] p = q.Local ? call.Transform(qp[0], qp[1], qp[2]) : qp;
            float[] v = q.Local ? Fx.Apply(callLin, q.V[0], q.V[1], q.V[2]) : q.V;
            float[] frame = Fx.NormCols(q.Local ? callLin : q.Lin);
            float[] b;
            int pt = D.PType;
            // billboards (v1.6.2): X along the screen's right, Y up, Z toward the camera, as eft's programs build them
            // from the view block's billboard matrix (fx_render's s4_view_block: bm = view -> world, its X the screen's
            // right). v1.6.0 took fx_render's CPU basis, whose X pointed left: the quad seen from behind, every billboard
            // mirrored (streaks / arcs pointing back, Pac-Man's streak behind him)
            if (pt == 0 || pt == 7)
                b = Fx.Cols(r, u, new[] { -f[0], -f[1], -f[2] });
            else if (pt == 8)
            {
                var x = Fx.Norm(new[] { r[0], 0, r[2] });
                b = Fx.Cols(x, new[] { 0f, 1f, 0f }, Fx.Cross(x, new[] { 0f, 1f, 0f }));
            }
            else if (pt == 1) b = frame;
            else if (pt == 2) b = Fx.Mul(frame, XZ);
            else
            {
                float s = Fx.Len(v);
                b = frame;
                // (v1.7.1) type 4 takes any motion, however small: eft's program normalizes it whatever its size, and
                // effects set a tiny one on purpose to turn the sheet (the common arcs, PtcCommonAttackArcB: 1e-6 along
                // the emitter's Y and 1e-8 out of a circle along -Z give X = -emitter X, the arc in front of Dr. Mario;
                // v1.7.0 took them as at rest, the emitter's frame, and drew it mirrored behind him)
                if (pt == 4 && s > 1e-12f)
                {
                    var y = new[] { v[0] / s, v[1] / s, v[2] / s };
                    var x = Fx.Cross(new[] { frame[1], frame[4], frame[7] }, y);
                    if (Fx.Len(x) < 1e-6f) x = new[] { frame[0], frame[3], frame[6] };
                    x = Fx.Norm(x);
                    b = Fx.Cols(x, y, Fx.Cross(x, y));
                }
                else if (pt == 3 && s > 1e-4f)
                {
                    var y = new[] { v[0] / s, v[1] / s, v[2] / s };
                    var x = Fx.Cross(y, new[] { -f[0], -f[1], -f[2] });
                    if (Fx.Len(x) < 1e-6f) x = Fx.Cross(y, new[] { frame[2], frame[5], frame[8] });
                    x = Fx.Norm(x);
                    b = Fx.Cols(x, y, Fx.Cross(x, y));
                }
            }
            var rot = new float[3];
            for (int i = 0; i < 3; i++) rot[i] = q.Rot[i] + D.RotAdd[i] * age;
            var R = Fx.Rot(rot, "xzy");
            // an XZ plate: turned in the emitter's frame, then laid flat with its Y onto the emitter's -Z (v1.7.1: eft's
            // own programs, fitted over two camera pitches on the common bank's plates (PtcCommonBombB ring1, the Genesis
            // beam's shoot1 meshes): frame x R x XZT; v1.7.0's XZ had the plate's Y and Z reversed, the Genesis beam's
            // head meshes pointing forward from their particle instead of back along the beam)
            b = pt == 2 ? Fx.Mul(Fx.Mul(Fx.Mul(b, XZT), R), XZT) : Fx.Mul(b, R);
            float[] pos = D.Mesh != null ? D.Mesh.Pos : QuadPos;
            int nv = pos.Length / 3;
            it.S = new float[nv * 3];
            it.UV = new float[nv * 2];
            it.Idx = D.Mesh != null ? D.Mesh.Idx : QuadIdx;
            var muv = D.Mesh != null ? D.Mesh.UV : QuadUV;
            if (D.Mesh != null && D.Mesh.Col != null) it.VCol = D.Mesh.Col;
            float depth = 0;
            for (int i = 0; i < nv; i++)
            {
                float lx = (pos[i * 3] + D.RotBasis[0]) * sx, ly = (pos[i * 3 + 1] + D.RotBasis[1]) * sy, lz = pos[i * 3 + 2] * sx;
                float wx = b[0] * lx + b[1] * ly + b[2] * lz + p[0], wy = b[3] * lx + b[4] * ly + b[5] * lz + p[1],
                      wz = b[6] * lx + b[7] * ly + b[8] * lz + p[2];
                float x = wx * r[0] + wy * r[1] + wz * r[2], y = wx * u[0] + wy * u[1] + wz * u[2], z = wx * f[0] + wy * f[1] + wz * f[2];
                z -= D.CameraOffset;
                it.S[i * 3] = cx + x * zoom; it.S[i * 3 + 1] = cy - y * zoom; it.S[i * 3 + 2] = z;
                depth += z;
                it.UV[i * 2] = muv[i * 2] * D.UScale; it.UV[i * 2 + 1] = muv[i * 2 + 1] * D.VScale;
            }
            it.Depth = depth / Math.Max(1, nv);
            return it;
        }

        /// <summary>The effect's model on its animation frame: one item a polygon (its material's blend, colour gain and
        /// UV scroll), placed by the call (size included).</summary>
        void AddModel(EffectSim sim, float frame, List<FxItem> items, float[] r, float[] u, float[] f, float cx, float cy,
                      float cr, float cg, float cb, float ca)
        {
            var m = sim.Assets.Model;
            var pose = m.Pose(frame);
            var M = sim.Call.M;
            int k = 0;
            foreach (var mesh in m.Model.Meshes)
                foreach (var p in mesh.Polys)
                {
                    var v = pose[k++];
                    if (!mesh.Visible) continue;
                    float[] gain, scaleUV, transUV, rotUV, comb0, comb1;
                    m.Material(p, frame, out gain, out scaleUV, out transUV, out rotUV, out comb0, out comb1);
                    float a = (gain.Length > 3 ? gain[3] : 1) * ca;
                    if (a <= 0.002f) continue;
                    int nv = v.Length / 3;
                    // big polygons are split into their triangles' own items (sorted with the particles)
                    var S = new float[nv * 3];
                    for (int i = 0; i < nv; i++)
                    {
                        float x0 = v[i * 3], y0 = v[i * 3 + 1], z0 = v[i * 3 + 2];
                        float wx = M[0] * x0 + M[1] * y0 + M[2] * z0 + M[3], wy = M[4] * x0 + M[5] * y0 + M[6] * z0 + M[7],
                              wz = M[8] * x0 + M[9] * y0 + M[10] * z0 + M[11];
                        S[i * 3] = cx + (wx * r[0] + wy * r[1] + wz * r[2]) * zoom;
                        S[i * 3 + 1] = cy - (wx * u[0] + wy * u[1] + wz * u[2]) * zoom;
                        S[i * 3 + 2] = wx * f[0] + wy * f[1] + wz * f[2];
                    }
                    var uv = new float[nv * 2];
                    if (p.UV != null)
                        for (int i = 0; i < nv; i++)
                        {
                            float U, V;
                            EffectModel.EffectUV(p.UV[i * 2], p.UV[i * 2 + 1], scaleUV, transUV, rotUV.Length > 0 ? rotUV[0] : 0, out U, out V);
                            uv[i * 2] = U; uv[i * 2 + 1] = V;
                        }
                    float gr = gain[0] * cr, gg = (gain.Length > 1 ? gain[1] : 1) * cg, gb = (gain.Length > 2 ? gain[2] : 1) * cb;
                    var item = new FxItem
                    {
                        S = S, UV = uv, Idx = p.Tris, VCol = p.Color, Tex = p.Texture,
                        R = gr, G = gg, B = gb, A = Math.Min(4, a),
                        Blend = p.Dst == 2 ? FxRaster.Add : p.Dst == 3 ? FxRaster.Sub : FxRaster.Alpha,
                    };
                    // v1.6.3: the combiner colours (NU_effCombinerColor0 / 1): colour 1 + (colour 0 - colour 1) x the
                    // texture, as eft's interpolating combiner (inferred: the effect pixel program isn't read yet)
                    if (comb0 != null && comb0.Length >= 3)
                    {
                        var c1 = comb1 != null && comb1.Length >= 3 ? comb1 : new[] { 0f, 0f, 0f };
                        item.R = comb0[0] * gr; item.G = comb0[1] * gg; item.B = comb0[2] * gb;
                        item.Col1 = new[] { c1[0] * gr, c1[1] * gg, c1[2] * gb };
                        item.Combiner = 4;
                    }
                    float d = 0;
                    for (int i = 0; i < nv; i++) d += S[i * 3 + 2];
                    item.Depth = d / Math.Max(1, nv);
                    items.Add(item);
                }
        }

        /// <summary>A sword trail as a ribbon: the blade's two points on this frame and the frames before (BlurLength of
        /// them, 4 steps between each two at the animation frames between), shaded by its trail shader with its two
        /// textures (FxRaster.TrailTri: U = fade - t along it, t 0 at the blade, 1 at the tail end; V point 1 to point 2).
        /// Without a texture found, Level 1's band (DrawTrails).</summary>
        void AddTrail(TrailData t, List<FxItem> items, float[] r, float[] u, float[] f, float cx, float cy)
        {
            var tex1 = t.Texture1 > 0 ? GetTrailTexture(t.Texture1) : null;
            var tex2 = t.Texture2 > 0 ? GetTrailTexture(t.Texture2) : null;
            if (tex1 == null && tex2 == null) return;
            texturedTrails.Add(t.Index);
            int g = Frame.GameFrame;
            float fade = 1;
            if (t.EndFrame >= 0 && g >= t.EndFrame) fade = 1 - (g - t.EndFrame + 1) / (float)(Math.Max(0, t.Fade) + 1);
            if (fade <= 0) return;
            int n = Math.Min(Math.Max(2, t.Blur), Math.Max(0, g - t.StartFrame));
            var frames = new List<float> { AnimFrame };
            for (int k = 0; k < n && k < TrailFrames.Count; k++) frames.Add(TrailFrames[k]);
            if (frames.Count < 2) return;
            const int steps = 4;
            var pts = new List<float[]>();
            for (int k = 0; k + 1 < frames.Count; k++)
                for (int s = 0; s < steps || (k + 2 == frames.Count && s == steps); s++)
                {
                    float af = frames[k] + (frames[k + 1] - frames[k]) * s / steps;
                    float[] a, b;
                    if (TrailPoints(t, af, out a, out b)) pts.Add(new[] { a[0], a[1], a[2], b[0], b[1], b[2] });
                }
            if (pts.Count < 2) return;
            int np = pts.Count;
            var S = new float[np * 2 * 3];
            var uv = new float[np * 2 * 2];
            var tt = new float[np * 2];
            float depth = 0;
            for (int i = 0; i < np; i++)
                for (int e = 0; e < 2; e++)
                {
                    float wx = pts[i][e * 3], wy = pts[i][e * 3 + 1], wz = pts[i][e * 3 + 2];
                    int o = (i * 2 + e) * 3;
                    S[o] = cx + (wx * r[0] + wy * r[1] + wz * r[2]) * zoom;
                    S[o + 1] = cy - (wx * u[0] + wy * u[1] + wz * u[2]) * zoom;
                    S[o + 2] = wx * f[0] + wy * f[1] + wz * f[2];
                    depth += S[o + 2];
                    float ti = i / (float)(np - 1);
                    tt[i * 2 + e] = ti;
                    uv[(i * 2 + e) * 2] = Math.Max(0, fade - ti);
                    uv[(i * 2 + e) * 2 + 1] = e;
                }
            var idx = new List<int>();
            for (int i = 0; i + 1 < np; i++)
            {
                int a0 = i * 2, a1 = i * 2 + 1, b0 = i * 2 + 2, b1 = i * 2 + 3;
                idx.AddRange(new[] { a0, b0, b1, a0, b1, a1 });
            }
            items.Add(new FxItem { S = S, UV = uv, T = tt, Idx = idx.ToArray(), Tex = tex1, Tex1 = tex2, Shader = Math.Max(1, t.Shader),
                                   Fade = fade, Depth = depth / (np * 2) });
        }

        readonly HashSet<int> texturedTrails = new HashSet<int>();
    }
}
