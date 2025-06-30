"""
i) Makes list of jobs to pass to condor_submit.sub
ii) Makes directories for where to route results and logs (expected by condor_submit.sub)
"""
import os

####################
# EDIT #
star_id = "kplr006184894" # Kepler-1627
#star_id = 'kplr008653134' # Kepler-1643
####################

lines = [f"{star_id},{ix},5000\n" for ix in range(5000)]
joblist_path = "debug_jobs.joblist"
with open(joblist_path, "w") as f:
	f.writelines(lines)
print(f"Created joblist with {len(lines)} entries at {joblist_path}")

from clean_directories import clean_result_and_log_directories
clean_result_and_log_directories(star_id)