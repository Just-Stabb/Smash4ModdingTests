using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Sm4shCommand.Viewer
{
    /// <summary>A decoded texture: Width x Height ARGB pixels, top row first.</summary>
    public class Texture
    {
        public int Width, Height;
        public int[] Argb;
        public bool HasAlpha;

        /// <summary>Nearest texel at (u, v), repeating.</summary>
        public int Sample(float u, float v)
        {
            int x = (int)Math.Floor(u * Width) % Width, y = (int)Math.Floor(v * Height) % Height;
            if (x < 0) x += Width;
            if (y < 0) y += Height;
            return Argb[y * Width + x];
        }
    }

    /// <summary>
    /// model.nut (Wii U, NTWU): every texture's first mip, decoded, by hash. The header layout and the
    /// GX2 deswizzle follow Smash Forge's NUT.cs / GTX.cs (MIT; GTX.cs ports AboodXD's GTX Extractor).
    /// </summary>
    public static class Nut
    {
        public static Dictionary<int, Texture> Load(string path)
        {
            var o = new Dictionary<int, Texture>();
            if (!File.Exists(path)) return o;
            var d = File.ReadAllBytes(path);
            if (d.Length < 0x10 || Encoding.ASCII.GetString(d, 0, 4) != "NTWU") return o;
            int count = BE.U16(d, 6), hp = 0x10;
            for (int i = 0; i < count && hp + 0x50 < d.Length; i++)
            {
                int headerSize = BE.U16(d, hp + 12);
                try
                {
                    int dataOffset = BE.I32(d, hp + 32) + hp, gtx = BE.I32(d, hp + 40) + hp;
                    int gidx = -1;
                    for (int p = hp; p + 12 <= hp + headerSize; p += 4)
                        if (d[p] == 'G' && d[p + 1] == 'I' && d[p + 2] == 'D' && d[p + 3] == 'X') { gidx = p; break; }
                    if (gidx >= 0)
                    {
                        int hash = BE.I32(d, gidx + 8);
                        int w = BE.I32(d, gtx + 4), h = BE.I32(d, gtx + 8), format = BE.I32(d, gtx + 20);
                        int imageSize = BE.I32(d, gtx + 32), tileMode = BE.I32(d, gtx + 48);
                        int swizzle = BE.I32(d, gtx + 52), pitch = BE.I32(d, gtx + 60);
                        imageSize = Math.Min(imageSize, d.Length - dataOffset);
                        var data = new byte[imageSize];
                        Array.Copy(d, dataOffset, data, 0, imageSize);
                        var tex = Decode(data, w, h, format, tileMode, swizzle, pitch);
                        if (tex != null && !o.ContainsKey(hash)) o[hash] = tex;
                    }
                }
                catch (Exception) { }     // an unsupported texture is just left out
                if (headerSize <= 0) break;
                hp += headerSize;
            }
            return o;
        }

        static Texture Decode(byte[] data, int w, int h, int format, int tileMode, int swizzle, int pitch)
        {
            int f = format & 0x3F;
            bool bc = f >= 0x31 && f <= 0x35;
            int bpp = f == 0x1A ? 32 : f == 0x08 || f == 0x0A || f == 0x0B ? 16 : bc ? (f == 0x31 || f == 0x34 ? 64 : 128) : 0;
            if (bpp == 0) return null;
            int ew = bc ? (w + 3) / 4 : w, eh = bc ? (h + 3) / 4 : h, eb = bpp / 8;
            var lin = Deswizzle(data, ew, eh, eb, bpp, tileMode, swizzle, pitch);
            var t = new Texture { Width = w, Height = h, Argb = new int[w * h] };
            if (!bc)
            {
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++)
                    {
                        int p = (y * w + x) * eb, a = 255, r, g, b;
                        if (f == 0x1A) { r = lin[p]; g = lin[p + 1]; b = lin[p + 2]; a = lin[p + 3]; }
                        else
                        {
                            int v = lin[p] | lin[p + 1] << 8;
                            if (f == 0x08) { r = (v >> 11 & 31) * 255 / 31; g = (v >> 5 & 63) * 255 / 63; b = (v & 31) * 255 / 31; }
                            else if (f == 0x0A) { r = (v & 31) * 255 / 31; g = (v >> 5 & 31) * 255 / 31; b = (v >> 10 & 31) * 255 / 31; a = (v >> 15) * 255; }
                            else { r = (v & 15) * 17; g = (v >> 4 & 15) * 17; b = (v >> 8 & 15) * 17; a = (v >> 12 & 15) * 17; }
                        }
                        t.Argb[y * w + x] = a << 24 | r << 16 | g << 8 | b;
                    }
            }
            else
            {
                var block = new int[16];
                for (int by = 0; by < eh; by++)
                    for (int bx = 0; bx < ew; bx++)
                    {
                        int p = (by * ew + bx) * eb;
                        switch (f)
                        {
                            case 0x31: Bc1(lin, p, block, true); break;
                            case 0x32: Bc1(lin, p + 8, block, false); Bc2Alpha(lin, p, block); break;
                            case 0x33: Bc1(lin, p + 8, block, false); Bc3Alpha(lin, p, block, 24); break;
                            case 0x34: Bc4(lin, p, block, false); break;
                            case 0x35: Bc4(lin, p, block, false); Bc4(lin, p + 8, block, true); break;
                        }
                        for (int j = 0; j < 16; j++)
                        {
                            int x = bx * 4 + (j & 3), y = by * 4 + (j >> 2);
                            if (x < w && y < h) t.Argb[y * w + x] = block[j];
                        }
                    }
            }
            foreach (int c in t.Argb)
                if ((uint)c >> 24 < 250) { t.HasAlpha = true; break; }
            return t;
        }

        /// <summary>The surface's elements (pixels, or 4x4 blocks), in rows.</summary>
        static byte[] Deswizzle(byte[] src, int ew, int eh, int eb, int bpp, int tileMode, int swizzle, int pitch)
        {
            var o = new byte[ew * eh * eb];
            int pipeSwizzle = ((swizzle >> 8) & 1) + (((swizzle >> 9) & 3) << 1);
            for (int y = 0; y < eh; y++)
                for (int x = 0; x < ew; x++)
                {
                    int pos;
                    if (tileMode == 0 || tileMode == 1)
                        pos = (y * pitch + x) * eb;
                    else if (tileMode == 2 || tileMode == 3)     // 1D tiled: 8x8 micro tiles in rows
                        pos = ((y / 8) * (pitch / 8) + x / 8) * 64 * eb + ((PixelIndexInMicroTile(x, y, bpp) * bpp) >> 3);
                    else
                        pos = MacroTiled(x, y, bpp, pitch, pipeSwizzle);
                    int dst = (y * ew + x) * eb;
                    if (pos >= 0 && pos + eb <= src.Length)
                        Array.Copy(src, pos, o, dst, eb);
                }
            return o;
        }

        // GTX.cs (Smash Forge): 2D macro-tiled thin surfaces, 2 pipes, 4 banks
        static int MacroTiled(int x, int y, int bpp, int pitch, int swizzle)
        {
            int pixelIndex = PixelIndexInMicroTile(x, y, bpp);
            int elemOffset = (bpp * pixelIndex) >> 3;
            int pipe = (y ^ x) >> 3 & 1;
            int bank = ((y >> 5 ^ x >> 3) & 1) | ((y >> 4 ^ x >> 4) & 1) << 1;
            int bankPipe = ((pipe + 2 * bank) ^ swizzle) % 9;
            pipe = bankPipe % 2;
            bank = bankPipe / 2;
            int macroTileBytes = (bpp * 512 + 7) >> 3;
            int macroTileOffset = (x / 32 + pitch / 32 * (y / 16)) * macroTileBytes;
            int unk1 = elemOffset + (macroTileOffset >> 3);
            int unk2 = unk1 & ~0xFF;
            return (unk2 << 3) | (0xFF & unk1) | (pipe << 8) | (bank << 9);
        }

        static int PixelIndexInMicroTile(int x, int y, int bpp)
        {
            int bits = ((x & 4) << 1) | ((y & 2) << 3) | ((y & 4) << 3);
            if (bpp == 32 || bpp == 96) bits |= (x & 1) | (x & 2) | ((y & 1) << 2);
            else if (bpp == 64) bits |= (x & 1) | ((y & 1) << 1) | ((x & 2) << 1);
            else if (bpp == 128) bits |= (y & 1) | ((x & 1) << 1) | ((x & 2) << 1);
            else if (bpp == 16) bits |= (x & 1) | (x & 2) | ((y & 1) << 2);   // same as 32 (thin, 16-bit)
            return bits;
        }

        static int Rgb565(int v) { return (v >> 11 & 31) * 255 / 31 << 16 | (v >> 5 & 63) * 255 / 63 << 8 | (v & 31) * 255 / 31; }

        static void Bc1(byte[] d, int p, int[] o, bool punchThrough)
        {
            int c0 = d[p] | d[p + 1] << 8, c1 = d[p + 2] | d[p + 3] << 8;
            int a = Rgb565(c0), b = Rgb565(c1);
            var pal = new int[4];
            pal[0] = a | unchecked((int)0xFF000000);
            pal[1] = b | unchecked((int)0xFF000000);
            if (c0 > c1 || !punchThrough)
            {
                pal[2] = Mix(a, b, 2, 1, 3) | unchecked((int)0xFF000000);
                pal[3] = Mix(a, b, 1, 2, 3) | unchecked((int)0xFF000000);
            }
            else
            {
                pal[2] = Mix(a, b, 1, 1, 2) | unchecked((int)0xFF000000);
                pal[3] = 0;
            }
            uint bits = (uint)(d[p + 4] | d[p + 5] << 8 | d[p + 6] << 16 | d[p + 7] << 24);
            for (int j = 0; j < 16; j++) o[j] = pal[(bits >> (2 * j)) & 3];
        }

        static int Mix(int a, int b, int wa, int wb, int div)
        {
            int r = ((a >> 16 & 255) * wa + (b >> 16 & 255) * wb) / div, g = ((a >> 8 & 255) * wa + (b >> 8 & 255) * wb) / div,
                bl = ((a & 255) * wa + (b & 255) * wb) / div;
            return r << 16 | g << 8 | bl;
        }

        static void Bc2Alpha(byte[] d, int p, int[] o)
        {
            for (int j = 0; j < 16; j++)
            {
                int a = (d[p + j / 2] >> (4 * (j & 1)) & 15) * 17;
                o[j] = (o[j] & 0xFFFFFF) | a << 24;
            }
        }

        static int[] Bc3Palette(byte[] d, int p)
        {
            int a0 = d[p], a1 = d[p + 1];
            var pal = new int[8];
            pal[0] = a0; pal[1] = a1;
            if (a0 > a1) for (int i = 1; i < 7; i++) pal[i + 1] = ((7 - i) * a0 + i * a1) / 7;
            else { for (int i = 1; i < 5; i++) pal[i + 1] = ((5 - i) * a0 + i * a1) / 5; pal[6] = 0; pal[7] = 255; }
            return pal;
        }

        static ulong Bits48(byte[] d, int p)
        {
            ulong bits = 0;
            for (int i = 0; i < 6; i++) bits |= (ulong)d[p + 2 + i] << (8 * i);
            return bits;
        }

        static void Bc3Alpha(byte[] d, int p, int[] o, int shift)
        {
            var pal = Bc3Palette(d, p);
            ulong bits = Bits48(d, p);
            for (int j = 0; j < 16; j++)
                o[j] = (o[j] & ~(255 << shift)) | pal[(int)(bits >> (3 * j)) & 7] << shift;
        }

        /// <summary>BC4 (one channel, shown as grey) or BC5's second channel (green).</summary>
        static void Bc4(byte[] d, int p, int[] o, bool green)
        {
            var pal = Bc3Palette(d, p);
            ulong bits = Bits48(d, p);
            for (int j = 0; j < 16; j++)
            {
                int v = pal[(int)(bits >> (3 * j)) & 7];
                o[j] = green ? (o[j] & ~0xFF00) | v << 8 : unchecked((int)0xFF000000) | v << 16 | (green ? 0 : v << 8) | v;
            }
        }
    }
}
