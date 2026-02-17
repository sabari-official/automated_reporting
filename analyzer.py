"""
analyzer.py — Deep statistical analysis of a DataFrame or text blob.

Returns a rich analysis dict consumed by report_builder.py.
"""

import re
import math
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def analyze(file_info: dict) -> dict:
    """
    Given the unified file_info dict from file_reader.read_file(),
    produce a comprehensive analysis dict.
    """
    result = {
        "file":      file_info,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overview":  {},
        "numeric":   {},
        "categorical": {},
        "datetime":  {},
        "correlations": {},
        "missing":   {},
        "outliers":  {},
        "text_stats": {},
        "insights":  [],
        "warnings":  [],
    }

    df = file_info.get("df")
    text = file_info.get("text", "")

    if df is not None and not df.empty:
        result.update(_analyze_df(df))
    elif text:
        result["text_stats"] = _analyze_text(text)

    result["insights"] = _generate_insights(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAME ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_df(df: pd.DataFrame) -> dict:
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    dt_cols   = _detect_datetime_cols(df)

    # ── Overview ──────────────────────────────────────────────────────────────
    overview = {
        "rows":         len(df),
        "columns":      len(df.columns),
        "numeric_cols": len(num_cols),
        "categorical_cols": len(cat_cols),
        "datetime_cols": len(dt_cols),
        "total_cells":  df.size,
        "missing_cells": int(df.isna().sum().sum()),
        "missing_pct":  round(df.isna().sum().sum() / max(df.size, 1) * 100, 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_kb":    round(df.memory_usage(deep=True).sum() / 1024, 2),
        "col_names":    df.columns.tolist(),
    }

    # ── Missing per column ────────────────────────────────────────────────────
    missing = {}
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n > 0:
            missing[col] = {"count": n, "pct": round(n / len(df) * 100, 2)}

    # ── Numeric stats ─────────────────────────────────────────────────────────
    numeric = {}
    for col in num_cols:
        s = df[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        skewness = float(s.skew()) if len(s) > 2 else 0.0
        kurtosis = float(s.kurtosis()) if len(s) > 3 else 0.0
        numeric[col] = {
            "count":  int(s.count()),
            "mean":   round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std":    round(float(s.std()), 4),
            "min":    round(float(s.min()), 4),
            "max":    round(float(s.max()), 4),
            "q1":     round(float(q1), 4),
            "q3":     round(float(q3), 4),
            "iqr":    round(float(iqr), 4),
            "range":  round(float(s.max() - s.min()), 4),
            "cv":     round(float(s.std() / s.mean() * 100), 2) if s.mean() != 0 else 0,
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
            "zeros":  int((s == 0).sum()),
            "negative": int((s < 0).sum()),
        }
        # Outlier detection (IQR method)
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        out_mask = (s < lo) | (s > hi)
        numeric[col]["outlier_count"] = int(out_mask.sum())
        numeric[col]["outlier_pct"]   = round(float(out_mask.sum()) / len(s) * 100, 2)

    # ── Categorical stats ─────────────────────────────────────────────────────
    categorical = {}
    for col in cat_cols[:20]:  # cap at 20
        s = df[col].dropna()
        vc = s.value_counts()
        categorical[col] = {
            "count":       int(s.count()),
            "unique":      int(s.nunique()),
            "top_value":   str(vc.index[0]) if len(vc) else "",
            "top_freq":    int(vc.iloc[0]) if len(vc) else 0,
            "top_pct":     round(float(vc.iloc[0]) / len(s) * 100, 2) if len(vc) else 0,
            "value_counts": {str(k): int(v) for k, v in vc.head(10).items()},
        }

    # ── Correlations ─────────────────────────────────────────────────────────
    correlations = {}
    if len(num_cols) >= 2:
        corr_df = df[num_cols].corr()
        # Top pairs
        pairs = []
        for i, c1 in enumerate(num_cols):
            for c2 in num_cols[i+1:]:
                val = corr_df.loc[c1, c2]
                if not math.isnan(val):
                    pairs.append({"col1": c1, "col2": c2, "r": round(float(val), 4)})
        pairs.sort(key=lambda x: abs(x["r"]), reverse=True)
        correlations = {
            "matrix": {c: {c2: round(float(v), 3) for c2, v in corr_df[c].items()}
                       for c in corr_df.columns},
            "top_pairs": pairs[:10],
        }

    # ── DateTime analysis ─────────────────────────────────────────────────────
    datetime_info = {}
    for col in dt_cols:
        try:
            s = pd.to_datetime(df[col], errors="coerce").dropna()
            if len(s) > 1:
                datetime_info[col] = {
                    "min": str(s.min()),
                    "max": str(s.max()),
                    "span_days": (s.max() - s.min()).days,
                    "count": len(s),
                }
        except Exception:
            pass

    return {
        "overview":     overview,
        "numeric":      numeric,
        "categorical":  categorical,
        "correlations": correlations,
        "missing":      missing,
        "datetime":     datetime_info,
    }


def _detect_datetime_cols(df: pd.DataFrame) -> list:
    """Heuristically detect columns that look like dates."""
    candidates = []
    date_keywords = ("date", "time", "dt", "year", "month", "created", "updated")
    for col in df.columns:
        if any(k in col.lower() for k in date_keywords):
            candidates.append(col)
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# TEXT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_text(text: str) -> dict:
    words     = re.findall(r"\b\w+\b", text.lower())
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lines     = [l for l in text.splitlines() if l.strip()]

    word_freq = {}
    stop = {"the","a","an","is","are","was","were","and","or","but","in",
            "on","at","to","for","of","with","by","from","as","this","that",
            "it","its","be","been","being","have","has","had","do","did","i",
            "you","he","she","we","they","not","so","if","all","can","will"}
    for w in words:
        if w not in stop and len(w) > 2:
            word_freq[w] = word_freq.get(w, 0) + 1

    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    avg_word_len = round(sum(len(w) for w in words) / max(len(words), 1), 2)
    avg_sent_len = round(len(words) / max(len(sentences), 1), 2)

    return {
        "char_count":   len(text),
        "word_count":   len(words),
        "unique_words": len(set(words)),
        "sentence_count": len(sentences),
        "line_count":   len(lines),
        "avg_word_length": avg_word_len,
        "avg_sentence_length": avg_sent_len,
        "top_words":    top_words,
        "lexical_diversity": round(len(set(words)) / max(len(words), 1), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _generate_insights(result: dict) -> list:
    insights = []
    ov  = result.get("overview", {})
    num = result.get("numeric", {})
    cat = result.get("categorical", {})
    cor = result.get("correlations", {})
    mis = result.get("missing", {})
    txt = result.get("text_stats", {})

    # Dataset size
    rows = ov.get("rows", 0)
    if rows:
        if rows > 100_000:
            insights.append(("Large Dataset", f"Dataset has {rows:,} rows — well suited for statistical modeling."))
        elif rows < 30:
            insights.append(("Small Sample", f"Only {rows} rows detected — interpret statistics cautiously."))

    # Missing data
    miss_pct = ov.get("missing_pct", 0)
    if miss_pct > 20:
        insights.append(("High Missing Data", f"{miss_pct:.1f}% of cells are missing — consider imputation."))
    elif miss_pct > 5:
        insights.append(("Moderate Missing Data", f"{miss_pct:.1f}% missing cells detected."))

    # Duplicates
    dups = ov.get("duplicate_rows", 0)
    if dups > 0:
        insights.append(("Duplicate Rows", f"{dups} duplicate rows found — deduplication recommended."))

    # Outliers
    for col, stats in num.items():
        if stats.get("outlier_pct", 0) > 10:
            insights.append(("Outliers Detected", f"Column '{col}' has {stats['outlier_pct']}% outliers (IQR method)."))

    # Skewed columns
    for col, stats in num.items():
        sk = abs(stats.get("skewness", 0))
        if sk > 2:
            dir_ = "positively" if stats["skewness"] > 0 else "negatively"
            insights.append(("Skewed Distribution", f"'{col}' is strongly {dir_} skewed (skewness={stats['skewness']:.2f})."))

    # Strong correlations
    for pair in cor.get("top_pairs", [])[:3]:
        if abs(pair["r"]) >= 0.8:
            insights.append(("Strong Correlation",
                f"'{pair['col1']}' and '{pair['col2']}' are strongly correlated (r={pair['r']:.3f})."))

    # Dominant categories
    for col, stats in cat.items():
        if stats.get("top_pct", 0) > 70:
            insights.append(("Dominant Category",
                f"'{stats['top_value']}' dominates '{col}' at {stats['top_pct']:.1f}%."))

    # Text insights
    if txt:
        div = txt.get("lexical_diversity", 0)
        if div < 0.3:
            insights.append(("Low Lexical Diversity", f"Text has low diversity ({div:.2f}) — possibly repetitive."))
        wc = txt.get("word_count", 0)
        insights.append(("Document Size", f"{wc:,} words across {txt.get('sentence_count', 0)} sentences."))

    return insights[:12]  # cap at 12
