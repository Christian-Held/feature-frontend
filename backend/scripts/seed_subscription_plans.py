"""Seed subscription plans into the database."""

from decimal import Decimal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import SessionLocal
from backend.db.models import SubscriptionPlan


def seed_plans():
    """Create free, pro, and enterprise subscription plans."""
    db = SessionLocal()

    try:
        # Check if plans already exist
        existing = db.query(SubscriptionPlan).count()
        if existing > 0:
            print(f"Plans already exist ({existing} found). Skipping seed.")
            return

        plans = [
            SubscriptionPlan(
                name="free",
                display_name="Free Plan",
                description="Perfect for getting started with basic features",
                price_cents=0,
                billing_period=None,
                features={
                    "api_access": True,
                    "priority_support": False,
                    "custom_models": False,
                    "advanced_analytics": False,
                    "dedicated_support": False,
                },
                rate_limit_multiplier=Decimal("1.0"),
                max_jobs_per_month=10,
                max_storage_mb=100,
                max_api_calls_per_day=100,
                is_active=True,
            ),
            SubscriptionPlan(
                name="pro",
                display_name="Pro Plan",
                description="For professionals who need more power and flexibility",
                price_cents=1999,  # $19.99
                billing_period="monthly",
                features={
                    "api_access": True,
                    "priority_support": True,
                    "custom_models": True,
                    "advanced_analytics": True,
                    "dedicated_support": False,
                },
                rate_limit_multiplier=Decimal("5.0"),
                max_jobs_per_month=500,
                max_storage_mb=10000,  # 10 GB
                max_api_calls_per_day=10000,
                is_active=True,
            ),
            SubscriptionPlan(
                name="enterprise",
                display_name="Enterprise Plan",
                description="For teams and organizations with advanced needs",
                price_cents=9999,  # $99.99
                billing_period="monthly",
                features={
                    "api_access": True,
                    "priority_support": True,
                    "custom_models": True,
                    "advanced_analytics": True,
                    "dedicated_support": True,
                    "sso": True,
                    "audit_logs": True,
                },
                rate_limit_multiplier=Decimal("10.0"),
                max_jobs_per_month=None,  # Unlimited
                max_storage_mb=None,  # Unlimited
                max_api_calls_per_day=None,  # Unlimited
                is_active=True,
            ),
        ]

        for plan in plans:
            db.add(plan)
            print(f"✓ Created plan: {plan.display_name} ({plan.name})")

        db.commit()
        print(f"\n✅ Successfully seeded {len(plans)} subscription plans")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding plans: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_plans()
