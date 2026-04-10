# get-stock-inventory.py

A Python script that uses Selenium to scrape your stock photo portfolio from **Adobe Stock** and **Shutterstock**, exporting asset metadata into CSV format for inventory purposes.

## New in v1.1

- File-based mode (no login required); bypass the web login and run parsing on locally downloaded files:
```
  python get-stock-inventory.py --shutterstock --file index.html
  python get-stock-inventory.py --adobe --file *.html
```

- Page limit option; allows to scrape only the nth page(s):
```
  python get-stock-inventory.py --shutterstock --page 2
```

- Cleaner Shutterstock output format

## Features

- Logs into stock contributor platforms
- Iterates through portfolio pages
- Extracts:
  - Filename
  - Asset ID
  - Title
- Outputs results as CSV to stdout
- Supports:
  - Adobe Stock (via Google login)
  - Shutterstock (direct login)
- Retry mechanism for page loading failures

## Requirements

- Python 3.8+
- Google Chrome installed
- Compatible ChromeDriver installed and available in PATH
- Python packages:
  - `selenium`

Install:
```pip install selenium
```

## Setup

Rename the provided file:
default_credentials.ini → credentials.ini

Update credentials.ini:
```[shutterstock]
username=your_email
password=your_password

[adobe]
username=your_google_email
```

## Usage

Shutterstock:
```
python get-stock-inventory.py --shutterstock
```

Adobe:
```python get-stock-inventory.py --adobe
```

Limit pages:
```
python get-stock-inventory.py --shutterstock --page 3
```

File mode:
```
python get-stock-inventory.py --shutterstock --file index.html
python get-stock-inventory.py --adobe --file *.html
```

## Output

```
platform,filename,asset_id,title
Shutterstock,image.jpg,1234567890,"Title"
Adobe Stock,image.jpg,ASSET_ID,"Title"
```

Redirect to file:
```
python get-stock-inventory.py --shutterstock > shutterstockdb.csv
```

## Notes

- Adobe requires manual Google login (2FA)
- File mode skips login entirely
- Script relies on HTML structure and regex (may break if UI changes)
- Use responsibly and respect platform terms

## Configuration

```
MAX_RETRIES = 3  
DELAY = 2
```

## Limitations

- No official API
- Fragile to UI changes
- Not for large-scale scraping