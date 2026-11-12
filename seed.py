import os
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models import (
    Role, User, UserPreference, NotificationPreference,
    AccountType, FinancialAccount,
    Category, Subcategory, Merchant, MerchantAlias, CategoryRule,
    Transaction, TransactionType, TransactionStatus, TransactionTag,
    Budget, BudgetItem, SavingsGoal, SavingsContribution
)
from app.services.categorization_service import CategorizationService
from app.services.anomaly_service import AnomalyService
from app.services.subscription_service import SubscriptionService
from app.utils.security import hash_password
from app.utils.validators import normalize_description

def utcnow():
    return datetime.now(timezone.utc)

def run_seed():
    app = create_app()
    with app.app_context():
        print("Creating all tables in database...")
        db.create_all()

        print("1. Seeding Roles...")
        roles = {
            "admin": "System Administrator with reference data controls",
            "user": "Individual Account Holder"
        }
        role_objs = {}
        for r_name, r_desc in roles.items():
            r = Role.query.filter_by(name=r_name).first()
            if not r:
                r = Role(name=r_name, description=r_desc)
                db.session.add(r)
            role_objs[r_name] = r
        db.session.flush()

        print("2. Seeding Account Types...")
        acc_types = ["current", "savings", "cash", "wallet", "credit"]
        type_objs = {}
        for t_name in acc_types:
            at = AccountType.query.filter_by(name=t_name).first()
            if not at:
                at = AccountType(name=t_name, description=f"{t_name.title()} financial account")
                db.session.add(at)
            type_objs[t_name] = at
        db.session.flush()

        print("3. Seeding Transaction Types & Statuses...")
        tx_types = ["income", "expense", "transfer"]
        tx_type_objs = {}
        for tt in tx_types:
            t = TransactionType.query.filter_by(name=tt).first()
            if not t:
                t = TransactionType(name=tt, description=f"{tt.title()} flow")
                db.session.add(t)
            tx_type_objs[tt] = t

        tx_statuses = ["completed", "pending", "void", "failed"]
        tx_status_objs = {}
        for ts in tx_statuses:
            s = TransactionStatus.query.filter_by(name=ts).first()
            if not s:
                s = TransactionStatus(name=ts, description=f"{ts.title()} transaction")
                db.session.add(s)
            tx_status_objs[ts] = s
        db.session.flush()

        print("4. Seeding Global Categories & Subcategories...")
        categories_data = {
            ("Food & Dining", "Expense"): ["Restaurants", "Fast Food", "Cafes", "Delivery"],
            ("Groceries", "Expense"): ["Supermarkets", "Bakeries", "Produce", "Meat & Poultry"],
            ("Transport", "Expense"): ["Fuel", "Ride-Hailing", "Public Transit", "Maintenance"],
            ("Subscriptions", "Expense"): ["Streaming", "Software", "Cloud Storage", "Music"],
            ("Utilities", "Expense"): ["Electricity", "Gas", "Water", "Internet & TV"],
            ("Housing", "Expense"): ["Rent", "Repairs", "Furniture", "Maintenance"],
            ("Healthcare", "Expense"): ["Pharmacy", "Doctor Visits", "Lab Tests", "Dental"],
            ("Shopping", "Expense"): ["Clothing", "Electronics", "Gifts", "Personal Care"],
            ("Cash Withdrawal", "Expense"): ["ATM Withdrawal", "Branch Cash"],
            ("Income", "Income"): ["Salary", "Freelancing", "Investment Profit", "Bonus", "Gift"],
            ("Education", "Expense"): ["Tuition", "Books", "Courses", "Supplies"],
            ("Travel & Leisure", "Expense"): ["Flights", "Hotels", "Activities"]
        }

        category_objs = {}
        for (c_name, c_kind), subs in categories_data.items():
            cat = Category.query.filter_by(name=c_name, user_id=None).first()
            if not cat:
                cat = Category(name=c_name, kind=c_kind, user_id=None, is_active=True, created_at=utcnow())
                db.session.add(cat)
                db.session.flush()
            category_objs[c_name] = cat

            for sub_name in subs:
                sub = Subcategory.query.filter_by(category_id=cat.id, name=sub_name).first()
                if not sub:
                    sub = Subcategory(category_id=cat.id, name=sub_name, is_active=True)
                    db.session.add(sub)
        db.session.flush()

        print("5. Seeding Merchants & Statement Aliases...")
        merchants_data = [
            ("KFC Pakistan", "Food & Dining", ["POS PURCHASE KFC DHA", "KFC LAHORE GULBERG", "KFC DELIVERY", "KFC KARACHI"]),
            ("McDonald's", "Food & Dining", ["MCDONALDS DRIVE THRU", "MCDONALDS LAHORE", "MCD DELIVERY"]),
            ("Subway", "Food & Dining", ["SUBWAY RESTAURANT", "SUBWAY DHA PHASE 5"]),
            ("Shell", "Transport", ["SHELL PETROL STATION", "SHELL MM ALAM", "SHELL DEFENCE", "SHELL SERVICE STATION"]),
            ("Total Parco", "Transport", ["TOTAL PARCO FUEL", "TOTAL FILLING STATION"]),
            ("PSO", "Transport", ["PSO SERVICE STATION", "PSO FUEL PUMP"]),
            ("Uber", "Transport", ["UBER TRIP HELP.UBER.COM", "UBER BV NETHERLANDS", "UBER RIDE"]),
            ("Careem", "Transport", ["CAREEM RIDE PAYMENT", "CAREEM NOW"]),
            ("Netflix", "Subscriptions", ["NETFLIX.COM", "NETFLIX MONTHLY SUB", "NETFLIX STREAMING"]),
            ("Spotify", "Subscriptions", ["SPOTIFY PREMIUM", "SPOTIFY AB SWEDEN"]),
            ("OpenAI", "Subscriptions", ["OPENAI CHATGPT PLUS", "CHATGPT SUBSCRIPTION"]),
            ("Carrefour", "Groceries", ["CARREFOUR PACKAGES MALL", "CARREFOUR HYPERMARKET"]),
            ("Al-Fatah", "Groceries", ["AL FATAH STORE HYPERMARKET", "AL FATAH GULBERG"]),
            ("LESCO", "Utilities", ["LESCO ELECTRICITY BILL PAYMENT", "LESCO BILL"]),
            ("SNGPL", "Utilities", ["SNGPL GAS BILL ONLINE", "SNGPL BILL"]),
            ("PTCL", "Utilities", ["PTCL INTERNET SMART TV BILL", "PTCL EVO FIBER"]),
            ("HBL ATM", "Cash Withdrawal", ["ATM CASH WITHDRAWAL HBL", "HBL ATM CASH"]),
            ("Meezan Bank ATM", "Cash Withdrawal", ["ATM WITHDRAWAL MEEZAN BANK", "MEEZAN ATM CASH"]),
        ]

        for m_name, cat_name, aliases in merchants_data:
            cat = category_objs.get(cat_name)
            merch = Merchant.query.filter_by(name=m_name).first()
            if not merch:
                merch = Merchant(name=m_name, default_category_id=cat.id if cat else None, is_active=True)
                db.session.add(merch)
                db.session.flush()

            for alias_text in aliases:
                norm_alias = normalize_description(alias_text)
                al = MerchantAlias.query.filter_by(merchant_id=merch.id, alias_text=norm_alias).first()
                if not al:
                    al = MerchantAlias(merchant_id=merch.id, alias_text=norm_alias, source="Admin", created_at=utcnow())
                    db.session.add(al)
        db.session.flush()

        print("6. Seeding Global Category Rules...")
        rules_data = [
            ("SALARY", "Income", 20),
            ("FREELANCE", "Income", 18),
            ("PROFIT", "Income", 15),
            ("PETROL", "Transport", 15),
            ("FUEL", "Transport", 15),
            ("GROCERY", "Groceries", 15),
            ("SUPERMARKET", "Groceries", 15),
            ("PHARMACY", "Healthcare", 15),
            ("HOSPITAL", "Healthcare", 15),
            ("CLINIC", "Healthcare", 15),
            ("ATM CASH", "Cash Withdrawal", 25),
        ]

        for pat, cat_name, prio in rules_data:
            cat = category_objs.get(cat_name)
            if cat:
                r = CategoryRule.query.filter_by(pattern=pat, category_id=cat.id, user_id=None).first()
                if not r:
                    r = CategoryRule(category_id=cat.id, pattern=pat, match_type="Contains", priority=prio, is_active=True)
                    db.session.add(r)
        db.session.flush()

        print("7. Seeding Admin and Demo Users...")
        # Admin user
        admin_email = "admin@finance.app"
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                full_name="System Administrator",
                email=admin_email,
                password_hash=hash_password("Admin123!"),
                role_id=role_objs["admin"].id,
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(admin)
            db.session.flush()

            pref = UserPreference(user_id=admin.id, currency_code="PKR", timezone="Asia/Karachi", theme="light", week_start=0, created_at=utcnow(), updated_at=utcnow())
            notif_pref = NotificationPreference(user_id=admin.id, budget_alerts=True, anomaly_alerts=True, subscription_alerts=True, email_enabled=False, created_at=utcnow())
            db.session.add(pref)
            db.session.add(notif_pref)

        # Demo user
        demo_email = "demo@finance.app"
        demo = User.query.filter_by(email=demo_email).first()
        if not demo:
            demo = User(
                full_name="Sarah Khan",
                email=demo_email,
                password_hash=hash_password("Demo123!"),
                role_id=role_objs["user"].id,
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(demo)
            db.session.flush()

            pref = UserPreference(user_id=demo.id, currency_code="PKR", timezone="Asia/Karachi", theme="light", week_start=0, created_at=utcnow(), updated_at=utcnow())
            notif_pref = NotificationPreference(user_id=demo.id, budget_alerts=True, anomaly_alerts=True, subscription_alerts=True, email_enabled=False, created_at=utcnow())
            db.session.add(pref)
            db.session.add(notif_pref)
        db.session.flush()

        print("8. Seeding Demo Accounts & Transactions...")
        # Create accounts for demo user
        main_bank = FinancialAccount.query.filter_by(user_id=demo.id, name="HBL Main Account").first()
        if not main_bank:
            main_bank = FinancialAccount(
                user_id=demo.id,
                account_type_id=type_objs["current"].id,
                name="HBL Main Account",
                institution_name="Habib Bank Limited",
                currency_code="PKR",
                opening_balance=Decimal("150000.00"),
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(main_bank)

        cash_wallet = FinancialAccount.query.filter_by(user_id=demo.id, name="Cash in Wallet").first()
        if not cash_wallet:
            cash_wallet = FinancialAccount(
                user_id=demo.id,
                account_type_id=type_objs["cash"].id,
                name="Cash in Wallet",
                institution_name="Cash Wallet",
                currency_code="PKR",
                opening_balance=Decimal("15000.00"),
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(cash_wallet)
        db.session.flush()

        # Seed realistic transactions for demo user across recent months
        today = date.today()
        seed_txs = [
            # Incomes
            (today - timedelta(days=60), "MONTHLY SALARY CREDIT TECH CORP", Decimal("250000.00"), "income", "Income", "TX-SAL-01"),
            (today - timedelta(days=30), "MONTHLY SALARY CREDIT TECH CORP", Decimal("250000.00"), "income", "Income", "TX-SAL-02"),
            (today - timedelta(days=2), "FREELANCE UPWORK ESCROW PAYOUT", Decimal("65000.00"), "income", "Income", "TX-FREE-01"),
            
            # Recurring Subscriptions (Netflix, Spotify, ChatGPT)
            (today - timedelta(days=62), "NETFLIX.COM MONTHLY SUB", Decimal("1500.00"), "expense", "Subscriptions", "TX-NF-01"),
            (today - timedelta(days=32), "NETFLIX.COM MONTHLY SUB", Decimal("1500.00"), "expense", "Subscriptions", "TX-NF-02"),
            (today - timedelta(days=2), "NETFLIX.COM MONTHLY SUB", Decimal("1500.00"), "expense", "Subscriptions", "TX-NF-03"),
            
            (today - timedelta(days=65), "SPOTIFY PREMIUM AB", Decimal("599.00"), "expense", "Subscriptions", "TX-SP-01"),
            (today - timedelta(days=35), "SPOTIFY PREMIUM AB", Decimal("599.00"), "expense", "Subscriptions", "TX-SP-02"),
            (today - timedelta(days=5), "SPOTIFY PREMIUM AB", Decimal("599.00"), "expense", "Subscriptions", "TX-SP-03"),
            
            (today - timedelta(days=61), "OPENAI CHATGPT PLUS", Decimal("5800.00"), "expense", "Subscriptions", "TX-GPT-01"),
            (today - timedelta(days=31), "OPENAI CHATGPT PLUS", Decimal("5800.00"), "expense", "Subscriptions", "TX-GPT-02"),
            (today - timedelta(days=1), "OPENAI CHATGPT PLUS", Decimal("5800.00"), "expense", "Subscriptions", "TX-GPT-03"),

            # Groceries
            (today - timedelta(days=55), "CARREFOUR PACKAGES MALL", Decimal("14250.00"), "expense", "Groceries", "TX-GR-01"),
            (today - timedelta(days=40), "AL FATAH STORE HYPERMARKET", Decimal("9800.00"), "expense", "Groceries", "TX-GR-02"),
            (today - timedelta(days=25), "CARREFOUR PACKAGES MALL", Decimal("16400.00"), "expense", "Groceries", "TX-GR-03"),
            (today - timedelta(days=10), "AL FATAH STORE HYPERMARKET", Decimal("8200.00"), "expense", "Groceries", "TX-GR-04"),
            (today - timedelta(days=3), "CARREFOUR PACKAGES MALL", Decimal("12100.00"), "expense", "Groceries", "TX-GR-05"),

            # Food & Dining
            (today - timedelta(days=50), "POS PURCHASE KFC DHA", Decimal("2850.00"), "expense", "Food & Dining", "TX-FD-01"),
            (today - timedelta(days=38), "MCDONALDS DRIVE THRU GULBERG", Decimal("1950.00"), "expense", "Food & Dining", "TX-FD-02"),
            (today - timedelta(days=22), "SUBWAY RESTAURANT LAHORE", Decimal("1450.00"), "expense", "Food & Dining", "TX-FD-03"),
            (today - timedelta(days=15), "POS PURCHASE KFC DHA", Decimal("3200.00"), "expense", "Food & Dining", "TX-FD-04"),
            (today - timedelta(days=7), "MCDONALDS DRIVE THRU GULBERG", Decimal("2400.00"), "expense", "Food & Dining", "TX-FD-05"),

            # Transport
            (today - timedelta(days=52), "SHELL PETROL STATION MM ALAM", Decimal("7500.00"), "expense", "Transport", "TX-TR-01"),
            (today - timedelta(days=45), "CAREEM RIDE PAYMENT", Decimal("950.00"), "expense", "Transport", "TX-TR-02"),
            (today - timedelta(days=34), "SHELL PETROL STATION MM ALAM", Decimal("8000.00"), "expense", "Transport", "TX-TR-03"),
            (today - timedelta(days=20), "UBER TRIP HELP.UBER.COM", Decimal("1200.00"), "expense", "Transport", "TX-TR-04"),
            (today - timedelta(days=12), "SHELL PETROL STATION MM ALAM", Decimal("7800.00"), "expense", "Transport", "TX-TR-05"),
            (today - timedelta(days=4), "CAREEM RIDE PAYMENT", Decimal("850.00"), "expense", "Transport", "TX-TR-06"),

            # Utilities
            (today - timedelta(days=50), "LESCO ELECTRICITY BILL PAYMENT", Decimal("24500.00"), "expense", "Utilities", "TX-UT-01"),
            (today - timedelta(days=48), "PTCL INTERNET SMART TV BILL", Decimal("4500.00"), "expense", "Utilities", "TX-UT-02"),
            (today - timedelta(days=18), "LESCO ELECTRICITY BILL PAYMENT", Decimal("22800.00"), "expense", "Utilities", "TX-UT-03"),
            (today - timedelta(days=16), "PTCL INTERNET SMART TV BILL", Decimal("4500.00"), "expense", "Utilities", "TX-UT-04"),

            # Cash Withdrawals
            (today - timedelta(days=42), "ATM CASH WITHDRAWAL HBL", Decimal("20000.00"), "expense", "Cash Withdrawal", "TX-ATM-01"),
            (today - timedelta(days=14), "ATM CASH WITHDRAWAL HBL", Decimal("25000.00"), "expense", "Cash Withdrawal", "TX-ATM-02"),

            # Unusual Anomaly Expense! (Huge Laptop purchase for anomaly demo)
            (today - timedelta(days=8), "MACBOOK PRO M3 MAX RETAIL APPLE STORE", Decimal("185000.00"), "expense", "Shopping", "TX-ANOMALY-01"),
        ]

        # Check if transactions already exist
        existing_count = Transaction.query.filter_by(user_id=demo.id).count()
        if existing_count == 0:
            for t_date, desc, amt, t_direction, cat_name, ref in seed_txs:
                cat = category_objs.get(cat_name)
                tx_t = tx_type_objs[t_direction]
                norm_d = normalize_description(desc)
                
                # Check merchant
                merch, _ = CategorizationService.match_merchant_and_alias(norm_d)

                tx = Transaction(
                    user_id=demo.id,
                    account_id=main_bank.id,
                    transaction_type_id=tx_t.id,
                    transaction_status_id=tx_status_objs["completed"].id,
                    category_id=cat.id if cat else None,
                    merchant_id=merch.id if merch else None,
                    transaction_date=t_date,
                    description_original=desc,
                    description_normalized=norm_d,
                    amount=amt,
                    currency_code="PKR",
                    reference=ref,
                    category_confidence=Decimal("0.9800"),
                    category_method="Seed/Merchant",
                    is_reviewed=True,
                    created_at=utcnow(),
                    updated_at=utcnow()
                )
                db.session.add(tx)
            db.session.flush()

        print("9. Seeding Demo Budget...")
        existing_budget = Budget.query.filter_by(user_id=demo.id, name="Monthly Household Budget").first()
        if not existing_budget:
            b_start = date(today.year, today.month, 1)
            b_end = date(today.year, today.month, 28)
            budget = Budget(
                user_id=demo.id,
                name="Monthly Household Budget",
                period_type="Monthly",
                start_date=b_start,
                end_date=b_end,
                currency_code="PKR",
                is_active=True
            )
            db.session.add(budget)
            db.session.flush()

            budget_items = [
                ("Food & Dining", Decimal("25000.00"), Decimal("80.00")),
                ("Groceries", Decimal("35000.00"), Decimal("80.00")),
                ("Transport", Decimal("20000.00"), Decimal("80.00")),
                ("Utilities", Decimal("35000.00"), Decimal("85.00")),
                ("Subscriptions", Decimal("10000.00"), Decimal("90.00")),
            ]
            for c_name, lim, warn in budget_items:
                cat = category_objs.get(c_name)
                if cat:
                    item = BudgetItem(
                        budget_id=budget.id,
                        category_id=cat.id,
                        limit_amount=lim,
                        warning_percent=warn
                    )
                    db.session.add(item)
            db.session.flush()

        print("10. Seeding Demo Savings Goal...")
        existing_goal = SavingsGoal.query.filter_by(user_id=demo.id, name="Emergency Reserve Fund").first()
        if not existing_goal:
            goal = SavingsGoal(
                user_id=demo.id,
                name="Emergency Reserve Fund",
                target_amount=Decimal("300000.00"),
                target_date=today + timedelta(days=180),
                currency_code="PKR",
                status="Active",
                created_at=utcnow()
            )
            db.session.add(goal)
            db.session.flush()

            contrib1 = SavingsContribution(
                goal_id=goal.id,
                amount=Decimal("50000.00"),
                contribution_date=today - timedelta(days=45),
                note="Initial bonus savings"
            )
            contrib2 = SavingsContribution(
                goal_id=goal.id,
                amount=Decimal("40000.00"),
                contribution_date=today - timedelta(days=15),
                note="Monthly savings allocation"
            )
            db.session.add(contrib1)
            db.session.add(contrib2)
            db.session.flush()

        db.session.commit()

        print("11. Training Baseline ML Model...")
        CategorizationService.train_baseline_model()

        print("12. Running initial Anomaly & Subscription scans for demo user...")
        try:
            AnomalyService.run_detection(demo.id, today - timedelta(days=60), today)
            SubscriptionService.detect_recurring_candidates(demo.id)
        except Exception as e:
            print("Scan notice:", e)

        print("\n=== SEEDING COMPLETED SUCCESSFULLY! ===")
        print("Admin user: admin@finance.app / Admin123!")
        print("Demo user:  demo@finance.app  / Demo123!")

if __name__ == "__main__":
    run_seed()
