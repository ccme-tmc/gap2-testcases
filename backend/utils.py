# -*- coding: utf-8 -*-
"""testcase utitlies"""
from __future__ import print_function
import logging
import glob
import re
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter

def gap_parser(docstr):
    """parser of gap test"""
    p = ArgumentParser(description=docstr,
                       formatter_class=RawDescriptionHelpFormatter)
    p.add_argument(dest="gap_version", type=str,
                   help="version of gap")
    p.add_argument("-l", dest="logname", type=str, default="gaptest")
    p.add_argument("-x", dest="exclude", type=str, default=None, nargs="+",
                    help="testcases to exclude, default to None")
    p.add_argument("-i", dest="include", type=str, default=None, nargs="+",
                   help="testcases to include, default to include all cases")
    p.add_argument("-n", type=int, dest="nprocs", default=1,
                   help="default number of processors for running")
    p.add_argument("--init", action="store_true",
                   help="initialize WIEN2k and GAP inputs")
    p.add_argument("--init-gap", dest="init_gap", action="store_true",
                   help="only initialize GAP inputs with finished WIEN2k SCF")
    p.add_argument("--dry", action="store_true", help="dry run for test use")
    p.add_argument("-p", dest="preview", action="store_true",
                   help="preview names of testcases to be run and exit")
    p.add_argument("--gf", dest="gap_suffix", type=str, default=None,
                   help="suffix of gap executable, e.g. ir4o in gap2e-mpi-ir4o.x")
    p.add_argument("-d", dest="workspace", type=str, default="workspace",
                   help="working directory")
    p.add_argument("-D", dest="debug", action="store_true", help="debug mode")
    p.add_argument("-a", dest="append", action="store_true",
                   help="append mode for logger")
    p.add_argument("--force", dest="force_restart", action="store_true",
                   help="forcing restart an existing testcase")
    return p

def which(executable):
    """emulation of which function in shutil of Python3

    Args:
        executable (str)

    Returns
        str, if executable is found in PATH
        None otherwise
    """
    path = os.popen("which %s 2> /dev/null" % executable).read().strip()
    if path:
        return path
    return None


def trim_after(string, regex, include_pattern=False):
    """Trim a string after the first match of regex.

    If fail to match any pattern, the original string is returned

    The matched pattern is trimed as well.

    Args:
        string (str): the string to trim
        regex (regex): the regex to match
        include_pattern (bool): if the matched pattern is included
        in the return string
    """
    m = re.search(regex, string)
    if m is None:
        if include_pattern:
            return string[:m.end()]
        return string[:m.start()]
    return string


def create_logger(name, debug=False, log=True, stream=True, append=False):
    """create a logger

    Args:
        log (bool): write to log
        stream (bool): write to stream
    """
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    mode = 'w'
    if append:
        mode = 'a'
    if log:
        hand_file = logging.FileHandler(name+".log", mode=mode)
        hand_file.setLevel(log_level)
        form_file = logging.Formatter(fmt='%(asctime)s - %(name)7s:%(levelname)8s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        hand_file.setFormatter(form_file)
        logger.addHandler(hand_file)
    if stream:
        hand_stream = logging.StreamHandler()
        form_stream = logging.Formatter(fmt='%(name)7s:%(levelname)8s - %(message)s')
        hand_stream.setFormatter(form_stream)
        hand_stream.setLevel(logging.INFO)
        logger.addHandler(hand_stream)
    return logger

def intify(strlist):
    """convert the integer string in strlist to integer"""
    new = []
    for x in strlist:
        try:
            new.append(int(x))
        except ValueError:
            new.append(x)
    return new

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

def cleanup_tmp(ext):
    """clean up large files in tmp directory generated from GAP2 calculation

    Args:
        ext (str): part of the extension name

    """
    pat = "tmp/*.{}*".format(ext)
    fs = glob.glob(pat)
    for f in fs:
        os.unlink(f)

def get_divisors(num, ascend=False):
    """get all divisors of integer num

    Args:
        num (int)
        ascend (bool): if True, the divisors are sorted in ascending order.
            Otherwise in descending order.

    Returns:
        list
    """
    seq = (num, 0, -1)
    if ascend:
        seq = (1, num+1, 1)
    return [i for i in range(*seq) if num%i == 0]

# run itself as test
if __name__ == "__main__":
    import unittest as ut

    class test_utils(ut.TestCase):
        def test_get_divisors(self):
            """get divisors of integers"""
            self.assertListEqual([9, 3, 1], get_divisors(9))
            self.assertListEqual([1, 3, 9], get_divisors(9, ascend=True))
            self.assertListEqual([216, 108, 72, 54, 36, 27, 24, 18, 12, 9, 8, 6, 4, 3, 2, 1],
                                 get_divisors(216))
    ut.main()
