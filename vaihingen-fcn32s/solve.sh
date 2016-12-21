#!/bin/bash

set -x
set -e
exec &> >(tee -a "logs/log_fcn_voc32.txt.`date +'%Y-%m-%d_%H-%M-%S'`")
time ./solve.py