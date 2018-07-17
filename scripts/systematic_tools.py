
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import scripts.plot_tools as pt
import scripts.fit_helpers as fh

def pileup_morph(df, feature, bins):
    '''
    Generates templates for morphing of distributions due to pileup variance.
    '''

    from scipy.interpolate import interp1d

    pileup_file = open('data/pileup_sf.pkl', 'rb')
    pu_bins     = pickle.load(pileup_file)
    sf_nominal  = interp1d(pu_bins, pickle.load(pileup_file), kind='linear')
    sf_up       = interp1d(pu_bins, pickle.load(pileup_file), kind='linear')
    sf_down     = interp1d(pu_bins, pickle.load(pileup_file), kind='linear')

    df_tmp     = df.query(f'n_pu > {pu_bins.min()} and n_pu < {pu_bins.max()}')
    #w_up       = df_tmp.weight*(sf_up(df_tmp.n_pu)/df_tmp.pileup_weight)
    #w_down     = df_tmp.weight*(sf_down(df_tmp.n_pu)/df_tmp.pileup_weight)
    w_up       = df_tmp.weight*(sf_up(df_tmp.n_pu)/sf_nominal(df_tmp.n_pu))
    w_down     = df_tmp.weight*(sf_down(df_tmp.n_pu)/sf_nominal(df_tmp.n_pu))
    h_up, _      = np.histogram(df_tmp[feature], bins=bins, weights=w_up)
    h_down, _    = np.histogram(df_tmp[feature], bins=bins, weights=w_down)
    h_nominal, _ = np.histogram(df_tmp[feature], bins=bins, weights=df_tmp.weight)
    
    return h_up/h_nominal, h_down/h_nominal
    
def les_morph(df, feature, bins, scale):
    '''
    lepton energy scale morphing
    '''

    h_up, _      = np.histogram((1+scale)*df[feature], bins=bins, weights=df.weight)
    h_down, _    = np.histogram((1-scale)*df[feature], bins=bins, weights=df.weight)
    h_nominal, _ = np.histogram(df[feature], bins=bins, weights=df.weight)

    return h_up/h_nominal, h_down/h_nominal

def jet_scale(df, feature, bins, sys_type, jet_condition):
    '''
    Jet systematics are treated as shape systematics, but mostly vary depending
    on the jet/b tag multiplicity.  Nonetheless, it's easier to account for
    them as a shape systematic.
    '''

    # nominal histogram
    h_nominal, _ = np.histogram(df.query(jet_condition)[feature], bins=bins, weights=df.query(jet_condition).weight)

    # systematic up/down
    up_condition   = jet_condition.replace('n_bjets', f'n_bjets_{sys_type}_up')
    down_condition = jet_condition.replace('n_bjets', f'n_bjets_{sys_type}_down')
    if sys_type not in ['btag', 'mistag']:
        up_condition   = up_condition.replace('n_jets', f'n_jets_{sys_type}_up')
        down_condition = down_condition.replace('n_jets', f'n_jets_{sys_type}_down')

    h_up, _      = np.histogram(df.query(up_condition)[feature], bins=bins, weights=df.query(up_condition).weight)
    h_down, _    = np.histogram(df.query(down_condition)[feature], bins=bins, weights=df.query(down_condition).weight)

    return h_up/h_nominal, h_down/h_nominal

def theory_systematics(df_nominal, dm, feature, bins, sys_type):
    '''
    Theory systematics are handled in two different ways: a subset of the
    systematics are estimated from dedicated samples where a particular
    generator parameter has been scale +/- 1 sigma from the nominal value.
    These indclude,
       * isr
       * fsr
       * ME+PS (hdamp)
       * UE (tune)
    Other systematics are calculated based on event level weights.  These include,
       * PDF
       * alpha_s
       * QCD scale (mu_R and mu_F)
    (It may make more sense to split this into two functions)
    '''

    h_nominal, _ = np.histogram(df_nominal[feature], bins=bins, weights=df_nominal.weight)
    if sys_type in ['isr', 'fsr', 'hdamp', 'tune']:
        df_up     = dm.get_dataframe(f'ttbar_{sys_type}up')
        df_down   = dm.get_dataframe(f'ttbar_{sys_type}down')

        h_up, _   = np.histogram(df_up[feature], bins=bins, weights=df_up.weight)
        h_down, _ = np.histogram(df_down[feature], bins=bins, weights=df_down.weight)
    elif sys_type == 'pdf':
        h_up, _   = np.histogram(df_nominal[feature], bins=bins, weights=df_nominal.weight*(1 + np.sqrt(df_nominal.pdf_var)/np.sqrt(99)))
        h_down, _ = np.histogram(df_nominal[feature], bins=bins, weights=df_nominal.weight*(1 - np.sqrt(df_nominal.pdf_var)/np.sqrt(99)))
    elif sys_type == 'qcd':
        h_up, _   = np.histogram(df_nominal[feature], bins=bins, weights=df_nominal.weight*df_nominal.qcd_weight_up_up)
        h_down, _ = np.histogram(df_nominal[feature], bins=bins, weights=df_nominal.weight*df_nominal.qcd_weight_down_down)

    return h_up/h_nominal, h_down/h_nominal

def template_overlays(h_nominal, h_up, h_down, bins, systematic, selection, feature, jetcat):
    '''
    Overlay nominal, variation up, and variation down templates.
    '''
    fig, axes = plt.subplots(2, 1, figsize=(6, 6), facecolor='white', sharex=False, gridspec_kw={'height_ratios':[3,1]})
    fig.subplots_adjust(hspace=0)

    dx = (bins[1:] - bins[:-1])/2
    x = bins[:-1] + dx

    ax = axes[0]
    ax.plot(x, h_nominal/dx, drawstyle='steps-post', c='C1', linestyle='-', linewidth=1.)
    ax.plot(x, h_up/dx, drawstyle='steps-post', c='C0', linestyle='-', linewidth=1.)
    ax.plot(x, h_down/dx, drawstyle='steps-post', c='C2', linestyle='-', linewidth=1.)
    ax.fill_between(x, h_up/dx, h_down/dx, color = 'C1', alpha=0.5, step='post')

    ax.set_xlim(bins[0], bins[-2])
    ax.set_ylim(0., 1.25*np.max(h_nominal/dx))
    ax.legend(['nominal', r'$+\sigma$', r'$-\sigma$'])
    ax.set_ylabel('Entries / GeV')
    ax.set_title(fh.fancy_labels[selection][1])
    ax.grid()

    ax = axes[1]
    y_up   = h_up/h_nominal
    y_down = h_down/h_nominal
    ax.plot(x, y_up, 'C0', drawstyle='steps-post')
    ax.plot(x, y_down, 'C2', drawstyle='steps-post')
    ax.fill_between(x, y_up, y_down, color = 'C1', alpha=0.5, step='post')
    ax.plot([bins[0], bins[-2]], [1, 1], 'C1--')

    ax.set_xlim(bins[0], bins[-2])
    ax.set_ylim(0.95*np.min([y_up.min(), y_down.min()]), 1.05*np.max([y_up.max(), y_down.max()]))
    ax.set_xlabel(fh.fancy_labels[selection][0])
    ax.set_ylabel(r'$\sf \frac{N^{\pm}}{N^{0}}$', fontsize=14)
    ax.grid()
    #ax.set_yscale('linear')

    plt.tight_layout()
    plt.savefig(f'plots/systematics/{selection}/{systematic}_{jetcat}.pdf')
    plt.savefig(f'plots/systematics/{selection}/{systematic}_{jetcat}.png')
    plt.close()

