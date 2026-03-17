# Automatizaci-n-de-facturas-a-SQL
Sistema de procesamiento automático de facturas electrónicas peruanas (SUNAT). Detecta correos con adjuntos, normaliza archivos a PDF, extrae campos clave mediante regex y los registra en SQL Server — todo sin intervención manual.
Stack
CapaTecnologíaAPI de procesamientoPython + FlaskExtracción de textopdfplumberConversión de imágenesimg2pdf + PillowAutomatización de flujosn8n (Docker)Base de datosSQL ServerTrigger de entradaGmail API (OAuth2)

Arquitectura de flujo
Gmail (correo con factura adjunta)
        ↓
   n8n Workflow 1
        ↓
Flask API :5001/procesar
   ├── converter.py  → normaliza PDF/PNG/JPG a PDF
   └── extractor.py  → extrae campos SUNAT con regex
        ↓
   IF status == ok?
   ↙              ↘
SQL INSERT      Gmail (correo de error)

n8n Workflow 2 (18:00 diario)
        ↓
   SQL Query → v_resumen_hoy
        ↓
   Gmail (resumen del día)

 Campos extraídos
CampoDescripciónnro_facturaNúmero de comprobante (F001-XXXXXXXX)ruc_emisorRUC del proveedor (11 dígitos)proveedorRazón social del emisorruc_clienteRUC del receptorfecha_emisionFecha en formato dd/MM/yyyymonto_totalImporte total como floatmonedaPEN o USD

Cómo correr el proyecto
Requisitos

Python 3.10+
SQL Server (instancia local)
Docker Desktop
n8n corriendo en Docker

Instalación
bash# 1. Clonar el repo
git clone https://github.com/brunoportal72/factura-automatizacion
cd factura-automatizacion

# 2. Instalar dependencias
pip install flask img2pdf pdfplumber Pillow pyodbc

# 3. Crear tabla en SQL Server
# Ejecutar create_table.sql en tu instancia

# 4. Levantar Flask
python app.py
n8n
bashdocker start n8n
# Acceder en http://localhost:(tu_url)
Importar los workflows desde la carpeta /workflows.

📁 Estructura del proyecto
factura_api/
├── app.py           # Flask API principal
├── converter.py     # Normalización a PDF
├── extractor.py     # Extracción de campos SUNAT
├── create_table.sql # Schema SQL Server
└── workflows/
    ├── workflow_procesamiento.json
    └── workflow_resumen_diario.json

📌 Notas
El sistema soporta facturas electrónicas SUNAT con texto embebido (no escaneadas)
PDFs escaneados retornan status: error con mensaje descriptivo
El resumen diario se envía automáticamente a las 6pm con el consolidado del día
Extensible a otros formatos de factura modificando los patrones regex en extractor.py


👤 Autor
Bruno Portal Cossio
LinkedIn · GitHub
