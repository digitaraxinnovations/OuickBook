"""
Document numbers (estimate 1001, 1002... credit memo 1001, 1002...).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NumberSequence


class DocumentNumberService:
    def __init__(self, session: Session, first_number: int):
        self.session = session
        self.first_number = first_number

    def next_number(self, company_id: int, sequence_key: str) -> str:
        """Return the next free number and move the counter on. Does not commit."""
        sequence = self.find_or_create(company_id, sequence_key)
        number = sequence.next_number
        sequence.next_number = number + 1
        return str(number)

    def peek(self, company_id: int, sequence_key: str) -> int:
        """The number the next document will get, without using it up."""
        return self.find_or_create(company_id, sequence_key).next_number

    def move_past(self, company_id: int, sequence_key: str, used_number: str | int) -> None:
        """
        Someone typed a number by hand (e.g. check 2050). Make sure the next
        automatic number comes after it. Non-numeric numbers are ignored.
        """
        try:
            used = int(used_number)
        except (TypeError, ValueError):
            return
        sequence = self.find_or_create(company_id, sequence_key)
        if used + 1 > sequence.next_number:
            sequence.next_number = used + 1

    def find_or_create(self, company_id: int, sequence_key: str) -> NumberSequence:
        query = (
            select(NumberSequence)
            .where(NumberSequence.company_id == company_id, NumberSequence.sequence_key == sequence_key)
            .with_for_update()  # two users saving at once never get the same number
        )
        sequence = self.session.scalar(query)
        if sequence is None:
            sequence = NumberSequence(company_id=company_id, sequence_key=sequence_key, next_number=self.first_number)
            self.session.add(sequence)
            self.session.flush()
        return sequence
