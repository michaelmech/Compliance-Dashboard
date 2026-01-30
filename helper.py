import numpy as np
import pandas as pd

def pad_leading_zeros(numbers, total_len=6):
  """
  Converts a series of numbers to strings and pads them with leading zeros
  to a total length of 'total_len' characters.

  Args:
    numbers: A pandas Series or list of numbers.
    total_len: The desired total length of the padded string.

  Returns:
    A pandas Series of strings, where each string represents a number padded
    with leading zeros.
  """
  # Ensure it's a Series for .apply()
  if not isinstance(numbers, pd.Series):
      numbers = pd.Series(numbers)
      
  return numbers.astype(str).str.zfill(total_len)

def split_comma_values(df, name_col, date_col=None, delimiter=","):
    """
    Explode comma-delimited values in name_col (and optional date_col) into
    separate rows while preserving positional alignment, blanks, and all
    original columns.

    - Trailing commas produce None (blank) entries instead of being dropped.
    - If lengths mismatch, dates are aligned by index; extra names get None dates.
    - No columns are lost; the schema stays the same.
    """
    temp = df.copy()

    def split_preserve_blanks(val):
        if pd.isna(val):
            return []
        parts = [p.strip() for p in str(val).split(delimiter)]
        # Map empty strings to None to represent blanks explicitly
        return [p if p != "" else None for p in parts]

    out_rows = []
    for _, row in temp.iterrows():
        names = split_preserve_blanks(row.get(name_col))
        if not names:
            continue  # nothing to explode for this row

        dates = []
        if date_col:
            dates = split_preserve_blanks(row.get(date_col))

        # Drive by names length; align dates by position; pad with None as needed
        for i, n in enumerate(names):
            new_row = row.copy()
            new_row[name_col] = n
            if date_col:
                new_row[date_col] = dates[i] if i < len(dates) else None
            out_rows.append(new_row)

    # Keep original column order
    return pd.DataFrame(out_rows, columns=df.columns)


supv_view_cols = [
    "ID",
    "Name",
    "OCC",
    "Pay Status",
    "Checklist Descr",
    "Brief Stat",
    "Course Name",
    "Lic/Cert Code",
    "Licensure/Cert Name",
    "Meal Error Type"
]


def format_name(full_name):
        """Convert 'Last, First' to 'First Last'."""
        if pd.isna(full_name):
            return None
        parts = [p.strip() for p in str(full_name).split(",")]
        return " ".join(parts[::-1]) if len(parts) == 2 else full_name

comply_map = {
            'Checklist': ('Checklist Item', None),
            'Courses': ('Course Code', 'Course Expir Date'),
            'Licenses': ('Lic/Cert Code', 'Lic/Cert Expir Date'),
            'Meals': ('Meal Error Type', None)
        }

comply_map_verbose = {
    "Checklist": ('Checklist Descr', None),
    "Courses": ('Course Name', 'Course Expir Date'),
    "Licenses": ('Licensure/Cert Name', 'Lic/Cert Expir Date'),
    "Meals": ('Meal Error Type', None)
    }

pivot_cols=["Unit", "Mgr Level", "Dept Name",'Job Title','Location','Full/Part']