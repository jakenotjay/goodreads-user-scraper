"""
Test module for BookRecord model and CSV handling.
"""

import csv
import pytest
from pathlib import Path
from typing import Dict, Any

from models import BookRecord
from pydantic import ValidationError


class TestBookRecord:
    """Test cases for BookRecord model."""

    def test_create_basic_book_record(self):
        """Test creating a basic BookRecord."""
        book = BookRecord(
            title="Test Book",
            author="Test Author",
            isbn="0142000272",  # ISBN10 format
            my_rating=4,
            date_added="2023-01-01",
            read_count=1,
            my_review="Great book!",
            bookshelves=["fiction", "favorites"],
            date_read="2023-01-15"
        )
        
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.isbn == "0142000272"
        assert book.my_rating == 4
        assert book.bookshelves == ["fiction", "favorites"]

    def test_isbn10_validation(self):
        """Test ISBN10 validation - only ISBN10 format is accepted."""
        # Test valid ISBN10
        book_isbn10 = BookRecord(
            title="Test",
            author="Author", 
            isbn="0142000272"
        )
        assert book_isbn10.isbn == "0142000272"
        
        # Test ISBN10 with X check digit
        book_isbn10_x = BookRecord(
            title="Test",
            author="Author",
            isbn="043942089X"
        )
        assert book_isbn10_x.isbn == "043942089X"
        
        # Test that ISBN13 is rejected
        with pytest.raises(ValidationError):
            BookRecord(
                title="Test",
                author="Author",
                isbn="9780142000274"  # ISBN13 should be rejected
            )

    def test_isbn_csv_artifact_cleaning(self):
        """Test cleaning of CSV artifacts in ISBN."""
        book = BookRecord(
            title="Test",
            author="Author",
            isbn='="0142000272"'  # Common Excel CSV artifact
        )
        assert book.isbn == "0142000272"  # Should clean artifacts and validate as ISBN10

    def test_isbn_with_hyphens_and_spaces(self):
        """Test ISBN10 with hyphens and spaces."""
        book = BookRecord(
            title="Test",
            author="Author",
            isbn="0-14-200027-2"
        )
        assert book.isbn == "0142000272"

    def test_invalid_isbn_handling(self):
        """Test handling of invalid ISBN."""
        # Test completely invalid ISBN with letters
        with pytest.raises(ValidationError):
            BookRecord(
                title="Test",
                author="Author",
                isbn="invalid-isbn"
            )
        
        # Test too short ISBN
        with pytest.raises(ValidationError):
            BookRecord(
                title="Test",
                author="Author",
                isbn="123"  # Too short (less than 4 digits)
            )
        
        # Test too long ISBN
        with pytest.raises(ValidationError):
            BookRecord(
                title="Test",
                author="Author",
                isbn="1234567890123"  # Too long (more than 12 digits)
            )
        
        # Test ISBN13 (should be rejected)
        with pytest.raises(ValidationError):
            BookRecord(
                title="Test",
                author="Author",
                isbn="9780142000274"  # ISBN13 not allowed
            )
        
        # Test invalid check digit for proper 10-digit ISBN
        with pytest.raises(ValidationError):
            BookRecord(
                title="Test",
                author="Author",
                isbn="0142000271"  # Wrong check digit for 10-digit ISBN
            )

    def test_malformed_isbn_handling(self):
        """Test handling of malformed ISBNs (common in legacy data)."""
        # Test 8-digit ISBN (like in sample data)
        book1 = BookRecord(
            title="Test",
            author="Author",
            isbn="99498189"  # 8 digits - should be accepted
        )
        assert book1.isbn == "99498189"
        
        # Test 9-digit ISBN (like in sample data)
        book2 = BookRecord(
            title="Test",
            author="Author",
            isbn="316172324"  # 9 digits - should be accepted
        )
        assert book2.isbn == "316172324"

    def test_rating_validation(self):
        """Test rating validation."""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            book = BookRecord(title="Test", author="Author", my_rating=rating)
            assert book.my_rating == rating

        # Zero rating should become None
        book = BookRecord(title="Test", author="Author", my_rating=0)
        assert book.my_rating is None

        # None rating should remain None
        book = BookRecord(title="Test", author="Author", my_rating=None)
        assert book.my_rating is None

        # Invalid ratings should raise validation error
        with pytest.raises(ValidationError):
            BookRecord(title="Test", author="Author", my_rating=6)
        
        with pytest.raises(ValidationError):
            BookRecord(title="Test", author="Author", my_rating=-1)

    def test_bookshelves_parsing(self):
        """Test bookshelves parsing from string to list."""
        # Test string parsing
        book1 = BookRecord(
            title="Test",
            author="Author",
            bookshelves="fiction, mystery, favorites"
        )
        assert book1.bookshelves == ["fiction", "mystery", "favorites"]

        # Test empty string
        book2 = BookRecord(
            title="Test", 
            author="Author",
            bookshelves=""
        )
        assert book2.bookshelves == []

        # Test list input
        book3 = BookRecord(
            title="Test",
            author="Author", 
            bookshelves=["sci-fi", "classics"]
        )
        assert book3.bookshelves == ["sci-fi", "classics"]

    def test_date_validation(self):
        """Test date format validation."""
        # Valid date formats
        book1 = BookRecord(title="Test", author="Author", date_added="2023-01-01")
        assert book1.date_added == "2023-01-01"

        book2 = BookRecord(title="Test", author="Author", date_read="2023/01/01")
        assert book2.date_read == "2023/01/01"

        # Invalid date format should return None
        book3 = BookRecord(title="Test", author="Author", date_added="invalid-date")
        assert book3.date_added is None

    def test_csv_conversion(self):
        """Test CSV conversion methods."""
        book = BookRecord(
            title="Test Book",
            author="Test Author",
            isbn="0142000272",  # ISBN10 format
            my_rating=4,
            date_added="2023-01-01",
            read_count=2,
            my_review="Excellent!",
            bookshelves=["fiction", "classics"],
            date_read="2023-02-01"
        )

        # Test to_csv_row
        csv_row = book.to_csv_row()
        expected = {
            'Title': 'Test Book',
            'Author': 'Test Author',
            'ISBN': '0142000272',
            'My Rating': 4,
            'Date Added': '2023-01-01',
            'Read Count': 2,
            'My Review': 'Excellent!',
            'Bookshelves': 'fiction, classics',
            'Date Read': '2023-02-01'
        }
        assert csv_row == expected

        # Test from_csv_row
        book_from_csv = BookRecord.from_csv_row(csv_row)
        assert book_from_csv.title == book.title
        assert book_from_csv.author == book.author
        assert book_from_csv.isbn == book.isbn
        assert book_from_csv.my_rating == book.my_rating
        assert book_from_csv.bookshelves == book.bookshelves


class TestSampleCSVImport:
    """Test reading and processing the sample CSV file."""
    
    @pytest.fixture
    def sample_csv_path(self):
        """Path to the sample CSV file."""
        return Path("sample_export.csv")
    
    def test_sample_csv_exists(self, sample_csv_path):
        """Test that the sample CSV file exists."""
        assert sample_csv_path.exists(), "sample_export.csv should exist in the project root"
    
    def test_read_sample_csv(self, sample_csv_path):
        """Test reading and parsing the sample CSV file."""
        books = []
        
        with open(sample_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Map CSV columns to our expected format, combining Shelves and Bookshelves
                shelves = row.get('Shelves', '').strip()
                bookshelves = row.get(' Bookshelves', '').strip()
                
                # Combine both shelf columns
                all_shelves = []
                if shelves:
                    all_shelves.extend([s.strip() for s in shelves.split(',') if s.strip()])
                if bookshelves:
                    all_shelves.extend([s.strip() for s in bookshelves.split(',') if s.strip()])
                
                mapped_row = {
                    'Title': row.get('Title', '').strip(),
                    'Author': row.get(' Author', '').strip(),  # Note the space in sample CSV
                    'ISBN': row.get(' ISBN', '').strip(),
                    'My Rating': row.get(' My Rating', '').strip(),
                    'Date Added': row.get(' Date Added', '').strip(),
                    'Read Count': '1',  # Default since not in sample CSV
                    'My Review': row.get(' My Review', '').strip(),
                    'Bookshelves': ', '.join(all_shelves),
                    'Date Read': row.get(' Date Read', '').strip()
                }
                
                try:
                    book = BookRecord.from_csv_row(mapped_row)
                    books.append(book)
                except ValidationError as e:
                    # For now, just record that there was an error
                    # In real usage, you might want to log this or handle differently
                    print(f"Validation error for book '{mapped_row.get('Title', 'Unknown')}': {e}")
        
        # Verify we parsed some books
        assert len(books) > 0, "Should have parsed at least one book from sample CSV"
        
        # Check specific books from the sample
        titles = [book.title for book in books]
        assert "memoirs of a geisha" in titles
        assert "Blink: The Power of Thinking Without Thinking" in titles
    
    def test_sample_csv_book_details(self, sample_csv_path):
        """Test specific book details from sample CSV."""
        with open(sample_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader)
            
            # Map first book data, combining Shelves and Bookshelves
            shelves = first_row.get('Shelves', '').strip()
            bookshelves = first_row.get(' Bookshelves', '').strip()
            
            # Combine both shelf columns
            all_shelves = []
            if shelves:
                all_shelves.extend([s.strip() for s in shelves.split(',') if s.strip()])
            if bookshelves:
                all_shelves.extend([s.strip() for s in bookshelves.split(',') if s.strip()])
            
            mapped_row = {
                'Title': first_row.get('Title', '').strip(),
                'Author': first_row.get(' Author', '').strip(),
                'ISBN': first_row.get(' ISBN', '').strip(),
                'My Rating': first_row.get(' My Rating', '').strip(),
                'Date Added': first_row.get(' Date Added', '').strip(),
                'Read Count': '1',
                'My Review': first_row.get(' My Review', '').strip(),
                'Bookshelves': ', '.join(all_shelves),
                'Date Read': first_row.get(' Date Read', '').strip()
            }
            
            try:
                book = BookRecord.from_csv_row(mapped_row)
                
                assert book.title == "memoirs of a geisha"
                assert book.author == "arthur golden"
                assert book.my_rating == 4
                assert book.date_added == "2007-02-14"
                assert "fiction" in book.bookshelves
                assert "to-read" in book.bookshelves
                
            except ValidationError as e:
                pytest.fail(f"Failed to parse first book from sample CSV: {e}")


if __name__ == "__main__":
    # Run tests if executed directly
    import sys
    sys.path.insert(0, "..")
    pytest.main([__file__])
