import pickle
from multiprocessing import Process, Queue, Pool

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import numdifftools as nd

#from functools import partial
#from scipy.integrate import quad
#from lmfit import Parameters

#import nllfit.fit_tools as ft
import scripts.plot_tools as pt

np.set_printoptions(precision=2)

fancy_labels = dict(
                    mumu  = [r'$\sf p_{T,\mu}$', r'$\sf \mu\mu$'],
                    ee    = [r'$\sf p_{T,e}$', r'$\sf ee$'],
                    emu   = [r'$\sf p_{T,trailing}$', r'$\sf e\mu$'],
                    mutau = [r'$\sf p_{T,\tau}$', r'$\sf \mu\tau$'],
                    etau  = [r'$\sf p_{T,\tau}$', r'$\sf e\tau$'],
                    mu4j  = [r'$\sf p_{T,\mu}$', r'$\sf \mu+jets$'],
                    e4j   = [r'$\sf p_{T,e}$', r'$\sf e+jets$'],
                    )
features = dict(
                mumu  = 'lepton2_pt', # trailing muon pt
                ee    = 'lepton2_pt', # trailing electron pt
                emu   = 'trailing_lepton_pt', # like the name says
                mutau = 'lepton2_pt', # tau pt
                etau  = 'lepton2_pt', # tau pt
                mu4j  = 'lepton1_pt', # muon pt
                e4j   = 'lepton1_pt', # electron pt
                )

def signal_amplitudes(beta, br_tau, single_w = False):
    '''
    Returns an array of branching fractions for each signal channel.

    parameters:
    ===========
    beta : W branching fractions [beta_e, beta_mu, beta_tau, beta_h]
    br_tau : tau branching fractions [br_e, br_mu, br_h]
    single_w : if process contains a single w decay
    '''

    if single_w:
        amplitudes = np.array([beta[0],  # e 
                               beta[1],  # mu
                               beta[2]*br_tau[0],  # tau_e
                               beta[2]*br_tau[1],  # tau_mu
                               beta[2]*br_tau[2],  # tau_h
                               beta[3],  # h
                               ])
    else:
        amplitudes = np.array([beta[0]*beta[0],  # e, e
                               beta[1]*beta[1],  # mu, mu
                               2*beta[0]*beta[1],  # e, mu
                               beta[2]*beta[2]*br_tau[0]**2,  # tau_e, tau_e
                               beta[2]*beta[2]*br_tau[1]**2,  # tau_mu, tau_mu
                               2*beta[2]*beta[2]*br_tau[0]*br_tau[1],  # tau_e, tau_m
                               2*beta[2]*beta[2]*br_tau[0]*br_tau[2],  # tau_e, tau_h
                               2*beta[2]*beta[2]*br_tau[1]*br_tau[2],  # tau_mu, tau_h
                               beta[2]*beta[2]*br_tau[2]*br_tau[2],  # tau_h, tau_h
                               2*beta[0]*beta[2]*br_tau[0],  # e, tau_e
                               2*beta[0]*beta[2]*br_tau[1],  # e, tau_mu
                               2*beta[0]*beta[2]*br_tau[2],  # e, tau_h
                               2*beta[1]*beta[2]*br_tau[0],  # mu, tau_e
                               2*beta[1]*beta[2]*br_tau[1],  # mu, tau_mu
                               2*beta[1]*beta[2]*br_tau[2],  # mu, tau_h
                               2*beta[0]*beta[3],  # e, h
                               2*beta[1]*beta[3],  # mu, h
                               2*beta[2]*beta[3]*br_tau[0],  # tau_e, h
                               2*beta[2]*beta[3]*br_tau[1],  # tau_mu, h
                               2*beta[2]*beta[3]*br_tau[2],  # tau_h, h
                               beta[3]*beta[3],  # h, h
                               ])

    return amplitudes

# covariance approximators
def calculate_variance(f, x0):
    '''
    calculates variance for input function.
    '''

    hcalc = nd.Hessdiag(f)
    hobj = hcalc(x0)[0]
    var = 1./hobj

    return var

def calculate_covariance(f, x0):
    '''
    calculates covariance for input function.
    '''

    hcalc = nd.Hessian(f,
                       step        = 1e-3,
                       method      = 'forward',
                       full_output = True
                       )

    hobj = hcalc(x0)[0]
    if np.linalg.det(hobj) != 0:
        # calculate the full covariance matrix in the case that the H
        hinv        = np.linalg.pinv(hobj)
        sig         = np.sqrt(hinv.diagonal())
        corr_matrix = hinv/np.outer(sig, sig)

        return sig, corr_matrix
    else:
        return False

# GOF statistics
def chi2_test(y1, y2, var1, var2):
    chi2 = 0.5*(y1 - y2)**2/(var1 + var2)
    return chi2

# modified objective for testing lepton universality
def objective_lu(params, data, objective, test_type=1):
    if test_type == 1:
        beta = params[0]
        params_new = np.concatenate([[beta, beta, beta, 1 - 3*beta], params[1:]])
    elif test_type == 2:
        beta_emu = params[0]
        beta_tau = params[1]
        params_new = np.concatenate([[beta_emu, beta_emu, beta_tau, 1 - 2*beta_emu - beta_tau], params[2:]])
    return objective(params_new, data)

def reduced_objective(params, data, params_fixed, mask, objective):
    new_params = params_fixed.copy()
    new_params[mask] = params
    return objective(new_params, data) 

# Barlow-Beeston method for limited MC statistics
def bb_objective_aux(params_mc, data_val, exp_val, exp_var):
    a = 1
    b = exp_var/exp_val - 1
    c = -1*data_val*exp_var/exp_val**2
    beta_plus  = (-1*b + np.sqrt(b**2 - 4*a*c))/2
    beta_minus = (-1*b - np.sqrt(b**2 - 4*a*c))/2

    return beta_plus, beta_minus
        

class FitData(object):
    def __init__(self, path, selections, processes, process_cut=0):
        self._selections     = selections
        self._processes      = processes
        self._n_selections   = len(selections)
        self._n_processess   = len(processes)
        self._selection_data = {s: self._initialize_data(path, s) for s in selections}

        # retrieve parameter configurations
        self._decay_map = pd.read_csv('data/decay_map.csv').set_index('id')
        self._initialize_parameters()

        # initialize branching fraction parameters
        self._beta_init   = self._pval_init[:4]
        self._br_tau_init = self._pval_init[4:7]
        self._ww_amp_init = signal_amplitudes(self._beta_init, self._br_tau_init)
        self._w_amp_init  = signal_amplitudes(self._beta_init, self._br_tau_init, single_w=True)

        # initialize fit data
        self.veto_list = ['ee_cat_gt2_eq0', 'mumu_cat_gt2_eq0'] # used to remove categories from fit
        self._initialize_fit_tensor(process_cut)

        # minimization cache
        self.initialize_minimization_cache()

        # initialize cost (do this last)
        self._cost_init = 0
        self._cost_init = self.objective(self.get_params_init(as_array=True))

    # initialization functions
    def _initialize_data(self, location, selection):
        '''
        Gets data for given selection including:
        * data templates
        * signal templates
        * background templates
        * morphing templates for shape systematics
        * binning
        '''

        infile = open(f'{location}/{selection}_templates.pkl', 'rb')
        data = pickle.load(infile)
        infile.close()

        return data

    def _initialize_parameters(self):
        '''
        Gets parameter configuration from a file.
        '''
        df_params = pd.read_csv('data/model_parameters.csv')
        df_params = df_params.set_index('name')
        df_params = df_params.astype({'err_init':float, 'val_init':float})

        self._nparams    = df_params.shape[0]
        self._npoi       = df_params.query('type == "poi"').shape[0]
        self._nnorm      = df_params.query('type == "norm"').shape[0]
        self._nshape     = df_params.query('type == "shape"').shape[0]
        self._pval_init  = df_params['val_init'].values
        self._perr_init  = df_params['err_init'].values
        self._parameters = df_params

        return

    def _initialize_fit_tensor(self, process_cut):
        '''
        This converts the data stored in the input dataframes into a numpy tensor of
        dimensions (n_selections*n_categories*n_bins, n_processes, n_nuisances).
        '''

        #def np_templates():
        #    for pname, param in params.iterrows():
        #        if param.type == 'shape' and param[sel]:
        #            if f'{pname}_up' in sub_template.columns and param['active'] and param[ds]: 
        #                deff_plus  = sub_template[f'{pname}_up'].values - val
        #                deff_minus = sub_template[f'{pname}_down'].values - val
        #            else:
        #                deff_plus  = np.zeros_like(val)
        #                deff_minus = np.zeros_like(val)
        #            delta_plus.append(deff_plus + deff_minus)
        #            delta_minus.append(deff_plus - deff_minus)
        #        elif param.type == 'norm':
        #            if param[sel] and param[ds] and param['active']:
        #                norm_vector.append(1)
        #            else:
        #                norm_vector.append(0)
        
        params = self._parameters.query('type != "poi"')
        self._model_data = dict()
        self._bin_np     = dict()
        self._rnum_cache = dict()
        self._categories = []
        for sel in self._selections:
            category_tensor = []
            for category, templates in self.get_selection_data(sel).items():
                self._categories.append(f'{sel}_{category}') 
                templates                             = templates['templates']
                data_val, data_var                    = templates['data']['val'], templates['data']['var']
                self._bin_np[f'{sel}_{category}']     = np.ones(data_val.size)
                self._rnum_cache[f'{sel}_{category}'] = np.random.randn(data_val.size)

                norm_mask  = []
                process_mask = []
                data_tensor  = []
                for ds in self._processes:

                    if sel in ['etau', 'mutau', 'emu'] and ds == 'fakes':
                        ds = 'fakes_ss'

                    # initialize mask for removing irrelevant processes
                    if ds not in templates.keys():
                        if ds in ['ttbar', 't', 'ww']:
                            process_mask.extend(21*[0,])
                        elif ds == 'wjets':
                            process_mask.extend(6*[0,])
                        else:
                            process_mask.append(0)

                        continue
                    else:
                        template = templates[ds]

                        if sel in ['etau', 'mutau', 'emu'] and ds == 'fakes_ss':
                            ds = 'fakes'

                
                    if ds in ['zjets_alt', 'diboson', 'fakes']: # processes that are not subdivided

                        val, var = template['val'].values, template['var'].values
                        #print(ds, val/np.sqrt(data_var))

                        # determine whether process contribution is significant
                        # or should be masked (this should be studied for
                        # impact on poi to determine proper threshold)
                        if val.sum()/np.sqrt(data_var.sum()) <= process_cut:
                            process_mask.append(0)
                            continue
                        else:
                            process_mask.append(1)

                        delta_plus, delta_minus = [], []
                        norm_vector = []
                        for pname, param in params.iterrows():
                            if param.type == 'shape' and param[sel]:
                                if f'{pname}_up' in template.columns and param['active'] and param[ds]:
                                    deff_plus  = template[f'{pname}_up'].values - val
                                    deff_minus = template[f'{pname}_down'].values - val
                                else:
                                    deff_plus  = np.zeros_like(val)
                                    deff_minus = np.zeros_like(val)
                                delta_plus.append(deff_plus + deff_minus)
                                delta_minus.append(deff_plus - deff_minus)

                            elif param.type == 'norm':
                                if param[sel] and param[ds] and param['active']:
                                    norm_vector.append(1)
                                else:
                                    norm_vector.append(0)

                        process_array = np.vstack([val.reshape(1, val.size), var.reshape(1, var.size), delta_plus, delta_minus])
                        data_tensor.append(process_array.T)
                        norm_mask.append(norm_vector)

                    elif ds in ['ttbar', 't', 'ww', 'wjets']: # datasets with sub-templates
                        full_sum, reduced_sum = 0, 0
                        for sub_ds, sub_template in template.items():
                            val, var = sub_template['val'].values, sub_template['var'].values
                            full_sum += val.sum()

                            # determine wheter process should be masked
                            if val.sum()/np.sqrt(data_var.sum()) <= process_cut:
                                process_mask.append(0)
                                continue
                            else:
                                process_mask.append(1)

                            delta_plus, delta_minus = [], []
                            norm_vector = []
                            for pname, param in params.iterrows():
                                if param.type == 'shape' and param[sel]:
                                    if f'{pname}_up' in sub_template.columns and param['active'] and param[ds]: 
                                        deff_plus  = sub_template[f'{pname}_up'].values - val
                                        deff_minus = sub_template[f'{pname}_down'].values - val
                                    else:
                                        deff_plus  = np.zeros_like(val)
                                        deff_minus = np.zeros_like(val)
                                    delta_plus.append(deff_plus + deff_minus)
                                    delta_minus.append(deff_plus - deff_minus)
                                elif param.type == 'norm':
                                    if param[sel] and param[ds] and param['active']:
                                        norm_vector.append(1)
                                    else:
                                        norm_vector.append(0)

                            process_array = np.vstack([val.reshape(1, val.size), var.reshape(1, var.size), delta_plus, delta_minus])
                            data_tensor.append(process_array.T)
                            norm_mask.append(norm_vector)

                self._model_data[f'{sel}_{category}'] = dict(
                                                             data             = (data_val, data_var),
                                                             model            = np.stack(data_tensor),
                                                             process_mask     = np.array(process_mask, dtype=bool),
                                                             shape_param_mask = params.query('type == "shape"')[sel].values.astype(bool),
                                                             norm_mask        = np.stack(norm_mask)
                                                             )

        return

    def initialize_minimization_cache(self):
        '''
        Used for debugging minimization and analyzing per bin statistical n.p. and cost
        '''
        self._cache = {cat:dict(cost = 0, np_bb = 0) for cat in self._categories}
        self._np_cost = 0
 
    # getter functions
    def get_selection_data(self, selection):
        return self._selection_data[selection]

    def get_model_data(self, category):
        return self._model_data[category]

    def get_params_init(self, as_array=False):
        if as_array:
            return self._parameters['val_init'].values
        else:
            return self._parameters['val_init']

    def get_errs_init(self, as_array=False):
        if as_array:
            return self._parameters['err_init'].values
        else:
            return self._parameters['err_init']

    # model building
    def model_sums(self, selection, category):
        '''
        This sums over all datasets/sub_datasets in selection_data for the given category.
        '''

        templates = self._selection_data[selection][category]['templates'] 
        outdata = np.zeros_like(templates['data']['val'], dtype=float)
        for ds, template in templates.items():
            if ds == 'data':
                continue 

            if ds in ['ttbar', 't', 'ww', 'wjets']:
                for sub_ds, sub_template in template.items():
                    outdata += sub_template['val'].values
            else:
                outdata += template['val'].values

        return outdata

    def mixture_model(self, params, category, 
                      process_amplitudes=None, 
                      no_sum=False, 
                      randomize=False
                      ):
        '''
        Outputs mixture and associated variance for a given category.

        Parameters:
        ===========
        params: parameter values for model
        category: description of lepton/jet/b tag category
        process_amplitudes: if signal process amplitudes have been calculated
            they can be passed in, otherwise calculates values based on input
            parameters
        no_sum: (default False) if set to True, will not sum across the process dimension
        randomize: (default False) if set to True, will randomly displace
            individual bin normalizations based on the cached values.  
        '''

        # get the model data
        model_data = self.get_model_data(category)

        # split parameters into poi, normalization and shape
        norm_params  = params[self._npoi:self._npoi + self._nnorm]
        shape_params = params[self._npoi + self._nnorm:]

        # update norm parameter array
        norm_params = model_data['norm_mask']*norm_params
        norm_params[norm_params == 0] = 1
        norm_params = np.product(norm_params, axis=1)

        # apply shape parameter mask and build array for morphing
        shape_params_masked = shape_params[model_data['shape_param_mask']]
        shape_params_masked = np.concatenate([[1, 0], 0.5*shape_params_masked**2, 0.5*shape_params_masked])

        # get calculate process_amplitudes
        if process_amplitudes is None:
            beta, br_tau = params[:4], params[4:7]
            ww_amp = signal_amplitudes(beta, br_tau)/self._ww_amp_init
            w_amp  = signal_amplitudes(beta, br_tau, single_w=True)/self._w_amp_init
            process_amplitudes = np.concatenate([ww_amp, ww_amp, ww_amp, w_amp, [1, 1, 1]])

        # mask the process amplitudes for this category and apply normalization parameters
        process_amplitudes_masked = process_amplitudes[model_data['process_mask']]
        process_amplitudes_masked = norm_params.T*process_amplitudes_masked

        # build expectation from model_tensor and propogate systematics
        model_tensor = model_data['model']
        model_val    = np.tensordot(model_tensor[:,:,0].T, process_amplitudes_masked, axes=1)
        model_val    = np.tensordot(model_tensor, shape_params_masked, axes=1) # n.p. modification
        if not no_sum:
            model_val = np.tensordot(model_val.T, process_amplitudes_masked, axes=1)

        #print(model_val)
        model_var = model_tensor[:,:,1].sum(axis=0) 
        #model_var    = np.tensordot(model_tensor[:,:,1].T, process_amplitudes_masked, axes=1)

        if randomize:
            model_val += np.sqrt(model_var)*self._rnum_cache[category]

        return model_val, model_var
        
    def objective(self, params, 
                  data                = None,
                  cost_type           = 'poisson',
                  no_shape            = False,
                  do_mc_stat          = True,
                  randomize_templates = False
                 ):
        '''
        Cost function for MC data model.  This version has no background
        compononent and is intended for fitting toy data generated from the signal
        MC.

        Parameters:
        ===========
        params : numpy array of parameters.  The first four are the W branching
                 fractions, all successive ones are nuisance parameters.
        data : dataset to be fitted
        cost_type : either 'chi2' or 'poisson'
        no_shape : sums over all bins in input templates
        do_mc_stat: include bin-by-bin Barlow-Beeston parameters accounting for limited MC statistics
        randomize_templates: displaces the prediction in each bin by a fixed, random amount.
        '''

        # build the process amplitudes (once per evaluation) 
        beta, br_tau = params[:4], params[4:7]
        ww_amp = signal_amplitudes(beta, br_tau)/self._ww_amp_init
        w_amp  = signal_amplitudes(beta, br_tau, single_w=True)/self._w_amp_init
        process_amplitudes = np.concatenate([ww_amp, ww_amp, ww_amp, w_amp, [1, 1, 1]]) 
        
        # calculate per category, per selection costs
        cost = 0
        for category, template_data in self._model_data.items():

            # omit categories from calculation of cost
            if category in self.veto_list:
                continue

            # get the model and data templates
            model_val, model_var = self.mixture_model(params, category, process_amplitudes, randomize=randomize_templates)
            if data is None:
                data_val, data_var = template_data['data']
            else:
                data_val, data_var = data[category]

            # for testing parameter estimation while excluding kinematic shape information
            #veto_list = []
            if no_shape: # or category.split('_')[0] in veto_list:
                data_val  = np.sum(data_val)
                data_var  = np.sum(data_var)
                model_val = np.sum(model_val)
                model_var = np.sum(model_var)

            # include effect of MC statisitcs (important that this is done
            # AFTER no_shape condition so inputs are integrated over)
            if do_mc_stat:
                bin_amp = self._bin_np[category]
                bin_amp = bb_objective_aux(bin_amp, data_val, model_val, model_var)[0]
                model_val *= bin_amp

                self._bin_np[category] = bin_amp 
                bb_penalty = (1 - bin_amp)**2/(2*model_var/model_val**2)
                cost += np.sum(bb_penalty)

                self._cache[category]['bb_penalty'] = bb_penalty


            # calculate the cost
            if cost_type == 'poisson':
                mask = (model_val > 0) & (data_val > 0)
                nll = -data_val[mask]*np.log(model_val[mask]) + model_val[mask]
                nll += data_val[mask]*np.log(data_val[mask]) - data_val[mask]
            elif cost_type == 'chi2':
                mask = data_var + model_var > 0
                nll = 0.5*(data_val[mask] - model_val[mask])**2 / (data_var[mask] + model_var[mask])

            self._cache[category]['cost'] = nll
            cost += nll.sum()

        # Add prior constraint terms for nuisance parameters 
        pi_param = (params[4:] - self._pval_init[4:])**2 / (2*self._perr_init[4:]**2)
        cost += pi_param.sum()
        self._np_cost = pi_param

        # require that the branching fractions sum to 1
        beta  = params[:4]
        cost += (1 - np.sum(beta))**2/(2e-12)

        # require that all branching fractions are contained in [0, 1]
        if np.any((beta <= 0.) | (beta >= 1.)):
            cost = np.inf

        return cost
