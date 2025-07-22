"""
Base Fetcher with BeautifulSoup Helper Methods

Provides type-safe helper methods for common BeautifulSoup operations
to eliminate mypy errors and reduce code duplication.
"""

from typing import Any

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag


class BaseFetcher:
    """Base class with common BeautifulSoup helper methods"""

    @staticmethod
    def safe_get_attr(element: Tag | PageElement | NavigableString | None, attr: str, default: str = "") -> str:
        """Safely get attribute from BeautifulSoup element"""
        if isinstance(element, Tag):
            value = element.get(attr)
            return str(value) if value else default
        return default

    @staticmethod
    def safe_get_text(element: Tag | PageElement | NavigableString | None, default: str = "") -> str:
        """Safely get text content from BeautifulSoup element"""
        if isinstance(element, Tag):
            return element.get_text(strip=True) or default
        return default

    @staticmethod
    def safe_find_text(soup: BeautifulSoup, *args: Any, **kwargs: Any) -> str:
        """Find element and safely extract text"""
        element = soup.find(*args, **kwargs)
        return BaseFetcher.safe_get_text(element)

    @staticmethod
    def safe_find_attr(soup: BeautifulSoup, attr: str, *args: Any, **kwargs: Any) -> str:
        """Find element and safely extract attribute"""
        element = soup.find(*args, **kwargs)
        return BaseFetcher.safe_get_attr(element, attr)

    @staticmethod
    def safe_find_all_text(soup: BeautifulSoup, *args: Any, **kwargs: Any) -> list[str]:
        """Find all elements and extract text from each"""
        elements = soup.find_all(*args, **kwargs)
        return [
            BaseFetcher.safe_get_text(elem)
            for elem in elements
            if isinstance(elem, Tag) and BaseFetcher.safe_get_text(elem)
        ]

    @staticmethod
    def safe_find_all_attrs(soup: BeautifulSoup, attr: str, *args: Any, **kwargs: Any) -> list[str]:
        """Find all elements and extract attribute from each"""
        elements = soup.find_all(*args, **kwargs)
        return [
            BaseFetcher.safe_get_attr(elem, attr)
            for elem in elements
            if isinstance(elem, Tag) and BaseFetcher.safe_get_attr(elem, attr)
        ]

    @staticmethod
    def safe_select_text(soup: BeautifulSoup, selector: str, default: str = "") -> str:
        """CSS selector with safe text extraction"""
        element = soup.select_one(selector)
        return BaseFetcher.safe_get_text(element, default)

    @staticmethod
    def safe_select_attr(soup: BeautifulSoup, selector: str, attr: str, default: str = "") -> str:
        """CSS selector with safe attribute extraction"""
        element = soup.select_one(selector)
        return BaseFetcher.safe_get_attr(element, attr, default)

    @staticmethod
    def safe_has_attr(element: Tag | PageElement | NavigableString | None, attr: str) -> bool:
        """Safely check if element has attribute"""
        if isinstance(element, Tag):
            return element.has_attr(attr)
        return False

    @staticmethod
    def safe_find_parent(element: Tag | PageElement | NavigableString | None, *args: Any, **kwargs: Any) -> Tag | None:
        """Safely find parent element"""
        if isinstance(element, Tag):
            parent = element.find_parent(*args, **kwargs)
            return parent if isinstance(parent, Tag) else None
        return None

    @staticmethod
    def safe_string(element: Tag | PageElement | NavigableString | None, default: str = "") -> str:
        """Safely get string property from element"""
        if isinstance(element, Tag):
            return str(element.string) if element.string else default
        return default

    @staticmethod
    def safe_find(element: Tag | PageElement | NavigableString | None, *args: Any, **kwargs: Any) -> Tag | None:
        """Safely call find() on an element"""
        if isinstance(element, Tag):
            result = element.find(*args, **kwargs)
            return result if isinstance(result, Tag) else None
        return None

    @staticmethod
    def safe_find_all(element: Tag | PageElement | NavigableString | None, *args: Any, **kwargs: Any) -> list[Tag]:
        """Safely call find_all() on an element"""
        if isinstance(element, Tag):
            results = element.find_all(*args, **kwargs)
            return [r for r in results if isinstance(r, Tag)]
        return []
