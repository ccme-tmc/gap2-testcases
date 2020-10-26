#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""initialize the testcase"""
from __future__ import print_function, with_statement
import glob
import os
import shutil
import json
import logging
import subprocess as sp

from utils import create_logger, gap_parser

rootdir = "workspace"

def init_w2k_scf(rkmax, ecut, xc, spin_polarized=False):
    """initialze wien2k input files"""
    initlapw = ["init_lapw", "-rkmax", str(rkmax), "-ecut",
                str(ecut), "-vxc", str(xc)]
    if spin_polarized:
        initlapw.append("-sp")
    sp.check_call(initlapw)

def run_w2k(exe=None, ec=1.0e-8, spin_polarized=False):
    """run wien2k calculation"""
    if exe is None:
        exe = "run_lapw"
        if spin_polarized:
            exe = "runsp_lapw"
    runlapw = [exe, "-ec", str(ec)]
    sp.check_call(runlapw)

def init_testcase(jsonname, logger):
    """initialize the inputs of test case setup by JSON file

    Args:
        jsonname (str): path to JSON file
    """
    with open(jsonname, 'r') as h:
        d = json.load(h)

def gap_test():
    """run initializtion"""
    args = gap_parser()
    log_level = logging.INFO
    if args.debug:
        log_level = logging.debug
    logger = create_logger(log_level)
    if os.path.isdir(rootdir):
        if args.force_restart:
            logger.info("Forced restart")
            shutil.rmtree(rootdir)
        else:
            raise IOError("working directory exists. Remove it before continue")
    testcases = list(glob.glob("init/*.json"))
    for x in testcases:
        logger.info("Found test: %s", x)
        if args.init_all:
            logger.info("Initiaizing")
            init_testcase(x, logger)


if __name__ == "__main__":
    gap_test()

