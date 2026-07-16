"""
PRODAFLT Alert Engine — Unit Tests
===================================
Run with: python -m pytest tests.py -v
Or simply: python tests.py
"""
from __future__ import annotations

import unittest
from decimal import Decimal
from datetime import datetime

from engine import evaluate_campaign
from models import CampaignMetrics, AlertFlag, AlertType


class TestAlertEngine(unittest.TestCase):
    """Test cases for the alert engine threshold logic."""

    def _make_campaign(
        self,
        campaign_id: int = 1,
        creative_code: str = "TEST-001",
        spend: float | None = 120.0,
        clicks: int | None = 45,
        installs: int | None = 12,
        deposits: int | None = 3,
        cpc: float | None = None,
        cpi: float | None = None,
        uepc: float | None = None,
        roi: float | None = None,
        revenue: float | None = None,
    ) -> CampaignMetrics:
        return CampaignMetrics(
            id=campaign_id,
            creative_code=creative_code,
            spend=Decimal(str(spend)) if spend is not None else None,
            clicks=clicks,
            installs=installs,
            deposits=deposits,
            cpc=Decimal(str(cpc)) if cpc is not None else None,
            cpi=Decimal(str(cpi)) if cpi is not None else None,
            uepc=Decimal(str(uepc)) if uepc is not None else None,
            roi=Decimal(str(roi)) if roi is not None else None,
            revenue=Decimal(str(revenue)) if revenue is not None else None,
            recorded_at=datetime.now(),
        )

    # ------------------------------------------------------------------
    # RED (KILL) tests
    # ------------------------------------------------------------------

    def test_red_cpi_kill(self):
        """CPI $5.30 ≥ $5.00 → RED"""
        c = self._make_campaign(cpi=5.30, cpc=1.20, uepc=3.50, roi=0.25)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertIn(AlertType.CPI_SPIKE, d.alert_types)
        self.assertIn("CPI $5.30", d.decision)

    def test_red_cpc_kill(self):
        """CPC $2.80 ≥ $2.50 → RED"""
        c = self._make_campaign(cpi=3.00, cpc=2.80, uepc=3.50)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertIn("CPC $2.80", d.decision)

    def test_red_uepc_kill(self):
        """uEPC $8.50 ≥ $8.00 → RED"""
        c = self._make_campaign(cpi=4.00, cpc=1.50, uepc=8.50)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertIn("uEPC $8.50", d.decision)

    def test_red_roi_kill(self):
        """ROI -60% ≤ -50% → RED"""
        c = self._make_campaign(cpi=4.00, cpc=1.50, uepc=3.50, roi=-0.60)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertIn("ROI -0.6", d.decision)

    def test_red_multiple_signals(self):
        """CPI $6.00 + uEPC $9.00 → RED with multiple triggers"""
        c = self._make_campaign(cpi=6.00, cpc=1.50, uepc=9.00)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertGreaterEqual(len(d.alert_types), 1)

    # ------------------------------------------------------------------
    # GREEN (SCALE) tests
    # ------------------------------------------------------------------

    def test_green_scale(self):
        """uEPC $3.10 < $4, CPI $4.00 ≤ $5, ROI 25% > 0 → GREEN"""
        c = self._make_campaign(cpi=4.00, cpc=1.20, uepc=3.10, roi=0.25)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.GREEN)
        self.assertIn("SCALE", d.decision)

    def test_green_not_enough_conditions(self):
        """Only uEPC good, but CPI missing → not GREEN"""
        c = self._make_campaign(cpi=None, cpc=1.20, uepc=3.10, roi=0.25)
        d = evaluate_campaign(c)
        self.assertNotEqual(d.flag, AlertFlag.GREEN)

    # ------------------------------------------------------------------
    # YELLOW (WATCH) tests
    # ------------------------------------------------------------------

    def test_yellow_watch_uepc(self):
        """uEPC $6.50 between 4 and 8 → YELLOW"""
        c = self._make_campaign(cpi=4.50, cpc=1.80, uepc=6.50, roi=0.10)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.YELLOW)
        self.assertIn("WATCH", d.decision)

    def test_yellow_watch_cpi(self):
        """CPI $4.20 approaching $5 → YELLOW"""
        c = self._make_campaign(cpi=4.20, cpc=1.80, uepc=3.90, roi=0.10)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.YELLOW)

    # ------------------------------------------------------------------
    # WHITE (INSUFFICIENT / NO ACTION) tests
    # ------------------------------------------------------------------

    def test_white_low_spend(self):
        """Spend $5 < $20 → WHITE (insufficient data)"""
        c = self._make_campaign(spend=5.0, clicks=3, installs=1)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.WHITE)
        self.assertIn("INSUFFICIENT DATA", d.decision)

    def test_white_low_clicks(self):
        """Spend $50 but clicks 3 < 10 → WHITE"""
        c = self._make_campaign(spend=50.0, clicks=3, installs=1)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.WHITE)

    def test_white_normal_range(self):
        """Metrics inside normal range, no strong signal → WHITE"""
        c = self._make_campaign(cpi=3.50, cpc=1.20, uepc=3.80, roi=0.15)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.WHITE)
        self.assertIn("NO ACTION", d.decision)

    # ------------------------------------------------------------------
    # Confidence tests
    # ------------------------------------------------------------------

    def test_confidence_high_sample(self):
        """Large sample → confidence 95-100%"""
        c = self._make_campaign(spend=250.0, clicks=120, installs=30, cpi=6.00)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertGreaterEqual(d.confidence, Decimal("95"))

    def test_confidence_low_sample(self):
        """Small sample → confidence 70-85%"""
        c = self._make_campaign(spend=25.0, clicks=12, installs=4, cpi=6.00)
        d = evaluate_campaign(c)
        self.assertEqual(d.flag, AlertFlag.RED)
        self.assertLessEqual(d.confidence, Decimal("85"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
