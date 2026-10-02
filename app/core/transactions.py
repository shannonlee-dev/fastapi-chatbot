"""Service가 사용하는 최소 DB transaction 계약이다."""

from typing import Protocol


class Transaction(Protocol):
    """Persistence 구현과 독립적인 transaction 완료 계약이다."""

    def commit(self) -> None:
        """진행 중인 변경을 확정한다."""
        ...

    def rollback(self) -> None:
        """진행 중인 transaction을 종료하고 변경을 취소한다."""
        ...
