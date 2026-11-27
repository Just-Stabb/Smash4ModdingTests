"""A fake Azahar for the tests: a GDB-stub server (Citra's packet set and register layout) in front of a Unicorn ARM11
running the dump's real enemy_fs.cro, loaded and relocated at a chosen base with tests/croload.py (as the RO service
loads it), its imports resolved against static.crs's exports. code.bin itself is not in the dump copy, so its
functions are stubs at their real addresses (`bx lr`, a few with Python behaviour: operator new allocates, the
Behavior constructor stores the accessor / kind / variation, random_range returns a scripted value ...). The
enemy_fs.cro code that runs (e.g. the Goomba's notice-hop enter, which reads its params through the
EnemyParamAccessor singleton and calls play_se through its import veneer) is the game's own.

The scenario is a list of calls (address, r0-r3, s0-s3, stack words). The server runs them one after the other
whenever the client continues, stopping at breakpoints (Z0, or BKPT words the client wrote with M), and replies W00
when the scenario is over.
"""
import socket
import struct
import threading

import unicorn as U
from unicorn import arm_const as A

RET_MAGIC = 0x0B0FFF00          # every scenario call returns here
HEAP = 0x0C000000
STACK_TOP = 0x0D100000


class Machine:
    def __init__(s, cpu_model=None):
        s.uc = U.Uc(U.UC_ARCH_ARM, U.UC_MODE_ARM)
        s.regions = []
        s.specials = {}       # addr -> fn(machine)
        s.heap = HEAP + 0x10000
        s.bps = set()
        s.stop_reason = None
        s.stepping_over = None
        s.insn_limit = 200000
        s.calls = []          # (name, addr) log of stub hits
        s.uc.hook_add(U.UC_HOOK_CODE, s._code)
        s.uc.hook_add(U.UC_HOOK_INTR, s._intr)
        s.uc.hook_add(U.UC_HOOK_MEM_UNMAPPED, s._unmapped)
        s.fault = None

    def map(s, lo, size):
        lo &= ~0xFFF
        size = (size + 0xFFF) & ~0xFFF
        s.uc.mem_map(lo, size)
        s.regions.append((lo, lo + size))

    def mapped(s, a, n=1):
        return any(lo <= a and a + n <= hi for lo, hi in s.regions)

    def write(s, a, b):
        s.uc.mem_write(a, bytes(b))
        try:
            s.uc.ctl_remove_cache(a & ~0xFFF, (a + len(b) + 0xFFF) & ~0xFFF)   # drop stale translated code
        except (AttributeError, U.UcError):
            pass

    def read(s, a, n):
        return bytes(s.uc.mem_read(a, n))

    def w32(s, a, v):
        s.write(a, struct.pack('<I', v & 0xFFFFFFFF))

    def r32(s, a):
        return struct.unpack('<I', s.read(a, 4))[0]

    def alloc(s, n, fill=b'\0'):
        a = s.heap
        s.heap += (n + 0xF) & ~0xF
        s.write(a, (fill * ((n + len(fill) - 1) // len(fill)))[:n])
        return a

    def enable_vfp(s):
        s.uc.reg_write(A.UC_ARM_REG_C1_C0_2, s.uc.reg_read(A.UC_ARM_REG_C1_C0_2) | (0xF << 20))
        s.uc.reg_write(A.UC_ARM_REG_FPEXC, 0x40000000)

    def _code(s, uc, addr, size, _ud):
        if addr in s.bps and s.stepping_over != addr:
            s.stop_reason = ('bp', addr)
            uc.emu_stop()
            return
        s.stepping_over = None
        fn = s.specials.get(addr)
        if fn:
            fn(s)

    def _intr(s, uc, intno, _ud):
        pc = uc.reg_read(A.UC_ARM_REG_PC)
        # a BKPT the client planted (unicorn reports the exception with PC after or at the instruction)
        for cand in (pc, pc - 4, pc - 2):
            w = s.read(cand, 4) if s.mapped(cand, 4) else b''
            if w == struct.pack('<I', 0xE1200070) or w[:2] == b'\x00\xbe':
                uc.reg_write(A.UC_ARM_REG_PC, cand)
                s.stop_reason = ('bkpt', cand)
                uc.emu_stop()
                return
        s.stop_reason = ('intr', intno)
        uc.emu_stop()

    def _unmapped(s, uc, access, addr, size, value, _ud):
        s.fault = (access, addr, uc.reg_read(A.UC_ARM_REG_PC))
        return False

    def reg(s, n):
        return s.uc.reg_read(A.UC_ARM_REG_R0 + n) if n < 13 else \
            s.uc.reg_read({13: A.UC_ARM_REG_SP, 14: A.UC_ARM_REG_LR, 15: A.UC_ARM_REG_PC}[n])

    def set_reg(s, n, v):
        if n < 13:
            s.uc.reg_write(A.UC_ARM_REG_R0 + n, v & 0xFFFFFFFF)
        else:
            s.uc.reg_write({13: A.UC_ARM_REG_SP, 14: A.UC_ARM_REG_LR, 15: A.UC_ARM_REG_PC}[n], v & 0xFFFFFFFF)

    def sreg(s, n):
        return s.uc.reg_read(A.UC_ARM_REG_S0 + n)

    def set_sreg_f(s, n, f):
        s.uc.reg_write(A.UC_ARM_REG_S0 + n, struct.unpack('<I', struct.pack('<f', f))[0])

    def dreg(s, n):
        return s.uc.reg_read(A.UC_ARM_REG_D0 + n)

    def run(s, count=0):
        """run from PC until RET_MAGIC, a breakpoint, or an instruction limit"""
        s.stop_reason = None
        pc = s.reg(15)
        thumb = bool(s.uc.reg_read(A.UC_ARM_REG_CPSR) & 0x20)
        try:
            s.uc.emu_start(pc | (1 if thumb else 0), RET_MAGIC, count=count or s.insn_limit)
        except U.UcError as e:
            s.stop_reason = ('fault', str(e), s.fault)
            return s.stop_reason
        if s.stop_reason is None:
            bp_ret = RET_MAGIC in s.bps or s.read(RET_MAGIC, 4) == struct.pack('<I', 0xE1200070)
            if s.reg(15) == RET_MAGIC and bp_ret and s.stepping_over != RET_MAGIC and not count:
                s.stop_reason = ('bp', RET_MAGIC)     # a return breakpoint on the scenario's return address
                s.stepping_over = RET_MAGIC
            elif s.reg(15) == RET_MAGIC:
                s.stop_reason = ('ret',)
            elif count:
                s.stop_reason = ('step',)
            else:
                s.stop_reason = ('limit',)
        return s.stop_reason


class Scenario:
    """calls run in order: (label, addr, regs dict, sregs dict, stack words)"""

    def __init__(s, m, steps):
        s.m = m
        s.steps = list(steps)
        s.i = -1
        s.active = False
        s.log = []

    def start_next(s):
        s.i += 1
        if s.i >= len(s.steps):
            return False
        label, addr, regs, sregs, stack = s.steps[s.i]
        if callable(regs):
            regs = regs()
        m = s.m
        sp = STACK_TOP - 0x1000
        for k, w in enumerate(stack or []):
            m.w32(sp + 4 * k, w)
        for n in range(13):
            m.set_reg(n, 0)
        for n, v in (regs or {}).items():
            m.set_reg(n, v)
        for n, f in (sregs or {}).items():
            m.set_sreg_f(n, f)
        m.set_reg(13, sp)
        m.set_reg(14, RET_MAGIC)
        cpsr = m.uc.reg_read(A.UC_ARM_REG_CPSR)
        m.uc.reg_write(A.UC_ARM_REG_CPSR, (cpsr & ~0x20) | (0x20 if addr & 1 else 0))
        m.set_reg(15, addr & ~1)
        s.active = True
        s.log.append(label)
        return True

    def cont(s):
        """continue: run until a stop worth reporting; None = scenario over"""
        while True:
            if not s.active:
                if not s.start_next():
                    return None
            if s.m.reg(15) == RET_MAGIC and s.m.stepping_over == RET_MAGIC:
                s.m.stepping_over = None
                s.active = False             # returned (the return breakpoint was reported)
                continue
            r = s.m.run()
            if r[0] in ('bp', 'bkpt'):
                return r
            if r[0] == 'ret':
                s.active = False
                continue
            s.log.append(('stopped', r))
            s.active = False


class GDBServer:
    """Citra's stub, as far as the tracer uses it: qSupported, ?, g, p, m, M, Z0 / z0, c, s, vCont?, \\x03, D, k"""

    def __init__(s, machine, scenario, port=0, z0=True, ack=True):
        s.m, s.sc = machine, scenario
        s.z0 = z0
        s.ack = ack
        s.lsock = socket.socket()
        s.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.lsock.bind(('127.0.0.1', port))
        s.lsock.listen(1)
        s.port = s.lsock.getsockname()[1]
        s.thread = threading.Thread(target=s.serve, daemon=True)
        s.packets = []
        s.done = threading.Event()
        s.over = False

    def start(s):
        s.thread.start()
        return s

    def serve(s):
        while not s.done.is_set():
            try:
                c, _ = s.lsock.accept()
            except OSError:
                return
            s.handle_conn(c)
            if s.over:
                break
        s.done.set()

    def send(s, c, payload):
        body = payload.encode('latin1')
        c.sendall(b'$' + body + b'#' + ('%02x' % (sum(body) & 0xFF)).encode())

    def handle_conn(s, c):
        buf = b''
        noack = False
        while True:
            try:
                d = c.recv(65536)
            except OSError:
                return
            if not d:
                return
            buf += d
            while buf:
                if buf[:1] in (b'+', b'-'):
                    buf = buf[1:]
                    continue
                if buf[:1] == b'\x03':
                    buf = buf[1:]
                    s.send(c, 'S02')
                    continue
                i = buf.find(b'$')
                j = buf.find(b'#', i)
                if i < 0 or j < 0 or len(buf) < j + 3:
                    break
                body = buf[i + 1:j]
                buf = buf[j + 3:]
                if not noack:
                    c.sendall(b'+')
                pkt = body.decode('latin1')
                s.packets.append(pkt)
                r = s.reply(pkt)
                if pkt == 'QStartNoAckMode':
                    s.send(c, 'OK')
                    noack = True
                    continue
                if r is None:
                    continue
                s.send(c, r)
                if pkt in ('D', 'k'):
                    c.close()
                    if s.over:
                        s.done.set()
                    return

    def regs_hex(s):
        m = s.m
        h = ''.join(struct.pack('<I', m.reg(i)).hex() for i in range(16))
        h += struct.pack('<I', m.uc.reg_read(A.UC_ARM_REG_CPSR)).hex()
        h += ''.join(struct.pack('<Q', m.dreg(i)).hex() for i in range(16))
        h += struct.pack('<I', 0).hex()
        return h

    def stop_reply(s, r):
        if r is None:
            s.over = True
            return 'W00'
        pc = s.m.reg(15)
        return 'T05%02x:%s;0d:%s;thread:1;' % (15, struct.pack('<I', pc).hex(), struct.pack('<I', s.m.reg(13)).hex())

    def reply(s, p):
        m = s.m
        if p.startswith('qSupported'):
            return 'PacketSize=1000;qXfer:features:read-;swbreak+' + (';QStartNoAckMode+' if not s.ack else '')
        if p == 'QStartNoAckMode':
            return None
        if p == '?':
            return 'T05thread:1;'
        if p == 'vCont?':
            return ''
        if p == 'g':
            return s.regs_hex()
        if p.startswith('p'):
            n = int(p[1:], 16)
            if n < 16:
                return struct.pack('<I', m.reg(n)).hex()
            if n == 25:
                return struct.pack('<I', m.uc.reg_read(A.UC_ARM_REG_CPSR)).hex()
            if 26 <= n < 42:
                return struct.pack('<Q', m.dreg(n - 26)).hex()
            return 'E01'
        if p.startswith('m'):
            a, n = [int(x, 16) for x in p[1:].split(',')]
            if not m.mapped(a, n):
                return 'E01'
            return m.read(a, n).hex()
        if p.startswith('M'):
            head, data = p[1:].split(':')
            a, n = [int(x, 16) for x in head.split(',')]
            if not m.mapped(a, n):
                return 'E01'
            m.write(a, bytes.fromhex(data))
            return 'OK'
        if p.startswith('Z0') or p.startswith('z0'):
            if not s.z0:
                return ''
            a = int(p.split(',')[1], 16)
            (m.bps.add if p[0] == 'Z' else m.bps.discard)(a)
            return 'OK'
        if p == 'c' or p == 'vCont;c':
            return s.stop_reply(s.sc.cont())
        if p == 's' or p == 'vCont;s':
            pc = m.reg(15)
            m.stepping_over = pc
            r = m.run(count=1)
            if r[0] == 'ret':
                s.sc.active = False
            return 'T05%02x:%s;' % (15, struct.pack('<I', m.reg(15)).hex())
        if p in ('D', 'k'):
            return 'OK'
        return ''

    def close(s):
        s.done.set()
        try:
            s.lsock.close()
        except OSError:
            pass
