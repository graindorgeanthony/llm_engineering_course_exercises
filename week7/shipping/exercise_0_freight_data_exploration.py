"""
Exercise 0: Freight Rate Data Exploration

This script performs exploratory data analysis (EDA) on your freight booking dataset.
Run this BEFORE creating your training dataset to understand:
- Price distribution and outliers
- TEU (volume) patterns
- Route frequencies
- Temporal trends
- Currency breakdown
- Commodity types
- Data quality issues

This helps you make informed decisions about:
- Which rows to include/exclude
- Whether to normalize currencies
- How to handle outliers
- What features are most predictive
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Seaborn styling
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Configuration
CSV_PATH = "shipping/pricing-extract.csv"  # Update this to your actual data file
SAMPLE_SIZE = None  # Set to integer to analyze a sample (e.g., 10000), None for all data


def load_data(csv_path: str, sample_size: int = None):
    """
    Load freight booking data from CSV.
    
    Args:
        csv_path: Path to CSV file
        sample_size: Number of rows to sample (None = all)
        
    Returns:
        DataFrame with freight bookings
    """
    print("=" * 60)
    print("Loading Freight Rate Data")
    print("=" * 60)
    print(f"File: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42)
        print(f"Loaded {len(df):,} rows (sampled from larger dataset)")
    else:
        print(f"Loaded {len(df):,} rows")
    
    print(f"Columns: {list(df.columns)}")
    print()
    
    return df


def basic_statistics(df):
    """Display basic dataset statistics."""
    print("=" * 60)
    print("Basic Dataset Statistics")
    print("=" * 60)
    
    print(f"\n📊 Dataset Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
    
    print("\n📋 Column Data Types:")
    print(df.dtypes)
    
    print("\n🔍 Missing Values:")
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(missing[missing > 0])
    else:
        print("No missing values!")
    
    print("\n📈 Numeric Column Statistics:")
    print(df.describe())
    print()


def analyze_prices(df):
    """Analyze price distribution and statistics."""
    print("=" * 60)
    print("💰 Price Analysis")
    print("=" * 60)
    
    prices = df['TOTAL_PRICE']
    
    print(f"\n📊 Price Statistics:")
    print(f"  Count: {len(prices):,}")
    print(f"  Mean: ${prices.mean():,.2f}")
    print(f"  Median: ${prices.median():,.2f}")
    print(f"  Std Dev: ${prices.std():,.2f}")
    print(f"  Min: ${prices.min():,.2f}")
    print(f"  Max: ${prices.max():,.2f}")
    
    # Quartiles
    print(f"\n📏 Quartiles:")
    print(f"  25th percentile: ${prices.quantile(0.25):,.2f}")
    print(f"  50th percentile (median): ${prices.quantile(0.50):,.2f}")
    print(f"  75th percentile: ${prices.quantile(0.75):,.2f}")
    print(f"  95th percentile: ${prices.quantile(0.95):,.2f}")
    print(f"  99th percentile: ${prices.quantile(0.99):,.2f}")
    
    # Potential outliers
    Q1 = prices.quantile(0.25)
    Q3 = prices.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = df[(prices < lower_bound) | (prices > upper_bound)]
    print(f"\n⚠️  Potential Outliers (IQR method): {len(outliers):,} ({len(outliers)/len(df)*100:.1f}%)")
    print(f"  Lower bound: ${lower_bound:,.2f}")
    print(f"  Upper bound: ${upper_bound:,.2f}")
    
    # Zero or negative prices
    invalid_prices = df[prices <= 0]
    if len(invalid_prices) > 0:
        print(f"\n❌ Invalid Prices (≤ 0): {len(invalid_prices):,}")
    
    # Price distribution plot
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Histogram
    axes[0, 0].hist(prices, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
    axes[0, 0].set_xlabel('Price ($)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Price Distribution (All Data)')
    axes[0, 0].axvline(prices.mean(), color='red', linestyle='--', label=f'Mean: ${prices.mean():,.0f}')
    axes[0, 0].axvline(prices.median(), color='green', linestyle='--', label=f'Median: ${prices.median():,.0f}')
    axes[0, 0].legend()
    
    # Log scale histogram (better for wide ranges)
    axes[0, 1].hist(prices[prices > 0], bins=50, edgecolor='black', alpha=0.7, color='coral')
    axes[0, 1].set_xlabel('Price ($)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Price Distribution (Log Scale)')
    axes[0, 1].set_xscale('log')
    
    # Box plot
    axes[1, 0].boxplot(prices, vert=False)
    axes[1, 0].set_xlabel('Price ($)')
    axes[1, 0].set_title('Price Distribution (Box Plot)')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Cumulative distribution
    sorted_prices = np.sort(prices)
    cumulative = np.arange(1, len(sorted_prices) + 1) / len(sorted_prices) * 100
    axes[1, 1].plot(sorted_prices, cumulative, linewidth=2, color='purple')
    axes[1, 1].set_xlabel('Price ($)')
    axes[1, 1].set_ylabel('Cumulative Percentage (%)')
    axes[1, 1].set_title('Cumulative Price Distribution')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].axhline(50, color='red', linestyle='--', alpha=0.5, label='50th percentile')
    axes[1, 1].axhline(95, color='orange', linestyle='--', alpha=0.5, label='95th percentile')
    axes[1, 1].legend()
    
    plt.tight_layout()
    plt.savefig('freight_price_distribution.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_price_distribution.png")
    plt.show()
    print()


def analyze_teu(df):
    """Analyze TEU (volume) distribution."""
    print("=" * 60)
    print("📦 TEU (Volume) Analysis")
    print("=" * 60)
    
    teu = df['TOTAL_TEU']
    
    print(f"\n📊 TEU Statistics:")
    print(f"  Mean: {teu.mean():,.1f} TEU")
    print(f"  Median: {teu.median():,.1f} TEU")
    print(f"  Min: {teu.min():,.1f} TEU")
    print(f"  Max: {teu.max():,.1f} TEU")
    print(f"  95th percentile: {teu.quantile(0.95):,.1f} TEU")
    
    # TEU bins
    print(f"\n📏 Volume Categories:")
    small = len(df[teu < 20])
    medium = len(df[(teu >= 20) & (teu < 100)])
    large = len(df[(teu >= 100) & (teu < 500)])
    xlarge = len(df[teu >= 500])
    
    print(f"  Small (< 20 TEU): {small:,} ({small/len(df)*100:.1f}%)")
    print(f"  Medium (20-100 TEU): {medium:,} ({medium/len(df)*100:.1f}%)")
    print(f"  Large (100-500 TEU): {large:,} ({large/len(df)*100:.1f}%)")
    print(f"  Extra Large (≥ 500 TEU): {xlarge:,} ({xlarge/len(df)*100:.1f}%)")
    
    # TEU distribution plot
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # Histogram
    axes[0].hist(teu, bins=50, edgecolor='black', alpha=0.7, color='green')
    axes[0].set_xlabel('TEU')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('TEU Distribution')
    axes[0].axvline(teu.mean(), color='red', linestyle='--', label=f'Mean: {teu.mean():.0f}')
    axes[0].legend()
    
    # Log scale
    axes[1].hist(teu[teu > 0], bins=50, edgecolor='black', alpha=0.7, color='darkgreen')
    axes[1].set_xlabel('TEU')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title('TEU Distribution (Log Scale)')
    axes[1].set_xscale('log')
    
    plt.tight_layout()
    plt.savefig('freight_teu_distribution.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_teu_distribution.png")
    plt.show()
    print()


def analyze_price_per_teu(df):
    """Analyze price per TEU metric."""
    print("=" * 60)
    print("💵 Price per TEU Analysis")
    print("=" * 60)
    
    df['PRICE_PER_TEU'] = df['TOTAL_PRICE'] / df['TOTAL_TEU']
    price_per_teu = df['PRICE_PER_TEU'][df['PRICE_PER_TEU'].notna()]
    
    print(f"\n📊 Price per TEU Statistics:")
    print(f"  Mean: ${price_per_teu.mean():,.2f}/TEU")
    print(f"  Median: ${price_per_teu.median():,.2f}/TEU")
    print(f"  Min: ${price_per_teu.min():,.2f}/TEU")
    print(f"  Max: ${price_per_teu.max():,.2f}/TEU")
    
    # Plot
    plt.figure(figsize=(12, 5))
    plt.hist(price_per_teu[price_per_teu < price_per_teu.quantile(0.99)], 
             bins=50, edgecolor='black', alpha=0.7, color='teal')
    plt.xlabel('Price per TEU ($)')
    plt.ylabel('Frequency')
    plt.title('Price per TEU Distribution (99th percentile)')
    plt.axvline(price_per_teu.mean(), color='red', linestyle='--', 
                label=f'Mean: ${price_per_teu.mean():.0f}')
    plt.axvline(price_per_teu.median(), color='green', linestyle='--', 
                label=f'Median: ${price_per_teu.median():.0f}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('freight_price_per_teu.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_price_per_teu.png")
    plt.show()
    print()


def analyze_routes(df):
    """Analyze route patterns."""
    print("=" * 60)
    print("🌍 Route Analysis")
    print("=" * 60)
    
    # Top origins
    print(f"\n📍 Top 10 Origins (POL):")
    top_pol = df['POL'].value_counts().head(10)
    for port, count in top_pol.items():
        print(f"  {port}: {count:,} bookings ({count/len(df)*100:.1f}%)")
    
    # Top destinations
    print(f"\n📍 Top 10 Destinations (POD):")
    top_pod = df['POD'].value_counts().head(10)
    for port, count in top_pod.items():
        print(f"  {port}: {count:,} bookings ({count/len(df)*100:.1f}%)")
    
    # Top routes
    df['ROUTE'] = df['POL'] + ' → ' + df['POD']
    print(f"\n🛳️  Top 10 Routes:")
    top_routes = df['ROUTE'].value_counts().head(10)
    for route, count in top_routes.items():
        print(f"  {route}: {count:,} bookings ({count/len(df)*100:.1f}%)")
    
    print(f"\n📊 Unique Routes: {df['ROUTE'].nunique():,}")
    print(f"📊 Unique Origins: {df['POL'].nunique():,}")
    print(f"📊 Unique Destinations: {df['POD'].nunique():,}")
    print()


def analyze_currencies(df):
    """Analyze currency breakdown."""
    print("=" * 60)
    print("💱 Currency Analysis")
    print("=" * 60)
    
    currency_counts = df['CHG_CURRENCY'].value_counts()
    
    print(f"\n💵 Currency Distribution:")
    for currency, count in currency_counts.items():
        avg_price = df[df['CHG_CURRENCY'] == currency]['TOTAL_PRICE'].mean()
        print(f"  {currency}: {count:,} bookings ({count/len(df)*100:.1f}%) - Avg: ${avg_price:,.2f}")
    
    # Plot
    plt.figure(figsize=(10, 6))
    currency_counts.plot(kind='bar', color='gold', edgecolor='black', alpha=0.7)
    plt.xlabel('Currency')
    plt.ylabel('Number of Bookings')
    plt.title('Bookings by Currency')
    plt.xticks(rotation=0)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig('freight_currency_distribution.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_currency_distribution.png")
    plt.show()
    print()


def analyze_temporal(df):
    """Analyze temporal patterns."""
    print("=" * 60)
    print("📅 Temporal Analysis")
    print("=" * 60)
    
    # Year distribution
    print(f"\n📆 Bookings by Year:")
    year_counts = df['BOOKING_YEAR'].value_counts().sort_index()
    for year, count in year_counts.items():
        print(f"  {year}: {count:,} bookings ({count/len(df)*100:.1f}%)")
    
    # Month distribution
    print(f"\n📆 Bookings by Month:")
    month_counts = df['BOOKING_MONTH'].value_counts().sort_index()
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for month, count in month_counts.items():
        month_name = month_names[int(month)-1] if 1 <= month <= 12 else str(month)
        print(f"  {month_name}: {count:,} bookings ({count/len(df)*100:.1f}%)")
    
    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # Year plot
    year_counts.plot(kind='bar', ax=axes[0], color='steelblue', edgecolor='black', alpha=0.7)
    axes[0].set_xlabel('Year')
    axes[0].set_ylabel('Number of Bookings')
    axes[0].set_title('Bookings by Year')
    axes[0].grid(True, alpha=0.3, axis='y')
    
    # Month plot
    month_counts.plot(kind='bar', ax=axes[1], color='coral', edgecolor='black', alpha=0.7)
    axes[1].set_xlabel('Month')
    axes[1].set_ylabel('Number of Bookings')
    axes[1].set_title('Bookings by Month')
    axes[1].set_xticklabels([month_names[i-1] for i in month_counts.index], rotation=45)
    axes[1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('freight_temporal_distribution.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_temporal_distribution.png")
    plt.show()
    print()


def analyze_booking_types(df):
    """Analyze booking type distribution."""
    print("=" * 60)
    print("📋 Booking Type Analysis")
    print("=" * 60)
    
    type_counts = df['BOOKING_TYPE'].value_counts()
    
    print(f"\n📊 Booking Types:")
    for booking_type, count in type_counts.items():
        avg_price = df[df['BOOKING_TYPE'] == booking_type]['TOTAL_PRICE'].mean()
        print(f"  {booking_type}: {count:,} bookings ({count/len(df)*100:.1f}%) - Avg: ${avg_price:,.2f}")
    
    # Plot
    plt.figure(figsize=(10, 6))
    type_counts.plot(kind='bar', color='purple', edgecolor='black', alpha=0.7)
    plt.xlabel('Booking Type')
    plt.ylabel('Number of Bookings')
    plt.title('Bookings by Type')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig('freight_booking_types.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_booking_types.png")
    plt.show()
    print()


def analyze_channels(df):
    """Analyze booking channel distribution."""
    print("=" * 60)
    print("🌐 Booking Channel Analysis")
    print("=" * 60)
    
    channel_counts = df['BOOKING_CHANNEL'].value_counts()
    
    print(f"\n📊 Booking Channels:")
    for channel, count in channel_counts.items():
        print(f"  {channel}: {count:,} bookings ({count/len(df)*100:.1f}%)")
    
    # Plot
    plt.figure(figsize=(10, 6))
    channel_counts.plot(kind='barh', color='darkblue', edgecolor='black', alpha=0.7)
    plt.xlabel('Number of Bookings')
    plt.ylabel('Channel')
    plt.title('Bookings by Channel')
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig('freight_channels.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved: freight_channels.png")
    plt.show()
    print()


def analyze_commodities(df):
    """Analyze commodity patterns."""
    print("=" * 60)
    print("📦 Commodity Analysis")
    print("=" * 60)
    
    print(f"\n📊 Top 15 Commodities by Volume:")
    top_commodities = df['COMMODITY_DESCRIPTION'].value_counts().head(15)
    for commodity, count in top_commodities.items():
        avg_price = df[df['COMMODITY_DESCRIPTION'] == commodity]['TOTAL_PRICE'].mean()
        commodity_short = commodity[:50] + "..." if len(commodity) > 50 else commodity
        print(f"  {commodity_short}: {count:,} ({count/len(df)*100:.1f}%) - Avg: ${avg_price:,.2f}")
    
    print(f"\n📊 Unique Commodities: {df['COMMODITY_DESCRIPTION'].nunique():,}")
    print()


def data_quality_report(df):
    """Generate data quality report."""
    print("=" * 60)
    print("🔍 Data Quality Report")
    print("=" * 60)
    
    issues = []
    
    # Check for zeros
    zero_prices = len(df[df['TOTAL_PRICE'] == 0])
    if zero_prices > 0:
        issues.append(f"❌ {zero_prices:,} bookings with $0 price")
    
    zero_teu = len(df[df['TOTAL_TEU'] == 0])
    if zero_teu > 0:
        issues.append(f"❌ {zero_teu:,} bookings with 0 TEU")
    
    # Check for negatives
    neg_prices = len(df[df['TOTAL_PRICE'] < 0])
    if neg_prices > 0:
        issues.append(f"❌ {neg_prices:,} bookings with negative price")
    
    # Check for missing data
    missing = df.isnull().sum()
    for col, count in missing.items():
        if count > 0:
            issues.append(f"❌ {count:,} missing values in {col}")
    
    # Display results
    if issues:
        print("\n⚠️  Data Quality Issues Found:")
        for issue in issues:
            print(f"  {issue}")
        print("\n💡 Recommendation: Clean these issues before training")
    else:
        print("\n✅ No major data quality issues found!")
    
    print()


def recommendations(df):
    """Provide recommendations based on analysis."""
    print("=" * 60)
    print("💡 Recommendations for Fine-Tuning")
    print("=" * 60)
    
    prices = df['TOTAL_PRICE']
    teu = df['TOTAL_TEU']
    
    print("\n1️⃣  Data Cleaning:")
    if len(df[prices <= 0]) > 0:
        print(f"   ✅ Remove {len(df[prices <= 0]):,} bookings with price ≤ 0")
    if len(df[teu <= 0]) > 0:
        print(f"   ✅ Remove {len(df[teu <= 0]):,} bookings with TEU ≤ 0")
    
    # Outliers
    Q1, Q3 = prices.quantile(0.25), prices.quantile(0.75)
    IQR = Q3 - Q1
    outliers = len(df[(prices < Q1 - 1.5*IQR) | (prices > Q3 + 1.5*IQR)])
    if outliers > 0:
        print(f"   ⚠️  Consider reviewing {outliers:,} outliers (or keep for diversity)")
    
    print("\n2️⃣  Dataset Size:")
    if len(df) < 10000:
        print(f"   ⚠️  Only {len(df):,} rows - recommend extracting at least 25,000")
    elif len(df) < 25000:
        print(f"   ✅ {len(df):,} rows is acceptable for lite mode")
    else:
        print(f"   ✅ {len(df):,} rows is good for training!")
    
    print("\n3️⃣  Currency Handling:")
    n_currencies = df['CHG_CURRENCY'].nunique()
    if n_currencies > 1:
        print(f"   ⚠️  {n_currencies} different currencies detected")
        print(f"   💡 Options:")
        print(f"      a) Train model to predict with currency (current approach)")
        print(f"      b) Convert all to USD and predict single currency")
        print(f"      c) Train separate models per currency")
    
    print("\n4️⃣  Feature Engineering:")
    if df['POL'].nunique() > 100:
        print(f"   💡 Consider grouping less frequent ports (you have {df['POL'].nunique()} unique ports)")
    
    print("\n5️⃣  Model Training:")
    print(f"   ✅ Price range: ${prices.min():,.0f} - ${prices.max():,.0f}")
    print(f"   ✅ Use log transform if range is very wide (>100x difference)")
    print(f"   ✅ Start with LITE_MODE=True (faster iteration)")
    
    print()


def main():
    """Main function to run all analyses."""
    print("\n")
    print("🚢" * 30)
    print("FREIGHT RATE DATA EXPLORATION")
    print("🚢" * 30)
    print()
    
    # Load data
    df = load_data(CSV_PATH, SAMPLE_SIZE)
    
    # Run all analyses
    basic_statistics(df)
    analyze_prices(df)
    analyze_teu(df)
    analyze_price_per_teu(df)
    analyze_routes(df)
    analyze_currencies(df)
    analyze_temporal(df)
    analyze_booking_types(df)
    analyze_channels(df)
    analyze_commodities(df)
    data_quality_report(df)
    recommendations(df)
    
    # Final summary
    print("=" * 60)
    print("📊 Exploration Complete!")
    print("=" * 60)
    print("\n✅ Generated visualizations:")
    print("   - freight_price_distribution.png")
    print("   - freight_teu_distribution.png")
    print("   - freight_price_per_teu.png")
    print("   - freight_currency_distribution.png")
    print("   - freight_temporal_distribution.png")
    print("   - freight_booking_types.png")
    print("   - freight_channels.png")
    
    print("\n🚀 Next Steps:")
    print("   1. Review the visualizations and statistics above")
    print("   2. Extract your full dataset (25K or 150K rows)")
    print("   3. Clean any data quality issues identified")
    print("   4. Run exercise_1_freight_dataset_building.py")
    print()


if __name__ == "__main__":
    main()
