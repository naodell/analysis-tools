from __future__ import division

import numpy as np
import numdifftools as nd
from scipy.optimize import minimize
from lmfit import Parameter, Parameters, report_fit

class NLLFitter:
    '''
    Class for estimating PDFs using negative log likelihood minimization.  Fits
    a Model class to a dataset.    

    Parameters:
    ==========
    model    : a Model object or and array of Model objects
    data     : the dataset or datasets we wish to carry out the modelling on
    min_algo : algorith used for minimizing the nll (uses available scipy.optimize algorithms)
	verbose  : control verbosity of fit method
    '''
    def __init__(self, model, min_algo='SLSQP', verbose=True, lmult=(1., 1.)):
       self.model     = model
       self.min_algo  = min_algo
       self.verbose   = verbose
       self._lmult    = lmult

    def _objective(self, params, data):
        '''
        Default objective function.  Perhaps it would make sense to make this
        easy to specify.  Includes L1 and L2 regularization terms which might
        be problematic...
        
        Parameters:
        ==========
        a: model parameters in an numpy array
        '''
        nll = self.model.calc_nll(data, params)
        return nll + self._lmult[0] * np.sum(np.abs(params)) + self._lmult[1] * np.sum(params**2)

    def _get_corr(self, data, params):

        f_obj   = lambda a: self._objective(a, data)
        hcalc   = nd.Hessian(f_obj, step=0.01, method='central', full_output=True) 
        hobj    = hcalc(params)[0]
        hinv    = np.linalg.inv(hobj)

        # get uncertainties on parameters
        sig = np.sqrt(hinv.diagonal())

        # calculate correlation matrix
        mcorr = hinv/np.outer(sig, sig)

        return sig, mcorr

    def fit(self, data, min_algo='SLSQP', params_init=None, calculate_corr=True):
        '''
        Fits the model to the given dataset using scipy.optimize.minimize.
        Returns the fit result object.

        Parameter:
        ==========
        data           : dataset to be fit the model to
        min_algo       : minimization algorithm to be used (defaults to SLSQP
                         since it doesn't require gradient information and accepts bounds and
                         constraints).
        params_init    : initialization parameters; if not specified, current values are used
        calculate_corr : specify whether the covariance matrix should be
                         calculated.  If true, this will do a numerical calculation of the
                         covariance matrix based on the currenct objective function about the
                         minimum determined from the fit
        '''

        if params_init: 
            self.model.update_params(params_init)
        else:
            params_init = self.model.get_parameters(by_value=True)

        result = minimize(self._objective, 
                          params_init,
                          method = self.min_algo, 
                          bounds = self.model.get_bounds(),
                          #constraints = self.model.get_constraints(),
                          args   = (data)
                          )
        if self.verbose:
            print 'Fit finished with status: {0}'.format(result.status)

        if result.status == 0:
            if calculate_corr:
                sigma, corr = self._get_corr(data, result.x)
            else:
                sigma, corr = result.x, 0.

            self.model.update_parameters(result.x, (sigma, corr))

            if self.verbose:
                report_fit(self.model.get_parameters(), show_correl=False)
                print ''
                print '[[Correlation matrix]]'
                print corr, '\n'

        return result	

