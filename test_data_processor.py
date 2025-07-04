#!/usr/bin/env python3
"""
Test script to verify data processor functionality
"""

from src.data_processor import TicketDataProcessor

def test_data_processor():
    print("Testing Data Processor...")
    
    # Initialize processor
    processor = TicketDataProcessor("sample_tickets_template.csv")
    
    # Load data
    print("Loading data...")
    df = processor.load_data()
    print(f"Loaded {len(df)} tickets")
    
    # Clean data
    print("Cleaning data...")
    df_clean = processor.clean_data()
    print(f"Cleaned data shape: {df_clean.shape}")
    
    # Check days_open column
    print(f"Days open column exists: {'days_open' in df_clean.columns}")
    if 'days_open' in df_clean.columns:
        print(f"Days open sample: {df_clean['days_open'].head(10).tolist()}")
        print(f"Days open mean: {df_clean['days_open'].mean():.2f}")
        print(f"Days open min: {df_clean['days_open'].min()}")
        print(f"Days open max: {df_clean['days_open'].max()}")
    
    # Get analysis
    print("Getting analysis...")
    analysis = processor.analyze_patterns()
    print(f"Analysis avg_days_open: {analysis.get('avg_days_open', 0):.2f}")
    print(f"Total tickets: {analysis.get('total_tickets', 0)}")
    
    # Check date columns
    print("\nDate column info:")
    for col in ['Created', 'Updated', 'Closed']:
        if col in df_clean.columns:
            print(f"{col}: {df_clean[col].dtype}")
            print(f"{col} sample: {df_clean[col].head(3).tolist()}")
    
    return analysis

if __name__ == "__main__":
    analysis = test_data_processor()
    print(f"\nFinal result - Average days open: {analysis.get('avg_days_open', 0):.2f}") 