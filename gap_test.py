#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""initialize and run the testfarm of GAP2 code for many-body perturbation calculation
"""
from __future__ import print_function, with_statement
import glob
import os
from shutil import rmtree
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from utils import create_logger, TestCase, workspace

__project__ = "gap2-testcases"
__version__ = "0.0.1"

def gap_parser():
    """parser of gap test"""
    p = ArgumentParser(description=__doc__,
                       formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("--init", action="store_true",
                   help="initialize WIEN2k and GAP inputs")
    p.add_argument("--dry", action="store_true",
                   help="dry run for test use")
    p.add_argument("--gap", dest="gap_version", type=str, default="2c",
                   help="gap version")
    p.add_argument("--debug", dest="debug", action="store_true",
                   help="debug mode")
    p.add_argument("--force", dest="force_restart", action="store_true",
                   help="forcing delete the workspace and restart")
    return p.parse_args()

def gap_test():
    """run initializtion"""
    args = gap_parser()
    logger = create_logger(debug=args.debug)
    if os.path.isdir(workspace):
        if args.force_restart:
            logger.info("Forced restart, cleaning workspace")
            rmtree(workspace)
        else:
            raise IOError("workspace exists. Remove it before continue")
    testcases = list(glob.glob("init/*.json"))
    for x in testcases:
        logger.info("Found test: %s", x)
        tc = TestCase(x, logger, init=args.init)
        tc.run(args.gap_version, dry=args.dry)

if __name__ == "__main__":
    gap_test()

