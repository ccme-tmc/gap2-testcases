# -*- coding: utf-8 -*-
"""testcase object"""
# pylint: disable=R0205,W0707
from __future__ import print_function
import os
import glob
import json
import subprocess as sp
from shutil import copy2

from .utils import which, create_logger, intify, cleanup_tmp

_logger = create_logger("testdriver", log=False, stream=True)
del create_logger

rootdir = os.path.dirname(os.path.dirname(__file__))
initdir = os.path.join(rootdir, "init")
structdir = os.path.join(rootdir, "struct_files")
inputsdir = os.path.join(rootdir, "inputs")
refersdir = os.path.join(rootdir, "refs")

w2kroot = None
version_w2k = None
# pylint: disable=W0702,W0703
try:
    w2kroot = os.environ["WIENROOT"]
    with open(os.path.join(w2kroot, "VERSION"), 'r') as _:
        version_w2k = _.readline().split('_')[1].split()[0]
except Exception:
    pass

gapinput_ext = ["core", "vxc", "struct", "energy", "vector", "vsp", "in1"]

# predefined set of test cases for comparison with literature
predefine_sets = {
    "JiangH16": ["JH16"],
    }


def get_all_testcases():
    """get all available tests"""
    all_tests = []
    for x in os.listdir(initdir):
        d = os.path.join(initdir, x)
        if os.path.isdir(d):
            _logger.debug("searching %s", x)
            jsons = [os.path.basename(y) for y in glob.glob(os.path.join(d, "*.json"))]
            jsons.sort(key=lambda y: int(y.split('_')[0]))
            all_tests.extend(os.path.join(x, y) for y in jsons)
    _logger.info("all available test cases: %r", all_tests)
    return all_tests

def find_tests(include=None, exclude=None, use_predef=None):
    """find test cases satisfying conditions.

    If the same testcase is present in both include and exclude,
    it is excluded at the end.
    """
    def _have_id_name(index, name, l):
        d, fn = name.split('/')
        if index in l or d in l or fn in l or name in l:
            return True
        return False
    all_tests = get_all_testcases()
    found = []

    if not (include is None or use_predef is None):
        raise ValueError("specify either include or use_predef")

    if include is not None:
        include = intify(include)

    if use_predef is not None:
        include = predefine_sets.get(use_predef, None)
        if include is None:
            raise ValueError("Undefined set name {}".format(use_predef))

    if exclude is not None:
        exclude = intify(exclude)
    else:
        exclude = []

    os.chdir(initdir)
    for i, t in enumerate(all_tests):
        if _have_id_name(i+1, t, exclude):
            continue
        if include and not _have_id_name(i+1, t, include):
            continue
        found.append(t)
    os.chdir(rootdir)
    _logger.info("all test cases to be run: %r", found)
    return found


class TestCase(object):
    """test case

    Args:
        jsonname (str): path to JSON file
        logger (logging.Logger): logger for recording running info
    """
    def __init__(self, pjson, logger, init_mode=False,
                 workspace=None, force_restart=False, **kwargs):
        self.logger = logger
        self._force_restart = force_restart
        with open(os.path.join(initdir, pjson), 'r') as h:
            d = json.load(h)
        _logger.info("> case loaded, information:")
        try:
            for key in ["casename", "rkmax", "is_sp", "task"]:
                _logger.info(">> %s: %s", key, d[key])
                self.__setattr__(key, d[key])
        except KeyError:
            raise KeyError("broken testcase file, missing required key %s" % key)
        self.scf_args = d["scf"]
        _logger.info(">> wien2k SCF initialization parameters:")
        for k, v in self.scf_args.items():
            _logger.info(">> %10s : %r", k, v)
        self._w2k_nprocs = self.scf_args.get("nprocs", 1)
        self.gap_args = d["gap"]
        self._gap_nprocs = self.gap_args.get("nprocs", 1)
        _logger.info(">> gap initialization parameters:")
        for k, v in self.gap_args.items():
            _logger.info(">> %10s : %r", k, v)
        self.category, self.index = pjson.split('/')
        self.index = int(os.path.splitext(self.index)[0].split('_')[0])
        self._init_mode = init_mode
        #self._testcase = os.path.join(self.category,
        #                              str(self.index) + "_" + self.casename + "_task_" + self.task)
        self._testcase = os.path.splitext(pjson)[0]
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
        if not self._init_mode:
            return
        gap_init = "gap" + gap_version + "_init"
        if which(gap_init) is None and not dry:
            info = "gap_init for version %s is not found: %s" % (gap_version, gap_init)
            _logger.error(info)
            raise ValueError(info)
        self._create_input_case()
        self._switch_to_wien_case()
        if not dry:
            if self._init_mode == "w":
                self._init_w2k_scf()
                self._run_w2k_scf()
            if self._init_mode in ["g", "w"]:
                self._run_gap_init(gap_init)
        self._switch_to_rootdir()

    def run(self, gap_version, gap_suffix=None,
            nprocs=None, dry=False):
        """start test case

        Args:
            maxnprocs (int)
            dry (bool) : fake run for workflow test
        """
        gap_nprocs = [self._gap_nprocs,]
        if isinstance(self._gap_nprocs, list):
            gap_nprocs = self._gap_nprocs
        gap_nprocs.sort(reverse=True)
        if nprocs is None:
            nprocs = gap_nprocs[0]
        else:
            for x in gap_nprocs:
                if x < nprocs:
                    x = nprocs
                    break
        gap_x = "gap" + gap_version + {1: ""}.get(nprocs, "-mpi") \
                + {None: ""}.get(gap_suffix, "-{}".format(gap_suffix)) + ".x"
        if which(gap_x) is None and not dry:
            info = "gap.x for version %s is not found: %s" % (gap_version, gap_x)
            _logger.error(info)
            raise ValueError(info)

        self._link_inputs_to_workspace_case()
        self._switch_to_workspace_case()
        if not dry:
            try:
                self._run_gap(gap_x, nprocs)
            except IOError:
                self.logger.warning("Test case %s has been run before hand. Skip.",
                                    self._testcase)
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

    def _run_gap(self, gap_x, nprocs, cleanup=True):
        """run gap calculation

        Args:
            gap_x (str): gap.x executable
        """
        rungap = [gap_x,]
        if nprocs > 1:
            rungap = ["mpirun", "-np", str(nprocs)] + rungap
        try:
            self.logger.info("> begin to run case: %s", " ".join(self._testcase))
            self.logger.info(">> command %s", " ".join(rungap))
            sp.check_call(rungap)
        except sp.CalledProcessError:
            info = "> fail for case: %s" % self._testcase
            self.logger.error(info)
        else:
            self.logger.info("> finished case successfully :)")
            # TODO analyse data when finished successfully
            if cleanup:
                self.logger.info("> clean up large files in tmp")
                for ext in ["eps", "mwm", "vmat"]:
                    self.logger.info(">> cleaning %s", ext)
                    cleanup_tmp(ext)

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
            raise IOError("workspace directory exists: {}.\nUse --force to run anyway"
                          .format(self._workspace))
        os.makedirs(self._workspace)
        for f in [self.casename + "." + ext for ext in gapinput_ext] + ["gw.inp"]:
            src = os.path.join(self._gapdir, f)
            dst = os.path.join(self._workspace, f)
            if os.path.isfile(src):
                os.symlink(src, dst)
                _logger.debug("linking %s to %s", src, dst)

