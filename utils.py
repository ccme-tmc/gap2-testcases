# -*- coding: utf-8 -*-
"""testcase utitlies"""
try:
    from __future__ import print_function
except ImportError:
    pass
import json
import logging
import subprocess as sp
import re
import os
from shutil import copy2

rootdir = os.path.dirname(__file__)
structdir = os.path.join(rootdir, "struct_files")
inputsdir = os.path.join(rootdir, "inputs")
refersdir = os.path.join(rootdir, "refs")

w2kroot = None
version_w2k = None
# pylint: disable=W0702,W0703
try:
    w2kroot = os.environ["WIENROOT"]
    with open(os.path.join(w2kroot, "VERSION"), 'r') as _h:
        version_w2k = _h.readline().split('_')[1].split()[0]
except Exception:
    pass
gapinput_ext = ["core", "vxc", "struct", "energy", "vector", "vsp", "in1"]

def which(executable):
    """emulation of which function in shutil of Python3

    Args:
        executable (str)

    Returns
        str, if executable is found in PATH
        None otherwise
    """
    path = os.popen("which %s" % executable).read()
    if path:
        return path.strip()
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


def create_logger(name="results_gap.log", debug=False):
    """create a logger"""
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
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

class TestCase(object):
    """test case

    Args:
        jsonname (str): path to JSON file
        logger (logging.Logger)
    """
    def __init__(self, pjson, logger, init_w2k=False, init_gap=False,
                 workspace=None, force_restart=False, **kwargs):
        self.logger = logger
        self._force_restart = force_restart
        with open(pjson, 'r') as h:
            d = json.load(h)
        logger.info("> case loaded, information:")
        try:
            for key in ["casename", "rkmax", "is_sp", "task"]:
                logger.info(">> %s: %s", key, d[key])
                self.__setattr__(key, d[key])
        except KeyError:
            raise KeyError("broken testcase file, missing required key %s" % key)
        self.scf_args = d["scf"]
        logger.info(">> wien2k SCF initialization parameters:")
        for k, v in self.scf_args.items():
            logger.info(">> %10s : %r", k, v)
        self._w2k_nprocs = self.scf_args.get("nprocs", 1)
        self.gap_args = d["gap"]
        self._gap_nprocs = self.gap_args.get("nprocs", 1)
        logger.info(">> gap initialization parameters:")
        for k, v in self.gap_args.items():
            logger.info(">> %10s : %r", k, v)
        self.index = int(os.path.splitext(os.path.basename(pjson))[0])
        self._init_w2k = init_w2k
        self._init_gap = init_gap
        self._testcase = str(self.index) + "_" + self.casename + "_task_" + self.task
        # prepare all inputs file under self._inputdir
        self._inputdir = os.path.join(inputsdir, self._testcase)
        # struct file at self._struct
        self._struct = os.path.join(structdir, self.casename + ".struct")
        # wien2k calculation in self._wiendir
        self._wiendir = os.path.join(self._inputdir, self.casename)
        # gap inputs file in self._gapdir
        self._gapdir = os.path.join(self._inputdir, "gap")
        # the workspace to run gap.x
        if workspace is None:
            workspace = "workspace"
        workspace = os.path.join(rootdir, workspace)
        self._workspace = os.path.join(workspace, self._testcase)

    def init(self, gap_version, dry=False):
        """initialize test case

        Args:
            dry (bool) : fake run for workflow test
        """
        gap_init = "gap" + gap_version + "_init"
        if which(gap_init) is None and not dry:
            info = "gap_init for version %s is not found: %s" % (gap_version, gap_init)
            self.logger.error(info)
            raise ValueError(info)
        self._create_input_case()
        self._switch_to_wien_case()
        if not dry:
            if self._init_w2k:
                self._init_w2k_scf()
                self._run_w2k_scf()
            if self._init_gap:
                self._run_gap_init(gap_init)
        self._switch_to_rootdir()

    def run(self, gap_version, nprocs=None, dry=False):
        """start test case

        Args:
            dry (bool) : fake run for workflow test
        """
        if nprocs is None:
            nprocs = self._gap_nprocs
        gap_x = "gap" + gap_version + {1: ""}.get(nprocs, "-mpi") + ".x"
        if which(gap_x) is None and not dry:
            info = "gap.x for version %s is not found: %s" % (gap_version, gap_x)
            self.logger.error(info)
            raise ValueError(info)

        self._link_inputs_to_workspace_case()
        self._switch_to_workspace_case()
        if not dry:
            self._run_gap(gap_x, nprocs)
        self._switch_to_rootdir()

    def _init_w2k_scf(self):
        """initialze wien2k input files"""
        initlapw = ["init_lapw", "-b", "-rkmax", str(self.rkmax),]
        for key in ["ecut", "vxc"]:
            initlapw.extend(["-" + key, str(self.scf_args.get(key))])
        if self.is_sp:
            initlapw.append("-sp")
        numk = self.scf_args.get("numk")
        if numk is None:
            raise NotImplementedError("manual kmesh is not supported")
        initlapw.extend(["-numk", str(numk)])
        try:
            self.logger.info(">> initializing with %s", " ".join(initlapw))
            sp.check_call(initlapw)
        except sp.CalledProcessError:
            info = "fail to initialize %s" % self._testcase
            self.logger.error(info)

    def _run_gap_init(self, gap_init):
        """initialize gap inputs"""
        initgap = [gap_init, "-d", self._gapdir, "-t", self.task]
        #initgap = [gap_init, "-d", self._gapdir,]
        nkp = self.gap_args.pop("nkp")
        if nkp > 0:
            initgap.extend(["-nkp", str(nkp)])
        else:
            kmesh = self.gap_args.get("kmesh_gw")
            raise NotImplementedError
        # spin-unpolarized gw with sp input
        if self.is_sp:
            initgap.extend(["-s", "1"])
        # pop out other arguments not belonging to gap_init
        for k in ["version", "kmesh_gw", "nprocs"]:
            self.gap_args.pop(k, None)
        for k, v in self.gap_args.items():
            initgap.extend(["-"+k, str(v)])
        try:
            self.logger.info(">> run gap_init with %s", " ".join(initgap))
            sp.check_call(initgap)
        except sp.CalledProcessError:
            info = "fail to run initgap for %s" % self._testcase
            self.logger.error(info)

    def _run_w2k_scf(self, exe=None):
        """run wien2k calculation"""
        exe = self.scf_args.get("exe", None)
        if exe is None:
            exe = "run_lapw"
            if self.is_sp:
                exe = "runsp_lapw"
        ec = self.scf_args.get("ec")
        runlapw = [exe, "-ec", "%15.12f" % ec]
        try:
            self.logger.info(">> run SCF with %s", " ".join(runlapw))
            sp.check_call(runlapw)
        except sp.CalledProcessError:
            info = "fail to run SCF for %s" % self._testcase
            self.logger.error(info)

    def _run_gap(self, gap_x, nprocs):
        """run gap calculation

        Args:
            gap_x (str): gap.x executable
        """
        rungap = [gap_x,]
        if nprocs > 1:
            rungap = ["mpirun", "-np", str(nprocs)] + rungap
        try:
            self.logger.info(">> run gap.x with %s", " ".join(rungap))
            sp.check_call(rungap)
        except sp.CalledProcessError:
            info = "fail to run gap.x for %s" % self._testcase
            self.logger.error(info)

    def _switch_to_workspace_case(self):
        os.chdir(self._workspace)

    def _switch_to_rootdir(self):
        os.chdir(rootdir)

    def _switch_to_input_case(self):
        os.chdir(self._inputdir)

    def _switch_to_wien_case(self):
        os.chdir(self._wiendir)

    def _create_input_case(self):
        if not os.path.isdir(self._wiendir):
            os.makedirs(self._wiendir)
            copy2(self._struct, self._wiendir)

    def _link_inputs_to_workspace_case(self):
        if os.path.isdir(self._workspace):
            if self._force_restart:
                #rmtree(self._workspace)
                self.logger.warning("force restart anyway")
                return
            raise IOError("workspace directory exists!")
        os.makedirs(self._workspace)
        for f in [self.casename + "." + ext for ext in gapinput_ext] + ["gw.inp"]:
            src = os.path.join(self._gapdir, f)
            dst = os.path.join(self._workspace, f)
            if os.path.isfile(src):
                os.symlink(src, dst)
                self.logger.debug("linking %s to %s", src, dst)


class GwInp():
    """
    The changable parameters are saved in a dict, with the names of parameters as keys.
    The values are 6-member tuple, with members as

    1. Data type
    2. Pattern to match target block
    3. Default value
    4. Line in the block, 0 for one-line parameter
    5. Number of paramters in the block line, 0 for one-line parameter
    6. Index of parameter in the line, 0 for one-line parameter

    Args:
        path_gw_inp (str) : path to gw.inp
    """
    available_params = {
        "pwm": (float, r"%BareCoul", 2.0, 1, 2, 0),
        "kmr": (float, r"%MixBasis", 0.75, 1, 1, 0),
        "barcevtol": (float, r"barcevtol", 0.1, 0, 0, 0),
        "MB_emax": (float, r"MB_emax", 20.0, 0, 0, 0),
        "lmbmax": (int, r"%MixBasis", 3, 2, 3, 0),
        "wftol": (float, r"%MixBasis", 1.0E-4, 2, 3, 1),
        "lblmax": (int, r"%MixBasis", 0, 2, 3, 2),
        "iop_core": (int, r"iop_core", 0, 0, 0, 0),
        "iop_fgrid": (int, r"%FreqGrid", 3, 1, 5, 0),
        "nomeg": (int, r"%FreqGrid", 16, 1, 5, 1),
        "omegmax": (float, r"%FreqGrid", 0.42, 1, 5, 2),
        "omegmin": (float, r"%FreqGrid", 0.00, 1, 5, 3),
        "emaxpol": (float, r"emaxpol", 1.0E10, 0, 0, 0),
        "emaxsc": (float, r"emaxsc", 1.0E10, 0, 0, 0),
        }

    @classmethod
    def get_available_params(cls):
        """return the changable parameters"""
        return tuple(cls.available_params.keys())

    def __init__(self, path_gw_inp='gw.inp'):
        with open(path_gw_inp, 'r') as h:
            self._lines = [l for l in h.readlines()]
        self._params = {}
        self._locate_params()

    def _locate_params(self):
        """locate line indices of parameters"""
        for i, line in enumerate(self._lines):
            l = trim_after(line, r'#').strip()
            if l == '':
                continue
            for k, v in self.available_params.items():
                if l.startswith(v[1]):
                    self._params[k] = i + v[3]
                    continue

    @property
    def params(self):
        """dict, line index of parameter"""
        return self._params

    def get_param(self, key):
        """Get the value of the parameter specified by key
        """
        if key not in self.available_params:
            raise KeyError("%s is not available" % key)
        raise NotImplementedError

    def modify_params(self, **kwargs):
        """Change parameters

        Note:
            To modify parameters in block, the block should be present
            in the input file, otherwise it will be written as one-line
            parameter. This may be fixed in the future
        """
        gwlines = []
        linos = []
        params = []
        extras = []
        for k in kwargs:
            if k in self.available_params:
                params.append(k)
                linos.append(self._params[k])
            else:
                extras.append("%s = %s\n" % (k, kwargs[k]))
        for i, l in enumerate(self._lines):
            l = l.strip()
            if i in linos:
                k = params[linos.index(i)]
                pat = _get_pattern(self.available_params[k][-2])
                sub = _get_substr(*self.available_params[k][-2:], kwargs[k])
                l = re.sub(pat, sub, l.strip())
            gwlines.append(l+'\n')
        gwlines.extend(extras)
        return gwlines


_COMMENT_PAT = r"(#[\w \|\(\),\.-]*)?"

def _get_pattern(n):
    '''Return the pattern of n parameter block line'''
    if n > 0:
        s = [r"([\w \.-]+)",] * n
        return r'^' + r'\|'.join(s) + _COMMENT_PAT + r'$'
    return r"^" + r"([\w \.-]+)=([\w \.-]+)" + _COMMENT_PAT + r"$"

def _get_substr(n, ind, value):
    '''Substitute parameter with value'''
    if n == 0:
        sub = "\\1 = " + str(value) + ' \\3'
    else:
        sublist = ["\\"+str(i+1) for i in range(n)]
        sublist[ind] = str(value)
        sub = ' | '.join(sublist) + ' \\' + str(n+1)
    return sub
