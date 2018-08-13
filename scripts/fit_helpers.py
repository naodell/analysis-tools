import pickle

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
#from functools import partial
import numdifftools as nd
#from scipy.integrate import quad
#from lmfit import Parameters

#import nllfit.fit_tools as ft
import scripts.plot_tools as pt

np.set_printoptions(precision=2)

features = dict()
features['mumu']  = 'lepton2_pt' # trailing muon pt
features['ee']    = 'lepton2_pt' # trailing electron pt
features['emu']   = 'trailing_lepton_pt' # like the name says
features['mutau'] = 'lepton2_pt' # tau pt
features['etau']  = 'lepton2_pt' # tau pt
features['mu4j']  = 'lepton1_pt' # muon pt
features['e4j']   = 'lepton1_pt' # electron pt

fancy_labels = dict()
fancy_labels['mumu']  = (r'$\sf p_{T,\mu}$', r'$\sf \mu\mu$')
fancy_labels['ee']    = (r'$\sf p_{T,e}$', r'$\sf ee$')
fancy_labels['emu']   = (r'$\sf p_{T,trailing}$', r'$\sf e\mu$')
fancy_labels['mutau'] = (r'$\sf p_{T,\tau}$', r'$\sf \mu\tau$')
fancy_labels['etau']  = (r'$\sf p_{T,\tau}$', r'$\sf e\tau$')
fancy_labels['mu4j']  = (r'$\sf p_{T,\mu}$', r'$\sf \mu+jets$')
fancy_labels['e4j']   = (r'$\sf p_{T,e}$', r'$\sf e+jets$')


def ebar_wrapper(data, ax, bins, limits, style):
    x, y, err = pt.hist_to_errorbar(data, bins, limits)
    mask = y > 0.
    x, y, err = x[mask], y[mask], err[mask]
    ax.errorbar(x, y, yerr=err,
                capsize = 0,
                fmt = style,
                elinewidth = 2,
                markersize = 5
                )

def shape_morphing(f, templates, order='quadratic'):
    '''
    Efficiency shape morphing for nuisance parameters.  

    Parameters:
    ===========
    f: value of nuisance parameter
    templates: triplet of (nominal, up, down) template variations
    order: choose either a linear or quadratic variation of templates with nuisance parameter f
    '''
    t_nom  = templates[0]
    t_up   = templates[1]
    t_down = templates[2]

    if order == 'linear':
        t_eff = t_nom + f*(t_up - t_down)/2
    elif order == 'quadratic':
        t_eff = (f*(f - 1)/2)*t_down - (f - 1)*(f + 1)*t_nom + (f*(f + 1)/2)*t_up

    return t_eff

class FitData(object):
    def __init__(self, path, selections, feature_map):
        self._selections     = selections
        self._n_selections   = len(selections)
        self._decay_map      = pd.read_csv('data/decay_map.csv').set_index('id')
        self._selection_data = {s: self._initialize_template_data(path, feature_map[s], s) for s in selections}

        # parameters
        self._beta   = [0.108, 0.108, 0.108, 1 - 3*0.108]  # e, mu, tau, h
        self._tau_br = [0.1783, 0.1741, 0.6476]  # e, mu, h
        self._initialize_nuisance_parameters()

    def _initialize_template_data(self, location, target, selection):
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

    def _initialize_nuisance_parameters(self):
        '''
        Retrieves nuisance parameters (needs development)
        '''
        self._nuisance_params = pd.read_csv('data/nuisance_parameters.csv')

    def get_selection_data(self, selection):
        return self._selection_data[selection]

    def get_params_init(self):
        return self._beta

    def modify_template(self, templates, pdict):
        '''
        Modifies a single template based on all shape nuisance parameters save
        in templates dataframe. 
        '''
        t_nominal = templates['val'] 
        t_new = np.zeros(t_nominal.shape)
        for pname, pval in pdict.items():
            t_up, t_down = templates[f'{pname}_up'], templates[f'{pname}_down'] 
            dt = shape_morphing(pval, (t_nominal, t_up, t_down)) - t_nominal
            t_new += dt

        t_new += t_nominal

        return t_new


    def objective(self, params, data, cost_type='poisson', no_shape=False):
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
        mask : an array with same size as the input parameters for indicating parameters to fix
        no_shape : sums over all bins in input templates
        '''

        # unpack parameters here
        # branching fractions first
        beta = params[:4]
        pdict = dict(zip(self._param_names, params))

        # calculate per category, per bin costs
        cost = 0
        for sel in self._selections:
            sdata = self.get_selection_data(sel)

            for b, bdata in sdata.items():
                templates = bdata['templates']

                # get the data
                f_data, var_data = templates['data']['val'], templates['data']['var']

                # get simulated background components and apply cross-section nuisance parameters
                f_zjets, var_zjets     = templates['zjets']['val'], templates['zjets']['var']
                f_diboson, var_diboson = templates['diboson']['val'], templates['diboson']['var']
                f_model   = pdict['xs_zjets']*f_zjets + pdict['xs_diboson']*f_diboson
                var_model = var_zjets + var_diboson

                # get the signal components and apply mixing of W decay modes according to beta
                for sig_label in ['ttbar', 't']:#, 'wjets']:
                    template_collection = templates[sig_label]
                    signal_template     = pd.DataFrame.from_items((dm, modify_template(t[dm], pdict)) for dm, t in templates[sig_label])
                    f_sig, var_sig      = signal_mixture_model(beta,
                                                               br_tau   = self._tau_br,
                                                               h_temp   = signal_template,
                                                               single_w = (sig_label == 'wjets')
                                                              )
                    # prepare mixture
                    var_model += var_sig
                    f_model += pdict[f'xs_{sig_label}']

                # lepton efficiencies as normalization nuisance parameters
                # lepton energy scale as morphing parameters
                if sel in 'ee':
                    f_model *= pdict['trigger_e']**2
                    f_model *= pdict['eff_e']**2
                elif sel in 'emu':
                    f_model *= pdict['trigger_mu']*pdict['trigger_e']
                    f_model *= pdict['eff_e']*pdict['eff_mu']
                elif sel in 'mumu':
                    f_model *= trigger_mu**2
                    f_model *= eff_mu**2
                elif sel == 'etau':
                    f_model *= trigger_e
                    f_model *= eff_tau*eff_e
                elif sel == 'mutau':
                    f_model *= trigger_mu
                    f_model *= eff_tau*eff_mu
                elif sel == 'e4j':
                    f_model *= trigger_e
                    f_model *= eff_e
                elif sel == 'mu4j':
                    f_model *= trigger_mu
                    f_model *= eff_mu

                # apply overall lumi nuisance parameter
                f_model *= lumi

                # get fake background and include normalization nuisance parameters
                if sel in ['etau', 'mutau', 'mu4j']: 
                    f_fakes, var_fakes = templates['fakes']['val'], templates['fakes']['var']
                    f_model   += pdict['norm_fakes']*f_fakes
                    var_model += var_fakes

                # for testing fit without kinematic fit
                if no_shape:
                    f_data = np.sum(f_data)
                    f_model = np.sum(f_model)

                # calculate the cost
                if cost_type == 'chi2':
                    mask = var_data + var_model > 0
                    nll = (f_data - f_model)**2 / (var_data + var_model)
                    nll = nll[mask]
                elif cost_type == 'poisson':
                    mask = f_model > 0
                    nll = -f_data[mask]*np.log(f_model[mask]) + f_model[mask]
                cost += np.sum(nll)

        # require that the branching fractions sum to 1
        cost += (1 - np.sum(beta))**2/(2*0.000001**2)  

        # Add prior terms for nuisance parameters correlated across channels
        # (lumi, cross-sections) luminosity
        for pname in self._param_names:
            cost += (pdict[pname] - self._param_init[pname])**2 / (2*self._param_vars[pname])

        return cost


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
                               2*beta[2]*beta[2]*br_tau[0]*br_tau[2],  # tau_e, tau_
                               2*beta[2]*beta[2]*br_tau[1]*br_tau[2],  # tau_mu, tau_h
                               2*beta[0]*beta[2]*br_tau[0],  # e, tau_e
                               beta[2]*beta[2]*br_tau[2]*br_tau[2],  # tau_h, tau_h
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
                               beta[3]*beta[3],  # tau_h, h
                               ])

    return amplitudes

def signal_mixture_model(beta, br_tau, h_temp, mask=None, sample=False, single_w=False):
    '''
    Mixture model for the ttbar/tW signal model.  The output will be an array
    corresponding to a sum over the input template histograms scaled by their
    respective efficiencies and branching fraction products.

    parameters:
    ==========
    beta : branching fractions for the W decay
    br_tau : branching fractions for the tau decay
    h_temp : dataframe with template histograms for each signal component
    mask : a mask that selects a subset of mixture components
    sample : if True, the input templates will be sampled before returning
    single_w : if process contains a single w decay
    '''

    beta_init  = signal_amplitudes([0.108, 0.108, 0.108, 0.676], [0.1783, 0.1741, 0.6476], single_w)
    beta_fit   = signal_amplitudes(beta, br_tau, single_w)
    beta_ratio = beta_fit/beta_init

    if not isinstance(mask, type(None)):
        beta_ratio = mask*beta_ratio

    if sample:
        f = np.dot(np.random.poisson(h_temp), beta_ratio)
    else:
        f = np.dot(h_temp, beta_ratio)

    return f

def calculate_covariance(f, x0):
    '''
    calculates covariance for input function.
    '''

    hcalc = nd.Hessian(f,
                       step        = 1e-2,
                       method      = 'central',
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

def fit_plot(fit_data, selection, xlabel, log_scale=False):

    # unpack fit_data
    results  = fit_data['results']
    ix       = fit_data['selections'].index(selection)
    n_sel    = fit_data['n_selections']
    br_tau   = fit_data['br_tau']

    sel_data = fit_data[selection]
    data     = sel_data['data']
    bg       = sel_data['bg']
    signal   = sel_data['signal']

    #print(data[0].sum(), bg[0].sum(), signal[0].sum())

    # starting amplitudes
    p_init     = fit_data['p_init']['vals']
    beta_init  = p_init[n_sel+1:]
    lumi_scale = results.x[0]
    alpha_fit  = results.x[ix+1]
    beta_fit   = results.x[n_sel+1:]

    # initialize the canvas
    fig, axes = plt.subplots(2, 1,
                             figsize     = (8, 9),
                             facecolor   = 'white',
                             sharex      = True,
                             gridspec_kw = {'height_ratios': [3, 1]}
                             )
    fig.subplots_adjust(hspace=0)

    # initialize bins
    bins = fit_data[selection]['bins']
    xmin, xmax = bins.min(), bins.max()
    dx = (bins[1:] - bins[:-1])
    dx = np.append(dx, dx[-1])
    x = bins + dx/2

    # plot the data
    y_data, yerr_data = data[0], np.sqrt(data[1])
    data_plot = axes[0].errorbar(x, y_data/dx, yerr_data/dx,
                                 fmt        = 'ko',
                                 capsize    = 0,
                                 elinewidth = 2
                                 )

    # plot signal and bg (prefit)
    y_bg, yerr_bg = bg[0], np.sqrt(bg[1])
    axes[0].errorbar(x, y_bg/dx, yerr_bg/dx,
                     label='_nolegend_',
                     fmt        = 'C1.',
                     markersize = 0,
                     capsize    = 0,
                     elinewidth = 5,
                     alpha = 0.5
                     )
    axes[0].plot(bins, y_bg/dx, drawstyle='steps-post', c='C1', alpha=0.5)

    y_sig, yvar_sig = signal_mixture_model(beta_init, br_tau, signal)
    y_combined, yerr_combined = y_bg + y_sig, np.sqrt(yerr_bg**2 + yvar_sig)
    axes[0].errorbar(x, y_combined/dx, yerr_combined/dx,
                     label='_nolegend_',
                     fmt        = 'C0.',
                     markersize = 0,
                     capsize    = 0,
                     elinewidth = 5,
                     alpha = 0.5
                     )
    axes[0].plot(bins, y_combined/dx, drawstyle='steps-post', c='C0', alpha=0.5)

    ratio_pre = y_data/y_combined
    ratio_pre_err = (1/y_combined**2)*np.sqrt(y_data**2*yerr_combined**2 + y_combined**2*yerr_data**2)

    y_bg, yerr_bg = lumi_scale*alpha_fit*y_bg, lumi_scale*alpha_fit*yerr_bg
    axes[0].errorbar(x, y_bg/dx, yerr_bg/dx,
                     label = '_nolegend_',
                     fmt        = 'C3.',
                     markersize = 0,
                     capsize    = 0,
                     elinewidth = 5,
                     alpha = 0.5,
                     )
    axes[0].plot(bins, y_bg/dx, drawstyle='steps-post', linestyle='--', label='_nolegend_', c='C3')

    y_sig, yvar_sig = signal_mixture_model(beta_fit, br_tau, signal)
    y_combined      = y_bg + lumi_scale*y_sig
    yerr_combined   = np.sqrt(yerr_bg**2 + yvar_sig*lumi_scale**2)
    axes[0].errorbar(x, y_combined/dx, yerr_combined/dx,
                     fmt        = 'C9.',
                     capsize    = 0,
                     markersize = 0,
                     elinewidth = 5,
                     alpha = 0.5,
                     label = '_nolegend_'
                     )
    axes[0].plot(bins, y_combined/dx, drawstyle='steps-post', linestyle='--', label='_nolegend_', c='C9')

    ratio_post = y_data/y_combined
    ratio_post_err = (1/y_combined**2)*np.sqrt(y_data**2*yerr_combined**2 + y_combined**2*yerr_data**2)

    axes[0].grid()
    axes[0].set_ylabel(r'Events / 1 GeV')
    axes[0].set_xlim(xmin, xmax)
    if log_scale:
        axes[0].set_yscale('log')
        axes[0].set_ylim(0.05, 10*np.max(y_data/dx))
    else:
        axes[0].set_ylim(0., 1.2*np.max(y_data/dx))

    # custom legend handles
    from matplotlib.legend_handler import HandlerBase

    class AnyObjectHandler(HandlerBase):
        def create_artists(self, legend, orig_handle, x0, y0, width, height, fontsize, trans):
            l1 = plt.Line2D([x0, y0+width],
                            [0.7*height, 0.7*height],
                            linestyle='--',
                            color=orig_handle[1]
                            )
            l2 = plt.Line2D([x0, y0+width],
                            [0.3*height, 0.3*height],
                            color=orig_handle[0]
                            )
            return [l1, l2]

    axes[0].legend([('C1', 'C3'), ('C0', 'C9'), data_plot],
                   ['background', r'$\sf t\bar{t}+tW$', 'data'],
                   handler_map={tuple: AnyObjectHandler()}
                   )

    #axes[0].legend([
    #                r'BG',
    #                r'$\sf t\bar{t}/tW$',
    #                'Data',
    #                ])

    #axes[0].text(80, 2200, r'$\alpha = $' + f' {results.x[0]:3.4} +/- {sig[0]:2.2}', {'size':20})

    ### calculate ratios
    axes[1].errorbar(x, ratio_pre, ratio_pre_err,
                     fmt        = 'C0o',
                     ecolor     = 'C0',
                     capsize    = 0,
                     elinewidth = 3,
                     alpha = 1.
                     )
    axes[1].errorbar(x, ratio_post, ratio_post_err,
                     fmt        = 'C1o',
                     ecolor     = 'C1',
                     capsize    = 0,
                     elinewidth = 3,
                     alpha = 1.
                     )

    axes[1].grid()
    axes[1].set_xlabel(xlabel)
    axes[1].set_ylabel('Data / MC')
    axes[1].set_ylim(0.8, 1.19)
    #axes[1].legend(['prefit', 'postfit'], loc=1, fontsize=16)
    axes[1].plot([xmin, xmax], [1, 1], 'k--', alpha=0.5)

    plt.savefig(f'plots/fits/{selection}_channel.pdf')
    plt.savefig(f'plots/fits/{selection}_channel.png')
    plt.show()
