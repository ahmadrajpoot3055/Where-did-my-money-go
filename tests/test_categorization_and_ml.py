from app.services.categorization_service import CategorizationService
from app.utils.validators import normalize_description

def test_normalization():
    assert normalize_description("  pos purchase   KFC dha! ") == "POS PURCHASE KFC DHA"
    assert normalize_description("netflix.com   ") == "NETFLIX.COM"

def test_merchant_alias_categorization(app):
    with app.app_context():
        # KFC alias was seeded in conftest
        cat, merch, conf, method = CategorizationService.categorize("POS PURCHASE KFC DHA 102", user_id=1)
        assert cat is not None
        assert cat.name == "Food & Dining"
        assert merch.name == "KFC"
        assert method == "Merchant"
        assert conf > 0.90

def test_rule_categorization(app):
    with app.app_context():
        # SHELL rule was seeded in conftest
        cat, merch, conf, method = CategorizationService.categorize("SHELL PETROL STATION GULBERG", user_id=1)
        assert cat is not None
        assert cat.name == "Transport"
        assert method == "Rule"

def test_ml_baseline_training(app):
    with app.app_context():
        trained = CategorizationService.train_baseline_model()
        assert trained is True
        # Test ML suggestion on unseen text
        cat, merch, conf, method = CategorizationService.categorize("MCDONALDS BURGERS", user_id=1)
        assert cat is not None
        assert cat.name == "Food & Dining"

