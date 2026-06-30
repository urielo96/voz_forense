#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para services.py
Ubicación: raíz del proyecto (junto a manage.py)
Uso: python test_services.py
"""

import sys
import os
import django

# Configurar Django antes de importar cualquier módulo del proyecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuration.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from extraccion import services as sc

# ── Ruta a los archivos de prueba ──────────────────────────────────────
DIRECTORIO_PRUEBA = "tests/fixtures"

# ── Parámetros de prueba ───────────────────────────────────────────────
GENERO         = "F"
VOCALES        = ['a', 'e', 'i', 'o', 'u']
PITCH_MODE     = "mean"
FORMANT_MODE   = [1, 2, 3, 4]
INTENSITY_MODE = "maximum"   # <- el que fallaba antes del fix

CENTER_B = True
SD_B     = True
SK_B     = True
KUR_B    = True

# ──────────────────────────────────────────────────────────────────────

errores = []  # acumula fallos para reportar al final


def test_process_file_s():
    """Prueba extracción de /s/ con intensity_mode='maximum' — el caso que fallaba."""
    print("\n=== TEST: process_file_s (modo maximum) ===")
    archivos = [
        os.path.splitext(os.path.join(DIRECTORIO_PRUEBA, f))[0]
        for f in os.listdir(DIRECTORIO_PRUEBA)
        if f.endswith('.wav')
    ]
    if not archivos:
        msg = f"No se encontraron archivos .wav en: {DIRECTORIO_PRUEBA}"
        print(f"❌ {msg}")
        errores.append(msg)
        return

    for file_path in archivos:
        print(f"\n  Procesando: {os.path.basename(file_path)}")
        try:
            df = sc.process_file_s(
                file_path,
                intensity_mode=INTENSITY_MODE,
                center_b=CENTER_B,
                sd_b=SD_B,
                sk_b=SK_B,
                kur_b=KUR_B,
            )
            print(f"  ✅ OK — {len(df)} intervalos encontrados")
            print(df.head().to_string())
        except Exception as e:
            msg = f"process_file_s falló en {os.path.basename(file_path)}: {e}"
            print(f"  ❌ {msg}")
            errores.append(msg)


def test_process_file_vocal():
    """Prueba extracción de vocales."""
    print("\n=== TEST: process_file_vocal ===")
    archivos = [
        os.path.splitext(os.path.join(DIRECTORIO_PRUEBA, f))[0]
        for f in os.listdir(DIRECTORIO_PRUEBA)
        if f.endswith('.wav')
    ]
    if not archivos:
        msg = f"No se encontraron archivos .wav en: {DIRECTORIO_PRUEBA}"
        print(f"❌ {msg}")
        errores.append(msg)
        return

    for file_path in archivos:
        print(f"\n  Procesando: {os.path.basename(file_path)}")
        try:
            df = sc.process_file_vocal(
                file_path,
                vocales=VOCALES,
                genero=GENERO,
                pitch_mode=PITCH_MODE,
                formant_mode=FORMANT_MODE,
            )
            print(f"  ✅ OK — {len(df)} intervalos encontrados")
            print(df.head().to_string())
        except Exception as e:
            msg = f"process_file_vocal falló en {os.path.basename(file_path)}: {e}"
            print(f"  ❌ {msg}")
            errores.append(msg)


def test_process_sample_separado():
    """Prueba el flujo completo — mismo camino que views.py."""
    print("\n=== TEST: process_sample_separado (flujo completo) ===")
    try:
        sc.process_sample_separado(
            DIRECTORIO_PRUEBA,
            vocales=VOCALES,
            genero=GENERO,
            pitch_mode=PITCH_MODE,
            formant_mode=FORMANT_MODE,
            intensity_mode=INTENSITY_MODE,
            center_b=CENTER_B,
            sd_b=SD_B,
            sk_b=SK_B,
            kur_b=KUR_B,
        )
        for nombre_csv in ["General_Vocal.csv", "General_S.csv"]:
            ruta = os.path.join(DIRECTORIO_PRUEBA, nombre_csv)
            if os.path.exists(ruta):
                print(f"  ✅ {nombre_csv} generado")
            else:
                msg = f"{nombre_csv} no se generó"
                print(f"  ❌ {msg}")
                errores.append(msg)
    except Exception as e:
        msg = f"process_sample_separado falló: {e}"
        print(f"  ❌ {msg}")
        errores.append(msg)


if __name__ == "__main__":
    print(f"Directorio de prueba : {DIRECTORIO_PRUEBA}")
    print(f"Intensity mode       : {INTENSITY_MODE}")

    test_process_file_s()
    test_process_file_vocal()
    test_process_sample_separado()

    print("\n" + "=" * 50)
    if errores:
        print(f"RESULTADO: {len(errores)} error(es) encontrado(s):")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)   # exit code 1 → GitHub Actions marca el job como fallido
    else:
        print("RESULTADO: todos los tests pasaron ✅")
        sys.exit(0)
