"""GDB Remote Serial Protocol client (standard library only), for Azahar / Citra / Lime3DS's GDB stub.

What it speaks:
- packets `$data#cc` with the checksum, `+` / `-` acks (retransmit on `-`), `QStartNoAckMode` when offered;
- escapes (`}` + byte ^ 0x20 for `$ # } *`) both ways, run-length encoding (`X*n`: X repeated ord(n) - 29 more
  times) when decoding;
- `qSupported` (PacketSize, qXfer:features:read, swbreak, vContSupported ...), `?`, `g` / `p` registers,
  `m` memory (chunked to the stub's packet size), `M` (only to plant / restore a BKPT when Z0 is missing),
  `Z0` / `z0` software breakpoints, `c` / `s` (or `vCont;c` / `vCont;s`), `\\x03` interrupt, `D` detach;
- stop replies `T05..` (register / thread pairs), `S05`, `W` / `X` (exit), `O` (console output).

Everything else in the toolkit goes through `Target`, which also keeps the breakpoints: they are all removed on
`close()` (also on Ctrl+C / errors: the tracer calls it in a finally block), and BKPT words planted by the fallback
are restored to the original bytes.
"""
import socket
import struct
import time
import re


class RSPError(Exception):
    pass


class Disconnected(RSPError):
    pass


def checksum(data):
    return sum(data) & 0xFF


def escape(data):
    out = bytearray()
    for b in data:
        if b in (0x23, 0x24, 0x7D, 0x2A):     # # $ } *
            out += bytes((0x7D, b ^ 0x20))
        else:
            out.append(b)
    return bytes(out)


def decode_body(data):
    """undo escapes and run-length encoding of a received packet body"""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == 0x7D and i + 1 < n:
            out.append(data[i + 1] ^ 0x20)
            i += 2
        elif b == 0x2A and i + 1 < n and out:
            out += bytes((out[-1],)) * (data[i + 1] - 29)
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def frame(payload):
    if isinstance(payload, str):
        payload = payload.encode('latin1')
    body = escape(payload)
    return b'$' + body + b'#' + ('%02x' % checksum(body)).encode()


class StopReply:
    def __init__(s, raw):
        s.raw = raw
        s.signal = None
        s.regs = {}
        s.thread = None
        s.kind = raw[:1]
        s.reason = None
        s.exited = False
        if raw[:1] in ('T', 'S') and len(raw) >= 3:
            s.signal = int(raw[1:3], 16)
            for part in raw[3:].split(';'):
                if ':' not in part:
                    continue
                k, v = part.split(':', 1)
                if k == 'thread':
                    s.thread = v
                elif re.fullmatch(r'[0-9a-fA-F]+', k):
                    s.regs[int(k, 16)] = v
                elif k in ('swbreak', 'hwbreak', 'watch', 'rwatch', 'awatch', 'library', 'replaylog'):
                    s.reason = k
        elif raw[:1] in ('W', 'X'):
            s.exited = True

    def __repr__(s):
        return 'StopReply(%r)' % s.raw


# Citra's register numbering (gdbstub.cpp): r0-r15 = 0-15, CPSR = 25, D0-D15 = 26-41, FPSCR = 42. `g` sends r0-r15,
# cpsr, then the VFP registers. A target.xml from qXfer overrides this when the stub offers one.
CITRA_REGS = [('r%d' % i, 32, i) for i in range(16)] + [('cpsr', 32, 25)] + \
             [('d%d' % i, 64, 26 + i) for i in range(16)] + [('fpscr', 32, 42)]


class RSPClient:
    def __init__(s, host='127.0.0.1', port=24689, timeout=10.0, trace=None):
        s.host, s.port, s.timeout = host, port, timeout
        s.sock = None
        s.buf = b''
        s.noack = False
        s.packet_size = 0x800
        s.features = {}
        s.trace = trace            # callable(direction, bytes) for --rsp-log
        s.async_stop = None
        s.ack_nudge = True

    # ---------------------------------------------------------------- transport
    def connect(s):
        s.sock = socket.create_connection((s.host, s.port), timeout=s.timeout)
        s.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.buf = b''
        s.noack = False

    def close(s):
        if s.sock:
            try:
                s.sock.close()
            except OSError:
                pass
        s.sock = None

    def _recv_more(s, timeout):
        s.sock.settimeout(timeout)
        try:
            d = s.sock.recv(65536)
        except socket.timeout:
            raise
        except OSError as e:
            raise Disconnected(str(e))
        if not d:
            raise Disconnected('connection closed by the stub')
        if s.trace:
            s.trace('<', d)
        s.buf += d

    def _send_raw(s, b):
        if s.trace:
            s.trace('>', b)
        try:
            s.sock.sendall(b)
        except OSError as e:
            raise Disconnected(str(e))

    def read_packet(s, timeout=None):
        """next packet body (str), acking it; skips stray acks and notifications"""
        timeout = s.timeout if timeout is None else timeout
        end = time.time() + timeout
        while True:
            i = s.buf.find(b'$')
            j = s.buf.find(b'#', i + 1) if i >= 0 else -1
            if i >= 0 and j >= 0 and len(s.buf) >= j + 3:
                body = s.buf[i + 1:j]
                cs = s.buf[j + 1:j + 3]
                pre = s.buf[:i]
                s.buf = s.buf[j + 3:]
                if b'%' in pre:
                    pass                    # notification (non-stop mode): not used
                ok = False
                try:
                    ok = int(cs, 16) == checksum(body)
                except ValueError:
                    ok = False
                if not ok:
                    if not s.noack:
                        s._send_raw(b'-')
                    continue
                if not s.noack:
                    s._send_raw(b'+')
                return decode_body(body).decode('latin1')
            left = end - time.time()
            if left <= 0:
                raise socket.timeout('no packet from the stub')
            s._recv_more(left)

    def send_packet(s, payload, tries=5):
        f = frame(payload)
        for _ in range(tries):
            s._send_raw(f)
            if s.noack:
                return
            end = time.time() + s.timeout
            while True:
                while s.buf[:1] == b'\x00':
                    s.buf = s.buf[1:]
                if s.buf[:1] == b'+':
                    s.buf = s.buf[1:]
                    if s.ack_nudge:
                        # a stray '+' (stubs ignore it) makes our TCP stack send the ACK now: a stub that writes its
                        # ack and its reply separately with Nagle on would otherwise wait for our delayed ACK
                        # (40-200 ms) before every reply
                        s._send_raw(b'+')
                    return
                if s.buf[:1] == b'-':
                    s.buf = s.buf[1:]
                    break
                if s.buf[:1] == b'$':
                    return                  # some stubs reply without acking first
                if s.buf:
                    s.buf = s.buf[1:]
                    continue
                left = end - time.time()
                if left <= 0:
                    raise socket.timeout('no ack from the stub')
                s._recv_more(left)
        raise RSPError('packet refused %d times: %r' % (tries, payload[:40]))

    def command(s, payload, timeout=None):
        s.send_packet(payload)
        while True:
            r = s.read_packet(timeout)
            if r[:1] == 'O' and r != 'OK' and re.fullmatch(r'O[0-9a-fA-F]*', r):
                continue                    # console output
            return r

    def interrupt(s):
        s._send_raw(b'\x03')

    # ---------------------------------------------------------------- handshake
    def handshake(s):
        r = s.command('qSupported:multiprocess-;swbreak+;hwbreak+;vContSupported+;xmlRegisters=arm')
        for item in r.split(';'):
            if '=' in item:
                k, v = item.split('=', 1)
                s.features[k] = v
            elif item.endswith('+') or item.endswith('-'):
                s.features[item[:-1]] = item[-1] == '+'
            elif item:
                s.features[item] = True
        if 'PacketSize' in s.features:
            try:
                s.packet_size = max(0x40, int(s.features['PacketSize'], 16))
            except ValueError:
                pass
        if s.features.get('QStartNoAckMode'):
            if s.command('QStartNoAckMode') == 'OK':
                s.noack = True
        return s.features


class Target:
    """A halted-or-running 3DS behind the stub: registers, memory, breakpoints, run control."""

    def __init__(s, client, log=print, bp_mode='auto', step_over=True):
        s.c = client
        s.log = log
        s.regs_layout = list(CITRA_REGS)
        s.g_layout = None
        s.bps = {}                  # addr -> {'kind': 2/4, 'how': 'z0'/'bkpt', 'orig': bytes}
        s.bp_mode = bp_mode         # auto / z0 / bkpt
        s.z0_ok = None
        s.step_over = step_over
        s.running = False
        s.has_vcont = False
        s.mem_errors = 0

    # ---------------------------------------------------------------- setup
    def attach(s):
        s.c.connect()
        f = s.c.handshake()
        s._load_target_xml()
        r = s.c.command('vCont?')
        s.has_vcont = r.startswith('vCont') and ';c' in r and ';s' in r
        stop = StopReply(s.c.command('?'))
        s.running = False
        return f, stop

    def _xfer(s, annex):
        data, off = '', 0
        while True:
            r = s.c.command('qXfer:features:read:%s:%x,%x' % (annex, off, 0x400))
            if not r or r[0] not in 'lm':
                return None
            data += r[1:]
            off += len(r) - 1
            if r[0] == 'l':
                return data

    def _load_target_xml(s):
        if not s.c.features.get('qXfer:features:read'):
            return
        try:
            xml = s._xfer('target.xml')
        except (RSPError, socket.timeout):
            return
        if not xml:
            return
        for inc in re.findall(r'<xi:include href="([^"]+)"', xml):
            sub = s._xfer(inc)
            if sub:
                xml += sub
        regs, num = [], 0
        for m in re.finditer(r'<reg\s([^>]*)/?>', xml):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            if 'regnum' in a:
                num = int(a['regnum'])
            regs.append((a.get('name', 'r%d' % num), int(a.get('bitsize', 32)), num))
            num += 1
        if any(r[0] == 'pc' or r[0] == 'r15' for r in regs):
            s.regs_layout = [(('r15' if n == 'pc' else 'r14' if n == 'lr' else 'r13' if n == 'sp' else n), b, k)
                             for n, b, k in regs]

    # ---------------------------------------------------------------- registers
    def read_regs(s):
        """{'r0'..'r15', 'cpsr', 'd0'..'d15' (when the g layout fits)} as ints"""
        g = s.c.command('g')
        if g.startswith('E') and len(g) == 3:
            raise RSPError('g refused: ' + g)
        out, pos = {}, 0
        for name, bits, _num in s.regs_layout:
            n = bits // 4
            if pos + n > len(g):
                break
            h = g[pos:pos + n]
            pos += n
            if 'x' in h:
                continue
            out[name] = int.from_bytes(bytes.fromhex(h), 'little')
        if 'r15' not in out:
            for i in range(16):
                out['r%d' % i] = s.read_reg(i)
        return out

    def read_reg(s, num, bits=32):
        r = s.c.command('p%x' % num)
        if not r or r.startswith('E') and len(r) == 3:
            raise RSPError('p%x refused: %r' % (num, r))
        return int.from_bytes(bytes.fromhex(r[:bits // 4]), 'little')

    def read_sregs(s, count=16):
        """VFP single registers s0.. (from the d registers)"""
        out = []
        for i in range((count + 1) // 2):
            num = next((k for n, b, k in s.regs_layout if n == 'd%d' % i), 26 + i)
            try:
                v = s.read_reg(num, 64)
            except RSPError:
                v = 0
            out += [struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0],
                    struct.unpack('<f', struct.pack('<I', v >> 32))[0]]
        return out[:count]

    # ---------------------------------------------------------------- memory
    def read(s, addr, size):
        out = bytearray()
        step = max(0x10, (s.c.packet_size - 8) // 2)
        while size > 0:
            n = min(size, step)
            r = s.c.command('m%x,%x' % (addr, n))
            if not r or (r[0] == 'E' and len(r) == 3):
                s.mem_errors += 1
                raise RSPError('cannot read 0x%08X (%s)' % (addr, r))
            b = bytes.fromhex(r)
            if not b:
                raise RSPError('empty read at 0x%08X' % addr)
            out += b
            addr += len(b)
            size -= len(b)
        return bytes(out)

    def try_read(s, addr, size):
        try:
            return s.read(addr, size)
        except RSPError:
            return None

    def u32(s, addr):
        return struct.unpack('<I', s.read(addr, 4))[0]

    def write(s, addr, data):
        r = s.c.command('M%x,%x:%s' % (addr, len(data), data.hex()))
        if r != 'OK':
            raise RSPError('M refused at 0x%08X: %s' % (addr, r))

    # ---------------------------------------------------------------- breakpoints
    def add_bp(s, addr, thumb=False):
        addr &= ~1
        if addr in s.bps:
            return True
        kind = 2 if thumb else 4
        if s.bp_mode in ('auto', 'z0') and s.z0_ok is not False:
            r = s.c.command('Z0,%x,%x' % (addr, kind))
            if r == 'OK':
                s.z0_ok = True
                s.bps[addr] = {'kind': kind, 'how': 'z0'}
                return True
            if r == '' or s.bp_mode == 'auto' and s.z0_ok is None:
                if s.z0_ok is None:
                    s.log('[rsp] the stub has no Z0 (reply %r): planting BKPT instructions instead' % r)
                s.z0_ok = False
            elif s.bp_mode == 'z0':
                s.log('[rsp] Z0 at 0x%08X refused: %s' % (addr, r))
                return False
        if s.bp_mode == 'z0':
            return False
        orig = s.try_read(addr, kind)
        if orig is None:
            return False
        bk = b'\x00\xbe' if thumb else struct.pack('<I', 0xE1200070)
        try:
            s.write(addr, bk)
        except RSPError as e:
            s.log('[rsp] cannot plant a BKPT at 0x%08X: %s' % (addr, e))
            return False
        s.bps[addr] = {'kind': kind, 'how': 'bkpt', 'orig': orig}
        return True

    def remove_bp(s, addr, forget_only=False):
        addr &= ~1
        b = s.bps.pop(addr, None)
        if not b or forget_only:
            return
        try:
            if b['how'] == 'z0':
                s.c.command('z0,%x,%x' % (addr, b['kind']))
            else:
                s.write(addr, b['orig'])
        except (RSPError, OSError, socket.timeout) as e:
            s.log('[rsp] could not remove the breakpoint at 0x%08X: %s' % (addr, e))

    def remove_all(s):
        for a in list(s.bps):
            s.remove_bp(a)

    def forget_range(s, lo, hi):
        """a module went away: drop its breakpoints without touching memory"""
        for a in [a for a in s.bps if lo <= a < hi]:
            if s.bps[a]['how'] == 'z0':
                s.remove_bp(a)
            else:
                s.remove_bp(a, forget_only=True)

    # ---------------------------------------------------------------- run control
    def _resume(s, step=False):
        if s.has_vcont:
            s.c.send_packet('vCont;s' if step else 'vCont;c')
        else:
            s.c.send_packet('s' if step else 'c')
        s.running = True

    def step(s, timeout=10.0):
        s._resume(step=True)
        return s.wait(timeout)

    def cont(s, pc=None):
        """resume; when stopped on one of our breakpoints, step over it first"""
        if pc is not None and s.step_over and (pc & ~1) in s.bps:
            a = pc & ~1
            b = s.bps[a]
            s.remove_bp(a)
            st = s.step()
            s.add_bp(a, b['kind'] == 2)
            if st is not None and st.signal not in (5, None):
                return st
            if st is not None and st.signal == 5:
                npc = s.pc_of(st)
                if npc is not None and (npc & ~1) in s.bps and (npc & ~1) != a:
                    return st              # stepped straight onto another breakpoint
        s._resume()
        return None

    def wait(s, timeout=None):
        """the next stop reply, or None on timeout (target still running)"""
        try:
            r = s.c.read_packet(timeout)
        except socket.timeout:
            return None
        while r[:1] == 'O' and r != 'OK':
            try:
                r = s.c.read_packet(timeout)
            except socket.timeout:
                return None
        s.running = False
        return StopReply(r)

    def halt(s, timeout=5.0):
        s.c.interrupt()
        return s.wait(timeout)

    def pc_of(s, stop):
        if 15 in stop.regs:
            return int.from_bytes(bytes.fromhex(stop.regs[15][:8]), 'little')
        return None

    def detach(s):
        """leave the game running. Citra-style stubs (Azahar's) halt the game while a client is connected and only
        a continue lets it run again; they may ignore 'D', so detaching with 'D' alone left the game frozen until a
        reboot (v1.0.0, reported by the user after `probe`). So: continue first (no stop reply is awaited), then 'D'
        for stubs that want it, then the caller closes the socket. Breakpoints must already be removed."""
        if not s.running:
            try:
                s.c.send_packet('vCont;c' if s.has_vcont else 'c')
                s.running = True
            except (RSPError, OSError, socket.timeout):
                pass
        try:
            s.c.command('D', timeout=1)
        except (RSPError, OSError, socket.timeout):
            pass
