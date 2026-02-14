from __future__ import annotations

from dataclasses import dataclass

from grab.core.db import GrabRepository

MAX_PUBLIC_REVIEWS = 5


@dataclass(slots=True)
class ReviewRecord:
    source: str
    author: str | None
    rating: float | None
    review_date: str | None
    text: str
    url: str | None = None
    helpful_count: int | None = None


class ReviewsService:
    """
    MVP: принимает уже собранные отзывы и пишет в БД с лимитом 5 публичных на продукт.
    Сбор из внешних карточек добавляется в расширении.
    """

    def __init__(self, repository: GrabRepository):
        self.repository = repository

    def save_public_reviews(self, product_id: int, reviews: list[ReviewRecord]) -> int:
        existing = self.repository.count_public_reviews(product_id)
        allowed = max(0, MAX_PUBLIC_REVIEWS - existing)
        stored = 0

        for review in reviews[:allowed]:
            self.repository.upsert_review(
                product_id=product_id,
                item_id=None,
                review_type="public",
                source=review.source,
                author=review.author,
                rating=review.rating,
                review_date=review.review_date,
                text=review.text,
                url=review.url,
                helpful_count=review.helpful_count,
            )
            stored += 1

        return stored

    def save_my_review(self, item_id: int, product_id: int | None, review: ReviewRecord) -> int:
        return self.repository.upsert_review(
            product_id=product_id,
            item_id=item_id,
            review_type="my",
            source=review.source,
            author=review.author,
            rating=review.rating,
            review_date=review.review_date,
            text=review.text,
            url=review.url,
            helpful_count=review.helpful_count,
        )
