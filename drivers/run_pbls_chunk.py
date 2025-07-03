"""
Usage: `python run_pbls.py <star_id> <period_grid_chunk_id> <N_total_chunks> [<iter_ix>]`
See docstring for pbls_pipeline.run_pbls for verbose explanation.

Examples:
```
python run_pbls_chunk.py "kplr006184894" 42 5000 # Kepler-1627, chunk 5000 times, do 42nd chunk
python run_pbls_chunk.py "kplr006184894" 42 5000 1 # Kepler-1627, chunk 5000 times, second iteration
python run_pbls_chunk.py "TOI-837" 42 1000 # Ditto, for TOI-837
python run_pbls_chunk.py "AU_Mic" 42 100 # Ditto, for AU Mic
```
"""
import sys
from pbls.pbls_chunk_pipeline import run_pbls_chunk

def main():
    star_id = sys.argv[1]
    period_grid_chunk_ix = int(sys.argv[2])
    N_total_chunks = int(sys.argv[3])
    default_iter_ix = 0
    iter_ix = int(sys.argv[4]) if len(sys.argv) > 4 else default_iter_ix

    run_pbls_chunk(star_id, period_grid_chunk_ix, N_total_chunks, iter_ix=iter_ix)

if __name__ == "__main__":
    main()
