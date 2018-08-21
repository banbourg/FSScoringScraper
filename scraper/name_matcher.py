import numpy as np
import pandas as pd
import psycopg2
import recordlinkage

from init import settings


bad_matches = [
    ['alexandra kunova', 'alexandra proklova'],
    ['alexandra kunova', 'alexandra trusova'],
    ['yuna kim', 'na hyun kim'],
    ['dan fang', 'fan zhang'],
    ['mao asada', 'mai asada'],
    ['anastasia tarakanova', 'anastasiia gubanova']
]

conn = psycopg2.connect(database=settings.DB, user=settings.UN, password=settings.PW, host=settings.H,
                        port=settings.PORT)


def bad_match(row):
    names = [row['name_First'], row['name_Second']]
    names.sort()
    for match in bad_matches:
        match.sort()
        if names == match:
            return True

    return False


def linkage(df):
    indexer = recordlinkage.Index()
    indexer.full()
    pairs = indexer.index(df)
    compare_cl = recordlinkage.Compare()
    compare_cl.string('name', 'name', method='cosine', label='name_match')

    features = compare_cl.compute(pairs, df)

    matches = features[features.name_match >= .75]
    matches.reset_index(inplace=True)
    matches = matches[matches['line_id_1'] != matches['line_id_2']]

    matched = matches.merge(df, left_on='line_id_1', right_on='line_id')
    matched = matched.merge(df, left_on='line_id_2', right_on='line_id', suffixes=['_First', '_Second'])
    matched = matched[(matched['disc_First'] == matched['disc_Second'])]

    matched['bad_match'] = matched.apply(bad_match, axis=1)

    return matched


def depair(df):
    d = {}
    check = 0

    for index, row in df[df['bad_match'] is False].iterrows():
        if not d:
            d[row['line_id_1']] = []
            d[row['line_id_1']].append(row['line_id_1'])
            d[row['line_id_1']].append(row['line_id_2'])
        else:
            for key in d.keys():
                if row['line_id_1'] in d[key]:
                    if row['line_id_2'] in d[key]:
                        check = 1
                    else:
                        d[key].append(row['line_id_2'])
                        check = 1
                elif row['line_id_2'] in d[key]:
                    if row['line_id_1'] in d[key]:
                        check = 1
                    else:
                        d[key].append(row['line_id_1'])
                        check = 1
            if check != 1:
                d[row['line_id_1']] = []
                d[row['line_id_1']].append(row['line_id_1'])
                d[row['line_id_1']].append(row['line_id_2'])
            check = 0

    id_pair = {}
    for key in d.keys():
        for line_id in d[key]:
            id_pair[line_id] = key

    return id_pair


def merge(df, pairs):
    id_pair_df = pd.DataFrame(pd.Series(pairs))
    id_pair_df.reset_index(inplace=True)
    id_pair_df.rename(columns={'index': 'line_id', 0: 'master_competitor_id'}, inplace=True)

    df_final = df.merge(id_pair_df, on='line_id', how='outer')
    df_final['master_competitor_id'] = df_final.apply(lambda x: int(x['line_id']) if np.isnan(x['master_competitor_id'])
                                                      else int(x['master_competitor_id']), axis=1)

    df_final = df_final.merge(df_final[['line_id', 'name']], left_on='master_competitor_id', right_on='line_id',
                              suffixes=['', 'x'])

    df_final.drop('line_idx', axis=1, inplace=True)
    df_final.rename(columns={'namex': 'master_competitor_name'}, inplace=True)

    return df_final


def to_sql(df):
    cursor = conn.cursor()

    cursor.execute(psycopg2.sql.SQL("DROP TABLE IF EXISTS competitors_unmatched;"))
    cursor.execute(psycopg2.sql.SQL("ALTER TABLE IF EXISTS competitors RENAME TO competitors_unmatched;"))
    conn.commit()

    df.to_sql('competitors', conn, chunksize=10000, index=False)


if __name__ == '__main__':

    df_clean = pd.read_sql_query("Select * FROM competitors", conn)
    df = df_clean.copy()
    df.set_index('line_id', inplace=True)
    df['name'] = df['name'].apply(lambda x: x.lower())

    to_sql(merge(df, depair(linkage(df))))
