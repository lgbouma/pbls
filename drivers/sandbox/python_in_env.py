import sys
import os
import pickle

def main():
    star_id = sys.argv[1]
    print(star_id)
    print(42)
    import numpy as np
    print(np.array([42]))
    #datadir = f'/home/ekul/proj/pbls/results'
    print(os.listdir('./'))
    pklpath = './kplr006184894_merged_pbls_periodogram_iter0.pkl'
    with open(pklpath, 'rb') as f:
        d = pickle.load(f)

if __name__ == "__main__":
    main()

