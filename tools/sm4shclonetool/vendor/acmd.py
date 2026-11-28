"""ACMD script files (the game's animcmd .bin): read, edit and write; command table in acmd_info.json (from Sammi
Husky's SALT, MIT).

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import json
import os
import struct
import sys
import zlib
END = 1466366089
_INFO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'acmd_info.json')))['commands']
INFO = {int(k, 16): v for k, v in _INFO.items()}
BY_NAME = {v['name'].lower(): k for k, v in INFO.items()}
NEW_VAR = zlib.crc32(b'New_Var') & 4294967295
NEW_VAR_BASE, NEW_VAR_SLOTS, NEW_VAR_NAME_WORDS = (251659136, 64, 6)
VAR_NAMES = {}

def new_var_name(c):
    if c.ident != NEW_VAR or len(c.params) != 4 + NEW_VAR_NAME_WORDS:
        return None
    raw = b''.join((struct.pack('>I', int(w) & 4294967295) for w in c.params[4:])).split(b'\x00')[0]
    try:
        return raw.decode('ascii') or None
    except UnicodeDecodeError:
        return None

def crc(name):
    return zlib.crc32(name.lower().encode()) & 4294967295

class Command:

    def __init__(self, ident, params=None):
        self.ident = ident
        self.params = list(params or [])

    @property
    def info(self):
        return INFO.get(self.ident, {'size': 1 + len(self.params), 'name': 'unk_%08X' % self.ident, 'format': [], 'syntax': []})

    @property
    def name(self):
        return self.info['name']

    def kind(self, i):
        fmt = self.info['format']
        return fmt[i] if i < len(fmt) else 0

    def encode(self):
        out = struct.pack('>I', self.ident)
        for i, p in enumerate(self.params):
            if self.kind(i) == 1:
                out += struct.pack('>f', float(p))
            else:
                out += struct.pack('>I', int(p) & 4294967295)
        return out

    def __str__(self):
        name = new_var_name(self)
        if name:
            ident = self.params[0]
            slot = ident - NEW_VAR_BASE if NEW_VAR_BASE <= ident < NEW_VAR_BASE + NEW_VAR_SLOTS else '0x%X' % ident
            return 'New_Var(Name=%s, Type=%s, Initial=%g, Scope=%s, Slot=%s)' % (name, {0: 'float', 1: 'int'}.get(self.params[1], self.params[1]), self.params[2], {0: 'object', 1: 'move'}.get(self.params[3], self.params[3]), slot)
        syn = self.info['syntax']
        parts = []
        for i, p in enumerate(self.params):
            k = self.kind(i)
            if k == 1:
                v = '%g' % p if abs(p) < 1000000.0 else repr(p)
            elif k == 3:
                v = VAR_NAMES.get(p, 'var 0x%X' % p)
            else:
                v = '0x%X' % p if p > 9 else str(p)
            parts.append('%s=%s' % (syn[i], v) if i < len(syn) else v)
        return '%s(%s)' % (self.name, ', '.join(parts))

class ACMDFile:

    def __init__(self, scripts, version_bytes=b'\x00\x00\x00\x02'):
        self.scripts = scripts
        self.version_bytes = version_bytes

    @classmethod
    def load(cls, path):
        d = open(path, 'rb').read()
        if d[:4] != b'ACMD':
            sys.exit('%s: not an ACMD file' % path)
        if d[4] != 0:
            sys.exit('%s: little-endian (3DS) ACMD not supported' % path)
        count, = struct.unpack('>I', d[8:12])
        table = [struct.unpack('>II', d[16 + i * 8:24 + i * 8]) for i in range(count)]
        starts = sorted(set((off for _h, off in table))) + [len(d)]
        scripts = {}
        for h, off in table:
            bound = starts[starts.index(off) + 1]
            cmds = []
            a = off
            while True:
                ident, = struct.unpack('>I', d[a:a + 4])
                if ident == END:
                    cmds.append(Command(END))
                    a += 4
                    if a + 4 <= bound and struct.unpack('>I', d[a:a + 4])[0] in INFO:
                        continue
                    break
                if ident not in INFO:
                    sys.exit('unknown command 0x%08X in script 0x%08X at 0x%X' % (ident, h, a))
                c = Command(ident)
                for j in range(INFO[ident]['size'] - 1):
                    raw = d[a + 4 + j * 4:a + 8 + j * 4]
                    c.params.append(struct.unpack('>f', raw)[0] if c.kind(j) == 1 else struct.unpack('>I', raw)[0])
                cmds.append(c)
                a += INFO[ident]['size'] * 4
            scripts[h] = cmds
        f = cls(scripts, d[4:8])
        VAR_NAMES.update({c.params[0]: n for c, n in f.new_vars()})
        return f

    def new_vars(self):
        return [(c, new_var_name(c)) for k in sorted(self.scripts) for c in self.scripts[k] if new_var_name(c)]

    def script(self, name_or_crc):
        h = name_or_crc if isinstance(name_or_crc, int) else crc(name_or_crc)
        return self.scripts.get(h)

    def encode(self):
        keys = sorted(self.scripts)
        body = b''
        table = b''
        base = 16 + 8 * len(keys)
        total = 0
        for k in keys:
            data = b''.join((c.encode() for c in self.scripts[k]))
            table += struct.pack('>II', k, base + len(body))
            body += data
            total += len(self.scripts[k])
        return b'ACMD' + self.version_bytes + struct.pack('>II', len(keys), total) + table + body

    def save(self, path):
        open(path, 'wb').write(self.encode())

def fmt_script(cmds, indent='  '):
    lines = []
    depth = 0
    for c in cmds:
        if c.ident == END:
            continue
        n = c.name
        if n in ('End_If', 'End_Else', 'End_Loop') or n.lower().startswith('end'):
            depth = max(0, depth - 1)
        lines.append(indent * (depth + 1) + str(c))
        if n in ('If_Compare', 'If_Bit_Is_Set', 'If', 'Else', 'Loop', 'IF_BIT', 'If_Compare2', 'Bit_Is_Set') or n.lower().startswith('if') or n == 'Else':
            depth += 1
    return '\n'.join(lines)
