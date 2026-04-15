#!/usr/bin/env python3
"""
ARIA Pre-Deployment Final Validation
Comprehensive checks before pushing to GitHub and Streamlit Cloud
"""

import os
import sys
import json
import hashlib
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_check(status, text):
    symbol = "PASS" if status else "FAIL"
    print(f"{symbol}: {text}")

def check_python_version():
    print_header("Python Version Check")
    version = sys.version_info
    required = (3, 10)

    if version >= required:
        print_check(True, f"Python {version.major}.{version.minor}.{version.micro} (3.10+ required)")
        return True
    else:
        print_check(False, f"Python {version.major}.{version.minor}.{version.micro} (Upgrade to 3.10+ needed)")
        return False

def check_files():
    print_header("Required Files Check")

    required_files = [
        'aria_app.py',
        'requirements.txt',
        'runtime.txt',
        'packages.txt',
        '.gitignore',
        'README.md',
        '.streamlit/config.toml',
        '01_Data/aria_dataset_manifest.json',
        '01_Data/final_aria_dataset.csv',
        '01_Data/aria_executive_review_dataset.csv',
        '01_Data/aria_executive_overrides.csv',
    ]
    
    all_exist = True
    for file in required_files:
        exists = Path(file).exists()
        print_check(exists, file)
        if not exists:
            all_exist = False
    
    return all_exist

def check_requirements():
    print_header("Dependencies Check")

    required = [
        'setuptools',
        'wheel',
        'streamlit',
        'pandas',
        'numpy',
        'plotly',
        'scikit-learn',
    ]

    req_file = Path('requirements.txt')
    if not req_file.exists():
        print_check(False, "requirements.txt not found")
        return False

    content = req_file.read_text()
    all_found = True

    for package in required:
        found = package.lower() in content.lower()
        print_check(found, f"{package} in requirements.txt")
        if not found:
            all_found = False

    return all_found

def check_runtime():
    print_header("Runtime Configuration Check")

    runtime_file = Path('runtime.txt')
    if not runtime_file.exists():
        print_check(False, "runtime.txt not found")
        return False

    content = runtime_file.read_text().strip()
    is_310 = '3.10' in content

    print_check(is_310, f"Python 3.10 specified: {content}")
    
    if is_310:
        has_version = len(content.split('-')) > 1
        print_check(has_version, f"Specific version format: {content}")
        return has_version

    return is_310

def check_streamlit_config():
    print_header("Streamlit Configuration Check")

    config_file = Path('.streamlit/config.toml')
    if not config_file.exists():
        print_check(False, ".streamlit/config.toml not found")
        return False

    content = config_file.read_text()

    checks = [
        ('headless = true', 'Headless mode enabled'),
        ('fileWatcherType = "none"', 'Production mode (file watcher disabled)'),
        ('toolbarMode = "viewer"', 'Viewer toolbar mode'),
        ('enableXsrfProtection = true', 'CSRF protection'),
    ]

    all_good = True
    for check_str, description in checks:
        found = check_str in content
        print_check(found, description)
        if not found:
            all_good = False

    return all_good

def check_data_integrity():
    print_header("Data Integrity Check")

    manifest_path = Path('01_Data/aria_dataset_manifest.json')

    if not manifest_path.exists():
        print_check(False, "Manifest file not found")
        return False

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        print_check(True, "Manifest valid JSON")

        hash_pairs = [
            ("raw_dataset_sha256", "final_aria_dataset.csv"),
            ("executive_dataset_sha256", "aria_executive_review_dataset.csv"),
            ("override_table_sha256", "aria_executive_overrides.csv"),
        ]
        for manifest_key, fname in hash_pairs:
            expected_hash = str(manifest.get(manifest_key, "")).strip().lower()
            file_path = Path('01_Data') / fname
            if not expected_hash:
                print_check(False, f"Missing manifest key {manifest_key}")
                return False
            if not file_path.exists():
                print_check(False, f"{fname} not found")
                return False
            with open(file_path, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            matches = actual_hash == expected_hash
            print_check(matches, f"{fname} hash verified ({manifest_key})")
            if not matches:
                return False

        return True

    except Exception as e:
        print_check(False, f"Manifest validation failed: {e}")
        return False

def check_git_ignore():
    print_header("Git Ignore Configuration Check")

    gitignore_file = Path('.gitignore')
    if not gitignore_file.exists():
        print_check(False, ".gitignore not found")
        return False

    content = gitignore_file.read_text()

    should_exclude = [
        '__pycache__',
        '.streamlit/secrets.toml',
        '*.pyc',
        '.env',
    ]

    should_include = [
        '!01_Data/*.csv',  # Negation patterns that INCLUDE files
        '!01_Data/*.json',
    ]

    all_good = True

    for pattern in should_exclude:
        found = pattern in content
        print_check(found, f"Excludes {pattern}")
        if not found:
            all_good = False

    for pattern in should_include:
        found = pattern in content
        print_check(found, f"Includes data files with pattern: {pattern}")
        if not found:
            all_good = False

    return all_good

def check_app_structure():
    print_header("Application Structure Check")

    app_file = Path('aria_app.py')
    if not app_file.exists():
        print_check(False, "aria_app.py not found")
        return False

    content = app_file.read_text(encoding='utf-8')

    checks = [
        ('import streamlit as st', 'Streamlit imported'),
        ('import pandas as pd', 'Pandas imported'),
        ('import plotly', 'Plotly imported'),
        ('st.set_page_config', 'Page config set'),
        ('@st.cache_data', 'Caching configured'),
    ]

    all_good = True
    for check_str, description in checks:
        found = check_str in content
        print_check(found, description)
        if not found:
            all_good = False

    file_size = len(content)
    print_check(file_size > 10000, f"Application size: {file_size} bytes")

    return all_good

def main():
    print("\n" + "="*60)
    print("  ARIA PRE-DEPLOYMENT FINAL VALIDATION")
    print("="*60)

    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_files),
        ("Dependencies", check_requirements),
        ("Runtime Config", check_runtime),
        ("Streamlit Config", check_streamlit_config),
        ("Data Integrity", check_data_integrity),
        ("Git Ignore", check_git_ignore),
        ("App Structure", check_app_structure),
    ]

    results = {}
    for name, check_func in checks:
        results[name] = check_func()

    print_header("FINAL VALIDATION REPORT")

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        print_check(result, name)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n" + "SUCCESS "*10)
        print("\nALL CHECKS PASSED - READY FOR DEPLOYMENT!\n")
        print("Next steps:")
        print("1. Push all files to GitHub")
        print("2. Go to share.streamlit.io")
        print("3. Create new app from your repository")
        print("4. Set runtime to Python 3.10")
        print("5. Deploy!")
        print("\n" + "SUCCESS "*10 + "\n")
        return 0
    else:
        print("\nSOME CHECKS FAILED")
        print("\nPlease fix the issues above before deploying.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())