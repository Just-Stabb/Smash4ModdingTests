"""UI textures (.nut): decode an icon to a PIL image (tools/nut.py), and put a PNG into a portrait file."""
import os
import struct
import zlib

from . import _paths  # noqa: F401

_cache = {}


def read_nut(path):
    data = open(path, 'rb').read()
    if data[:2] == b'\x78\x9c':
        data = zlib.decompress(data)
    return data


def texture_ids(data):
    out = []
    i = data.find(b'GIDX')
    while i >= 0:
        out.append((i + 8, struct.unpack('>I', data[i + 8:i + 12])[0]))
        i = data.find(b'GIDX', i + 4)
    return out


def decode(path):
    """the first texture of a .nut as a PIL RGBA image (None when it can't be read)"""
    if path in _cache:
        return _cache[path]
    img = None
    try:
        import numpy as np  # noqa: F401
        from PIL import Image
        import nut
        data = read_nut(path)
        if data[:4] == b'NTP3':
            texs = nut.read_ntp3(data)
            img = Image.fromarray(texs[0][2], 'RGBA')
        else:
            d, texs = nut.load_bytes(data)
            img = Image.fromarray(nut.decode(d, texs[0]), 'RGBA')
    except Exception:
        img = None
    _cache[path] = img
    return img


def put_png(template, png, tex_ids):
    """the .nut bytes `template` (NTWU) with its first texture's picture replaced by the PNG (resized to the
    texture's size, same format) and its texture ids set to tex_ids (one per texture, in order)"""
    import numpy as np
    from PIL import Image
    import nut
    data = read_nut(template) if isinstance(template, str) else bytes(template)
    d, texs = nut.load_bytes(data)
    t = texs[0]
    img = np.asarray(Image.open(png).convert('RGBA').resize((t.w, t.h), Image.LANCZOS))
    if t.levels <= 1:
        out = bytearray(nut.replace(d, t, img))
    else:                                   # mipmapped: a new single-mip texture of the same format
        fmt = t.fmt & 0x3F
        fmt = {0x31: 0x31, 0x33: 0x33, 0x1A: 0x1A}.get(fmt, 0x33)
        out = bytearray(nut.write_ntwu([(tex_ids[0], fmt, img)]))
    for (off, _), tid in zip(texture_ids(out), tex_ids):
        struct.pack_into('>I', out, off, tid)
    return bytes(out)


def new_nut(png, tex_id, size=None, fmt=0x33):
    """a new single-texture NTWU .nut from a PNG (BC3 by default)"""
    import numpy as np
    from PIL import Image
    import nut
    im = Image.open(png).convert('RGBA')
    if size:
        im = im.resize(size, Image.LANCZOS)
    w, h = im.size
    im = im.resize((max(4, (w + 3) // 4 * 4), max(4, (h + 3) // 4 * 4)), Image.LANCZOS)
    return nut.write_ntwu([(tex_id, fmt, np.asarray(im))])


def find_icon(ui_dirs, sets, name, idx='01'):
    """the first existing <set>_<name>[_NN].nut under replace[/append]/<chr|stage>/ of the given UI folders"""
    for d in ui_dirs:
        if not d:
            continue
        for st in sets:
            kind = 'stage' if st.startswith('stage') else 'chr'
            for root in ('replace/append', 'replace'):
                for fn in ('%s_%s_%s.nut' % (st, name, idx), '%s_%s.nut' % (st, name)):
                    p = os.path.join(d, root, kind, st, fn)
                    if os.path.exists(p):
                        return p
    return None
