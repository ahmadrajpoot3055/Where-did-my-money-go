from decimal import Decimal
from datetime import datetime, date, timezone
from typing import List, Optional
import numpy as np
from app.extensions import db
from app.models.intelligence import AnomalyModel, AnalysisRun, AnomalyResult, AnomalyReview
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.reporting import Notification

def utcnow():
    return datetime.now(timezone.utc)

class AnomalyService:
    @classmethod
    def get_or_create_default_model(cls) -> AnomalyModel:
        model = AnomalyModel.query.filter_by(name="Statistical-IQR-Detector", is_active=True).first()
        if not model:
            model = AnomalyModel(
                name="Statistical-IQR-Detector",
                version="1.0.0",
                algorithm="Category Median Interquartile Range (IQR) & Z-Score",
                is_active=True,
                trained_at=utcnow()
            )
            db.session.add(model)
            db.session.commit()
        return model

    @classmethod
    def run_detection(cls, user_id: int, start_date: date, end_date: date) -> AnalysisRun:
        """
        Runs statistical and rule-based anomaly detection on user's expense transactions.
        Identifies unusually large transactions (> 3x category median or > user median + 3*std).
        """
        model = cls.get_or_create_default_model()
        run = AnalysisRun(
            user_id=user_id,
            anomaly_model_id=model.id,
            start_date=start_date,
            end_date=end_date,
            status="Running",
            started_at=utcnow()
        )
        db.session.add(run)
        db.session.commit()

        try:
            completed_status = TransactionStatus.query.filter_by(name="completed").first()
            expense_type = TransactionType.query.filter_by(name="expense").first()
            status_id = completed_status.id if completed_status else 1
            expense_type_id = expense_type.id if expense_type else 2

            # Historical baseline for user
            historical_txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_status_id == status_id,
                Transaction.transaction_type_id == expense_type_id,
            ).all()

            # Transactions in current analysis window
            current_txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_status_id == status_id,
                Transaction.transaction_type_id == expense_type_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            ).all()

            if not current_txs:
                run.status = "Completed"
                run.completed_at = utcnow()
                db.session.commit()
                return run

            # Group historical expenses by category
            category_amounts = {}
            all_amounts = [float(t.amount) for t in historical_txs] if historical_txs else []

            overall_median = np.median(all_amounts) if all_amounts else 0.0
            overall_std = np.std(all_amounts) if len(all_amounts) > 2 else 0.0

            for t in historical_txs:
                cat_key = t.category_id or 0
                if cat_key not in category_amounts:
                    category_amounts[cat_key] = []
                category_amounts[cat_key].append(float(t.amount))

            category_medians = {
                cat_id: np.median(amts) for cat_id, amts in category_amounts.items() if amts
            }

            anomaly_count = 0
            for tx in current_txs:
                amt = float(tx.amount)
                cat_key = tx.category_id or 0
                cat_med = category_medians.get(cat_key, overall_median)
                cat_name = tx.category.name if tx.category else "Uncategorized"

                is_anomaly = False
                score = 0.0
                reason_parts = []

                # Rule 1: Amount exceeds 3x category median (if category has history)
                if cat_med > 0 and amt > 3.0 * cat_med:
                    is_anomaly = True
                    ratio = round(amt / cat_med, 1)
                    score = min(0.99, 0.5 + (ratio * 0.08))
                    reason_parts.append(
                        f"Amount ({amt:,.2f} {tx.currency_code}) is {ratio}x higher than typical {cat_name} median ({cat_med:,.2f} {tx.currency_code})"
                    )

                # Rule 2: Overall extreme outlier (> 3 std dev above mean)
                if overall_std > 0 and amt > (overall_median + 3 * overall_std):
                    is_anomaly = True
                    score = max(score, 0.95)
                    reason_parts.append(f"Statistically rare high amount compared to your overall spending history")

                if is_anomaly:
                    # Check if already flagged in this run or active results
                    existing = AnomalyResult.query.filter_by(
                        transaction_id=tx.id,
                        status="New"
                    ).first()

                    if not existing:
                        res = AnomalyResult(
                            analysis_run_id=run.id,
                            transaction_id=tx.id,
                            score=Decimal(str(round(score, 4))),
                            reason="; ".join(reason_parts),
                            status="New"
                        )
                        db.session.add(res)
                        anomaly_count += 1

            run.status = "Completed"
            run.completed_at = utcnow()

            # Create notification if anomalies found
            if anomaly_count > 0:
                notif = Notification(
                    user_id=user_id,
                    notification_type="AnomalyAlert",
                    title="Unusual Spending Detected",
                    body=f"We noticed {anomaly_count} transaction(s) with unusual spending patterns for review.",
                    target_url="/insights/anomalies"
                )
                db.session.add(notif)

            db.session.commit()
            return run
        except Exception:
            db.session.rollback()
            run.status = "Failed"
            run.completed_at = utcnow()
            db.session.commit()
            raise

    @classmethod
    def record_review(cls, result_id: int, user_id: int, decision: str, comment: Optional[str] = None):
        """
        Record user review for an anomaly (Expected / Incorrect / FollowUp).
        """
        result = AnomalyResult.query.get_or_404(result_id)
        if result.transaction.user_id != user_id:
            raise PermissionError("Unauthorized access to anomaly result")

        review = AnomalyReview(
            anomaly_result_id=result.id,
            user_id=user_id,
            decision=decision,
            comment=comment,
            reviewed_at=utcnow()
        )
        db.session.add(review)

        result.status = decision # Expected, Incorrect, FollowUp
        db.session.commit()
        return review

