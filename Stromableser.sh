#!/bin/bash

PY_DIR=/usr/local/ocv-cam

. ~/.bashrc
conda activate ocv-cam

cd "$PY_DIR"
python Stromableser.py
