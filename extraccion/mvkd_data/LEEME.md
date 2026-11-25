# Datos del modelo MVKD (demostración técnica)

- `original_julio/`: scripts originales de Julio (10-nov-2026), traducción a Python del código en R
  `multifeature_MVLR_cal_X-val_4_Fernanda_v3.r` (Aitken & Lucy 2004, Morrison 2011).
- La plataforma usa `extraccion/mvkd.py`, que es el mismo cálculo adaptado para correr dentro de Django.
- **Falta** la población de referencia: `er_mid_target_F-patt_vals_no_Alison_Maxine.txt`
  (vocal inglesa "er", 24 locutoras). Va en esta carpeta. Sin ella el paso 4 muestra un aviso.

No interpretar forensemente: la población es del inglés y los audios de ForVoz son vocales del español.
