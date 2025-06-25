"""
Usage: `python run_pbls.py <star_id> <period_grid_chunk_id>`
See docstring for pbls_pipeline.run_pbls for verbose explanation.

Examples:
```
python run_pbls.py "kplr006184894" 42 5000 # Kepler-1627, chunk 5000 times, do 42nd chunk
python run_pbls.py "AU_Mic" 42 100 # Ditto, for AU Mic
```
"""
import sys
from pbls.pbls_chunk_pipeline import run_pbls_chunk

def main():
    star_id = sys.argv[1]
    period_grid_chunk_ix = sys.argv[2]
    run_pbls_chunk(star_id, period_grid_chunk_ix, N_total_chunks)

if __name__ == "__main__":
    main()
