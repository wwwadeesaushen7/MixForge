"""Bound native math thread pools for responsive use on modest computers."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMBA_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(name,'2')
