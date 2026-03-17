import img2pdf
from PIL import Image
from pathlib import Path
import shutil
import uuid


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def normalize_to_pdf(input_path: str, output_dir: str) -> str:
    """
    Recibe cualquier archivo (PDF, PNG, JPG) y devuelve
    la ruta a un PDF normalizado en output_dir.
    Lanza ValueError si el formato no es soportado o el archivo no existe.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise ValueError(f"Archivo no encontrado: {input_path}")

    ext = input_path.suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {ext}")

    # UUID evita colisiones si llegan dos archivos con el mismo nombre
    output_path = output_dir / f"{uuid.uuid4().hex}.pdf"

    if ext == ".pdf":
        shutil.copy2(input_path, output_path)

    elif ext in {".png", ".jpg", ".jpeg"}:
        # Solo convertimos a RGB si la imagen tiene canal alpha (ej: PNG con transparencia)
        # Si no tiene alpha, img2pdf puede convertir directamente — más eficiente
        with Image.open(input_path) as img:
            needs_rgb = img.mode in ("RGBA", "LA", "P")

        if needs_rgb:
            temp_jpg = output_dir / f"{uuid.uuid4().hex}_temp.jpg"
            try:
                with Image.open(input_path) as img:
                    img.convert("RGB").save(temp_jpg, "JPEG")
                with open(output_path, "wb") as f:
                    f.write(img2pdf.convert(str(temp_jpg)))
            finally:
                if temp_jpg.exists():
                    temp_jpg.unlink()
        else:
            # Conversión directa sin pasos intermedios
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(str(input_path)))

    return str(output_path)