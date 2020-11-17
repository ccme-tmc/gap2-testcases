#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""distribute tarball to remote servers for running tests"""
from __future__ import print_function
import os
import json
import subprocess as sp
import warnings
from gap_test import __version__, __project__

try:
    with open('remotes.json') as _h:
        dist_remotes = json.load(_h)
except IOError:
    dist_remotes = {}

#dist_remotes = {
#    "tmcws": "/home/zhangmy/programs/",
#    "stevezhang@222.29.156.87": "/home/stevezhang/quamtum-codes/",
#    "1501210186@162.105.133.134": "/gpfs/share/home/1501210186/program/",
#    "1501210186@162.105.133.164": "/gpfs/share/home/1501210186/program/",
#    "1501210186@115.27.161.31": "/gpfs/share/home/1501210186/program/",
#    }

rsync_cmd = ["rsync", "-qazrul", "--inplace"]
tar_cmd = ["tar", "-zxp"]


def rsync_and_untar(tarball, remote_ip, dirpath, verbose=False):
    """distribute mushroom tarball to dirpath on remote_ip by rsync"""
    try:
        cmds = rsync_cmd + [str(tarball), "{}:{}/".format(remote_ip, dirpath)]
        if verbose:
            print("running commands:", " ".join(cmds))
        sp.call(cmds)
    except sp.CalledProcessError:
        warnings.warn("fail to rsync {} to {}:{}/".format(tarball, remote_ip, dirpath))
        return
    
    try:
        cmds = ["ssh", remote_ip] + tar_cmd + \
               ["-f", "{}/{}".format(dirpath, os.path.basename(tarball)), "-C", dirpath]
        if verbose:
            print("running commands:", " ".join(cmds))
        sp.call(cmds)
    except sp.CalledProcessError:
        warnings.warn("fail to extract {} at {}:{}".format(os.path.basename(tarball), remote_ip, dirpath))
    print("Done rsyncing", str(tarball), "to", "{}:{}".format(remote_ip, dirpath))

def dist():
    """distribute tarball"""
    tarball = os.path.join(os.path.dirname(__file__), "dist",
                           "%s-%s.tar.gz" % (__project__, __version__))
    for remote_ip, dirpath in dist_remotes.items():
        if isinstance(dirpath, list):
            for dp in dirpath:
                rsync_and_untar(tarball, remote_ip, dp)
        else:
            rsync_and_untar(tarball, remote_ip, dirpath)


if __name__ == "__main__":
    dist()

