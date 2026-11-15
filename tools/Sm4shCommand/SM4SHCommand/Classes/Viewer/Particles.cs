using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace Sm4shCommand.Viewer
{
    // v1.6.0 (Level 2): the effects drawn. The .ptcl's particles simulated on the CPU (a port of tools/fx_render.py's
    // Smash 4 side: s4_emitters, simulate, shape_point, spread, emitter_matrix, basis, Canvas.tri), the effect models
    // (efc entry -> model/<name>: nud / nut / vbn / omo / mta) and the sword trails' textures. Approximate on purpose:
    // no game shaders (each emitter's pixel program, its combiner), no bloom / glare, no distortion, no complex-emitter
    // fields / fluctuation / children, a fixed-seed System.Random (not eft's generator): README "Effects (v1.6.0)".

    /// <summary>An emitter key animation (KEYA block, docs/ptcl-format.md): a value over the emitter's frames.</summary>
    public class KeyAnim
    {
        public int Target, Interp;      // interpolation 0 linear, 1 smoothstep
        public bool Loop;
        public float[] Frames, Values;

        /// <summary>Before the first key its value, after the last (no loop) the last's; looped, the frame modulo the
        /// last key's.</summary>
        public float At(float frame)
        {
            int n = Frames.Length;
            if (n == 0) return 0;
            if (Loop && Frames[n - 1] > 0)
            {
                frame %= Frames[n - 1];
                if (frame < 0) frame += Frames[n - 1];
            }
            if (frame <= Frames[0]) return Values[0];
            if (frame >= Frames[n - 1]) return Values[n - 1];
            for (int i = 0; i + 1 < n; i++)
                if (frame < Frames[i + 1])
                {
                    float span = Frames[i + 1] - Frames[i], t = span > 0 ? (frame - Frames[i]) / span : 1;
                    if (Interp == 1) t = t * t * (3 - 2 * t);
                    return Values[i] + (Values[i + 1] - Values[i]) * t;
                }
            return Values[n - 1];
        }
    }

    /// <summary>A .ptcl primitive (an emitter's own mesh instead of the quad): positions, UVs, colours, triangles.</summary>
    public class PtclMesh
    {
        public float[] Pos;     // x y z
        public float[] UV;      // u v
        public float[] Col;     // r g b a, or null
        public int[] Idx;
    }

    /// <summary>
    /// What a .ptcl emitter does, read from its data (offsets as tools/ptcl.py's FIELDS; meanings as tools/fx_render.py's
    /// s4_emitters): emission, the volume, velocity, gravity / air, life, the scale / alpha / colour curves over the
    /// particle's life, rotation, the particle type, blend, texture slot 0 (its first flipbook cell), key animations.
    /// </summary>
    public class EmitterDef
    {
        public const int Forever = 0x7FFFFFFF;
        public string Name;
        public int Start, Interval, IntervalRandom, Duration, Life, LifeRandom, VolumeType, PType, Blend, Follow;
        public float Rate, SweepStart, SweepParam, SurfaceRandom, AllDir, DirSpeed, Dispersion, VelRandom, Air, CameraOffset;
        public bool SweepRandom, WorldGravity, Distortion, Universal;
        public int Combiner;                // 0x314: 0 colour 0 (alpha = tex red), 1 colour 0 x tex (alpha = tex alpha), 2 colour 1 + (0 - 1) x tex
                                            // (alpha = tex red); the alpha source then fixed up by the texture (Read): 3, 4, 5
        public float[] Scale, Rotation, Translation, Radius, Direction, Gravity;
        public float SizeX, SizeY, SizeRandX, SizeRandY;
        public float[] S0, S1, S2;          // the scale curve (x, y): init, after section 1, at the end
        public float SS1, SS2;              // its sections (fraction of life)
        public float A0, A1, A2, AS1, AS2;  // the alpha curve
        public int Color0Type, Color1Type;
        public float[] C0, C1;              // 8 keys x rgb (x the colour scale)
        public float[] C0Secs, C1Secs;      // 3 sections each (fraction of life)
        public float[] RotInit, RotRand, RotAdd;
        public float[] EmColor0, EmColor1, ShapeScale;   // the emitter's colour / alpha / shape-scale multipliers (0x378-0x3A7)
        public float EmAlpha;
        public float UScale = 1, VScale = 1;
        // v1.6.3: stripes (particle types 5 stripe / 6 complex stripe, eft's ribbons): the complex emitter's stripe block
        // (+0x8CE, 13 words: type 0 billboard / 1 emitter matrix / 2 emitter up-down, option, connect (2: to the emitter),
        // texture coordinates, history length, divisions, start / end alpha, UV scroll, ...)
        public int StripeType, StripeConnect, StripeHistory = 8, StripeDivide = 1;
        public float StripeStartAlpha = 1, StripeEndAlpha = 1;
        public bool IsStripe { get { return PType == 5 || PType == 6; } }
        public Texture Tex;
        // v1.6.1: texture slot 1 (29 of Mario's 497 emitters: a shape over slot 0's noise), taken as a mask on the colour
        // and alpha, its first cell (its own UV scale, 0x584)
        public Texture Tex1;
        public float U1Scale = 1, V1Scale = 1;
        public PtclMesh Mesh;
        public Dictionary<int, KeyAnim> Anims = new Dictionary<int, KeyAnim>();
        public string Note = "";

        /// <summary>A key-animated emitter value at this emitter frame (target: docs/ptcl-format.md), else the default.</summary>
        public float A(int target, float def, float frame)
        {
            KeyAnim k;
            return Anims.TryGetValue(target, out k) ? k.At(frame) : def;
        }

        static float[] F(PtclFile.Emitter e, int off, int n)
        {
            var v = new float[n];
            for (int i = 0; i < n; i++) v[i] = e.F(off + 4 * i);
            return v;
        }

        public static EmitterDef Read(PtclFile.Emitter e)
        {
            var d = new EmitterDef { Name = e.Name };
            d.Start = e.StartFrame + e.EmitStart;
            d.Interval = e.I(0x454);
            d.IntervalRandom = Math.Max(0, e.I(0x458));
            d.Duration = e.OneTime ? e.EndFrame : Forever;
            d.Rate = e.EmitRate;
            int life = e.Life;
            d.Life = life >= Forever ? 600 : Math.Max(1, life);      // (fx_render: a particle that lives forever, 600)
            d.LifeRandom = life >= Forever ? 0 : Math.Max(0, e.LifeRandom);
            d.Scale = F(e, 0x408, 3); d.Rotation = F(e, 0x414, 3); d.Translation = F(e, 0x420, 3);
            d.VolumeType = e.I(0x340);
            d.Radius = F(e, 0x348, 3);
            d.SweepStart = e.F(0x354); d.SweepParam = e.F(0x358); d.SurfaceRandom = e.F(0x35C); d.SweepRandom = e.U8(0x303) != 0;
            d.AllDir = e.F(0x45C); d.VelRandom = e.F(0x460); d.DirSpeed = e.F(0x464);
            d.Direction = F(e, 0x468, 3);
            d.Dispersion = e.F(0x474);
            d.Air = e.F(0x484);
            d.Gravity = F(e, 0x4A4, 3);
            d.WorldGravity = e.U8(0x2F8) != 0;
            d.PType = e.I(0x4BC);
            d.CameraOffset = e.F(0x4D0);
            d.UScale = e.F(0x508); d.VScale = e.F(0x50C);
            if (d.UScale == 0) d.UScale = 1;
            if (d.VScale == 0) d.VScale = 1;
            d.Follow = e.I(0x310);
            d.Blend = e.BlendType;
            var sc = F(e, 0x7D4, 2);
            d.SizeX = sc[0]; d.SizeY = sc[1];
            var sr = F(e, 0x7CC, 2);
            d.SizeRandX = sr[0]; d.SizeRandY = sr[1];
            d.S0 = F(e, 0x7DC, 2);
            var d21 = F(e, 0x7E4, 2);
            var d32 = F(e, 0x7EC, 2);
            d.S1 = new[] { d.S0[0] + d21[0], d.S0[1] + d21[1] };
            d.S2 = new[] { d.S1[0] + d32[0], d.S1[1] + d32[1] };
            d.SS1 = e.I(0x7C4) / 100f; d.SS2 = e.I(0x7C8) / 100f;
            d.A0 = e.F(0x784); d.A1 = d.A0 + e.F(0x788); d.A2 = d.A1 + e.F(0x78C);
            d.AS1 = e.F(0x790); d.AS2 = e.F(0x794);
            float cs = e.F(0x778);
            d.Color0Type = e.I(0x648); d.Color1Type = e.I(0x64C);
            d.C0 = new float[24]; d.C1 = new float[24];
            for (int k = 0; k < 8; k++)
                for (int c = 0; c < 3; c++)
                {
                    d.C0[k * 3 + c] = e.F(0x650 + 16 * k + 4 * c) * cs;
                    d.C1[k * 3 + c] = e.F(0x6D0 + 16 * k + 4 * c) * cs;
                }
            d.C0Secs = new[] { e.I(0x750) / 100f, e.I(0x758) / 100f, e.I(0x760) / 100f };
            d.C1Secs = new[] { e.I(0x754) / 100f, e.I(0x75C) / 100f, e.I(0x764) / 100f };
            // the colour combiner (docs/ptcl-format.md 0x314, read off the vanilla pixel shaders); other values: as 1
            d.Combiner = e.I(0x314);
            if (d.Combiner < 0 || d.Combiner > 2) d.Combiner = 1;
            // where the alpha comes from: the combiner word's rule (0 / 2 red, 1 alpha) is the vanilla programs' for their
            // textures, but a texture with an alpha channel of its own (comp_sel's alpha a real channel other than red's:
            // the converted effects' BC5 masks, red the colour and green the alpha) is drawn with that alpha, and a
            // one-channel texture (R R R 1, BC4's selector) with its red, whatever the combiner (1 would draw its whole
            // quad): 3 = 1 with red, 4 = 2 with alpha, 5 = 0 with alpha
            int sel = e.I(0x40 + 0x14), selA = sel & 0xFF, selR = sel >> 24 & 0xFF;
            bool ownAlpha = selA < 4 && selA != selR;
            if (ownAlpha) d.Combiner = d.Combiner == 2 ? 4 : d.Combiner == 0 ? 5 : 1;
            else if (d.Combiner == 1) d.Combiner = 3;
            d.Universal = PtclData.Universal(e);
            d.RotInit = F(e, 0x7F8, 3); d.RotRand = F(e, 0x804, 3); d.RotAdd = F(e, 0x810, 3);
            d.ShapeScale = F(e, 0x378, 3);
            d.EmColor0 = F(e, 0x384, 3);
            d.EmColor1 = F(e, 0x394, 3);
            d.EmAlpha = e.F(0x3A4);
            foreach (var k in PtclData.KeyAnims(e))
                if (k.Target < 0x1C) d.Anims[k.Target] = k;
            try { d.Tex = PtclData.DecodeTexture(e, 0); }
            catch (Exception) { d.Tex = null; d.Note += "texture not decoded; "; }
            // v1.6.3: a texture with no alpha (every texel opaque: a one-channel BC4 whose selector names an alpha it
            // hasn't, an RGB image) drawn by a combiner that reads the alpha covered its whole quad, a translucent
            // square (Pac-Man's neutral air, Dr. Mario's Cyclone ring): its red is the shape, as the combiners that read red
            if (d.Tex != null && (d.Combiner == 1 || d.Combiner == 4 || d.Combiner == 5) && PtclData.Opaque(d.Tex))
            {
                d.Combiner = d.Combiner == 1 ? 3 : d.Combiner == 4 ? 2 : 0;
                d.Note += "texture has no alpha: alpha from red; ";
            }
            try { d.Tex1 = PtclData.DecodeTexture(e, 1); } catch (Exception) { d.Tex1 = null; }
            d.U1Scale = e.F(0x584); d.V1Scale = e.F(0x588);
            if (d.U1Scale == 0) d.U1Scale = 1;
            if (d.V1Scale == 0) d.V1Scale = 1;
            int prim = e.I(0x2DC);
            if (prim >= 0)
            {
                try { d.Mesh = PtclData.Primitive(e.File, prim); } catch (Exception) { d.Mesh = null; }
            }
            d.Distortion = PtclData.Distortion(e);
            if (e.I(0) == 1)
            {
                int so = BE.U16(e.File.Data, e.Pos + 0x8CE);
                if (so > 0 && e.Pos + so + 0x34 <= e.File.Data.Length)
                {
                    d.StripeType = e.I(so); d.StripeConnect = e.I(so + 8);
                    d.StripeHistory = Math.Max(2, Math.Min(256, e.I(so + 0x10)));
                    d.StripeDivide = Math.Max(1, Math.Min(16, e.I(so + 0x14)));
                    d.StripeStartAlpha = e.F(so + 0x18); d.StripeEndAlpha = e.F(so + 0x1C);
                }
            }
            if (d.Distortion) d.Note += "distortion pass (not drawn); ";
            if (e.I(0) == 1) d.Note += "complex emitter (fields / fluctuation / children not simulated); ";
            return d;
        }

        /// <summary>eft's 3-key ramp at t (0-1): v0 -> v1 at s1, held to s2, -> v2 at 1.</summary>
        public static float Three(float v0, float v1, float v2, float s1, float s2, float t)
        {
            if (t < s1) return v0 + (v1 - v0) * (s1 > 0 ? t / s1 : 1);
            if (t <= s2) return v1;
            return v1 + (v2 - v1) * (s2 < 1 ? (t - s2) / (1 - s2) : 0);
        }

        public float Alpha(float t) { return Three(A0, A1, A2, AS1, AS2, t); }
        public float SizeCurve(int axis, float t) { return Three(S0[axis], S1[axis], S2[axis], SS1, SS2, t); }

        /// <summary>A colour track (0 / 1) at t: its first key, or (type 2, animated) the 3 keys over their sections.</summary>
        public void Colour(int track, float t, float[] o)
        {
            var k = track == 0 ? C0 : C1;
            int type = track == 0 ? Color0Type : Color1Type;
            var s = track == 0 ? C0Secs : C1Secs;
            for (int c = 0; c < 3; c++)
            {
                float k0 = k[c], k1 = k[3 + c], k2 = k[6 + c];
                if (type != 2 || t <= s[0]) o[c] = k0;
                else if (t >= s[2]) o[c] = k2;
                else o[c] = k0 + (k1 - k0) * Math.Min(1, (t - s[0]) / Math.Max(s[1] - s[0], 1e-6f))
                            + (k2 - k1) * Math.Max(0, (t - s[1]) / Math.Max(s[2] - s[1], 1e-6f));
            }
        }

        /// <summary>Emitter -> effect at this emitter frame: T R S (R = Rz Ry Rx), key animations 2-10 over it.</summary>
        public Mat4 Matrix(float frame)
        {
            var s = new float[3]; var r = new float[3]; var t = new float[3];
            for (int i = 0; i < 3; i++)
            {
                s[i] = A(2 + i, Scale[i], frame);
                r[i] = A(5 + i, Rotation[i], frame);
                t[i] = A(8 + i, Translation[i], frame);
            }
            var R = Fx.Rot(r, "zyx");
            var m = Mat4.Identity();
            for (int i = 0; i < 3; i++)
            {
                for (int j = 0; j < 3; j++) m[i, j] = R[i * 3 + j] * s[j];
                m[i, 3] = t[i];
            }
            return m;
        }
    }

    /// <summary>Reading the parts of a .ptcl the particles need (tools/ptcl.py: key_anims, decode_texture, primitive,
    /// shader_entry).</summary>
    public static class PtclData
    {
        static readonly Dictionary<int, int> EftGx2 = new Dictionary<int, int> {
            { 2, 0x1A }, { 3, 0x31 }, { 4, 0x431 }, { 5, 0x32 }, { 6, 0x432 }, { 7, 0x33 }, { 8, 0x433 }, { 9, 0x34 },
            { 10, 0x234 }, { 11, 0x35 }, { 12, 0x235 } };

        static readonly System.Runtime.CompilerServices.ConditionalWeakTable<Texture, object> opaque =
            new System.Runtime.CompilerServices.ConditionalWeakTable<Texture, object>();

        /// <summary>Every texel's alpha 255 (cached per texture).</summary>
        public static bool Opaque(Texture t)
        {
            object o;
            if (opaque.TryGetValue(t, out o)) return (bool)o;
            bool all = true;
            foreach (int c in t.Argb) if ((uint)c >> 24 != 255) { all = false; break; }
            opaque.Add(t, all);
            return all;
        }

        public static List<KeyAnim> KeyAnims(PtclFile.Emitter e)
        {
            var o = new List<KeyAnim>();
            var d = e.File.Data;
            int pos = e.I(0x2CC), size = e.I(0x2D0);
            if (size <= 0) return o;
            int b = e.File.KeyAnimPos + pos;
            if (b < 0 || b + 8 > d.Length || d[b] != 'K' || d[b + 1] != 'E' || d[b + 2] != 'Y' || d[b + 3] != 'A') return o;
            int count = BE.I32(d, b + 4), p = b + 8;
            for (int i = 0; i < count && p + 0x1C <= d.Length; i++)
            {
                int nk = BE.I32(d, p), interp = BE.I32(d, p + 4), target = BE.I32(d, p + 8), loop = BE.I32(d, p + 12), blk = BE.I32(d, p + 0x18);
                if (nk < 0 || nk > 4096 || p + 0x1C + 8 * nk > d.Length) break;
                var k = new KeyAnim { Target = target, Interp = interp, Loop = loop != 0, Frames = new float[nk], Values = new float[nk] };
                for (int j = 0; j < nk; j++)
                {
                    k.Frames[j] = BE.F32(d, p + 0x1C + 8 * j);
                    k.Values[j] = target == 0x20 ? BE.I32(d, p + 0x20 + 8 * j) : BE.F32(d, p + 0x20 + 8 * j);
                }
                o.Add(k);
                if (blk <= 0) break;
                p += blk;
            }
            return o;
        }

        /// <summary>Texture slot `slot` (TexRes at 0x40 + 0xD8 x slot): the native GX2 surface through the model textures'
        /// decoder, its channels picked by comp_sel (0-3 r g b a, 4 zero, 5 one). Null when the slot is empty.</summary>
        public static Texture DecodeTexture(PtclFile.Emitter e, int slot)
        {
            int o = 0x40 + 0xD8 * slot;
            var d = e.File.Data;
            int w = BE.U16(d, e.Pos + o), h = BE.U16(d, e.Pos + o + 2);
            int tile = e.I(o + 4), swizzle = e.I(o + 8), sel = e.I(o + 0x14);
            int fmt = e.I(o + 0x2C), nsize = e.I(o + 0x30), npos = e.I(o + 0x34);
            if (w == 0 || h == 0) return null;
            // v1.6.3: no native surface but the original image (+0x20 format, +0x24 pos, +0x28 size): format 2 is plain
            // RGBA8, row after row (Pac-Man's Final Smash eyes / scores, its light: v1.6.2 drew them as solid squares)
            int ofmt = e.I(o + 0x20), opos = e.I(o + 0x24), osize = e.I(o + 0x28);
            bool original = nsize <= 0;
            if (original && (ofmt != 2 || osize < w * h * 4)) return null;
            long key = original ? ((long)opos << 20 ^ (long)sel << 4 ^ 0x7F000) : ((long)npos << 20 ^ (long)sel << 4 ^ fmt);
            Texture t;
            if (e.File.TextureCache.TryGetValue(key, out t)) return t;
            int gx2;
            if (original) gx2 = 0x1A;
            else if (!EftGx2.TryGetValue(fmt, out gx2)) { e.File.TextureCache[key] = null; return null; }
            int start = e.File.TexPos + (original ? opos : npos);
            int len = Math.Min(original ? w * h * 4 : nsize, d.Length - start);
            if (start < 0 || len <= 0) return null;
            var data = new byte[len];
            Array.Copy(d, start, data, 0, len);
            if (original)
            {
                if (len < w * h * 4) { e.File.TextureCache[key] = null; return null; }
                t = new Texture { Width = w, Height = h, Argb = new int[w * h] };
                for (int i = 0; i < w * h; i++)
                    t.Argb[i] = data[i * 4 + 3] << 24 | data[i * 4] << 16 | data[i * 4 + 1] << 8 | data[i * 4 + 2];
            }
            else
            {
                bool bc = (gx2 & 0x3F) >= 0x31 && (gx2 & 0x3F) <= 0x35;
                int ew = bc ? (w + 3) / 4 : w;
                int pitch = (ew + 31) / 32 * 32;          // tools/ptcl.py surface(): the pitch the table's surfaces have
                t = Nut.DecodeSurface(data, w, h, gx2 & 0x3F, tile, swizzle, pitch);
            }
            if (t != null)
            {
                int f = gx2 & 0x3F;
                var src = new int[6];
                for (int i = 0; i < t.Argb.Length; i++)
                {
                    int c = t.Argb[i];
                    src[0] = c >> 16 & 255; src[1] = c >> 8 & 255; src[2] = f == 0x35 ? 0 : c & 255; src[3] = (int)((uint)c >> 24);
                    src[4] = 0; src[5] = 255;
                    int r = src[Math.Min(5, sel >> 24 & 0xFF)], g = src[Math.Min(5, sel >> 16 & 0xFF)];
                    int b = src[Math.Min(5, sel >> 8 & 0xFF)], a = src[Math.Min(5, sel & 0xFF)];
                    t.Argb[i] = a << 24 | r << 16 | g << 8 | b;
                }
                t.HasAlpha = true;
            }
            e.File.TextureCache[key] = t;
            return t;
        }

        /// <summary>Primitive i of the primitive table (pos, normal, colour, uv, index streams; tools/ptcl.py primitive).</summary>
        public static PtclMesh Primitive(PtclFile f, int i)
        {
            var d = f.Data;
            int b = f.PrimPos;
            int count = BE.I32(d, b), eo = BE.I32(d, b + 8);
            if (i < 0 || i >= count) return null;
            int baseOff = b + eo + 0x50 * count;
            Func<int, float[]> stream = k =>
            {
                int q = b + eo + 0x50 * i + 16 * k;
                int comps = BE.I32(d, q + 4), off = BE.I32(d, q + 8), size = BE.I32(d, q + 12);
                if (size <= 0 || comps <= 0) return null;
                int n = size / 4;
                var v = new float[n];
                for (int j = 0; j < n; j++) v[j] = BE.F32(d, baseOff + off + 4 * j);
                return v;
            };
            Func<int, int> comps0 = k => BE.I32(d, b + eo + 0x50 * i + 16 * k + 4);
            var m = new PtclMesh();
            m.Pos = stream(0);
            var col = stream(2);
            var uv = stream(3);
            int q4 = b + eo + 0x50 * i + 16 * 4;
            int isize = BE.I32(d, q4 + 12), ioff = BE.I32(d, q4 + 8);
            m.Idx = new int[Math.Max(0, isize / 4) / 3 * 3];
            for (int j = 0; j < m.Idx.Length; j++) m.Idx[j] = BE.I32(d, baseOff + ioff + 4 * j);
            if (m.Pos == null) return null;
            int nv = m.Pos.Length / Math.Max(1, comps0(0));
            if (comps0(0) != 3)
            {
                var p3 = new float[nv * 3];
                int c = comps0(0);
                for (int j = 0; j < nv; j++) for (int k = 0; k < Math.Min(3, c); k++) p3[j * 3 + k] = m.Pos[j * c + k];
                m.Pos = p3;
            }
            m.UV = new float[nv * 2];
            if (uv != null)
            {
                int c = Math.Max(1, comps0(3));
                for (int j = 0; j < nv && j * c + 1 < uv.Length; j++) { m.UV[j * 2] = uv[j * c]; m.UV[j * 2 + 1] = uv[j * c + 1]; }
            }
            if (col != null && comps0(2) == 4 && col.Length >= nv * 4) m.Col = col;
            foreach (int x in m.Idx) if (x < 0 || x >= nv) return null;
            return m;
        }

        /// <summary>The emitter's shader is a universal-path one (Ultimate's programs lowered: tools/fx_render.py is_universal):
        /// its binary never names emitterStaticUniformBlock, which every vanilla eft program does.</summary>
        public static bool Universal(PtclFile.Emitter e)
        {
            var d = e.File.Data;
            int sh = e.I(0x844), b = e.File.ShaderPos;
            if (sh < 0 || b <= 0 || b + 0x18 > d.Length) return false;
            int eo = b + BE.I32(d, b + 0x14) + 0x78 * sh;
            if (eo + 0x70 > d.Length) return false;
            int size = BE.I32(d, eo + 0x68), off = BE.I32(d, eo + 0x6C), start = b + BE.I32(d, b + 0x10) + off;
            if (size <= 0 || start < 0 || start + size > d.Length) return false;
            var key = Encoding.ASCII.GetBytes("emitterStaticUniformBlock");
            for (int i = start; i + key.Length <= start + size; i++)
            {
                if (d[i] != key[0]) continue;
                int k = 1;
                while (k < key.Length && d[i + k] == key[k]) k++;
                if (k == key.Length) return false;
            }
            return true;
        }

        /// <summary>Shader entry's first byte 5 / 6: a distortion pass (it bends what's behind it), left out.</summary>
        public static bool Distortion(PtclFile.Emitter e)
        {
            var d = e.File.Data;
            int sh = e.I(0x844), b = e.File.ShaderPos;
            if (b <= 0 || b + 0x18 > d.Length) return false;
            int eo = b + BE.I32(d, b + 0x14) + 0x78 * sh;
            if (sh < 0 || eo + 4 > d.Length) return false;
            int k = BE.I32(d, eo) & 0xFF;
            return k == 5 || k == 6;
        }
    }

    /// <summary>Small 3-D helpers (3x3 row-major float[9]).</summary>
    public static class Fx
    {
        /// <summary>R as the product of the axis rotations in the order named (radians): "zyx" = Rz Ry Rx (the emitter
        /// matrix), "xzy" = Rx Rz Ry (eft's particle rotation).</summary>
        public static float[] Rot(float[] r, string order)
        {
            float cx = (float)Math.Cos(r[0]), sx = (float)Math.Sin(r[0]), cy = (float)Math.Cos(r[1]), sy = (float)Math.Sin(r[1]);
            float cz = (float)Math.Cos(r[2]), sz = (float)Math.Sin(r[2]);
            Func<char, float[]> m = a => a == 'x' ? new[] { 1, 0, 0, 0, cx, -sx, 0, sx, cx }
                                       : a == 'y' ? new[] { cy, 0, sy, 0, 1, 0, -sy, 0, cy }
                                       : new[] { cz, -sz, 0, sz, cz, 0, 0, 0, 1f };
            return Mul(Mul(m(order[0]), m(order[1])), m(order[2]));
        }

        public static float[] Mul(float[] a, float[] b)
        {
            var o = new float[9];
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                    o[i * 3 + j] = a[i * 3] * b[j] + a[i * 3 + 1] * b[3 + j] + a[i * 3 + 2] * b[6 + j];
            return o;
        }

        public static float[] Apply(float[] m, float x, float y, float z)
        {
            return new[] { m[0] * x + m[1] * y + m[2] * z, m[3] * x + m[4] * y + m[5] * z, m[6] * x + m[7] * y + m[8] * z };
        }

        public static float[] Lin(Mat4 m)
        {
            return new[] { m[0, 0], m[0, 1], m[0, 2], m[1, 0], m[1, 1], m[1, 2], m[2, 0], m[2, 1], m[2, 2] };
        }

        public static float Len(float[] v) { return (float)Math.Sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); }

        public static float[] Norm(float[] v)
        {
            float l = Len(v);
            return l > 1e-9f ? new[] { v[0] / l, v[1] / l, v[2] / l } : new[] { 0f, 0f, 0f };
        }

        public static float[] Cross(float[] a, float[] b)
        {
            return new[] { a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0] };
        }

        /// <summary>Columns of m (3x3) normalised.</summary>
        public static float[] NormCols(float[] m)
        {
            var o = (float[])m.Clone();
            for (int c = 0; c < 3; c++)
            {
                float l = (float)Math.Sqrt(m[c] * m[c] + m[3 + c] * m[3 + c] + m[6 + c] * m[6 + c]);
                if (l < 1e-9f) l = 1;
                o[c] /= l; o[3 + c] /= l; o[6 + c] /= l;
            }
            return o;
        }

        /// <summary>A 3x3 from three column vectors.</summary>
        public static float[] Cols(float[] x, float[] y, float[] z)
        {
            return new[] { x[0], y[0], z[0], x[1], y[1], z[1], x[2], y[2], z[2] };
        }
    }

    /// <summary>One particle: its place and velocity (model space, or the call's space when it follows the effect),
    /// age / life, its random size factors, rotation, the key-animated scale at birth and the emitter frame it was born in.</summary>
    public class Particle
    {
        public float[] P, V, Rot, Lin;
        // v1.6.3: a stripe's history (newest first): where it was in model space each frame, and the emitter's Y axis then
        public List<float[]> Hist, HistAxis;
        public int Age, Life;
        public float Sr, Sry, SaX, SaY;
        public bool Local;      // v1.6.2: in the emitter's own space, placed by its live matrix each frame (0x310 = 0)
    }

    /// <summary>One emitter's particles over time (tools/fx_render.py simulate): emission by rate / interval, the
    /// volume, velocity, air, gravity, life.</summary>
    public class EmitterSim
    {
        public EmitterDef D;
        public Random Rng;
        public double Carry;
        public int NextEmit;
        public List<Particle> Live = new List<Particle>();
        public int Born;                       // particles emitted so far
        public float[] PrevOrg;
        /// <summary>v1.6.2: call x emitter matrix of the last frame stepped (the following particles are placed by it).</summary>
        public Mat4 LastM;

        /// <summary>v1.6.3: a stripe particle's history: its place in model space this frame (newest first, as many as the
        /// stripe's history length) and the emitter's Y axis then.</summary>
        void Remember(Particle q, Mat4 m, float[] axis)
        {
            if (q.Hist == null) { q.Hist = new List<float[]>(); q.HistAxis = new List<float[]>(); }
            var w = q.Local ? m.Transform(q.P[0], q.P[1], q.P[2]) : (float[])q.P.Clone();
            q.Hist.Insert(0, w);
            q.HistAxis.Insert(0, axis);
            while (q.Hist.Count > D.StripeHistory) { q.Hist.RemoveAt(q.Hist.Count - 1); q.HistAxis.RemoveAt(q.HistAxis.Count - 1); }
        }

        /// <summary>A particle's place in model space (a following one through the live emitter matrix).</summary>
        public float[] World(Particle q) { return q.Local && LastM != null ? LastM.Transform(q.P[0], q.P[1], q.P[2]) : q.P; }

        float U() { return (float)Rng.NextDouble(); }

        /// <summary>A point of the emitter's volume (fx_render shape_point, eft's circles): 0 point, 1 circle (random),
        /// 2 circle (even), 3 / 4 filled circle, 5 / 6 sphere, 7 / 8 filled sphere, the rest a sphere.</summary>
        float[] ShapePoint(int number, int count, float frame)
        {
            int vt = D.VolumeType;
            float rx = D.Radius[0] * D.A(22, D.ShapeScale[0], frame), ry = D.Radius[1] * D.A(23, D.ShapeScale[1], frame),
                  rz = D.Radius[2] * D.A(24, D.ShapeScale[2], frame);
            if (vt == 0) return new[] { 0f, 0f, 0f };
            if (vt == 1 || vt == 2)
            {
                float start = D.SweepStart, param = D.SweepParam;
                if (D.SweepRandom) start = (float)(2 * Math.PI * U());
                float a;
                if (vt == 1) a = start + U() * param;
                else
                {
                    bool full = Math.Abs(param - 2 * Math.PI) < 1e-4;
                    float step = count <= 1 ? 0 : param / (full ? count : count - 1);
                    a = start + number * step;
                }
                if (D.SurfaceRandom != 0) a += (float)(D.SurfaceRandom * Math.PI / 180 * (U() * 2 - 1));
                return new[] { (float)Math.Sin(a) * rx, 0f, (float)Math.Cos(a) * rz };
            }
            if (vt == 3 || vt == 4)
            {
                float a = (float)(U() * 2 * Math.PI), k = (float)Math.Sqrt(U());
                return new[] { (float)Math.Cos(a) * rx * k, 0f, (float)Math.Sin(a) * rz * k };
            }
            // a direction from three normal draws (Box-Muller)
            var g = new float[3];
            for (int i = 0; i < 3; i++)
            {
                double u1 = Math.Max(1e-12, Rng.NextDouble()), u2 = Rng.NextDouble();
                g[i] = (float)(Math.Sqrt(-2 * Math.Log(u1)) * Math.Cos(2 * Math.PI * u2));
            }
            g = Fx.Len(g) > 1e-9f ? Fx.Norm(g) : new[] { 0f, 1f, 0f };
            float s = vt == 5 || vt == 6 ? 1 : (float)Math.Pow(U(), 1 / 3.0);
            return new[] { g[0] * rx * s, g[1] * ry * s, g[2] * rz * s };
        }

        /// <summary>d turned at random within angle degrees (fx_render spread).</summary>
        float[] Spread(float[] d, float angle)
        {
            if (angle == 0) return d;
            float a = (float)(angle * Math.PI / 180 * U()), b = (float)(U() * 2 * Math.PI);
            var u = Fx.Norm(Fx.Cross(d, Math.Abs(d[1]) < 0.9f ? new[] { 0f, 1f, 0f } : new[] { 1f, 0f, 0f }));
            var w = Fx.Cross(d, u);
            float ca = (float)Math.Cos(a), sa = (float)Math.Sin(a), cb = (float)Math.Cos(b), sb = (float)Math.Sin(b);
            return new[] { d[0] * ca + (u[0] * cb + w[0] * sb) * sa, d[1] * ca + (u[1] * cb + w[1] * sb) * sa, d[2] * ca + (u[2] * cb + w[2] * sb) * sa };
        }

        /// <summary>One frame: the live particles move (by the velocity they had, then air and gravity) and age, the dead
        /// go, then this frame's births. k: frames since the effect started; call: effect -> model (its size in it);
        /// csize: the call's size (particle sizes, gravity); emitting: the effect is still on.</summary>
        public void Step(int k, Mat4 call, float csize, bool emitting, int cap)
        {
            var em = D.Matrix(k);
            var m = call * em;
            var lin = Fx.Lin(m);
            var org = new[] { m[0, 3], m[1, 3], m[2, 3] };
            var callLin = Fx.Lin(call);
            var emLin = Fx.Lin(em);
            LastM = m;
            float[] gWorld = null, gLocalCall = null;
            if (D.Gravity[0] != 0 || D.Gravity[1] != 0 || D.Gravity[2] != 0)
            {
                // gLocalCall: the gravity in the emitter's own space (its following particles)
                if (D.WorldGravity)
                {
                    gWorld = new[] { D.Gravity[0] * csize, D.Gravity[1] * csize, D.Gravity[2] * csize };
                    var inv = m.Inverse();
                    gLocalCall = new[] {
                        inv[0, 0] * gWorld[0] + inv[0, 1] * gWorld[1] + inv[0, 2] * gWorld[2],
                        inv[1, 0] * gWorld[0] + inv[1, 1] * gWorld[1] + inv[1, 2] * gWorld[2],
                        inv[2, 0] * gWorld[0] + inv[2, 1] * gWorld[1] + inv[2, 2] * gWorld[2] };
                }
                else
                {
                    // fx_render: lin @ gravity / |lin[:, 1]| x the size, in the top frame: in the emitter's own frame that
                    // is the gravity x the size / |lin[:, 1]|
                    float l = (float)Math.Max(1e-6, Math.Sqrt(lin[1] * lin[1] + lin[4] * lin[4] + lin[7] * lin[7]));
                    gLocalCall = new[] { D.Gravity[0] * csize / l, D.Gravity[1] * csize / l, D.Gravity[2] * csize / l };
                }
            }
            var drift = PrevOrg != null && D.Follow == 2 ? new[] { org[0] - PrevOrg[0], org[1] - PrevOrg[1], org[2] - PrevOrg[2] } : null;
            // move and age
            var keep = new List<Particle>(Live.Count + 4);
            foreach (var q in Live)
            {
                for (int i = 0; i < 3; i++) q.P[i] += q.V[i];
                if (drift != null) for (int i = 0; i < 3; i++) q.P[i] += drift[i];
                float[] g = null;
                if (q.Local) g = gLocalCall;
                else if (gWorld != null) g = gWorld;
                else if (gLocalCall != null)
                {
                    // the emitter's frame at the particle's birth (fx_render: lin @ gravity / |lin[:, 1]|) x the size
                    var gb = Fx.Apply(q.Lin, D.Gravity[0], D.Gravity[1], D.Gravity[2]);
                    float l = (float)Math.Max(1e-6, Math.Sqrt(q.Lin[1] * q.Lin[1] + q.Lin[4] * q.Lin[4] + q.Lin[7] * q.Lin[7]));
                    g = new[] { gb[0] / l * csize, gb[1] / l * csize, gb[2] / l * csize };
                }
                for (int i = 0; i < 3; i++) q.V[i] = q.V[i] * D.Air + (g != null ? g[i] : 0);
                q.Age++;
                if (q.Age < q.Life) keep.Add(q);
            }
            Live = keep;
            if (D.IsStripe)
            {
                var axis = Fx.Norm(new[] { lin[1], lin[4], lin[7] });
                foreach (var q in Live) Remember(q, m, axis);
            }
            PrevOrg = org;
            // births: when the gap has run out (the first on the window's first frame), rate (key-animated) a time
            int kk = k - D.Start;
            int births = 0;
            if (emitting && kk >= 0 && kk < D.Duration && kk >= NextEmit)
            {
                NextEmit = kk + D.Interval + 1 + (D.IntervalRandom > 0 ? (int)(U() * D.IntervalRandom) : 0);
                Carry += D.A(0, D.Rate, k);
                while (Carry >= 1 - 1e-6) { Carry -= 1; births++; }
            }
            for (int n = 0; n < births; n++)
            {
                var p = ShapePoint(n, births, k);
                var dir = Fx.Norm(D.Direction);
                if (Fx.Len(dir) < 1e-9f) dir = new[] { 0f, 1f, 0f };
                var d = Spread(dir, D.Dispersion);
                float pl = Fx.Len(p);
                var outward = pl > 1e-6f ? new[] { p[0] / pl, p[1] / pl, p[2] / pl } : Spread(new[] { 0f, 1f, 0f }, 180);
                float all = D.A(15, D.AllDir, k), sp = D.A(16, D.DirSpeed, k);
                var v = new[] { outward[0] * all + d[0] * sp, outward[1] * all + d[1] * sp, outward[2] * all + d[2] * sp };
                float vr = 1 - D.VelRandom * U();
                for (int i = 0; i < 3; i++) v[i] *= vr;
                float sr = 1 - D.SizeRandX * U();
                float sry = D.SizeRandY == D.SizeRandX ? sr : 1 - D.SizeRandY * U();
                var rot = new float[3];
                for (int i = 0; i < 3; i++) rot[i] = D.RotInit[i] + D.RotRand[i] * U();
                int life = Math.Max(1, (int)D.A(1, D.Life, k) - (D.LifeRandom > 0 ? (int)(U() * D.LifeRandom) : 0));
                Born++;
                if (Live.Count >= cap) continue;            // the cap (the viewer's quality setting)
                var q = new Particle { Age = 0, Life = life, Sr = sr, Sry = sry, SaX = D.A(17, 1, k), SaY = D.A(18, 1, k), Rot = rot };
                if (D.Follow == 0)
                {
                    // follows the emitter (docs/ptcl-format.md 0x310: the particle points at the emitter's live matrices):
                    // kept in the emitter's own space, placed by the call x the emitter matrix of the frame shown, its key
                    // animations included (v1.6.2: v1.6.0 froze the emitter's rotation at the particle's birth, so a
                    // swoosh whose emitter turns with the swing stayed where the swing started: Mario's up smash / forward
                    // air arcs drawn behind him)
                    q.Local = true;
                    q.P = (float[])p.Clone();
                    q.V = (float[])v.Clone();
                    q.Lin = null;
                }
                else
                {
                    q.P = new[] { lin[0] * p[0] + lin[1] * p[1] + lin[2] * p[2] + org[0], lin[3] * p[0] + lin[4] * p[1] + lin[5] * p[2] + org[1],
                                  lin[6] * p[0] + lin[7] * p[1] + lin[8] * p[2] + org[2] };
                    q.V = Fx.Apply(lin, v[0], v[1], v[2]);
                    q.Lin = lin;
                }
                Live.Add(q);
                if (D.IsStripe) Remember(q, m, Fx.Norm(new[] { lin[1], lin[4], lin[7] }));
            }
        }
    }

    /// <summary>What an effect id draws: its .ptcl set's emitters and its effect model (either may be missing).</summary>
    public class EffectAssets
    {
        public List<EmitterDef> Emitters = new List<EmitterDef>();
        public EffectModel Model;
        public string SetName;
    }

    /// <summary>
    /// One effect call played over time: its emitters' particles stepped frame by frame from its start (fixed seeds: the
    /// same picture every time), its model's animation frame. Stepped forward incrementally; a frame before the last one
    /// stepped starts it again.
    /// </summary>
    public class EffectSim
    {
        public EffectData Effect;
        public EffectAssets Assets;
        public List<EmitterSim> Emitters = new List<EmitterSim>();
        public int At = int.MinValue;          // the game frame stepped to
        public int Cap;
        public Mat4 Call;                      // effect -> model on the frame stepped to (size included)
        public float CSize = 1;
        // v1.6.1: the effect's own time (its frames, at its rate: LAST_EFFECT_SET_RATE; eft's set step x the rate) on game
        // frame At: 0 on its first frame, + Rate each game frame after; NextK the next emitter frame to step
        public double Time;
        public int NextK;
        /// <summary>How far the effect's time is past its last whole step (0-1): particles are drawn moved on by it.</summary>
        public float Frac { get { return NextK <= 0 ? 0 : (float)Math.Max(0, Math.Min(1, Time - (NextK - 1))); } }
        public static float RateOf(EffectData e) { return Math.Max(0, e.Rate); }

        public EffectSim(EffectData e, EffectAssets a, int cap)
        {
            Effect = e; Assets = a; Cap = cap;
            Reset();
        }

        public void Reset()
        {
            Emitters.Clear();
            if (Assets != null)
                for (int i = 0; i < Assets.Emitters.Count; i++)
                    Emitters.Add(new EmitterSim { D = Assets.Emitters[i], Rng = new Random(1 + 7919 * i + 104729 * (Effect.Index + 1)) });
            At = Effect.StartFrame - 1;
            Time = 0;
            NextK = 0;
            Call = null;
        }

        /// <summary>The call's size (the effect's Size x LAST_EFFECT_SET_SCALE_W's mean).</summary>
        public static float SizeOf(EffectData e)
        {
            return e.Size * (e.HasScale ? (e.SX + e.SY + e.SZ) / 3 : 1);
        }

        /// <summary>Steps to game frame g (from the start again when g is before the last frame stepped). callAt(frame):
        /// the effect's matrix (effect -> model, no size) on that game frame, null when it can't be placed.</summary>
        public void StepTo(int g, Func<int, Mat4> callAt)
        {
            if (g < At) Reset();
            float size = SizeOf(Effect);
            var sc = Mat4.Identity();
            sc[0, 0] = Effect.Size * (Effect.HasScale ? Effect.SX : 1);
            sc[1, 1] = Effect.Size * (Effect.HasScale ? Effect.SY : 1);
            sc[2, 2] = Effect.Size * (Effect.HasScale ? Effect.SZ : 1);
            CSize = size;
            float rate = RateOf(Effect);
            while (At < g)
            {
                At++;
                if (At > Effect.StartFrame) Time += rate;
                var m = callAt(At);
                if (m == null) continue;
                Call = m * sc;
                // the emitter frames this game frame reaches (rate 2: two a frame; 0.5: one every other frame)
                while (NextK <= Math.Floor(Time + 1e-6))
                {
                    foreach (var es in Emitters)
                        es.Step(NextK, Call, size, true, Cap);
                    NextK++;
                }
            }
            if (Call == null)
            {
                var m = callAt(g);
                if (m != null) Call = m * sc;
            }
        }

        public int ParticleCount { get { return Emitters.Sum(x => x.Live.Count); } }

        /// <summary>The model's animation frame on game frame g: the effect's time since it started (game frames x its
        /// rate), looped while it follows (an aura), held on the last for a one-shot.</summary>
        public float ModelFrame(int g)
        {
            if (Assets == null || Assets.Model == null) return 0;
            int n = Assets.Model.Frames;
            float k = Math.Max(0, g - Effect.StartFrame) * RateOf(Effect);
            if (n <= 1) return 0;
            if (Effect.Follow && Effect.DetachFrame < 0) return k % n;
            return Math.Min(k, n - 1);
        }
    }

    /// <summary>A model.mta (MTA4; tools/mta.py): per material (by NU_materialHash's bits) its animated values a frame.</summary>
    public class Mta
    {
        public int Frames;
        public readonly Dictionary<uint, Dictionary<string, float[][]>> Mats = new Dictionary<uint, Dictionary<string, float[][]>>();

        public Mta(byte[] d)
        {
            if (d.Length < 0x28 || Encoding.ASCII.GetString(d, 0, 4) != "MTA4") throw new InvalidDataException("not an MTA4 file");
            Frames = BE.I32(d, 8);
            int mc = BE.I32(d, 0x18), mo = BE.I32(d, 0x1C);
            for (int i = 0; i < mc && mo + 4 * i + 4 <= d.Length; i++)
            {
                int e = BE.I32(d, mo + 4 * i);
                uint hash = BE.U32(d, e + 4);
                int pc = BE.I32(d, e + 8), pp = BE.I32(d, e + 12);
                var props = new Dictionary<string, float[][]>();
                for (int k = 0; k < pc; k++)
                {
                    int q = BE.I32(d, pp + 4 * k);
                    string name = BE.CStr(d, BE.I32(d, q));
                    int count = BE.I32(d, q + 8), fc = BE.I32(d, q + 12), dof = BE.I32(d, q + 20);
                    if (count <= 0 || count > 16 || fc <= 0 || dof + 4 * count * fc > d.Length) continue;
                    var v = new float[fc][];
                    for (int j = 0; j < fc; j++)
                    {
                        v[j] = new float[count];
                        for (int c = 0; c < count; c++) v[j][c] = BE.F32(d, dof + 4 * (j * count + c));
                    }
                    props[name] = v;
                }
                Mats[hash] = props;
            }
        }

        /// <summary>The material's value on this frame (held past the last), or null when it doesn't animate it.</summary>
        public float[] Value(uint hash, string prop, float frame)
        {
            Dictionary<string, float[][]> m;
            float[][] v;
            if (!Mats.TryGetValue(hash, out m) || !m.TryGetValue(prop, out v) || v.Length == 0) return null;
            int a = Math.Max(0, Math.Min(v.Length - 1, (int)Math.Floor(frame))), b = Math.Min(v.Length - 1, a + 1);
            float t = Math.Max(0, Math.Min(1, frame - a));
            var o = new float[v[a].Length];
            for (int i = 0; i < o.Length; i++) o[i] = v[a][i] + (v[b][i] - v[a][i]) * t;
            return o;
        }
    }

    /// <summary>An effect model (efc entry -> model/&lt;name&gt;/): model.nud / .nut / .vbn, its bone animation model.omo
    /// played from the spawn and its material animation model.mta (NU_effColorGain, NU_effTransUV / ScaleUV).</summary>
    public class EffectModel
    {
        public string Name, Folder;
        public NudModel Model;
        public Skeleton Skeleton;
        public Omo Anim;
        public Mta Mta;
        public Dictionary<int, Texture> Textures = new Dictionary<int, Texture>();

        public int Frames { get { return Math.Max(Anim != null ? Anim.Frames : 0, Mta != null ? Mta.Frames : 0); } }

        public static EffectModel Load(string dir)
        {
            string nud = Path.Combine(dir, "model.nud");
            if (!File.Exists(nud)) return null;
            var m = new EffectModel { Folder = dir, Name = Path.GetFileName(dir) };
            m.Model = NudModel.Load(nud);
            string vbn = Path.Combine(dir, "model.vbn");
            if (File.Exists(vbn)) m.Skeleton = Skeleton.Load(vbn);
            try { m.Textures = Nut.Load(Path.Combine(dir, "model.nut")); } catch (Exception) { }
            string omo = Path.Combine(dir, "model.omo");
            try { if (File.Exists(omo)) m.Anim = new Omo(File.ReadAllBytes(omo)); } catch (Exception) { m.Anim = null; }
            string mta = Path.Combine(dir, "model.mta");
            try { if (File.Exists(mta)) m.Mta = new Mta(File.ReadAllBytes(mta)); } catch (Exception) { m.Mta = null; }
            foreach (var mesh in m.Model.Meshes)
                foreach (var p in mesh.Polys)
                {
                    Texture t;
                    if (p.UV != null && m.Textures.TryGetValue(p.TextureHash, out t)) p.Texture = t;
                }
            return m;
        }

        /// <summary>The vertices on this animation frame in the model's own space (skinned as the fighters are:
        /// Viewport.Skin), one array per polygon (x y z).</summary>
        public List<float[]> Pose(float frame)
        {
            var o = new List<float[]>();
            Mat4[] skin = null;
            if (Skeleton != null)
            {
                var w = Skeleton.World(Anim, frame);
                skin = new Mat4[w.Length];
                for (int i = 0; i < w.Length; i++) skin[i] = w[i] * Skeleton.InverseBind[i];
            }
            foreach (var mesh in Model.Meshes)
                foreach (var p in mesh.Polys)
                {
                    int vc = p.Pos.Length / 3;
                    var v = new float[vc * 3];
                    for (int k = 0; k < vc; k++)
                    {
                        float x = p.Pos[k * 3], y = p.Pos[k * 3 + 1], z = p.Pos[k * 3 + 2], ox = 0, oy = 0, oz = 0, ws = 0;
                        if (skin != null)
                            for (int j = 0; j < 4; j++)
                            {
                                float wt = p.Weights[k * 4 + j];
                                int bi = p.Bones[k * 4 + j];
                                if (wt <= 0 || bi < 0 || bi >= skin.Length) continue;
                                var M = skin[bi].M;
                                ox += wt * (M[0] * x + M[1] * y + M[2] * z + M[3]);
                                oy += wt * (M[4] * x + M[5] * y + M[6] * z + M[7]);
                                oz += wt * (M[8] * x + M[9] * y + M[10] * z + M[11]);
                                ws += wt;
                            }
                        if (ws <= 0) { ox = x; oy = y; oz = z; }
                        else if (Math.Abs(ws - 1) > 1e-3) { ox /= ws; oy /= ws; oz /= ws; }
                        v[k * 3] = ox; v[k * 3 + 1] = oy; v[k * 3 + 2] = oz;
                    }
                    o.Add(v);
                }
            return o;
        }

        /// <summary>A polygon's material on this frame: colour gain (r g b a; the MTA's, else the material's own), UV
        /// scale (u v) and offset (u v).</summary>
        public void Material(NudModel.Poly p, float frame, out float[] gain, out float[] scaleUV, out float[] transUV)
        {
            float[] h;
            uint hash = p.Props.TryGetValue("NU_materialHash", out h) && h.Length > 0 ? BitConverter.ToUInt32(BitConverter.GetBytes(h[0]), 0) : 0;
            Func<string, float[], float[]> val = (name, def) =>
            {
                float[] v = Mta != null ? Mta.Value(hash, name, frame) : null;
                if (v == null && !p.Props.TryGetValue(name, out v)) v = def;
                return v;
            };
            gain = val("NU_effColorGain", new[] { 1f, 1f, 1f, 1f });
            scaleUV = val("NU_effScaleUV", new[] { 1f, 1f, 0, 0 });
            transUV = val("NU_effTransUV", new[] { 0f, 0, 0, 0 });
        }
    }

    /// <summary>
    /// Drawing into the viewport's pixels: one triangle with a texture (nearest, or bilinear on "HQ"), a colour, per-vertex
    /// colours, blended into what's there (alpha, add, subtract), tested against the depth buffer but not written to it
    /// (effects are drawn after the opaque models, far to near).
    /// </summary>
    public static class FxRaster
    {
        public const int Alpha = 0, Add = 1, Sub = 2;

        static void Sample(Texture t, float u, float v, bool bilinear, out float r, out float g, out float b, out float a)
        {
            int w = t.Width, h = t.Height;
            var px = t.Argb;
            if (!bilinear)
            {
                int xi = (int)Math.Floor(u * w) % w, yi = (int)Math.Floor(v * h) % h;
                if (xi < 0) xi += w;
                if (yi < 0) yi += h;
                int c = px[yi * w + xi];
                r = (c >> 16 & 255) * (1 / 255f); g = (c >> 8 & 255) * (1 / 255f); b = (c & 255) * (1 / 255f); a = (c >> 24 & 255) * (1 / 255f);
                return;
            }
            float x = u * w - 0.5f, y = v * h - 0.5f;
            float fxf = (float)Math.Floor(x), fyf = (float)Math.Floor(y);
            float fx = x - fxf, fy = y - fyf;
            int x0 = (int)fxf % w, y0 = (int)fyf % h;
            if (x0 < 0) x0 += w;
            if (y0 < 0) y0 += h;
            int x1 = x0 + 1 == w ? 0 : x0 + 1, y1 = y0 + 1 == h ? 0 : y0 + 1;
            int c00 = px[y0 * w + x0], c10 = px[y0 * w + x1], c01 = px[y1 * w + x0], c11 = px[y1 * w + x1];
            float w00 = (1 - fx) * (1 - fy), w10 = fx * (1 - fy), w01 = (1 - fx) * fy, w11 = fx * fy;
            const float k = 1 / 255f;
            r = ((c00 >> 16 & 255) * w00 + (c10 >> 16 & 255) * w10 + (c01 >> 16 & 255) * w01 + (c11 >> 16 & 255) * w11) * k;
            g = ((c00 >> 8 & 255) * w00 + (c10 >> 8 & 255) * w10 + (c01 >> 8 & 255) * w01 + (c11 >> 8 & 255) * w11) * k;
            b = ((c00 & 255) * w00 + (c10 & 255) * w10 + (c01 & 255) * w01 + (c11 & 255) * w11) * k;
            a = ((c00 >> 24 & 255) * w00 + (c10 >> 24 & 255) * w10 + (c01 >> 24 & 255) * w01 + (c11 >> 24 & 255) * w11) * k;
        }

        /// <summary>
        /// One triangle (screen x y, depth z per corner). uv: 6 floats (null: untextured); col: the colour (r g b, may be
        /// over 1) and alpha; col1: the second colour (combiner 2); vcol: 12 floats, r g b a per corner (null: none);
        /// combiner: as an emitter's 0x314 (0 colour, alpha = tex red; 1 colour x tex, alpha = tex alpha; 2 colour 1 +
        /// (colour - colour 1) x tex, alpha = tex red; 3 colour x tex, alpha = tex red; 4 / 5 as 2 / 0 with the texture's
        /// alpha).
        /// Returns the pixels drawn.
        /// </summary>
        public static int Tri(int[] pix, float[] zb, int w, int h, float ax, float ay, float az, float bx, float by, float bz,
                              float cx, float cy, float cz, float[] uv, Texture tex, bool bilinear, float cr, float cg, float cb,
                              float ca, float[] col1, float[] vcol, int blend, int combiner = 1, Texture mask = null, float mu = 1, float mv = 1)
        {
            int minX = Math.Max(0, (int)Math.Floor(Math.Min(ax, Math.Min(bx, cx))));
            int maxX = Math.Min(w - 1, (int)Math.Ceiling(Math.Max(ax, Math.Max(bx, cx))));
            int minY = Math.Max(0, (int)Math.Floor(Math.Min(ay, Math.Min(by, cy))));
            int maxY = Math.Min(h - 1, (int)Math.Ceiling(Math.Max(ay, Math.Max(by, cy))));
            if (minX > maxX || minY > maxY) return 0;
            float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
            if (Math.Abs(area) < 1e-6f) return 0;
            float inv = 1 / area;
            int drawn = 0;
            for (int y = minY; y <= maxY; y++)
            {
                float py = y + 0.5f;
                int xs, xe;
                if (!Span(ax, ay, bx, by, cx, cy, inv, py, minX, maxX, out xs, out xe)) continue;
                for (int x = xs; x <= xe; x++)
                {
                    float px = x + 0.5f;
                    float w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) * inv;
                    float w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) * inv;
                    float w2 = 1 - w0 - w1;
                    if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                    int i = y * w + x;
                    float z = w0 * az + w1 * bz + w2 * cz;
                    if (z >= zb[i]) continue;
                    float tr = 1, tg = 1, tb = 1, ta = 1;
                    if (tex != null && uv != null)
                        Sample(tex, w0 * uv[0] + w1 * uv[2] + w2 * uv[4], w0 * uv[1] + w1 * uv[3] + w2 * uv[5], bilinear, out tr, out tg, out tb, out ta);
                    float r, g, b, a;
                    if (combiner == 0 || combiner == 5) { r = cr; g = cg; b = cb; a = ca * (combiner == 5 ? ta : tr); }
                    else if (combiner == 2 || combiner == 4)
                    {
                        float c1r = col1 != null ? col1[0] : 0, c1g = col1 != null ? col1[1] : 0, c1b = col1 != null ? col1[2] : 0;
                        r = c1r + (cr - c1r) * tr; g = c1g + (cg - c1g) * tg; b = c1b + (cb - c1b) * tb; a = ca * (combiner == 4 ? ta : tr);
                    }
                    else { r = cr * tr; g = cg * tg; b = cb * tb; a = ca * (combiner == 3 ? tr : ta); }
                    if (mask != null)
                    {
                        float mr, mg, mb, ma;
                        Sample(mask, (w0 * uv[0] + w1 * uv[2] + w2 * uv[4]) * mu, (w0 * uv[1] + w1 * uv[3] + w2 * uv[5]) * mv, bilinear, out mr, out mg, out mb, out ma);
                        r *= mr; g *= mg; b *= mb; a *= ma;
                    }
                    if (vcol != null)
                    {
                        r *= w0 * vcol[0] + w1 * vcol[4] + w2 * vcol[8];
                        g *= w0 * vcol[1] + w1 * vcol[5] + w2 * vcol[9];
                        b *= w0 * vcol[2] + w1 * vcol[6] + w2 * vcol[10];
                        a *= w0 * vcol[3] + w1 * vcol[7] + w2 * vcol[11];
                    }
                    if (a <= 0.002f) continue;
                    if (a > 1) a = 1;
                    if (r < 0) r = 0; if (g < 0) g = 0; if (b < 0) b = 0;
                    int c = pix[i];
                    float dr = c >> 16 & 255, dg = c >> 8 & 255, db = c & 255;
                    if (blend == Add) { dr += r * a * 255; dg += g * a * 255; db += b * a * 255; }
                    else if (blend == Sub) { dr -= r * a * 255; dg -= g * a * 255; db -= b * a * 255; }
                    else
                    {
                        dr = dr * (1 - a) + Math.Min(1, r) * 255 * a;
                        dg = dg * (1 - a) + Math.Min(1, g) * 255 * a;
                        db = db * (1 - a) + Math.Min(1, b) * 255 * a;
                    }
                    pix[i] = unchecked((int)0xFF000000) | Clamp(dr) << 16 | Clamp(dg) << 8 | Clamp(db);
                    drawn++;
                }
            }
            return drawn;
        }

        static int Clamp(float v) { return v <= 0 ? 0 : v >= 255 ? 255 : (int)(v + 0.5f); }

        /// <summary>The pixels of row py (centres) inside the triangle: where its three barycentric weights, linear along
        /// the row, are all >= 0 (a pixel's width of slack: the per-pixel test still decides).</summary>
        static bool Span(float ax, float ay, float bx, float by, float cx, float cy, float inv, float py, int minX, int maxX, out int xs, out int xe)
        {
            xs = minX; xe = maxX;
            float p0 = minX + 0.5f;
            float w0 = ((bx - p0) * (cy - py) - (by - py) * (cx - p0)) * inv, d0 = (by - cy) * inv;
            float w1 = ((cx - p0) * (ay - py) - (cy - py) * (ax - p0)) * inv, d1 = (cy - ay) * inv;
            float w2 = 1 - w0 - w1, d2 = -d0 - d1;
            float lo = 0, hi = maxX - minX;
            Clip(w0, d0, ref lo, ref hi);
            Clip(w1, d1, ref lo, ref hi);
            Clip(w2, d2, ref lo, ref hi);
            if (lo > hi + 1) return false;
            xs = Math.Max(minX, minX + (int)Math.Floor(lo) - 1);
            xe = Math.Min(maxX, minX + (int)Math.Ceiling(hi) + 1);
            return xs <= xe;
        }

        static void Clip(float w, float d, ref float lo, ref float hi)
        {
            if (d > 1e-12f) lo = Math.Max(lo, -w / d);
            else if (d < -1e-12f) hi = Math.Min(hi, -w / d);
            else if (w < 0) { lo = 1; hi = -1; }
        }

        /// <summary>
        /// One triangle of a sword trail, shaded as the game's trail shaders (docs/native-notes.md "The trail shaders"):
        /// per corner U V (uv, 6) and t (0 at the blade, 1 at the tail end); fade 1 -> 0 over Terminate_Sword_Glow's
        /// frames. Shader 1: rgb = (t0.rgb t0.a + t1.rgb t1.a) va, a = t0.a va; 2: rgb = (t0.rgb t0.a (1 - t1.a) + t1.rgb
        /// t1.a) va, a = t1.a va (va = (1 - t) fade); 3 (tools/shaders/trail_retract.psh): the mask t1 at U = 1 - t / fade,
        /// t0 at U + (1 - fade) / 2, a = t0.a mask.a, rgb = t0.rgb x 2 t1.g x a. Premultiplied (ONE / INV_SRC_ALPHA).
        /// </summary>
        public static void TrailTri(int[] pix, float[] zb, int w, int h, float ax, float ay, float az, float bx, float by, float bz,
                                    float cx, float cy, float cz, float[] uv, float[] tt, Texture t0, Texture t1, int shader, float fade, bool bilinear)
        {
            int minX = Math.Max(0, (int)Math.Floor(Math.Min(ax, Math.Min(bx, cx))));
            int maxX = Math.Min(w - 1, (int)Math.Ceiling(Math.Max(ax, Math.Max(bx, cx))));
            int minY = Math.Max(0, (int)Math.Floor(Math.Min(ay, Math.Min(by, cy))));
            int maxY = Math.Min(h - 1, (int)Math.Ceiling(Math.Max(ay, Math.Max(by, cy))));
            if (minX > maxX || minY > maxY) return;
            float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
            if (Math.Abs(area) < 1e-6f) return;
            float inv = 1 / area;
            for (int y = minY; y <= maxY; y++)
            {
                float py = y + 0.5f;
                int xs, xe;
                if (!Span(ax, ay, bx, by, cx, cy, inv, py, minX, maxX, out xs, out xe)) continue;
                for (int x = xs; x <= xe; x++)
                {
                    float px = x + 0.5f;
                    float w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) * inv;
                    float w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) * inv;
                    float w2 = 1 - w0 - w1;
                    if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                    int i = y * w + x;
                    float z = w0 * az + w1 * bz + w2 * cz;
                    if (z >= zb[i]) continue;
                    float U = w0 * uv[0] + w1 * uv[2] + w2 * uv[4], V = w0 * uv[1] + w1 * uv[3] + w2 * uv[5];
                    float T = w0 * tt[0] + w1 * tt[1] + w2 * tt[2];
                    float r0 = 0, g0 = 0, b0 = 0, a0 = 0, r1 = 0, g1 = 0, b1 = 0, a1 = 0, r, g, b, a;
                    if (shader == 3)
                    {
                        float um = fade > 0 ? 1 - T / fade : 1;
                        if (um < 0) continue;
                        if (t1 != null) Sample(t1, Math.Min(um, 0.999f), V, bilinear, out r1, out g1, out b1, out a1); else { g1 = 0.5f; a1 = 1; }
                        if (t0 != null) Sample(t0, U + (1 - fade) / 2, V, bilinear, out r0, out g0, out b0, out a0);
                        a = a0 * a1;
                        float k = 2 * g1 * a;
                        r = r0 * k; g = g0 * k; b = b0 * k;
                    }
                    else
                    {
                        if (t0 != null) Sample(t0, U, V, bilinear, out r0, out g0, out b0, out a0);
                        if (t1 != null) Sample(t1, U, V, bilinear, out r1, out g1, out b1, out a1);
                        float va = Math.Max(0, (1 - T) * fade);
                        if (shader == 2)
                        {
                            r = (r0 * a0 * (1 - a1) + r1 * a1) * va; g = (g0 * a0 * (1 - a1) + g1 * a1) * va; b = (b0 * a0 * (1 - a1) + b1 * a1) * va;
                            a = a1 * va;
                        }
                        else
                        {
                            r = (r0 * a0 + r1 * a1) * va; g = (g0 * a0 + g1 * a1) * va; b = (b0 * a0 + b1 * a1) * va;
                            a = (t0 != null ? a0 : a1) * va;
                        }
                    }
                    if (a <= 0.002f && r + g + b <= 0.004f) continue;
                    a = Math.Min(1, a);
                    int c = pix[i];
                    float dr = (c >> 16 & 255) * (1 - a) + r * 255, dg = (c >> 8 & 255) * (1 - a) + g * 255, db = (c & 255) * (1 - a) + b * 255;
                    pix[i] = unchecked((int)0xFF000000) | Clamp(dr) << 16 | Clamp(dg) << 8 | Clamp(db);
                }
            }
        }
    }
}
