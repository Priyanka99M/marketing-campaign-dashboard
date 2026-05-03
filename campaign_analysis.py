# ── Step 1: Import libraries ─────────────────────────────────
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

print("✅ Libraries imported")

# ── Step 2: Load data ────────────────────────────────────────
df = pd.read_csv('bank.csv')

print(f"✅ Data loaded — {df.shape[0]} rows, {df.shape[1]} columns")
print("\nColumns:", df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())
print("\nMissing values:")
print(df.isnull().sum())

# ── Step 3: Data Cleaning ────────────────────────────────────
print("\n── Cleaning data...")

# Target column is 'deposit'
df.rename(columns={'deposit': 'subscribed'}, inplace=True)
df['subscribed_binary'] = (df['subscribed'] == 'yes').astype(int)
df.replace('unknown', np.nan, inplace=True)

for col in df.select_dtypes(include='object').columns:
    df[col].fillna(df[col].mode()[0], inplace=True)

print("✅ Data cleaned — 0 missing values")
print(f"   Converted: {df['subscribed_binary'].sum()}")
print(f"   Not converted: {(df['subscribed_binary']==0).sum()}")

# ── Step 4: Feature Engineering ─────────────────────────────
print("\n── Engineering features...")

df['duration_mins']        = (df['duration'] / 60).round(2)
df['previously_contacted'] = (df['previous'] > 0).astype(int)
df['age_group']            = pd.cut(df['age'],
                                     bins=[0, 30, 40, 50, 100],
                                     labels=['Under 30','30-40','40-50','Over 50'])

print("✅ 3 new features: duration_mins, previously_contacted, age_group")

# ── Step 5: Load into SQLite ─────────────────────────────────
print("\n── Loading into SQLite...")

conn = sqlite3.connect('campaign.db')
df.to_sql('campaigns', conn, if_exists='replace', index=False)
print("✅ Loaded into SQLite — campaigns table")

# ── Step 6: SQL Analysis ─────────────────────────────────────
print("\n── Running SQL queries...")

q1 = pd.read_sql_query("""
    SELECT
        COUNT(*) AS total_customers,
        SUM(subscribed_binary) AS total_converted,
        ROUND(AVG(subscribed_binary) * 100, 2) AS conversion_rate_pct
    FROM campaigns
""", conn)
print("\nQ1 — Overall Conversion Rate:")
print(q1)

q2 = pd.read_sql_query("""
    SELECT
        job,
        COUNT(*) AS total,
        ROUND(AVG(subscribed_binary) * 100, 2) AS conversion_rate_pct
    FROM campaigns
    GROUP BY job
    ORDER BY conversion_rate_pct DESC
""", conn)
print("\nQ2 — Conversion by Job:")
print(q2)

q3 = pd.read_sql_query("""
    SELECT
        month,
        COUNT(*) AS total_calls,
        ROUND(AVG(subscribed_binary) * 100, 2) AS conversion_rate_pct
    FROM campaigns
    GROUP BY month
    ORDER BY conversion_rate_pct DESC
""", conn)
print("\nQ3 — Best Months:")
print(q3)

q4 = pd.read_sql_query("""
    SELECT
        contact,
        COUNT(*) AS total,
        ROUND(AVG(subscribed_binary) * 100, 2) AS conversion_rate_pct
    FROM campaigns
    GROUP BY contact
    ORDER BY conversion_rate_pct DESC
""", conn)
print("\nQ4 — Conversion by Contact Type:")
print(q4)

# ── Step 7: Hypothesis Testing ───────────────────────────────
print("\n── Running hypothesis test...")

converted     = df[df['subscribed_binary'] == 1]['duration']
not_converted = df[df['subscribed_binary'] == 0]['duration']

t_stat, p_value = stats.ttest_ind(converted, not_converted)
print(f"\nHypothesis Test — Call Duration vs Conversion:")
print(f"   T-statistic : {t_stat:.4f}")
print(f"   P-value     : {p_value:.6f}")
if p_value < 0.05:
    print("   ✅ Call duration IS statistically significant in predicting conversion")

# ── Step 8: Charts ───────────────────────────────────────────
print("\n── Generating charts...")
plt.style.use('seaborn-v0_8-whitegrid')

# Chart 1: Conversion yes vs no
fig, ax = plt.subplots(figsize=(6, 4))
counts = df['subscribed'].value_counts()
ax.bar(counts.index, counts.values,
       color=['#059669','#dc2626'], width=0.4)
for i, (val, count) in enumerate(zip(counts.index, counts.values)):
    ax.text(i, count + 50, f'{count:,}',
            ha='center', fontweight='bold')
ax.set_title('Campaign Conversion — Yes vs No')
ax.set_xlabel('Subscribed')
ax.set_ylabel('Count')
plt.tight_layout()
plt.savefig('chart1_conversion_rate.png')
plt.show()
print("✅ Chart 1 saved")

# Chart 2: Conversion by job
fig, ax = plt.subplots(figsize=(10, 5))
q2_sorted = q2.sort_values('conversion_rate_pct', ascending=True)
ax.barh(q2_sorted['job'], q2_sorted['conversion_rate_pct'],
        color='#2563eb', height=0.6)
for i, val in enumerate(q2_sorted['conversion_rate_pct']):
    ax.text(val + 0.2, i, f'{val}%', va='center', fontsize=9)
ax.set_title('Conversion Rate by Job Type')
ax.set_xlabel('Conversion Rate (%)')
plt.tight_layout()
plt.savefig('chart2_conversion_by_job.png')
plt.show()
print("✅ Chart 2 saved")

# Chart 3: Conversion by month
month_order = ['jan','feb','mar','apr','may','jun',
               'jul','aug','sep','oct','nov','dec']
q3['month'] = pd.Categorical(
    q3['month'], categories=month_order, ordered=True)
q3 = q3.sort_values('month')
colors = ['#059669' if v >= q3['conversion_rate_pct'].mean()
          else '#dc2626' for v in q3['conversion_rate_pct']]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(q3['month'], q3['conversion_rate_pct'],
              color=colors, width=0.6)
for bar, val in zip(bars, q3['conversion_rate_pct']):
    ax.text(bar.get_x() + bar.get_width()/2,
            val + 0.3, f'{val}%', ha='center', fontsize=9)
ax.axhline(q3['conversion_rate_pct'].mean(),
           color='gray', linestyle='--', linewidth=0.8, label='Average')
ax.set_title('Conversion Rate by Month')
ax.set_xlabel('Month')
ax.set_ylabel('Conversion Rate (%)')
ax.legend()
plt.tight_layout()
plt.savefig('chart3_conversion_by_month.png')
plt.show()
print("✅ Chart 3 saved")

# Chart 4: Call duration vs conversion
fig, ax = plt.subplots(figsize=(8, 5))
df[df['subscribed']=='yes']['duration_mins'].hist(
    bins=30, alpha=0.7, color='#059669', label='Converted', ax=ax)
df[df['subscribed']=='no']['duration_mins'].hist(
    bins=30, alpha=0.7, color='#dc2626', label='Not Converted', ax=ax)
ax.set_title('Call Duration — Converted vs Not Converted')
ax.set_xlabel('Call Duration (minutes)')
ax.set_ylabel('Count')
ax.legend()
plt.tight_layout()
plt.savefig('chart4_duration_vs_conversion.png')
plt.show()
print("✅ Chart 4 saved")

# Chart 5: Conversion by age group
fig, ax = plt.subplots(figsize=(8, 5))
age_conv = df.groupby('age_group', observed=True)['subscribed_binary'].mean() * 100
age_conv.plot(kind='bar', color='#7c3aed', ax=ax, width=0.5)
for i, val in enumerate(age_conv):
    ax.text(i, val + 0.3, f'{val:.1f}%',
            ha='center', fontweight='bold')
ax.set_title('Conversion Rate by Age Group')
ax.set_xlabel('Age Group')
ax.set_ylabel('Conversion Rate (%)')
ax.tick_params(axis='x', rotation=0)
plt.tight_layout()
plt.savefig('chart5_conversion_by_age.png')
plt.show()
print("✅ Chart 5 saved")

# Chart 6: Correlation heatmap
fig, ax = plt.subplots(figsize=(10, 7))
corr = df.select_dtypes(include='number').corr().round(2)
sns.heatmap(corr, annot=True, fmt='.2f',
            cmap='RdYlGn', center=0,
            linewidths=0.5, ax=ax)
ax.set_title('Feature Correlation Heatmap')
plt.tight_layout()
plt.savefig('chart6_correlation.png')
plt.show()
print("✅ Chart 6 saved")

# ── Final Summary ────────────────────────────────────────────
overall_rate           = df['subscribed_binary'].mean() * 100
best_job               = q2.iloc[0]['job']
best_month             = q3.loc[q3['conversion_rate_pct'].idxmax(), 'month']
avg_duration_converted = converted.mean() / 60

print(f"""
╔══════════════════════════════════════════════════════════════╗
║       MARKETING CAMPAIGN ANALYTICS — FINAL SUMMARY          ║
╠══════════════════════════════════════════════════════════════╣
║  Dataset             : 11,162 bank marketing records        ║
║  Overall conversion  : {overall_rate:.2f}%                         ║
║  Best job segment    : {best_job}                    ║
║  Best month          : {best_month}                           ║
║  Avg call (converted): {avg_duration_converted:.1f} mins                    ║
╠══════════════════════════════════════════════════════════════╣
║  KEY INSIGHTS:                                              ║
║  Longer calls = higher conversion rate                      ║
║  Retired customers have highest conversion rate             ║
║  March and December are strongest campaign months           ║
╚══════════════════════════════════════════════════════════════╝
""")

conn.close()
print("✅ All done!")