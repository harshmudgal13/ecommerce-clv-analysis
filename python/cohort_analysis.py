import pandas as pd
import numpy as np
import os

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_data():
    customers = pd.read_csv('../data/raw/customers.csv', parse_dates=['signup_date'])
    orders    = pd.read_csv('../data/raw/orders.csv',    parse_dates=['order_date'])
    orders    = orders[orders['is_returned'] == False]
    return customers, orders

# ── BUILD COHORT TABLE ────────────────────────────────────────────────────────
def build_cohort_table(customers, orders):
    """
    Groups customers by the month they first bought (cohort month).
    Then tracks how many from that cohort are still active each month after.
    
    Example output row:
    Cohort: Jan 2021 → Month 0: 100% → Month 1: 60% → Month 6: 35%
    """
    
    # Get each customer's first purchase date (cohort assignment)
    first_purchase = orders.groupby('customer_id')['order_date'].min().reset_index()
    first_purchase.columns = ['customer_id', 'first_purchase_date']
    first_purchase['cohort_month'] = first_purchase['first_purchase_date'].dt.to_period('M')
    
    # Merge cohort info into all orders
    orders_with_cohort = orders.merge(first_purchase[['customer_id', 'cohort_month']], 
                                       on='customer_id', how='left')
    
    # Calculate which month number each order falls in (0 = cohort month, 1 = month after, etc.)
    orders_with_cohort['order_month'] = orders_with_cohort['order_date'].dt.to_period('M')
    orders_with_cohort['month_number'] = (
        orders_with_cohort['order_month'].astype(int) - 
        orders_with_cohort['cohort_month'].astype(int)
    )
    
    # Count unique active customers per cohort per month
    cohort_data = orders_with_cohort.groupby(['cohort_month', 'month_number'])['customer_id'].nunique().reset_index()
    cohort_data.columns = ['cohort_month', 'month_number', 'active_customers']
    
    # Pivot into matrix: rows = cohorts, columns = month numbers
    cohort_pivot = cohort_data.pivot_table(
        index='cohort_month', 
        columns='month_number', 
        values='active_customers'
    )
    
    # Retention rates: divide each cell by the cohort size (month 0)
    cohort_size = cohort_pivot[0]
    retention_matrix = cohort_pivot.divide(cohort_size, axis=0).round(3) * 100
    
    return cohort_pivot, retention_matrix, cohort_size

# ── MONTHLY REVENUE COHORT ────────────────────────────────────────────────────
def revenue_by_cohort(orders, first_purchase):
    """
    Same as retention but tracks revenue instead of customer count.
    Shows: how much does each cohort earn us over time?
    """
    orders_with_cohort = orders.merge(first_purchase[['customer_id', 'cohort_month']], 
                                       on='customer_id', how='left')
    
    orders_with_cohort['order_month'] = orders_with_cohort['order_date'].dt.to_period('M')
    orders_with_cohort['month_number'] = (
        orders_with_cohort['order_month'].astype(int) - 
        orders_with_cohort['cohort_month'].astype(int)
    )
    
    revenue_cohort = orders_with_cohort.groupby(['cohort_month', 'month_number'])['order_value'].sum().reset_index()
    revenue_cohort.columns = ['cohort_month', 'month_number', 'revenue']
    
    revenue_pivot = revenue_cohort.pivot_table(
        index='cohort_month',
        columns='month_number',
        values='revenue'
    ).round(2)
    
    return revenue_pivot

# ── CHURN RATE CALCULATION ────────────────────────────────────────────────────
def calculate_churn(retention_matrix):
    """
    Churn rate = 1 - retention rate at each month.
    We look at Month 1 churn specifically (how many drop off after first purchase).
    """
    if 1 in retention_matrix.columns:
        month1_retention = retention_matrix[1].mean()
        month1_churn     = 100 - month1_retention
        print(f"\n📉 Average Month-1 Churn Rate: {month1_churn:.1f}%")
        print(f"   (This means {month1_churn:.1f}% of customers don't buy again after first purchase)")
    
    if 6 in retention_matrix.columns:
        month6_retention = retention_matrix[6].dropna().mean()
        print(f"📉 Average Month-6 Retention: {month6_retention:.1f}%")

# ── FLATTEN FOR TABLEAU ───────────────────────────────────────────────────────
def flatten_for_tableau(cohort_pivot, retention_matrix):
    """
    Tableau needs flat (long format) data, not pivot tables.
    This converts the matrix into rows.
    """
    # Retention flat
    retention_flat = retention_matrix.reset_index().melt(
        id_vars='cohort_month', 
        var_name='month_number', 
        value_name='retention_rate'
    )
    retention_flat['cohort_month'] = retention_flat['cohort_month'].astype(str)
    retention_flat = retention_flat.dropna()
    
    # Customer count flat
    count_flat = cohort_pivot.reset_index().melt(
        id_vars='cohort_month',
        var_name='month_number',
        value_name='active_customers'
    )
    count_flat['cohort_month'] = count_flat['cohort_month'].astype(str)
    count_flat = count_flat.dropna()
    
    return retention_flat, count_flat

# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Loading data...")
    customers, orders = load_data()
    
    print("Building cohort table...")
    cohort_pivot, retention_matrix, cohort_size = build_cohort_table(customers, orders)
    
    # Get first purchase for revenue cohort
    first_purchase = orders.groupby('customer_id')['order_date'].min().reset_index()
    first_purchase.columns = ['customer_id', 'first_purchase_date']
    first_purchase['cohort_month'] = first_purchase['first_purchase_date'].dt.to_period('M')
    
    print("Building revenue cohort...")
    revenue_pivot = revenue_by_cohort(orders, first_purchase)
    
    print("Calculating churn rates...")
    calculate_churn(retention_matrix)
    
    print("Flattening data for Tableau...")
    retention_flat, count_flat = flatten_for_tableau(cohort_pivot, retention_matrix)
    
    # Monthly revenue summary (for Tableau line chart)
    monthly_revenue = orders.copy()
    monthly_revenue['month'] = monthly_revenue['order_date'].dt.to_period('M').astype(str)
    monthly_revenue = monthly_revenue.groupby('month').agg(
        total_revenue    = ('order_value', 'sum'),
        total_orders     = ('order_id',    'count'),
        unique_customers = ('customer_id', 'nunique')
    ).reset_index()
    monthly_revenue['avg_order_value'] = (monthly_revenue['total_revenue'] / 
                                           monthly_revenue['total_orders']).round(2)
    
    # Save
    os.makedirs('../data/processed', exist_ok=True)
    retention_flat.to_csv('../data/processed/cohort_retention.csv',  index=False)
    count_flat.to_csv('../data/processed/cohort_counts.csv',          index=False)
    monthly_revenue.to_csv('../data/processed/monthly_revenue.csv',   index=False)
    
    # Save retention matrix as-is (useful for reference)
    retention_matrix.to_csv('../data/processed/retention_matrix.csv')
    
    print("\n✅ Cohort analysis complete! Files saved to data/processed/")