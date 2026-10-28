import numpy as np
import pandas as pd
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from pipeline import survey
from pipeline.features import PMT_FEATURES

from .models import Indicator
from .services.simulator import reached


class SurveyRatioTests(TestCase):
    def test_weighted_share_and_domain(self):
        df = pd.DataFrame({
            "y": [1, 0, 1, 1], "w": [1.0, 3.0, 2.0, 2.0], "d": [1, 1, 0, 1],
            "stratum": ["a", "a", "b", "b"], "psu": [1, 2, 3, 4],
        })
        r = survey.ratio(df, "y", pd.Series(1, index=df.index), weight="w", domain="d")
        self.assertAlmostEqual(r["estimate"], 3 / 6)  # (1*1 + 0*3 + 1*2) / (1 + 3 + 2)
        self.assertEqual(r["n"], 3)
        self.assertGreater(r["se"], 0)

    def test_empty_domain_is_nan(self):
        df = pd.DataFrame({"y": [1], "w": [1.0], "stratum": ["a"], "psu": [1]})
        self.assertTrue(np.isnan(survey.ratio(df, "y", "y", weight="w", domain=pd.Series([0]))["estimate"]))


class SimulatorTests(TestCase):
    def test_reached_is_capped_by_excluded_pool(self):
        self.assertAlmostEqual(reached(1000, 0.8, 0), 0)
        self.assertLess(reached(1000, 0.8, 10**7), 1000.0001)
        self.assertGreater(reached(1000, 0.8, 500), reached(1000, 0.4, 500))


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_indicators", verbosity=0)
        call_command("load_satellite", verbosity=0)

    def test_pages_render(self):
        slug = Indicator.objects.first().district.slug
        for url in [reverse("dashboard:map"), reverse("dashboard:simulator") + "?pct=20",
                    reverse("dashboard:checker"), reverse("dashboard:about"),
                    reverse("dashboard:district", args=[slug]), reverse("dashboard:geojson")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_district_shows_satellite_panel(self):
        slug = Indicator.objects.first().district.slug
        resp = self.client.get(reverse("dashboard:district", args=[slug]))
        self.assertIsNotNone(resp.context["satellite"])
        self.assertContains(resp, "Satellite view")

    def test_need_based_never_worse_than_proportional(self):
        ctx = self.client.get(reverse("dashboard:simulator") + "?pct=15").context
        self.assertGreaterEqual(ctx["result"]["need_total"], ctx["result"]["proportional_total"])

    def test_checker_scores_household(self):
        data = {f["name"]: (f.get("min", 0) if f["kind"] != "bool" else "") for f in PMT_FEATURES}
        data = {k: v for k, v in data.items() if v != ""}
        resp = self.client.post(reverse("dashboard:checker"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["result"])
        self.assertTrue(0 <= resp.context["result"]["probability"] <= 1)
