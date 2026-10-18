
import os
import glob
import numpy as np
import pandas as pd

DATA_DIR = "/content/lendingclub"
OUT_DIR = "/content/lendingclub_outputs"
os.makedirs(OUT_DIR, exist_ok=True)

REJECTED_PATH = glob.glob(
    DATA_DIR + "/**/rejected_2007_to_2018Q4.csv.gz",
    recursive=True
)[0]

ACCEPTED_PATH = glob.glob(
    DATA_DIR + "/**/accepted_2007_to_2018Q4.csv.gz",
    recursive=True
)[0]

CHUNK_SIZE = 50_000
SAMPLE_SIZE = 100_000
SEED = 42

rng = np.random.default_rng(SEED)

def find_col(columns, candidates):
    """Match actual CSV column names, ignoring case and whitespace."""
    lookup = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None

def standardize_purpose(s):
    s = s.fillna("unknown").astype(str).str.strip().str.lower()
    s = s.str.replace(r"[_-]+", " ", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True)

    aliases = {
        "debt consolidation": "debt_consolidation",
        "credit card": "credit_card",
        "credit card refinancing": "credit_card",
        "car financing": "car",
        "moving and relocation": "moving",
        "medical expenses": "medical",
        "major purchase": "major_purchase",
    }
    return s.replace(aliases)

def standardize_employment(s):
    return (
        s.fillna("unknown").astype(str).str.strip().str.lower()
         .replace({"nan": "unknown", "": "unknown"})
    )

def amount_band(s):
    x = pd.to_numeric(
        s.astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )
    return pd.cut(
        x,
        bins=[-np.inf, 5000, 10000, 15000, 20000, 25000, np.inf],
        labels=["<=5k", "5-10k", "10-15k",
                "15-20k", "20-25k", ">25k"]
    ).astype("string").fillna("Unknown")

def dti_band(s):
    x = pd.to_numeric(
        s.astype(str).str.replace("%", "", regex=False),
        errors="coerce"
    )
    return pd.cut(
        x,
        bins=[-np.inf, 10, 20, 30, 40, np.inf],
        labels=["<=10", "10-20", "20-30", "30-40", ">40"]
    ).astype("string").fillna("Unknown")

def terminal_outcome(s):
    x = s.fillna("").astype(str).str.lower().str.strip()
    out = pd.Series("other", index=s.index, dtype="object")
    out[x.str.contains("fully paid", regex=False)] = "paid"
    out[x.str.contains("charged off", regex=False)] = "default"
    out[x.eq("default")] = "default"
    return out

# Read headers to map the real schema.
rcols = pd.read_csv(REJECTED_PATH, compression="gzip", nrows=0).columns
acols = pd.read_csv(ACCEPTED_PATH, compression="gzip", nrows=0).columns

R = {
    "amount": find_col(rcols, ["Amount Requested"]),
    "date": find_col(rcols, ["Application Date"]),
    "purpose": find_col(rcols, ["Loan Title"]),
    "dti": find_col(rcols, ["Debt-To-Income Ratio"]),
    "state": find_col(rcols, ["State"]),
    "employment": find_col(rcols, ["Employment Length"]),
}

A = {
    "amount": find_col(acols, ["loan_amnt"]),
    "date": find_col(acols, ["issue_d"]),
    "purpose": find_col(acols, ["purpose"]),
    "dti": find_col(acols, ["dti"]),
    "state": find_col(acols, ["addr_state"]),
    "employment": find_col(acols, ["emp_length"]),
    "status": find_col(acols, ["loan_status"]),
}

print("Rejected field mapping:", R)
print("Accepted field mapping:", A)

if any(v is None for v in R.values()):
    raise ValueError("Rejected schema differs from expected fields; inspect R mapping.")
if any(v is None for v in A.values()):
    raise ValueError("Accepted schema differs from expected fields; inspect A mapping.")

# Store aggregate counts, not every original row.
rejected_counts = {}
accepted_counts = {}
samples = {"rejected": pd.DataFrame(), "accepted": pd.DataFrame()}
totals = {"rejected": 0, "accepted": 0}
missing_counts = {"rejected": {}, "accepted": {}}

def add_sample(source, df):
    """Uniform sample using random priorities, bounded in memory."""
    if df.empty:
        return
    df = df.copy()
    df["_priority"] = rng.random(len(df))
    combined = pd.concat([samples[source], df], ignore_index=True)
    samples[source] = (
        combined.nsmallest(SAMPLE_SIZE, "_priority")
                 .reset_index(drop=True)
    )

def process_file(path, source, mapping):
    usecols = list(dict.fromkeys(mapping.values()))
    chunk_number = 0

    for chunk in pd.read_csv(
        path, compression="gzip", usecols=usecols,
        dtype=str, chunksize=CHUNK_SIZE, low_memory=False
    ):
        chunk_number += 1
        n = len(chunk)
        totals[source] += n

        # Record missingness in source fields.
        for key, col in mapping.items():
            missing_counts[source][key] = (
                missing_counts[source].get(key, 0)
                + int(chunk[col].isna().sum())
            )

        df = pd.DataFrame(index=chunk.index)
        df["source_type"] = source
        df["amount"] = pd.to_numeric(
            chunk[mapping["amount"]].str.replace(",", "", regex=False),
            errors="coerce"
        )
        df["dti"] = pd.to_numeric(
            chunk[mapping["dti"]].str.replace("%", "", regex=False),
            errors="coerce"
        )
        df["purpose"] = standardize_purpose(chunk[mapping["purpose"]])
        df["employment_length"] = standardize_employment(
            chunk[mapping["employment"]]
        )
        df["state"] = (
            chunk[mapping["state"]].fillna("unknown")
            .astype(str).str.strip().str.upper()
        )
        df["record_date"] = chunk[mapping["date"]].fillna("").astype(str)
        df["amount_band"] = amount_band(df["amount"])
        df["dti_band"] = dti_band(df["dti"])

        if source == "accepted":
            df["loan_status"] = chunk[mapping["status"]].fillna("")
            df["outcome_group"] = terminal_outcome(df["loan_status"])
        else:
            df["loan_status"] = ""
            df["outcome_group"] = ""

        keys = ["dti_band", "amount_band", "purpose", "employment_length"]

        if source == "rejected":
            # Full-data rejected segment counts.
            counts = df.groupby(keys, dropna=False).size()
            for key, value in counts.items():
                rejected_counts[key] = rejected_counts.get(key, 0) + int(value)

        else:
            # Full-data accepted counts, including terminal outcomes.
            counts = (
                df.groupby(keys + ["outcome_group"], dropna=False)
                  .size()
            )
            for key, value in counts.items():
                accepted_counts[key] = accepted_counts.get(key, 0) + int(value)

        add_sample(source, df)

        if chunk_number % 10 == 0:
            print(f"{source}: processed {totals[source]:,} rows")

    print(f"{source}: COMPLETE — {totals[source]:,} rows")

process_file(REJECTED_PATH, "rejected", R)
process_file(ACCEPTED_PATH, "accepted", A)

# Export exact full-data aggregates.
key_cols = ["dti_band", "amount_band", "purpose", "employment_length"]

rej = pd.DataFrame([
    (*key, count) for key, count in rejected_counts.items()
], columns=key_cols + ["rejected_applications"])

acc = pd.DataFrame([
    (*key, outcome, count)
    for (*key, outcome), count in accepted_counts.items()
], columns=key_cols + ["outcome_group", "loan_count"])

rej.to_csv(f"{OUT_DIR}/rejected_full_counts.csv", index=False)
acc.to_csv(f"{OUT_DIR}/accepted_full_outcomes.csv", index=False)

# Export source quality report.
quality_rows = []
for source in totals:
    for field, missing in missing_counts[source].items():
        quality_rows.append({
            "source_type": source,
            "total_rows": totals[source],
            "field": field,
            "missing_rows": missing,
            "missing_pct": round(100 * missing / totals[source], 4)
        })

pd.DataFrame(quality_rows).to_csv(
    f"{OUT_DIR}/data_quality.csv", index=False
)

# Export manageable sample for Splunk.
sample_df = pd.concat(samples.values(), ignore_index=True)
sample_df = sample_df.drop(columns=["_priority"], errors="ignore")
sample_df.to_csv(f"{OUT_DIR}/lendingclub_splunk_sample.csv", index=False)

print("\nFULL SOURCE ROW COUNTS:", totals)
print("Rejected segments:", len(rej))
print("Accepted segment/outcome rows:", len(acc))
print("Sample rows exported:", len(sample_df))
print("Outputs:", OUT_DIR)
