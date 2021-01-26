#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""initialize and run the testfarm of GAP2 code for many-body perturbation calculation
"""
from __future__ import print_function

from backend.utils import create_logger, gap_parser
from backend.testcase import TestCase, find_tests

__project__ = "gap2-testcases"
__version__ = "0.0.3"

def gap_test():
    """run initializtion"""
    args = gap_parser(__doc__).parse_args()
    logger = create_logger(args.logname, debug=args.debug, stream=False)
    init_mode = False
    testcases = find_tests(include=args.include,
                           exclude=args.exclude)
    if args.preview:
        print("Preview mode:")
        for i, tc in enumerate(testcases):
            print("{:3d}: {:s}".format(i+1, tc))
        return
    if args.init:
        init_mode = "w"
    if args.init_gap:
        init_mode = "g"

    for x in testcases:
        logger.info("Found test: %s", x)
        tc = TestCase(x, logger, workspace=args.workspace,
                      init_mode=init_mode,
                      force_restart=args.force_restart)
        tc.init(args.gap_version, dry=args.dry)
        tc.run(args.gap_version, args.gap_suffix, nprocs=args.nprocs,
               dry=args.dry)


if __name__ == "__main__":
    gap_test()

