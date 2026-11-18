from pathlib import Path
import json
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def load_csv(filename):
    """Load a project CSV file."""
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return pd.read_csv(path)


def load_education():
    """Load and validate cleaned education observations."""
    df = load_csv("education_clean.csv")

    required = [
        "year", "region", "education_level",
        "indicator", "gender", "school_type",
        "analysis_value"
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["year"] = pd.to_numeric(
        df["year"], errors="raise"
    ).astype(int)

    df["analysis_value"] = pd.to_numeric(
        df["analysis_value"], errors="coerce"
    )

    return df


def load_boundaries():
    """Load the 20-region Kazakhstan GeoJSON."""
    path = DATA_DIR / "kazakhstan_regions.geojson"

    with open(path, encoding="utf-8") as file:
        geojson = json.load(file)

    features = geojson.get("features", [])

    if len(features) != 20:
        raise ValueError("Expected 20 map features.")

    names = [
        f.get("properties", {}).get("analysis_region")
        for f in features
    ]

    if None in names or len(set(names)) != 20:
        raise ValueError("Map region names are invalid.")

    return geojson


def filter_data(
    df, year, level, indicator, gender, school_type
):
    """Filter the dataset using dashboard selections."""
    return df.loc[
        (df["year"] == year)
        & (df["education_level"] == level)
        & (df["indicator"] == indicator)
        & (df["gender"] == gender)
        & (df["school_type"] == school_type)
    ].copy()


def national_value(
    df, level, indicator,
    school_type="Not applicable"
):
    """Return the 2025 national total when available."""
    subset = filter_data(
        df, 2025, level, indicator, "Total", school_type
    )

    values = subset.loc[
        subset["region"] == "Kazakhstan",
        "analysis_value"
    ].dropna()

    return float(values.iloc[0]) if len(values) == 1 else None


def calculate_female_share(df, year, level):
    """Calculate regional female enrollment percentages."""
    subset = df.loc[
        (df["year"] == year)
        & (df["region"] != "Kazakhstan")
        & (df["education_level"] == level)
        & (df["indicator"] == "enrollment")
        & (df["gender"].isin(["Female", "Total"]))
        & (df["school_type"] != "Evening")
    ].copy()

    if subset.empty:
        return pd.DataFrame()

    pivot = subset.pivot_table(
        index="region",
        columns="gender",
        values="analysis_value",
        aggfunc="first"
    )

    if not {"Female", "Total"}.issubset(pivot.columns):
        return pd.DataFrame()

    result = pivot.reset_index()

    result["female_share_pct"] = (
        100 * result["Female"] / result["Total"]
    )

    invalid = (
        (result["Total"] <= 0)
        | (result["Female"] < 0)
        | (result["Female"] > result["Total"])
    )

    result.loc[invalid, "female_share_pct"] = float("nan")

    return result


def read_database(query, params=()):
    """Execute a read-only query on the SQLite database."""
    db_path = DATA_DIR / "education.db"

    if not db_path.exists():
        raise FileNotFoundError("SQLite database not found.")

    if not query.lstrip().upper().startswith(
        ("SELECT", "WITH")
    ):
        raise ValueError("Only SELECT/CTE queries are supported.")

    with sqlite3.connect(db_path) as connection:
        return pd.read_sql_query(
            query, connection, params=params
        )
