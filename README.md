# get-stock-inventory.py

A Python script that uses Selenium to scrape your stock photo portfolio from **Adobe Stock** and **Shutterstock**, exporting asset metadata into CSV format for inventory purposes.

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

Install dependencies:

```bash
pip install selenium
```

## Setup
1. Create credentials file

Create a credentials.ini file in the same directory:

```ini
[shutterstock]
username=your_email
password=your_password

[adobe]
username=your_google_email
```

2. ChromeDriver

Ensure ChromeDriver matches your Chrome version and is available in your PATH.

Check:

```
chromedriver --version
Usage
Run for Shutterstock
python get-stock-inventory.py --shutterstock
Run for Adobe Stock
python get-stock-inventory.py --adobe
Output
```

The script prints CSV data to stdout:

```
platform,filename,asset_id,title
Shutterstock,1234567890 - image.jpg,1234567890,"Image Title"
Adobe Stock,image_name.jpg,ASSET_ID,"Image Title"
```

You can redirect output to a file:

```
python get-stock-inventory.py --shutterstock > inventory.csv
```

### How It Works
- General Flow
1. Launches a Chrome browser via Selenium
2. Logs into the selected platform
3. Iterates through portfolio pages
4. Extracts asset metadata using regex
5. Stops when no more items are found

- Adobe Flow
1. Uses Google authentication
2. Requires manual completion of login (password + 2FA)
3. Scrapes portfolio pages via HTML content

- Shutterstock Flow
1. Logs in using credentials from credentials.ini
2. Scrapes portfolio pages directly

### Important Notes
- Adobe login requires manual interaction after email entry (Google login flow)
- The script relies on HTML structure and regex parsing, which may break if the websites change
- Use responsibly and respect platform terms of service
- Avoid rapid requests; the script includes delays and retries

# Configuration

Constants defined in the script:
```
MAX_RETRIES = 3
DELAY = 2  # seconds between pages
```

You can adjust these values depending on your network speed and tolerance for retries.

# Troubleshooting
## ChromeDriver mismatch

If you see version errors:

- Update ChromeDriver to match your Chrome version
- Or let Selenium Manager handle it (if using a newer Selenium version)
## Login issues
- Verify credentials in credentials.ini
- Ensure your account is not blocked or requiring additional verification
- For Adobe, complete the Google login manually when prompted
## No results returned
- Check if your portfolio has assets
- Ensure you are logged in successfully
- The platform UI may have changed (selectors or HTML structure)
## Limitations
- No official API usage (relies on web scraping)
- Dependent on page structure (fragile to UI changes)
- Adobe requires manual login step
- Not designed for large-scale or high-frequency scraping
## License
Use at your own risk. No warranty provided.