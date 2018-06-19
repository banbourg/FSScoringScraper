import psycopg2
import os

#conn = psycopg2.connect("host=localhost dbname=fs_scores user=clarapouletty")
conn = psycopg2.connect(database="fsscores_2010", user="cpouletty", password="Ins1d10us",
        host="fsdb.c3ldus0yxoex.eu-west-1.rds.amazonaws.com", port="5432")
#sslmode='verify-full',connect_timeout=10, sslrootcert = 'rds-combined-ca-bundle.pem')

cur = conn.cursor()
print 'connected to aws database'

# cur.execute("DROP TABLE judges_180619")
# cur.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")

cur.execute("""
CREATE TABLE judges_180619(
    elt_id text PRIMARY KEY,
    season text,
    year integer,
    event text,
    sub_event text,
    discipline text,
    category text,
    segment text,
    role text,
    judge_name text,
    country text
    );
""")
print 'created judges table'
f = open(r'/users/clarapouletty/desktop/bias/output/judges_h214to1718.csv', 'r')
f.readline()
cur.copy_from(f, 'judges_180619', sep=',')
f.close()
print 'populated judges table'


cur.execute("""
CREATE TABLE scores_180619(
    elt_id text PRIMARY KEY,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    elt_name text,
    level integer,
    h2 integer,
    elt_bv float,
    elt_sov_goe float,
    elt_total float
    );
""")
print 'created scores table'
f = open(r'/users/clarapouletty/desktop/bias/output/scores_H20910-1718.csv', 'r')
f.readline()
cur.copy_from(f, 'scores_180619', sep=',')
f.close()
print 'populated scores table'

cur.execute("""
CREATE TABLE pcs_180619(
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
    pcs float 
    );
""")
print 'created pcs table'
f = open(r'/users/clarapouletty/desktop/bias/output/pcs_H20910to1718.csv', 'r')
f.readline()
cur.copy_from(f, 'pcs_180619', sep=',')
f.close()
print 'populated pcs table'

cur.execute("""
CREATE TABLE goe_180619(
    elt_id text PRIMARY KEY,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    judge text,
    goe integer 
    );
""")
print 'created goe table'
f = open(r'/users/clarapouletty/desktop/bias/output/goe_H20910to1718.csv', 'r')
f.readline()
cur.copy_from(f, 'goe_180619', sep=',')
f.close()
print 'populated goe table'

cur.execute("""
CREATE TABLE competitors_180619(
    line_id integer PRIMARY KEY,
    season text,
    discipline text,
    category text,
    skater_name text,
    country text
    );
""")
print 'created competitors table'
f = open(r'/users/clarapouletty/desktop/bias/output/competitors_H20910to1718.csv', 'r')
f.readline()
cur.copy_from(f, 'competitors_180619', sep=',')
f.close()
print 'populated competitors table'

cur.execute("""
CREATE TABLE calls_180619(
    elt_id text PRIMARY KEY,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    elt_no integer,
    elt_name text,
    level integer,
    invalid integer,
    h2 integer,
    combo_flag integer,
    ur_flag integer,
    downgrade_flag integer,
    severe_edge_flag integer,
    unclear_edge_flag integer,
    rep_flag integer,
    jump_1 text,
    j1_sev_edge integer,
    j1_unc_edge	integer,
    j1_ur integer,	
    j1_down integer,
    jump_2 text,
    j2_sev_edge integer,
    j2_unc_edge	integer,
    j2_ur integer,	
    j2_down integer,
    jump_3 text,
    j3_sev_edge integer,
    j3_unc_edge	integer,
    j3_ur integer,	
    j3_down integer,
    jump_4 text,
    j4_sev_edge integer,
    j4_unc_edge	integer,
    j4_ur integer,	
    j4_down integer,
    failed_spin integer
    );
""")
print 'created calls table'
f = open(r'/users/clarapouletty/desktop/bias/output/calls_H20910to1718.csv', 'r')
next(f)
cur.copy_from(f, 'calls_180619', sep=',')
f.close()
print 'populated calls table'

cur.execute("""
CREATE TABLE deductions_180619(
    line_id integer PRIMARY KEY,
    discipline text,
    category text,
    season text,
    event text,
    sub_event text,
    skater_name text,
    segment text,
    ded_type text,
    ded_points integer
    );
""")
print 'created deductions table'
f = open(r'/users/clarapouletty/desktop/bias/output/deductions_H20910to1718.csv', 'r')
f.readline()
cur.copy_from(f, 'deductions_180619', sep=',')
f.close()
print 'populated deductions table'

conn.commit()
cur.close()
conn.close()