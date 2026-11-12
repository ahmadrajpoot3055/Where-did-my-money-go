import os
import re
import joblib
from pathlib import Path
from flask import current_app
from app.extensions import db
from app.models.category import Category, Merchant, MerchantAlias, CategoryRule
from app.models.transaction import Transaction
from app.utils.validators import normalize_description

class CategorizationService:
    @staticmethod
    def normalize_text(text: str) -> str:
        return normalize_description(text)

    @classmethod
    def match_merchant_and_alias(cls, norm_text: str):
        """Check merchant aliases for matches in description."""
        aliases = MerchantAlias.query.all()
        for alias in aliases:
            cleaned_alias = cls.normalize_text(alias.alias_text)
            if cleaned_alias and cleaned_alias in norm_text:
                merchant = alias.merchant
                if merchant and merchant.is_active:
                    return merchant, merchant.default_category
        return None, None

    @classmethod
    def match_rules(cls, norm_text: str, user_id: int):
        """Check rules: user-specific first, then global, ordered by priority desc."""
        rules = CategoryRule.query.filter(
            CategoryRule.is_active == True,
            (CategoryRule.user_id == user_id) | (CategoryRule.user_id == None)
        ).order_by(
            CategoryRule.user_id.desc(), # User rules first
            CategoryRule.priority.desc()
        ).all()

        for rule in rules:
            pat = cls.normalize_text(rule.pattern)
            matched = False
            if rule.match_type.lower() == "exact":
                matched = (norm_text == pat)
            elif rule.match_type.lower() == "regex":
                try:
                    if re.search(rule.pattern, norm_text, re.IGNORECASE):
                        matched = True
                except re.error:
                    continue
            else: # Contains
                matched = (pat in norm_text)

            if matched and rule.category and rule.category.is_active:
                return rule.category
        return None

    @classmethod
    def predict_ml(cls, norm_text: str):
        """Predict category using persisted ML vectorizer and classifier."""
        try:
            artifact_dir = Path(current_app.config["ML_ARTIFACTS_FOLDER"])
            model_path = artifact_dir / "category_model.joblib"
            if not model_path.exists():
                return None, 0.0

            pipeline = joblib.load(model_path)
            probs = pipeline.predict_proba([norm_text])[0]
            classes = pipeline.classes_
            best_idx = probs.argmax()
            confidence = float(probs[best_idx])
            cat_name = classes[best_idx]

            # In multi-class classification (7+ classes), 1/N is ~0.14. A threshold of 0.15 indicates above-chance support.
            if confidence >= 0.15:
                category = Category.query.filter_by(name=cat_name, is_active=True).first()
                if category:
                    return category, round(confidence, 4)
        except Exception:
            pass
        return None, 0.0

    @classmethod
    def categorize(cls, description: str, user_id: int):
        """
        Main pipeline:
        1. Merchant Alias
        2. Category Rule
        3. ML Model
        Returns (category, merchant, confidence, method)
        """
        norm_text = cls.normalize_text(description)
        if not norm_text:
            return None, None, 0.0, None

        # 1. Merchant Alias
        merchant, category = cls.match_merchant_and_alias(norm_text)
        if category:
            return category, merchant, 0.9900, "Merchant"
        if merchant and not category:
            # We identified the merchant, but merchant has no default category
            pass

        # 2. Rules
        cat_by_rule = cls.match_rules(norm_text, user_id)
        if cat_by_rule:
            return cat_by_rule, merchant, 0.9500, "Rule"

        # 3. ML Model
        cat_by_ml, confidence = cls.predict_ml(norm_text)
        if cat_by_ml:
            return cat_by_ml, merchant, confidence, "ML"

        return None, merchant, 0.0, None

    @classmethod
    def train_baseline_model(cls):
        """Train or retrain baseline ML model using reviewed transactions + seed corpus."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline

        # Seed training samples
        seed_data = [
            ("POS PURCHASE KFC DHA", "Food & Dining"),
            ("MCDONALDS DRIVE THRU GULBERG", "Food & Dining"),
            ("SUBWAY RESTAURANT LAHORE", "Food & Dining"),
            ("DOMINOS PIZZA ORDER", "Food & Dining"),
            ("CAFE AYLANTO KARACHI", "Food & Dining"),
            ("SHELL PETROL STATION MM ALAM", "Transport"),
            ("TOTAL PARCO FUEL", "Transport"),
            ("PSO SERVICE STATION", "Transport"),
            ("UBER TRIP HELP.UBER.COM", "Transport"),
            ("CAREEM RIDE PAYMENT", "Transport"),
            ("INDRIVE FARE LAHORE", "Transport"),
            ("NETFLIX.COM MONTHLY SUB", "Subscriptions"),
            ("SPOTIFY PREMIUM AB", "Subscriptions"),
            ("YOUTUBE PREMIUM GOOGLE", "Subscriptions"),
            ("CHATGPT PLUS SUBSCRIPTION", "Subscriptions"),
            ("CARREFOUR PACKAGES MALL", "Groceries"),
            ("AL FATAH STORE HYPERMARKET", "Groceries"),
            ("IMTIAZ SUPER MARKET KARACHI", "Groceries"),
            ("METRO CASH AND CARRY", "Groceries"),
            ("JALAL SONS BAKERY GROCERY", "Groceries"),
            ("ATM CASH WITHDRAWAL HBL", "Cash Withdrawal"),
            ("ATM CASH UBL GULBERG", "Cash Withdrawal"),
            ("ATM WITHDRAWAL MEEZAN BANK", "Cash Withdrawal"),
            ("LESCO ELECTRICITY BILL PAYMENT", "Utilities"),
            ("SNGPL GAS BILL ONLINE", "Utilities"),
            ("PTCL INTERNET SMART TV BILL", "Utilities"),
            ("SALARY CREDIT MONTHLY", "Income"),
            ("FREELANCE UPWORK ESCROW PAYOUT", "Income"),
            ("PROFIT ON SAVINGS ACCOUNT", "Income"),
        ]

        # Add reviewed transactions from the database
        reviewed_txs = Transaction.query.filter(
            Transaction.is_reviewed == True,
            Transaction.category_id != None
        ).all()

        texts = [x[0] for x in seed_data]
        labels = [x[1] for x in seed_data]

        for tx in reviewed_txs:
            if tx.category and tx.description_normalized:
                texts.append(tx.description_normalized)
                labels.append(tx.category.name)

        if len(set(labels)) < 2:
            return False

        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=200))
        ])

        pipe.fit(texts, labels)

        artifact_dir = Path(current_app.config["ML_ARTIFACTS_FOLDER"])
        artifact_dir.mkdir(parents=True, exist_ok=True)
        model_path = artifact_dir / "category_model.joblib"
        joblib.dump(pipe, model_path)
        return True
