import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
import os

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_data():
    rfm     = pd.read_csv('../data/processed/rfm_scores.csv',  parse_dates=['last_order_date', 'signup_date'])
    orders  = pd.read_csv('../data/raw/orders.csv',            parse_dates=['order_date'])
    orders  = orders[orders['is_returned'] == False]
    return rfm, orders

# ── FEATURE ENGINEERING ───────────────────────────────────────────────────────
def build_features(rfm, orders):
    """
    Creates features (inputs) for our CLV prediction model.
    The model will learn: given these features → predict total future spend.
    """
    
    # Average order value per customer
    aov = orders.groupby('customer_id')['order_value'].mean().reset_index()
    aov.columns = ['customer_id', 'avg_order_value']
    
    # Average days between orders (purchase velocity)
    orders_sorted = orders.sort_values(['customer_id', 'order_date'])
    orders_sorted['prev_order_date'] = orders_sorted.groupby('customer_id')['order_date'].shift(1)
    orders_sorted['days_between']    = (orders_sorted['order_date'] - orders_sorted['prev_order_date']).dt.days
    
    avg_days_between = orders_sorted.groupby('customer_id')['days_between'].mean().reset_index()
    avg_days_between.columns = ['customer_id', 'avg_days_between_orders']
    
    # Number of categories purchased from (breadth of engagement)
    category_count = orders.groupby('customer_id')['category'].nunique().reset_index()
    category_count.columns = ['customer_id', 'category_diversity']
    
    # Spend trend: is the customer spending more or less over time?
    # We compare first half vs second half of their purchase history
    def spend_trend(group):
        if len(group) < 4:
            return 0.0   # not enough data
        mid = len(group) // 2
        first_half_avg  = group.iloc[:mid]['order_value'].mean()
        second_half_avg = group.iloc[mid:]['order_value'].mean()
        return second_half_avg - first_half_avg   # positive = spending more
    
    trend = orders_sorted.groupby('customer_id').apply(spend_trend).reset_index()
    trend.columns = ['customer_id', 'spend_trend']
    
    # Customer age (days since signup)
    rfm['customer_age_days'] = (pd.Timestamp('2024-01-01') - rfm['signup_date']).dt.days
    
    # Merge all features
    features = rfm[['customer_id', 'recency', 'frequency', 'monetary', 
                     'r_score', 'f_score', 'm_score', 'rfm_total', 'customer_age_days']].copy()
    
    features = features.merge(aov,               on='customer_id', how='left')
    features = features.merge(avg_days_between,  on='customer_id', how='left')
    features = features.merge(category_count,    on='customer_id', how='left')
    features = features.merge(trend,             on='customer_id', how='left')
    
    # Fill NaN (customers with only 1 order have no days_between)
    features['avg_days_between_orders'] = features['avg_days_between_orders'].fillna(365)
    features['spend_trend']             = features['spend_trend'].fillna(0)
    
    return features

# ── BUILD CLV TARGET ──────────────────────────────────────────────────────────
def calculate_simple_clv(features):
    """
    Simple CLV formula: AOV × (365 / avg_days_between_orders) × projected_years
    This gives an estimated annual CLV based on purchase behavior.
    projected_years = 1 year
    """
    features = features.copy()
    
    # Purchases per year (frequency normalized to annual)
    features['purchases_per_year'] = 365 / features['avg_days_between_orders'].clip(lower=7)
    
    # Simple CLV (1 year)
    features['clv_simple'] = (features['avg_order_value'] * features['purchases_per_year']).round(2)
    
    # Cap extreme values (outliers)
    upper_cap = features['clv_simple'].quantile(0.99)
    features['clv_simple'] = features['clv_simple'].clip(upper=upper_cap)
    
    return features

# ── TRAIN PREDICTIVE MODEL ────────────────────────────────────────────────────
def train_clv_model(features):
    """
    Trains a Random Forest model to predict CLV.
    Uses RFM scores + engineered features as inputs.
    We use the simple CLV as our target (what we're trying to predict).
    In real life you'd use actual future revenue as the target.
    """
    
    feature_cols = ['recency', 'frequency', 'r_score', 'f_score', 'm_score',
                    'avg_order_value', 'avg_days_between_orders', 
                    'category_diversity', 'spend_trend', 'customer_age_days']
    
    X = features[feature_cols].fillna(0)
    y = features['clv_simple']
    
    # Split: 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Random Forest model
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # Predict on test set
    y_pred = model.predict(X_test)
    
    # Evaluation
    mae  = mean_absolute_error(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred) * 100
    
    print(f"\n🤖 CLV Model Performance:")
    print(f"   MAE  (Mean Absolute Error):            ${mae:.2f}")
    print(f"   MAPE (Mean Absolute % Error):          {mape:.1f}%")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature':    feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n📊 Feature Importance (what drives CLV predictions):")
    print(importance.to_string(index=False))
    
    # Predict CLV for ALL customers
    features['clv_predicted'] = model.predict(X).round(2)
    
    # CLV tier segmentation
    features['clv_tier'] = pd.qcut(
        features['clv_predicted'], 
        q=4, 
        labels=['Low Value', 'Medium Value', 'High Value', 'Premium']
    )
    
    return features, model, importance

# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Loading data...")
    rfm, orders = load_data()
    
    print("Engineering features...")
    features = build_features(rfm, orders)
    
    print("Calculating simple CLV...")
    features = calculate_simple_clv(features)
    
    print("Training CLV prediction model...")
    features, model, importance = train_clv_model(features)
    
    # Merge segment info back
    rfm_segments = rfm[['customer_id', 'segment', 'location', 'age_group', 'gender']]
    final = features.merge(rfm_segments, on='customer_id', how='left')
    
    # Summary by segment
    clv_by_segment = final.groupby('segment').agg(
        customers       = ('customer_id',    'count'),
        avg_clv         = ('clv_predicted',  'mean'),
        total_clv       = ('clv_predicted',  'sum'),
        avg_order_value = ('avg_order_value','mean')
    ).round(2).reset_index().sort_values('avg_clv', ascending=False)
    
    print("\n💰 Predicted CLV by Segment:")
    print(clv_by_segment.to_string(index=False))
    
    # Save
    final.to_csv('../data/processed/clv_scores.csv', index=False)
    importance.to_csv('../data/processed/feature_importance.csv', index=False)
    clv_by_segment.to_csv('../data/processed/clv_by_segment.csv', index=False)
    
    print("\n✅ CLV model complete! Files saved to data/processed/")