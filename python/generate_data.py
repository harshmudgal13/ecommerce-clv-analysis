import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Set seed so data is reproducible (same result every time you run it)
np.random.seed(42)
random.seed(42)

# ── CONFIG ────────────────────────────────────────────────────────────────────
NUM_CUSTOMERS = 5000
START_DATE = datetime(2021, 1, 1)
END_DATE = datetime(2023, 12, 31)

CATEGORIES = ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books', 'Beauty']
LOCATIONS = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
             'London', 'Toronto', 'Sydney', 'Berlin', 'Paris']

# Price ranges per category (min, max)
CATEGORY_PRICES = {
    'Electronics':   (50, 1500),
    'Clothing':      (20, 300),
    'Home & Garden': (15, 500),
    'Sports':        (25, 400),
    'Books':         (10, 60),
    'Beauty':        (10, 150)
}

# ── GENERATE CUSTOMERS ────────────────────────────────────────────────────────
def generate_customers(n):
    customer_ids = [f'CUST_{str(i).zfill(5)}' for i in range(1, n + 1)]
    
    # Signup dates spread across 2021-2023
    signup_dates = [START_DATE + timedelta(days=random.randint(0, 1000)) for _ in range(n)]
    
    customers = pd.DataFrame({
        'customer_id':   customer_ids,
        'signup_date':   signup_dates,
        'location':      [random.choice(LOCATIONS) for _ in range(n)],
        'age_group':     [random.choice(['18-25', '26-35', '36-45', '46-55', '55+']) for _ in range(n)],
        'gender':        [random.choice(['Male', 'Female', 'Other']) for _ in range(n)]
    })
    
    return customers

# ── GENERATE ORDERS ───────────────────────────────────────────────────────────
def generate_orders(customers):
    orders = []
    order_id = 1
    
    for _, customer in customers.iterrows():
        # Different customer types: champions buy a lot, lost customers buy once
        customer_type = np.random.choice(
            ['champion', 'loyal', 'at_risk', 'lost'],
            p=[0.15, 0.25, 0.30, 0.30]   # 30% lost, 30% at risk, etc.
        )
        
        # Number of orders based on customer type
        if customer_type == 'champion':
            num_orders = random.randint(20, 60)
        elif customer_type == 'loyal':
            num_orders = random.randint(8, 20)
        elif customer_type == 'at_risk':
            num_orders = random.randint(3, 8)
        else:  # lost
            num_orders = random.randint(1, 3)
        
        # Last order date based on type (champions bought recently, lost customers didn't)
        if customer_type == 'champion':
            last_order_cutoff = END_DATE - timedelta(days=60)   # within last 60 days
        elif customer_type == 'loyal':
            last_order_cutoff = END_DATE - timedelta(days=120)
        elif customer_type == 'at_risk':
            last_order_cutoff = END_DATE - timedelta(days=240)
        else:
            last_order_cutoff = END_DATE - timedelta(days=300)  # very old
        
        # Generate order dates
        order_dates = sorted([
            customer['signup_date'] + timedelta(days=random.randint(1, 
                max(1, (last_order_cutoff - customer['signup_date']).days)))
            for _ in range(num_orders)
        ])
        
        # Clamp to our date range
        order_dates = [d for d in order_dates if START_DATE <= d <= END_DATE]
        if not order_dates:
            order_dates = [customer['signup_date'] + timedelta(days=random.randint(1, 30))]
        
        for order_date in order_dates:
            category = random.choice(CATEGORIES)
            min_price, max_price = CATEGORY_PRICES[category]
            
            # Champions tend to spend more
            if customer_type == 'champion':
                order_value = round(random.uniform(min_price * 1.5, max_price), 2)
            else:
                order_value = round(random.uniform(min_price, max_price * 0.8), 2)
            
            orders.append({
                'order_id':      f'ORD_{str(order_id).zfill(7)}',
                'customer_id':   customer['customer_id'],
                'order_date':    order_date,
                'order_value':   order_value,
                'category':      category,
                'quantity':      random.randint(1, 5),
                'is_returned':   random.random() < 0.05   # 5% return rate
            })
            order_id += 1
    
    return pd.DataFrame(orders)

# ── GENERATE PRODUCTS ─────────────────────────────────────────────────────────
def generate_products():
    products = []
    for category in CATEGORIES:
        for i in range(1, 11):  # 10 products per category
            min_price, max_price = CATEGORY_PRICES[category]
            products.append({
                'product_id':   f'{category[:3].upper()}_{str(i).zfill(3)}',
                'product_name': f'{category} Product {i}',
                'category':     category,
                'unit_price':   round(random.uniform(min_price, max_price), 2)
            })
    return pd.DataFrame(products)

# ── RUN AND SAVE ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Generating customers...")
    customers = generate_customers(NUM_CUSTOMERS)
    
    print("Generating orders...")
    orders = generate_orders(customers)
    
    print("Generating products...")
    products = generate_products()
    
    # Save raw data
    os.makedirs('../data/raw', exist_ok=True)
    customers.to_csv('../data/raw/customers.csv', index=False)
    orders.to_csv('../data/raw/orders.csv', index=False)
    products.to_csv('../data/raw/products.csv', index=False)
    
    print(f"\n✅ Data generated successfully!")
    print(f"   Customers : {len(customers):,}")
    print(f"   Orders    : {len(orders):,}")
    print(f"   Products  : {len(products):,}")
    print(f"   Date range: {orders['order_date'].min().date()} → {orders['order_date'].max().date()}")
    print(f"\n   Files saved to data/raw/")