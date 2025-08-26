from glob import glob
import pandas as pd, matplotlib.pyplot as plt, numpy as np

csvpaths = glob("cepher_target_vetting/*csv")
df = pd.concat((pd.read_csv(f) for f in csvpaths))

bins = np.arange(0,20.5,0.5)
plt.hist(df.prot_median_days, bins=bins)
plt.savefig('cepher_target_vetting/hist_cepher_prot.png', dpi=300)

df.to_csv("tab_supp_CepHer_X_Kepler_with_Prots.csv", index=False)
