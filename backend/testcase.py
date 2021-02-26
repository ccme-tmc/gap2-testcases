# -*- coding: utf-8 -*-
"""testcase object"""
from __future__ import print_function
import os
import glob
import json
import subprocess as sp
import datetime as dt
from shutil import copy2

from .utils import which, create_logger, intify, cleanup_tmp, get_divisors

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

def get_all_tcnames():
    """get all available tests"""
    all_tests = []
    for x in os.listdir(initdir):
        d = os.path.join(initdir, x)
        if os.path.isdir(d):
            _logger.debug("searching %s", x)
            jsons = [os.path.basename(y) for y in glob.glob(os.path.join(d, "*.json"))]
            jsons.sort(key=lambda y: int(y.split('_')[0]))
            all_tests.extend(os.path.join(x, os.path.splitext(y)[0]) for y in jsons)
    _logger.info("all available test cases: %r", all_tests)
    return all_tests

def find_tests(include=None, exclude=None):
    """find test cases satisfying conditions.

    If the same testcase is present in both include and exclude,
    it is excluded at the end.
    """
    def _have_id_name(index, name, l):
        d, fn = name.split('/')
        fn = fn.strip('.json')
        if index in l or d in l or fn in l or name in l:
            return True
        return False
    all_tests = get_all_tcnames()
    found = []

    if include is not None:
        include = intify(include)
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
        tcname (str): name of testcase, relative to the init directory
        logger (logging.Logger): logger for recording running info and results
            For driver and initializaiton info, use _logger
    """
    def __init__(self, tcname, logger, init_mode=False,
                 workspace=None, force_restart=False, **kwargs):
        self.logger = logger
        self._force_restart = force_restart
        self._tcname = tcname
        with open(os.path.join(initdir, tcname+".json"), 'r') as h:
            d = json.load(h)
        _logger.info("> case loaded, information:")
        try:
            for key in ["casename", "rkmax", "is_sp", "task"]:
                v = d.pop(key)
                _logger.info(">> %s: %s", key, v)
                self.__setattr__(key, v)
        except KeyError:
            raise KeyError("broken testcase file, missing required key %s" % key)
        self.scf_args = d.pop("scf")
        _logger.info(">> wien2k SCF initialization parameters:")
        for k, v in self.scf_args.items():
            _logger.info(">> %10s : %r", k, v)
        self._w2k_nprocs = self.scf_args.pop("nprocs", 1)
        self.gap_args = d.pop("gap")
        self._gap_nprocs = self.gap_args.pop("nprocs", None)
        if self._gap_nprocs is None:
            self._gap_nprocs = get_divisors(self.gap_args["nkp"])
        _logger.info(">> gap initialization parameters:")
        for k, v in self.gap_args.items():
            _logger.info(">> %10s : %r", k, v)
        self.category, self.index = tcname.split('/')
        self.index = int(os.path.splitext(self.index)[0].split('_')[0])
        self._init_mode = init_mode
        # prepare all inputs file under self._inputdir
        self._inputdir = os.path.join(inputsdir, self._tcname)
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
        self._workspace = os.path.join(workspace, self._tcname)

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
        # quickly return if in initialization mode
        if self._init_mode:
            return
        gap_nprocs = [self._gap_nprocs,]
        if isinstance(self._gap_nprocs, list):
            gap_nprocs = self._gap_nprocs
        gap_nprocs.sort(reverse=True)
        if nprocs is None:
            nprocs = gap_nprocs[0]
        else:
            for x in gap_nprocs:
                if x <= nprocs:
                    nprocs = x
                    break
        _logger.info(">> using %d processors", nprocs)
        _logger.info(">>   from %r", gap_nprocs)
        if gap_suffix is not None:
            gap_suffix = "-{}".format(gap_suffix)
        else:
            gap_suffix = ''
        gap_x = "gap" + gap_version + {1: ""}.get(nprocs, "-mpi") \
                + "{}.x".format(gap_suffix)
        if which(gap_x) is None and not dry:
            info = "gap.x for version %s is not found: %s" % (gap_version, gap_x)
            _logger.error(info)
            raise ValueError(info)
        try:
            self._link_inputs_to_workspace_case()
        except IOError:
            self.logger.warning("Test case %s has been skipped.",
                                 self._tcname)
            return
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
            info = "fail to initialize %s" % self._tcname
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
            _logger.info(">> run gap_init with %s", " ".join(initgap))
            sp.check_call(initgap)
        except sp.CalledProcessError:
            info = "fail to run initgap for %s" % self._tcname
            _logger.error(info)

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
            _logger.info(">> run SCF with %s", " ".join(runlapw))
            sp.check_call(runlapw)
        except sp.CalledProcessError:
            info = "fail to run SCF for %s" % self._tcname
            _logger.error(info)

    def _run_gap(self, gap_x, nprocs, cleanup=True):
        """run gap calculation

        Args:
            gap_x (str): gap.x executable
        """
        rungap = [gap_x,]
        if nprocs > 1:
            rungap = ["mpirun", "-np", str(nprocs)] + rungap
        try:
            self.logger.info("> begin to run case: %s", self._tcname)
            self.logger.info(">> command %s", " ".join(rungap))
            with open("gaptest_{}.log".format(dt.datetime.today().strftime("%y%m%d-%H%M%S")),
                      'w') as h:
                proc = sp.Popen(rungap, stdout=h, stderr=sp.STDOUT)
                proc.wait()
        except sp.CalledProcessError:
            info = "> fail for case: %s" % self._tcname
            self.logger.error(info)
        else:
            self.logger.info("> finished case successfully :)")
            # TODO analyse data when finished successfully
        finally:
            if cleanup:
                self.logger.info("> clean up large files in tmp")
                for ext in ["eps", "mwm", "vmat", "sxc_nn", "sx_nn"]:
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
                self.logger.warning("forced restart anyway")
                return
            raise IOError("workspace directory exists: {}. skip\nUse --force to run anyway"
                          .format(self._workspace))
        os.makedirs(self._workspace)
        for f in [self.casename + "." + ext for ext in gapinput_ext] + ["gw.inp"]:
            src = os.path.join(self._gapdir, f)
            dst = os.path.join(self._workspace, f)
            if os.path.isfile(src):
                os.symlink(src, dst)
                _logger.debug("linking %s to %s", src, dst)

