# Goodreads User Scraper

A robust tool to scrape a user's profile page from Goodreads and export their library to CSV format. This tool is particularly useful for users who have been locked out of their accounts or forgotten their passwords and need to recover their book data. 

In my case the email I had used to sign up was an education email and I could no longer access the account.

## Features

- 📚 **Complete library export** - Scrapes all books from a user's Goodreads profile
- 🏷️ **Multiple book identifiers** - Captures ISBN, ISBN13, and ASIN for maximum compatibility
- 📊 **Rich metadata** - Extracts ratings, reviews, bookshelves, dates, and read counts
- 🛡️ **Robust error handling** - Automatic retries with exponential backoff for network issues
- ⚡ **Respectful scraping** - Configurable delays to avoid overwhelming Goodreads servers
- 🎯 **Flexible shelf selection** - Scrape specific shelves or entire libraries

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. First, install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repository and install dependencies:

```bash
git clone git@github.com:jakenotjay/goodreads-user-scraper.git
cd goodreads-user-scraper
uv install
```

## Usage

### Basic Usage

```bash
# Scrape a user's entire library
uv run python scraper.py <user_id> --output books.csv

# Example with a real user ID
uv run python scraper.py 92488118 --output my_books.csv
```

### Finding a User ID

The user ID can be found in the Goodreads profile URL. For example:
URL: https://www.goodreads.com/user/show/45198798-leynes
ID: 45198798

### Command Line Options

```bash
uv run python scraper.py <user_id> [options]
```

**Required:**
- `user_id` - The Goodreads user ID to scrape

**Options:**
- `--output FILE` - Output CSV filename (default: `{user_id}_books.csv`)
- `--shelves SHELF1,SHELF2` - Comma-separated list of specific shelves to scrape
- `--delay SECONDS` - Delay between requests in seconds
- `--list-shelves` - List available bookshelves and exit

### Examples

```bash
# Scrape only specific shelves
uv run python scraper.py 92488118 --shelves "read,currently-reading" --output my_read_books.csv

# Use longer delays to be extra respectful (recommended for large libraries)
uv run python scraper.py 92488118 --delay 2.0 --output books.csv

# List available shelves first
uv run python scraper.py 92488118 --list-shelves

# Scrape with custom output filename
uv run python scraper.py 92488118 --output "john_doe_library_2024.csv"
```

## Output Format

The scraper generates a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| `Title` | Book title |
| `Author` | Primary author name |
| `ISBN` | ISBN-10 identifier (if available) |
| `ISBN13` | ISBN-13 identifier (if available) |
| `ASIN` | Amazon Standard Identification Number (if available) |
| `My Rating` | User's rating (1-5, empty if unrated) |
| `Date Added` | Date book was added to library |
| `Read Count` | Number of times the book has been read |
| `My Review` | User's review text |
| `Bookshelves` | Comma-separated list of shelf names |
| `Date Read` | Date book was finished (if available) |

## Rate Limiting & Best Practices

- **Default delay**: 1 second between requests (configurable with `--delay`)
- **Minimum delay**: 0.5 seconds (enforced to be respectful to Goodreads)
- **Automatic retries**: Up to 3 retries with exponential backoff for failed requests
- **Large libraries**: For libraries with 500+ books, consider using `--delay 2.0` or higher

## Error Handling

The scraper includes robust error handling:

- **Network timeouts**: Automatically retries with exponential backoff
- **Server errors**: Retries temporary server issues (5xx errors)
- **Connection issues**: Handles temporary network problems
- **Rate limiting**: Respects delays and implements exponential backoff on failures

## Technical Details

- **Authentication**: Not required - works with public profiles
- **Page limit**: Goodreads limits to 20 books per page for unauthenticated users
- **Book identifiers**: Captures multiple ID formats since different books may only have ISBN, ISBN13, or ASIN available
- **Data validation**: Uses Pydantic models to ensure data quality and consistency

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

## Legal Notice

This tool is intended for personal use to recover your own book data or publicly available information. Please respect Goodreads' Terms of Service and use responsibly. The authors are not responsible for any misuse of this tool.

## License
This project is licensed under the Apache License 2.0.
