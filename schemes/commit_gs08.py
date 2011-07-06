# Groth-Sahai Commitment Scheme
# 
# From: "J. Groth, A. Sahai.  Efficient Non-interactive Proof Systems for Bilinear Groups".
# Published in: Eurocrypt 2008
# Available from: http://www.cs.ucl.ac.uk/staff/J.Groth/WImoduleFull.pdf
# Notes: This implements only the SXDH and DLIN instantiations, in prime-order groups.
#
# type:			commitment
# setting:		bilinear groups
#
# Implementer:	M Green
# Date:			6/2011

from toolbox.pairinggroup import *
from toolbox.Commitment import *

class Commitment_GS08(Commitment):
    def __init__(self, groupObj, setting='SXDH'):
        Commitment.__init__(self)
        Commitment.setProperty(self, secdef='CM_PHCB', assumption='SXDH', assumption='DLIN', 
                          message_space=[G1, 'KEM'], secmodel='SM')
        global group
        group = groupObj
    
    # Generates commitment parameters for either G1 or G2 (specified by groupChoice).
    # By default this generates the binding commitment parameters.  Set commitType to 'hiding'
    # in order to generate hiding parameters.
    def setup(self, secparam=None, groupChoice=G1, commitType='binding')
        g1, h1 = group.random(groupChoice), group.random(groupChoice)
        s, t = group.random(Zr), group.random(Zr)
        if (commitType == 'binding')
            g2, h2 = g1 ** s, h1 ** s
        else     
            g2, h2 = g1 ** s, h1 ** t
        
        return (g1, g2, h1, h2)
        
    def commit(self, params, msg):
        # TODO: check that the message is in the same group as the params
        (g1, g2, h1, g2) = params
        r1, r2 = group.random(Zr), group.random(Zr)
        
        c1 = (g1 ** r1) * (h1 ** r2)
        c2 = message * (g2 ** r1) * (h2 ** r2)
        
        return ({ 'c1':c1, 'c2':c2 }, { 'r1':r1, 'r2':r2 })
        
    def decommit(self, params, c, d, msg):
        # TODO: check that the message is in the same group as the params
        (g1, g2, h1, g2) = params
        
        if (c['c1'] != ((g1 ** d['r1']) * (h1 ** d['r2'])))
            return false
        
        if ((c['c2'] / msg) != ((g2 ** d['r1']) * (h2 ** d['r2'])))
            return false
        
        return true
        