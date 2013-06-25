#!/usr/bin/python3
"""
CPOR with Private Verificability

| From paper: Compact Proofs of Retrievavility
| Published in: ASIACRYPT 2005

:Authors: 
:Date:    
""" 
from charm.toolbox.pairinggroup import PairingGroup, GT 
from charm.core.math.pairing import hashPair as sha1 
from charm.core.math.integer import integer,randomBits,randomPrime 
from charm.core.math.integer import random as charm_random
from charm.core.engine.protocol import * 
from charm.toolbox.symcrypto import MessageAuthenticator 
from charm.toolbox.RandSubset import RandSubset 
from charm.toolbox.POR import PORbase 
from charm.core.crypto.cryptobase import selectPRF,AES,MODE_ECB
from charm.toolbox.paddingschemes import PKCS7Padding
import sys, math, argparse, random

def int2bytes(v):
    v, r = divmod(v, 256)
    yield r
    if v == 0:
        raise StopIteration
    for r in int2bytes(v):
        yield r

def prf_generator(num, prf, prime):
    padding = PKCS7Padding(block_size = 16)
    byte_val = int2bytes(int(num))
    function = prf.encrypt(padding.encode(bytes(bytes(byte_val))))
    sized = function[:len(str(prime))]
    return int.from_bytes(sized, byteorder='big')

class CPORpriv (PORbase):
  def __init__(self, common_input = None):
    self.enc_key_len = 1024
    self.mac_key_len = 1024
    self.prf_key_len = 256
    self.block_size = 4096
    self.num_challenge_blocks = 512
    self.lambda_size = 80
    self.sector_size = (self.lambda_size - 1) / 8
    self.prime = randomPrime(self.lambda_size, 1)
    PORbase.__init__(self, common_input)

  def set_attributes(self, args):
    """ 
    Implements :py:func:`POR.PORbase.set_attributes()`
    """ 
    if hasattr(args, 'mac_length'):
        self.mac_key_len = args.mac_length 
    if hasattr(args, 'enc_length'):
        self.enc_key_len = args.enc_length 
    if hasattr(args, 'prf_length'):
        self.prf_key_len = args.prf_length
    if hasattr(args, 'block_size'):
        self.block_size = args.block_size
        print("Blocksize:", self.block_size)
    if hasattr(args, 'num_chal_blocks'):
        self.num_challenge_blocks = args.num_chal_blocks
        print("Challenging", self.num_challenge_blocks, "blocks:")
    return None 

  def keyGen(self):
    """ 
    Chooses a random symmetric encryption key, and a random MAC key, and combines them
    to create the secret key. No public key.

    Implements :py:func:`POR.PORbase.keyGen()`
    """ 
    pk, sk = dict(), dict()
    print("Generating MAC key...")
    k = randomBits(self.mac_key_len) 
    sk["kmac"] = bytes(int2bytes (k))
    print("Generating Encryption key...") 
    k = randomBits(self.enc_key_len) 
    sk["kenc"] = bytes(int2bytes(k)) 
    return (pk, sk) 

  def tag (self, filename, pk, sk):
    """ 
    Erasure Codes the file, breaks the file into n blocks, each s sectors long.
    Then a PRF key is chosen along with s random numbers, where s in prime.
    t0 is n concatinated with the  encryption, using the random enc key, of the random s numbers after the PRF key is applied to them. 
    The tag is t0 concated with the MAC, using the MAC key, of (t0).
    For each i, or each block, a sigman is calculated using the PRF key on i which is concated with  all the random number of the sector, times the message sector&block
    formula: sigma[i]=Fk(i) + for j = 1, j <=s, j++: alpha[j]*message[i][j], where k = PRF key, F= some function, s = the total amount of random numbers, i = block id, j = sector id
    M* = {mij}, 1<= i <= n, 1 <= j <= s processed with {sigman[i]}
    
    Implements :py:func:`POR.PORbase.tag()`
    """
    # the number of sectors in a block
    num_sectors = int(self.block_size // self.sector_size)
    if (self.block_size % self.sector_size is not 0):
        num_sectors += 1


    f = open(filename, 'rb')
    message = f.read()
    f.close()

    
    #TODO: this is where we would transform via erasure-code in future
    Mprime = len(message) 

    print("Determining the number of blocks in the file...")
    num_blocks = Mprime // self.block_size
    if (Mprime % self.block_size is not 0):
        num_blocks += 1 

    m = [[] for i in range(int(num_blocks))]

    print("Storing file blocks by sectors...")
    # Opening the file and storing the message.
    with open(filename, "rb") as f:
        block = f.read(self.block_size)
        i = 0
        while block:
            # parse out the sectors
            sectors = bytearray(block) 
            for j in range(int(num_sectors)):
                jstart = j * self.sector_size 
                jend = jstart + min(self.sector_size - 1, len (sectors) - jstart) 
                m[i].append(bytes(sectors[int(jstart):int(jend)]))
            block = f.read(self.block_size)
            i = i + 1
    
    
    #
    # make the tags:
    # For a stateless verifier, we can store E(kenc; <kprf, alpha>) and MAC(kmac; <num_blocks, ctx>)
    # and store these with the prover;
    # For simplicity, we skip this and store these privately in local state
    # to ensure Prover-Verifier interaction is a Sigma protocol
    #
    print("Generating Pseudo Random Function key...")
    kbits = randomBits(self.prf_key_len) 
    kprf = bytes(int2bytes(kbits)) # a random PRF key
    
    print("Generating Pseudo Random Function...")
    prf = selectPRF(AES,(kprf, MODE_ECB))
   
    print("Generating alphas...")
    alpha = [int(integer(charm_random(self.prime))) for i in range(num_sectors)] # a list of random numbers from Zp, |alpha| = num_sectors

    filestate = {}
    filestate["num_blocks"] = num_blocks
    filestate["kprf"] = kprf 
    filestate["alpha"] = alpha
    #
    # generate the sigmas
    #
    sigmas =[] # for each block, a sigma is generated with a function using PRFkey on each block, adding the product of all the alphas, and the sectors
    for i in range(num_blocks):
        am = [alpha[j] * int.from_bytes(m[i][j], byteorder='big') for j in range(len(m[i]))]
        fkprf = prf_generator((i+1), prf, self.prime)
        s = fkprf + sum(am) 
        sigmas.append(s) 
    
    data = {}
    data["data"] = m 
    data["sigmas"] = sigmas 
    return (filestate, data) 

  def generateChallenge(self, filestate, pk, sk):
    """
    Take the sk and use the kmac to verify the MAC on the tag. If invalid abort.
    If not aborted, use kenc on the tag to decrypt the ecnrypted PRF key and the random numbers. 
    Pick a random element, from 1 to num_blocks, and for each(i) add a random element nu, creating the set Q{(i,nui)}
    send Q to the prover.
    Implements :py:func:`POR.PORbase.generateChallenge()`
    """
    #
    # Need to unpack num_blocks, and the encrypted kprf, and alphas to check MAC in packed tag
    #
    print("Generating Challenge...")
    g = RandSubset()
    num_blocks = filestate["num_blocks"]
    kprf = filestate["kprf"]
    alpha = filestate["alpha"]

    if(num_blocks < self.num_challenge_blocks):
        challenge = num_blocks
    else:
        challenge = self.num_challenge_blocks
    check_set = g.gen(challenge, (num_blocks - 1))
    # picks a random amount of blocks to check, making sure the amount of blocks
    # picked are within the num_block range
    NU =[int(integer(charm_random(self.prime))) for i in range(len(check_set))]

    Q = dict() # set of group of check_set and their corresponding NU values

    for x in range(len(check_set)):
        Q[check_set[x]] = NU[x] 

    challenge = Q 
    chalData = {}
    chalData["kprf"] = kprf 
    chalData["alpha"] = alpha 
    return(challenge, chalData) 

  def generateProof(self, challenge, pk, data):
    """
    Take the processed file m[][], along with sigma and Q.
    Compute the mu values and sigma value.
    mu for each sector is obtained by multiplying each nui to the same sector in each block.
    the signma value is obtained by the multiplication of the nui and sigma[i] added together with the other blocks value.
    these values are sent back to the verifier  
    Implements :py:func:`POR.PORbase.generateProof()`
    """
    print("Generating Proof...")
    m = data["data"]
    Q = challenge
    sigmas = data["sigmas"]
    MU = {}
    for j in range(len(m[0])):
        add = []
        for i in Q:
            add.append(Q[i] * int.from_bytes(m[i][j], byteorder='big'))
        MU[j] = sum(add)

    final_sigma =[Q[i] * sigmas[i] for i in Q]
    final_sigma = sum(final_sigma) 
    p = {}
    p["MU"] = MU 
    p["final_sigma"] = final_sigma 
    p["data"] = m
    return p 

  def verifyProof(self, proof, challenge, chalData, pk, sk):
    """
    Parse the results obtained from the proover to obtain the mus and sigma
    if parsing fails, then abort
    If no abort then check if the sigma value is correct
    This is done by: concatinating the sum of (the nus for each block multiplied by the PRF of the block) and (the sum of the mus for each sector multiplied by the random number for the sector)
    If these values match the sigma returned from the proover then all is good, otherwise abort.
    Implements :py:func:`POR.PORbase.verifyProof()`
    """ 
    print("Verifying Proof...")
    MU = proof["MU"]
    final_sigma = proof["final_sigma"]
    kprf = chalData["kprf"]
    alpha = chalData["alpha"]
    m = proof["data"]
    Q = challenge
    if not MU:
        return False
    else:
        prf = selectPRF(AES,(kprf, MODE_ECB)) 
        temp1 = [Q[i] * prf_generator((i+1), prf, self.prime) for i in Q]
        temp2 = [alpha[j] * MU[j] for j in range(len(m[0]))]
        check = sum(temp1) + sum(temp2) 

        if check == final_sigma:
            return True
        else:
            return False 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description ="CPOR-Priv Scheme")
    parser.add_argument("-v", "--verbose", action ="store_true", 
                        default=False, dest="verbose", 
                        help = "Verbose output") 
    parser.add_argument("-f", "--filename", action = "store", 
                        dest = "file_name",
                        help = "Path to file, to store and audit.")
    parser.add_argument("-c", "--challenger", action = "store_true", 
                        default = False,
                        dest = "challenger", 
                        help = "Act as challenger.")
    parser.add_argument("-p", "--prover", action = "store_true", 
                        default = False, dest = "prover", 
                        help = "Act as prover.") 
    parser.add_argument("-l", "--num_audits",
                        action="store", type=int, 
                        default = 3, dest="num_of_audits", 
                        help = "Number of times to audit (default, 3)")
    parser.add_argument("-b", "--block_size",
                        action="store", type = int, 
                        default = 4096, dest="block_size", 
                        help ="Block size in bytes (default, 4096)")
    parser.add_argument("-n", "--num_challenge_blocks",
                        action="store", type=int, default=512,
                        dest="num_chal_blocks", help="Blocks per challenge (default, 512)")
    args = parser.parse_args()
    pdp = CPORpriv(None) 
    pdp.start(args)
