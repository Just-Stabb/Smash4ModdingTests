#!/usr/bin/env python3
"""Run one of the research repository's executable tests on a clone-engine build, with the generators pointed at the
Sm4shCloneTool's code space (the tests import the generators and read their layout).

  python3 tools/sm4shclonetool/tests/repo_test.py TEST PATCHED.rpx ORIGINAL.rpx [ARGS...]

TEST: kind_expand_test, weapon_expand_test, base_effects_test, base_customs_test, stage_slot_test,
import_call_check (ORIGINAL first for that one). The kinds JSON the tests take is written from PATCHED's own marker
(the registry), so KINDS is not given. Repository-only (the tests are not in the standalone package).
"""
import json
import os
import runpy
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import exe as E  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402

TOOLS = os.path.dirname(os.path.dirname(HERE))


def main():
    test, patched, orig = sys.argv[1:4]
    rest = sys.argv[4:]
    base, rec = E.find_marker(Rpx(patched))
    E.configure(base)
    reg = rec['registry']
    spec = os.path.join(tempfile.mkdtemp(prefix='ce_t_'), 'kinds.json')
    json.dump(E.kind_spec(reg), open(spec, 'w'))
    if test == 'import_call_check':
        sys.argv = [test + '.py', orig, patched] + rest
    elif test == 'stage_slot_test':
        sys.argv = [test + '.py', patched, orig] + ['%s:0x%X' % (s['name'], s['cosmetic']) for s in reg['stages']]
    elif test == 'base_customs_test':
        sys.argv = [test + '.py', patched, orig] + rest
    else:
        sys.argv = [test + '.py', patched, orig, spec] + rest
    runpy.run_path(os.path.join(TOOLS, test + '.py'), run_name='__main__')


if __name__ == '__main__':
    main()
