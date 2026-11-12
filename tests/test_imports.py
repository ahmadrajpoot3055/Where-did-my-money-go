import io
from decimal import Decimal
from datetime import date
from werkzeug.datastructures import FileStorage
from app.services.import_service import ImportService
from app.services.duplicate_service import DuplicateService
from app.models.imports import ImportBatch, ImportError
from app.models.transaction import Transaction

def test_date_and_decimal_parsing():
    assert ImportService.parse_date("2026-11-05") == date(2026, 11, 5)
    assert ImportService.parse_date("05/11/2026") == date(2026, 11, 5)
    assert ImportService.parse_decimal("1,500.50 PKR") == Decimal("1500.50")
    assert ImportService.parse_decimal("  $250.00  ") == Decimal("250.00")

def test_duplicate_detection(app):
    with app.app_context():
        # Insert a transaction
        tx = Transaction(
            user_id=1,
            account_id=1,
            transaction_type_id=2, # expense
            transaction_status_id=1, # completed
            transaction_date=date(2026, 10, 15),
            description_original="KFC DHA ORDER",
            description_normalized="KFC DHA ORDER",
            amount=Decimal("2500.00"),
            currency_code="PKR",
            reference="REF-KFC-01"
        )
        from app.extensions import db
        db.session.add(tx)
        db.session.commit()

        # Exact reference duplicate
        is_dup, reason = DuplicateService.check_duplicate(
            account_id=1,
            tx_date=date(2026, 10, 15),
            amount=Decimal("2500.00"),
            currency_code="PKR",
            description="KFC DHA ORDER",
            reference="REF-KFC-01"
        )
        assert is_dup is True
        assert "reference" in reason.lower()

        # Non-duplicate
        is_dup, _ = DuplicateService.check_duplicate(
            account_id=1,
            tx_date=date(2026, 10, 16),
            amount=Decimal("1200.00"),
            currency_code="PKR",
            description="ANOTHER ORDER",
            reference="REF-KFC-99"
        )
        assert is_dup is False

def test_import_workflow_with_malformed_and_valid_rows(app):
    with app.app_context():
        csv_content = """Date,Description,Amount,Ref
2026-10-01,SALARY DEPOSIT,100000.00,SAL-01
2026-10-02,POS PURCHASE KFC DHA,-1500.00,KFC-01
INVALID_DATE,CORRUPT ROW,INVALID_AMOUNT,ERR-01
"""
        file_obj = FileStorage(
            stream=io.BytesIO(csv_content.encode("utf-8")),
            filename="test_statement.csv",
            content_type="text/csv"
        )

        batch = ImportService.create_batch_from_upload(user_id=1, account_id=1, uploaded_file=file_obj)
        assert batch.id is not None
        assert batch.status == "Uploaded"

        mapping = {
            "date_column": "Date",
            "description_column": "Description",
            "amount_column": "Amount",
            "date_format": None
        }

        preview = ImportService.parse_and_preview(batch, mapping)
        assert preview["total_rows"] == 3
        assert preview["accepted_rows"] == 2
        assert preview["rejected_rows"] == 1

        errors = ImportError.query.filter_by(batch_id=batch.id).all()
        assert len(errors) == 1
        assert errors[0].error_code in ("INVALID_DATE", "INVALID_AMOUNT")

        # Commit batch
        committed = ImportService.commit_batch(batch, preview["all_valid_rows"])
        assert committed == 2
        assert batch.status == "CompletedWithErrors"

