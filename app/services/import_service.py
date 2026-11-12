import csv
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
from flask import current_app
from app.extensions import db
from app.models.imports import ImportBatch, ImportMapping, ImportError
from app.models.account import FinancialAccount
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.services.categorization_service import CategorizationService
from app.services.duplicate_service import DuplicateService
from app.utils.security import generate_stored_filename
from app.utils.validators import normalize_description

class ImportService:
    DATE_FORMATS = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d",
        "%d %b %Y", "%d %B %Y", "%b %d, %Y"
    ]

    @classmethod
    def parse_date(cls, val: Any, custom_format: str = None) -> date:
        if isinstance(val, (datetime, date)):
            return val if isinstance(val, date) else val.date()
        val_str = str(val).strip()
        if custom_format:
            try:
                return datetime.strptime(val_str, custom_format).date()
            except ValueError:
                pass
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(val_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Could not parse date '{val_str}' with supported formats")

    @classmethod
    def parse_decimal(cls, val: Any) -> Decimal:
        if val is None or pd.isna(val):
            raise ValueError("Amount is empty")
        val_str = str(val).strip().replace(",", "").replace("$", "").replace("PKR", "").replace("Rs", "").strip()
        try:
            dec = Decimal(val_str)
            if dec.is_nan() or dec.is_infinite():
                raise ValueError("Amount is NaN or Infinity")
            return dec
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid monetary amount: '{val}'")

    @classmethod
    def create_batch_from_upload(cls, user_id: int, account_id: int, uploaded_file) -> ImportBatch:
        filename = uploaded_file.filename
        ext = Path(filename).suffix.lower()
        if ext not in [".csv", ".xlsx", ".xls"]:
            raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")

        stored_name = generate_stored_filename(filename)
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_path = upload_dir / stored_name
        uploaded_file.save(saved_path)

        batch = ImportBatch(
            user_id=user_id,
            account_id=account_id,
            original_filename=filename,
            stored_filename=stored_name,
            file_type=ext.replace(".", "").upper(),
            status="Uploaded"
        )
        db.session.add(batch)
        db.session.commit()
        return batch

    @classmethod
    def read_file_dataframe(cls, batch: ImportBatch) -> pd.DataFrame:
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_dir / batch.stored_filename
        if not file_path.exists():
            raise FileNotFoundError("Imported file not found on disk")

        if batch.file_type == "CSV":
            try:
                df = pd.read_csv(file_path, dtype=str)
            except Exception:
                df = pd.read_csv(file_path, encoding="latin1", dtype=str)
        else:
            df = pd.read_excel(file_path, dtype=str)
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        return df

    @classmethod
    def parse_and_preview(cls, batch: ImportBatch, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Parses rows using mapping and returns preview with valid rows and error rows.
        """
        df = cls.read_file_dataframe(batch)
        batch.total_rows = len(df)
        batch.status = "Preview"

        # Clear previous errors for this batch
        ImportError.query.filter_by(batch_id=batch.id).delete()

        date_col = mapping.get("date_column")
        desc_col = mapping.get("description_column")
        amt_col = mapping.get("amount_column")
        debit_col = mapping.get("debit_column")
        credit_col = mapping.get("credit_column")
        date_fmt = mapping.get("date_format")

        account = batch.account
        currency_code = account.currency_code if account else "PKR"

        valid_rows = []
        rejected_count = 0

        for idx, row in df.iterrows():
            row_num = int(idx) + 1
            raw_data = row.dropna().to_dict()

            # Date parse
            raw_date = row.get(date_col)
            if not raw_date or pd.isna(raw_date):
                err = ImportError(
                    batch_id=batch.id,
                    row_number=row_num,
                    error_code="MISSING_DATE",
                    message=f"Missing date in column '{date_col}'",
                    raw_row_json=json.dumps(raw_data)
                )
                db.session.add(err)
                rejected_count += 1
                continue

            try:
                parsed_date = cls.parse_date(raw_date, date_fmt)
            except Exception as e:
                err = ImportError(
                    batch_id=batch.id,
                    row_number=row_num,
                    error_code="INVALID_DATE",
                    message=str(e),
                    raw_row_json=json.dumps(raw_data)
                )
                db.session.add(err)
                rejected_count += 1
                continue

            # Description parse
            raw_desc = str(row.get(desc_col, "")).strip()
            if not raw_desc or pd.isna(row.get(desc_col)):
                err = ImportError(
                    batch_id=batch.id,
                    row_number=row_num,
                    error_code="MISSING_DESC",
                    message=f"Missing description in column '{desc_col}'",
                    raw_row_json=json.dumps(raw_data)
                )
                db.session.add(err)
                rejected_count += 1
                continue

            # Amount & direction parse
            amount = Decimal("0.00")
            direction = "expense"
            
            try:
                if debit_col and credit_col and debit_col in row and credit_col in row:
                    debit_val = row.get(debit_col)
                    credit_val = row.get(credit_col)
                    if debit_val and not pd.isna(debit_val) and str(debit_val).strip():
                        amount = abs(cls.parse_decimal(debit_val))
                        direction = "expense"
                    elif credit_val and not pd.isna(credit_val) and str(credit_val).strip():
                        amount = abs(cls.parse_decimal(credit_val))
                        direction = "income"
                    else:
                        raise ValueError("Both debit and credit columns are empty")
                elif amt_col and amt_col in row:
                    raw_amt = cls.parse_decimal(row.get(amt_col))
                    if raw_amt < 0:
                        amount = abs(raw_amt)
                        direction = "expense"
                    else:
                        amount = raw_amt
                        direction = "income" if raw_amt > 0 else "expense"
                else:
                    raise ValueError("No amount or debit/credit column mapped")

                if amount <= Decimal("0.00"):
                    raise ValueError("Transaction amount must be greater than zero")
            except Exception as e:
                err = ImportError(
                    batch_id=batch.id,
                    row_number=row_num,
                    error_code="INVALID_AMOUNT",
                    message=str(e),
                    raw_row_json=json.dumps(raw_data)
                )
                db.session.add(err)
                rejected_count += 1
                continue

            # Duplicate check
            ref_val = row.get("reference") or row.get("Reference") or row.get("ref") or None
            is_dup, dup_reason = DuplicateService.check_duplicate(
                account_id=batch.account_id,
                tx_date=parsed_date,
                amount=amount,
                currency_code=currency_code,
                description=raw_desc,
                reference=str(ref_val) if ref_val else None
            )

            # Categorization prediction
            cat, merchant, conf, method = CategorizationService.categorize(raw_desc, batch.user_id)

            valid_rows.append({
                "row_number": row_num,
                "date": parsed_date.isoformat(),
                "description": raw_desc,
                "amount": str(amount),
                "direction": direction,
                "currency_code": currency_code,
                "reference": str(ref_val) if ref_val else "",
                "is_duplicate": is_dup,
                "duplicate_reason": dup_reason,
                "predicted_category_id": cat.id if cat else None,
                "predicted_category_name": cat.name if cat else "Uncategorized",
                "predicted_merchant_id": merchant.id if merchant else None,
                "confidence": str(conf),
                "method": method or "None"
            })

        batch.accepted_rows = len(valid_rows)
        batch.rejected_rows = rejected_count
        db.session.commit()

        return {
            "batch_id": batch.id,
            "total_rows": batch.total_rows,
            "accepted_rows": len(valid_rows),
            "rejected_rows": rejected_count,
            "preview_rows": valid_rows[:15],
            "all_valid_rows": valid_rows,
        }

    @classmethod
    def commit_batch(cls, batch: ImportBatch, approved_rows: List[Dict[str, Any]]) -> int:
        """
        Commit approved valid rows into transactions table inside an atomic transaction.
        """
        type_income = TransactionType.query.filter_by(name="income").first()
        type_expense = TransactionType.query.filter_by(name="expense").first()
        type_transfer = TransactionType.query.filter_by(name="transfer").first()
        status_completed = TransactionStatus.query.filter_by(name="completed").first()

        committed_count = 0
        try:
            for item in approved_rows:
                tx_type = type_expense
                if item["direction"] == "income":
                    tx_type = type_income
                elif item["direction"] == "transfer":
                    tx_type = type_transfer

                tx_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                amount = Decimal(item["amount"])
                desc = item["description"]
                cat_id = item.get("predicted_category_id")
                merch_id = item.get("predicted_merchant_id")
                conf = Decimal(item.get("confidence", "0.0")) if item.get("confidence") else None
                method = item.get("method") if item.get("method") != "None" else None

                tx = Transaction(
                    user_id=batch.user_id,
                    account_id=batch.account_id,
                    import_batch_id=batch.id,
                    transaction_type_id=tx_type.id,
                    transaction_status_id=status_completed.id,
                    category_id=cat_id,
                    merchant_id=merch_id,
                    transaction_date=tx_date,
                    description_original=desc,
                    description_normalized=normalize_description(desc),
                    amount=amount,
                    currency_code=item.get("currency_code", "PKR"),
                    reference=item.get("reference") or None,
                    category_confidence=conf,
                    category_method=method,
                    is_reviewed=(conf is not None and conf > Decimal("0.90"))
                )
                db.session.add(tx)
                committed_count += 1

            batch.status = "Completed" if batch.rejected_rows == 0 else "CompletedWithErrors"
            batch.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return committed_count
        except Exception:
            db.session.rollback()
            batch.status = "Failed"
            db.session.commit()
            raise
