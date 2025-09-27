#!/usr/bin/env python3
"""
Goodreads User Library Scraper

Scrapes a user's Goodreads library to create a CSV export compatible with
Goodreads' own export format. Useful for users locked out of their accounts.
"""

import argparse
import csv
import random
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from models import BookRecord


class GoodreadsScraper:
    """Scraper for Goodreads user libraries."""
    
    BASE_URL = "https://www.goodreads.com"
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def __init__(self, user_id: str, delay: float = 1.0):
        """
        Initialize scraper for a specific user.
        
        Args:
            user_id: Goodreads user ID
            delay: Delay between requests in seconds (be respectful!)
        """
        self.user_id = user_id
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def _make_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make a GET request with error handling, rate limiting, and exponential backoff retry."""
        for attempt in range(max_retries + 1):
            # Apply delay before each request (including first attempt for rate limiting)
            if attempt == 0:
                time.sleep(self.delay)
            else:
                # Exponential backoff: 2^attempt seconds (2s, 4s, 8s)
                backoff_delay = 2 ** attempt
                print(f"  Retrying in {backoff_delay} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(backoff_delay)
            
            try:
                response = self.session.get(url, timeout=15)  # Increased timeout
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                if attempt > 0:
                    print(f"  Request succeeded on attempt {attempt + 1}")
                
                return response
                
            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    print(f"  Request timed out (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    continue
                else:
                    print(f"Error: Request timed out after {max_retries + 1} attempts: {e}")
                    raise
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    print(f"  Connection error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    continue
                else:
                    print(f"Error: Connection failed after {max_retries + 1} attempts: {e}")
                    raise
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500 and attempt < max_retries:
                    # Retry on server errors (5xx)
                    print(f"  Server error {e.response.status_code} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    continue
                else:
                    print(f"Error: HTTP error {e.response.status_code}: {e}")
                    raise
                    
            except requests.RequestException as e:
                if attempt < max_retries:
                    print(f"  Request error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    continue
                else:
                    print(f"Error: Request failed after {max_retries + 1} attempts: {e}")
                    raise
    
    def get_user_books_url(self, shelf: Optional[str] = None, page: int = 1) -> str:
        """Construct URL for user's books page."""
        url = f"{self.BASE_URL}/review/list/{self.user_id}"
        params = []
        
        if shelf and shelf != "all":
            params.append(f"shelf={shelf}")
        if page > 1:
            params.append(f"page={page}")
        
        # Add table view parameter (per_page=100 doesn't work without authentication)
        params.append("view=table")
        
        if params:
            url += "?" + "&".join(params)
            
        return url
    
    def scrape_bookshelves(self) -> List[str]:
        """
        Scrape available bookshelves from the user's profile.
        
        Returns:
            List of bookshelf names (excluding 'all'/'#ALL#')
        """
        print(f"Scraping bookshelves for user {self.user_id}...")
        
        url = self.get_user_books_url()
        response = self._make_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        bookshelves = []
        
        # Look for the shelvesSection div
        shelves_section = soup.find('div', id='shelvesSection')
        
        if shelves_section:
            # Look for the paginatedShelfList div within shelvesSection
            paginated_shelf_list = shelves_section.find('div', id='paginatedShelfList')
            
            if paginated_shelf_list:
                # Find all userShelf divs
                user_shelves = paginated_shelf_list.find_all('div', class_='userShelf')
                
                for shelf_div in user_shelves:
                    # Find the link within each userShelf div
                    link = shelf_div.find('a', href=True)
                    if link:
                        href = link.get('href', '')
                        
                        # Extract shelf name from URL like /review/list/92488118-lildred?shelf=to-read
                        shelf_match = re.search(r'shelf=([^&]+)', href)
                        if shelf_match:
                            shelf_name = shelf_match.group(1)
                            # Skip the 'all' shelf and URL-encoded '#ALL#' (%23ALL%23)
                            if shelf_name not in ['all', '%23ALL%23', '#ALL#']:
                                bookshelves.append(shelf_name)
                                print(f"  Found shelf: {shelf_name}")
        
        # Fallback: look for any shelf links in the entire page
        if not bookshelves:
            print("  No shelves found in shelvesSection, trying fallback method...")
            shelf_links = soup.find_all('a', href=re.compile(r'/review/list/.*\?shelf='))
            
            for link in shelf_links:
                href = link.get('href', '')
                shelf_match = re.search(r'shelf=([^&]+)', href)
                if shelf_match:
                    shelf_name = shelf_match.group(1)
                    # Skip the 'all' shelf and URL-encoded variations
                    if shelf_name not in ['all', '%23ALL%23', '#ALL#']:
                        bookshelves.append(shelf_name)
                        print(f"  Found shelf (fallback): {shelf_name}")
        
        bookshelves = list(set(bookshelves))  # Remove duplicates
        print(f"Found bookshelves: {bookshelves}")
        return bookshelves
    
    def scrape_books_from_page(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract book data from a single page of the table view.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of book data dictionaries
        """
        books = []
        
        # Look for the table containing book data
        table = soup.find('table', id='books')
        
        if not table:
            print("Warning: Could not find books table on page")
            return books
        
        # Find all book rows (they have class "bookalike review")
        book_rows = table.find_all('tr', class_='bookalike review')
        
        if not book_rows:
            print("Warning: No book rows found in table")
            return books
        
        print(f"  Found {len(book_rows)} book rows")
        
        # Process each book row
        for row in book_rows:
            book_data = {}
            
            # Extract title
            title_cell = row.find('td', class_='field title')
            if title_cell:
                title_value = title_cell.find('div', class_='value')
                if title_value:
                    # Get text but remove any series info in parentheses for main title
                    title_text = title_value.get_text(strip=True)
                    book_data['Title'] = title_text
            
            # Extract author  
            author_cell = row.find('td', class_='field author')
            if author_cell:
                author_value = author_cell.find('div', class_='value')
                if author_value:
                    # Get author name, but exclude the * (Goodreads Author indicator)
                    author_link = author_value.find('a')
                    if author_link:
                        book_data['Author'] = author_link.get_text(strip=True)
                    else:
                        # Fallback to text content
                        author_text = author_value.get_text(strip=True)
                        book_data['Author'] = author_text.replace('*', '').strip()
            
            # Extract ISBN
            isbn_cell = row.find('td', class_='field isbn')
            if isbn_cell:
                isbn_value = isbn_cell.find('div', class_='value')
                if isbn_value:
                    isbn_text = isbn_value.get_text(strip=True)
                    if isbn_text:
                        book_data['ISBN'] = isbn_text

            # Extract ISBN13
            isbn13_cell = row.find('td', class_='field isbn13')
            if isbn13_cell:
                isbn13_value = isbn13_cell.find('div', class_='value')
                if isbn13_value:
                    isbn13_text = isbn13_value.get_text(strip=True)
                    if isbn13_text:
                        book_data['ISBN13'] = isbn13_text

            # Extract ASIN
            asin_cell = row.find('td', class_='field asin')
            if asin_cell:
                asin_value = asin_cell.find('div', class_='value')
                if asin_value:
                    asin_text = asin_value.get_text(strip=True)
                    if asin_text:
                        book_data['ASIN'] = asin_text

            # Extract rating from the star display
            rating_cell = row.find('td', class_='field rating')
            if rating_cell:
                rating_value = rating_cell.find('div', class_='value')
                if rating_value:
                    # Look for star elements to count rating
                    stars = rating_value.find_all('span', class_='staticStar p10')
                    if stars:
                        book_data['My Rating'] = str(len(stars))
                    else:
                        # If no filled stars, it's unrated
                        book_data['My Rating'] = '0'
            
            # Extract read count
            read_count_cell = row.find('td', class_='field read_count')
            if read_count_cell:
                count_value = read_count_cell.find('div', class_='value')
                if count_value:
                    count_text = count_value.get_text(strip=True)
                    if count_text.isdigit():
                        book_data['Read Count'] = count_text
                    else:
                        book_data['Read Count'] = '0'
            
            # Extract date read
            date_read_cell = row.find('td', class_='field date_read')
            if date_read_cell:
                date_read_span = date_read_cell.find('span', class_='date_read_value')
                if date_read_span:
                    date_text = date_read_span.get_text(strip=True)
                    if date_text and 'not set' not in date_text.lower():
                        book_data['Date Read'] = date_text
            
            # Extract date added
            date_added_cell = row.find('td', class_='field date_added')
            if date_added_cell:
                date_value = date_added_cell.find('div', class_='value')
                if date_value:
                    # Look for span with title attribute or direct text
                    date_span = date_value.find('span')
                    if date_span:
                        date_text = date_span.get_text(strip=True)
                        if date_text:
                            book_data['Date Added'] = date_text
            
            # Extract review (might be hidden)
            review_cell = row.find('td', class_='field review')
            if review_cell:
                review_value = review_cell.find('div', class_='value')
                if review_value:
                    # Check if there's actual review text (not just "None")
                    review_text = review_value.get_text(strip=True)
                    if review_text and review_text.lower() != 'none':
                        book_data['My Review'] = review_text
                    else:
                        book_data['My Review'] = ''
            
            # Only add book if we have essential data
            if book_data.get('Title') and book_data.get('Author'):
                books.append(book_data)
                print(f"    Extracted: {book_data.get('Title')} by {book_data.get('Author')}")
            else:
                print(f"    Skipped row - missing essential data")
        
        return books
    
    def scrape_books_from_shelf(self, shelf: Optional[str] = None) -> List[BookRecord]:
        """
        Scrape all books from a specific shelf (or all books if shelf is None).
        
        Args:
            shelf: Shelf name to scrape, or None for all books
            
        Returns:
            List of validated BookRecord objects
        """
        shelf_name = shelf or "all books"
        print(f"Scraping books from shelf: {shelf_name}")
        
        all_books = []
        page = 1
        
        while True:
            print(f"  Scraping page {page}...")
            
            url = self.get_user_books_url(shelf=shelf, page=page)
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract books from this page
            page_books = self.scrape_books_from_page(soup)
            
            if not page_books:
                print(f"  No books found on page {page}, stopping")
                break
            
            # Convert to BookRecord objects
            for book_data in page_books:
                try:
                    # Set bookshelves for this book
                    if shelf:
                        book_data['Bookshelves'] = shelf
                    
                    book_record = BookRecord.from_csv_row(book_data)
                    all_books.append(book_record)
                except ValidationError as e:
                    print(f"  Warning: Could not validate book '{book_data.get('Title', 'Unknown')}': {e}")
            
            print(f"  Found {len(page_books)} books on page {page}")
            
            # Check if there's a next page
            next_link = soup.find('a', class_='next_page')
            if not next_link or 'disabled' in next_link.get('class', []):
                break
                
            page += 1
        
        print(f"Total books scraped from {shelf_name}: {len(all_books)}")
        return all_books
    
    def scrape_all_books(self, shelves: Optional[List[str]] = None) -> List[BookRecord]:
        """
        Scrape books from all specified shelves or all available shelves.
        
        Args:
            shelves: List of shelf names to scrape, or None to scrape all shelves
            
        Returns:
            List of BookRecord objects with bookshelf information
        """
        all_books = []
        
        if shelves is None:
            # Get all available shelves
            try:
                shelves = self.scrape_bookshelves()
            except Exception as e:
                print(f"Error getting bookshelves: {e}")
                print("Falling back to scraping all books...")
                return self.scrape_books_from_shelf(shelf=None)
        
        if not shelves:
            print("No shelves found, scraping all books...")
            return self.scrape_books_from_shelf(shelf=None)
        
        # Scrape each shelf
        books_by_shelf = {}
        for shelf in shelves:
            try:
                shelf_books = self.scrape_books_from_shelf(shelf=shelf)
                books_by_shelf[shelf] = shelf_books
                all_books.extend(shelf_books)
            except Exception as e:
                print(f"Error scraping shelf '{shelf}': {e}")
        
        # Note: Books might appear in multiple shelves, so we might have duplicates
        # For now, we'll keep them all and let the user decide how to handle duplicates
        
        return all_books
    
    def save_to_csv(self, books: List[BookRecord], filename: str) -> None:
        """Save books to CSV file."""
        if not books:
            print("No books to save")
            return
        
        print(f"Saving {len(books)} books to {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Get all possible fieldnames from the first book
            fieldnames = list(books[0].to_csv_row().keys())
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for book in books:
                writer.writerow(book.to_csv_row())
        
        print(f"Successfully saved books to {filename}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Scrape a Goodreads user's library to create a CSV export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper.py 92488118
  python scraper.py 92488118 --output my_library.csv
  python scraper.py 92488118 --shelves "to-read,currently-reading"
  python scraper.py 92488118 --delay 2.0
        """
    )
    
    parser.add_argument(
        'user_id',
        help='Goodreads user ID (found in profile URL)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='goodreads_export.csv',
        help='Output CSV filename (default: goodreads_export.csv)'
    )
    
    parser.add_argument(
        '-s', '--shelves',
        help='Comma-separated list of shelves to scrape (default: all shelves)'
    )
    
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0, be respectful!)'
    )
    
    parser.add_argument(
        '--list-shelves',
        action='store_true',
        help='Just list available shelves and exit'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = GoodreadsScraper(args.user_id, delay=args.delay)
    
    try:
        if args.list_shelves:
            # Just list shelves
            shelves = scraper.scrape_bookshelves()
            if shelves:
                print("Available bookshelves:")
                for shelf in sorted(shelves):
                    print(f"  - {shelf}")
            else:
                print("No bookshelves found")
            return
        
        # Parse shelves if provided
        target_shelves = None
        if args.shelves:
            target_shelves = [s.strip() for s in args.shelves.split(',')]
        
        # Scrape books
        books = scraper.scrape_all_books(shelves=target_shelves)
        
        if not books:
            print("No books found")
            sys.exit(1)
        
        # Save to CSV
        scraper.save_to_csv(books, args.output)
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during scraping: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
