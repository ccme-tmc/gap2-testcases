#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""initialize the testcase"""
from __future__ import print_function
import glob
import json
import logging
import subprocess as sp
from argparse import ArgumentParser

def create_logger(log_level):
    """create a logger"""
    hand_file = logging.FileHandler("results_test.log", mode='w')
    hand_stream = logging.StreamHandler()
    form_file = logging.Formatter(fmt='%(asctime)s - %(name)7s:%(levelname)8s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    form_stream = logging.Formatter(fmt='%(name)7s:%(levelname)8s - %(message)s')
    hand_file.setFormatter(form_file)
    hand_file.setLevel(log_level)
    hand_stream.setFormatter(form_stream)
    hand_stream.setLevel(logging.INFO)
    logger = logging.getLogger("gaptest")
    logger.setLevel(log_level)
    logger.addHandler(hand_file)
    logger.addHandler(hand_stream)
    return logger

def _parser():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--init-all", dest="init_all", action="store_true",
                        help="initialize WIEN2k and GAP inputs")
    parser.add_argument("--debug", dest="debug", action="store_true",
                        help="debug mode")
    return parser.parse_args()

def clean_init_dir():
    pass

def init_wien2k():
    pass

def init_gap():
    pass

def gap_test():
    """run initializtion"""
    args = _parser()
    log_level = logging.INFO
    if args.debug:
        log_level = logging.debug
    logger = create_logger(log_level)
    testcases = list(glob.glob("init/*.json"))
    initparams = []
    for x in testcases:
        logger.debug("found test in JSON: %s", x)
        with open(x, 'r') as h:
            initparams.append(json.load(h))
        logger.debug(">> input parameters: %r", initparams[-1])
    print(initparams)
    if args.init_all:
        return


if __name__ == "__main__":
    gap_test()

