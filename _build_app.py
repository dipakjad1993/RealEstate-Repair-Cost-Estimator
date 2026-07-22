# This script reads app.py, replaces specific page functions with enhanced versions,
# and writes back. Run with: python _build_app.py

import os

fpath = r'C:\realestate_repair_cost_estimator\app.py'

with open(fpath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line numbers for all defs
def get_def_lines():
    defs = {}
    current = None
    for i, l in enumerate(lines):
        if l.startswith('def '):
            name = l.split('(')[0].replace('def ', '').strip()
            if name not in ('_generate_sample_findings', '_generate_sample_report_text'):
                current = name
                defs[current] = i
    return defs

defs = get_def_lines()

# Read old functions to get exact boundaries
func_ranges = {}
current = None
start = 0
for i, l in enumerate(lines):
    if l.startswith('def '):
        name = l.split('(')[0].replace('def ', '').strip()
        if name in ('_generate_sample_findings', '_generate_sample_report_text'):
            continue
        if current:
            func_ranges[current] = (start, i)
        current = name
        start = i
    elif i == len(lines) - 1:
        if current:
            func_ranges[current] = (start, i+1)

print("Function ranges:")
for name, (s, e) in sorted(func_ranges.items(), key=lambda x: x[1][0]):
    print(f"  {name}: {s}-{e-1}")

# Now we need to write replacement functions.
# Strategy: write each new function to a separate file, then read them back and replace.
