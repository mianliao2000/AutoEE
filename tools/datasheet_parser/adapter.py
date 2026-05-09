from __future__ import annotations

from typing import Dict


def parse_datasheet(pdf_path: str) -> Dict[str, object]:
    return {"status": "not_configured", "pdf_path": pdf_path, "confidence": "missing"}


def extract_pinout(parsed_datasheet: Dict[str, object]) -> Dict[str, object]:
    return {"status": "requires_human_review", "pinout": {}, "source": parsed_datasheet.get("pdf_path")}


def extract_abs_max_ratings(parsed_datasheet: Dict[str, object]) -> Dict[str, object]:
    return {"status": "missing", "ratings": {}, "source": parsed_datasheet.get("pdf_path")}


def extract_package_info(parsed_datasheet: Dict[str, object]) -> Dict[str, object]:
    return {"status": "requires_human_review", "package": {}, "source": parsed_datasheet.get("pdf_path")}
