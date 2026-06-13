"""Jurisdiction pre-filtering for legal chunk catalog."""

from __future__ import annotations

EU_COUNTRIES = {
    "FIN", "GBR", "DEU", "FRA", "SWE", "NLD", "BEL", "ESP", "ITA", "POL",
    "AUT", "IRL", "PRT", "GRC", "DNK", "CZE", "HUN", "ROU", "BGR", "HRV",
    "SVK", "SVN", "LTU", "LVA", "EST", "LUX", "MLT", "CYP",
}


def jurisdictions_for_country(country_iso: str | None) -> list[str]:
    if not country_iso:
        return ["EU", "ECHR", "EVIDENCE"]

    code = country_iso.upper()
    if code == "FIN":
        return ["FIN", "EU", "ECHR", "EVIDENCE"]
    if code in EU_COUNTRIES:
        return ["EU", "ECHR", "EVIDENCE"]
    return ["EU", "ECHR", "EVIDENCE"]
