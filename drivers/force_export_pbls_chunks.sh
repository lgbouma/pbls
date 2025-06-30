# ...if a particular node is stalled and I don't really mind

star_id="kplr006184894" # Kepler-1627
star_id='kplr008653134' # Kepler-1643

result_dir="/ospool/ap21/data/ekul/pbls_results/${star_id}"
pattern="${result_dir}/joboutput_${star_id}*.tar.gz"
remote="luke@wh2.caltech.edu:/ar0/RECEIVING/"

echo "Transferring files to $remote"
rsync -av $pattern "$remote"
echo "Done."
