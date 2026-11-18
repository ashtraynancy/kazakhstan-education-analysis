import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium

from branca.colormap import linear
from streamlit.components.v1 import html

from data_utils import (
    load_csv,
    load_education,
    load_boundaries,
    filter_data,
    national_value,
    calculate_female_share,
    read_database
)


st.set_page_config(
    page_title="Kazakhstan Education Statistics",
    page_icon="🎓",
    layout="wide"
)

st.title("Kazakhstan Regional Education Statistics")

st.write(
    "Compare educational enrollment, gender distribution, "
    "regional indicators, historical trends and forecasts."
)


@st.cache_data
def get_data():
    return load_education()


@st.cache_data
def get_geojson():
    return load_boundaries()


df = get_data()

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------

st.sidebar.header("Analysis Filters")

years = sorted(df["year"].dropna().unique(), reverse=True)

year = st.sidebar.selectbox("Year", years)

levels = sorted(df["education_level"].dropna().unique())

level = st.sidebar.selectbox(
    "Education level", levels,
    index=levels.index("Higher") if "Higher" in levels else 0
)

available = df.loc[
    (df["year"] == year)
    & (df["education_level"] == level)
]

indicators = sorted(available["indicator"].dropna().unique())

if not indicators:
    st.warning("No indicators available for this selection.")
    st.stop()

indicator = st.sidebar.selectbox(
    "Indicator", indicators,
    index=indicators.index("enrollment")
    if "enrollment" in indicators else 0
)

available = available.loc[
    available["indicator"] == indicator
]

genders = sorted(available["gender"].dropna().unique())

gender = st.sidebar.selectbox(
    "Gender", genders,
    index=genders.index("Total") if "Total" in genders else 0
)

available = available.loc[
    available["gender"] == gender
]

school_types = sorted(
    available["school_type"].dropna().unique()
)

school_type = st.sidebar.selectbox(
    "School type", school_types
)

regional_df = filter_data(
    df, year, level, indicator, gender, school_type
)

regional_df = regional_df.loc[
    regional_df["region"] != "Kazakhstan"
].dropna(subset=["analysis_value"])

regions = sorted(regional_df["region"].unique())

region_choice = st.sidebar.selectbox(
    "Region",
    ["All regions"] + regions
)

# ------------------------------------------------------------
# DASHBOARD TABS
# ------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Gender & Geography",
    "Trends & Forecasting",
    "Database Explorer"
])


# ------------------------------------------------------------
# TAB 1 — REGIONAL OVERVIEW
# ------------------------------------------------------------

with tab1:

    st.subheader("Regional Education Comparison")

    c1, c2, c3 = st.columns(3)

    c1.metric("Selected year", str(year))
    c2.metric("Education level", level)
    c3.metric("Regions with data", len(regional_df))

    if regional_df.empty:
        st.info("No observations for these filters.")

    elif region_choice == "All regions":

        chart_df = (
            regional_df.groupby("region", as_index=False)
            ["analysis_value"].sum()
            .sort_values("analysis_value", ascending=False)
        )

        fig = px.bar(
            chart_df,
            x="region",
            y="analysis_value",
            title=f"{indicator.title()} by Region ({year})",
            labels={
                "region": "Region",
                "analysis_value": "Value"
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            height=480
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(chart_df, use_container_width=True)

    else:

        selected = regional_df.loc[
            regional_df["region"] == region_choice
        ]

        st.metric(
            f"{region_choice}: {indicator}",
            f"{selected['analysis_value'].sum():,.0f}"
        )

        st.dataframe(selected, use_container_width=True)

    national = national_value(df, "Higher", "enrollment")

    if national is not None:
        st.metric(
            "National higher enrollment (2025)",
            f"{national:,.0f}"
        )


# ------------------------------------------------------------
# TAB 2 — GENDER AND GEOGRAPHY
# ------------------------------------------------------------

with tab2:

    st.subheader("Female Enrollment Share")

    female_df = calculate_female_share(df, year, level)

    if female_df.empty:
        st.info(
            "Gender breakdown is unavailable "
            "for this year and education level."
        )

    else:

        female_df = female_df.dropna(
            subset=["female_share_pct"]
        )

        fig = px.bar(
            female_df.sort_values("female_share_pct"),
            x="female_share_pct",
            y="region",
            orientation="h",
            title="Female Share of Enrollment",
            labels={
                "female_share_pct": "Female share (%)",
                "region": "Region"
            },
            height=650
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Geographical Distribution")

        boundaries = get_geojson()

        m = folium.Map(
            location=[48.0, 67.0],
            zoom_start=4,
            tiles=None
        )

        joined = {
            row["region"]: row["female_share_pct"]
            for _, row in female_df.iterrows()
        }

        color_scale = linear.YlOrRd_09.scale(0, 100)
        color_scale.caption = "Female enrollment share (%)"

        def color_feature(feature):
            region = feature["properties"]["analysis_region"]
            value = joined.get(region)

            if value is None or pd.isna(value):
                return {
                    "fillColor": "#d0d0d0",
                    "color": "#555555",
                    "weight": 1,
                    "fillOpacity": 0.55
                }

            return {
                "fillColor": color_scale(value),
                "color": "#555555",
                "weight": 1,
                "fillOpacity": 0.75
            }

        layer = folium.GeoJson(
            boundaries,
            style_function=color_feature,
            tooltip=folium.GeoJsonTooltip(
                fields=["analysis_region"],
                aliases=["Region"]
            )
        )

        layer.add_to(m)
        m.fit_bounds(layer.get_bounds())
        color_scale.add_to(m)

        html(
            m.get_root().render(),
            height=550,
            scrolling=False
        )


# ------------------------------------------------------------
# TAB 3 — NATIONAL TRENDS AND FORECASTING
# ------------------------------------------------------------

with tab3:

    st.subheader("Historical Trends")

    ts = load_csv("national_timeseries.csv")

    st.dataframe(ts.tail(15), use_container_width=True)

    year_columns = [
        col for col in ts.columns
        if col.lower() == "year"
    ]

    numeric_cols = [
        col for col in ts.select_dtypes(
            include="number"
        ).columns
        if col not in year_columns
    ]

    if year_columns and numeric_cols:
        selected_series = st.selectbox(
            "Time-series indicator",
            numeric_cols
        )

        fig = px.line(
            ts,
            x=year_columns[0],
            y=selected_series,
            markers=True,
            title=f"National Trend: {selected_series}"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Forecasting Models")

    forecast = load_csv("forecast_results.csv")
    metrics = load_csv("forecast_metrics.csv")

    required_columns = {
        "year", "method", "actual", "predicted"
    }

    if required_columns.issubset(forecast.columns):

        fig = go.Figure()

        actual = (
            forecast[["year", "actual"]]
            .drop_duplicates(subset="year")
            .sort_values("year")
        )

        fig.add_trace(go.Scatter(
            x=actual["year"],
            y=actual["actual"],
            name="Actual admissions",
            mode="lines+markers",
            line=dict(width=4)
        ))

        for method, subset in forecast.groupby("method"):

            subset = subset.sort_values("year")

            fig.add_trace(go.Scatter(
                x=subset["year"],
                y=subset["predicted"],
                name=method,
                mode="lines+markers"
            ))

        fig.update_layout(
            title="Actual vs Predicted Admissions",
            xaxis_title="Year",
            yaxis_title="Admissions",
            hovermode="x unified",
            height=480
        )

        st.plotly_chart(fig, use_container_width=True)

    st.write("Model Evaluation Metrics")
    st.dataframe(metrics, use_container_width=True)

    if {"method", "MAE"}.issubset(metrics.columns):
        fig_mae = px.bar(
            metrics.sort_values("MAE"),
            x="method",
            y="MAE",
            title="Forecasting Model Comparison (MAE)"
        )

        st.plotly_chart(fig_mae, use_container_width=True)


# ------------------------------------------------------------
# TAB 4 — DATABASE EXPLORER
# ------------------------------------------------------------

with tab4:

    st.subheader("SQLite Database Explorer")

    tables = read_database("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    st.write("Database Tables")
    st.dataframe(tables, use_container_width=True)

    st.write("Observation Count")

    counts = read_database("""
        SELECT COUNT(*) AS total_observations
        FROM observations
    """)

    st.dataframe(counts, use_container_width=True)

    st.write("Regions with Most Observations")

    region_counts = read_database("""
        SELECT
            r.region_name,
            COUNT(*) AS observation_count
        FROM observations o
        JOIN regions r
          ON o.region_id = r.region_id
        GROUP BY r.region_name
        ORDER BY observation_count DESC
        LIMIT 10
    """)

    st.dataframe(
        region_counts,
        use_container_width=True
    )


st.divider()

st.caption(
    "Source: Bureau of National Statistics of Kazakhstan. "
    "Missing values are preserved and are not treated as zero."
)
