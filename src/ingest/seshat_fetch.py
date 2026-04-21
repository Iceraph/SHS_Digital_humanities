"""Seshat data fetcher and authentication module.

Handles downloading Seshat data from the public Equinox-2020 release
at http://seshat-db.com/

Seshat data requires either:
1. Public download from Equinox-2020 dataset
2. Account creation + authentication for full access

Reference: https://seshatdatabank.info/data
"""

from pathlib import Path
from typing import Optional, Tuple
import os
import json

import pandas as pd
import requests

# Optional: BeautifulSoup for HTML parsing (only needed for authentication)
try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False


# Seshat API endpoints
SESHAT_DB_BASE = "http://seshat-db.com"
SESHAT_DOWNLOADS = f"{SESHAT_DB_BASE}/downloads_page"
SESHAT_API = f"{SESHAT_DB_BASE}/api"
SESHAT_LOGIN = f"{SESHAT_DB_BASE}/accounts/login/"


def get_seshat_credentials() -> Optional[Tuple[str, str]]:
    """
    Retrieve Seshat credentials from environment.
    
    Returns:
        Tuple of (email, password) if available, else None
    
    Environment variables:
        SESHAT_EMAIL: Email for Seshat account
        SESHAT_PASSWORD: Password for Seshat account
    """
    email = os.environ.get("SESHAT_EMAIL")
    password = os.environ.get("SESHAT_PASSWORD")
    
    if email and password:
        return (email, password)
    return None


def authenticate_seshat(email: str, password: str) -> requests.Session:
    """
    Authenticate with Seshat database and return session.
    
    Args:
        email: Email for Seshat account
        password: Password for Seshat account
    
    Returns:
        Authenticated requests.Session
    
    Raises:
        requests.exceptions.RequestException: If authentication fails
        ImportError: If BeautifulSoup is not installed
    """
    if not HAS_BEAUTIFULSOUP:
        raise ImportError(
            "BeautifulSoup4 is required for Seshat authentication. "
            "Install with: pip install beautifulsoup4"
        )
    
    session = requests.Session()
    
    # Fetch login page to get CSRF token
    try:
        response = session.get(SESHAT_LOGIN)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract CSRF token (if needed)
        csrf_token = None
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        if csrf_input:
            csrf_token = csrf_input.get("value")
        
        # Attempt login
        login_data = {
            "email": email,
            "password": password,
            "csrfmiddlewaretoken": csrf_token,
        }
        
        response = session.post(SESHAT_LOGIN, data=login_data)
        response.raise_for_status()
        
        return session
    
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"Failed to authenticate with Seshat: {e}"
        ) from e


def download_seshat_polities(
    output_path: Path,
    session: Optional[requests.Session] = None,
) -> Optional[Path]:
    """
    Download Seshat polities data.
    
    Args:
        output_path: Path where to save polities.csv
        session: Authenticated session (optional)
    
    Returns:
        Path to downloaded file if successful, else None
    """
    try:
        # Try to fetch from public Equinox-2020 release
        # The exact endpoint may vary; this attempts the most common pattern
        url = f"{SESHAT_DB_BASE}/data/polities"
        
        if session:
            response = session.get(url)
        else:
            response = requests.get(url)
        
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try parsing as JSON first (API response)
        try:
            data = response.json()
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False)
            return output_path
        except json.JSONDecodeError:
            # Fall back to treating as CSV
            with open(output_path, "w") as f:
                f.write(response.text)
            return output_path
    
    except requests.exceptions.RequestException as e:
        print(f"Could not download polities from {url}: {e}")
        return None


def download_seshat_data(
    output_path: Path,
    session: Optional[requests.Session] = None,
) -> Optional[Path]:
    """
    Download Seshat coded data.
    
    Args:
        output_path: Path where to save data.csv
        session: Authenticated session (optional)
    
    Returns:
        Path to downloaded file if successful, else None
    """
    try:
        url = f"{SESHAT_DB_BASE}/data/values"
        
        if session:
            response = session.get(url)
        else:
            response = requests.get(url)
        
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try parsing as JSON first
        try:
            data = response.json()
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False)
            return output_path
        except json.JSONDecodeError:
            # Fall back to treating as CSV
            with open(output_path, "w") as f:
                f.write(response.text)
            return output_path
    
    except requests.exceptions.RequestException as e:
        print(f"Could not download data from {url}: {e}")
        return None


def fetch_seshat_equinox2020(
    output_dir: Path = Path("data/raw/seshat"),
) -> bool:
    """
    Download Seshat Equinox-2020 public dataset.
    
    Attempts to download the public Equinox-2020 dataset release.
    If full API access is needed, provide SESHAT_EMAIL and SESHAT_PASSWORD
    environment variables.
    
    Args:
        output_dir: Directory where to save Seshat CSVs
    
    Returns:
        True if at least one file was downloaded, False otherwise
    
    Reference:
        https://seshatdatabank.info/data
        http://seshat-db.com/
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for credentials
    creds = get_seshat_credentials()
    session = None
    if creds:
        try:
            session = authenticate_seshat(*creds)
            print("✓ Authenticated with Seshat API")
        except requests.exceptions.RequestException as e:
            print(f"⚠ Authentication failed: {e}")
            print("  Attempting public data download...")
    
    # Attempt downloads
    success = False
    
    polities_path = output_dir / "polities.csv"
    if download_seshat_polities(polities_path, session):
        print(f"✓ Downloaded polities: {polities_path}")
        success = True
    
    data_path = output_dir / "data.csv"
    if download_seshat_data(data_path, session):
        print(f"✓ Downloaded data: {data_path}")
        success = True
    
    return success


def create_seshat_setup_instructions(output_path: Path = Path("SESHAT_SETUP.md")) -> None:
    """
    Create instructions for Seshat data access.
    
    Args:
        output_path: Path where to write instructions
    """
    instructions = """# Seshat Data Access Guide

## Public Data (No Authentication Required)

Seshat publishes periodic public snapshots of curated data at:
- **Equinox-2020 Dataset:** http://seshat-db.com/

This release is freely available and can be downloaded manually from the website.

### Manual Download Steps

1. Visit http://seshat-db.com/downloads_page
2. Download the Equinox-2020 spreadsheet files
3. Save to `data/raw/seshat/`:
   - `polities.csv` — Polity metadata
   - `data.csv` — Coded observations
   - `variables.csv` — Variable definitions

## Full Access (Requires Account)

For access to complete Seshat data including unpublished variables:

1. Visit https://seshat-db.com/
2. Create an account (Google or email registration)
3. Contact seshat.admin@csh.ac.at to request researcher access
4. Add credentials to `.env`:
   ```
   SESHAT_EMAIL=your.email@example.com
   SESHAT_PASSWORD=your_password
   ```

## Programmatic Access

To fetch Seshat data programmatically:

```python
from src.ingest.seshat_fetch import fetch_seshat_equinox2020

# Public data (no credentials needed)
success = fetch_seshat_equinox2020(
    output_dir="data/raw/seshat"
)

# With authentication (credentials in .env)
# Automatically attempts if SESHAT_EMAIL and SESHAT_PASSWORD are set
```

## Parser

After downloading data, use:

```python
from src.ingest.seshat import parse_seshat

df = parse_seshat(
    polities_path="data/raw/seshat/polities.csv",
    variables_path="data/raw/seshat/variables.csv",
    data_path="data/raw/seshat/data.csv",
    output_path="data/processed/seshat_raw.parquet"
)
```

If files are not available, parser falls back to mock data for testing.

## Files Generated

- `data/processed/seshat_raw.parquet` — Standardized output (13-column schema)
- `data/reference/seshat_variable_mapping.csv` — Variable metadata

## References

- Seshat Website: https://seshatdatabank.info/
- Data Portal: http://seshat-db.com/
- Equinox-2020: http://seshat-db.com/downloads_page
- Methods: https://seshatdatabank.info/methods/world-sample-30
"""
    
    output_path.write_text(instructions)
    print(f"✓ Setup instructions written to {output_path}")
