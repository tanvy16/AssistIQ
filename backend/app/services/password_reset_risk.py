"""Preferred filename alias for password-reset risk assessment."""

from app.services.password_risk import RiskInput, RiskResult, assess_password_reset_risk

__all__ = ["RiskInput", "RiskResult", "assess_password_reset_risk"]
