from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationInfo, ConfigDict
from pydantic_extra_types.isbn import isbn10_digit_calc
import re


class BookRecord(BaseModel):
    """
    Represents a book record from a Goodreads library export.
    
    This model handles the core fields needed to recreate a Goodreads library
    import CSV for users who have been locked out of their accounts.
    """
    
    title: str = Field(..., description="The book title")
    author: str = Field(..., description="The primary author name")
    isbn: Optional[str] = Field(None, description="ISBN number (ISBN10 format only)")
    isbn13: Optional[str] = Field(None, description="ISBN13 number")
    asin: Optional[str] = Field(None, description="Amazon Standard Identification Number")
    my_rating: Optional[int] = Field(None, ge=0, le=5, description="User's rating (0-5, where 0 means unrated)")
    read_count: int = Field(default=0, ge=0, description="Number of times the book has been read")
    my_review: Optional[str] = Field(None, description="User's review text")
    bookshelves: List[str] = Field(default_factory=list, description="List of bookshelf names")
    date_added: Optional[str] = Field(None, description="Date when book was added to library")
    date_read: Optional[str] = Field(None, description="Date when book was last finished")

    @field_validator('isbn')
    @classmethod
    def validate_isbn10_only(cls, v) -> Optional[str]:
        """Validate and clean ISBN10 format only. Handles malformed ISBNs gracefully."""
        if v is None or v == '':
            return None
        
        # Remove any quotes, equals signs, or other CSV artifacts
        isbn_clean = re.sub(r'[=""]', '', str(v)).strip()
        
        if not isbn_clean:
            return None
            
        # Remove hyphens and spaces
        isbn_digits = re.sub(r'[-\s]', '', isbn_clean)
        
        # Reject ISBN13 format explicitly
        if len(isbn_digits) == 13:
            raise ValueError("ISBN13 format not allowed. Only ISBN10 (10 digits) is accepted.")
        
        # For exact 10-digit ISBNs, validate properly
        if len(isbn_digits) == 10:
            # Validate format: first 9 digits must be numeric, last can be digit or X
            if not isbn_digits[:9].isdigit() or (isbn_digits[9] not in '0123456789X'):
                raise ValueError("Invalid ISBN10 format. First 9 characters must be digits, last can be digit or X.")
            
            # Validate check digit
            expected_check_digit = isbn10_digit_calc(isbn_digits)
            if isbn_digits[9] != expected_check_digit:
                raise ValueError(f"Invalid ISBN10 check digit. Expected '{expected_check_digit}', got '{isbn_digits[9]}'.")
            
            return isbn_digits
        
        # For malformed ISBNs (common in legacy data), store as-is but validate basic format
        if len(isbn_digits) < 4 or len(isbn_digits) > 12:
            raise ValueError(f"ISBN must be between 4-12 characters, got {len(isbn_digits)} digits.")
        
        # Basic validation: should be mostly numeric (allow X at end)
        if not (isbn_digits[:-1].isdigit() and isbn_digits[-1] in '0123456789X'):
            if not isbn_digits.isdigit():
                raise ValueError("ISBN contains invalid characters. Only digits and 'X' at the end are allowed.")
        
        return isbn_digits

    @field_validator('my_rating')
    @classmethod
    def validate_rating(cls, v: Optional[int]) -> Optional[int]:
        """Ensure rating is valid or None for unrated books."""
        if v is None or v == 0:
            return None
        return v

    @field_validator('date_added', 'date_read')
    @classmethod
    def validate_date_format(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate date format and handle various Goodreads date formats."""
        if v is None or v == '':
            return None
        
        # Handle common Goodreads date formats
        # Format: YYYY/MM/DD or YYYY-MM-DD
        date_pattern = r'^\d{4}[-/]\d{2}[-/]\d{2}$'
        
        if re.match(date_pattern, v.strip()):
            return v.strip()
        
        # If invalid format, return None rather than raising error
        # This allows for graceful handling of malformed data
        return None

    @field_validator('bookshelves', mode='before')
    @classmethod
    def parse_bookshelves(cls, v) -> List[str]:
        """Parse bookshelves from comma-separated string or return list as-is."""
        if isinstance(v, str):
            if not v.strip():
                return []
            # Split by comma and clean each shelf name
            shelves = [shelf.strip() for shelf in v.split(',') if shelf.strip()]
            return shelves
        elif isinstance(v, list):
            return v
        else:
            return []

    @field_validator('my_review')
    @classmethod
    def clean_review(cls, v: Optional[str]) -> Optional[str]:
        """Clean and validate review text."""
        if v is None or v == '':
            return None
        
        # Clean up any extra whitespace
        cleaned = v.strip()
        return cleaned if cleaned else None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
        
    def to_csv_row(self) -> dict:
        """Convert model to dictionary suitable for CSV export."""
        return {
            'Title': self.title,
            'Author': self.author,
            'ISBN': self.isbn if self.isbn else '',
            'ISBN13': self.isbn13 if self.isbn13 else '',
            'ASIN': self.asin if self.asin else '',
            'My Rating': self.my_rating or 0,
            'Date Added': self.date_added or '',
            'Read Count': self.read_count,
            'My Review': self.my_review or '',
            'Bookshelves': ', '.join(self.bookshelves),
            'Date Read': self.date_read or ''
        }

    @classmethod
    def from_csv_row(cls, row: dict) -> 'BookRecord':
        """Create BookRecord from CSV row dictionary."""
        return cls(
            title=row.get('Title', ''),
            author=row.get('Author', ''),
            isbn=row.get('ISBN'),
            isbn13=row.get('ISBN13'),
            asin=row.get('ASIN'),
            my_rating=row.get('My Rating') if row.get('My Rating') not in [None, '', '0'] else None,
            date_added=row.get('Date Added'),
            read_count=int(row.get('Read Count', 0)),
            my_review=row.get('My Review'),
            bookshelves=row.get('Bookshelves', ''),  # Will be parsed by validator
            date_read=row.get('Date Read')
        )
