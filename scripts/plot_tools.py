'''
    Tools for creating HEP style plots with bacon pickles :)
'''

import os
from collections import namedtuple

import numpy as np
import pandas as pd
from scipy.stats import beta
import matplotlib.pyplot as plt
plt.ioff()

from tqdm import tqdm
tqdm.monitor_interval = 0

dataset_dict = dict(
                    muon     = ['muon_2016B', 'muon_2016C', 'muon_2016D', 
                                'muon_2016E', 'muon_2016F', 'muon_2016G', 'muon_2016H'],
                    electron = ['electron_2016B', 'electron_2016C', 'electron_2016D', 
                                'electron_2016E', 'electron_2016F', 'electron_2016G', 
                                'electron_2016H'
                                ],
                    ttbar    = ['ttbar_inclusive'], #'ttbar_lep', 'ttbar_semilep',
                    t        = ['t_tw', 'tbar_tw'], #'t_t', 'tbar_t',
                    wjets    = ['w1jets', 'w2jets', 'w3jets', 'w4jets'],
                    zjets_alt = ['zjets_m-50_alt',  'zjets_m-10to50_alt'],
                    zjets    = ['zjets_m-50',  'zjets_m-10to50',
                                'z1jets_m-50', 'z1jets_m-10to50',
                                'z2jets_m-50', 'z2jets_m-10to50',
                                'z3jets_m-50', 'z3jets_m-10to50',
                                'z4jets_m-50', 'z4jets_m-10to50'
                                ],
                    qcd      = ['qcd_ht100to200', 'qcd_ht200to300', 'qcd_ht300to500',
                                'qcd_ht500to1000', 'qcd_ht1000to1500', 'qcd_ht1500to2000',
                                'qcd_ht2000'
                                ],
                    ww_qg    = ['ww_qq', 'ww_gg'],
                    diboson  = ['wz_2l2q', 'wz_3lnu', 'zz_2l2q'], #'zz_4l',
                    fakes    = ['muon_2016B_fakes', 'muon_2016C_fakes', 'muon_2016D_fakes',
                                'muon_2016E_fakes', 'muon_2016F_fakes', 'muon_2016G_fakes',
                                'muon_2016H_fakes'
                                'electron_2016B_fakes', 'electron_2016C_fakes', 'electron_2016D_fakes', 
                                'electron_2016E_fakes', 'electron_2016F_fakes', 'electron_2016G_fakes', 
                                'electron_2016H_fakes'
                                ],
                    fakes_ss = ['fakes_ss']
                    )

selection_dataset_dict = dict(
                              ee    = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson'],
                              mumu  = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson'],
                              emu   = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson', 'fakes_ss'],
                              etau  = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson', 'fakes_ss'],
                              mutau = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson', 'fakes_ss'],
                              e4j   = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson', 'fakes'],
                              mu4j  = ['ttbar', 't', 'zjets_alt', 'wjets', 'ww_qg', 'diboson', 'fakes'],
                              )

cuts = dict(
            ee    = 'lepton1_q != lepton2_q and lepton1_pt > 30 and lepton2_pt > 20 \
                     and dilepton1_mass > 12', 
            mumu  = 'lepton1_q != lepton2_q and lepton1_pt > 25 and lepton2_pt > 10 \
                     and dilepton1_mass > 12',
            emu   = 'lepton1_q != lepton2_q and lepton1_pt > 10 and lepton2_pt > 20 \
                     and dilepton1_mass > 12',
            etau  = 'lepton1_q != lepton2_q and lepton1_pt > 30 and lepton2_pt > 20 \
                     and dilepton1_mass > 12',
            mutau = 'lepton1_q != lepton2_q and lepton1_pt > 25 and lepton2_pt > 20 \
                     and dilepton1_mass > 12',
            e4j   = 'lepton1_pt > 30',
            mu4j  = 'lepton1_pt > 25',
            )

# WIP
tau_dy_cut = '(dilepton1_mass > 40 and dilepton1_mass < 90 \
               and dilepton1_delta_phi > 2.5 and lepton1_mt < 60)'
ll_dy_veto = '(dilepton1_mass > 101 or dilepton1_mass < 81)'
Category = namedtuple('Category', ['cut', 'jet_cut', 'selections', 'label', 'njets'])
categories = dict(
                  #cat_gt2_eq1_a = Category('n_jets >= 2 and n_bjets == 1',                   ['emu', 'etau', 'mutau', 'e4j', 'mu4j'], '$N_{j} \geq 2, N_{b} = 1$'),
                  #cat_gt2_eq1_b = Category(f'n_jets >= 2 and n_bjets == 1 and {ll_dy_veto}', ['ee', 'mumu'], '$N_{j} \geq 2, N_{b} = 1$, Z veto'),
                  #cat_gt2_gt2_a = Category('n_jets >= 2 and n_bjets >= 2',                   ['emu', 'etau', 'mutau', 'e4j', 'mu4j'], '$N_{j} \geq 2, N_{b} \geq 2$'),
                  #cat_gt2_gt2_b = Category(f'n_jets >= 2 and n_bjets >= 2 and {ll_dy_veto}', ['ee', 'mumu'], '$N_{j} \geq 2, N_{b} \geq 2$, Z veto'),

                  cat_gt2_eq0   = Category(None,       'n_jets >= 2 and n_bjets == 0', ['etau', 'mutau', 'ee', 'mumu', 'emu'], '$N_{j} \geq 2, N_{b} = 0$', 2),

                  cat_eq0_eq0   = Category(tau_dy_cut, 'n_jets == 0 and n_bjets == 0', ['etau', 'mutau'],                       '$N_{j} = 0, N_{b} = 0$, W veto',       0),
                  cat_eq1_eq0   = Category(tau_dy_cut, 'n_jets == 1 and n_bjets == 0', ['etau', 'mutau'],                       '$N_{j} = 1, N_{b} = 0$, W veto',       1),
                  cat_eq1_eq1   = Category(None,       'n_jets == 1 and n_bjets == 1', ['etau', 'mutau'],                       '$N_{j} = 1, N_{b} = 1$',               1),
                  cat_eq2_eq1   = Category(None,       'n_jets == 2 and n_bjets == 1', ['etau', 'mutau'],                       '$N_{j} = 2, N_{b} = 1$',               2),
                  cat_gt3_eq1   = Category(None,       'n_jets >= 3 and n_bjets == 1', ['etau', 'mutau'],                       '$N_{j} \geq 3, N_{b} = 1$',            3),
                  cat_eq2_gt2   = Category(None,       'n_jets == 2 and n_bjets >= 2', ['etau', 'mutau'],                       '$N_{j} = 2, N_{b} \geq 2$',            2),
                  cat_gt3_gt2   = Category(None,       'n_jets >= 3 and n_bjets >= 2', ['etau', 'mutau'],                       '$N_{j} \geq 3, N_{b} \geq 2$',         3),

                  cat_eq0_eq0_a = Category(None,       'n_jets == 0 and n_bjets == 0', ['emu'], '$N_{j} = 0, N_{b} = 0$',       0),
                  cat_eq1_eq0_a = Category(None,       'n_jets == 1 and n_bjets == 0', ['emu'], '$N_{j} = 1, N_{b} = 0$',       1),
                  cat_eq1_eq1_a = Category(None,       'n_jets == 1 and n_bjets == 1', ['emu'], '$N_{j} = 1, N_{b} = 1$',       1),
                  cat_gt2_eq1_a = Category(None,       'n_jets >= 2 and n_bjets == 1', ['emu'], '$N_{j} \geq 2, N_{b} = 1$',    2),
                  cat_gt2_gt2_a = Category(None,       'n_jets >= 2 and n_bjets >= 2', ['emu'], '$N_{j} \geq 2, N_{b} \geq 2$', 2),

                  cat_gt2_eq1_b = Category(ll_dy_veto, 'n_jets >= 2 and n_bjets == 1', ['ee',   'mumu'],                        '$N_{j} \geq 2, N_{b} = 1$, Z veto',    2),
                  cat_gt2_gt2_b = Category(ll_dy_veto, 'n_jets >= 2 and n_bjets >= 2', ['ee',   'mumu'],                        '$N_{j} \geq 2, N_{b} \geq 2$, Z veto', 2),

                  cat_gt4_eq1   = Category(None,       'n_jets >= 4 and n_bjets == 1', ['e4j',  'mu4j'],                        '$N_{j} \geq 4, N_{b} = 1$',            4),
                  cat_gt4_gt2   = Category(None,       'n_jets >= 4 and n_bjets >= 2', ['e4j',  'mu4j'],                        '$N_{j} \geq 4, N_{b} \geq 2$',         4),
                 )

def make_directory(file_path, clear=True):
    if not os.path.exists(file_path):
        os.system('mkdir -p '+file_path)

    if clear and len(os.listdir(file_path)) != 0:
        os.system('rm -r '+file_path+'/*')

def calculate_efficiency(num, den, bins, alpha=0.317):
    '''
    Calculates efficiencies given the provided binning and estimates
    uncertainties using the Clopper-Pearson interval construction. 
    
    Parameters:
    ===========
    num: array for numerator (subset of denominator)
    den: array for denominator
    bins: bin edges for histogram
    alpha: confidence interval will correspond to 1 - alpha
    '''
    n, _ = np.histogram(num, bins=bins)
    d, b = np.histogram(den, bins=bins)
    
    x = (b[1:] + b[:-1])/2.
    x_err = (b[1:] - b[:-1])/2.
    eff = n.astype(float)/d
    eff_err = [np.abs(eff - beta.ppf(alpha/2, n, d - n + 1)), 
               np.abs(eff - beta.ppf(1 - alpha/2, n + 1, d - n))]
    
    return x, eff, x_err, eff_err

def hist_to_errorbar(data, bins, normed=False):
    '''
    Wrapper for converting a histogram to data for drawing markers with errorbars.

    Parameters:
    ===========
    data: data to be histogrammed
    bins: histogram binning
    '''
    y, _ = np.histogram(data, bins=bins)
    x = (bins[1:] + bins[:-1])/2.
    yerr = np.sqrt(y)

    return x, y, yerr

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


def ratio_errors(num, sig_num, den, sig_den):
    '''
    Error of ratio assuming numerator and denominator are uncorrelated.

    Parameters:
    ===========
    num : numerator
    num : error on the numerator
    den : denominator
    den : error on the denominator
    '''
    ratio = num/den
    error = ratio*np.sqrt(sig_num**2/num**2 + sig_den**2/den**2)
    return error


def poisson_errors(bin_content, suppress_zero=False):
    '''
    Returns a high and low 1-sigma error bar for an input bin value, as defined
    in: https://www-cdf.fnal.gov/physics/statistics/notes/pois_eb.txt.

    If bin_content > 9, returns the sqrt(bin_content)
    '''
    error_dict = {
        0: (0.000000, 1.000000),
        1: (0.381966, 2.618034),
        2: (1.000000, 4.000000),
        3: (1.697224, 5.302776),
        4: (2.438447, 6.561553),
        5: (3.208712, 7.791288),
        6: (4.000000, 9.000000),
        7: (4.807418, 10.192582),
        8: (5.627719, 11.372281),
        9: (6.458619, 12.541381)}

    if suppress_zero and bin_content == 0:
        return (0, 0)
    elif bin_content in error_dict:
        return error_dict[bin_content]
    else:
        return (np.sqrt(bin_content), np.sqrt(bin_content))


def get_data_and_weights(dataframes, feature, labels, condition):
    data    = []
    weights = []
    for label in labels:
        if label not in dataframes.keys():
            continue

        if condition == '':
            df = dataframes[label]
        else:
            df = dataframes[label].query(condition)
        data.append(df[feature].values)
        weights.append(df['weight'].values)

    return data, weights

def set_default_style():
    import matplotlib
    np.set_printoptions(precision=3)
    matplotlib.style.use('default')
    rc_params = {
                 'figure.figsize': (10, 10),
                 'axes.labelsize': 20,
                 'axes.facecolor': 'white',
                 'axes.titlesize':'x-large',
                 'legend.fontsize': 20,
                 'xtick.labelsize':18,
                 'ytick.labelsize':18,
                 'font.size':18,
                 'font.sans-serif':['Arial', 'sans-serif'],
                 'mathtext.sf':'Arial',
                 'mathtext.fontset':'custom',
                 'mathtext.default':'regular',
                 'lines.markersize':8.,
                 'lines.linewidth':2.5,
                }

    matplotlib.rcParams.update(rc_params)


def add_lumi_text(ax, lumi):
    ax.text(0.03, 1.01, 'CMS', 
            fontsize=25, 
            fontname='Arial',
            fontweight='bold',
            transform=ax.transAxes
            )
    ax.text(0.13, 1.01, 'Preliminary',
            fontsize=15,
            fontname='Arial',
            fontstyle='italic',
            transform=ax.transAxes
            )
    ax.text(0.62, 1.01,
            r'$\mathsf{{ {0:.1f}\,fb^{{-1}}}}\,(\sqrt{{\mathit{{s}}}}=13\,\mathsf{{TeV}})$'.format(lumi),
            fontsize=20,
            fontname='Arial',
            transform=ax.transAxes
            )

def fit_plot(bins, data_val, model_pre, model_post, 
             templates, template_labels,
             model_stat_err, model_syst_err,
             xlabel      = 'x [a.u.]',
             title       = None,
             output_path = 'plots/fits/plot.png',
             show        = False
             ):
    '''
    Produces plot comparing pre/post-fit distributions to fitted data for
    binned likelihood fits.

    Parameters:
    ===========
    '''
    fig, axes = plt.subplots(2, 1, figsize=(10, 12), facecolor='white', sharex=True, gridspec_kw={'height_ratios':[5,2]})
    #fig.subplots_adjust(hspace=0) # doesn't work with tight layout

    # get bin widths and central points
    dx = (bins[1:] - bins[:-1])
    dx = np.append(dx, dx[-1]) 
    x  = bins + dx/2         

    ax = axes[0]

    # unpack model data
    histsum = np.zeros(model_pre.size)
    labels = []
    colors = ['#3182bd', '#6baed6', '#9ecae1', '#c6dbef']
    colors = colors[::-1]
    count = 0
    for label in template_labels[::-1]:
        template = templates[label]
        if label == 'Z':
            color = 'r'
        elif label == 'W':
            color = 'g'
        elif label == 'QCD':
            color = 'C1'
        elif label == 'VV (non-WW)':
            color = 'C5'
        elif 'other' in label:
            color = 'gray'
        else:
            color = colors[count]
            count += 1

        ax.plot(bins, (histsum + template)/dx, 
                drawstyle='steps-post', 
                alpha=0.5,
                color=color, 
                linestyle=':', 
                linewidth=1.5,
                label='_nolegend_'
                )
        ax.fill_between(bins, histsum/dx, (histsum + template)/dx, 
                        step='post',
                        color=color, 
                        alpha=0.8,
                        label=label
                        )
        histsum += template

        if 'tW' in label:
            labels.append(label)

    labels = labels[::-1]
    labels.extend(['W', 'Z', 'VV (non-WW)'])

    # overlay data and model
    ax.errorbar(x, data_val/dx, np.sqrt(data_val)/dx, 
                fmt='ko', 
                markersize=10,
                capsize=0, 
                elinewidth=2, 
                label='data'
                )
    ax.plot(bins, model_pre/dx, 
            drawstyle='steps-post', 
            c='gray', 
            linestyle='--', 
            label='expected (prefit)'
            )
    #ax.plot(bins, model_post/dx,
    #        drawstyle='steps-post',
    #        c='C1',
    #        linestyle='--',
    #        label='expected (postfit)'
    #        )
    ax.fill_between(bins, (model_pre - model_stat_err)/dx, (model_pre + model_stat_err)/dx,
                    color='grey',
                    step='post',
                    hatch='/',
                    alpha=0.2,
                    label=r'$\sigma_{\sf stat. exp.}$'
                    )
    ax.fill_between(bins, model_syst_err[0]/dx, model_syst_err[1]/dx,
                    color='k',
                    step='post',
                    hatch='\\',
                    alpha=0.2,
                    label=r'$\sigma_{\sf syst. exp.}$'
                    )

    ax.set_yscale('log')
    ax.set_ylim(0.1*np.min(data_val/dx), 10.*np.max(data_val/dx))
    ax.set_ylabel('Events / GeV')
    ax.text(0.03, 0.94, title, 
            fontsize=20, 
            fontname='Arial', 
            color='red', 
            transform=ax.transAxes
            )
    add_lumi_text(ax, 35.9)
    ax.legend()
    #ax.legend(labels + [r'$\sigma_{\sf stat.}$', r'$\sigma_{\sf syst.}$', 'Data'])

    ax.grid()

    ax = axes[1]
    ax.plot(bins[[0,-1]], [1, 1], 'k:')

    #ax.errorbar(x, data_val/model_pre, np.sqrt(data_val)/model_pre, 
    ax.errorbar(x*(1-0.01), data_val/model_pre, np.sqrt(data_val)/model_pre, 
                markersize=8,
                fmt='ko', 
                capsize=0, 
                elinewidth=2, 
                label='prefit'
                )
    ax.errorbar(x*(1+0.01), data_val/model_post, np.sqrt(data_val)/model_post, 
                markersize=8,
                fmt='C0o', 
                capsize=0, 
                elinewidth=2, 
                label='postfit'
                )
    ax.plot(bins, model_pre/model_post, drawstyle='steps-post', 
            c='C0', 
            linestyle='--', 
            label='prefit/postfit'
            )
    ax.fill_between(bins, 1 - model_stat_err/model_pre, 1 + model_stat_err/model_pre, 
            color='grey', 
            step='post', 
            hatch='/', 
            alpha=0.2, 
            label='$\sigma_{stat.}$'
            )
    ax.fill_between(bins, model_syst_err[0]/model_pre, model_syst_err[1]/model_pre,
                    color='k',
                    step='post',
                    hatch='\\',
                    alpha=0.2,
                    label=r'$\sigma_{\sf syst. exp.}$'
                    )

    ax.set_xlim(x[0]-dx[0]/2, x[-2]+dx[-2]/2)
    ax.set_ylim(0.5, 1.5)
    ax.set_ylabel('Obs./Exp.')
    ax.set_xlabel(xlabel)
    #ax.legend()
    ax.grid(axis='y')

    plt.tight_layout(h_pad=0., rect=[0., 0., 1., 0.95])
    plt.savefig(output_path)

    if show:
        plt.show()
    else:
        plt.close()

    return

def systematics_plot():
    pass


class DataManager():
    def __init__(self, input_dir, dataset_names, selection,
                 period   = 2016,
                 scale    = 1,
                 cuts     = '',
                 combine  = True,
                 features = None
                 ):
        self._input_dir     = input_dir
        self._dataset_names = dataset_names
        self._selection     = selection
        self._period        = period
        self._scale         = scale
        self._cuts          = cuts
        self._combine       = combine
        self._features      = features
        self._load_luts()
        self._load_dataframes()

    def _load_luts(self):
        '''
        Retrieve look-up tables for datasets and variables
        '''
        self._event_counts = pd.read_csv('{0}/event_counts.csv'.format(self._input_dir, self._selection))
        self._lut_datasets = pd.read_excel('data/plotting_lut.xlsx',
                                           sheet_name='datasets_{0}'.format(self._period),
                                           index_col='dataset_name'
                                          ).dropna(how='all')
        lut_features_default = pd.read_excel('data/plotting_lut.xlsx',
                                             sheet_name='variables',
                                             index_col='variable_name'
                                            ).dropna(how='all')
        lut_features_select = pd.read_excel('data/plotting_lut.xlsx',
                                            sheet_name='variables_{0}'.format(self._selection),
                                            index_col='variable_name'
                                           ).dropna(how='all')
        self._lut_features = pd.concat([lut_features_default, lut_features_select], sort=True)

    def _load_dataframes(self):
        '''
        Get dataframes from input directory.  This method is only for execution
        while initializing the class instance.
        '''
        dataframes = {}
        for dataset in tqdm(self._dataset_names,
                            desc       = 'Loading dataframes',
                            unit_scale = True,
                            ncols      = 75,
                            total      = len(self._dataset_names)
                            ):

            fname = f'{self._input_dir}/ntuple_{dataset}.pkl'
            if not os.path.isfile(fname):
                continue

            df = pd.read_pickle(fname)
            if df.size == 0:
                continue

            ### apply selection cuts ###
            if self._cuts != '':
                df = df.query(self._cuts).copy()

            ### only keep certain features ###
            if self._features is not None:
                df = df[self._features + ['weight']]

            init_count        = self._event_counts[dataset][0]
            lut_entry         = self._lut_datasets.loc[dataset]
            label             = lut_entry.label
            df.loc[:,'label'] = df.shape[0]*[label, ]

            ### update weights with lumi scale factors ###
            if label == 'data':
                df.loc[:, 'weight'] = 1.
            elif label in ['fakes', 'fakes_ss']:
                df.loc[:, 'weight'] *= lut_entry.cross_section
            else:
                scale = self._scale
                scale *= lut_entry.cross_section
                scale *= lut_entry.branching_fraction

                if label == 'zjets_alt':
                    scale *= df.gen_weight
                    neg_count = self._event_counts[dataset][9]
                    scale /= init_count - 2*neg_count
                else:
                    scale /= init_count

                #if dataset == 'ww':
                #    df.loc[:, 'weight'] /= df['ww_pt_weight']

                df.loc[:, 'weight'] *= scale

            ### combined datasets if required ###
            if self._combine:
                if label not in dataframes.keys():
                    dataframes[label] = df
                else:
                    dataframes[label] = dataframes[label].append(df, sort=False)
            else:
                dataframes[dataset] = df
    

        # hack to remove overlapping data; remove when this is fixed upstream :(
        if 'data' in dataframes.keys():
            df = dataframes['data']
            dataframes['data'] = df.drop_duplicates(subset=['run_number', 'event_number'])



        self._dataframes = dataframes

    def get_dataframe(self, dataset_name, condition=''):
        df = self._dataframes[dataset_name]
        if condition != '':
            return df.query(condition)
        else:
            return df

    def get_dataframes(self, dataset_names, concat=False, condition=''):
        dataframes = {}
        for dataset in dataset_names:
            if dataset not in self._dataframes.keys():
                print(f'Can not find {dataset} in datasets.')
                continue

            df = self._dataframes[dataset]
            if condition == '':
                dataframes[dataset] = df
            else:
                dataframes[dataset] = df.query(condition)

        if concat:
            df = pd.concat(list(dataframes.values()), sort=False)
            return df
        else:
            return dataframes

    def get_dataset_names(self):
        return self._dataset_names

    def get_bounds_dict(self):
        df = self._lut_features[['xmin', 'xmax']]
        bdict = df.T.to_dict('list')
        return bdict

    def print_yields(self, dataset_names,
                     exclude    = [],
                     conditions = [''],
                     labels     = None,
                     mc_scale   = True,
                     do_string  = False,
                     output_format = 'csv'
                     ):
        '''
        Prints sum of the weights for the provided datasets

        Parameters
        ==========
        dataset_names : list of datasets to print
        exclude       : list of datasets to exclude from sum background calculation
        conditions    : list of conditions to apply
        mc_scale      : scale MC according to weights and scale
        do_string     : format of output cells: if True then string else float
        output_format : formatting of the table (default:markdown)
        '''

        # print header
        table = dict()
        dataset_names = [dn for dn in dataset_names if dn in self._dataframes.keys()]
        for i, (condition_label, condition) in enumerate(conditions.items()):
            table[f'{condition_label}'] = []
            if not do_string:
                table[f'error_{i+1}'] = []

            bg_total = [0., 0.]
            dataframes = self.get_dataframes(dataset_names, condition = condition)
            for dataset in dataset_names:
                df = dataframes[dataset]
                if condition != '' and condition != 'preselection':
                    df = df.query(condition).copy()

                if mc_scale:
                    n   = df.weight.sum()
                    var_stat = np.sum(df.weight**2)
                    sigma_xs = 0.1 if dataset in ['zjets_alt', 'diboson'] else 0.05
                    var_syst = (sigma_xs**2 + 0.025**2)*n**2
                    err = np.sqrt(var_stat + var_syst)
                    
                else:
                    n   = df.shape[0]
                    err = np.sqrt(n)

                # calculate sum of bg events
                if dataset not in exclude and dataset != 'data':
                    bg_total[0] += n
                    bg_total[1] += err**2

                if do_string:
                    if dataset == 'data':
                        table[f'{condition_label}'].append('${0}$'.format(int(n)))
                    else:
                        table[f'{condition_label}'].append('${0:.1f} \pm {1:.1f}$'.format(n, err))
                else:
                    table[f'{condition_label}'].append(n)
                    table[f'error_{i+1}'].append(err)

                dataframes[dataset] = df  # update dataframes so cuts are applied sequentially

            if do_string:
                table[f'{condition_label}'].append('${0:.1f} \pm {1:.1f}$'.format(bg_total[0], np.sqrt(bg_total[1])))
            else:
                table[f'{condition_label}'].append(bg_total[0])
                table[f'error_{i+1}'].append(np.sqrt(bg_total[1]))

        if do_string:
            labels = [self._lut_datasets.loc[d].text for d in dataset_names]
        else:
            labels = dataset_names

        table = pd.DataFrame(table, index=labels+['background'])
        return table


class PlotManager():
    def __init__(self, data_manager, features, stack_labels, 
                 overlay_labels = [],
                 top_overlay    = False,
                 output_path    = 'plots',
                 file_ext       = 'png'
                 ):
        # required
        self._dm             = data_manager
        self._features       = features
        self._stack_labels   = [l for l in stack_labels if l in data_manager._dataframes.keys()]

        # optional
        self._overlay_labels = overlay_labels
        self._top_overlay    = top_overlay
        self._output_path    = output_path
        self._file_ext       = file_ext
        self._initialize_colors()

    def set_output_path(self, new_path):
        self._output_path = new_path

    def _initialize_colors(self):
        lut = self._dm._lut_datasets
        self._stack_colors   = [lut.loc[l].color for l in self._stack_labels]
        self._overlay_colors = [lut.loc[l].color for l in self._overlay_labels]

    def make_overlays(self, features,
                      plot_data     = True,
                      do_ratio      = True,
                      do_cms_text   = True,
                      normed        = False,
                      ):
        dm = self._dm
        make_directory(self._output_path)

        ### alias dataframes and datasets lut###
        dataframes   = dm._dataframes
        lut_datasets = dm._lut_datasets

        ### initialize legend text ###
        legend_text = []
        legend_text.extend([lut_datasets.loc[label].text for label in self._stack_labels[::-1]])

        if len(self._stack_labels) > 0:
            legend_text.append('BG error')

        if plot_data:
            legend_text.append('Data')

        for feature in tqdm(features, 
                            desc='plotting...', 
                            unit_scale=True, 
                            ncols=75, 
                            total=len(features)
                            ):
            if feature not in self._features:
                print('{0} not in features.')
                continue

            ### Get style data for the feature ###
            lut_entry = dm._lut_features.loc[feature]
            cut = lut_entry.condition if lut_entry.condition != 'None' else ''

            ### initialize figure ###
            if do_ratio:
                fig, axes = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={'height_ratios':[3,1]})
                fig.subplots_adjust(hspace=0)
                ax = axes[0]
            else:
                fig, ax = plt.subplots(1, 1)

            ### Get stack data and apply mask if necessary ###
            binning = np.linspace(lut_entry.xmin, lut_entry.xmax, lut_entry.n_bins+1)
            stack_data, stack_weights = get_data_and_weights(dataframes, feature, self._stack_labels, cut)
            stack, _, _ = ax.hist(stack_data, 
                                  bins      = binning,
                                  color     = self._stack_colors,
                                  alpha     = 1.,
                                  linewidth = 1.,
                                  stacked   = True,
                                  histtype  = 'stepfilled',
                                  weights   = stack_weights
                                 )

            ### Need to histogram the stack with the square of the weights to get the errors ### 
            stack_var, _ = np.histogram(np.concatenate(stack_data),
                                            bins    = binning,
                                            weights = np.concatenate(stack_weights)**2
                                           )

            stack_x   = (binning[1:] + binning[:-1])/2.
            stack_sum = stack[-1] if len(stack_data) > 1 else stack
            stack_err = np.sqrt(stack_var)

            ax.fill_between(stack_x, stack_sum-stack_err, stack_sum+stack_err,
                            color = 'k',
                            step = 'mid',
                            alpha = 0.25,
                            label = 'MC error',
                           )

            denominator = (stack_sum, stack_err)

            ### Get overlay data and apply mask if necessary ###
            if len(self._overlay_labels) > 0:
                overlay_data, overlay_weights = get_data_and_weights(dataframes, feature, self._overlay_labels, cut)
                hists, _, _ = ax.hist(overlay_data,
                                         bins      = binning,
                                         color     = self._overlay_colors,
                                         alpha     = 1.,
                                         histtype  = 'step',
                                         linewidth = 2.,
                                         normed    = normed,
                                         bottom    = 0 if y_max == 0 or not self._top_overlay else stack[-1],
                                         weights   = overlay_weights
                                        )


            ### If there's data to overlay: apply feature condition and get
            ### datapoints plus errors
            if plot_data:
                data, _ = get_data_and_weights(dataframes, feature, ['data'], cut)
                x, y, yerr = hist_to_errorbar(data, binning)
                numerator = (y, yerr)

                x, y, yerr = x[y>0], y[y>0], yerr[y>0]
                eb = ax.errorbar(x, y, yerr=yerr, 
                              fmt        = 'ko',
                              capsize    = 0,
                              elinewidth = 2
                             )

            ### make the legend ###
            ax.legend(legend_text, loc=1)

            ax.set_ylabel(r'$\sf {0}$'.format(lut_entry.y_label))
            ax.set_xlim((lut_entry.xmin, lut_entry.xmax))
            ax.grid()

            ### Add lumi text ###
            if do_cms_text:
                add_lumi_text(ax, dm._scale/1000)

            ### labels and x limits ###
            if do_ratio:
                ax_ratio = axes[1]
                ax_ratio.set_xlabel(r'$\sf {0}$'.format(lut_entry.x_label))
                ax_ratio.set_ylabel(r'Data/MC')
                ax_ratio.set_ylim((0.5, 1.49))
                ax_ratio.grid()

                ### calculate ratios 
                mask = (numerator[0] > 0) & (denominator[0] > 0)
                num_val   = numerator[0][mask]
                num_err   = numerator[1][mask]
                denom_val = denominator[0][mask]
                denom_err = denominator[1][mask]

                ratio = num_val/denom_val
                error = ratio*np.sqrt(num_err**2/num_val**2 + denom_err**2/denom_val**2)
                ax_ratio.errorbar(stack_x[mask], ratio, yerr=error,
                            fmt = 'ko',
                            capsize = 0,
                            elinewidth = 2
                           )
                ax_ratio.plot([lut_entry.xmin, lut_entry.xmax], [1., 1.], 'r--')
            else:
                ax.set_xlabel(r'$\sf {0}$'.format(lut_entry.x_label))

            ### Make output directory if it does not exist ###
            make_directory('{0}/linear/{1}'.format(self._output_path, lut_entry.category), False)
            make_directory('{0}/log/{1}'.format(self._output_path, lut_entry.category), False)

            ### Save output plot ###
            plt.tight_layout(h_pad=0., rect=[0., 0., 1., 0.95])

            ### linear scale ###
            ymax, ymin = np.max(stack_sum), np.min(stack_sum)
            ax.set_ylim((0., 1.5*ymax))
            fig.savefig('{0}/linear/{1}/{2}.{3}'.format(self._output_path, 
                                                        lut_entry.category, 
                                                        feature, 
                                                        self._file_ext
                                                       ))

            ### log scale ###
            ax.set_yscale('log')
            ax.set_ylim(np.max([0.1, ymin]), 15.*ymax)
            fig.savefig('{0}/log/{1}/{2}.{3}'.format(self._output_path,
                                                     lut_entry.category,
                                                     feature,
                                                     self._file_ext
                                                     ))

            fig.clear()
            plt.close()

    def make_sideband_overlays(self, label, cuts, features,
                               do_cms_text = True,
                               do_stacked  = False
                               ):

        ### alias dataframes and datasets lut###
        df_pre = self._dm.get_dataframe(label)
        df_sr  = df_pre.query(cuts[0])
        df_sb  = df_pre.query(cuts[1])
        for feature in tqdm(features, 
                            desc       = 'Plotting',
                            unit_scale = True,
                            ncols      = 75,
                            total      = len(features
                           )):
            if feature not in self._features:
                print('{0} not in features.')
                continue

            fig, ax = plt.subplots(1, 1)
            lut_entry = self._dm._lut_features.loc[feature]
            x_sr = df_sr[feature].values
            x_sb = df_sb[feature].values
            hist, bins, _ = ax.hist([x_sr, x_sb],
                                    bins      = lut_entry.n_bins,
                                    range     = (lut_entry.xmin, lut_entry.xmax),
                                    color     = ['k', 'r'],
                                    alpha     = 0.9,
                                    histtype  = 'step',
                                    linewidth = 2.,
                                    normed    = True,
                                    stacked   = do_stacked
                                   )

            ### make the legend ###
            #legend_text = cuts # Need to do something with this
            legend_text = [r'$\sf M_{\mu\mu}\,\notin\,[24,33]$', r'$\sf M_{\mu\mu}\,\in\,[24, 33]$']
            ax.legend(legend_text)

            ### labels and x limits ###
            ax.set_xlabel(r'$\sf {0}$'.format(lut_entry.x_label))
            ax.set_ylabel(r'$\sf {0}$'.format(lut_entry.y_label))
            ax.set_xlim((lut_entry.xmin, lut_entry.xmax))
            ax.grid()

            ### Add lumi text ###
            #if do_cms_text:
            #    add_lumi_text(ax, dm._scale, dm._period)

            ### Make output directory if it does not exist ###
            make_directory('{0}/linear/{1}'.format(self._output_path, lut_entry.category), False)
            make_directory('{0}/log/{1}'.format(self._output_path, lut_entry.category), False)

            ### Save output plot ###
            ### linear scale ###
            ymax, ymin = np.max(hist), np.min(hist)
            ax.set_ylim((0., 1.5*ymax))
            fig.savefig('{0}/linear/{1}/{2}.{3}'.format(self._output_path, 
                                                        lut_entry.category, 
                                                        feature, 
                                                        self._file_ext
                                                       ))

            ### log scale ###
            ax.set_yscale('log')
            ax.set_ylim(np.max([0.1, ymin]), 15.*ymax)
            fig.savefig('{0}/log/{1}/{2}.{3}'.format(self._output_path, 
                                                     lut_entry.category, 
                                                     feature, 
                                                     self._file_ext
                                                    ))
            fig.clear()
            plt.close()


    def make_conditional_overlays(self, features, labels, conditions, legend, c_colors,     
                                  cut = '', 
                                  aux_labels  = [], 
                                  do_data     = True,
                                  do_ratio    = True,
                                  do_stacked  = True,
                                  do_cms_text = False
                                 ):
        '''
        Make overlays while combining and redividing samples based on
        conditional input.  For example, two samples can be combined into a
        single sample that can be successively split based on a list of
        conditions.
        '''

        # start with auxiliary samples
        df_model = [self._dm.get_dataframe(l, cut) for l in aux_labels]

        # combine target datasets and split on conditions
        df_combined = self._dm.get_dataframes(labels, concat=True, condition=cut)
        df_combined = [df_combined.query(c) for c in conditions]
        sort_ix = np.argsort([df.shape[0] for df in df_combined])
        df_model.extend([df_combined[ix] for ix in sort_ix])

        if do_data:
            df_data = self._dm.get_dataframe('data', condition=cut)

        # initialize legend text
        legend_text = [self._dm._lut_datasets.loc[l].text for l in aux_labels]
        legend_text.extend([legend[ix] for ix in sort_ix])

        # get colors
        colors = [self._dm._lut_datasets.loc[l].color for l in aux_labels]
        colors.extend([c_colors[ix] for ix in sort_ix])

        for feature in tqdm(features, 
                            desc       = 'plotting...',
                            unit_scale = True,
                            ncols      = 75,
                            total      = len(features)
                            ):
            if feature not in self._features:
                print('{0} not in features.')
                continue


            ### initialize figure ###
            if do_ratio:
                fig, axes = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={'height_ratios':[3,1]})
                fig.subplots_adjust(hspace=0)
                ax = axes[0]
            else:
                fig, ax   = plt.subplots(1, 1, figsize=(10, 7))

            lut_entry = self._dm._lut_features.loc[feature]
            hist_data = [df[feature].values for df in df_model]
            weights   = [df['weight'].values for df in df_model]
            hist, bins, _ = ax.hist(hist_data,
                                    bins      = int(lut_entry.n_bins),
                                    range     = (lut_entry.xmin, lut_entry.xmax),
                                    color     = colors,
                                    alpha     = 0.9,
                                    histtype  = 'stepfilled' if do_stacked else 'step',
                                    linewidth = 2.,
                                    weights   = weights,
                                    stacked   = True
                                   )

            # calculate variance for each bin
            hvar, _ = np.histogram(np.concatenate(hist_data),
                                   bins    = bins,
                                   weights = np.concatenate(weights)**2
                                  ) 
            x = bins[:-1]
            herr = np.sqrt(hvar)
            ax.fill_between(x, hist[-1]-herr, hist[-1]+herr,
                            color = 'k',
                            step = 'post',
                            alpha = 0.25,
                            label = 'MC error',
                            )

            if do_ratio:
                denominator = (x, hist[-1], herr)

            if do_data:
                x, y, yerr = hist_to_errorbar(df_data[feature], bins)
                if do_ratio:
                    numerator = (x, y, yerr)

                x, y, yerr = x[y>0], y[y>0], yerr[y>0]
                eb = ax.errorbar(x, y, yerr=yerr, 
                              fmt        = 'ko',
                              capsize    = 0,
                              elinewidth = 2
                             )

            ### make the legend ###
            #legend_text = cuts # Need to do something with this
            ax.legend(legend_text[::-1] + ['MC error', 'data'], loc=1)

            ### labels and x limits ###
            ax.set_ylabel(r'$\sf {0}$'.format(lut_entry.y_label))
            ax.set_xlim((lut_entry.xmin, lut_entry.xmax))
            ax.grid()

            ### labels and x limits ###
            if do_ratio and do_data:
                ### calculate ratios 
                mask = (numerator[1] > 0) & (denominator[1] > 0)
                 
                ratio = numerator[1][mask]/denominator[1][mask]
                error = ratio*np.sqrt(numerator[2][mask]**2/numerator[1][mask]**2 + denominator[2][mask]**2/denominator[1][mask]**2)
                axes[1].errorbar(numerator[0][mask], ratio, yerr=error,
                                 fmt = 'ko',
                                 capsize = 0,
                                 elinewidth = 2
                                )
                axes[1].plot([lut_entry.xmin, lut_entry.xmax], [1., 1.], 'r--')
                axes[1].set_xlabel(r'$\sf {0}$'.format(lut_entry.x_label))
                axes[1].set_ylabel(r'Data/MC')
                axes[1].set_ylim((0.5, 1.49))
                axes[1].grid()

            else:
                ax.set_xlabel(r'$\sf {0}$'.format(lut_entry.x_label))


            ### Add lumi text ###
            if do_cms_text:
                add_lumi_text(ax, self._dm._scale/1000)

            ### Make output directory if it does not exist ###
            make_directory(f'{self._output_path}/linear/{lut_entry.category}', False)
            make_directory(f'{self._output_path}/log/{lut_entry.category}', False)

            ### Save output plot ###
            plt.tight_layout()
            fig.subplots_adjust(top=0.94)

            ### linear scale ###
            ymax, ymin = np.max(hist), np.min(hist)
            ax.set_ylim((0., 1.5*ymax))
            fig.savefig('{0}/linear/{1}/{2}.{3}'.format(self._output_path, 
                                                        lut_entry.category, 
                                                        feature, 
                                                        self._file_ext
                                                       ))

            ### log scale ###
            ax.set_yscale('log')
            ax.set_ylim(np.max([0.1, ymin]), 15.*ymax)
            fig.savefig('{0}/log/{1}/{2}.{3}'.format(self._output_path, 
                                                     lut_entry.category, 
                                                     feature, 
                                                     self._file_ext
                                                    ))
            fig.clear()
            plt.close()
