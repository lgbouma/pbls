"""
Usage: `python run_pbls.py <star_id> <period_grid_chunk_id> <N_total_chunks> [<iter_ix>]`
See docstring for pbls_pipeline.run_pbls for verbose explanation.

Examples:
```
# Kepler-1627, chunk 5000 times, do 42nd chunk
python run_pbls_chunk.py "kplr006184894" 42 5000

# Kepler-1627, chunk 5000 times, second iteration
python run_pbls_chunk.py "kplr006184894" 42 5000 1

# Ditto, for TOI-837
python run_pbls_chunk.py "TOI-837" 42 1000

# Ditto, for AU Mic
python run_pbls_chunk.py "AU_Mic" 42 100

# Kepler-1627 w/ injection, chunk 5000 times, first iteration
python run_pbls_chunk.py "kplr006184894_inject-P6p941-R10p1-T2p6-E1p234" 42 5000
```
"""
import sys
from pbls.pbls_chunk_pipeline import run_pbls_chunk

def main():
    star_id = sys.argv[1]
    period_grid_chunk_ix = int(sys.argv[2])
    N_total_chunks = int(sys.argv[3])
    if len(sys.argv) < 5:
        iter_ix = 0
    else:
        iter_ix = int(sys.argv[4])

    run_pbls_chunk(star_id, period_grid_chunk_ix, N_total_chunks, iter_ix=iter_ix)

if __name__ == "__main__":
    main()
