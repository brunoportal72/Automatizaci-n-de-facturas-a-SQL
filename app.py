from flask import Flask, request, jsonify
from pathlib import Path
import uuid
import logging

from converter import normalize_to_pdf
from extractor import extract_invoice_data

# ── App & configuración ───────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB máximo

UPLOAD_DIR  = Path("uploads")
PROCESS_DIR = Path("processed")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Verifica que el servicio está activo."""
    return jsonify({"status": "ok"})


@app.route("/procesar", methods=["POST"])
def procesar():
    """
    Procesa un archivo de factura enviado desde n8n.

    Body: multipart/form-data
        file: archivo (PDF, PNG, JPG)

    Response 200: {"status": "ok", "data": {...}, "filename_original": "..."}
    Response 422: {"status": "error", "missing": [...], "data": {...}}
    Response 400/415/500: {"status": "error", "message": "..."}
    """
    pdf_path = None  # necesario para el finally

    # — Validaciones de entrada —
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No se recibió archivo"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"status": "error", "message": "Nombre de archivo vacío"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "status": "error",
            "message": f"Formato '{ext}' no soportado. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 415

    # — Guardado temporal —
    temp_name = f"{uuid.uuid4().hex}{ext}"
    temp_path = UPLOAD_DIR / temp_name
    file.save(temp_path)
    logger.info(f"Archivo recibido: {file.filename} → {temp_name}")

    try:
        # 1. Normalizar a PDF
        pdf_path = normalize_to_pdf(str(temp_path), str(PROCESS_DIR))
        logger.info(f"PDF generado: {Path(pdf_path).name}")

        # 2. Extraer y validar campos
        result = extract_invoice_data(pdf_path)
        result["filename_original"] = file.filename

        status_code = 200 if result["status"] == "ok" else 422
        logger.info(f"Resultado: {result['status']} | {file.filename}")
        return jsonify(result), status_code

    except ValueError as e:
        logger.warning(f"Formato no soportado: {e}")
        return jsonify({"status": "error", "message": str(e)}), 415

    except Exception as e:
        logger.error(f"Error interno: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error interno: {str(e)}"}), 500

    finally:
        # Limpiar temporales 
        if temp_path.exists():
            temp_path.unlink()
        if pdf_path and Path(pdf_path).exists():
            Path(pdf_path).unlink()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)