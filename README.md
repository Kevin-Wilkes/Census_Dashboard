# Renter Cost Burden Explorer

A Streamlit app that maps where renters are most cost-burdened (spending 30%+ of income on rent) across the census tracts of any U.S. city, using live data from the U.S. Census Bureau API (ACS 2020–2024 5-year estimates).

## How to run

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy env.example .env             # macOS/Linux: cp env.example .env
streamlit run app.py
```

Add your free Census API key to `.env` ([sign up here](https://api.census.gov/data/key_signup.html)). The app also runs without a key at low volume.

## Structure

```
├── app.py                    # Streamlit UI
├── appTest.py                # quick pipeline check without the UI
├── census/
│   ├── client.py             # Census API requests, retries, error handling
│   ├── transform.py          # cleaning, rent burden, reliability flags, Gazetteer join
│   └── viz.py                # map building and auto-zoom
├── Data/
│   ├── raw/                  # raw Gazetteer download (not committed)
│   └── gaz_tracts.parquet    # tract coordinates and land area
├── Scripts/
│   └── Gaz_Formater.py       # builds gaz_tracts.parquet from the raw Gazetteer file
├── requirements.txt          # app dependencies
├── requirements-dev.txt      # adds testing and linting tools
└── env.example               # template for the .env file
```