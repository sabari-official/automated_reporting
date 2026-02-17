import os, json, re
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────

def read_file(path: str) -> dict:

    result = {
        "type": None, "filename": os.path.basename(path),
        "filesize": _human_size(path),
        "df": None, "text": "", "raw": None,
        "sheets": [], "error": None,
    }

    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".csv":
            result.update(_read_csv(path))
        elif ext == ".tsv":
            result.update(_read_tsv(path))
        elif ext in (".xlsx", ".xls"):
            result.update(_read_excel(path))
        elif ext == ".json":
            result.update(_read_json(path))
        elif ext in (".txt", ".md", ".log"):
            result.update(_read_txt(path))
        elif ext == ".pdf":
            result.update(_read_pdf(path))
        else:
            # Try CSV as fallback
            try:
                result.update(_read_csv(path))
            except Exception:
                result["error"] = f"Unsupported file type: {ext}"
    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# READERS
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(path):
    # Try multiple encodings and separators
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
            df = _clean_df(df)
            return {"type": "csv", "df": df, "raw": df}
        except Exception:
            continue
    raise ValueError("Could not decode CSV with any supported encoding.")


def _read_tsv(path):
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, sep="\t", encoding=enc, on_bad_lines="skip")
            df = _clean_df(df)
            return {"type": "tsv", "df": df, "raw": df}
        except Exception:
            continue
    raise ValueError("Could not decode TSV.")


def _read_excel(path):
    xl = pd.ExcelFile(path)
    sheets = xl.sheet_names
    frames = {}
    for sh in sheets:
        df = pd.read_excel(xl, sheet_name=sh)
        frames[sh] = _clean_df(df)
    # Use first sheet as primary df
    primary = frames[sheets[0]]
    return {"type": "excel", "df": primary, "raw": frames, "sheets": sheets}


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Try to normalise to DataFrame
    try:
        if isinstance(data, list):
            df = pd.json_normalize(data)
        elif isinstance(data, dict):
            # Try values
            first_val = next(iter(data.values()), None)
            if isinstance(first_val, list):
                df = pd.json_normalize(data[next(iter(data))])
            else:
                df = pd.json_normalize([data])
        else:
            df = pd.DataFrame()
        df = _clean_df(df)
    except Exception:
        df = pd.DataFrame()
    return {"type": "json", "df": df, "raw": data,
            "text": json.dumps(data, indent=2)[:5000]}


def _read_txt(path):
    for enc in ("utf-8", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                text = f.read()
            # Try to detect if it's actually tabular
            df = _txt_to_df(text)
            return {"type": "txt", "df": df, "raw": text,
                    "text": text[:10000]}
        except Exception:
            continue
    raise ValueError("Could not read text file.")


def _read_pdf(path):
    try:
        import pdfplumber
        text_parts = []
        tables = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
                tbls = page.extract_tables()
                for tbl in tbls:
                    if tbl and len(tbl) > 1:
                        try:
                            df = pd.DataFrame(tbl[1:], columns=tbl[0])
                            tables.append(_clean_df(df))
                        except Exception:
                            pass
        full_text = "\n".join(text_parts)
        primary_df = tables[0] if tables else _txt_to_df(full_text)
        return {"type": "pdf", "df": primary_df, "raw": tables,
                "text": full_text[:10000]}
    except ImportError:
        raise ValueError("pdfplumber not installed. Run: pip install pdfplumber")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column names, drop fully-empty rows/cols."""
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    # Convert obvious numeric columns
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df.reset_index(drop=True)


def _txt_to_df(text: str) -> pd.DataFrame:
    """Try to parse delimited lines from plain text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return pd.DataFrame()
    # Detect delimiter
    sample = lines[0]
    for sep in (",", "\t", ";", "|"):
        if sep in sample and sample.count(sep) >= 1:
            rows = [l.split(sep) for l in lines]
            if len(set(len(r) for r in rows[:5])) == 1:
                df = pd.DataFrame(rows[1:], columns=rows[0])
                return _clean_df(df)
    return pd.DataFrame()


def _human_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
    except Exception:
        return "Unknown"
