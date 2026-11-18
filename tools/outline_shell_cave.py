#!/usr/bin/env python3
"""Outline_Shell (model_commands v2, exe_v46z_outline2): a real outline OUTSIDE an object's silhouette - a band of colour
around the character (Xenoverse 2's "Flashing White Body Outline", BPE 85) - drawn as an inverted hull: each of the
model's meshes drawn a second time right after itself, pushed out along its normals, its front faces culled (only the
back faces of the fattened copy show, round the edges), in a flat colour, depth-tested so it stays behind the body.
Outline_Set (v1) colours the fighter shaders' rim light, which is inside the silhouette; this is the outside band.
Prints rpx_patch.py arguments for an executable with tools/mesh_vis_cave.py's patches (exe_v46z_outline, or the v2
mesh visibility); asserts every word it replaces.

  python3 tools/rpx_patch.py exe_v46z_outline.rpx exe_v46z_outline2.rpx \\
      $(python3 tools/outline_shell_cave.py --rpx exe_v46z_outline.rpx)
  python3 tools/outline_shell_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

How a fighter's mesh is drawn (cross_f.rpx, docs/native-notes.md "Outline shell"):
  - Every NUD polygon of a model is a NU::CommandDrawModel (vtable 0x10207DC0; execute 0x037173EC): per sub-draw it
    binds the material (shaders, constant buffers through the device context's caches), the vertex buffers and the
    vertex declaration (the fetch shader), then draws through NU::DeviceContextWiiU's DrawIndexed (0x036F3EDC; the
    non-instanced call 0x036F3EC8 goes there with one instance): the flush 0x036F3CE0 (attributes, fetch shader), then
    GX2RDrawIndexed.
  - The device context caches what it set: +0x1C4 the GX2VertexShader, +0x1C8 the geometry shader, +0x1CC the
    GX2PixelShader, +0x1D0 + 8 x slot the vertex uniform blocks {data, size}, +0x2B0 + 8 x slot the pixel ones, +0x3B0
    the blend state (+0xC target 0's GX2BlendControlReg {target, reg}, +0x4C the GX2AlphaTestReg), +0x438 the depth
    state (+0x440 its DB_DEPTH_CONTROL), +0x44C the rasterizer state (+0x450 its PA_SU_SC_MODE_CNTL), +0x468 the colour
    control (+4 logic op, +8 blend mask, +0xC multi-write, +0x10 colour buffer on).
  - The fighter vertex programs read a_Position (attribute location 0) and a_Normal (location 1: the same in all 620
    texas_cross shaders) already skinned, PerDraw (CB2) vec4 0-3 the LocalToWorld rows, PerView (CB3) vec4 0-3 the
    WorldToProjection rows, FB1 (CB7) vec4 9 compressParam (world z squashed: C.x (z - C.y) + C.y), as special.nsh's
    mask program does. No texas_cross (or other) program reads FB1 vec4 12-15 (outlineColor / padding).
So the shell is: CommandDrawModel's two draw calls hooked; after the game's draw, when the pixel program in use is a
material program (uniform blocks at 4: MC, and 7: FB1) and the FB1 bound to both stages carries this cave's mark, the
same draw again with this cave's vertex / pixel programs and states (front faces culled, depth test and write on,
stencil off, alpha test off, blend on target 0), then every state put back from the device's caches. Which models get
it is decided by the FB1 the model's own instance builds each frame (outline_cave.py's unlock hook, chained): the
outlined instance's FB1 gets the colour (vec4 12) and width (vec4 13), every other FB1 is zeroed by the game.

The programs (latte-asm sources below; tools/outline_shell_test.py re-assembles them and runs them in
tools/latte_exec.py):
  vertex: world = p L (compressParam on z); nw = normalize(n L3x3); Width < 0: world += nw x |Width| (game units);
          clip = world P; Width > 0: clip.xy += d x Width x clip.w, d the normal's screen direction in NDC per pixel
          of a 1280 x 720 picture (nc = nw P2x2; d = nc / |(640 nc.x, 360 nc.y)|): a band Width pixels wide whatever
          the zoom.
  pixel:  FB1 vec4 12 (r, g, b, alpha).
  Registers: special.nsh's (the game's own mask shaders, no pixel inputs), the vertex one with 9 GPRs and two
  semantics (0 -> R1, 1 -> R2).

Command: Outline_Shell(Target, Red, Green, Blue, Alpha, Width, Frames, FadeIn, FadeOut, Flash, Blend) (index OS_INDEX,
CRC of the name), 12 words. One shell per object (a new one replaces it, fading from where it is).
  Target   whose (acmd_ext's targets: 0 this object, ...).
  Red/Green/Blue  the band's colour, 0-255.
  Alpha    0-255: how solid (255 solid; Blend 1 adds colour x Alpha); 0 ends the shell (over this command's FadeOut).
  Width    the band's width: > 0 pixels of the 1280 x 720 picture (constant on screen), < 0 game units (-0.5: half a
           unit round the model, growing with the zoom). The fades and the pulse scale it.
  Frames / FadeIn / FadeOut / Flash  as Outline_Set's.
  Blend    0 the colour over what is behind (Alpha 255 solid), 1 added to it (a glow).

Hooks (each word asserted):
  DRAW_I 0x037174D8  bl 0x036F3EDC (CommandDrawModel's instanced draw) -> os_drawI
  DRAW_N 0x037174E8  bl 0x036F3EC8 (its draw) -> os_drawN: the game's draw, then the shell's
  FB     outline_cave.py's ol_fbgo `bl ol_apply` -> os_fb: ol_apply, then the shell's colour / width into FB1
  TICK   0x032EFB78  bl (mesh_vis_cave.py's mv_tick) -> os_tick: the earlier tick, then the shells' frame
  CLEAR  the clear-all chain's last `b 0x02FB349C` (mv_clear's) -> os_clear
  LOOKUP / SIZE1 / SIZE2 / FETCH: chained in front of Mesh_Visibility's.
  --diag: TEST ONLY OSReport lines (S4SC / S4SD per command; S4ST per shell frame with the counts of shells drawn, draws
  checked while a shell is in use and marked FB1s refused; S4SF per FB1 write, S4SR per shell drawn, S4SX a marked FB1
  refused (the pixel program's blocks): the first 30 frames after a command, then every 30th).
Space: 0x04BE5000-0x04BE8000 (docs/native-notes.md "Outline shell": past the mesh visibility's, the text region grown),
the programs at 0x04BE7400 / 0x04BE7800 (256-aligned).
Test: tools/outline_shell_test.py.
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import line_test_cave as LT  # noqa: E402
import outline_cave as OL  # noqa: E402
import mesh_vis_cave as MV  # noqa: E402

CAVE, LIMIT = 0x04BE5000, 0x04BE8000   # (v6: grown to 0x04BE8000)
TEXT_REGION = LIMIT - 0x02000000
VS_PROG, PS_PROG = 0x04BE7400, 0x04BE7800   # (v6: the region grown; v4 0x04BE6A00 / 0x04BE6E00)
OS_INDEX = 2600                 # (Mesh_Visibility 2500)
CMD_NAME = 'Outline_Shell'
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF
NPARAMS = 11
N_ENT, ENT = 16, 0x50
MAGIC = 0x53344F53              # 'S4OS' in FB1 +0xD4: this FB1 carries a shell
SMAGIC = struct.unpack('<I', struct.pack('>I', MAGIC))[0]   # the same after the unlock's in-place swap
FB_COL, FB_SHELL = 0xC0, 0xD0   # FB1 vec4 12 (r, g, b, alpha), vec4 13 (width, MAGIC, blend, weight)
MAX_WIDTH = 64.0
VARIANTS = ('full', 'noprog', 'nodraw')   # v4 TEST ONLY (--variant, with --diag): noprog keeps the game's programs for
                                          # the shell's draw, nodraw sets the shell's programs / states but skips the draw

DRAW_I, DRAW_N = 0x037174D8, 0x037174E8
DRAW_FN_I, DRAW_FN_N = 0x036F3EDC, 0x036F3EC8
DRAW_SIG = {0x037174C0: 0x2C090000, 0x037174D4: 0x41820014, 0x037174DC: 0x3BFFFFFF, 0x037174E0: 0x3BBD0040,
            0x037173EC: 0x9421FFE0, 0x10207DCC: 0x037173EC,
            0x036F3EC8: 0x81830000, 0x036F3ECC: 0x800C00B4, 0x102064F8: 0x036F3EDC}
# the device context's caches, read off the code that fills them (address: word)
CTX = dict(vs=0x1C4, gs=0x1C8, ps=0x1CC, vcb=0x1D0, pcb=0x2B0, blend=0x3B0, blend0=0x3BC, atest=0x3FC, ds=0x438,
           dsreg=0x440, rs=0x44C, rsreg=0x450, cc=0x468)
CTX_SIG = {0x036F435C: 0x801F01C4, 0x036F4418: 0x801F01C8, 0x036F4558: 0x801F01CC, 0x036F3B28: 0x3BA301D0,
           0x036F3BAC: 0x3BA302B0, 0x036F4668: 0x3BBE03B0, 0x036F4744: 0x9127000C, 0x036F4750: 0x90070010,
           0x036F46FC: 0x911D004C, 0x036F4704: 0x913D0050, 0x036F4AFC: 0x816A0438, 0x036F4B90: 0x90FE0008,
           0x036F4C48: 0x8003044C, 0x036F4C88: 0x915D0004, 0x036F4A44: 0x38FE0468, 0x036F4A58: 0x80670004,
           0x036F4A60: 0x80A7000C, 0x036F4A68: 0x80C70010, 0x036F4A6C: 0x9B670008}
# GX2 import stubs: (stub, a call site the rpx's relocations name)
GX2 = dict(SetVertexShader=(0x04B7BD08, 0x036F436C), SetPixelShader=(0x04B7BBC0, 0x036F4570),
           SetPolygonControlReg=(0x04B7BC08, 0x036F4C70), SetDepthStencilControlReg=(0x04B7BB18, 0x036F4B80),
           SetBlendControlReg=(0x04B7BA48, 0x036F4730), SetColorControl=(0x04B7BA70, 0x036F4A74),
           SetAlphaTestReg=(0x04B7BA10, 0x036F46E4))
BLEND_REG = {0: 0x21000504, 1: 0x21000104}  # CB_BLEND0_CONTROL: colour SRC_ALPHA x (INV_SRC_ALPHA | ONE); alpha kept
CULL_FRONT, CULL_BACK = 1, 2    # PA_SU_SC_MODE_CNTL bits 0 / 1
DS_STENCIL, DS_Z, DS_ZWRITE, DS_BACKFACE = 0x1, 0x2, 0x4, 0x80   # DB_DEPTH_CONTROL
DIAG_EVERY = 30

# the programs: special.nsh's registers (its vertex / pixel headers, the game's mask pass) with this vertex program's
# GPR count and two semantics
VS_REGS = ([0x109, 0, 0, 1] + [0xFFFFFFFF] * 10 + [0, 0xFFFFFFFC, 2, 0, 1] + [0xFF] * 30 + [0, 0xE, 0x10])
PS_REGS = [1, 2, 0x04000000, 0, 0] + [0] * 32 + [0xF, 1, 0x10, 0]
assert len(VS_REGS) == 52 and len(PS_REGS) == 41

PS_SOURCE = """; $MODE = "UniformBlock"
; $UNIFORM_BLOCKS[0].name = "FB1"
; $UNIFORM_BLOCKS[0].offset = 7
; $UNIFORM_BLOCKS[0].size = 672
; $NUM_SPI_PS_INPUT_CNTL = 0
; $SQ_PGM_RESOURCES_PS.NUM_GPRS = 1
; $SQ_PGM_RESOURCES_PS.STACK_SIZE = 0
; $SQ_PGM_EXPORTS_PS.EXPORT_MODE = 2
; $CB_SHADER_MASK.OUTPUT0_ENABLE = true
; $CB_SHADER_CONTROL.RT0_ENABLE = true

00 ALU: KCACHE0(CB7:0-15)
  0  x: MOV R0.x, KC0[12].x
     y: MOV R0.y, KC0[12].y
     z: MOV R0.z, KC0[12].z
     w: MOV R0.w, KC0[12].w
01 EXP_DONE: PIX0, R0.xyzw
END_OF_PROGRAM
"""

VS_HEADER = """; $MODE = "UniformBlock"
; $UNIFORM_BLOCKS[0].name = "PerDraw"
; $UNIFORM_BLOCKS[0].offset = 2
; $UNIFORM_BLOCKS[0].size = 192
; $UNIFORM_BLOCKS[1].name = "PerView"
; $UNIFORM_BLOCKS[1].offset = 3
; $UNIFORM_BLOCKS[1].size = 192
; $UNIFORM_BLOCKS[2].name = "FB1"
; $UNIFORM_BLOCKS[2].offset = 7
; $UNIFORM_BLOCKS[2].size = 672
; $ATTRIB_VARS[0].name = "a_Position"
; $ATTRIB_VARS[0].type = "vec4"
; $ATTRIB_VARS[0].location = 0
; $ATTRIB_VARS[1].name = "a_Normal"
; $ATTRIB_VARS[1].type = "vec4"
; $ATTRIB_VARS[1].location = 1
; $SQ_PGM_RESOURCES_VS.NUM_GPRS = 9
; $SQ_PGM_RESOURCES_VS.STACK_SIZE = 1
; $NUM_SPI_VS_OUT_ID = 1
; $SPI_VS_OUT_ID[0].SEMANTIC_0 = 0
; $SQ_VTX_SEMANTIC_CLEAR = 0xFFFFFFFC
; $NUM_SQ_VTX_SEMANTIC = 2
; $SQ_VTX_SEMANTIC[0].SEMANTIC_ID = 0
; $SQ_VTX_SEMANTIC[1].SEMANTIC_ID = 1
; $VGT_VERTEX_REUSE_BLOCK_CNTL.VTX_REUSE_DEPTH = 14
; $VGT_HOS_REUSE_DEPTH.REUSE_DEPTH = 16
"""


def vs_source():
    """the vertex program (latte-asm). One ALU instruction a group (operands read in cycles 0 / 1 / 2: no GPR
    read-port conflicts), the DOT4s whole; R1 a_Position, R2 a_Normal"""
    def dot4(dst, a, xyz=True):
        return [('x', 'DOT4 %s.x, %s.x, %s.x' % (dst, a, a)), ('y', 'DOT4 ____, %s.y, %s.y' % (a, a)),
                ('z', 'DOT4 ____, %s.z, %s.z' % (a, a) if xyz else 'DOT4 ____, 0.0f, 0.0f'),
                ('w', 'DOT4 ____, 0.0f, 0.0f')]
    c1 = []     # KC0 = CB2 (PerDraw: LocalToWorld rows 0-3), KC1 = CB7 (FB1)
    for ch in 'xyz':                                  # nw = n.x L0 + n.y L1 + n.z L2
        c1 += [[(ch, 'MUL R3.%s, R2.x, KC0[0].%s' % (ch, ch))],
               [(ch, 'MULADD R3.%s, R2.y, KC0[1].%s, R3.%s' % (ch, ch, ch))],
               [(ch, 'MULADD R3.%s, R2.z, KC0[2].%s, R3.%s' % (ch, ch, ch))]]
    c1 += [dot4('R5', 'R3')]                          # |nw|^2
    c1 += [[('t', 'RECIPSQRT_IEEE R5.y, PV@.x')]]
    for ch in 'xyzw':                                 # world = p.x L0 + p.y L1 + p.z L2 + L3
        c1 += [[(ch, 'MUL R4.%s, R1.x, KC0[0].%s' % (ch, ch))],
               [(ch, 'MULADD R4.%s, R1.y, KC0[1].%s, R4.%s' % (ch, ch, ch))],
               [(ch, 'MULADD R4.%s, R1.z, KC0[2].%s, R4.%s' % (ch, ch, ch))],
               [(ch, 'ADD R4.%s, R4.%s, KC0[3].%s' % (ch, ch, ch))]]
    c1 += [[('z', 'ADD R4.z, R4.z, -KC1[9].y')], [('z', 'MULADD R4.z, R4.z, KC1[9].x, KC1[9].y')]]   # compressParam
    c1 += [[('w', 'MAX R5.w, -KC1[13].x, 0.0f')], [('w', 'MUL R5.w, R5.w, R5.y')]]   # game units: max(-W, 0) / |nw|
    for ch in 'xyz':
        c1 += [[(ch, 'MULADD R4.%s, R3.%s, R5.w, R4.%s' % (ch, ch, ch))]]
    c1 += [[('w', 'MAX R7.w, KC1[13].x, 0.0f')]]     # pixels: max(W, 0)
    c2 = []     # KC0 = CB3 (PerView: WorldToProjection rows 0-3)
    for ch in 'xyzw':
        c2 += [[(ch, 'MUL R6.%s, R4.x, KC0[0].%s' % (ch, ch))]]
        c2 += [[(ch, 'MULADD R6.%s, R4.%s, KC0[%d].%s, R6.%s' % (ch, 'yzw'[k], k + 1, ch, ch))] for k in range(3)]
    for ch in 'xy':                                   # the normal's clip direction
        c2 += [[(ch, 'MUL R7.%s, R3.x, KC0[0].%s' % (ch, ch))],
               [(ch, 'MULADD R7.%s, R3.y, KC0[1].%s, R7.%s' % (ch, ch, ch))],
               [(ch, 'MULADD R7.%s, R3.z, KC0[2].%s, R7.%s' % (ch, ch, ch))]]
    c2 += [[('x', 'MUL R8.x, R7.x, 0x44200000')], [('y', 'MUL R8.y, R7.y, 0x43B40000')]]   # x 640, y 360: pixels
    c2 += [dot4('R8', 'R8', False)]
    c2 += [[('t', 'RECIPSQRT_IEEE R8.w, PV@.x')]]
    c2 += [[('z', 'MUL R8.z, R7.w, R6.w')], [('z', 'MUL R8.z, R8.z, R8.w')]]
    c2 += [[('x', 'MULADD R6.x, R7.x, R8.z, R6.x')], [('y', 'MULADD R6.y, R7.y, R8.z, R6.y')]]
    out, g = [VS_HEADER, '00 CALL_FS NO_BARRIER'], 0
    for n, (kc, cl) in enumerate([('KCACHE0(CB2:0-15) KCACHE1(CB7:0-15)', c1), ('KCACHE0(CB3:0-15)', c2)]):
        out.append('%02d ALU: %s' % (n + 1, kc))
        for grp in cl:
            for k, (slot, ins) in enumerate(grp):
                out.append(('%3d ' % g if k == 0 else '    ') + ' %s: %s' % (slot, ins.replace('PV@', 'PV%d' % (g - 1))))
            g += 1
    out += ['03 EXP_DONE: POS0, R6.xyzw', '04 EXP_DONE: PARAM0, R6.____ NO_BARRIER', 'END_OF_PROGRAM', '']
    return '\n'.join(out)


# latte-asm's output for vs_source() / PS_SOURCE (tools/outline_shell_test.py re-assembles and compares)
VS_PROGRAM = bytes.fromhex("""
00000000000080092000805C010094A04600C040000088A03C2003008806009400400300FF0F201400000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000020010809000600002241080030062000248108003006200
020090809000602002249080030462200248908003046220020010819000604002241081030862400248108103086240036000001028A000
03648000002800200368000100280040F80C9F8100280060FE0000809034A020010010809000800001241080040082000148108004008200
0460108010008000010090809000802001249080040482200148908004048220046490801000802001001081900080400124108104088240
01481081040882400468108110008040010090819000806001249081040C826001489081040C8260046C9081100080600428958210008040
04281580A9048240AD109F819001A06005AC80809000A06003A080810400820003A480810404822003A8808104088240AD009F819001E060
040010809000C000042410800600C200044810800600C200046C10800600C200040090809000C020042490800604C220044890800604C220
046C90800604C220040010819000C040042410810608C240044810810608C240046C10810608C240040090819000C06004249081060CC260
04489081060CC260046C9081060CC260030010809000E000032410800700E200034810800700E200030090809000E020032490800704E220
034890800704E22007A01F8090000001000020440000000007A41F80900000210000B4430000000008000100102800010804810000280020
F8081F0100280040F80C9F8100280060FE0000809034006107CC8081900000410808818190000041070001810600C200070401810604C220
""".replace('\n', ''))
PS_PROGRAM = bytes.fromhex("""
2000C04100000CA0000000008806209400000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
00000000000000000000000000000000000000000000000000000000000000008C000000900C00008C040000900C00208C080000900C0040
8C0C0080900C0060
""".replace('\n', ''))


def assemble():
    """(vertex program, pixel program) bytes from the sources (needs tools/latte_dis/latte-asm: build_asm.sh)"""
    import ult_to_latte as U
    out = []
    for text, stage, typ in ((vs_source(), 'vs', 5), (PS_SOURCE, 'ps', 7)):
        b = U.assemble(text, stage)
        out += [b[o:o + s] for t, o, s in U._gsh_blocks(b) if t == typ]
    return tuple(out)


def gsh(stage):
    """a GX2 shader file (.gsh) of the cave's program with its registers (for tools/latte_exec.py): latte-asm's
    file with the program and registers replaced by the cave's"""
    import ult_to_latte as U
    b = bytearray(U.assemble(vs_source() if stage == 'vs' else PS_SOURCE, stage))
    for t, o, s in U._gsh_blocks(bytes(b)):
        if t == (3 if stage == 'vs' else 6):
            regs = VS_REGS if stage == 'vs' else PS_REGS
            struct.pack_into('>%dI' % len(regs), b, o, *regs)
        if t == (5 if stage == 'vs' else 7):
            prog = VS_PROGRAM if stage == 'vs' else PS_PROGRAM
            assert len(prog) == s
            b[o:o + s] = prog
    return bytes(b)


_T = OL._T
NEW_CMDS = [
    (CMD_NAME, 'h_shell', [
        ('Target', 0, _T),
        ('Red', 1, 'The band\'s red, 0-255.'),
        ('Green', 1, 'Its green, 0-255.'),
        ('Blue', 1, 'Its blue, 0-255.'),
        ('Alpha', 1, 'How solid, 0-255 (255 solid; with Blend 1 the colour added x Alpha / 255). 0 ends the shell '
                     '(it fades out over this command\'s FadeOut; 0 at once).'),
        ('Width', 1, 'The band\'s width outside the silhouette: above 0 in pixels of the 1280 x 720 picture (the same '
                     'on screen whatever the camera\'s zoom: 1.5 a thin line, 3 a clear band, 6 a thick glow); below '
                     '0 in game units round the model (-0.5: half a unit, growing as the camera zooms in). Up to 64. '
                     'The fades and the pulse scale it.'),
        ('Frames', 0, 'Held this many frames once faded in, then it fades out over FadeOut. 0: until Alpha 0, a KO '
                      'or the match end.'),
        ('FadeIn', 0, 'Frames to grow in (0: at once). A new shell on an object that has one grows from where that one '
                      'is.'),
        ('FadeOut', 0, 'Frames to shrink away when Frames run out (with Alpha 0: over this many; 0 at once).'),
        ('Flash', 0, 'A pulse: one cycle every Flash frames (full width, none, full again, smoothly); 0 steady.'),
        ('Blend', 0, '0: the colour over what is behind it (Alpha 255 solid); 1: added to it (a glow: white stays '
                     'white over bright backgrounds, black adds nothing).')],
     'A band of colour round an object\'s silhouette, outside it (a real outline): its meshes drawn again, pushed out '
     'along their normals with their front faces culled, in a flat colour behind the body; grown in and out and '
     'pulsing. One per object; ends with Alpha 0, its Frames, a KO, the match end or a training reset. New command: '
     'needs the patched cross_f.rpx (tools/outline_shell_cave.py, exe_v46z_outline2).'),
]


def _bl(at, w):
    return OL._bl_target(at, w)


def fb_hook(orig):
    """outline_cave.py's ol_fbgo `bl ol_apply` (after `mr r4, r31; mr r5, r27`, ol_fbB's end) -> (address, ol_apply)"""
    hits = []
    for x in range(OL.CAVE, OL.LIMIT - 8, 4):
        if orig(x) == 0x7FE4FB78 and orig(x + 4) == 0x7F65DB78:
            t = _bl(x + 8, orig(x + 8))
            if t is not None and OL.CAVE <= t < OL.LIMIT:
                hits.append((x + 8, t))
    assert len(hits) == 1, 'outline cave: ol_fbgo not found once (%d)' % len(hits)
    return hits[0]


def find(orig):
    s = OL.table_find(orig, CAVE, LIMIT)
    for at, want in list(DRAW_SIG.items()) + list(CTX_SIG.items()):
        assert orig(at) == want, '0x%08X: 0x%08X, not 0x%08X' % (at, orig(at), want)
    for at, fn in ((DRAW_I, DRAW_FN_I), (DRAW_N, DRAW_FN_N)):
        assert _bl(at, orig(at)) == fn, 'draw 0x%08X: 0x%08X (want bl 0x%08X)' % (at, orig(at), fn)
    for name, site, stub in IMPORTS:
        assert _bl(site, orig(site)) == stub, '%s: 0x%08X does not call 0x%08X' % (name, site, stub)
    for i, want in enumerate(OL.NC_TARGET_SIG):
        assert orig(OL.NC_TARGET + 4 * i) == want, 'nc_target 0x%08X' % (OL.NC_TARGET + 4 * i)
    s['tick_prev'] = OL.tick_prev(orig)
    assert not CAVE <= s['tick_prev'] < LIMIT, 'already patched (tick)'
    assert MV.CAVE <= s['tick_prev'] < MV.LIMIT, 'tick: want mesh_vis_cave.py\'s mv_tick (exe_v46z_outline)'
    s['clear_at'] = OL.clear_tail(orig)
    assert not CAVE <= s['clear_at'] < LIMIT, 'already patched (clear)'
    s['fb_at'], s['ol_apply'] = fb_hook(orig)
    return s


DIAG_FMTS = [
    ('s_sc', 'S4SC t=%d acc=%08X mi=%08X c=%08X %08X %08X a=%08X\n'),
    ('s_sd', 'S4SD width=%08X fr=%d in=%d out=%d flash=%d blend=%d k=%d\n'),
    ('s_st', 'S4ST n=%d k=%d ph=%d eff=%08X drawn=%d checked=%d refused=%d\n'),
    ('s_sf', 'S4SF n=%d mi=%08X fb=%08X width=%08X a=%08X blend=%d marked=%d\n'),
    ('s_sr', 'S4SR n=%d c=%08X v=%08X p=%08X f=%08X w=%08X r=%08X d=%08X\n'),
    ('s_sx', 'S4SX n=%d c=%08X p=%08X b=%d t=%08X f=%08X\n'),
    ('s_sp', 'S4SP s=%d n=%d c=%d r=%08X %08X %08X %08X\n'),
    ('s_sm', 'S4SM c=%08X f=%08X v=%08X g=%08X p=%08X b=%d t=%08X\n'),
]
DIAG_MARKS = 4                  # S4SM: the first 4 marked draws
DIAG_PAUSE = 3107812            # 50 ms of the 62.15625 MHz timer (OSSleepTicks) after each S4SM / S4SP
OS_SLEEP_TICKS = (0x04B80970, 0x03335974)    # OSSleepTicks: the file's bl target, a game site calling it
DIAG_STEPS = 4                  # S4SP: the first 4 shells drawn, every step (v5: 4, each line + a pause)
OS_GET_CORE_ID = (0x04B80340, 0x032EF0F8)    # OSGetCoreId: the same (also 0x036F7564, ...)
# v6: imports are called through the address the game's own `bl` at a site reaches AT RUN TIME (os_resolve). The
# file's bl target (the first number) is NOT the function: Cemu resolves each import to an HLE entry elsewhere and
# rewrites the game's REL24 `bl` (rpl.cpp: relative if in reach, else an absolute `bla` to a trampoline); the file's
# targets lie in other caves' space (0x04B7BD08 is in APC_CODE). v2-v5 called them directly: the first shell drawn
# jumped into other code (the user's v5 crash log: IP 0x04B80974, in OSSleepTicks' file target).
IMPORTS = [('GX2' + k, GX2[k][1], GX2[k][0]) for k in sorted(GX2)] + \
    [('OSSleepTicks', OS_SLEEP_TICKS[1], OS_SLEEP_TICKS[0]), ('OSGetCoreId', OS_GET_CORE_ID[1], OS_GET_CORE_ID[0])]
IMP = {nm: k for k, (nm, _s, _t) in enumerate(IMPORTS)}


def call(name):
    """asm: call import `name` through os_fn (r12, CTR; a trampoline may use r11)"""
    return '''
        lis r12, os_fn@ha
        addi r12, r12, os_fn@l
        lwz r12, %d(r12)               # %s
        mtctr r12
        bctrl''' % (4 * IMP[name], name)


def src(s, hand, diag=False, pad=False, variant='full'):
    assert variant in VARIANTS
    D = dict(size=1 + NPARAMS, step=4 * (1 + NPARAMS), n=N_ENT, ent=ENT, nct=OL.NC_TARGET,
             tick_prev=s['tick_prev'], clear_to=OL.CLEAR_BACK, smvt_h=OL.FIGHTER_SM_VT >> 16,
             smvt_l=OL.FIGHTER_SM_VT & 0xFFFF, dead=OL.DEAD, every=DIAG_EVERY, ol_apply=s['ol_apply'],
             col=FB_COL, col4=FB_COL + 4, col8=FB_COL + 8, colc=FB_COL + 12, sh=FB_SHELL, sh4=FB_SHELL + 4,
             sh8=FB_SHELL + 8, shc=FB_SHELL + 12, magic_h=MAGIC >> 16, magic_l=MAGIC & 0xFFFF, smagic_h=SMAGIC >> 16, smagic_l=SMAGIC & 0xFFFF,
             fni_h=DRAW_FN_I >> 16, fni_l=DRAW_FN_I & 0xFFFF, fnn_h=DRAW_FN_N >> 16, fnn_l=DRAW_FN_N & 0xFFFF,
             bl0_h=BLEND_REG[0] >> 16, bl0_l=BLEND_REG[0] & 0xFFFF, bl1_l=BLEND_REG[1] & 0xFFFF,
             cf=CULL_FRONT, cb=CULL_BACK, dsoff=DS_STENCIL | DS_BACKFACE, dson=DS_Z | DS_ZWRITE,
             vcb7=CTX['vcb'] + 8 * 7, pcb7=CTX['pcb'] + 8 * 7, pcb7s=CTX['pcb'] + 8 * 7 + 4,
             **{'c_' + k: v for k, v in CTX.items()}, **{'g_' + k: v[0] for k, v in GX2.items()})
    step = (lambda n: '\n        li r3, %d\n        mr r4, r31\n        bl os_dstep' % n) if diag else (lambda n: '')
    D.update({'x_' + k: call('GX2' + k) for k in GX2})
    D.update(mark='\n        mr r3, r31\n        bl os_dmark' if diag else '')
    D.update(st1=step(1), st2=step(2), st3=step(3), st4=step(4), st5=step(5),
             setprog='' if variant == 'noprog' else '''
        lis r3, os_vs@ha                # the shell's programs
        addi r3, r3, os_vs@l''' + call('GX2SetVertexShader') + '''
        lis r3, os_ps@ha
        addi r3, r3, os_ps@l''' + call('GX2SetPixelShader'),
             redraw='' if variant == 'nodraw' else '\n        bctrl')
    D.update(maxw=MAX_WIDTH, cc4=CTX['cc'] + 4, cc8=CTX['cc'] + 8, ccc=CTX['cc'] + 0xC, cc10=CTX['cc'] + 0x10)
    chk, mi_of = OL.chk, OL.mi_of
    out = OL.table_src(s, 'os', OS_INDEX, CMD_CRC, 1 + NPARAMS, hand)
    out += """
# --- Outline_Shell(Target, Red, Green, Blue, Alpha, Width, Frames, FadeIn, FadeOut, Flash, Blend):
#     (r3 accessor, r5 script state, r6 (+8 execute), r7 parameters) ---------------------------------------------
# entry (0x%(ent)X): +0 accessor (0 free), +4 instance, +8 phase (1 in, 2 held, 3 out), +0xC w, +0x10 in rate,
# +0x14 out rate, +0x18 Frames left, +0x1C-+0x24 colour (0-1), +0x28 alpha (0-1), +0x2C width, +0x30 blend (0 / 1),
# +0x38 Flash, +0x3C frames since the command, +0x40 the weight drawn (w x the pulse)
h_shell:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r5
        mr r30, r7
        mr r29, r3
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq os_step
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r11, 0xC(r12)               # commands run
        addi r11, r11, 1
        stw r11, 0xC(r12)
        li r0, 0
        stw r0, 0x10(r12)               # (diag: frames since)
        mr r3, r29
        lwz r4, 0(r30)                  # Target
        bl 0x%(nct)08X
        mr. r28, r3
        beq os_step""" % D + mi_of('r28', 'r27', 'os_step') + """
        lis r26, os_tab@ha              # r26: its entry, or a free one, or the round-robin one
        addi r26, r26, os_tab@l
        li r11, %(n)d
        mr r10, r26
        li r9, 0
osf_loop:
        lwz r0, 0(r10)
        cmplw r0, r28
        beq osf_have
        cmpwi r9, 0
        bne osf_next
        cmpwi r0, 0
        bne osf_next
        mr r9, r10
osf_next:
        addi r10, r10, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne osf_loop
        lfs f1, 0x10(r30)               # not showing: Alpha 0 -> nothing
        lis r12, os_k@ha
        lfs f0, os_k@l(r12)
        fcmpu cr0, f1, f0
        ble os_done
        mr r10, r9
        cmpwi r10, 0
        bne osf_new
        lis r12, os_g@ha                # all in use: the round-robin one
        addi r12, r12, os_g@l
        lwz r11, 0x14(r12)
        addi r0, r11, 1
        cmplwi r0, %(n)d
        blt osf_rr
        li r0, 0
osf_rr:
        stw r0, 0x14(r12)
        mulli r11, r11, %(ent)d
        add r10, r26, r11
osf_new:
        li r0, 0                        # a new entry: from nothing
        stw r0, 8(r10)
        stw r0, 0xC(r10)
osf_have:
        mr r26, r10
        lis r12, os_k@ha
        addi r12, r12, os_k@l
        lfs f0, 0(r12)                  # 0
        lfs f1, 0x10(r30)               # Alpha
        fcmpu cr0, f1, f0
        bgt os_start
        lwz r0, 8(r26)                  # Alpha 0: fade out (or off)
        cmpwi r0, 0
        beq os_free
        lwz r3, 0x20(r30)               # FadeOut
        bl os_rate
        stfs f1, 0x14(r26)
        lis r12, os_k@ha
        lfs f0, os_k@l(r12)
        fcmpu cr0, f1, f0
        beq os_free
        li r0, 3
        stw r0, 8(r26)
        b os_done
os_free:
        li r0, 0
        stw r0, 0(r26)
        stw r0, 8(r26)
        b os_done
os_start:
        stw r28, 0(r26)
        stw r27, 4(r26)
        lfs f2, 0x10(r12)               # 1 / 255
        lfs f5, 4(r12)                  # 1
        lfs f4, 4(r30)
        fmuls f4, f4, f2
        stfs f4, 0x1C(r26)
        lfs f4, 8(r30)
        fmuls f4, f4, f2
        stfs f4, 0x20(r26)
        lfs f4, 0xC(r30)
        fmuls f4, f4, f2
        stfs f4, 0x24(r26)
        fmuls f4, f1, f2                # alpha (0-1)
        fcmpu cr0, f4, f5
        ble osa_hi
        fmr f4, f5
osa_hi:
        stfs f4, 0x28(r26)
        lfs f4, 0x14(r30)               # Width, within +-%(maxw)s
        lfs f5, 0x28(r12)
        fcmpu cr0, f4, f5
        ble osw_hi
        fmr f4, f5
osw_hi:
        fneg f5, f5
        fcmpu cr0, f4, f5
        bge osw_lo
        fmr f4, f5
osw_lo:
        stfs f4, 0x2C(r26)
        lwz r0, 0x28(r30)               # Blend (0 / 1)
        li r9, 0
        cmpwi r0, 0
        beq osb
        li r9, 1
osb:
        stw r9, 0x30(r26)
        lwz r0, 0x18(r30)               # Frames (negative: 0)
        cmpwi r0, 0
        bge os_fr
        li r0, 0
os_fr:
        stw r0, 0x18(r26)
        lwz r0, 0x24(r30)               # Flash (negative: 0)
        cmpwi r0, 0
        bge os_fl
        li r0, 0
os_fl:
        stw r0, 0x38(r26)
        li r0, 0
        stw r0, 0x3C(r26)
        lwz r3, 0x20(r30)               # FadeOut
        bl os_rate
        stfs f1, 0x14(r26)
        lwz r3, 0x1C(r30)               # FadeIn
        bl os_rate
        lis r12, os_k@ha
        addi r12, r12, os_k@l
        lfs f0, 0(r12)
        fcmpu cr0, f1, f0
        beq os_now
        stfs f1, 0x10(r26)
        li r0, 1
        stw r0, 8(r26)
        b os_eff
os_now:
        lfs f1, 4(r12)                  # FadeIn 0: full at once
        stfs f1, 0xC(r26)
        li r0, 2
        stw r0, 8(r26)
os_eff:
        lfs f1, 0xC(r26)                # drawn from this frame: w (the pulse starts full)
        stfs f1, 0x40(r26)
os_done:
        bl os_count
        mr r3, r30
        mr r4, r28
        mr r5, r27
        mr r6, r26
        bl os_dcmd                      # (diag build: S4SC / S4SD; else a blr)
os_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne os_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
os_ret:
        lmw r26, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# os_rate(r3 frames) -> f1 1 / frames (frames > 0), else 0. r0 r12 f0
os_rate:
        lis r12, os_k@ha
        addi r12, r12, os_k@l
        lfs f1, 0(r12)
        cmpwi r3, 0
        blelr
        stwu r1, -0x20(r1)
        xoris r3, r3, 0x8000
        stw r3, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
        lfd f0, 0x18(r12)               # 2^52 + 2^31
        fsub f1, f1, f0
        frsp f1, f1
        lfs f0, 4(r12)
        fdivs f1, f0, f1
        addi r1, r1, 0x20
        blr

# os_count: os_g +0 = entries in use. r0 r9-r12
os_count:
        lis r12, os_tab@ha
        addi r12, r12, os_tab@l
        li r11, %(n)d
        li r9, 0
osc_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq osc_next
        addi r9, r9, 1
osc_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne osc_loop
        lis r12, os_g@ha
        stw r9, os_g@l(r12)
        blr

# --- os_tick: bl from 0x032EFB78 (the effect manager's frame): the earlier tick, then the shells' frame -----------
os_tick:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        bl 0x%(tick_prev)08X
        bl os_frame
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

os_frame:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r11, 4(r12)                 # frames ticked
        addi r11, r11, 1
        stw r11, 4(r12)
        lwz r11, 0x10(r12)              # (diag) since the last command
        addi r11, r11, 1
        stw r11, 0x10(r12)
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq osr_out
        lis r31, os_tab@ha
        addi r31, r31, os_tab@l
        li r30, %(n)d
osr_loop:
        lwz r29, 0(r31)
        cmpwi r29, 0
        beq osr_next""" % D + mi_of('r29', 'r28', 'osr_drop') + """
        lwz r0, 4(r31)                  # the object's model changed: drop it
        cmplw r0, r28
        bne osr_drop
        lwz r12, 0x20(r29)              # a fighter KO'd (StatusModule +0x48 = 0x%(dead)X): drop it""" % D + \
        chk('r12', 'osr_live') + """
        lwz r11, 0(r12)
        lis r10, %(smvt_h)d
        ori r10, r10, %(smvt_l)d
        cmplw r11, r10
        bne osr_live
        lwz r11, 0x48(r12)
        cmpwi r11, %(dead)d
        beq osr_drop
osr_live:
        lis r12, os_k@ha
        addi r12, r12, os_k@l
        lfs f0, 0(r12)                  # 0
        lfs f2, 4(r12)                  # 1
        lfs f1, 0xC(r31)                # w
        lwz r0, 8(r31)
        cmpwi r0, 1
        bne osr_held
        lfs f3, 0x10(r31)               # growing in
        fadds f1, f1, f3
        fcmpu cr0, f1, f2
        blt osr_w
        fmr f1, f2
        li r0, 2
        stw r0, 8(r31)
        b osr_w
osr_held:
        cmpwi r0, 2
        bne osr_out3
        lwz r11, 0x18(r31)              # Frames left (0: no count)
        cmpwi r11, 0
        beq osr_w
        addi r11, r11, -1
        cmpwi r11, 0
        stw r11, 0x18(r31)
        bne osr_w
        lfs f3, 0x14(r31)               # Frames over: shrink away, or off at once
        fcmpu cr0, f3, f0
        beq osr_drop
        li r0, 3
        stw r0, 8(r31)
        b osr_w
osr_out3:
        cmpwi r0, 3
        bne osr_drop
        lfs f3, 0x14(r31)
        fsubs f1, f1, f3
        fcmpu cr0, f1, f0
        ble osr_drop
osr_w:
        stfs f1, 0xC(r31)
        lwz r11, 0x3C(r31)              # the pulse
        addi r11, r11, 1
        stw r11, 0x3C(r31)
        lwz r10, 0x38(r31)
        cmpwi r10, 0
        ble osr_eff
        divwu r9, r11, r10              # m = t mod Flash; p = m / Flash; tri = |2p - 1|; f = tri^2 (3 - 2 tri)
        mullw r9, r9, r10
        subf r9, r9, r11
        stw r9, 0x14(r1)
        stw r10, 0x1C(r1)
        lis r0, 0x4330
        stw r0, 0x10(r1)
        stw r0, 0x18(r1)
        lfd f4, 0x10(r1)
        lfd f5, 0x18(r1)
        lfd f6, 0x20(r12)               # 2^52
        fsub f4, f4, f6
        fsub f5, f5, f6
        frsp f4, f4
        frsp f5, f5
        fdivs f4, f4, f5                # p
        lfs f5, 8(r12)                  # 2
        fmuls f4, f4, f5
        fsubs f4, f4, f2
        fabs f4, f4                     # tri
        lfs f6, 0xC(r12)                # 3
        fnmsubs f6, f5, f4, f6          # 3 - 2 tri
        fmuls f6, f6, f4
        fmuls f6, f6, f4
        fmuls f1, f1, f6
osr_eff:
        stfs f1, 0x40(r31)
        mr r3, r31
        li r4, %(n)d
        subf r4, r30, r4
        bl os_dtick                     # (diag: S4ST)
        b osr_next
osr_drop:
        li r0, 0
        stw r0, 0(r31)
        stw r0, 8(r31)
osr_next:
        addi r31, r31, %(ent)d
        addi r30, r30, -1
        cmpwi r30, 0
        bne osr_loop
        bl os_count
osr_out:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- os_fb: outline_cave.py's ol_fbgo `bl ol_apply` (r4 the instance, r5 its locked FB1, before the unlock):
#     ol_apply, then this instance's shell into FB1 vec4 12-13 ------------------------------------------------------
os_fb:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r4, 0x10(r1)
        stw r5, 0x14(r1)
        bl 0x%(ol_apply)08X
        lwz r4, 0x10(r1)
        lwz r5, 0x14(r1)
        bl os_apply
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# os_apply(r4 instance, r5 FB1): +0xC0 (r, g, b, alpha), +0xD0 (width x weight, MAGIC, blend, weight)
os_apply:
        lis r12, os_g@ha
        lwz r0, os_g@l(r12)
        cmpwi r0, 0
        beqlr""" % D + chk('r5', 'osa_no') + """
        lis r12, os_tab@ha
        addi r12, r12, os_tab@l
        li r11, %(n)d
osa_find:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq osa_next
        lwz r0, 4(r12)
        cmplw r0, r4
        bne osa_next
        lwz r0, 8(r12)
        cmpwi r0, 0
        bne osa_have
osa_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne osa_find
osa_no:
        blr
osa_have:
        lis r11, os_k@ha
        lfs f0, os_k@l(r11)             # 0
        lfs f1, 0x40(r12)               # weight
        fcmpu cr0, f1, f0
        blelr
        lwz r0, 0x1C(r12)
        stw r0, %(col)d(r5)
        lwz r0, 0x20(r12)
        stw r0, %(col4)d(r5)
        lwz r0, 0x24(r12)
        stw r0, %(col8)d(r5)
        lwz r0, 0x28(r12)
        stw r0, %(colc)d(r5)
        lfs f2, 0x2C(r12)               # width x weight
        fmuls f2, f2, f1
        stfs f2, %(sh)d(r5)
        lis r0, %(magic_h)d
        ori r0, r0, %(magic_l)d
        stw r0, %(sh4)d(r5)
        lwz r0, 0x30(r12)
        stw r0, %(sh8)d(r5)
        stfs f1, %(shc)d(r5)
        mr r3, r12
        b os_dfb                        # (diag: S4SF; else a blr)

# --- os_drawI / os_drawN: CommandDrawModel's draw calls (0x037174D8 bl 0x%(fni_h)04X%(fni_l)04X, 0x037174E8
#     bl 0x%(fnn_h)04X%(fnn_l)04X; r3 the device context, r4-r9 the draw): the game's draw, then the shell when this
#     draw's FB1 carries one ---------------------------------------------------------------------------------------
os_drawI:
        lis r12, %(fni_h)d
        ori r12, r12, %(fni_l)d
        b os_draw
os_drawN:
        lis r12, %(fnn_h)d
        ori r12, r12, %(fnn_l)d
os_draw:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r30, 0x58(r1)
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        stw r5, 0x18(r1)
        stw r6, 0x1C(r1)
        stw r7, 0x20(r1)
        stw r8, 0x24(r1)
        stw r9, 0x28(r1)
        stw r12, 0x2C(r1)
        mtctr r12
        bctrl                           # the game's draw
        lwz r31, 0x10(r1)%(mark)s
        mr r3, r31
        bl os_chk
        mr. r30, r3
        beq osd_out
        bl os_resolve                   # the imports' run-time addresses (once)
        cmpwi r3, 0
        beq osd_out%(st1)s%(setprog)s%(st2)s
        lwz r0, %(c_rsreg)d(r31)         # the rasterizer's: front faces culled (back faces, if the game culls front)
        clrlwi r11, r0, 30
        rlwinm r0, r0, 0, 0, 29
        cmpwi r11, %(cf)d
        li r11, %(cf)d
        bne osd_cull
        li r11, %(cb)d
osd_cull:
        or r0, r0, r11
        stw r0, 0x30(r1)
        addi r3, r1, 0x30
%(x_SetPolygonControlReg)s
        lwz r0, %(c_dsreg)d(r31)         # the depth's: test and write on (its compare kept), stencil off
        li r11, %(dsoff)d
        andc r0, r0, r11
        ori r0, r0, %(dson)d
        stw r0, 0x34(r1)
        addi r3, r1, 0x34
%(x_SetDepthStencilControlReg)s
        li r0, 0                        # target 0's blend: the colour x alpha over (Blend 0) / onto (1) it
        stw r0, 0x38(r1)
        lis r0, %(bl0_h)d
        ori r0, r0, %(bl0_l)d
        lwz r11, %(sh8)d(r30)
        cmpwi r11, 0
        beq osd_bl
        lis r0, %(bl0_h)d
        ori r0, r0, %(bl1_l)d
osd_bl:
        stw r0, 0x3C(r1)
        addi r3, r1, 0x38
%(x_SetBlendControlReg)s
        lwz r3, %(cc4)d(r31)             # blending on target 0 (the game's logic op, multi-write, colour buffer)
        lbz r4, %(cc8)d(r31)
        ori r4, r4, 1
        lwz r5, %(ccc)d(r31)
        lwz r6, %(cc10)d(r31)
%(x_SetColorControl)s
        li r0, 0                        # no alpha test
        stw r0, 0x40(r1)
        stw r0, 0x44(r1)
        addi r3, r1, 0x40
%(x_SetAlphaTestReg)s%(st3)s
        lwz r3, 0x10(r1)                # the same draw again
        lwz r4, 0x14(r1)
        lwz r5, 0x18(r1)
        lwz r6, 0x1C(r1)
        lwz r7, 0x20(r1)
        lwz r8, 0x24(r1)
        lwz r9, 0x28(r1)
        lwz r12, 0x2C(r1)
        mtctr r12%(redraw)s%(st4)s
        lwz r3, %(c_vs)d(r31)            # everything back as the device's caches have it
%(x_SetVertexShader)s
        lwz r3, %(c_ps)d(r31)
%(x_SetPixelShader)s
        addi r3, r31, %(c_rsreg)d
%(x_SetPolygonControlReg)s
        addi r3, r31, %(c_dsreg)d
%(x_SetDepthStencilControlReg)s
        addi r3, r31, %(c_blend0)d
%(x_SetBlendControlReg)s
        lwz r3, %(cc4)d(r31)
        lbz r4, %(cc8)d(r31)
        lwz r5, %(ccc)d(r31)
        lwz r6, %(cc10)d(r31)
%(x_SetColorControl)s
        addi r3, r31, %(c_atest)d
%(x_SetAlphaTestReg)s%(st5)s
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r11, 0x18(r12)              # shells drawn
        addi r11, r11, 1
        stw r11, 0x18(r12)
        mr r3, r31
        mr r4, r30
        addi r5, r1, 0x30
        bl os_ddraw                     # (diag: S4SR)
osd_out:
        lmw r30, 0x58(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr

# os_chk(r3 the device context) -> r3 the FB1 bound to this draw when it carries a shell and the draw is a material's
# (pixel program blocks 4 (MC) and 7 (FB1, 0x2A0 bytes); the vertex stage's FB1 the same; no geometry shader; the
# caches filled), else 0. r0 r3-r12 (diag: os_dref)
os_chk:
        lis r12, os_g@ha
        lwz r0, os_g@l(r12)
        cmpwi r0, 0
        beq oc_no
        addi r12, r12, os_g@l
        lwz r11, 0x20(r12)              # draws checked while a shell is in use
        addi r11, r11, 1
        stw r11, 0x20(r12)""" % D + chk('r3', 'oc_no') + """
        lwz r12, %(pcb7)d(r3)            # the pixel stage's FB1""" % D + chk('r12', 'oc_no') + """
        lwz r0, %(pcb7s)d(r3)
        cmplwi r0, 0x2A0
        blt oc_no
        lis r11, %(magic_h)d             # the mark: as written, or byte-swapped (NU::ConstantBufferWiiU's unlock,
        ori r11, r11, %(magic_l)d        # 0x037291BC, swaps the block in place for the GPU before the draw)
        lwz r0, %(sh4)d(r12)
        cmplw r0, r11
        beq oc_mark
        lis r11, %(smagic_h)d
        ori r11, r11, %(smagic_l)d
        cmplw r0, r11
        bne oc_no
oc_mark:
        lis r11, os_g@ha                # marked draws seen (diag: S4SF)
        addi r11, r11, os_g@l
        lwz r9, 0x24(r11)
        addi r9, r9, 1
        stw r9, 0x24(r11)
        lwz r0, %(vcb7)d(r3)             # the vertex stage's the same
        cmplw r0, r12
        bne oc_no
        lwz r0, %(c_gs)d(r3)
        cmpwi r0, 0
        bne oc_no
        lwz r9, %(c_vs)d(r3)""" % D + chk('r9', 'oc_no') + """
        lwz r9, %(c_rs)d(r3)""" % D + chk('r9', 'oc_no') + """
        lwz r9, %(c_ds)d(r3)""" % D + chk('r9', 'oc_no') + """
        lwz r9, %(c_blend)d(r3)""" % D + chk('r9', 'oc_no') + """
        lwz r10, %(c_ps)d(r3)            # the pixel program's uniform blocks: 4 (MC) and 7 (FB1)""" % D + \
        chk('r10', 'oc_no') + """
        lwz r11, 0xB0(r10)
        lwz r9, 0xB4(r10)
        srwi r0, r9, 20                 # (an offset from the struct as in the .gsh file: 0xD06xxxxx)
        cmplwi r0, 0xD06
        bne oc_abs
        clrlwi r9, r9, 12
        add r9, r9, r10
oc_abs:""" + chk('r9', 'oc_ref') + """
        cmplwi r11, 16
        bgt oc_ref
        li r8, 0
oc_loop:
        cmpwi r11, 0
        beq oc_end
        lwz r0, 4(r9)
        cmpwi r0, 7
        bne oc_4
        lwz r0, 8(r9)
        cmplwi r0, 0x2A0
        bne oc_next
        ori r8, r8, 1
        b oc_next
oc_4:
        cmpwi r0, 4
        bne oc_next
        ori r8, r8, 2
oc_next:
        addi r9, r9, 12
        addi r11, r11, -1
        b oc_loop
oc_end:
        cmpwi r8, 3
        bne oc_ref
        lis r11, os_k@ha
        lfs f0, os_k@l(r11)
        lfs f1, %(sh)d(r12)              # width 0: nothing to draw
        fcmpu cr0, f1, f0
        beq oc_no
        mr r3, r12
        blr
oc_ref:
        mr r4, r10
        mr r5, r12
        b os_dref                       # (diag: S4SX; else r3 0)
oc_no:
        li r3, 0
        blr

# --- os_clear: the clear-all chain (training reset, restart, match start / end; a leaf: r3 / r10 / LR kept): every
#     shell off, then on ----------------------------------------------------------------------------------------
os_clear:
        lis r12, os_tab@ha
        addi r12, r12, os_tab@l
        li r11, %(n)d
        li r0, 0
osx_loop:
        stw r0, 0(r12)
        stw r0, 8(r12)
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne osx_loop
        lis r12, os_g@ha
        stw r0, os_g@l(r12)
        b 0x%(clear_to)08X
""" % D
    if diag:
        out += _diag_src()
    else:
        out += """
os_dcmd:
os_dtick:
os_dfb:
os_ddraw:
os_dstep:
os_dmark:
        blr
os_dref:
        li r3, 0
        blr
"""
    out += """
# --- os_resolve() -> r3 1 when os_fn holds every import's run-time address, else 0: the first call reads the game's
#     own call at each site in os_site as Cemu left it (rpl.cpp: a relative `bl`, or an absolute `bla` to a trampoline
#     when out of reach) and stores its target; a site that isn't a `bl` / `bla` leaves os_fn unset (no shell drawn).
#     A leaf: r0, r3, r7-r12 ----------------------------------------------------------------------------------------
os_resolve:
        lis r12, os_fnok@ha
        lwz r3, os_fnok@l(r12)
        cmpwi r3, 0
        bnelr
        lis r11, os_site@ha
        addi r11, r11, os_site@l
        lis r12, os_fn@ha
        addi r12, r12, os_fn@l
        li r10, %(n)d
ors_loop:
        lwz r9, 0(r11)                  # the site
        lwz r8, 0(r9)                   # its instruction now
        srwi r0, r8, 26
        cmpwi r0, 18
        bne ors_fail
        andi. r0, r8, 1                 # LK
        beq ors_fail
        rlwinm r7, r8, 0, 6, 29         # LI
        rlwinm. r0, r7, 0, 6, 6         # (bit 0x02000000: the sign)
        beq ors_pos
        addis r7, r7, -0x0400           # (sign)
ors_pos:
        andi. r0, r8, 2                 # AA: absolute
        bne ors_abs
        add r7, r7, r9
ors_abs:
        stw r7, 0(r12)
        addi r11, r11, 4
        addi r12, r12, 4
        addi r10, r10, -1
        cmpwi r10, 0
        bne ors_loop
        li r3, 1
        lis r12, os_fnok@ha
        stw r3, os_fnok@l(r12)
        blr
ors_fail:
        li r3, 0
        blr
os_site:
""" % dict(n=len(IMPORTS)) + ''.join('        .word 0x%08X                 # %s\n' % (site, nm) for nm, site, _t in IMPORTS) + \
        'os_fn:\n' + '        .word 0\n' * len(IMPORTS) + 'os_fnok:\n        .word 0\n'
    out += ("        .word 0\n" if pad else "") + """
os_k:                                   # +0 0, +4 1, +8 2, +0xC 3, +0x10 1/255, +0x18 2^52 + 2^31, +0x20 2^52,
        .float 0                        # +0x28 the widest width
        .float 1
        .float 2
        .float 3
        .float 0.00392156862745098
        .word 0
        .word 0x43300000
        .word 0x80000000
        .word 0x43300000
        .word 0
        .float %r
        .word 0
os_g:                                   # +0 entries in use, +4 frames ticked, +8 FB1 writes, +0xC commands,
        .word 0                         # +0x10 frames since the last command (diag), +0x14 round robin, +0x18 shells
        .word 0                         # drawn, +0x1C marked FB1s refused (diag), +0x20 draws checked while a shell is
        .word 0                         # in use, +0x24 marked draws seen (diag), +0x28 shells stepped (diag S4SP),
        .word 0                         # +0x2C marks logged (diag S4SM)
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
os_vs:                                  # GX2VertexShader: special.nsh's registers, this program, uniform-block mode
""" % MAX_WIDTH + ''.join('        .word 0x%08X\n' % x for x in VS_REGS) + """
        .word %d
        .word 0x%08X
        .word 1
""" % (len(VS_PROGRAM), VS_PROG) + '        .word 0\n' * (0x134 // 4 - 52 - 3) + """
os_ps:                                  # GX2PixelShader
""" + ''.join('        .word 0x%08X\n' % x for x in PS_REGS) + """
        .word %d
        .word 0x%08X
        .word 1
""" % (len(PS_PROGRAM), PS_PROG) + '        .word 0\n' * (0xE8 // 4 - 41 - 3) + """
os_tab:
""" + '        .word 0\n' * (N_ENT * ENT // 4) + (_diag_data() if diag else '')
    return out


def _diag_src():
    import diag_godfist_cave as G
    rep = """
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        .word 0x%08X
        bctrl""" % (G.OSREPORT_VENEER >> 16, G.OSREPORT_VENEER & 0xFFFF, G.CRCLR_CR1EQ)
    gate = """
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r11, 0x10(r12)              # the first %(e)d frames after a command, then every %(e)dth
        cmpwi r11, %(e)d
        blt %(lab)s_log
        li r9, %(e)d
        divwu r8, r11, r9
        mullw r8, r8, r9
        cmpw r8, r11
        bne %(lab)s_out
%(lab)s_log:"""
    head = """
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x28(r1)"""
    tail = """
        lmw r27, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
"""
    return """
# --- diag: S4SC / S4SD at every command (r3 parameters, r4 target accessor, r5 instance, r6 entry) -------------------
os_dcmd:""" + head + """
        mr r31, r3
        mr r30, r4
        mr r29, r5
        mr r28, r6
        lis r3, s_sc@ha
        addi r3, r3, s_sc@l
        lwz r4, 0(r31)
        mr r5, r30
        mr r6, r29
        lwz r7, 4(r31)
        lwz r8, 8(r31)
        lwz r9, 0xC(r31)
        lwz r10, 0x10(r31)""" + rep + """
        lis r3, s_sd@ha
        addi r3, r3, s_sd@l
        lwz r4, 0x14(r31)
        lwz r5, 0x18(r31)
        lwz r6, 0x1C(r31)
        lwz r7, 0x20(r31)
        lwz r8, 0x24(r31)
        lwz r9, 0x28(r31)
        lis r10, os_tab@ha
        addi r10, r10, os_tab@l
        subf r10, r10, r28
        li r0, %(ent)d
        divwu r10, r10, r0""" % dict(ent=ENT) + rep + tail + """
# --- diag: S4ST per shell frame (r3 entry, r4 its number) -------------------------------------------------------------
os_dtick:""" + head + """
        mr r31, r3
        mr r30, r4""" + gate % dict(e=DIAG_EVERY, lab='odt') + """
        lis r3, s_st@ha
        addi r3, r3, s_st@l
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r4, 4(r12)
        mr r5, r30
        lwz r6, 8(r31)
        lwz r7, 0x40(r31)
        lwz r8, 0x18(r12)
        lwz r9, 0x20(r12)
        lwz r10, 0x1C(r12)""" + rep + """
odt_out:""" + tail + """
# --- diag: S4SF at an FB1 write (r3 entry, r4 instance, r5 FB1) ------------------------------------------------------
os_dfb:""" + head + """
        mr r31, r3
        mr r30, r4
        mr r29, r5
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r11, 8(r12)                 # FB1 writes
        addi r11, r11, 1
        stw r11, 8(r12)""" + gate % dict(e=DIAG_EVERY, lab='odf') + """
        lis r3, s_sf@ha
        addi r3, r3, s_sf@l
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r4, 8(r12)
        mr r5, r30
        mr r6, r29
        lwz r7, %(sh)d(r29)
        lwz r8, %(colc)d(r29)
        lwz r9, %(sh8)d(r29)
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r10, 0x24(r12)""" % dict(sh=FB_SHELL, colc=FB_COL + 12, sh8=FB_SHELL + 8) + rep + """
odf_out:""" + tail + """
# --- diag: S4SP at each step of the first DIAG_STEPS shells drawn (r3 the step: 1 the mark taken, 2 the programs
#     set, 3 the states set, 4 the draw made, 5 everything back; r4 the device context): the core, the return
#     addresses up the stack (who drew: CommandDrawModel, its caller, ...) ----------------------------------------
os_dstep:""" + head + """
        mr r31, r3
        mr r30, r4
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        cmpwi r31, 1
        bne ods_chk
        lwz r11, 0x28(r12)
        addi r11, r11, 1
        stw r11, 0x28(r12)
ods_chk:
        lwz r11, 0x28(r12)
        cmpwi r11, %d
        bgt ods_out""" % DIAG_STEPS + call('OSGetCoreId') + """
        mr r6, r3
        li r7, 0
        li r8, 0
        li r9, 0
        li r10, 0
        lwz r29, 0(r1)                  # os_draw's frame
        lwz r29, 0(r29)                 # its caller's (CommandDrawModel)""" + \
        OL.chk('r29', 'ods_pr') + """
        lwz r7, 4(r29)                  # the return into CommandDrawModel
        lwz r29, 0(r29)""" + OL.chk('r29', 'ods_pr') + """
        lwz r8, 4(r29)                  # into its caller
        lwz r29, 0(r29)""" + OL.chk('r29', 'ods_pr') + """
        lwz r9, 4(r29)
        lwz r29, 0(r29)""" + OL.chk('r29', 'ods_pr') + """
        lwz r10, 4(r29)
ods_pr:
        lis r3, s_sp@ha
        addi r3, r3, s_sp@l
        mr r4, r31
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r5, 0x28(r12)""" + rep + """
        bl os_dsleep
ods_out:""" + tail + """
# --- diag: S4SM the moment a draw's pixel-stage FB1 carries the mark (either byte order), before os_chk's other tests
#     (the first DIAG_MARKS; r3 the device context): the context, FB1, the vertex stage's FB1, the geometry shader,
#     the pixel shader, its block count and table; then a pause (os_dsleep) so Cemu's log thread writes the line out
#     before anything after it can crash -----------------------------------------------------------------------------
os_dmark:""" + head + """
        mr r31, r3
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq odm_out
        lwz r0, 0x2C(r12)
        cmpwi r0, %(nm)d
        bge odm_out""" % dict(nm=DIAG_MARKS) + OL.chk('r31', 'odm_out') + """
        lwz r30, %(pcb7)d(r31)""" % dict(pcb7=CTX['pcb'] + 8 * 7) + OL.chk('r30', 'odm_out') + """
        lwz r0, %(sh4)d(r30)
        lis r11, %(mh)d
        ori r11, r11, %(ml)d
        cmplw r0, r11
        beq odm_hit
        lis r11, %(smh)d
        ori r11, r11, %(sml)d
        cmplw r0, r11
        bne odm_out
odm_hit:
        lwz r11, 0x2C(r12)
        addi r11, r11, 1
        stw r11, 0x2C(r12)
        lis r3, s_sm@ha
        addi r3, r3, s_sm@l
        mr r4, r31
        mr r5, r30
        lwz r6, %(vcb7)d(r31)
        lwz r7, %(gs)d(r31)
        lwz r8, %(ps)d(r31)
        li r9, -1
        li r10, -1""" % dict(sh4=FB_SHELL + 4, mh=MAGIC >> 16, ml=MAGIC & 0xFFFF, smh=SMAGIC >> 16,
                             sml=SMAGIC & 0xFFFF, vcb7=CTX['vcb'] + 8 * 7, gs=CTX['gs'], ps=CTX['ps']) + \
        OL.chk('r8', 'odm_pr') + """
        lwz r9, 0xB0(r8)
        lwz r10, 0xB4(r8)
odm_pr:""" + rep + """
        bl os_dsleep
odm_out:""" + tail + """
# --- diag: a pause of DIAG_PAUSE ticks (OSSleepTicks): Cemu's log is written by its own thread from a queue, so the
#     last lines before a crash are lost unless the game waits a moment after them ----------------------------------
os_dsleep:
        stwu r1, -0x10(r1)
        mflr r0
        stw r0, 0x14(r1)
        bl os_resolve
        cmpwi r3, 0
        beq ods_slept
        li r3, 0
        lis r4, %(ph)d
        ori r4, r4, %(pl)d""" % dict(ph=DIAG_PAUSE >> 16, pl=DIAG_PAUSE & 0xFFFF) + call('OSSleepTicks') + """
ods_slept:
        lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr
""" + """
# --- diag: S4SR at a shell drawn (r3 the device context, r4 FB1, r5 the states set: rasterizer, depth) ---------------
os_ddraw:""" + head + """
        mr r31, r3
        mr r30, r4
        mr r29, r5""" + gate % dict(e=DIAG_EVERY, lab='odr') + """
        lis r3, s_sr@ha
        addi r3, r3, s_sr@l
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r4, 0x18(r12)
        mr r5, r31
        lwz r6, %(vs)d(r31)
        lwz r7, %(ps)d(r31)
        mr r8, r30
        lwz r9, %(sh)d(r30)
        lwz r10, 0(r29)""" % dict(vs=CTX['vs'], ps=CTX['ps'], sh=FB_SHELL) + rep + """
odr_out:""" + tail + """
# --- diag: S4SX at a marked FB1 refused (r3 the device context, r4 its pixel shader, r5 FB1) -> r3 0 ------------------
os_dref:""" + head + """
        mr r31, r3
        mr r30, r4
        mr r29, r5
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r11, 0x1C(r12)
        addi r11, r11, 1
        stw r11, 0x1C(r12)""" + gate % dict(e=DIAG_EVERY, lab='odx') + """
        lis r3, s_sx@ha
        addi r3, r3, s_sx@l
        lis r12, os_g@ha
        addi r12, r12, os_g@l
        lwz r4, 0x1C(r12)
        mr r5, r31
        mr r6, r30
        li r7, -1
        li r8, -1""" + OL.chk('r30', 'odx_np') + """
        lwz r7, 0xB0(r30)
        lwz r8, 0xB4(r30)
odx_np:
        mr r9, r29""" + rep + """
odx_out:
        li r3, 0""" + tail.replace('        blr\n', '        li r3, 0\n        blr\n')


def _diag_data():
    out = ''
    for lab, fmt in DIAG_FMTS:
        out += '%s:\n' % lab + OL._words(fmt)
    return out


def build(orig, diag=False, variant='full'):
    s = find(orig)
    hand, pad = 0, False
    for _p in range(3):
        a = Asm(CAVE)
        a.asm(src(s, hand, diag, pad, variant))
        hand = a.addr('h_shell')
        if a.addr('os_k') % 8:
            pad = not pad
    words = a.words()
    end = CAVE + 4 * len(words)
    assert end <= VS_PROG, 'cave too big: 0x%08X (the programs at 0x%08X)' % (end, VS_PROG)
    assert a.addr('os_k') % 8 == 0, 'os_k not 8-aligned (its doubles)'
    assert VS_PROG % 0x100 == 0 and PS_PROG % 0x100 == 0 and VS_PROG + len(VS_PROGRAM) <= PS_PROG and \
        PS_PROG + len(PS_PROGRAM) <= LIMIT
    for x in range(CAVE, LIMIT, 4):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for base, prog in ((VS_PROG, VS_PROGRAM), (PS_PROG, PS_PROGRAM)):
        for i in range(0, len(prog), 4):
            out[base + i] = struct.unpack_from('>I', prog, i)[0]
    out.update(OL.table_words(s, a, 'os'))
    out[DRAW_I] = LT.branch(DRAW_I, a.addr('os_drawI')) | 1
    out[DRAW_N] = LT.branch(DRAW_N, a.addr('os_drawN')) | 1
    out[s['fb_at']] = LT.branch(s['fb_at'], a.addr('os_fb')) | 1
    out[OL.TICK_AT] = LT.branch(OL.TICK_AT, a.addr('os_tick')) | 1
    out[s['clear_at']] = LT.branch(s['clear_at'], a.addr('os_clear'))
    return out, a.labels, s


def rpx_reader(path):
    return OL.rpx_reader(path, CAVE, LIMIT)


def labels(path):
    OL.labels(path, NEW_CMDS)


def present(img_w):
    return OL.present(img_w, CMD_CRC, CAVE)


def draws(img_w):
    """an executable whose shell draws: v3's FB1 mark taken byte-swapped (lis r11 / ori r11 of SMAGIC in os_chk;
    exe_v46z_outline2's never draws) and v6's imports resolved at run time (os_site; exe_v46z_outline3's crashes at
    the first shell: its GX2 calls went to the file's bl targets). exe_v46z_outline4 or later"""
    hi, lo = 0x3D600000 | (SMAGIC >> 16), 0x616B0000 | (SMAGIC & 0xFFFF)
    swapped = resolved = False
    for a in range(CAVE, LIMIT - 4, 4):
        if img_w(a) == hi and img_w(a + 4) == lo:
            swapped = True
        if img_w(a) == IMPORTS[0][1] and img_w(a + 4) == IMPORTS[1][1]:
            resolved = True               # v6's os_site table (exe_v46z_outline4): imports resolved at run time
    return swapped and resolved


def apply_ref(entry, weight):
    """the FB1 words os_apply writes (Python reference): entry {'rgb': (0-255) x 3, 'alpha': 0-255, 'width',
    'blend'} -> {'col': [r, g, b, a] (0-1), 'width', 'magic', 'blend', 'weight'}"""
    w = max(-MAX_WIDTH, min(MAX_WIDTH, entry['width']))
    return {'col': [c / 255.0 for c in entry['rgb']] + [min(entry['alpha'] / 255.0, 1.0)], 'width': w * weight,
            'magic': MAGIC, 'blend': 1 if entry['blend'] else 0, 'weight': weight}


def shell_ref(pos, nor, L, P, compress, width):
    """the vertex program's clip position (Python reference; numpy arrays: pos / nor [n, 3], L / P 4 x 4 rows)"""
    import numpy as np
    world = np.concatenate([pos, np.ones((len(pos), 1))], 1) @ L
    world[:, 2] = compress[0] * (world[:, 2] - compress[1]) + compress[1]
    nw = nor @ L[:3, :3]
    nwn = nw / np.linalg.norm(nw, axis=1, keepdims=True)
    world[:, :3] += nwn * max(-width, 0.0)
    clip = world @ P
    nc = nw @ P[:3, :2]
    d = nc / np.sqrt((640 * nc[:, 0]) ** 2 + (360 * nc[:, 1]) ** 2)[:, None]
    clip[:, :2] += d * max(width, 0.0) * clip[:, 3:4]
    return clip


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (exe_v46z_outline: mesh_vis_cave.py\'s, or later)')
    p.add_argument('--labels', help='update this param_labels.json with Outline_Shell')
    p.add_argument('--diag', action='store_true', help='TEST ONLY: the OSReport build (S4SC / S4SD / S4ST / S4SF / '
                   'S4SR / S4SX lines, docs/native-notes.md "Outline shell")')
    p.add_argument('--variant', default='full', choices=VARIANTS, help='TEST ONLY (with --diag): noprog draws the shell '
                   'with the game\'s own programs, nodraw sets the shell\'s programs and states but skips its draw')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    if not args.rpx:
        p.error('--rpx or --labels')
    if args.variant != 'full' and not args.diag:
        p.error('--variant is TEST ONLY: with --diag')
    words, lab, _s = build(rpx_reader(args.rpx), args.diag, args.variant)
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(words.items())]))
    sys.stderr.write('outline shell: %d words, Outline_Shell index %d (0x%08X), h_shell 0x%08X, os_draw 0x%08X, '
                     'code end 0x%08X\n' % (len(words), OS_INDEX, CMD_CRC, lab['h_shell'], lab['os_draw'],
                                            max(a for a in words if a < VS_PROG) + 4))


if __name__ == '__main__':
    main()
