#!/usr/bin/env python

import _init_paths
import caffe
import surgery, score

import numpy as np
import os

import setproctitle
setproctitle.setproctitle(os.path.basename(os.getcwd()))

weights = '../ilsvrc-nets/VGG_FCN.caffemodel'

# init
#caffe.set_device(int(sys.argv[1]))
caffe.set_device(1)
caffe.set_mode_gpu()

solver = caffe.SGDSolver('solver.prototxt')
solver.net.copy_from(weights)

# surgeries
interp_layers = [k for k in solver.net.params.keys() if 'up' in k]
surgery.interp(solver.net, interp_layers)

# scoring
val = np.loadtxt('../data/vaihingen/val.txt', dtype=str)

for _ in range(25):
    solver.step(400)
    score.seg_tests(solver, False, val, layer='score')
