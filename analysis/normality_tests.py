#!/bin/env python

import pandas as pd
from sqlalchemy import create_engine
import scipy.stats as stats
import sys
import pylab
import matplotlib.pyplot as plt

# ---- IMPORT CONSTANTS
UN, PW, H, DB, PORT = "", "", "", "", ""
WRITE_PATH = ""

try:
    from settings import *
    from bias.scripts import trimmed_mean
except ImportError as ex:
    sys.stderr.write("Error: failed to import custom module ({})".format(ex))
    pass

conn = create_engine("postgresql://" + UN + ":" + PW + "@" + H + ":" + PORT + "/" + DB, echo=False)
print("Created engine")

# ---- PULL GOE AND CALCULATE TRIMMED MEAN
goe_sql = """SELECT g.*, c.elt_type 
FROM goe g
LEFT JOIN calls c
  ON g.elt_id = c.elt_id
WHERE g.category = 'Sr';"""
goe_df = pd.read_sql(goe_sql, conn, index_col="line_id")

for disc in ["Men", "Ladies"]:

    disc_df = goe_df.loc[goe_df["discipline"] == disc]

    disc_tmeans = disc_df.groupby(["elt_type", "elt_id"]).apply(trimmed_mean, "goe").reset_index()
    disc_tmeans.rename(columns={0: "trimmed_mean"}, inplace=True)
    disc_tmeans.to_csv(WRITE_PATH + disc + "_goe_means.csv", mode="w", encoding="utf-8", header=True)

    n_tot = disc_tmeans["trimmed_mean"].count()

    print("Sr {0} overall: Shapiro (W, p-value), n = {1}".format(disc, n_tot), stats.shapiro(disc_tmeans["trimmed_mean"]))
    print("Sr {0} overall: KS (W, p-value), n = {1}".format(disc, n_tot), stats.kstest(disc_tmeans["trimmed_mean"]
                                                                                       .astype('float'), 'norm'))
    print("Sr {0} overall: Anderson-Darling (W, critical values, p-value), n = {1}".format(disc, n_tot),
          stats.anderson(disc_tmeans["trimmed_mean"].astype('float'), 'norm'))

    stats.probplot(disc_tmeans["trimmed_mean"].astype('float'), dist="norm", plot=pylab)
    pylab.show()
    plt.hist(disc_tmeans["trimmed_mean"].astype('float'), bins=20, normed=True)
    plt.title("Sr " + disc + ", all elements")
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.show()

    jumps = disc_tmeans.loc[(disc_tmeans["elt_type"] == "jump")]
    n_j = jumps["trimmed_mean"].count()

    print("Sr {0} jumps: Shapiro (W, p-value), n = {1}".format(disc, n_j),
          stats.shapiro(jumps["trimmed_mean"].astype('float')))
    print("Sr {0} jumps: Kolmogorov-Smirnov (W, p-value), n = {1}".format(disc, n_j),
          stats.kstest(jumps["trimmed_mean"].astype('float'), 'norm'))
    print("Sr {0} jumps: Anderson-Darling (W, critical values, p-value), n = {1}".format(disc, n_j),
          stats.anderson(jumps["trimmed_mean"].astype('float'), 'norm'))

    stats.probplot(jumps["trimmed_mean"].astype('float'), dist="norm", plot=pylab)
    pylab.show()
    plt.hist(jumps["trimmed_mean"].astype('float'), bins=20, normed=True)
    plt.title("Sr " + disc + ", jumps")
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.show()

    non_jumps = disc_tmeans.loc[(disc_tmeans["elt_type"] == "non_jump")]
    n_nj = non_jumps["trimmed_mean"].count()

    print("Sr {0} non jumps: Shapiro (W, p-value), n = {1}".format(disc, n_nj),
          stats.shapiro(non_jumps["trimmed_mean"].astype('float')))
    print("Sr {0} non jumps: KS (W, p-value), n = {1}".format(disc, n_nj),
          stats.kstest(non_jumps["trimmed_mean"].astype('float'), 'norm'))
    print("Sr {0} non jumps: Anderson-Darling (W, critical values, p-value), n = {1}".format(disc, n_nj),
          stats.anderson(non_jumps["trimmed_mean"].astype('float'), 'norm'))

    stats.probplot(non_jumps["trimmed_mean"].astype('float'), dist="norm", plot=pylab)
    pylab.show()
    stats.probplot(jumps["trimmed_mean"].astype('float'), dist="norm", plot=pylab)
    pylab.show()
    plt.hist(non_jumps["trimmed_mean"].astype('float'), bins=20, normed=True)
    plt.title("Sr " + disc + ", non jumps")
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.show()