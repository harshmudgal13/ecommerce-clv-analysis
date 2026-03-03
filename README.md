# E-Commerce Customer Lifetime Value & Retention Analysis

## Overview
End-to-end customer analytics system analyzing 3 years of e-commerce 
transaction data across 5,000 customers. Built RFM segmentation, 
predictive CLV modeling, and cohort retention analysis.

## Key Findings
- Top 20% of customers generate 80% of total revenue (Pareto principle confirmed)
- 59.3% of customers churn after their first purchase
- Only 31.7% of customers remain active at month 6
- Champions spend 21x more than Lost customers ($6,604 vs $306 avg)

## Tech Stack
- **Python** — data generation, RFM scoring, CLV modeling (scikit-learn Random Forest)
- **SQL** — cohort queries, RFM scoring, window functions (NTILE, LAG, PARTITION BY)
- **Tableau Public** — interactive 4-page dashboard

## Dashboard
🔗 [Live Tableau Dashboard](https://public.tableau.com/app/profile/harsh.mudgal/viz/E-CommerceCLVRetentionAnalysis/RevenueTrends?publish=yes)

## Project Structure
- `python/generate_data.py` — synthetic e-commerce data generation (5,000 customers, ~50K orders)
- `python/rfm_analysis.py` — RFM scoring and customer segmentation (8 segments)
- `python/clv_model.py` — Random Forest CLV prediction model
- `python/cohort_analysis.py` — cohort retention and churn analysis
- `sql/rfm_queries.sql` — SQL equivalents of all analysis (window functions, CTEs, cohort query)

## How to Run
pip install pandas numpy scikit-learn
cd python
python run_all.py

## RFM Segments

| Segment        | Customers | Avg CLV | Avg Orders |
| -------------- | --------- | ------- | ---------- |
| Champion       | 30.5%     | $6,604  | 26.7       |
| Loyal Customer | 16.7%     | $1,917  | 9.3        |
| At Risk        | 0.5%      | $2,585  | 11.8       |
| Lost           | 26.0%     | $306    | 2.2        |
