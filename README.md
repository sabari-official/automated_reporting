# Task 2 — Automated Report Generation
### CODTECH Internship · AutoReport

---

## What This Does

Give it **any data file** → get back a beautiful, **multi-page PDF report** with:

| Section | Content |
|---------|---------|
| Cover | File metadata, date, row/column counts |
| Executive Summary | Overview paragraph + key insights + quick stats table |
| Numeric Analysis | Full stats table (mean/median/std/skew/kurt/outliers) + histograms + box plot |
| Categorical Analysis | Frequency tables + bar charts + pie charts |
| Correlation Analysis | Pearson r matrix + ranked pair table + heatmap + scatter plot |
| Data Quality | Missing data map, per-column missing %, duplicate count |
| Appendix | Complete column inventory with data types |

---

## Supported File Types

| Format | Extension |
|--------|-----------|
| CSV    | `.csv` |
| TSV    | `.tsv` |
| Excel  | `.xlsx`, `.xls` |
| JSON   | `.json` |
| Plain text | `.txt`, `.md`, `.log` |
| PDF    | `.pdf` (text + table extraction) |

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
# Interactive (prompts for file path)
python main.py

# Pass file directly
python main.py my_data.csv

# Custom output filename
python main.py sales.xlsx --out sales_report_Q4.pdf

# Any supported format
python main.py data.json --out json_report.pdf
python main.py document.txt --out text_analysis.pdf
```

---

## What Gets Analyzed

### Numeric Columns
- Count, Mean, Median, Std Dev
- Min, Max, Range, IQR (Q1–Q3)
- Skewness & Kurtosis
- Coefficient of Variation
- Outlier detection (IQR method, flagged with %)
- Histogram with KDE overlay

### Categorical Columns
- Count, Unique value count
- Top value + frequency + percentage
- Top-10 value frequency breakdown
- Bar chart + Pie chart

### Correlations
- Full Pearson correlation matrix
- Ranked pairs by |r| value
- Labelled strength: Very Weak → Very Strong
- Correlation heatmap
- Scatter plot of top correlated pair

### Data Quality
- Total missing cells + per-column breakdown
- Severity rating per column (Low / Moderate / High / Critical)
- Missing data visual map
- Duplicate row count

### Text Files
- Word count, unique words, sentence count
- Lexical diversity score
- Top 15 word frequency bar chart
- Avg word/sentence length

---

## File Structure

```
task2_report_generator/
├── main.py              # Entry point — CLI, orchestration, terminal output
├── file_reader.py       # Detect & load any file type → unified dict
├── analyzer.py          # Statistical analysis → insight generation
├── chart_generator.py   # Matplotlib dark-theme charts → PNG bytes
├── report_builder.py    # ReportLab PDF assembler
├── requirements.txt
├── README.md
└── sample_ecommerce.csv # Demo dataset
```

---

## Sample Output

The included `sample_ecommerce.csv` (508 rows × 14 columns) demonstrates:
- Numeric: `customer_age`, `unit_price`, `revenue`, `profit`, `quantity`, etc.
- Categorical: `category`, `region`, `status`, `channel`
- Auto-detected insights: skewed price distributions, strong revenue-profit correlation, duplicate rows
