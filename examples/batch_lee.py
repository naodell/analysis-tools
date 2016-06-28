#!/usr/bin/env python

import pickle
import os,sys
import numpy as np
import nllfitter.lookee as lee

from scipy.stats import chi2, norm

if __name__ == '__main__':

    if len(sys.argv) > 2:
        channel = str(sys.argv[1])
        ndim    = int(sys.argv[2])
    else:
        channel = '1b1f'
        ndim    = 1
                   
    path        = 'data/batch_{0}_{1}D/'.format(channel, ndim)
    filenames   = [path + f for f in os.listdir(path) if os.path.isfile(path + f)]
    print 'Getting data from {0}...'.format(path)

    qmaxscan    = []
    phiscan     = []
    paramscan   = []
    u_0         = np.linspace(0., 20., 1000)
    for name in filenames:
        f = open(name, 'r')
        u_0 = pickle.load(f)
        qmaxscan.append(pickle.load(f))
        phiscan.append(pickle.load(f))
        paramscan.append(pickle.load(f))
        f.close()

    qmaxscan = np.array([q for scan in qmaxscan for q in scan])
    phiscan = np.concatenate(phiscan, axis=0)
    paramscan = np.concatenate(paramscan, axis=0)

    ### Calculate LEE correction ###
    if channel == '1b1f':
        qmax = 18.31
    elif channel == '1b1c':
        qmax = 9.8
    elif channel == 'combined':
        qmax = 24.43
    elif channel == 'combination': 
        qmax = 27.57

    k1, nvals1, p_global    = lee.lee_nD(np.sqrt(qmax), u_0, phiscan, j=ndim, k=1, fix_dof=True)
    k2, nvals2, p_global    = lee.lee_nD(np.sqrt(qmax), u_0, phiscan, j=ndim, k=2, fix_dof=True)
    k, nvals, p_global      = lee.lee_nD(np.sqrt(qmax), u_0, phiscan, j=ndim)
    lee.validation_plots(u_0, phiscan, qmaxscan, [nvals1, nvals2, nvals], [int(k1), int(k2), k], '{0}_{1}D'.format(channel, ndim))

    print 'k = {0:.2f}'.format(k)
    for i,n in enumerate(nvals):
        print 'N{0} = {1:.2f}'.format(i, n)
    print 'local p_value = {0:.7f},  local significance = {1:.2f}'.format(norm.cdf(-np.sqrt(qmax)), np.sqrt(qmax))
    print 'global p_value = {0:.7f}, global significance = {1:.2f}'.format(p_global, -norm.ppf(p_global))


