from decimal import Decimal
from datetime import date
from typing import Optional, Tuple
from app.models.transaction import Transaction
from app.utils.validators import normalize_description

class DuplicateService:
    @staticmethod
    def check_duplicate(
        account_id: int,
        tx_date: date,
        amount: Decimal,
        currency_code: str,
        description: str,
        reference: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if transaction is an exact or probable duplicate.
        Returns (is_duplicate: bool, reason: str).
        """
        # 1. Exact Reference Match
        if reference and reference.strip():
            ref_match = Transaction.query.filter_by(
                account_id=account_id,
                reference=reference.strip()
            ).first()
            if ref_match:
                return True, f"Exact reference match with transaction #{ref_match.id}"

        # 2. Same account, same date, same amount, same normalized description
        norm_desc = normalize_description(description)
        tx_matches = Transaction.query.filter(
            Transaction.account_id == account_id,
            Transaction.transaction_date == tx_date,
            Transaction.currency_code == currency_code,
            Transaction.amount == amount
        ).all()

        for match in tx_matches:
            if match.description_normalized == norm_desc:
                return True, f"Identical date, amount, and description to transaction #{match.id}"

        return False, ""

