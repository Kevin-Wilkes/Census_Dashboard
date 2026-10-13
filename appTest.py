from pathlib import Path

import pandas as pd

from census import client, transform, viz

#this is a simple test to check if the app is working

gaz = pd.read_parquet(Path("data/gaz_tracts.parquet"))
rows = client.tracts_for_city("48", "05000")       # Austin
df = transform.build_tract_table(rows, gaz)

print(df.shape)
print(df[["NAME", "rent_burden_pct", "reliable"]].head())
viz.build_map(df).show()