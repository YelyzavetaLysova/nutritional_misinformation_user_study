#!/usr/bin/env python3
"""
Script to update numeric categories to descriptive names in recipes.csv
1 → breakfast
2 → lunch  
3 → snack
4 → dessert
5 → dinner
"""

import pandas as pd
import os

def update_categories():
    csv_path = "data/recipes.csv"
    backup_path = "data/recipes_backup.csv"
    
    # Create backup first
    print(f"Creating backup at {backup_path}...")
    os.system(f"cp {csv_path} {backup_path}")
    
    # Load the CSV
    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path, sep=";")
    
    print(f"Loaded {len(df)} recipes")
    print(f"Current categories: {df['Category'].unique()}")
    
    # Define the mapping
    category_mapping = {
        1: "breakfast",
        2: "lunch", 
        3: "snack",
        4: "dessert",
        5: "dinner"
    }
    
    # Update the Category column
    print("Updating categories...")
    df['Category'] = df['Category'].map(category_mapping)
    
    # Check for any unmapped values
    unmapped = df['Category'].isna().sum()
    if unmapped > 0:
        print(f"WARNING: {unmapped} recipes have unmapped categories!")
        print("Unmapped values:", df[df['Category'].isna()]['Category'].unique())
    else:
        print("All categories successfully mapped!")
    
    print(f"New categories: {df['Category'].unique()}")
    print(f"Category counts: {df['Category'].value_counts().to_dict()}")
    
    # Save the updated CSV
    print(f"Saving updated CSV to {csv_path}...")
    df.to_csv(csv_path, sep=";", index=False)
    
    print("✅ Categories updated successfully!")
    print(f"Backup saved at: {backup_path}")

if __name__ == "__main__":
    update_categories()
