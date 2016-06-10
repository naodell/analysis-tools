from __future__ import division

from timeit import default_timer as timer

import numpy as np
from scipy.stats import norm
from lmfit import Parameter, Parameters

from nllfitter.fit_tools import get_data, fit_plot, scale_data
from nllfitter.future_fitter import Model, NLLFitter

def bg_pdf(x, a): 
    '''
    Second order Legendre Polynomial with constant term set to 0.5.

    Parameters:
    ===========
    x: data
    a: model parameters (a1 and a2)
    '''
    return 0.5 + a[0]*x + 0.5*a[1]*(3*x**2 - 1)

def sig_pdf(x, a):
    '''
    Second order Legendre Polynomial (normalized to unity) plus a Gaussian.

    Parameters:
    ===========
    x: data
    a: model parameters (A, mu, sigma, a1, a2)
    '''
    return a[0]*norm.pdf(x, a[1], a[2]) + (1 - a[0])*bg_pdf(x, a[3:5])


if __name__ == '__main__':

    ### Start the timer
    start = timer()

    ### get data and convert variables to be on the range [-1, 1]
    xlimits  = (12., 70.)
    channels = ['1b1f', '1b1c']

    datasets  = []
    for channel in channels:
        data, n_total  = get_data('data/events_pf_{0}.csv'.format(channel), 
                                  'dimuon_mass', xlimits)
        datasets.append(data)

    ### Fit single models to initialize parameters ###
    ### Define bg model and carry out fit ###
    bg1_params = Parameters()
    bg1_params.add_many(
                       ('a1', 0., True, None, None, None),
                       ('a2', 0., True, None, None, None)
                      )
    bg1_model = Model(bg_pdf, bg1_params)
    bg_fitter = NLLFitter(bg1_model)
    bg_result = bg_fitter.fit(datasets[0])

    bg2_params = Parameters()
    bg2_params.add_many(
                       ('b1', 0., True, None, None, None),
                       ('b2', 0., True, None, None, None)
                      )
    bg2_model = Model(bg_pdf, bg2_params)
    bg_fitter = NLLFitter(bg2_model)
    bg_result = bg_fitter.fit(datasets[1])

    ### Carry out combined fit ###
    bg_params = bg1_params + bg2_params

    print ''
    print 'runtime: {0:.2f} ms'.format(1e3*(timer() - start))

