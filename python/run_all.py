# ── RUN THIS FILE TO EXECUTE THE ENTIRE PIPELINE IN ONE GO ───────────────────
# It runs all 4 scripts in the correct order.
# 
# From the python/ folder, run:  python run_all.py

import subprocess
import sys
import os

scripts = [
    ('generate_data.py',   'Step 1/4: Generating synthetic data...'),
    ('rfm_analysis.py',    'Step 2/4: Running RFM analysis...'),
    ('clv_model.py',       'Step 3/4: Building CLV model...'),
    ('cohort_analysis.py', 'Step 4/4: Running cohort analysis...'),
]

print("=" * 60)
print("  E-COMMERCE CLV ANALYSIS — FULL PIPELINE")
print("=" * 60)

for script, message in scripts:
    print(f"\n{message}")
    print("-" * 40)
    result = subprocess.run([sys.executable, script], capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ Error in {script}. Pipeline stopped.")
        sys.exit(1)

print("\n" + "=" * 60)
print("  ✅ ALL STEPS COMPLETE!")
print("=" * 60)
print("""
Output files in data/processed/:
  → rfm_scores.csv          (connect to Tableau)
  → segment_summary.csv     (connect to Tableau)
  → clv_scores.csv          (connect to Tableau)
  → clv_by_segment.csv      (connect to Tableau)
  → cohort_retention.csv    (connect to Tableau)
  → monthly_revenue.csv     (connect to Tableau)
""")