#!/bin/env python

import psycopg2


date = '180626'
ver = '1'
conn = psycopg2.connect(database="fsscores_2010", user="cpouletty", password="Ins1d10us",
        host="fsdb.c3ldus0yxoex.eu-west-1.rds.amazonaws.com", port="5432")

cur = conn.cursor()
print 'connected to aws database'

# cur.execute("""
# CREATE TABLE judges_180619(
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
CREATE TABLE elt_scores_180626(
    elt_id text PRIMARY KEY,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    elt_name text,
    level text,
    h2 smallint,
    elt_bv float(1),
    elt_sov_goe float(1),
    elt_total float(1)
    );
""")
print 'created scores table'
f = open(r'/users/clarapouletty/desktop/bias/output/scores_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'elt_scores_180626', sep=',')
f.close()
print 'populated scores table'

cur.execute("""
CREATE TABLE pcs_180626(
    line_id integer PRIMARY KEY,
    component text,
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
cur.copy_from(f, 'pcs_180626', sep=',')
f.close()
print 'populated pcs table'

cur.execute("""
CREATE TABLE goe_180626(
    line_id integer PRIMARY KEY,
    elt_id text,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    judge text,
    goe smallint
    );
""")
print 'created goe table'
f = open(r'/users/clarapouletty/desktop/bias/output/goe_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'goe_180626', sep=',')
f.close()
print 'populated goe table'

# cur.execute("""
# CREATE TABLE competitors_180619(
#     line_id smallint PRIMARY KEY,
#     season text,
#     discipline text,
#     category text,
#     skater_name text,
#     country text
#     );
# """)
# print 'created competitors table'
# f = open(r'/users/clarapouletty/desktop/bias/output/competitors_'+date+ver+'.csv', 'r')
# f.readline()
# cur.copy_from(f, 'competitors_180619', sep=',')
# f.close()
# print 'populated competitors table'
#
cur.execute("""
CREATE TABLE calls_180626(
    elt_id text PRIMARY KEY,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    elt_no smallint,
    elt_name text,
    level text,
    invalid smallint,
    h2 smallint,
    combo_flag smallint,
    ur_flag smallint,
    downgrade_flag smallint,
    severe_edge_flag smallint,
    unclear_edge_flag smallint,
    rep_flag smallint,
    jump_1 text,
    j1_sev_edge smallint,
    j1_unc_edge	smallint,
    j1_ur smallint,
    j1_down smallint,
    jump_2 text,
    j2_sev_edge smallint,
    j2_unc_edge	smallint,
    j2_ur smallint,
    j2_down smallint,
    jump_3 text,
    j3_sev_edge smallint,
    j3_unc_edge	smallint,
    j3_ur smallint,
    j3_down smallint,
    jump_4 text,
    j4_sev_edge smallint,
    j4_unc_edge	smallint,
    j4_ur smallint,
    j4_down smallint,
    failed_spin smallint
    );
""")
print 'created calls table'
f = open(r'/users/clarapouletty/desktop/bias/output/calls_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'calls_180626', sep=',')
f.close()
print 'populated calls table'

cur.execute("""
CREATE TABLE deductions_180626(
    line_id smallint PRIMARY KEY,
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
cur.copy_from(f, 'deductions_180626', sep=',')
f.close()
print 'populated deductions table'

cur.execute("""
CREATE TABLE total_scores_180626(
    line_id smallint PRIMARY KEY,
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
    scraped_ded smallint,
    pcs_diff float(1),
    tes_diff float(1),
    ded_diff float(1) 
    );
""")
print 'created total scores table'
f = open(r'/users/clarapouletty/desktop/bias/output/totalscores_'+date+ver+'.csv', 'r')
f.readline()
cur.copy_from(f, 'total_scores_180626', sep=',')
f.close()
print 'populated deductions table'


conn.commit()
cur.close()
conn.close()