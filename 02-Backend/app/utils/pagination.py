"""Pagination helpers and standard list response models."""

from __future__ import annotations

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """Standard pagination query parameters."""

    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PageResponse(BaseModel, Generic[T]):
    """Standard paginated list envelope."""

    data: List[T]
    meta: PageMeta


def paginate(items: List[T], page: int, page_size: int) -> PageResponse[T]:
    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    return PageResponse(
        data=page_items,
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=end < total_items,
            has_previous=start > 0,
        ),
    )


def limit_offset(limit: int = 20, offset: int = 0) -> tuple[int, int]:
    if limit <= 0:
        limit = 20
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0
    return limit, offset
