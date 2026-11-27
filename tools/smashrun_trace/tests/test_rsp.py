#!/usr/bin/env python3
"""The RSP client against a scripted mock GDB server: framing, checksums, escapes, run-length encoding, acks and
retransmits, bad checksums, console output packets, qSupported / no-ack mode, registers, memory chunking,
breakpoints (Z0 and the BKPT fallback), stop replies, interrupts, detach.

  python3 tools/smashrun_trace/tests/test_rsp.py
"""
import os
import socket
import struct
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from srtrace import rsp     # noqa: E402

FAILS = []
N = [0]


def check(c, msg):
    N[0] += 1
    if not c:
        FAILS.append(msg)
        print('FAIL:', msg)


def rle(s):
    """GDB run-length encoding of a reply body (runs of > 3 identical chars, never producing # $ or a '*' count
    that would decode to those)"""
    out, i = '', 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i] and j - i < 97:
            j += 1
        n = j - i
        if n > 3 and chr(n - 1 + 29) not in '#$+-*}':
            out += s[i] + '*' + chr(n - 1 + 29)
            i = j
        else:
            out += s[i]
            i += 1
    return out


class Mock:
    def __init__(s, noack=False, z0=True, nack_first=True, bad_checksum_once=True, packet_size=0x40):
        s.mem = {}
        s.regs = [0x100 + i for i in range(16)]
        s.bps = set()
        s.log = []
        s.z0 = z0
        s.noack_offer = noack
        s.nack_first = nack_first
        s.bad_once = bad_checksum_once
        s.packet_size = packet_size
        s.ls = socket.socket()
        s.ls.bind(('127.0.0.1', 0))
        s.ls.listen(1)
        s.port = s.ls.getsockname()[1]
        s.noack = False
        s.th = threading.Thread(target=s.serve, daemon=True)
        s.th.start()

    def frame(s, body, corrupt=False):
        if isinstance(body, tuple):          # ('rle', text): already run-length encoded, '*' kept
            b = bytes(c ^ 0x20 if False else c for c in body[1].encode('latin1'))
            b = b.replace(b'}', b'}]').replace(b'#', b'}\x03').replace(b'$', b'}\x04')
        else:
            b = rsp.escape(body.encode('latin1'))
        cs = sum(b) & 0xFF
        if corrupt:
            cs ^= 0xFF
        return b'$' + b + b'#' + ('%02x' % cs).encode()

    def serve(s):
        c, _ = s.ls.accept()
        buf = b''
        first = True
        while True:
            d = c.recv(4096)
            if not d:
                return
            buf += d
            while True:
                while buf[:1] in (b'+', b'-'):
                    if buf[:1] == b'-':
                        s.log.append('client-nack')
                    buf = buf[1:]
                if buf[:1] == b'\x03':
                    buf = buf[1:]
                    c.sendall(s.frame('T02thread:1;'))
                    continue
                i = buf.find(b'$')
                j = buf.find(b'#', i)
                if i < 0 or j < 0 or len(buf) < j + 3:
                    break
                body = rsp.decode_body(buf[i + 1:j]).decode('latin1')
                buf = buf[j + 3:]
                if first and s.nack_first:
                    first = False
                    c.sendall(b'-')          # make the client resend
                    continue
                if not s.noack:
                    c.sendall(b'+')
                s.log.append(body)
                r = s.reply(body)
                if r is None:
                    continue
                if isinstance(r, list):
                    for x in r:
                        c.sendall(x)
                    continue
                if s.bad_once and body.startswith('m') and not isinstance(r, tuple):
                    s.bad_once = False
                    c.sendall(s.frame(r, corrupt=True))      # the client nacks it and takes the next copy
                c.sendall(s.frame(r))
                if body == 'QStartNoAckMode':
                    s.noack = True
                if body == 'D':
                    c.close()
                    return

    def reply(s, p):
        if p.startswith('qSupported'):
            return 'PacketSize=%x;swbreak+%s' % (s.packet_size, ';QStartNoAckMode+' if s.noack_offer else '')
        if p == 'QStartNoAckMode':
            return 'OK'
        if p == '?':
            return 'S05'
        if p == 'vCont?':
            return 'vCont;c;C;s;S'
        if p == 'g':
            return ('rle', rle(''.join(struct.pack('<I', v).hex() for v in s.regs) + '00000000' + '0' * 16 * 16 +
                               '00000000'))
        if p.startswith('p'):
            n = int(p[1:], 16)
            if 26 <= n < 42:
                return struct.pack('<ff', 1.5 + (n - 26), -2.0).hex()
            return struct.pack('<I', s.regs[n] if n < 16 else 0).hex()
        if p.startswith('m'):
            a, n = [int(x, 16) for x in p[1:].split(',')]
            if a >= 0x80000000:
                return 'E01'
            return bytes(s.mem.get(a + k, 0) for k in range(n)).hex()
        if p.startswith('M'):
            h, d = p[1:].split(':')
            a, n = [int(x, 16) for x in h.split(',')]
            for k, b in enumerate(bytes.fromhex(d)):
                s.mem[a + k] = b
            return 'OK'
        if p[:2] in ('Z0', 'z0'):
            if not s.z0:
                return ''
            a = int(p.split(',')[1], 16)
            (s.bps.add if p[0] == 'Z' else s.bps.discard)(a)
            return 'OK'
        if p in ('vCont;c', 'c'):
            s.regs[15] = 0x2000
            # console output first, then a stop with registers / thread
            return [s.frame('O' + b'hello\n'.hex()), s.frame('T05' + '0f:%s;0d:%s;thread:p1.2;swbreak:;' % (
                struct.pack('<I', 0x2000).hex(), struct.pack('<I', 0x7000).hex()))]
        if p in ('vCont;s', 's'):
            s.regs[15] += 4
            return 'T050f:%s;' % struct.pack('<I', s.regs[15]).hex()
        if p == 'D':
            return 'OK'
        if p == 'qEscape':
            return 'x}*#$'           # a reply that needs escaping
        return ''


def main():
    # framing helpers
    check(rsp.frame('m10,4') == b'$m10,4#' + ('%02x' % (sum(b'm10,4') & 0xFF)).encode(), 'frame / checksum')
    check(rsp.escape(b'a#b$c}d*') == b'a}\x03b}\x04c}]d}\x0a', 'escape # $ } *')
    check(rsp.decode_body(b'a}\x03b}\x04c}]d}\x0a') == b'a#b$c}d*', 'unescape')
    check(rsp.decode_body(b'0* ') == b'0000', 'run-length: "0* " = 4 zeros')
    check(rsp.decode_body(rle('f' * 40).encode()) == b'f' * 40, 'run-length round trip')
    sr = rsp.StopReply('T050f:00200000;0d:00700000;thread:p1.2;swbreak:;')
    check(sr.signal == 5 and sr.regs[15] == '00200000' and sr.thread == 'p1.2' and sr.reason == 'swbreak',
          'stop reply parsing')
    check(rsp.StopReply('W00').exited and rsp.StopReply('X09').exited, 'exit replies')

    for noack in (False, True):
        m = Mock(noack=noack)
        c = rsp.RSPClient('127.0.0.1', m.port, timeout=5)
        t = rsp.Target(c, log=lambda *a: None)
        feats, stop = t.attach()
        tag = '[noack=%s] ' % noack
        check(c.packet_size == 0x40, tag + 'PacketSize parsed')
        check(c.noack == noack, tag + 'no-ack mode only when offered')
        check(m.log.count('qSupported:multiprocess-;swbreak+;hwbreak+;vContSupported+;xmlRegisters=arm') == 1,
              tag + 'the nacked first packet was resent once')
        check(stop.signal == 5 and t.has_vcont, tag + '? and vCont? handled')
        regs = t.read_regs()
        check(regs['r0'] == 0x100 and regs['r15'] == 0x10F and regs['cpsr'] == 0, tag + 'g registers (RLE reply)')
        sr = t.read_sregs(4)
        check(sr == [1.5, -2.0, 2.5, -2.0], tag + 'VFP singles from p (d registers)')
        for k in range(0x100):
            m.mem[0x1000 + k] = k
        b = t.read(0x1000, 0x100)
        check(b == bytes(range(0x100)), tag + 'memory read chunked to the packet size (and a bad checksum retried)')
        chunks = [p for p in m.log if p.startswith('m1')]
        check(len(chunks) >= 8, tag + 'chunked reads: %d' % len(chunks))
        check(t.try_read(0x90000000, 4) is None, tag + 'unreadable memory -> None')
        if not noack:
            check('client-nack' in m.log, tag + 'the corrupt reply was nacked')
        check(c.command('qEscape') == 'x}*#$', tag + 'escaped reply decoded')
        check(t.add_bp(0x2000) and 0x2000 in m.bps, tag + 'Z0 breakpoint')
        t.cont()
        st = t.wait(5)
        check(st and st.signal == 5 and t.pc_of(st) == 0x2000, tag + 'continue -> console output skipped -> T05 at the bp')
        n_before = len(m.log)
        t.cont(0x2000)
        t.wait(5)
        seq = m.log[n_before:]
        check(seq[:4] == ['z0,2000,4', 'vCont;s', 'Z0,2000,4', 'vCont;c'], tag + 'step-over sequence: %s' % seq[:4])
        t.c.interrupt()
        st = t.wait(5)
        check(st and st.signal == 2, tag + 'interrupt -> stop')
        t.remove_all()
        check(not m.bps and not t.bps, tag + 'every breakpoint removed')
        t.detach()
        c.close()

    # BKPT fallback: a stub without Z0
    m = Mock(z0=False, nack_first=False, bad_checksum_once=False)
    c = rsp.RSPClient('127.0.0.1', m.port, timeout=5)
    t = rsp.Target(c, log=lambda *a: None)
    t.attach()
    for k, v in enumerate(b'\x1e\xff\x2f\xe1\x70\x47'):
        m.mem[0x3000 + k] = v
    check(t.add_bp(0x3000), 'BKPT fallback planted (ARM)')
    check(bytes(m.mem[0x3000 + k] for k in range(4)) == struct.pack('<I', 0xE1200070), 'ARM BKPT word written')
    check(t.add_bp(0x3005, thumb=True), 'BKPT fallback planted (Thumb)')
    check(bytes(m.mem[0x3004 + k] for k in range(2)) == b'\x00\xbe', 'Thumb BKPT halfword written')
    t.remove_all()
    check(bytes(m.mem[0x3000 + k] for k in range(6)) == b'\x1e\xff\x2f\xe1\x70\x47', 'original bytes restored')
    t.detach()
    c.close()
    print('rsp: %d checks, %d failed' % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
