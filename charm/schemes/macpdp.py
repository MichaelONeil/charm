#!/usr/bin/python3
"""
MAC-PDP is a simple POR scheme based on symmetric key cryptography. 

| Basic construction originally sugested by Naor-Rothblum (FOCS 2005) and 
| Juels-Kaliski (CCS 2007).

:Authors: Krisztina Riebel-Charity and Mark Gondree
:Date:    05/31/2013
"""
from charm.toolbox.pairinggroup import PairingGroup,GT
from charm.core.math.pairing import hashPair as sha1
from charm.core.math.integer import integer,random,randomBits
from charm.core.engine.protocol import *
from charm.toolbox.symcrypto import MessageAuthenticator
from charm.toolbox.RandSubset import RandSubset
from charm.toolbox.POR import PORbase
import sys, math, argparse

def int2bytes(v):
    v, r = divmod(v, 256)
    yield r
    if v == 0:
        raise StopIteration
    for r in int2bytes(v):
        yield r

class MACpdp(PORbase):
    def __init__(self, common_input=None):
        self.fileid = 0
        PORbase.__init__(self, common_input)    

    def set_attributes(self, args):
        """ Sets the following attributes:
        
        :param key_length: Length of secret key.
        :param block_size: Size of blocks.
        :param num_chal_blocks: Number of blocks to challenge per audit.

        Implements :py:func:`POR.PORbase.set_attributes()`
        """
        if hasattr(args, 'key_length'):
            self.mac_key_len = args.key_length
        if hasattr(args, 'block_size'):
            self.block_size = args.block_size
        if hasattr(args, 'num_chal_blocks'):
            self.num_chal_blocks = args.num_chal_blocks
        return None

    def keyGen(self):
        """ Generates a symmetric key *sk* used to tag blocks.

        Implements :py:func:`POR.PORbase.keyGen()`
        """
        k = randomBits(self.mac_key_len)
        sk = {"key":bytes(int2bytes(k))}
        pk = {}
        return (pk, sk)
    
    def tag(self, filename, pk, sk):
        """ Breaks the file into blocks, MACing each block
        with the block number and FID, a unique filename.
        FID is generated by appending a gloablly-unique index to the input
        filename.

        Implements :py:func:`POR.PORbase.tag()`
        """
        tags = []
        m = MessageAuthenticator(sk['key'])
        with open(filename, "rb") as f:
            blocknum = 0;
            datablock = f.read(self.block_size)
            if self.verbose:
                print ("Blocksize:", len(datablock))
            while datablock:
                data = (filename + "_" + str(self.fileid) + " " + 
                        str(blocknum) + " " + str(datablock) + " ")
                sigma = m.mac(data)
                # sigma holds both the MAC and the plaintext data
                tags.append(sigma)
                datablock = f.read(self.block_size)
                if datablock:
                    blocknum += 1
        f.close()
        self.fileid += 1
        filestate = {'num_blocks': blocknum+1}
        data = {'tags': tags}
        return filestate, data

    def generateChallenge(self, filestate, pk, sk):  
        """ Generates a random subset of *m* indices in the 
        range [0, *r*), where *r* is the number of blocks in the file. 
        The value *m* is a scheme parameter, set during initialization.
        The value *r* is stored in *filestate*.

        Implements :py:func:`POR.PORbase.generateChallenge()`
        """
        g = RandSubset()
        c = []
        if filestate['num_blocks'] > self.num_chal_blocks:
            c = g.gen(self.num_chal_blocks, filestate['num_blocks']-1)
        else : 
            c = list(range(filestate['num_blocks']))
        c.sort(key=int)

        if self.verbose:
            print ("Challenging %d blocks:" % (len(c)))
        return c, {}
    
    def generateProof(self, challenge, pk, data):  
        """ Generates a proof, consisting of the tags and blocks associated 
        with the challenged indices.

        Implements :py:func:`POR.PORbase.generateProof()`
        """
        proof = []
        for i in challenge:  
            proof.append(data['tags'][i])
        return proof
    
    def verifyProof(self, proof, challenge, chalData, pk, sk):
        """ Re-computes each MAC and compares with the tag.

        Implements :py:func:`POR.PORbase.verifyProof()`
        """
        m = MessageAuthenticator(sk['key'])
        for i in range (0, len(proof)):  
            if not m.verify(proof[i]):
                return False  
        return True
   
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAC-PDP Scheme")
    parser.add_argument("-v", "--verbose", 
        action="store_true", default=False, 
        dest="verbose", help="Verbose output")
    parser.add_argument("-f", "--filename",
        action="store", dest="file_name", 
        help="Path to file, to store and audit.")
    parser.add_argument("-c", "--challenger",
        action="store_true", default=False, 
        dest="challenger", help="Act as challenger.")
    parser.add_argument("-p", "--prover",
        action="store_true", default=False, 
        dest="prover", help="Act as prover.")

    parser.add_argument("-k", "--key_size",
        action="store", type=int, default=1024, 
        dest="key_length", help="Key length in bits (default, 1024)")
    parser.add_argument("-l", "--num_audits",
        action="store", type=int, default=3, 
        dest="num_of_audits", help="Number of times to audit (default, 3)")
    parser.add_argument("-b", "--block_size",
        action="store", type=int, default=4096, 
        dest="block_size", help="Block size in bytes (default, 4096)")
    parser.add_argument("-n", "--num_challenge_blocks",
        action="store", type=int, default=460, 
        dest="num_chal_blocks", help="Blocks per challenge (default, 460)")
    args = parser.parse_args()

    pdp = MACpdp(None)
    pdp.start(args)
