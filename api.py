"""
CatalogIQ REST API — FastAPI wrapper around the existing pipeline.

Provides programmatic access to the intelligence pipeline via HTTP,
alongside the existing Streamlit UI.

Run with:
    uvicorn api:app --reload

OpenAPI docs at:
    http://localhost:8000/docs
"""

from __future__ import annotations

import csv
import io
import time
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pipeline.correction_memory import load_corrections
from pipeline.enrichment import enrich_catalog
from pipeline.reference_data import DATA_DIR, load_reference_data, reference_data_status
from pipeline.schemas import ProductResult

app = FastAPI(
    title="CatalogIQ API",
    description="Evidence-Driven Product Intelligence for Industrial Commerce",
    version="1.0.0",
)

_reference_data = None


def _get_ref():
    global _reference_data
    if _reference_data is None:
        _reference_data = load_reference_data()
    return _reference_data


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ProductRow(BaseModel):
    product_id: str = Field(..., description="Unique product identifier")
    manufacturer: Optional[str] = Field(None, description="Raw manufacturer name")
    mpn: Optional[str] = Field(None, description="Manufacturer part number")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, description="Product category")
    raw_specs: Optional[str] = Field(None, description="Raw specifications text")


class EnrichRequest(BaseModel):
    products: list[ProductRow] = Field(..., description="List of product rows to enrich")


class FieldResultResponse(BaseModel):
    field: str
    value: Optional[str]
    confidence: float
    confidence_display: str
    decision: str
    reason: str
    is_conflict: bool
    conflict_severity: float
    correction_applied: bool
    evidence: list[dict]
    validation: dict


class ProductResultResponse(BaseModel):
    product_id: str
    overall_trust: float
    overall_decision: str
    conflict_count: int
    fields: dict[str, FieldResultResponse]


class EnrichResponse(BaseModel):
    n_products: int
    elapsed_seconds: float
    results: list[ProductResultResponse]


class HealthResponse(BaseModel):
    status: str
    reference_data: dict[str, bool]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _product_result_to_response(r: ProductResult) -> ProductResultResponse:
    fields = {}
    for name, fr in r.fields.items():
        fields[name] = FieldResultResponse(
            field=fr.field,
            value=fr.value,
            confidence=round(fr.confidence, 4),
            confidence_display=fr.confidence_pct(),
            decision=fr.decision.value,
            reason=fr.reason,
            is_conflict=fr.is_conflict,
            conflict_severity=round(fr.conflict_severity, 3),
            correction_applied=fr.correction_applied,
            evidence=[e.to_dict() for e in fr.evidence],
            validation=fr.validation.to_dict(),
        )
    return ProductResultResponse(
        product_id=r.product_id,
        overall_trust=round(r.overall_trust(), 4),
        overall_decision=r.overall_decision().value,
        conflict_count=r.conflict_count(),
        fields=fields,
    )


def _rows_from_csv_bytes(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    """Return application health and reference-data loading status."""
    status = reference_data_status()
    return HealthResponse(status="ok", reference_data=status)


@app.post("/enrich", response_model=EnrichResponse, tags=["enrich"])
def enrich_json(body: EnrichRequest):
    """Enrich a list of product rows sent as JSON."""
    ref = _get_ref()
    corrections = load_corrections()
    rows = [p.model_dump() for p in body.products]
    t0 = time.perf_counter()
    results = enrich_catalog(rows, ref, corrections)
    elapsed = time.perf_counter() - t0
    return EnrichResponse(
        n_products=len(results),
        elapsed_seconds=round(elapsed, 4),
        results=[_product_result_to_response(r) for r in results],
    )


@app.post("/enrich/csv", response_model=EnrichResponse, tags=["enrich"])
def enrich_csv(file: UploadFile = File(...)):
    """Enrich products from an uploaded CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = file.file.read()
    try:
        rows = _rows_from_csv_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    ref = _get_ref()
    corrections = load_corrections()
    t0 = time.perf_counter()
    results = enrich_catalog(rows, ref, corrections)
    elapsed = time.perf_counter() - t0
    return EnrichResponse(
        n_products=len(results),
        elapsed_seconds=round(elapsed, 4),
        results=[_product_result_to_response(r) for r in results],
    )
