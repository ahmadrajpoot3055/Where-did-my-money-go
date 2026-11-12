from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class AnomalyModel(db.Model):
    __tablename__ = "anomaly_models"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(40), nullable=False)
    algorithm = db.Column(db.String(80), nullable=False) # e.g. IsolationForest, Z-Score, Category-IQR
    artifact_path = db.Column(db.String(255), nullable=True)
    trained_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    runs = db.relationship("AnalysisRun", back_populates="anomaly_model")

    def __repr__(self):
        return f"<AnomalyModel {self.name} v{self.version}>"


class AnalysisRun(db.Model):
    __tablename__ = "analysis_runs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    anomaly_model_id = db.Column(db.Integer, db.ForeignKey("anomaly_models.id", ondelete="SET NULL"), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Queued", nullable=False) # Queued, Running, Completed, Failed
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="analysis_runs")
    anomaly_model = db.relationship("AnomalyModel", back_populates="runs")
    results = db.relationship("AnomalyResult", back_populates="analysis_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnalysisRun id={self.id} user={self.user_id} status={self.status}>"


class AnomalyResult(db.Model):
    __tablename__ = "anomaly_results"

    id = db.Column(db.Integer, primary_key=True)
    analysis_run_id = db.Column(db.Integer, db.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    score = db.Column(db.Numeric(7, 4), nullable=False) # Anomaly score
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(25), default="New", nullable=False) # New, Reviewed, Expected, Incorrect
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    analysis_run = db.relationship("AnalysisRun", back_populates="results")
    transaction = db.relationship("Transaction", back_populates="anomaly_results")
    reviews = db.relationship("AnomalyReview", back_populates="anomaly_result", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnomalyResult tx={self.transaction_id} score={self.score}>"


class AnomalyReview(db.Model):
    __tablename__ = "anomaly_reviews"

    id = db.Column(db.Integer, primary_key=True)
    anomaly_result_id = db.Column(db.Integer, db.ForeignKey("anomaly_results.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = db.Column(db.String(30), nullable=False) # Expected, Incorrect, FollowUp
    comment = db.Column(db.String(500), nullable=True)
    reviewed_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    anomaly_result = db.relationship("AnomalyResult", back_populates="reviews")
    user = db.relationship("User")

    def __repr__(self):
        return f"<AnomalyReview result={self.anomaly_result_id} decision={self.decision}>"

