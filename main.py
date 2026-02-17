import sys
import os
import argparse
import time

# ── ANSI colours ──────────────────────────────────────────────────────────────
RST  = "\033[0m"
def _c(t, code): return f"\033[{code}m{t}{RST}"
RED    = lambda t: _c(t, 91)
GREEN  = lambda t: _c(t, 92)
YELLOW = lambda t: _c(t, 93)
BLUE   = lambda t: _c(t, 94)
CYAN   = lambda t: _c(t, 96)
WHITE  = lambda t: _c(t, 97)
BOLD   = lambda t: _c(t, "1;97")
GRAY   = lambda t: _c(t, 90)

AMBER  = lambda t: _c(t, 93)

def _rule(char="─", w=68, c=GRAY): print(c(char * w))
def _step(icon, msg): print(f"  {icon}  {WHITE(msg)}")
def _ok(msg):   print(f"  {GREEN('✔')}  {msg}")
def _warn(msg): print(f"  {YELLOW('⚠')}  {msg}")
def _err(msg):  print(f"  {RED('✖')}  {msg}")


def _banner():
    print()
    _rule("═", 68, BLUE)
    print(BOLD("  📄  AutoReport  ·  Automated PDF Report Generator  ·  Task 2"))
    _rule("═", 68, BLUE)
    print()


def _supported_formats():
    print(f"  {GRAY('Supported file types:')}  "
          f"{CYAN('CSV')}  {CYAN('TSV')}  {CYAN('Excel (.xlsx/.xls)')}  "
          f"{CYAN('JSON')}  {CYAN('TXT')}  {CYAN('PDF')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="AutoReport — Task 2")
    parser.add_argument("file", nargs="?", help="Path to input data file")
    parser.add_argument("--out", default=None, help="Output PDF path")
    args = parser.parse_args()

    _banner()
    _supported_formats()

    # ── file path ─────────────────────────────────────────────────────────────
    if args.file:
        file_path = args.file.strip()
    else:
        try:
            file_path = input(f"  {CYAN('Enter path to your data file')}  › ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Aborted.")
            sys.exit(0)

    if not file_path:
        _err("No file path provided. Exiting.")
        sys.exit(1)

    # strip accidental quotes
    file_path = file_path.strip("'\"")

    if not os.path.isfile(file_path):
        _err(f"File not found: {file_path}")
        sys.exit(1)

    filename = os.path.basename(file_path)
    ext      = os.path.splitext(file_path)[1].lower()
    out_pdf  = args.out or f"report_{os.path.splitext(filename)[0]}.pdf"

    _rule()
    _step("📂", f"File      : {YELLOW(filename)}")
    _step("📏", f"Extension : {CYAN(ext)}")
    _step("💾", f"Output    : {GREEN(out_pdf)}")
    _rule()

    # ── Step 1: Read ──────────────────────────────────────────────────────────
    print()
    _step("1️⃣ ", "Reading file…")
    t0 = time.time()

    from file_reader import read_file
    file_info = read_file(file_path)

    if file_info.get("error"):
        _err(f"Could not read file: {file_info['error']}")
        sys.exit(1)

    df = file_info.get("df")
    _ok(f"Read complete in {time.time()-t0:.2f}s  "
        f"({file_info['type'].upper()}  ·  {file_info['filesize']})")

    if df is not None and not df.empty:
        _ok(f"DataFrame: {len(df):,} rows × {len(df.columns)} columns")
    elif file_info.get("text"):
        wc = len(file_info["text"].split())
        _ok(f"Text loaded: ~{wc:,} words")

    # Excel multi-sheet info
    sheets = file_info.get("sheets", [])
    if sheets and len(sheets) > 1:
        _warn(f"Excel has {len(sheets)} sheets. Using first sheet: '{sheets[0]}'")

    # ── Step 2: Analyze ───────────────────────────────────────────────────────
    print()
    _step("2️⃣ ", "Analyzing data…")
    t1 = time.time()

    from analyzer import analyze
    analysis = analyze(file_info)

    ov = analysis.get("overview", {})
    num_c = len(analysis.get("numeric", {}))
    cat_c = len(analysis.get("categorical", {}))
    _ok(f"Analysis done in {time.time()-t1:.2f}s")
    _ok(f"Numeric columns: {CYAN(str(num_c))}   Categorical: {CYAN(str(cat_c))}")
    _ok(f"Missing data: {YELLOW(str(ov.get('missing_pct', 0))+'%')}   "
        f"Duplicates: {YELLOW(str(ov.get('duplicate_rows', 0)))}")

    ins = analysis.get("insights", [])
    if ins:
        print()
        print(f"  {CYAN('Key Insights:')}")
        for title, body in ins:
            print(f"    {AMBER('●')} {WHITE(title)}: {GRAY(body)}")

    # ── Step 3: Build PDF ─────────────────────────────────────────────────────
    print()
    _step("3️⃣ ", "Building PDF report…")
    t3 = time.time()

    from report_builder import build_report
    try:
        build_report(analysis, {}, out_pdf)
    except Exception as e:
        import traceback
        _err(f"PDF build failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    size_kb = os.path.getsize(out_pdf) / 1024
    _ok(f"PDF built in {time.time()-t3:.2f}s  ({size_kb:.0f} KB)")

    # ── Done ──────────────────────────────────────────────────────────────────
    total = time.time() - t0
    print()
    _rule("═", 68, BLUE)
    print(BOLD("  ✅  Report generation complete!"))
    _step("📄", f"PDF saved → {GREEN(out_pdf)}")
    _step("⏱ ", f"Total time: {total:.2f}s")
    _rule("═", 68, BLUE)
    print()


if __name__ == "__main__":
    main()
