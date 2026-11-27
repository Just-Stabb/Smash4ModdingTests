"""Reading a hooked function's arguments from its demangled signature (ARM AAPCS with VFP: Smash 3DS passes floats in
s0-s15, back-filling, and core arguments in r0-r3 then the stack; a member function's `this` is r0).

Types are classified as:
- 'f32' float, 'f64' double (VFP);
- 'vec2' / 'vec3' / 'vec4' / 'color' (lib::Vector2 / 3 / 4, lib::Color4f) BY VALUE: homogeneous float aggregates,
  passed in s registers;
- 'ref:<T>' a reference or pointer: core register; the value is read from memory where the decoder knows T
  (lib::Vector3 const& -> 3 floats; the enemy param structs -> their words);
- 'i32' / 'u32' / 'bool' / 'u8' / 's8' / 'u16' / 's16' / enum: core register.
"""
import re
import struct

HFA = {'lib::Vector2': ('vec2', 2), 'lib::Vector3': ('vec3', 3), 'lib::Vector4': ('vec4', 4),
       'lib::Color4f': ('color', 4)}
INTS = {'int': 'i32', 'unsigned int': 'u32', 'bool': 'bool', 'unsigned char': 'u8', 'signed char': 's8',
        'char': 's8', 'short': 's16', 'unsigned short': 'u16', 'long': 'i32', 'unsigned long': 'u32'}
# how many bytes to show behind a reference / pointer of these types (words, floats)
REF_SIZES = {'lib::Vector2': 8, 'lib::Vector3': 12, 'lib::Vector4': 16, 'lib::Color4f': 16, 'lib::Matrix34': 48,
             'lib::Rect': 16, 'EnemyParamVL::InnerEnemyAttackParam': 168,
             'EnemyParamVL::InnerEnemyAttackParamOffset2': 176, 'EnemyParamVL::InnerEnemyLeaveParam': 32,
             'EnemyParamVL::InnerEnemyShieldParam': 48, 'EnemyParamVL::InnerEnemyAttackAbsoluteParam': 64,
             'app::AttackData': 0x80, 'app::Enemy::EnemyCreateParam': 0x40, 'app::ItemCreateParam': 0x50,
             'app::ItemLotCreateParam': 0x40, 'app::ItemEjectionParam': 0x40, 'app::StageShapeInfo3': 0x40,
             'app::StageDamageShapeInfo': 0x40, 'app::FieldSmashTreasureboxEjectionData': 0x40,
             'app::stGimmickNomalData': 0x40, 'app::stGimmickMovementData': 0x40,
             'app::stGimmickBeltConveyorData': 0x40, 'app::OnDamageEvent': 0x40,
             'app::GconMultiDoor::stEntryData': 0x30, 'app::GconMultiTreasure::stEntryData': 0x30,
             'unsigned int': 4, 'int': 4, 'float': 4, 'char': 32}


def split_args(sig):
    """'ns::C::f(int, lib::Vector3 const&, float) const' -> ('ns::C::f', ['int', ...], const?)"""
    depth, start = 0, None
    for i, ch in enumerate(sig):
        if ch == '(' and depth == 0 and start is None:
            start = i
        if ch in '(<':
            depth += 1
        elif ch in ')>':
            depth -= 1
    if start is None:
        return sig, [], False
    name = sig[:start]
    end = sig.rfind(')')
    inner = sig[start + 1:end]
    const = sig[end + 1:].strip().startswith('const')
    args, depth, cur = [], 0, ''
    for ch in inner:
        if ch in '(<':
            depth += 1
        elif ch in ')>':
            depth -= 1
        if ch == ',' and depth == 0:
            args.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip() and cur.strip() != 'void':
        args.append(cur.strip())
    return name, args, const


def classify(t):
    t = t.strip()
    is_ref = t.endswith('&') or t.endswith('*')
    base = re.sub(r'\b(const|volatile)\b', '', t.rstrip('&*')).strip()
    base = re.sub(r'\s+', ' ', base)
    if is_ref:
        return 'ref:' + base
    if base == 'float':
        return 'f32'
    if base == 'double':
        return 'f64'
    if base in HFA:
        return HFA[base][0]
    if base in INTS:
        return INTS[base]
    if base.startswith('app::') or base.startswith('lib::') or '::' in base:
        return 'enum:' + base           # enums / small classes by value (core register)
    return 'u32'


def is_member(name):
    """a member function? (static helpers / free functions take no `this`)"""
    parts = name.split('::')
    if len(parts) < 2:
        return False
    cls, fn = parts[-2], parts[-1]
    if fn in ('instance', 'instance_model') or cls.endswith('Utility') or cls.endswith('Util') or \
            cls in ('FieldSmashUtility', 'GlobalParameterLib', 'GlobalParameterPrizeUtility', 'MatchingUtility'):
        return False
    if parts[0] == 'app' and len(parts) == 2:
        return False
    return True


def plan(sig):
    """the argument locations: [(name, type, ('r', n) / ('s', n) / ('stack', off))]"""
    name, args, _c = split_args(sig)
    out = []
    core = 0
    stack = 0
    sfree = [True] * 16
    if is_member(name):
        out.append(('this', 'ptr', ('r', 0)))
        core = 1
    for i, a in enumerate(args):
        ty = classify(a)
        nm = 'a%d' % i
        if ty in ('f32', 'vec2', 'vec3', 'vec4', 'color', 'f64'):
            n = {'f32': 1, 'vec2': 2, 'vec3': 3, 'vec4': 4, 'color': 4, 'f64': 2}[ty]
            align = 2 if ty == 'f64' else 1
            loc = None
            for k in range(0, 17 - n, align):
                if all(sfree[k:k + n]):
                    loc = k
                    break
            if loc is not None:
                for k in range(loc, loc + n):
                    sfree[k] = False
                out.append((nm, ty, ('s', loc)))
            else:
                sfree = [False] * 16
                out.append((nm, ty, ('stack', stack)))
                stack += 4 * n
        else:
            if core < 4:
                out.append((nm, ty, ('r', core)))
                core += 1
            else:
                out.append((nm, ty, ('stack', stack)))
                stack += 4
    return out


def f32(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0]


def rnd(x):
    if isinstance(x, float):
        if x != x:
            return 'nan'
        return float('%.6g' % x)
    return x


def decode(plan_, regs, sregs, read, deref=True):
    """{arg name: value}; read(addr, size) -> bytes or None; sregs: list of floats or None (fetched only if needed)"""
    out = {}
    stk = regs.get('r13', 0)
    for nm, ty, (where, k) in plan_:
        if where == 'r':
            raw = regs.get('r%d' % k, 0)
        elif where == 's':
            raw = None
        else:
            b = read(stk + k, 4 * {'vec2': 2, 'vec3': 3, 'vec4': 4, 'color': 4, 'f64': 2}.get(ty, 1))
            raw = b
        if ty == 'ptr':
            out[nm] = '0x%08X' % raw
        elif ty in ('f32', 'vec2', 'vec3', 'vec4', 'color', 'f64'):
            n = {'f32': 1, 'vec2': 2, 'vec3': 3, 'vec4': 4, 'color': 4, 'f64': 2}[ty]
            if where == 's':
                vals = (sregs or [0.0] * 16)[k:k + n]
            elif isinstance(raw, (bytes, bytearray)) and len(raw) >= 4 * n:
                vals = list(struct.unpack('<%df' % n, raw[:4 * n]))
            else:
                vals = [None] * n
            if ty == 'f64':
                out[nm] = None
            else:
                out[nm] = rnd(vals[0]) if n == 1 else [rnd(v) for v in vals]
        elif ty.startswith('ref:'):
            if not isinstance(raw, int):
                raw = struct.unpack('<I', raw[:4])[0] if raw else 0
            T = ty[4:]
            out[nm] = '0x%08X' % raw
            size = REF_SIZES.get(T)
            if deref and size and raw:
                b = read(raw, size)
                if b:
                    if T in HFA or T in ('lib::Matrix34', 'lib::Rect', 'float'):
                        out[nm + '_val'] = [rnd(v) for v in struct.unpack('<%df' % (size // 4), b)]
                    elif T == 'char':
                        out[nm + '_str'] = b.split(b'\0')[0].decode('latin1', 'replace')
                    elif T in ('unsigned int', 'int'):
                        out[nm + '_val'] = struct.unpack('<I' if T[0] == 'u' else '<i', b)[0]
                    else:
                        out[nm + '_raw'] = b.hex()
        else:
            if not isinstance(raw, int):
                raw = struct.unpack('<I', raw[:4])[0] if raw else 0
            if ty == 'bool' or ty == 'u8':
                v = raw & 0xFF
                out[nm] = bool(v) if ty == 'bool' else v
            elif ty == 's8':
                out[nm] = struct.unpack('<b', bytes((raw & 0xFF,)))[0]
            elif ty == 'u16':
                out[nm] = raw & 0xFFFF
            elif ty == 's16':
                out[nm] = struct.unpack('<h', struct.pack('<H', raw & 0xFFFF))[0]
            elif ty == 'i32' or ty.startswith('enum:'):
                out[nm] = struct.unpack('<i', struct.pack('<I', raw & 0xFFFFFFFF))[0]
            else:
                out[nm] = raw
                if raw > 0xFFFF:
                    out[nm + '_hex'] = '0x%08X' % raw
    return out


def needs_sregs(plan_):
    return any(w == 's' for _n, _t, (w, _k) in plan_)
