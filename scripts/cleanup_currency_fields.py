#!/usr/bin/env python3
"""
Currency Field Cleanup Script

This script cleans up currency fields in the games database to ensure they contain
purely numeric values for proper price filtering and sorting.

Changes:
- price_eur: "10,99€" -> 10.99 (numeric)
- price_usd: "$10.99" -> 10.99 (numeric) 
- price_final: Already numeric, no changes needed

The script preserves all pricing information while converting formats.
"""

import sqlite3
import sys
from pathlib import Path


def clean_eur_price(price_str):
    """Convert EUR price string to numeric value.
    
    Examples:
    "10,99€" -> 10.99
    "1,94€" -> 1.94
    """
    if not price_str:
        return None

    # Remove € symbol and convert comma to decimal point
    cleaned = price_str.replace('€', '').replace(',', '.')

    try:
        return float(cleaned)
    except ValueError:
        print(f"Warning: Could not parse EUR price: {price_str}")
        return None

def clean_usd_price(price_str):
    """Convert USD price string to numeric value.
    
    Examples:
    "$10.99" -> 10.99
    "$1.99" -> 1.99
    """
    if not price_str:
        return None

    # Remove $ symbol
    cleaned = price_str.replace('$', '')

    try:
        return float(cleaned)
    except ValueError:
        print(f"Warning: Could not parse USD price: {price_str}")
        return None

def backup_database(db_path):
    """Create a backup of the database before making changes."""
    backup_path = db_path.with_suffix('.backup.db')

    # Copy database file
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def analyze_current_data(cursor):
    """Analyze current price field formats."""
    print("=== Current Data Analysis ===")

    # Count records with price data
    cursor.execute("""
        SELECT 
            COUNT(*) as total_games,
            COUNT(price_eur) as has_eur,
            COUNT(price_usd) as has_usd,
            COUNT(price_final) as has_final
        FROM games
    """)

    total, has_eur, has_usd, has_final = cursor.fetchone()
    print(f"Total games: {total}")
    print(f"Games with EUR price: {has_eur}")
    print(f"Games with USD price: {has_usd}")
    print(f"Games with final price: {has_final}")

    # Sample current formats
    print("\n=== Sample Current Formats ===")
    cursor.execute("SELECT price_eur, price_usd, price_final FROM games WHERE price_eur IS NOT NULL LIMIT 5")
    for row in cursor.fetchall():
        print(f"EUR: {row[0]}, USD: {row[1]}, Final: {row[2]}")

def add_numeric_columns(cursor):
    """Add new numeric price columns."""
    print("\n=== Adding New Numeric Columns ===")

    # Add new columns for numeric prices
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN price_eur_numeric REAL")
        print("Added price_eur_numeric column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("price_eur_numeric column already exists")
        else:
            raise

    try:
        cursor.execute("ALTER TABLE games ADD COLUMN price_usd_numeric REAL")
        print("Added price_usd_numeric column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("price_usd_numeric column already exists")
        else:
            raise

def populate_numeric_columns(cursor):
    """Populate the new numeric columns with cleaned data."""
    print("\n=== Populating Numeric Columns ===")

    # Get all games with price data
    cursor.execute("SELECT id, price_eur, price_usd FROM games WHERE price_eur IS NOT NULL OR price_usd IS NOT NULL")

    updates = []
    errors = []

    for game_id, price_eur, price_usd in cursor.fetchall():
        eur_numeric = clean_eur_price(price_eur)
        usd_numeric = clean_usd_price(price_usd)

        updates.append((eur_numeric, usd_numeric, game_id))

        if price_eur and eur_numeric is None:
            errors.append(f"EUR parsing error for game {game_id}: {price_eur}")
        if price_usd and usd_numeric is None:
            errors.append(f"USD parsing error for game {game_id}: {price_usd}")

    # Batch update
    cursor.executemany("""
        UPDATE games 
        SET price_eur_numeric = ?, price_usd_numeric = ?
        WHERE id = ?
    """, updates)

    print(f"Updated {len(updates)} games with numeric prices")

    if errors:
        print(f"\n=== Parsing Errors ({len(errors)}) ===")
        for error in errors[:10]:  # Show first 10 errors
            print(error)
        if len(errors) > 10:
            print(f"... and {len(errors) - 10} more errors")

    return len(errors) == 0

def validate_conversion(cursor):
    """Validate that the conversion was successful."""
    print("\n=== Validation ===")

    # Compare original vs numeric values
    cursor.execute("""
        SELECT 
            price_eur, price_eur_numeric,
            price_usd, price_usd_numeric,
            price_final
        FROM games 
        WHERE price_eur IS NOT NULL OR price_usd IS NOT NULL
        LIMIT 10
    """)

    print("Sample conversions:")
    print("EUR Original -> Numeric | USD Original -> Numeric | Final")
    print("-" * 60)

    for row in cursor.fetchall():
        eur_orig, eur_num, usd_orig, usd_num, final = row
        print(f"{eur_orig or 'NULL':>12} -> {eur_num or 'NULL':<8} | {usd_orig or 'NULL':>8} -> {usd_num or 'NULL':<8} | {final}")

    # Check for data consistency
    cursor.execute("""
        SELECT COUNT(*) 
        FROM games 
        WHERE price_eur IS NOT NULL 
        AND price_eur_numeric IS NULL
    """)
    eur_failures = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) 
        FROM games 
        WHERE price_usd IS NOT NULL 
        AND price_usd_numeric IS NULL
    """)
    usd_failures = cursor.fetchone()[0]

    print("\nConversion failures:")
    print(f"EUR: {eur_failures} failed conversions")
    print(f"USD: {usd_failures} failed conversions")

    return eur_failures == 0 and usd_failures == 0

def replace_original_columns(cursor):
    """Replace original text columns with numeric columns."""
    print("\n=== Replacing Original Columns ===")

    # SQLite doesn't support dropping columns directly, so we need to recreate the table
    # First, let's rename the original columns to backup names
    try:
        cursor.execute("ALTER TABLE games RENAME COLUMN price_eur TO price_eur_original")
        cursor.execute("ALTER TABLE games RENAME COLUMN price_usd TO price_usd_original")
        print("Renamed original columns to backup names")
    except sqlite3.OperationalError as e:
        if "no such column" in str(e):
            print("Original columns already renamed")
        else:
            raise

    # Rename numeric columns to the original names
    try:
        cursor.execute("ALTER TABLE games RENAME COLUMN price_eur_numeric TO price_eur")
        cursor.execute("ALTER TABLE games RENAME COLUMN price_usd_numeric TO price_usd")
        print("Renamed numeric columns to original names")
    except sqlite3.OperationalError as e:
        if "no such column" in str(e):
            print("Numeric columns already renamed")
        else:
            raise

def cleanup_backup_columns(cursor):
    """Remove the backup columns (SQLite limitation workaround)."""
    print("\n=== Cleanup (Note: SQLite doesn't support DROP COLUMN) ===")
    print("Original text columns renamed to price_eur_original and price_usd_original")
    print("These can be manually removed if needed, but keeping for safety")

def main():
    """Main cleanup function."""
    db_path = Path("data/games.db")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print("=== Currency Field Cleanup Script ===")
    print(f"Database: {db_path.absolute()}")

    # Create backup
    backup_path = backup_database(db_path)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Analyze current data
        analyze_current_data(cursor)

        # Add numeric columns
        add_numeric_columns(cursor)

        # Populate numeric columns
        success = populate_numeric_columns(cursor)

        if not success:
            print("\nErrors occurred during parsing. Check the output above.")
            response = input("Continue with replacement? (y/N): ")
            if response.lower() != 'y':
                print("Aborted. Database unchanged.")
                sys.exit(1)

        # Validate conversion
        validation_success = validate_conversion(cursor)

        if not validation_success:
            print("\nValidation failed. Check the output above.")
            response = input("Continue with replacement? (y/N): ")
            if response.lower() != 'y':
                print("Aborted. Database unchanged.")
                sys.exit(1)

        # Replace original columns
        replace_original_columns(cursor)

        # Commit changes
        conn.commit()

        print("\n=== Success! ===")
        print("Currency fields have been converted to numeric format")
        print(f"Backup saved at: {backup_path}")

        # Final validation
        print("\n=== Final Validation ===")
        cursor.execute("SELECT typeof(price_eur), typeof(price_usd) FROM games WHERE price_eur IS NOT NULL LIMIT 1")
        result = cursor.fetchone()
        if result:
            print(f"price_eur type: {result[0]}")
            print(f"price_usd type: {result[1]}")

        # Show sample of final data
        cursor.execute("SELECT price_eur, price_usd, price_final, name FROM games WHERE price_eur IS NOT NULL LIMIT 5")
        print("\nSample final data:")
        for row in cursor.fetchall():
            print(f"EUR: {row[0]}, USD: {row[1]}, Final: {row[2]} - {row[3]}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        print("Changes rolled back")
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
