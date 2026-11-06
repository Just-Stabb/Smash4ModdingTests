"""Lumen (.lm) ActionScript (AVM1) disassembler: the actions of tag F005 (SWF bytecode, little-endian on both the
Wii U and the 3DS); push types 0 / 8 / 9 are symbol indices (tag F001).

  python3 tools/lm_actions.py FILE.lm [ACTION...]
"""
import struct, sys
sys.path.insert(0, '/home/user/Smash4ModdingTests/tools')
import chara_layout as cl
OPS = {0x00:'End',0x04:'NextFrame',0x05:'PrevFrame',0x06:'Play',0x07:'Stop',0x0A:'Add',0x0B:'Subtract',0x0C:'Multiply',
 0x0D:'Divide',0x0E:'Equals',0x0F:'Less',0x10:'And',0x11:'Or',0x12:'Not',0x13:'StringEquals',0x14:'StringLength',
 0x17:'Pop',0x18:'ToInteger',0x1C:'GetVariable',0x1D:'SetVariable',0x20:'SetTarget2',0x21:'StringAdd',0x22:'GetProperty',
 0x23:'SetProperty',0x24:'CloneSprite',0x25:'RemoveSprite',0x26:'Trace',0x30:'RandomNumber',0x34:'GetTime',
 0x3A:'Delete',0x3B:'Delete2',0x3C:'DefineLocal',0x3D:'CallFunction',0x3E:'Return',0x3F:'Modulo',0x40:'NewObject',
 0x41:'DefineLocal2',0x42:'InitArray',0x43:'InitObject',0x44:'TypeOf',0x45:'TargetPath',0x46:'Enumerate',0x47:'Add2',
 0x48:'Less2',0x49:'Equals2',0x4A:'ToNumber',0x4B:'ToString',0x4C:'PushDuplicate',0x4D:'StackSwap',0x4E:'GetMember',
 0x4F:'SetMember',0x50:'Increment',0x51:'Decrement',0x52:'CallMethod',0x53:'NewMethod',0x54:'InstanceOf',
 0x55:'Enumerate2',0x60:'BitAnd',0x61:'BitOr',0x62:'BitXor',0x63:'BitLShift',0x64:'BitRShift',0x65:'BitURShift',
 0x66:'StrictEquals',0x67:'Greater',0x68:'StringGreater',0x69:'Extends',
 0x81:'GotoFrame',0x83:'GetURL',0x87:'StoreRegister',0x88:'ConstantPool',0x8A:'WaitForFrame',0x8B:'SetTarget',
 0x8C:'GoToLabel',0x8D:'WaitForFrame2',0x8E:'DefineFunction2',0x94:'With',0x96:'Push',0x99:'Jump',0x9A:'GetURL2',
 0x9B:'DefineFunction',0x9D:'If',0x9E:'Call',0x9F:'GotoFrame2'}
def actions(lm):
    for t, b in lm.tags:
        if t == 0xF005:
            n = struct.unpack('>I', b[:4])[0]; o = 4; out = []
            for _ in range(n):
                ln = struct.unpack('>I', b[o:o+4])[0]; out.append(bytes(b[o+4:o+4+ln])); o += 4 + ((ln+3) & ~3)
            return out
    return []
def dis(a, sy, base=0):
    o = 0; lines = []
    while o < len(a):
        op = a[o]; s = o; o += 1; arg = ''
        if op >= 0x80:
            ln = struct.unpack_from('<H', a, o)[0]; pl = a[o+2:o+2+ln]; o += 2+ln
            if op == 0x96:
                q = 0; vals = []
                while q < ln:
                    ty = pl[q]; q += 1
                    if ty in (0, 9): v = struct.unpack_from('<H', pl, q)[0]; q += 2; vals.append(repr(sy[v]) if v < len(sy) else '#%d' % v)
                    elif ty == 8: v = pl[q]; q += 1; vals.append(repr(sy[v]))
                    elif ty == 7: vals.append(str(struct.unpack_from('<i', pl, q)[0])); q += 4
                    elif ty == 1: vals.append('%gf' % struct.unpack_from('<f', pl, q)[0]); q += 4
                    elif ty == 6: vals.append('%g' % struct.unpack_from('<d', pl, q)[0]); q += 8
                    elif ty == 5: vals.append('true' if pl[q] else 'false'); q += 1
                    elif ty == 4: vals.append('r%d' % pl[q]); q += 1
                    elif ty == 2: vals.append('null')
                    elif ty == 3: vals.append('undefined')
                arg = ', '.join(vals)
            elif op in (0x99, 0x9D):
                arg = '-> %d' % (o + struct.unpack('<h', pl)[0])
            elif op == 0x8C:
                arg = repr(sy[struct.unpack('<H', pl[:2])[0]])
            elif op == 0x87:
                arg = 'r%d' % pl[0]
            elif op == 0x81:
                arg = str(struct.unpack('<H', pl)[0])
            elif op == 0x9B:
                nm, npar, = struct.unpack_from('<HH', pl, 0)
                pars = [sy[x] for x in struct.unpack_from('<%dH' % npar, pl, 4)]
                size = struct.unpack_from('<H', pl, 4 + 2*npar)[0]
                arg = '%s(%s) size %d' % (sy[nm] if nm else '', ', '.join(pars), size)
            elif op == 0x8E:
                nm, npar, nreg, flags = struct.unpack_from('<HHBH', pl, 0)
                q = 7; pars = []
                for _ in range(npar):
                    r = pl[q]; v = struct.unpack_from('<H', pl, q+1)[0]; q += 3; pars.append('r%d:%s' % (r, sy[v]))
                size = struct.unpack_from('<H', pl, q)[0]
                arg = '%s(%s) regs %d flags 0x%X size %d' % (sy[nm] if nm else '', ', '.join(pars), nreg, flags, size)
            else:
                arg = pl.hex()
        lines.append('%5d  %-16s %s' % (s, OPS.get(op, 'op_%02X' % op), arg))
    return lines
if __name__ == '__main__':
    lm = cl.Lm(open(sys.argv[1], 'rb').read())
    acts = actions(lm)
    only = [int(x) for x in sys.argv[2:]]
    for i, a in enumerate(acts):
        if only and i not in only: continue
        print('== action %d (%d bytes)' % (i, len(a)))
        print('\n'.join(dis(a, lm.sy)))
