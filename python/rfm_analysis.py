import pandas as pd
import numpy as np
from datetime import datetime
import os

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_data():
    customers = pd.read_csv('../data/raw/customers.csv', parse_dates=['signup_date'])
    orders    = pd.read_csv('../data/raw/orders.csv',    parse_dates=['order_date'])
    
    # Remove returned orders from analysis
    orders = orders[orders['is_returned'] == False]
    
    return customers, orders

# ── CALCULATE RFM METRICS ─────────────────────────────────────────────────────
def calculate_rfm(orders, snapshot_date=None):
    """
    Calculates raw R, F, M values for each customer.
    snapshot_date = the 'today' we measure from (use last date in data)
    """
    if snapshot_date is None:
        snapshot_date = orders['order_date'].max() + pd.Timedelta(days=1)
    
    rfm = orders.groupby('customer_id').agg(
        last_order_date = ('order_date',  'max'),       # most recent purchase
        frequency       = ('order_id',    'count'),     # number of orders
        monetary        = ('order_value', 'sum')        # total spend
    ).reset_index()
    
    # Recency = days since last purchase (lower is better)
    rfm['recency'] = (snapshot_date - rfm['last_order_date']).dt.days
    
    return rfm

# ── SCORE RFM (1-5 quintiles) ─────────────────────────────────────────────────
def score_rfm(rfm):
    """
    Assigns scores 1-5 to each R, F, M value using quintiles.
    For Recency: score 5 = most recent (LOWER days = BETTER)
    For Frequency and Monetary: score 5 = highest (MORE = BETTER)
    """
    rfm = rfm.copy()
    
    # Recency: reversed because lower days = more recent = better score
    rfm['r_score'] = pd.qcut(rfm['recency'],    q=5, labels=[5,4,3,2,1], duplicates='drop').astype(int)
    rfm['f_score'] = pd.qcut(rfm['frequency'],  q=5, labels=[1,2,3,4,5], duplicates='drop').astype(int)
    rfm['m_score'] = pd.qcut(rfm['monetary'],   q=5, labels=[1,2,3,4,5], duplicates='drop').astype(int)
    
    # Combined RFM score string e.g. "555" or "311"
    rfm['rfm_score'] = rfm['r_score'].astype(str) + rfm['f_score'].astype(str) + rfm['m_score'].astype(str)
    
    # Overall score (simple average)
    rfm['rfm_total'] = (rfm['r_score'] + rfm['f_score'] + rfm['m_score']) / 3
    
    return rfm

# ── ASSIGN SEGMENTS ───────────────────────────────────────────────────────────
def assign_segment(row):
    """
    Maps RFM scores to human-readable segment names.
    These rules are industry-standard segmentation logic.
    """
    r, f, m = row['r_score'], row['f_score'], row['m_score']
    
    if r >= 4 and f >= 4 and m >= 4:
        return 'Champion'
    elif r >= 3 and f >= 3 and m >= 3:
        return 'Loyal Customer'
    elif r >= 4 and f <= 2:
        return 'New Customer'
    elif r >= 3 and f >= 2 and m >= 4:
        return 'Potential Loyalist'
    elif r <= 2 and f >= 4 and m >= 4:
        return 'At Risk'
    elif r <= 2 and f >= 3 and m >= 3:
        return 'Needs Attention'
    elif r <= 2 and f <= 2 and m <= 2:
        return 'Lost'
    else:
        return 'Others'

# ── PARETO ANALYSIS (80/20 rule) ──────────────────────────────────────────────
def pareto_analysis(rfm):
    """
    Finds what % of customers drive 80% of revenue.
    Classic business insight: top 20% = 80% of revenue.
    """
    rfm_sorted = rfm.sort_values('monetary', ascending=False).copy()
    rfm_sorted['cumulative_revenue'] = rfm_sorted['monetary'].cumsum()
    total_revenue = rfm_sorted['monetary'].sum()
    rfm_sorted['cumulative_pct'] = rfm_sorted['cumulative_revenue'] / total_revenue * 100
    rfm_sorted['customer_rank_pct'] = range(1, len(rfm_sorted) + 1)
    rfm_sorted['customer_rank_pct'] = rfm_sorted['customer_rank_pct'] / len(rfm_sorted) * 100
    
    # Find the threshold where 80% of revenue is hit
    threshold = rfm_sorted[rfm_sorted['cumulative_pct'] >= 80].iloc[0]
    print(f"\n📊 Pareto Insight:")
    print(f"   Top {threshold['customer_rank_pct']:.1f}% of customers drive 80% of revenue")
    
    return rfm_sorted

# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Loading data...")
    customers, orders = load_data()
    
    print("Calculating RFM metrics...")
    rfm = calculate_rfm(orders)
    
    print("Scoring customers...")
    rfm = score_rfm(rfm)
    
    print("Assigning segments...")
    rfm['segment'] = rfm.apply(assign_segment, axis=1)
    
    # Merge with customer details
    rfm = rfm.merge(customers[['customer_id', 'signup_date', 'location', 'age_group', 'gender']], 
                    on='customer_id', how='left')
    
    # Pareto analysis
    rfm_pareto = pareto_analysis(rfm)
    
    # Segment summary
    segment_summary = rfm.groupby('segment').agg(
        customer_count  = ('customer_id', 'count'),
        avg_recency     = ('recency',     'mean'),
        avg_frequency   = ('frequency',   'mean'),
        avg_monetary    = ('monetary',    'mean'),
        total_revenue   = ('monetary',    'sum')
    ).round(2).reset_index()
    
    segment_summary['revenue_pct'] = (segment_summary['total_revenue'] / 
                                       segment_summary['total_revenue'].sum() * 100).round(1)
    
    print("\n📋 Segment Summary:")
    print(segment_summary.to_string(index=False))
    
    # Save outputs
    os.makedirs('../data/processed', exist_ok=True)
    rfm.to_csv('../data/processed/rfm_scores.csv', index=False)
    segment_summary.to_csv('../data/processed/segment_summary.csv', index=False)
    rfm_pareto.to_csv('../data/processed/pareto_analysis.csv', index=False)
    
    print("\n✅ RFM analysis complete! Files saved to data/processed/")