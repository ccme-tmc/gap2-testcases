# -*- coding: utf-8 -*-
"""testcase utitlies"""
import logging
from argparse import ArgumentParser
import os
w2kroot = None
version_w2k = None
# pylint: disable=W0702,W0703
try:
    w2kroot = os.environ["WIENROOT"]
    with open(os.path.join(w2kroot, "VERSION"), 'r') as h:
        version_w2k = h.readline().split('_')[1].split()[0]
except Exception:
    pass

def gap_parser():
    """parser of gap test"""
    p = ArgumentParser(description=__doc__)
    p.add_argument("--init-all", dest="init_all", action="store_true",
                   help="initialize WIEN2k and GAP inputs")
    p.add_argument("--debug", dest="debug", action="store_true",
                   help="debug mode")
    p.add_argument("--force", dest="force_restart", action="store_true",
                   help="forcing delete the workspace and restart")
    return p.parse_args()

def create_logger(name="results_teg.log", log_level=logging.INFO):
    """create a logger"""
    hand_file = logging.FileHandler(name, mode='w')
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

def check_wien2k_version(require_version):
    """check if version is qualified

    Args:
        require_version (str)

    Returns:
        bool
    """
    if require_version is None:
        return True
    return False

