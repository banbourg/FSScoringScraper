#!/bin/env python

import psycopg2


date = '180717'
ver = '1'
conn = psycopg2.connect(database="fsscores_2010", user="cpouletty", password="Ins1d10us",
        host="fsdb.c3ldus0yxoex.eu-west-1.rds.amazonaws.com", port="5432")

cur = conn.cursor()
print 'connected to aws database'

# cur.execute("""
# CREATE TABLE judges_180717(
#     elt_id text PRIMARY KEY,
#     season text,
#     year smallint,
#     event text,
#     sub_event text,
#     discipline text,
#     category text,
#     segment text,
#     role text,
#     judge_name text,
#     country text
#     );
# """)
# print 'created judges table'
# f = open(r'/users/clarapouletty/desktop/bias/output/judges_'+date+ver+'.csv', 'r')
# f.readline()
# cur.copy_from(f, 'judges_180619', sep=',')
# f.close()
# print 'populated judges table'

cur.execute("""
CREATE TABLE elt_scores_180717(
    elt_id text PRIMARY KEY,
    index text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    elt_name text,
    elt_type text,
    level text,
    no_positions text,
    h2 text,
    elt_bv float(1),
    elt_sov_goe float(1),
    elt_total float(1)
    );
UPDATE elt_scores_180717 SET level = cast(nullif(level, '') AS smallint);
UPDATE elt_scores_180717 SET h2 = cast(nullif(h2, '') AS smallint);
""")
print 'created scores table'
f = open(r'/users/clarapouletty/desktop/bias/output/scores_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'elt_scores_180717', sep=',')
f.close()
print 'populated scores table'

cur.execute("""
CREATE TABLE pcs_180717(
    line_id integer PRIMARY KEY,
    component text,
    index text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    judge text,
    pcs float(1)
    );
""")
print 'created pcs table'
f = open(r'/users/clarapouletty/desktop/bias/output/pcs_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'pcs_180717', sep=',')
f.close()
print 'populated pcs table'

cur.execute("""
CREATE TABLE goe_180717(
    line_id integer PRIMARY KEY,
    elt_id text,
    index text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    judge text,
    goe float(1)
    );
UPDATE goe_180717 SET goe = cast(goe AS smallint);
""")
print 'created goe table'
f = open(r'/users/clarapouletty/desktop/bias/output/goe_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'goe_180717', sep=',')
f.close()
print 'populated goe table'

cur.execute("""
CREATE TABLE competitors_180717(
    line_id smallint PRIMARY KEY,
    season text,
    discipline text,
    category text,
    skater_name text,
    country text
    );
""")
print 'created competitors table'
f = open(r'/users/clarapouletty/desktop/bias/output/competitors_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'competitors_180717', sep=',')
f.close()
print 'populated competitors table'

cur.execute("""
CREATE TABLE calls_180717(
    elt_id text PRIMARY KEY,
    index text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    elt_no smallint,
    elt_name text,
    elt_type text,
    level text,
    no_positions text,
    invalid smallint,
    h2 smallint,
    combo_flag smallint,
    seq_flag smallint,
    ur_flag smallint,
    downgrade_flag smallint,
    severe_edge_flag smallint,
    unclear_edge_flag smallint,
    rep_flag smallint,
    jump_1 text,
    j1_sev_edge float(1),
    j1_unc_edge	smallint,
    j1_ur smallint,
    j1_down smallint,
    jump_2 text,
    j2_sev_edge float(1),
    j2_unc_edge	float(1),
    j2_ur float(1),
    j2_down float(1),
    jump_3 text,
    j3_sev_edge float(1),
    j3_unc_edge	float(1),
    j3_ur float(1),
    j3_down float(1),
    jump_4 text,
    j4_sev_edge float(1),
    j4_unc_edge	float(1),
    j4_ur float(1),
    j4_down float(1),
    failed_spin float(1),
    missing_reqs float(1)
    );
UPDATE calls_180717 
  SET j1_sev_edge = cast(j1_sev_edge AS smallint),
  j2_sev_edge = cast(j2_sev_edge AS smallint),
  j2_unc_edge = cast(j2_unc_edge AS smallint),
  j2_ur = cast(j2_ur AS smallint),
  j2_down = cast(j2_down AS smallint),
  j3_sev_edge = cast(j3_sev_edge AS smallint),
  j3_unc_edge = cast(j3_unc_edge AS smallint),
  j3_ur = cast(j3_ur AS smallint),
  j3_down = cast(j3_down AS smallint),
  j4_sev_edge = cast(j4_sev_edge AS smallint),
  j4_unc_edge = cast(j4_unc_edge AS smallint),
  j4_ur = cast(j4_ur AS smallint),
  j4_down = cast(j4_down  AS smallint),
  failed_spin = cast(failed_spin AS smallint),
  missing_reqs = cast(missing_reqs AS smallint)
  ;
""")
print 'created calls table'
f = open(r'/users/clarapouletty/desktop/bias/output/calls_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'calls_180717', sep=',', null='')
f.close()
print 'populated calls table'

cur.execute("""
CREATE TABLE deductions_180717(
    line_id smallint PRIMARY KEY,
    index text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    ded_type text,
    ded_points float(1)
    );
""")
print 'created deductions table'
f = open(r'/users/clarapouletty/desktop/bias/output/deductions_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'deductions_180717', sep=',')
f.close()
print 'populated deductions table'

cur.execute("""
CREATE TABLE total_scores_180717(
    line_id smallint PRIMARY KEY,
    index text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    calc_pcs float(1),
    calc_tes float(1),
    calc_ded float(1),
    calc_total float(1),
    scraped_pcs	float(1),
    scraped_tes	float(1),
    scraped_total float(1),
    scraped_ded float(1),
    pcs_diff float(1),
    tes_diff float(1),
    ded_diff float(1)
    );
""")
print 'created total scores table'
f = open(r'/users/clarapouletty/desktop/bias/output/totalscores_180716'+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'total_scores_180717', sep=',')
f.close()
print 'populated total scores table'


conn.commit()
cur.close()
conn.close()