#!/bin/env python

import pandas as pd
import decimal as dec

DATE, VER = "180728", "1"
READ_PATH = ""
try:
    from settings import *
except ImportError:
    pass

pcs_factors = {"MenSP": "1", "MenFS": "2", "LadiesSP": "0.8", "LadiesFS": "1.6"}

types_dic = {"line_id": int, "component": str, "index": str, "discipline": str, "category": str, "season": str,
             "event": str, "sub_event": str, "skater_name": str, "segment": str, "judge":str, "elt_id": str,
             "elt_name": str, "level": str, "h2": int, "no_positions": str, "elt_type": str}

decs_dic = {"pcs": dec.Decimal, "elt_bv": dec.Decimal, "elt_sov_goe": dec.Decimal, "elt_total": dec.Decimal,
            "scraped_pcs": dec.Decimal, "scraped_tes": dec.Decimal, "scraped_total": dec.Decimal}

key_cols = ["index", "discipline", "category", "season", "event", "sub_event", "skater_name", "segment"]


def decimal_sum(group, source_col):
    s = group[source_col]
    gp_sum = dec.Decimal(s.sum())
    return gp_sum.quantize(dec.Decimal("0.00"))


def trimmed_mean(group, source_col):
    s = group[source_col]
    gp_min = dec.Decimal(s.min())
    gp_max = dec.Decimal(s.max())
    gp_sum = dec.Decimal(s.sum())
    gp_count = s.count()
    mean = dec.Decimal((gp_sum - gp_max - gp_min)/(gp_count - 2))
    return mean.quantize(dec.Decimal("0.00"))


def factoring(row):
    factor = dec.Decimal(pcs_factors[row["discipline"]+row["segment"]])
    factored_mean = dec.Decimal(factor * row["trimmed_mean"])
    return factored_mean.quantize(dec.Decimal("0.00"))


# 1 --- IMPORT PCS TABLE AND BUILD TOTAL FACTORED PCS FOR EACH SKATER
pcs_df = pd.read_csv(READ_PATH + "pcs_" + DATE + VER + ".csv", index_col=0, na_values="", dtype=types_dic,
                     converters=decs_dic)

pcs_tmeans = pcs_df.fillna("None").groupby(key_cols + ["component"]).apply(trimmed_mean, "pcs").reset_index()
pcs_tmeans.rename(columns={0: "trimmed_mean"}, inplace=True)

pcs_tmeans["factored_mean"] = pcs_tmeans.apply(factoring, axis=1)

pcs_totals = pcs_tmeans.groupby(key_cols).apply(decimal_sum, "factored_mean").reset_index()
pcs_totals.rename(columns={0: "factored_pcs"}, inplace=True)

# 2 --- IMPORT ELEMENT SCORES AND BUILT TOTAL TES FOR EACH SKATER
elt_scores_df = pd.read_csv(READ_PATH + "elt_scores_" + DATE + VER + ".csv", index_col=0, na_values="", dtype=types_dic,
                            converters=decs_dic)

elt_totals = elt_scores_df.fillna("None").groupby(key_cols).apply(decimal_sum, "elt_total").reset_index()
elt_totals.rename(columns={0: "tes_total"}, inplace=True)

# 3 --- IMPORT DEDUCTIONS AND BUILD TOTAL DEDUCTIONS FOR EACH SKATER
ded_df = pd.read_csv(READ_PATH + "deductions_" + DATE + VER + ".csv", index_col=0, na_values="", dtype=types_dic,
                     converters=decs_dic)

ded_totals = ded_df.fillna("None").groupby(key_cols)["ded_points"].sum().reset_index()
ded_totals.rename(columns={"ded_points": "ded_total"}, inplace=True)

ded_totals["ded_total"] = ded_totals["ded_total"].map(str) + ".00"
ded_totals["ded_total"] = ded_totals.apply(lambda x: dec.Decimal(x["ded_total"]), axis=1)

# 4 --- JOIN ALL THREE TOTALS, CALCULATE TOTAL SCORE
all_scores = pcs_totals.join(elt_totals.set_index(key_cols), on=key_cols, how="left", lsuffix="_pcs", rsuffix="_tes")
all_scores = all_scores.join(ded_totals.set_index(key_cols), on=key_cols, how="left", lsuffix="_ded", rsuffix="_rest")
all_scores.fillna(0, inplace=True)
print(all_scores.dtypes)

all_scores["total_score"] = all_scores.apply(lambda x: (dec.Decimal(x["factored_pcs"]) + dec.Decimal(x["tes_total"]) +
                                                        dec.Decimal(x["ded_total"])).quantize(dec.Decimal("0.00")),
                                             axis=1)
print(all_scores["total_score"])

# 5 --- IMPORT SCRAPED TOTALS AND CALCULATE IMPLIED DEDUCTIONS
scraped_df = pd.read_csv(READ_PATH + "scraped_totals_" + DATE + VER + ".csv", index_col=0, na_values="", dtype=types_dic,
                         converters=decs_dic)

scraped_df = scraped_df.fillna("None")
scraped_df["scraped_ded"] = scraped_df\
    .apply(lambda x: (dec.Decimal(x["scraped_total"]) - dec.Decimal(x["scraped_tes"]) - dec.Decimal(x["scraped_pcs"]))
           .quantize(dec.Decimal("0.00")), axis=1)

# 6 --- JOIN SCRAPED TO COMPUTED AND COMPARE
scores_diff = all_scores.join(scraped_df.set_index(key_cols), on=key_cols, how="left", lsuffix="_calc",
                              rsuffix="_scrape")

scores_diff["pcs_diff"] = scores_diff.apply(lambda x: (dec.Decimal(x["scraped_pcs"]) - dec.Decimal(x["factored_pcs"]))
                                            .quantize(dec.Decimal("0.00")), axis=1)
scores_diff["tes_diff"] = scores_diff.apply(lambda x: (dec.Decimal(x["scraped_tes"]) - dec.Decimal(x["tes_total"]))
                                            .quantize(dec.Decimal("0.00")), axis=1)
scores_diff["ded_diff"] = scores_diff.apply(lambda x: (dec.Decimal(x["scraped_ded"]) - dec.Decimal(x["ded_total"]))
                                            .quantize(dec.Decimal("0.00")), axis=1)

scores_diff.to_csv(READ_PATH + "total_scores_" + DATE + VER + ".csv", mode="a", encoding="utf-8", header=True)

