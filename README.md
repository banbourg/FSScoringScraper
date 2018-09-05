# Figure Skating Scoring Scraper and Analysis

## How to Use Scraper

1. Clone the repository.
2. Use pdf_fetcher.py to get pdfs.
3. Use isu_judge_scraper.py to get judges.
4. Use pdf_converter.py to convert pdfs to .xlsx
5. Structure the data using transformer_xlsx.py. If fetching additional data, change to ‘header=False’ in the to_csv calls at the end of the script & add reindexing instruction. Amend input & output directories, date and version (nth time extracted on date) as needed, as well as filename trimmer in line 69 (slices filename from full path).
6. Create summary tables (to check for bugs in total score calculation) using generate_summary.py.
7. Upload to RDS database using db_builder.py.

## How to Use Data

The analysis folder includes a Jupyter Notebook that has the initial setup to call the data from the database. Make a local copy of that notebook to use for your testing.
