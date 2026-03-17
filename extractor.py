import pdfplumber
import re
import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


# ── Patrones regex compilados para facturas electrónicas SUNAT ───────────────
# Compilados una sola vez al importar el módulo — mejor rendimiento

PATTERNS = {
    # F\d{3} en lugar de F\w{3}: solo acepta dígitos (F001, no FABC)
    "nro_factura":   re.compile(r"\b(F\d{3}-\d{4,8})\b", re.IGNORECASE),
    "ruc_emisor":    re.compile(r"R\.?U\.?C\.?\s*[:\-]?\s*(\d{11})", re.IGNORECASE),
    "fecha_emision": re.compile(r"Fecha\s+de\s+[Ee]misi[oó]n[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})", re.IGNORECASE),
    "monto_total":   re.compile(r"(?:IMPORTE\s+TOTAL|Total\s+a\s+Pagar|Valor\s+Total)[:\s]*S/?\.?\s*([\d,]+\.\d{2})", re.IGNORECASE),
    "moneda":        re.compile(r"\b(PEN|USD|SOLES?|D[OÓ]LARES?)\b", re.IGNORECASE),
    "proveedor":     re.compile(r"(?:Señor(?:es)?|Cliente|Adquiriente)[:\s]+(.{3,80})", re.IGNORECASE),
    "ruc_cliente":   re.compile(r"(?:RUC\s+del\s+[Aa]dquiriente|RUC\s+[Cc]liente)[:\s]*(\d{11})", re.IGNORECASE),
}

REQUIRED_FIELDS = {"nro_factura", "ruc_emisor", "fecha_emision", "monto_total"}


# ── Estructura tipada de datos ────────────────────────────────────────────────

@dataclass
class FacturaData:
    """Estructura tipada para los campos de una factura SUNAT."""
    nro_factura:    Optional[str]   = None
    ruc_emisor:     Optional[str]   = None
    fecha_emision:  Optional[str]   = None
    monto_total:    Optional[float] = None
    moneda:         str             = "PEN"
    proveedor:      Optional[str]   = None
    ruc_cliente:    Optional[str]   = None


# ── Extracción de texto ───────────────────────────────────────────────────────

def extract_text(pdf_path: str) -> str:
    """Extrae todo el texto del PDF con pdfplumber. Retorna '' si falla."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            parts = [p.extract_text() for p in pdf.pages if p.extract_text()]
            return "\n".join(parts)
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
        return ""


# ── Parseo de campos ──────────────────────────────────────────────────────────

def _best_monto(text: str) -> Optional[str]:
    """
    Para monto_total busca todas las coincidencias y devuelve la que
    tenga mayor contexto de palabras clave (evita capturar subtotales).
    """
    matches = list(PATTERNS["monto_total"].finditer(text))
    if not matches:
        return None
    for match in matches:
        ctx = text[max(0, match.start()-50): match.end()+50].upper()
        if any(kw in ctx for kw in ("TOTAL", "PAGAR", "IMPORTE")):
            return match.group(1).strip()
    return matches[0].group(1).strip()


def parse_fields(text: str) -> FacturaData:
    """Aplica regex sobre el texto y devuelve un FacturaData."""
    result = FacturaData()

    for field, pattern in PATTERNS.items():
        if field == "monto_total":
            raw = _best_monto(text)
            if raw:
                try:
                    result.monto_total = float(raw.replace(",", ""))
                except ValueError:
                    pass
            continue

        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip()

        if field == "moneda":
            result.moneda = "USD" if "D" in value.upper() else "PEN"
        else:
            setattr(result, field, value)

    return result


# ── Validación ────────────────────────────────────────────────────────────────

def validate(fields: FacturaData) -> list[str]:
    """Devuelve lista de campos requeridos faltantes o inválidos."""
    errors = []
    for f in REQUIRED_FIELDS:
        value = getattr(fields, f)
        if value is None:
            errors.append(f)
        elif f == "monto_total" and value <= 0:
            errors.append(f)
    return errors


# ── Orquestador ───────────────────────────────────────────────────────────────

def extract_invoice_data(pdf_path: str) -> dict:
    """
    Orquesta extracción + validación.
    Retorna:
        {"status": "ok",    "data": {...}}
        {"status": "error", "missing": [...], "data": {...}}
    """
    text = extract_text(pdf_path)

    if not text:
        return {
            "status": "error",
            "message": "No se pudo extraer texto del PDF. ¿Está escaneado?",
            "data": {}
        }

    fields = parse_fields(text)
    missing = validate(fields)

    # asdict() serializa el dataclass a dict plano — compatible con jsonify
    data = asdict(fields)

    if missing:
        return {"status": "error", "missing": missing, "data": data}

    return {"status": "ok", "data": data}