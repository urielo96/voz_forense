"""Convierte General_Vocal.csv (ForVoz, formantes en el punto medio) al formato de mvkd.py:
<locutor>_er_mid_F123.txt con columnas spk seg sess tok onset mid.target.F1..F3.
Uso: python convertir_forvoz.py General_Vocal.csv carpeta_salida VOCAL
  indubitada -> Indubitada, sesion 1 (K);  dubitada -> Dubitada, sesion 2 (Q)"""
import sys, pandas as pd
csv, salida, vocal = sys.argv[1:4]
d = pd.read_csv(csv)
d = d[d["Etiqueta"] == vocal]
cols = [c for c in ("F1", "F2", "F3")]
cols = [next(k for k in d.columns if k.startswith(c + " (")) for c in cols]
d = d.dropna(subset=cols)
for nombre, spk, sess in (("voz_indubitada", "Indubitada", 1), ("voz_dubitada", "Dubitada", 2)):
    t = d[d["Nombre"] == nombre].reset_index(drop=True)
    out = pd.DataFrame({"spk": spk, "seg": "er", "sess": sess,
                        "tok": ["%s_%s_%d" % (spk, vocal, i + 1) for i in range(len(t))],
                        "onset": 0,
                        "mid.target.F1": t[cols[0]].round(0).astype(int),
                        "mid.target.F2": t[cols[1]].round(0).astype(int),
                        "mid.target.F3": t[cols[2]].round(0).astype(int)})
    out.to_csv("%s/%s_er_mid_F123.txt" % (salida, spk), sep="\t", index=False)
    print(spk, "sesion", sess, "tokens", len(out))
