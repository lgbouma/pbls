#!/usr/bin/env python3

import sys
import os

def main():
    star_id = sys.argv[1]
    print(star_id)
    print(42)
    datadir = '/ospool/ap21/data/ekul/pbls_results'
    print(os.listdir(datadir))

if __name__ == "__main__":
    main()

