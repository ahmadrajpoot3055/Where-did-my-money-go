import json
import csv
import io
from datetime import datetime, date, timezone
from pathlib import Path
from flask import current_app
from app.extensions import db
from app.models.reporting import Report, ReportSection
from app.services.analytics_service import AnalyticsService

def utcnow():
    return datetime.now(timezone.utc)

class ReportService:
    @classmethod
    def generate_financial_report(
        cls,
        user_id: int,
        title: str,
        start_date: date,
        end_date: date,
        report_format: str = "CSV",
        currency_code: str = "PKR"
    ) -> Report:
        """
        Generate financial report for a user, calculate metrics, and save Report and ReportSections.
        """
        report = Report(
            user_id=user_id,
            title=title,
            period_start=start_date,
            period_end=end_date,
            format=report_format.upper(),
            status="Ready",
            created_at=utcnow()
        )
        db.session.add(report)
        db.session.flush()

        # 1. Summary Section
        kpis = AnalyticsService.get_dashboard_kpis(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            currency_code=currency_code
        )
        sec_summary = ReportSection(
            report_id=report.id,
            section_key="summary",
            title="Executive Summary & KPIs",
            content_json=json.dumps(kpis),
            display_order=1
        )
        db.session.add(sec_summary)

        # 2. Category Breakdown Section
        breakdown = AnalyticsService.get_category_breakdown(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            currency_code=currency_code
        )
        sec_cats = ReportSection(
            report_id=report.id,
            section_key="categories",
            title="Category Spending Breakdown",
            content_json=json.dumps(breakdown),
            display_order=2
        )
        db.session.add(sec_cats)

        # 3. Monthly Trends Section
        trends = AnalyticsService.get_monthly_trends(user_id=user_id, months=3, currency_code=currency_code)
        sec_trends = ReportSection(
            report_id=report.id,
            section_key="trends",
            title="Historical Cash Flow Trends",
            content_json=json.dumps(trends),
            display_order=3
        )
        db.session.add(sec_trends)

        # Save export file to private uploads
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"report_{report.id}_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        file_path = upload_dir / file_name

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Where Did My Money Go? - Financial Report"])
            writer.writerow(["Title", title])
            writer.writerow(["Period", f"{start_date} to {end_date}"])
            writer.writerow(["Currency", currency_code])
            writer.writerow([])
            writer.writerow(["--- Key Financial Indicators ---"])
            writer.writerow(["Total Income", f"{kpis['total_income']:.2f}"])
            writer.writerow(["Total Expense", f"{kpis['total_expense']:.2f}"])
            writer.writerow(["Net Cash Flow", f"{kpis['net_cash_flow']:.2f}"])
            writer.writerow(["Savings Rate (%)", f"{kpis['savings_rate'] if kpis['savings_rate'] is not None else 'N/A'}"])
            writer.writerow([])
            writer.writerow(["--- Category Spending ---"])
            writer.writerow(["Category", "Amount", "Share (%)", "Transaction Count"])
            for c in breakdown:
                writer.writerow([c["category"], f"{c['amount']:.2f}", f"{c['percentage']}%", c["count"]])

        report.file_path = str(file_name)
        db.session.commit()
        return report

