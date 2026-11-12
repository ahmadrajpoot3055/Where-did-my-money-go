import json
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any
from app.extensions import db
from app.models.subscription import Subscription, SubscriptionPayment, SubscriptionDetection
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.reporting import Notification

def utcnow():
    return datetime.now(timezone.utc)

class SubscriptionService:
    @classmethod
    def detect_recurring_candidates(cls, user_id: int) -> List[SubscriptionDetection]:
        """
        Scans user's historical expense transactions for recurring patterns.
        Looks for repeated transactions with similar amounts separated by ~7, ~30, or ~365 days.
        """
        completed_status = TransactionStatus.query.filter_by(name="completed").first()
        expense_type = TransactionType.query.filter_by(name="expense").first()
        status_id = completed_status.id if completed_status else 1
        expense_type_id = expense_type.id if expense_type else 2

        txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_status_id == status_id,
            Transaction.transaction_type_id == expense_type_id
        ).order_by(Transaction.transaction_date.asc()).all()

        # Group by merchant or normalized description
        groups: Dict[str, List[Transaction]] = {}
        for t in txs:
            key = t.merchant.name if t.merchant else t.description_normalized
            # Standardize key
            key = key[:40].strip()
            if key not in groups:
                groups[key] = []
            groups[key].append(t)

        new_detections = []

        for group_name, group_txs in groups.items():
            if len(group_txs) < 2:
                continue

            # Check intervals between consecutive transactions with similar amounts (within 10%)
            for i in range(len(group_txs) - 1):
                t1 = group_txs[i]
                t2 = group_txs[i+1]
                gap_days = (t2.transaction_date - t1.transaction_date).days

                if gap_days <= 0:
                    continue

                amt1 = float(t1.amount)
                amt2 = float(t2.amount)
                # Similar amount check (within 15% variation)
                if max(amt1, amt2) > 0 and abs(amt1 - amt2) / max(amt1, amt2) <= 0.15:
                    frequency = None
                    confidence = 0.0

                    if 25 <= gap_days <= 35:
                        frequency = "Monthly"
                        confidence = 0.88
                    elif 6 <= gap_days <= 8:
                        frequency = "Weekly"
                        confidence = 0.85
                    elif 350 <= gap_days <= 380:
                        frequency = "Yearly"
                        confidence = 0.90

                    if frequency:
                        # Check if already detected or already confirmed as subscription
                        existing = SubscriptionDetection.query.filter_by(
                            user_id=user_id,
                            candidate_name=group_name,
                            status="Pending"
                        ).first()

                        existing_sub = Subscription.query.filter_by(
                            user_id=user_id,
                            name=group_name,
                            status="Active"
                        ).first()

                        if not existing and not existing_sub:
                            evidence = {
                                "sample_dates": [t1.transaction_date.isoformat(), t2.transaction_date.isoformat()],
                                "amounts": [str(t1.amount), str(t2.amount)],
                                "gap_days": gap_days,
                                "matched_tx_ids": [t1.id, t2.id]
                            }

                            detection = SubscriptionDetection(
                                user_id=user_id,
                                merchant_id=t2.merchant_id,
                                candidate_name=group_name,
                                frequency_guess=frequency,
                                confidence=Decimal(str(confidence)),
                                evidence_json=json.dumps(evidence),
                                status="Pending"
                            )
                            db.session.add(detection)
                            new_detections.append(detection)
                            break

        if new_detections:
            notif = Notification(
                user_id=user_id,
                notification_type="SubscriptionReminder",
                title="Recurring Payments Detected",
                body=f"We discovered {len(new_detections)} recurring subscription candidate(s) for review.",
                target_url="/subscriptions"
            )
            db.session.add(notif)
            db.session.commit()

        return new_detections

    @classmethod
    def confirm_detection(cls, detection_id: int, user_id: int) -> Subscription:
        """Confirm a detection candidate and convert to an active Subscription."""
        detection = SubscriptionDetection.query.get_or_404(detection_id)
        if detection.user_id != user_id:
            raise PermissionError("Unauthorized access to detection")

        # Parse evidence to get amount and currency
        evidence = json.loads(detection.evidence_json) if detection.evidence_json else {}
        amounts = evidence.get("amounts", ["0.00"])
        sample_amt = Decimal(amounts[-1]) if amounts else Decimal("0.00")

        # Estimate next date
        next_date = date.today() + (timedelta(days=30) if detection.frequency_guess == "Monthly" else timedelta(days=7))

        sub = Subscription(
            user_id=user_id,
            merchant_id=detection.merchant_id,
            name=detection.candidate_name,
            expected_amount=sample_amt,
            currency_code="PKR",
            frequency=detection.frequency_guess,
            next_expected_date=next_date,
            status="Active"
        )
        db.session.add(sub)
        db.session.flush()

        # Link matched transactions as payments
        tx_ids = evidence.get("matched_tx_ids", [])
        for tid in tx_ids:
            tx = db.session.get(Transaction, tid)
            if tx and not tx.subscription_payment:
                sp = SubscriptionPayment(
                    subscription_id=sub.id,
                    transaction_id=tx.id,
                    paid_amount=tx.amount,
                    paid_date=tx.transaction_date
                )
                db.session.add(sp)

        detection.status = "Confirmed"
        db.session.commit()
        return sub

    @classmethod
    def reject_detection(cls, detection_id: int, user_id: int):
        detection = SubscriptionDetection.query.get_or_404(detection_id)
        if detection.user_id != user_id:
            raise PermissionError("Unauthorized access to detection")
        detection.status = "Rejected"
        db.session.commit()

