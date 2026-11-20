from app.services.numbering import DocumentNumberService


def check_sequence_key(bank_account_id: int) -> str:
    """Every bank account has its own check numbers."""
    return f"CHECK-{bank_account_id}"


class CheckNumberService:
    def __init__(self, numbering: DocumentNumberService):
        self.numbering = numbering

    def assign(self, company_id: int, bank_account_id: int, typed_number: str | None) -> str:
        """Use the typed number (and move the counter past it), or take the next one."""
        key = check_sequence_key(bank_account_id)
        if typed_number:
            self.numbering.move_past(company_id, key, typed_number)
            return typed_number
        return self.numbering.next_number(company_id, key)

    def peek(self, company_id: int, bank_account_id: int) -> int:
        return self.numbering.peek(company_id, check_sequence_key(bank_account_id))

    def move_past(self, company_id: int, bank_account_id: int, used_number: int) -> None:
        self.numbering.move_past(company_id, check_sequence_key(bank_account_id), used_number)
