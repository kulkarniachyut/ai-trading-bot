"""
Utility: Test a single provider standalone.

Usage:
    python tools/scripts/test_provider.py <provider_name> [method]

Examples:
    python tools/scripts/test_provider.py yfinance fetch_us_markets
    python tools/scripts/test_provider.py jugaad fetch_fii_dii
    python tools/scripts/test_provider.py newsapi fetch_news

This script will be fleshed out as providers are built.
"""
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/scripts/test_provider.py <provider_name> [method]")
        print("Available providers will be listed here as they are built.")
        sys.exit(1)

    provider_name = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else None

    # Will be populated as providers are built
    print(f"Testing provider: {provider_name}")
    print(f"Method: {method or 'default'}")
    print("Providers not yet built. This script grows with Step 3+.")


if __name__ == "__main__":
    main()
