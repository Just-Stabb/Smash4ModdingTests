#!/usr/bin/env python3
"""All the toolkit's tests: python3 tools/smashrun_trace/tests/run_all.py [DUMP_DIR]

DUMP_DIR (or $S3DS_DUMP): static.crs + cro/enemy_fs.cro + cro/main_field.cro of the 3DS dump (the CRO and fake
Azahar tests are skipped without it). Needs unicorn and capstone for the fake Azahar / CRO tests (the toolkit itself
needs neither).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('S3DS_DUMP', '')
    bad = 0
    for t, needs_dump in (('test_rsp.py', False), ('test_analyse.py', False), ('test_cro.py', True),
                          ('test_fake_azahar.py', True)):
        cmd = [sys.executable, os.path.join(HERE, t)] + ([dump] if needs_dump and dump else [])
        print('==', t)
        r = subprocess.run(cmd)
        bad += r.returncode != 0
    print('ALL PASSED' if not bad else '%d test file(s) failed' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
