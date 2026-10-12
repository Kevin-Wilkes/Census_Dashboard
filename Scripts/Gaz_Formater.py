from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / "2024_Gaz_tracts_national.txt"
OUT_FILE = ROOT / "data" / "gaz_tracts.parquet"

# Strips and converts the national Gazetteer file into a trimmed parquet file
gaz = pd.read_csv(RAW_FILE, sep="\t", dtype={"GEOID": str})
gaz.columns = gaz.columns.str.strip()  # remove trailing whitespace from the last column name
gaz[["GEOID", "INTPTLAT", "INTPTLONG", "ALAND_SQMI"]].to_parquet(OUT_FILE, index=False)

print(f"Wrote {len(gaz):,} tracts to {OUT_FILE}")