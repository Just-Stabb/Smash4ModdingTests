using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace Sm4shCommand.Viewer
{
    /// <summary>
    /// 4x4 matrix, row-major, column vectors (p' = M p); translation in column 3.
    /// </summary>
    public class Mat4
    {
        public readonly float[] M = new float[16];

        public float this[int r, int c] { get { return M[r * 4 + c]; } set { M[r * 4 + c] = value; } }

        public static Mat4 Identity()
        {
            var m = new Mat4();
            m.M[0] = m.M[5] = m.M[10] = m.M[15] = 1;
            return m;
        }

        public static Mat4 operator *(Mat4 a, Mat4 b)
        {
            var o = new Mat4();
            for (int r = 0; r < 4; r++)
                for (int c = 0; c < 4; c++)
                {
                    float s = 0;
                    for (int k = 0; k < 4; k++)
                        s += a.M[r * 4 + k] * b.M[k * 4 + c];
                    o.M[r * 4 + c] = s;
                }
            return o;
        }

        /// <summary>Translation, rotation (quaternion x y z w) and scale.</summary>
        public static Mat4 TRS(float[] p, float[] q, float[] s)
        {
            float x = q[0], y = q[1], z = q[2], w = q[3];
            var m = Identity();
            float[] r = {
                1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y) };
            for (int i = 0; i < 3; i++)
            {
                for (int j = 0; j < 3; j++)
                    m[i, j] = r[i * 3 + j] * s[j];
                m[i, 3] = p[i];
            }
            return m;
        }

        /// <summary>VBN bind rotation: Euler angles applied X, then Y, then Z (R = Rz Ry Rx).</summary>
        public static float[] EulerToQuat(float rx, float ry, float rz)
        {
            double cx = Math.Cos(rx / 2), sx = Math.Sin(rx / 2), cy = Math.Cos(ry / 2), sy = Math.Sin(ry / 2);
            double cz = Math.Cos(rz / 2), sz = Math.Sin(rz / 2);
            return new[] {
                (float)(sx * cy * cz - cx * sy * sz), (float)(cx * sy * cz + sx * cy * sz),
                (float)(cx * cy * sz - sx * sy * cz), (float)(cx * cy * cz + sx * sy * sz) };
        }

        public float[] Transform(float x, float y, float z)
        {
            return new[] { M[0] * x + M[1] * y + M[2] * z + M[3], M[4] * x + M[5] * y + M[6] * z + M[7],
                           M[8] * x + M[9] * y + M[10] * z + M[11] };
        }

        /// <summary>The same rotation and translation with each axis normalised (Forge's ClearScale:
        /// hitbox offsets aren't scaled by the bone).</summary>
        public Mat4 ClearScale()
        {
            var o = new Mat4();
            Array.Copy(M, o.M, 16);
            for (int c = 0; c < 3; c++)
            {
                float l = (float)Math.Sqrt(M[c] * M[c] + M[4 + c] * M[4 + c] + M[8 + c] * M[8 + c]);
                if (l > 1e-8f)
                    for (int r = 0; r < 3; r++)
                        o.M[r * 4 + c] = M[r * 4 + c] / l;
            }
            return o;
        }

        public Mat4 Inverse()
        {
            var a = new double[16];
            for (int i = 0; i < 16; i++) a[i] = M[i];
            var inv = new double[16];
            inv[0] = a[5] * a[10] * a[15] - a[5] * a[11] * a[14] - a[9] * a[6] * a[15] + a[9] * a[7] * a[14] + a[13] * a[6] * a[11] - a[13] * a[7] * a[10];
            inv[4] = -a[4] * a[10] * a[15] + a[4] * a[11] * a[14] + a[8] * a[6] * a[15] - a[8] * a[7] * a[14] - a[12] * a[6] * a[11] + a[12] * a[7] * a[10];
            inv[8] = a[4] * a[9] * a[15] - a[4] * a[11] * a[13] - a[8] * a[5] * a[15] + a[8] * a[7] * a[13] + a[12] * a[5] * a[11] - a[12] * a[7] * a[9];
            inv[12] = -a[4] * a[9] * a[14] + a[4] * a[10] * a[13] + a[8] * a[5] * a[14] - a[8] * a[6] * a[13] - a[12] * a[5] * a[10] + a[12] * a[6] * a[9];
            inv[1] = -a[1] * a[10] * a[15] + a[1] * a[11] * a[14] + a[9] * a[2] * a[15] - a[9] * a[3] * a[14] - a[13] * a[2] * a[11] + a[13] * a[3] * a[10];
            inv[5] = a[0] * a[10] * a[15] - a[0] * a[11] * a[14] - a[8] * a[2] * a[15] + a[8] * a[3] * a[14] + a[12] * a[2] * a[11] - a[12] * a[3] * a[10];
            inv[9] = -a[0] * a[9] * a[15] + a[0] * a[11] * a[13] + a[8] * a[1] * a[15] - a[8] * a[3] * a[13] - a[12] * a[1] * a[11] + a[12] * a[3] * a[9];
            inv[13] = a[0] * a[9] * a[14] - a[0] * a[10] * a[13] - a[8] * a[1] * a[14] + a[8] * a[2] * a[13] + a[12] * a[1] * a[10] - a[12] * a[2] * a[9];
            inv[2] = a[1] * a[6] * a[15] - a[1] * a[7] * a[14] - a[5] * a[2] * a[15] + a[5] * a[3] * a[14] + a[13] * a[2] * a[7] - a[13] * a[3] * a[6];
            inv[6] = -a[0] * a[6] * a[15] + a[0] * a[7] * a[14] + a[4] * a[2] * a[15] - a[4] * a[3] * a[14] - a[12] * a[2] * a[7] + a[12] * a[3] * a[6];
            inv[10] = a[0] * a[5] * a[15] - a[0] * a[7] * a[13] - a[4] * a[1] * a[15] + a[4] * a[3] * a[13] + a[12] * a[1] * a[7] - a[12] * a[3] * a[5];
            inv[14] = -a[0] * a[5] * a[14] + a[0] * a[6] * a[13] + a[4] * a[1] * a[14] - a[4] * a[2] * a[13] - a[12] * a[1] * a[6] + a[12] * a[2] * a[5];
            inv[3] = -a[1] * a[6] * a[11] + a[1] * a[7] * a[10] + a[5] * a[2] * a[11] - a[5] * a[3] * a[10] - a[9] * a[2] * a[7] + a[9] * a[3] * a[6];
            inv[7] = a[0] * a[6] * a[11] - a[0] * a[7] * a[10] - a[4] * a[2] * a[11] + a[4] * a[3] * a[10] + a[8] * a[2] * a[7] - a[8] * a[3] * a[6];
            inv[11] = -a[0] * a[5] * a[11] + a[0] * a[7] * a[9] + a[4] * a[1] * a[11] - a[4] * a[3] * a[9] - a[8] * a[1] * a[7] + a[8] * a[3] * a[5];
            inv[15] = a[0] * a[5] * a[10] - a[0] * a[6] * a[9] - a[4] * a[1] * a[10] + a[4] * a[2] * a[9] + a[8] * a[1] * a[6] - a[8] * a[2] * a[5];
            double det = a[0] * inv[0] + a[1] * inv[4] + a[2] * inv[8] + a[3] * inv[12];
            var o = new Mat4();
            if (Math.Abs(det) < 1e-12)
                return Identity();
            for (int i = 0; i < 16; i++) o.M[i] = (float)(inv[i] / det);
            return o;
        }
    }

    /// <summary>Big-endian reader over a byte array.</summary>
    class BE
    {
        public static uint U32(byte[] d, int o) { return (uint)(d[o] << 24 | d[o + 1] << 16 | d[o + 2] << 8 | d[o + 3]); }
        public static int I32(byte[] d, int o) { return (int)U32(d, o); }
        public static ushort U16(byte[] d, int o) { return (ushort)(d[o] << 8 | d[o + 1]); }
        public static short I16(byte[] d, int o) { return (short)U16(d, o); }
        public static float F32(byte[] d, int o) { return BitConverter.ToSingle(BitConverter.GetBytes(U32(d, o)), 0); }
        public static float Half(byte[] d, int o)
        {
            int h = U16(d, o);
            int s = (h >> 15) & 1, e = (h >> 10) & 0x1F, m = h & 0x3FF;
            double v = e == 0 ? m * Math.Pow(2, -24) : e == 31 ? (m == 0 ? double.PositiveInfinity : double.NaN)
                     : (1 + m / 1024.0) * Math.Pow(2, e - 15);
            return (float)(s == 1 ? -v : v);
        }
        public static string CStr(byte[] d, int o)
        {
            int e = o;
            while (e < d.Length && d[e] != 0) e++;
            return Encoding.ASCII.GetString(d, o, e - o);
        }
    }

    /// <summary>model.vbn: the skeleton and its bind pose.</summary>
    public class Skeleton
    {
        public class Bone
        {
            public string Name;
            public int Parent;
            public uint Hash;
            public float[] Pos, Rot, Scale;    // bind local: position, quaternion, scale
        }
        public List<Bone> Bones = new List<Bone>();
        public Mat4[] InverseBind;
        public List<List<int>> JointTables = new List<List<int>>();   // model.jtb

        public static Skeleton Load(string vbnPath)
        {
            var d = File.ReadAllBytes(vbnPath);
            // " NBV" files (most Wii U fighters) are little-endian, "VBN " ones big-endian
            if (d[0] == ' ' && d[1] == 'N')
            {
                for (int i = 8; i < 28; i += 4) Array.Reverse(d, i, 4);
                int n = BE.I32(d, 8), o = 28;
                for (int b = 0; b < n; b++, o += 76)          // name[64], type, parent, hash
                    for (int i = 64; i < 76; i += 4) Array.Reverse(d, o + i, 4);
                for (; o + 4 <= d.Length; o += 4) Array.Reverse(d, o, 4);   // the bind poses
            }
            var s = new Skeleton();
            int count = BE.I32(d, 8);
            int off = 28;
            for (int i = 0; i < count; i++)
            {
                s.Bones.Add(new Bone
                {
                    Name = BE.CStr(d, off),
                    Parent = BE.I32(d, off + 68),
                    Hash = BE.U32(d, off + 72),
                });
                off += 76;
            }
            foreach (var b in s.Bones)
            {
                float[] v = new float[9];
                for (int k = 0; k < 9; k++) v[k] = BE.F32(d, off + 4 * k);
                off += 36;
                b.Pos = new[] { v[0], v[1], v[2] };
                b.Rot = Mat4.EulerToQuat(v[3], v[4], v[5]);
                b.Scale = new[] { v[6], v[7], v[8] };
            }
            var bind = s.World(null, 0);
            s.InverseBind = new Mat4[bind.Length];
            for (int i = 0; i < bind.Length; i++) s.InverseBind[i] = bind[i].Inverse();
            string jtb = Path.Combine(Path.GetDirectoryName(vbnPath), "model.jtb");
            if (File.Exists(jtb))
                s.JointTables = LoadJtb(jtb);
            return s;
        }

        static List<List<int>> LoadJtb(string path)
        {
            var d = File.ReadAllBytes(path);
            var tables = new List<List<int>>();
            if (d.Length < 4) return tables;
            int n1 = BE.U16(d, 0), n2 = BE.U16(d, 2);
            int o = 4;
            foreach (int n in new[] { n1, n2 })
            {
                var t = new List<int>();
                for (int i = 0; i < n && o + 2 <= d.Length; i++, o += 2)
                    t.Add(BE.I16(d, o));
                tables.Add(t);
            }
            return tables;
        }

        /// <summary>World matrices of every bone for an animation frame (anim null: the bind pose).
        /// Bones the animation doesn't move keep their bind pose.</summary>
        public Mat4[] World(Omo anim, float frame)
        {
            var w = new Mat4[Bones.Count];
            for (int i = 0; i < Bones.Count; i++)
            {
                var b = Bones[i];
                float[] p = b.Pos, q = b.Rot, sc = b.Scale;
                if (anim != null)
                    anim.Sample(b.Hash, frame, ref p, ref q, ref sc);
                var local = Mat4.TRS(p, q, sc);
                w[i] = b.Parent >= 0 && b.Parent < i ? w[b.Parent] * local : local;
            }
            return w;
        }

        /// <summary>The bone an ACMD script means by a bone ID, as Smash Forge resolves it: IDs from
        /// 1000 up use model.jtb's later tables; in table 0, 0 is TransN and ID n is table[n - 1].</summary>
        public int ScriptBone(int id)
        {
            int table = 0;
            while (id >= 1000) { id -= 1000; table++; }
            if (JointTables.Count == 0 || JointTables[0].Count == 0)
                return id >= 0 && id < Bones.Count ? id : 0;
            if (table == 0)
            {
                if (id <= 0)
                {
                    int t = Bones.FindIndex(b => b.Name == "TransN");
                    return t >= 0 ? t : 0;
                }
                var t0 = JointTables[0];
                return id - 1 < t0.Count && t0[id - 1] >= 0 && t0[id - 1] < Bones.Count ? t0[id - 1] : 0;
            }
            var tt = JointTables[Math.Min(table, JointTables.Count - 1)];
            return id < tt.Count && tt[id] >= 0 && tt[id] < Bones.Count ? tt[id] : 0;
        }
    }

    /// <summary>model.nud (Wii U, NDP3): positions, bone weights and triangles of every mesh.</summary>
    public class NudModel
    {
        public class Poly
        {
            public float[] Pos;     // x y z per vertex
            public int[] Bones;     // 4 per vertex
            public float[] Weights; // 4 per vertex
            public int[] Tris;      // 3 per triangle
            public float[] UV;      // u v per vertex (the first UV set), or null
            public int TextureHash; // the material's first texture
            public bool AlphaTest;  // the material blends or alpha-tests
            public Texture Texture; // resolved from model.nut by FighterAssets
            public Dictionary<string, float[]> Props = new Dictionary<string, float[]>();   // NU_ material values
        }
        public class Mesh
        {
            public string Name;
            public List<Poly> Polys = new List<Poly>();
            public bool Visible = true;
        }
        public List<Mesh> Meshes = new List<Mesh>();

        public static NudModel Load(string path)
        {
            var d = File.ReadAllBytes(path);
            if (Encoding.ASCII.GetString(d, 0, 4) != "NDP3")
                throw new InvalidDataException("not a Wii U model.nud (NDP3)");
            int nsets = BE.U16(d, 10);
            int pcs = BE.I32(d, 16) + 0x30, pcz = BE.I32(d, 20), vcz = BE.I32(d, 24), vaz = BE.I32(d, 28);
            int vcs = pcs + pcz, vas = vcs + vcz, names = vas + vaz;
            int off = 0x30;
            var objs = new List<Tuple<string, int, int>>();
            for (int i = 0; i < nsets; i++)
            {
                off += 28;
                int noff = BE.I32(d, off + 4);
                off += 8;
                string name = BE.CStr(d, names + noff);
                int single = BE.I16(d, off + 4), pcount = BE.U16(d, off + 6);
                off += 12;
                objs.Add(Tuple.Create(name, single, pcount));
            }
            var model = new NudModel();
            foreach (var o in objs)
            {
                var mesh = new Mesh { Name = o.Item1 };
                for (int p = 0; p < o.Item3; p++)
                {
                    int ps = BE.I32(d, off) + pcs, vs = BE.I32(d, off + 4) + vcs, va = BE.I32(d, off + 8) + vas;
                    int vc = BE.U16(d, off + 12), vsz = d[off + 14], uvsz = d[off + 15];
                    int mat = BE.I32(d, off + 16);
                    int fc = BE.U16(d, off + 32), pflag = BE.U16(d, off + 34);
                    off += 48;
                    var poly = ReadPoly(d, ps, vs, va, vc, vsz, uvsz, fc, pflag, o.Item2);
                    ReadMaterial(d, mat, poly, names);
                    mesh.Polys.Add(poly);
                }
                model.Meshes.Add(mesh);
            }
            return model;
        }

        static Poly ReadPoly(byte[] d, int ps, int vs, int va, int vc, int vsz, int uvsz, int fc, int pflag, int single)
        {
            int boneType = vsz & 0xF0, normalType = vsz & 0xF;
            int uvCount = uvsz >> 4, colorType = uvsz & 0xE, uvType = uvsz & 1;
            int nsize;
            switch (normalType)
            {
                case 0: nsize = 4; break;
                case 1: nsize = 20; break;
                case 2: case 3: nsize = 52; break;
                case 6: nsize = 8; break;
                case 7: nsize = 24; break;
                default: throw new InvalidDataException("unsupported vertex type " + normalType);
            }
            int uvb = (colorType == 2 ? 4 : colorType == 4 ? 8 : 0) + uvCount * (uvType == 0 ? 4 : 8);
            var poly = new Poly { Pos = new float[vc * 3], Bones = new int[vc * 4], Weights = new float[vc * 4] };
            int cb = colorType == 2 ? 4 : colorType == 4 ? 8 : 0;
            if (uvCount > 0) poly.UV = new float[vc * 2];
            Action<int, int> readUV = (k, q) =>
            {
                if (poly.UV == null) return;
                q += cb;
                poly.UV[k * 2] = uvType == 0 ? BE.Half(d, q) : BE.F32(d, q);
                poly.UV[k * 2 + 1] = uvType == 0 ? BE.Half(d, q + 2) : BE.F32(d, q + 4);
            };
            if (boneType != 0)
            {
                for (int k = 0; k < vc; k++) readUV(k, vs + k * uvb);
                int bsz = boneType == 0x10 ? 32 : boneType == 0x20 ? 16 : 8;
                int p = va;
                for (int k = 0; k < vc; k++, p += 12 + nsize + bsz)
                {
                    for (int c = 0; c < 3; c++) poly.Pos[k * 3 + c] = BE.F32(d, p + 4 * c);
                    int q = p + 12 + nsize;
                    for (int j = 0; j < 4; j++)
                    {
                        if (boneType == 0x40) { poly.Bones[k * 4 + j] = d[q + j]; poly.Weights[k * 4 + j] = d[q + 4 + j] / 255f; }
                        else if (boneType == 0x20) { poly.Bones[k * 4 + j] = BE.U16(d, q + 2 * j); poly.Weights[k * 4 + j] = BE.Half(d, q + 8 + 2 * j); }
                        else { poly.Bones[k * 4 + j] = BE.I32(d, q + 4 * j); poly.Weights[k * 4 + j] = BE.F32(d, q + 16 + 4 * j); }
                    }
                }
            }
            else
            {
                int p = vs;
                for (int k = 0; k < vc; k++, p += 12 + nsize + uvb)
                {
                    for (int c = 0; c < 3; c++) poly.Pos[k * 3 + c] = BE.F32(d, p + 4 * c);
                    readUV(k, p + 12 + nsize);
                    poly.Bones[k * 4] = Math.Max(0, single);
                    poly.Weights[k * 4] = 1;
                }
            }
            var idx = new int[fc];
            for (int i = 0; i < fc; i++) idx[i] = BE.U16(d, ps + 2 * i);
            var tris = new List<int>();
            if ((pflag >> 8) == 0x40)
            {
                for (int i = 0; i + 2 < fc; i += 3) { tris.Add(idx[i]); tris.Add(idx[i + 1]); tris.Add(idx[i + 2]); }
            }
            else if (fc >= 3)     // triangle strips, 0xFFFF restarts
            {
                int f1 = idx[0], f2 = idx[1], dir = 1, i = 2;
                while (i < fc)
                {
                    int f3 = idx[i++];
                    if (f3 == 0xFFFF)
                    {
                        if (i + 1 >= fc) break;
                        f1 = idx[i++]; f2 = idx[i++]; dir = 1;
                        continue;
                    }
                    dir = -dir;
                    if (f1 != f2 && f2 != f3 && f3 != f1)
                    {
                        if (dir > 0) { tris.Add(f3); tris.Add(f2); tris.Add(f1); }
                        else { tris.Add(f2); tris.Add(f3); tris.Add(f1); }
                    }
                    f1 = f2; f2 = f3;
                }
            }
            poly.Tris = tris.Where(t => t < vc).Count() == tris.Count ? tris.ToArray() : FilterTris(tris, vc);
            return poly;
        }

        /// <summary>The first material (Smash Forge's NUD.ReadMaterials): blend / alpha test and texture 0.</summary>
        static void ReadMaterial(byte[] d, int mat, Poly poly, int names)
        {
            if (mat <= 0 || mat + 32 > d.Length) return;
            int src = BE.U16(d, mat + 8), texCount = BE.U16(d, mat + 10), dst = BE.U16(d, mat + 12), alphaFunc = BE.U16(d, mat + 14);
            poly.AlphaTest = src != 0 || dst != 0 || alphaFunc != 0;
            if (texCount > 0 && mat + 36 <= d.Length)
                poly.TextureHash = BE.I32(d, mat + 32);
            // the material's values (NU_colorGain, NU_diffuseColor, ...): size, name, count, values
            int p = mat + 32 + texCount * 24;
            for (int guard = 0; guard < 64 && p + 16 <= d.Length; guard++)
            {
                int size = BE.I32(d, p), name = BE.I32(d, p + 4), count = d[p + 11];
                if (count > 0 && count <= 16 && p + 16 + count * 4 <= d.Length)
                {
                    var v = new float[count];
                    for (int i = 0; i < count; i++) v[i] = BE.F32(d, p + 16 + 4 * i);
                    poly.Props[BE.CStr(d, names + name)] = v;
                }
                if (size == 0) break;
                p += size;
            }
        }

        static int[] FilterTris(List<int> tris, int vc)
        {
            var o = new List<int>();
            for (int i = 0; i + 2 < tris.Count; i += 3)
                if (tris[i] < vc && tris[i + 1] < vc && tris[i + 2] < vc)
                { o.Add(tris[i]); o.Add(tris[i + 1]); o.Add(tris[i + 2]); }
            return o.ToArray();
        }
    }

    /// <summary>A motion .pac: file name -> data.</summary>
    public static class Pac
    {
        public static Dictionary<string, byte[]> Load(string path)
        {
            var d = File.ReadAllBytes(path);
            var o = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
            if (Encoding.ASCII.GetString(d, 0, 4) != "KCAP")
                return o;
            int count = BE.I32(d, 8);
            for (int i = 0; i < count; i++)
            {
                int noff = BE.I32(d, 0x10 + 4 * i);
                int doff = BE.I32(d, 0x10 + 4 * count + 4 * i);
                int size = BE.I32(d, 0x10 + 8 * count + 4 * i);
                string name = BE.CStr(d, noff);
                if (size <= 0 || doff + size > d.Length) continue;
                var b = new byte[size];
                Array.Copy(d, doff, b, 0, size);
                o[name] = b;
            }
            return o;
        }
    }

    /// <summary>An OMO skeletal animation.</summary>
    public class Omo
    {
        public int Frames;
        class Node
        {
            public uint Hash;
            public int Flags, ConstOff, KeyOff;
        }
        readonly Dictionary<uint, Node> nodes = new Dictionary<uint, Node>();
        readonly byte[] d;
        readonly int consts, keys, frameSize;
        const int POS = 0x01000000, ROT = 0x02000000, SCL = 0x04000000;

        public Omo(byte[] data)
        {
            d = data;
            if (Encoding.ASCII.GetString(d, 0, 4) != "OMO ")
                throw new InvalidDataException("not an OMO animation");
            int nc = BE.U16(d, 0x0E);
            Frames = BE.U16(d, 0x10);
            frameSize = BE.U16(d, 0x12);
            int no = BE.I32(d, 0x14);
            consts = BE.I32(d, 0x18);
            keys = BE.I32(d, 0x1C);
            for (int k = 0; k < nc; k++)
            {
                int o = no + 16 * k;
                var n = new Node { Flags = BE.I32(d, o), Hash = BE.U32(d, o + 4), ConstOff = BE.I32(d, o + 8), KeyOff = BE.I32(d, o + 12) };
                nodes[n.Hash] = n;
            }
        }

        public bool Has(uint hash) { return nodes.ContainsKey(hash); }

        /// <summary>Overwrite the tracks the animation has for this bone (frame clamped, linearly
        /// interpolated between whole frames).</summary>
        public void Sample(uint hash, float frame, ref float[] pos, ref float[] rot, ref float[] scl)
        {
            Node n;
            if (!nodes.TryGetValue(hash, out n) || Frames <= 0)
                return;
            frame = Math.Max(0, Math.Min(frame, Frames - 1));
            int a = (int)Math.Floor(frame), b = Math.Min(a + 1, Frames - 1);
            float t = frame - a;
            float[] p0 = pos, r0 = rot, s0 = scl, p1 = pos, r1 = rot, s1 = scl;
            Read(n, a, ref p0, ref r0, ref s0);
            if (t > 0 && b != a)
            {
                Read(n, b, ref p1, ref r1, ref s1);
                p0 = Lerp(p0, p1, t); s0 = Lerp(s0, s1, t); r0 = Slerp(r0, r1, t);
            }
            pos = p0; rot = r0; scl = s0;
        }

        static float[] Lerp(float[] a, float[] b, float t)
        {
            return new[] { a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t };
        }

        static float[] Slerp(float[] a, float[] b, float t)
        {
            float dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
            float sgn = dot < 0 ? -1 : 1;
            var o = new float[4];
            for (int i = 0; i < 4; i++) o[i] = a[i] + (sgn * b[i] - a[i]) * t;
            float l = (float)Math.Sqrt(o[0] * o[0] + o[1] * o[1] + o[2] * o[2] + o[3] * o[3]);
            if (l > 0) for (int i = 0; i < 4; i++) o[i] /= l;
            return o;
        }

        void Read(Node n, int frame, ref float[] pos, ref float[] rot, ref float[] scl)
        {
            int f = n.Flags;
            int ci = consts + n.ConstOff, ki = keys + frame * frameSize + n.KeyOff;
            if ((f & POS) != 0)
            {
                int t = (f >> 16) & 0xFF;
                if (t == 0x08) { pos = Interp3(ci, ki); ci += 24; ki += 6; }
                else if (t == 0x20) { pos = Const3(ci); ci += 12; }
                else if (t == 0x04) { pos = Const3(ki); ki += 12; }
            }
            if ((f & ROT) != 0)
            {
                int t = (f >> 12) & 0xF;
                float[] v = null;
                if (t == 5) { v = Interp3(ci, ki); ci += 24; ki += 6; }
                else if (t == 7) { v = Const3(ci); ci += 12; }
                else if (t == 6)
                {
                    v = new[] { BE.F32(d, ci), BE.F32(d, ci + 4), BE.F32(d, ci + 8) + BE.F32(d, ci + 12) * BE.U16(d, ki) / 65535f };
                    ci += 16; ki += 2;
                }
                else if (t == 10) { rot = Rot10(ki); ki += 8; }
                if (v != null)
                {
                    float w2 = 1 - (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
                    rot = new[] { v[0], v[1], v[2], (float)Math.Sqrt(Math.Max(0, w2)) };
                }
            }
            if ((f & SCL) != 0)
            {
                int t = f & 0xFFF;
                if (t == 0x081) scl = Interp3(ci, ki);
                else if (t == 0x201) scl = Const3(ci);
            }
        }

        float[] Const3(int o) { return new[] { BE.F32(d, o), BE.F32(d, o + 4), BE.F32(d, o + 8) }; }

        float[] Interp3(int c, int k)
        {
            var v = new float[3];
            for (int i = 0; i < 3; i++)
                v[i] = BE.F32(d, c + 4 * i) + BE.F32(d, c + 12 + 4 * i) * BE.U16(d, k + 2 * i) / 65535f;
            return v;
        }

        /// <summary>Rotation type 10 (Smash Forge OMOOld.cs): three 20-bit components and the
        /// index of the left-out (largest) one.</summary>
        float[] Rot10(int k)
        {
            int f1 = d[k] << 12 | d[k + 1] << 4 | d[k + 2] >> 4;
            int f2 = (d[k + 2] & 0xF) << 16 | d[k + 3] << 8 | d[k + 4];
            int f3 = d[k + 5] << 12 | d[k + 6] << 4 | d[k + 7] >> 4;
            int miss = d[k + 7] & 0xF;
            float s1 = (float)(1 / Math.Sqrt(2));
            var c = new List<float> { f1 * 2 * s1 / 1048575f - s1, f2 * 2 * s1 / 1048575f - s1, f3 * 2 * s1 / 1048575f - s1 };
            float rest = 1 - (c[0] * c[0] + c[1] * c[1] + c[2] * c[2]);
            c.Insert(Math.Min(miss, 3), (float)Math.Sqrt(Math.Max(0, rest)));
            return c.ToArray();
        }
    }
}
