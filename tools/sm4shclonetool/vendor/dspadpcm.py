"""The GameCube / Wii DSP-ADPCM encoder in pure Python: a port of grok.c from jackoalan/gc-dspadpcm-encode
(MIT licence, Copyright (c) 2015 Jack Andersen; itself from BrawlLib's AudioConverter.cs). Same arithmetic (doubles for
the coefficient search, C integer division for the frames), so the frames come out as the C encoder's.

  coefs = correlate_coefs(pcm)                        # pcm: a list of int16 samples (mono)
  frames, decoded = encode(pcm, coefs)                # 8 bytes per 14 samples; the samples the DSP will decode
  pcm2 = decode(frames, coefs, n)                     # the DSP's own decoding

Adapted for Sm4shCloneTool (the tool's own copy; see THIRD_PARTY.txt for the licence)."""
import math

DBL_EPSILON = 2.2204460492503131e-016


def _cdiv(a, b):
    """C integer division (truncates toward zero)"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _inner(pcm, at):
    out = [0.0, 0.0, 0.0]
    for i in range(3):
        v = 0.0
        for x in range(14):
            v -= pcm[at + x - i] * pcm[at + x]
        out[i] = v
    return out


def _outer(pcm, at):
    mtx = [[0.0] * 3 for _ in range(3)]
    for x in (1, 2):
        for y in (1, 2):
            v = 0.0
            for z in range(14):
                v += pcm[at + z - x] * pcm[at + z - y]
            mtx[x][y] = v
    return mtx


def _analyze_ranges(mtx, idx):
    recips = [0.0] * 3
    for x in (1, 2):
        val = max(abs(mtx[x][1]), abs(mtx[x][2]))
        if val < DBL_EPSILON:
            return True
        recips[x] = 1.0 / val
    max_index = 0
    for i in (1, 2):
        for x in range(1, i):
            tmp = mtx[x][i]
            for y in range(1, x):
                tmp -= mtx[x][y] * mtx[y][i]
            mtx[x][i] = tmp
        val = 0.0
        for x in range(i, 3):
            tmp = mtx[x][i]
            for y in range(1, i):
                tmp -= mtx[x][y] * mtx[y][i]
            mtx[x][i] = tmp
            tmp = abs(tmp) * recips[x]
            if tmp >= val:
                val = tmp
                max_index = x
        if max_index != i:
            for y in (1, 2):
                mtx[max_index][y], mtx[i][y] = mtx[i][y], mtx[max_index][y]
            recips[max_index] = recips[i]
        idx[i] = max_index
        if mtx[i][i] == 0.0:
            return True
        if i != 2:
            tmp = 1.0 / mtx[i][i]
            for x in range(i + 1, 3):
                mtx[x][i] *= tmp
    lo, hi = 1.0e10, 0.0
    for i in (1, 2):
        tmp = abs(mtx[i][i])
        lo, hi = min(lo, tmp), max(hi, tmp)
    return lo / hi < 1.0e-10


def _bidirectional(mtx, idx, vec):
    x = 0
    for i in (1, 2):
        index = idx[i]
        tmp = vec[index]
        vec[index] = vec[i]
        if x != 0:
            for y in range(x, i):
                tmp -= vec[y] * mtx[i][y]
        elif tmp != 0.0:
            x = i
        vec[i] = tmp
    for i in (2, 1):
        tmp = vec[i]
        for y in range(i + 1, 3):
            tmp -= vec[y] * mtx[i][y]
        vec[i] = tmp / mtx[i][i]
    vec[0] = 1.0


def _quadratic_merge(v):
    v2 = v[2]
    tmp = 1.0 - v2 * v2
    if tmp == 0.0:
        return True
    v0 = (v[0] - v2 * v2) / tmp
    v1 = (v[1] - v[1] * v2) / tmp
    v[0], v[1] = v0, v1
    return abs(v1) > 1.0


def _finish_record(src):
    src = list(src)
    for z in (1, 2):
        if src[z] >= 1.0:
            src[z] = 0.9999999999
        elif src[z] <= -1.0:
            src[z] = -0.9999999999
    return [1.0, src[2] * src[1] + src[1], src[2]]


def _matrix_filter(src):
    mtx = [[0.0] * 3 for _ in range(3)]
    mtx[2][0] = 1.0
    for i in (1, 2):
        mtx[2][i] = -src[i]
    for i in (2, 1):
        val = 1.0 - mtx[i][i] * mtx[i][i]
        for y in range(1, i + 1):
            mtx[i - 1][y] = (mtx[i][i] * mtx[i][y] + mtx[i][y]) / val
    dst = [1.0, 0.0, 0.0]
    for i in (1, 2):
        dst[i] = 0.0
        for y in range(1, i + 1):
            dst[i] += mtx[i][y] * dst[i - y]
    return dst


def _merge_finish_record(src):
    dst = [1.0, 0.0, 0.0]
    tmp = [0.0, 0.0, 0.0]
    val = src[0]
    for i in (1, 2):
        v2 = 0.0
        for y in range(1, i):
            v2 += dst[y] * src[i - y]
        dst[i] = -(v2 + src[i]) / val if val > 0.0 else 0.0
        tmp[i] = dst[i]
        for y in range(1, i):
            dst[y] += dst[i] * dst[i - y]
        val *= 1.0 - dst[i] * dst[i]
    return _finish_record(tmp)


def _contrast(s1, s2):
    val = (s2[2] * s2[1] + -s2[1]) / (1.0 - s2[2] * s2[2])
    val1 = s1[0] * s1[0] + s1[1] * s1[1] + s1[2] * s1[2]
    val2 = s1[0] * s1[1] + s1[1] * s1[2]
    val3 = s1[0] * s1[2]
    return val1 + 2.0 * val * val2 + 2.0 * (-s2[1] * val + -s2[2]) * val3


def _filter_records(best, exp, records):
    for _x in range(2):
        buf_list = [[0.0, 0.0, 0.0] for _ in range(exp)]
        buf1 = [0] * exp
        for rec in records:
            index, value = 0, 1.0e30
            for i in range(exp):
                t = _contrast(best[i], rec)
                if t < value:
                    value, index = t, i
            buf1[index] += 1
            b2 = _matrix_filter(rec)
            for i in range(3):
                buf_list[index][i] += b2[i]
        for i in range(exp):
            if buf1[i] > 0:
                for y in range(3):
                    buf_list[i][y] /= buf1[i]
        for i in range(exp):
            best[i] = _merge_finish_record(buf_list[i])


def _clamp16(v):
    return 32767 if v > 32767 else (-32768 if v < -32768 else v)


def correlate_coefs(source):
    """the 16 coefficients (8 pairs) for the samples"""
    samples = len(source)
    records = []
    hist = [0] * 28                     # the previous 14 samples at 0-13, the current 14 at 14-27
    pos = 0
    block = 0x3800
    while pos < samples:
        n = min(block, samples - pos)
        buf = list(source[pos:pos + n]) + [0] * 14
        pos += n
        i = 0
        while i < n:
            hist[0:14] = hist[14:28]
            hist[14:28] = buf[i:i + 14] + [0] * (14 - len(buf[i:i + 14]))
            i += 14
            vec1 = _inner(hist, 14)
            if abs(vec1[0]) > 10.0:
                mtx = _outer(hist, 14)
                idx = [0, 0, 0]
                if not _analyze_ranges(mtx, idx):
                    _bidirectional(mtx, idx, vec1)
                    if not _quadratic_merge(vec1):
                        records.append(_finish_record(vec1))
    vec1 = [1.0, 0.0, 0.0]
    for rec in records:
        b0 = _matrix_filter(rec)
        for y in (1, 2):
            vec1[y] += b0[y]
    for y in (1, 2):
        vec1[y] /= max(1, len(records))
    best = [None] * 8
    best[0] = _merge_finish_record(vec1)
    exp = 1
    w = 0
    while w < 3:
        vec2 = [0.0, -1.0, 0.0]
        for i in range(exp):
            best[exp + i] = [0.01 * vec2[y] + best[i][y] for y in range(3)]
        w += 1
        exp = 1 << w
        _filter_records(best, exp, records)
    out = []
    for z in range(8):
        for k in (1, 2):
            d = -best[z][k] * 2048.0
            if d > 0.0:
                out.append(32767 if d > 32767.0 else int(math.floor(d + 0.5)))
            else:
                out.append(-32768 if d < -32768.0 else -int(math.floor(-d + 0.5)))
    return out


def encode_frame(pcm, count, coefs):
    """pcm: 16 ints (2 history + 14 samples), changed in place to the decoded samples; returns 8 bytes"""
    best_dist, best = None, None
    for i in range(8):
        c0, c1 = coefs[2 * i], coefs[2 * i + 1]
        ins = [0] * 16
        ins[0], ins[1] = pcm[0], pcm[1]
        distance = 0
        for s in range(count):
            v1 = _cdiv(pcm[s] * c1 + pcm[s + 1] * c0, 2048)
            ins[s + 2] = v1
            v3 = _clamp16(pcm[s + 2] - v1)
            if abs(v3) > abs(distance):
                distance = v3
        scale = 0
        while scale <= 12 and (distance > 7 or distance < -8):
            scale += 1
            distance = _cdiv(distance, 2)
        scale = -1 if scale <= 1 else scale - 2
        while True:
            scale += 1
            dist = 0.0
            index = 0
            outs = [0] * 14
            for s in range(count):
                v1 = ins[s] * c1 + ins[s + 1] * c0
                v2 = _cdiv((pcm[s + 2] << 11) - v1, 2048)
                f = v2 / (1 << scale)
                v3 = int(f + 0.4999999) if v2 > 0 else int(f - 0.4999999)
                if v3 < -8:
                    t = -8 - v3
                    if index < t:
                        index = t
                    v3 = -8
                elif v3 > 7:
                    t = v3 - 7
                    if index < t:
                        index = t
                    v3 = 7
                outs[s] = v3
                v1 = (v1 + ((v3 * (1 << scale)) << 11) + 1024) >> 11
                v2 = _clamp16(v1)
                ins[s + 2] = v2
                v3 = pcm[s + 2] - v2
                dist += v3 * float(v3)
            x = index + 8
            while x > 256:
                scale += 1
                if scale >= 12:
                    scale = 11
                x >>= 1
            if not (scale < 12 and index > 1):
                break
        if best_dist is None or dist < best_dist:
            best_dist, best = dist, (i, scale, outs, ins)
    i, scale, outs, ins = best
    for s in range(count):
        pcm[s + 2] = ins[s + 2]
    out = bytearray(8)
    out[0] = ((i << 4) | (scale & 0xF)) & 0xFF
    for y in range(7):
        out[y + 1] = ((outs[2 * y] << 4) | (outs[2 * y + 1] & 0xF)) & 0xFF
    return bytes(out)


def encode(pcm, coefs=None):
    """(coefs, frames bytes, decoded samples) of mono int16 samples"""
    coefs = coefs or correlate_coefs(pcm)
    n = len(pcm)
    frames = bytearray()
    dec = []
    buf = [0] * 16
    for p in range(0, n, 14):
        count = min(14, n - p)
        buf[2:16] = list(pcm[p:p + count]) + [0] * (14 - count)
        frames += encode_frame(buf, count, coefs)
        dec += buf[2:2 + count]
        buf[0], buf[1] = buf[14], buf[15]
    return coefs, bytes(frames), dec


def decode(frames, coefs, n, hist1=0, hist2=0):
    """the DSP's decoding of n samples"""
    out = []
    for f in range(0, len(frames), 8):
        ps = frames[f]
        scale = 1 << (ps & 0xF)
        c0, c1 = coefs[2 * (ps >> 4)], coefs[2 * (ps >> 4) + 1]
        for k in range(14):
            if len(out) >= n:
                return out
            b = frames[f + 1 + k // 2]
            nib = (b >> 4) if k % 2 == 0 else (b & 0xF)
            if nib >= 8:
                nib -= 16
            v = _clamp16((((nib * scale) << 11) + 1024 + c0 * hist1 + c1 * hist2) >> 11)
            hist2, hist1 = hist1, v
            out.append(v)
    return out
