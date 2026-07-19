#!/usr/bin/env python3
import csv

with open('/workspace/team2/data/messy_dataset.csv') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = reader.fieldnames

print("=== DATA QUALITY ANOMALIES ===")
for i, row in enumerate(rows, 1):
    age = row.get('age', '').strip()
    if age:
        try:
            age_int = int(age)
            if age_int > 120 or age_int < 0:
                print(f"Row {i}: age={age} is out of plausible range (0-120)")
        except:
            print(f"Row {i}: age is not a valid number")

print()
print("=== DUPLICATE ANALYSIS ===")
profiles = [(i, r['name'].strip(), r['city'].strip(), r['salary'].strip(), r['age'].strip()) for i, r in enumerate(rows, 1)]
for i in range(len(profiles)):
    for j in range(i+1, len(profiles)):
        r1, r2 = profiles[i], profiles[j]
        s = 0
        if r1[1] and r2[1] and r1[1] == r2[1]:
            s += 1
        if r1[2] and r2[2] and r1[2] == r2[2]:
            s += 1
        if r1[3] and r2[3] and r1[3] == r2[3]:
            s += 1
        if r1[4] and r2[4] and r1[4] == r2[4]:
            s += 1
        if s >= 3:
            print(f"Row {r1[0]} and Row {r2[0]}: {s}/4 content fields match")

print()
print("=== CROSS-REFERENCE ===")
with open('/workspace/team2/data/sample_dataset.csv') as f:
    sample_rows = list(csv.DictReader(f))
sample_names = {r['name'] for r in sample_rows if r['name'].strip()}
messy_names = set(r['name'].strip() for r in rows if r['name'].strip())
print(f"Names in both datasets: {sample_names & messy_names}")
print(f"Names only in messy: {messy_names - sample_names}")

# Also check row 7 pattern
print()
print("=== ROW 7 COMPARISON ===")
print("Row 7 raw data: {")
for col in columns:
    val = rows[6][col]
    print(f"  {col}: '{val}'")
print("}")
print("This row has only 'id' populated - likely a header/formatting artifact")
