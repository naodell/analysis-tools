#!/usr/bin/env python

import numpy as np
import pandas as pd
import ROOT as r

'''
Simple script for getting data out of ROOT files and into CSV format.
'''

if __name__ == '__main__':
    filenames = {
            '1b1f': 'data/amumuFile_MuMu2012ABCD_sasha_54b.root',
            '1b1c': 'data/amumuFile_MuMu2012ABCD_sasha_56b.root',
            '1b0f': 'data/amumuFile_MuMu2012ABCD_sasha_57b.root',
            '1b1c_inclusive': 'data/amumuFile_MuMu2012ABCD_sasha_58b.root'
            }

    rfiles = []

    for cat, name in filenames.iteritems():
        froot   = r.TFile(name)
        tree    = froot.Get('amumuTree_DATA')
        n       = tree.GetEntriesFast()
        ntuple  = {'dimuon_mass':[], 
                'muon1_pt':[], 'muon1_eta':[], 'muon1_phi':[], 
                'muon2_pt':[], 'muon2_eta':[], 'muon2_phi':[], 
                'met_mag':[], 'met_phi':[]
                }
        for i in xrange(n):
            tree.GetEntry(i)
            ntuple['dimuon_mass'].append(tree.x)
            ntuple['muon1_pt'].append(tree.muonOne.Pt())
            ntuple['muon1_eta'].append(tree.muonOne.Eta())
            ntuple['muon1_phi'].append(tree.muonOne.Phi())
            ntuple['muon2_pt'].append(tree.muonTwo.Pt())
            ntuple['muon2_eta'].append(tree.muonTwo.Eta())
            ntuple['muon2_phi'].append(tree.muonTwo.Phi())

            metx, mety = tree.met.Px(), tree.met.Py()
            ntuple['met_mag'].append(np.sqrt(metx**2 + mety**2))
            ntuple['met_phi'].append(np.arctan(mety/metx))

        df = pd.DataFrame(ntuple)
        df.to_csv('data/ntuple_{0}.csv'.format(cat), index=False)