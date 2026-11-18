# Kazakhstan Regional Education Statistics

Final project for Programming for Data Analysis and Database.

## Project
Analyze regional education indicators, gender distribution,
historical trends and forecasts for Kazakhstan.

## Technologies
Python, Pandas, SQLite, Plotly, Folium, Streamlit.

## Run the dashboard
1. Install Python.
2. Run: pip install -r requirements.txt
3. Run: streamlit run app.py

## Files
- app.py: interactive dashboard
- data_utils.py: reusable data functions
- data/: cleaned statistics, GeoJSON and SQLite database
- sql_queries.sql: database analysis
- test_project.py: automated tests, if included

## Data source
Bureau of National Statistics, Kazakhstan:
https://stat.gov.kz/

## Limitations
Missing values are not treated as zero.
Historical regional boundaries changed.
Enrollment does not directly measure academic achievement.



## Reproducing the Analysis

The analysis was developed in Google Colab using eight
official education statistics Excel workbooks and a
Kazakhstan regional GeoJSON file.

To reproduce it, open `Programming_final_project.ipynb`,
place the source files in `/content`, and run the cells
in order.

The Streamlit dashboard can run independently using
the cleaned datasets included in this project.

## Automated Tests

Run:

    python test_project.py

## Data Optimization

CSV, optimized CSV, and Parquet formats were compared
for loading time, memory usage, and storage size.

Results: `docs/benchmark_results.csv`
Optimized data: `data/education_optimized.parquet`

