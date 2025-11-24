# app/api/endpoints/converter.py

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import subprocess
import os
import uuid
from pathlib import Path
import shutil
from typing import Optional
import asyncio

router = APIRouter()

# Directorio temporal
TEMP_DIR = Path("/tmp/excel-to-pdf")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/health")
async def converter_health():
    """Verificar que LibreOffice está disponible"""
    try:
        result = subprocess.run(
            ["libreoffice", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return {
            "status": "healthy",
            "libreoffice": result.stdout.strip(),
            "service": "Excel to PDF Converter"
        }
    except FileNotFoundError:
        return {
            "status": "unhealthy",
            "error": "LibreOffice no está instalado",
            "service": "Excel to PDF Converter"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "Excel to PDF Converter"
        }

@router.post("/excel-to-pdf")
async def convert_excel_to_pdf(
    file: UploadFile = File(...),
    quality: Optional[str] = "normal"
):
    """
    Convierte un archivo Excel a PDF usando LibreOffice
    
    Args:
        file: Archivo Excel (.xlsx, .xls, .xlsm)
        quality: Calidad del PDF (normal, high) - opcional
        
    Returns:
        Archivo PDF descargable
    """
    
    print(f"\n{'='*60}")
    print(f"📊 [CONVERTER] Nueva solicitud de conversión")
    print(f"   Archivo: {file.filename}")
    print(f"   Tamaño: {file.size if hasattr(file, 'size') else 'unknown'} bytes")
    print(f"   Tipo: {file.content_type}")
    print(f"{'='*60}")
    
    # Validar extensión
    if not file.filename.endswith(('.xlsx', '.xls', '.xlsm')):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Formato no válido",
                "message": "Solo se permiten archivos Excel (.xlsx, .xls, .xlsm)",
                "received": file.filename
            }
        )
    
    # Generar ID único
    conversion_id = str(uuid.uuid4())
    
    # Paths temporales
    input_path = TEMP_DIR / f"{conversion_id}.xlsx"
    output_dir = TEMP_DIR / conversion_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Guardar archivo Excel
        print(f"💾 [CONVERTER] Guardando Excel temporal...")
        content = await file.read()
        
        with open(input_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"✅ [CONVERTER] Excel guardado: {input_path} ({len(content):,} bytes)")
        
        # 2. Comando LibreOffice
        command = [
            "libreoffice",
            "--headless",
            "--invisible",
            "--nocrashreport",
            "--nodefault",
            "--nofirststartwizard",
            "--nolockcheck",
            "--nologo",
            "--norestore",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(input_path)
        ]
        
        print(f"🔧 [CONVERTER] Iniciando conversión con LibreOffice...")
        
        # 3. Ejecutar conversión
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ [CONVERTER] Error en LibreOffice:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Error en conversión",
                    "message": result.stderr or "Error desconocido de LibreOffice",
                    "stdout": result.stdout
                }
            )
        
        print(f"✅ [CONVERTER] Conversión completada")
        
        # 4. Buscar PDF generado
        pdf_files = list(output_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ [CONVERTER] No se encontró PDF generado")
            print(f"   Archivos en directorio: {list(output_dir.iterdir())}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "PDF no generado",
                    "message": "LibreOffice no generó el archivo PDF esperado"
                }
            )
        
        pdf_path = pdf_files[0]
        pdf_size = pdf_path.stat().st_size
        
        print(f"✅ [CONVERTER] PDF encontrado: {pdf_path.name} ({pdf_size:,} bytes)")
        
        # 5. Generar nombre de salida
        output_filename = f"{Path(file.filename).stem}.pdf"
        
        print(f"📤 [CONVERTER] Enviando PDF al cliente: {output_filename}")
        print(f"{'='*60}\n")
        
        # 6. Retornar archivo
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=output_filename,
            background=None
        )
        
    except subprocess.TimeoutExpired:
        print(f"❌ [CONVERTER] Timeout en conversión (>30s)")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Timeout",
                "message": "La conversión tardó demasiado tiempo (>30 segundos)"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [CONVERTER] Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno",
                "message": str(e)
            }
        )
    finally:
        # 7. Limpiar archivos temporales (con delay para permitir descarga)
        async def cleanup():
            await asyncio.sleep(2)  # Esperar 2 segundos
            try:
                if input_path.exists():
                    input_path.unlink()
                if output_dir.exists():
                    shutil.rmtree(output_dir, ignore_errors=True)
                print(f"🧹 [CONVERTER] Archivos temporales limpiados: {conversion_id}")
            except Exception as e:
                print(f"⚠️  [CONVERTER] Error al limpiar: {e}")
        
        # Ejecutar limpieza en background
        asyncio.create_task(cleanup())

@router.delete("/cleanup")
async def cleanup_old_files(hours: int = 1):
    """
    Limpia archivos temporales más antiguos que X horas
    """
    import time
    
    print(f"\n🧹 [CONVERTER] Iniciando limpieza de archivos > {hours}h...")
    
    deleted = 0
    now = time.time()
    cutoff = now - (hours * 3600)
    
    try:
        for item in TEMP_DIR.iterdir():
            if item.stat().st_mtime < cutoff:
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item, ignore_errors=True)
                deleted += 1
        
        print(f"✅ [CONVERTER] Limpieza completada: {deleted} items eliminados")
        
        return {
            "status": "success",
            "deleted_items": deleted,
            "cutoff_hours": hours
        }
    except Exception as e:
        print(f"❌ [CONVERTER] Error al limpiar: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al limpiar archivos temporales: {str(e)}"
        )