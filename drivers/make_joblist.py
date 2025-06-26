"""
i) Makes list of jobs to pass to condor_submit.sub
ii) Makes directories for where to route results and logs (expected by condor_submit.sub)
"""
import os

####################
# EDIT #
star_id = "kplr006184894" # Kepler-1627
star_id = 'kplr008653134' # Kepler-1643
####################

lines = [f"{star_id},{ix},5000\n" for ix in range(5000)]
joblist_path = "debug_jobs.joblist"
with open(joblist_path, "w") as f:
	f.writelines(lines)
print(f"Created joblist with {len(lines)} entries at {joblist_path}")

res_basedir = '/ospool/ap21/data/ekul/pbls_results'
results_dir = os.path.join(res_basedir, star_id)
if not os.path.exists(results_dir):
	os.makedirs(results_dir)
	print(f"Created results directory: {results_dir}")

log_basedir = '/home/ekul/proj/pbls/drivers/logs'
logs_dir = os.path.join(log_basedir, star_id)
if not os.path.exists(logs_dir):
	os.makedirs(logs_dir)
	print(f"Created logging directory: {logs_dir}")
