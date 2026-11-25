"""
Comparación MVKD (multivariate kernel density) entre voz dubitada e indubitada.

DEMOSTRACIÓN TÉCNICA. Es el cálculo de mvkd_demo.py (Julio, nov-2026), traducción
del código en R multifeature_MVLR_cal_X-val_4_Fernanda_v3.r (Aitken & Lucy 2004;
Morrison 2011), adaptado para correr dentro de la plataforma:

- lee las mediciones de General_Vocal.csv (lo que hacía convertir_forvoz.py),
- no usa rutas fijas ni abre ventanas: la gráfica de Tippett se regresa como PNG,
- la validación cruzada no depende de Q ni de K, así que se calcula una vez y se guarda.

La población de referencia es la vocal inglesa "er" (24 locutoras), por lo que el
resultado NO tiene interpretación forense con audios en español.
"""

import base64
import io
import os
from functools import lru_cache

import numpy as np
import pandas as pd
from django.conf import settings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


CARPETA_DATOS = os.path.join(settings.BASE_DIR, "extraccion", "mvkd_data")
ARCHIVO_POBLACION = "er_mid_target_F-patt_vals_no_Alison_Maxine.txt"
VARIABLES = ["mid.target.F1", "mid.target.F2", "mid.target.F3"]
SEGMENTO = "er_mid_F123"
PARTICION = "R1.R2"
PRIOR = 0.5
# locutores con una sola grabación: se quedan en la población pero no son de prueba
UN_SOLO_REC = ["Anna", "Clea", "Dom", "Anon", "Nat"]
MIN_TOKENS = 2


class PoblacionNoDisponible(Exception):
    pass


def ruta_poblacion():
    return os.path.join(CARPETA_DATOS, ARCHIVO_POBLACION)


def poblacion_disponible():
    return os.path.exists(ruta_poblacion())


# ------------------------------------------------------- datos de ForVoz (Q y K)

def _columnas_formantes(df):
    """Columnas F1, F2 y F3 de General_Vocal.csv (p. ej. 'F1 (Media)')."""
    cols = []
    for f in ("F1", "F2", "F3"):
        col = next((c for c in df.columns if c.startswith(f + " (")), None)
        if col is None:
            return None
        cols.append(col)
    return cols


def leer_general_vocal(ruta_csv):
    """Regresa (DataFrame, columnas F1-F3) o (None, None) si faltan formantes."""
    df = pd.read_csv(ruta_csv)
    cols = _columnas_formantes(df)
    if cols is None:
        return None, None
    df = df.dropna(subset=cols)
    df["Etiqueta"] = df["Etiqueta"].astype(str).str.strip()
    return df, cols


def vocales_comparables(df):
    """Vocales con al menos MIN_TOKENS en las dos voces, con su conteo."""
    resultado = []
    for vocal in sorted(df["Etiqueta"].unique()):
        d = df[df["Etiqueta"] == vocal]
        n_k = int((d["Nombre"] == "voz_indubitada").sum())
        n_q = int((d["Nombre"] == "voz_dubitada").sum())
        resultado.append({"vocal": vocal, "n_k": n_k, "n_q": n_q,
                          "ok": n_k >= MIN_TOKENS and n_q >= MIN_TOKENS})
    return resultado


def _tokens(df, cols, vocal, nombre):
    """Igual que convertir_forvoz.py: formantes redondeados a enteros."""
    t = df[(df["Etiqueta"] == vocal) & (df["Nombre"] == nombre)]
    return t[cols].round(0).astype(int).to_numpy(dtype=float)


# ------------------------------------------- componentes de varianza U y C

def componentes_varianza(poblacion, variables, col_grupo="spk"):
    grupos = list(pd.unique(poblacion[col_grupo]))
    m = len(grupos)
    p = len(variables)

    X = poblacion[variables].to_numpy(dtype=float)
    etiquetas = poblacion[col_grupo].to_numpy()

    tokens = np.array([np.sum(etiquetas == g) for g in grupos], dtype=float)
    if np.any(tokens < 2):
        raise ValueError("hay locutores sin repeticiones")
    n_por_grupo = tokens[0] if len(np.unique(tokens)) == 1 else tokens.mean()

    media_global = X.mean(axis=0)
    medias_grupo = np.zeros((m, p))
    S_dentro = np.zeros((p, p))
    S_entre = np.zeros((p, p))

    for i, g in enumerate(grupos):
        filas = X[etiquetas == g]
        media = filas.mean(axis=0)
        medias_grupo[i] = media
        d = filas - media
        S_dentro += d.T @ d
        d = (media - media_global).reshape(-1, 1)
        S_entre += d @ d.T

    MS_dentro = S_dentro / (tokens.sum() - m)
    MS_entre = (n_por_grupo * S_entre) / (m - 1)

    U = MS_dentro
    C = (MS_entre - MS_dentro) / n_por_grupo

    rho = np.sqrt(np.trace(U / n_por_grupo) / np.trace(C + U / n_por_grupo))
    if rho > 0.5:
        raise ValueError("rho mayor a 0.5, harían falta estimadores ponderados")

    return {"U": U, "C": C, "medias_grupo": medias_grupo}


# --------------------------------------------------------------- modelo MVKD

def h_optima(m, p):
    return ((4.0 / (2 * p + 1)) ** (1.0 / (p + 4))) * (m ** (-1.0 / (p + 4)))


def _determinante(M):
    # como en R: prod(eigen(M)$values), porque algunas matrices son casi singulares
    return float(np.prod(np.real(np.linalg.eigvals(M))))


def _forma_cuadratica(diferencias, M):
    return np.einsum("ij,jk,ik->i", diferencias, M, diferencias)


def lr_mvkd(media_control, media_recuperado, Nc, Nr, U, C, medias_grupo, h):
    p = len(media_control)
    m = medias_grupo.shape[0]

    y1 = np.asarray(media_control, dtype=float).reshape(-1, 1)
    y2 = np.asarray(media_recuperado, dtype=float).reshape(-1, 1)

    D1 = U / Nc
    D2 = U / Nr
    U_inv = np.linalg.inv(U)
    inv_D1 = U_inv * Nc
    inv_D2 = U_inv * Nr

    A = inv_D1 + inv_D2
    inv_A = U / (Nc + Nr)
    y_estrella = inv_A @ (inv_D1 @ y1 + inv_D2 @ y2)

    inv_h2_C = np.linalg.inv((h ** 2) * C)
    dif = y1 - y2

    arriba1 = np.sqrt(_determinante(C))
    arriba2 = m * (h ** p)
    arriba3 = 1.0 / np.sqrt(_determinante(A + inv_h2_C))
    arriba4 = float(np.exp(-0.5 * (dif.T @ np.linalg.inv(D1 + D2) @ dif)).item())
    K = np.linalg.inv(inv_A + (h ** 2) * C)
    arriba5 = np.sum(np.exp(-0.5 * _forma_cuadratica(y_estrella.ravel() - medias_grupo, K)))
    numerador = arriba1 * arriba2 * arriba3 * arriba4 * arriba5

    abajo1 = 1.0 / np.sqrt(_determinante(inv_D1 + inv_h2_C))
    K1 = np.linalg.inv(D1 + (h ** 2) * C)
    abajo2 = np.sum(np.exp(-0.5 * _forma_cuadratica(y1.ravel() - medias_grupo, K1)))
    abajo3 = 1.0 / np.sqrt(_determinante(inv_D2 + inv_h2_C))
    K2 = np.linalg.inv(D2 + (h ** 2) * C)
    abajo4 = np.sum(np.exp(-0.5 * _forma_cuadratica(y2.ravel() - medias_grupo, K2)))
    denominador = abajo1 * abajo2 * abajo3 * abajo4

    return numerador / denominador


# ----------------------------------------------------- fusión y calibración

def _direccion_conjugada(u, g, g_vieja):
    delta = g - g_vieja
    den = float((u.T @ delta).item())
    if den == 0:
        return g * 0.0
    beta = float(((g.T @ delta) / den).item())
    return g - beta * u


def pesos_fusion(scores_ss, scores_ds, prior=0.5, max_iter=1000):
    objetivo = np.log(10.0 ** np.atleast_2d(scores_ss)).T
    no_objetivo = np.log(10.0 ** np.atleast_2d(scores_ds)).T

    d, nt = objetivo.shape
    nn = no_objetivo.shape[1]
    prop = nt / (nn + nt)

    pesos = np.concatenate([(prior / prop) * np.ones(nt),
                            ((1 - prior) / (1 - prop)) * np.ones(nn)]).reshape(1, -1)
    x = np.hstack([np.vstack([objetivo, np.ones((1, nt))]),
                   -np.vstack([no_objetivo, np.ones((1, nn))])])
    offset = (np.log(prior / (1 - prior)) *
              np.concatenate([np.ones(nt), -np.ones(nn)])).reshape(1, -1)

    w = np.zeros((d + 1, 1))
    g_vieja = np.zeros_like(w)
    u = None
    for iteracion in range(1, max_iter + 1):
        w_vieja = w.copy()
        s1 = 1.0 / (1.0 + np.exp(w.T @ x + offset))
        g = x @ (s1 * pesos).T
        u = g if iteracion == 1 else _direccion_conjugada(u, g, g_vieja)
        ug = float((u.T @ g).item())
        ux = u.T @ x
        a = pesos * s1 * (1 - s1)
        uhu = float(((ux ** 2) @ a.T).item())
        w = w + (ug / uhu) * u
        g_vieja = g
        if np.max(np.abs(w - w_vieja)) < 1e-5:
            break
    return w


def aplica_fusion(w, scores):
    s = np.log(10.0 ** np.atleast_2d(scores))
    X = np.vstack([s.T, np.ones((1, s.shape[0]))])
    return (w.T @ X).ravel() / np.log(10)


def cllr(ss_log10, ds_log10):
    ss = 10.0 ** np.asarray(ss_log10, dtype=float)
    ds = 10.0 ** np.asarray(ds_log10, dtype=float)
    return (np.mean(np.log2(1 + 1 / ss)) + np.mean(np.log2(1 + ds))) / 2


# ------------------------------------------- validación cruzada (una sola vez)

def _leer_poblacion():
    if not poblacion_disponible():
        raise PoblacionNoDisponible(ARCHIVO_POBLACION)
    tabla = pd.read_csv(ruta_poblacion(), sep=r"\s+", na_values="na")
    tabla["sess"] = tabla["sess"].astype(str)
    return tabla


@lru_cache(maxsize=1)
def validacion_cruzada():
    """Scores de todos los pares de locutores de prueba, calibración y la U/C
    que se usa para Q-K (la de la última iteración, igual que en el código en R)."""
    poblacion = _leer_poblacion()
    datos_prueba = poblacion[~poblacion["spk"].isin(UN_SOLO_REC)]
    poblacion_sin_na = poblacion.dropna()
    locutores = list(pd.unique(datos_prueba["spk"]))
    n = len(locutores)
    sesion_sus, sesion_off = (s[1] for s in PARTICION.split("."))

    scores, pares, ultimo = [], [], None
    for i in range(n):
        for j in range(i, n):
            if i == j:
                sus = datos_prueba[(datos_prueba.spk == locutores[i]) & (datos_prueba.sess == "1")]
                off = datos_prueba[(datos_prueba.spk == locutores[j]) & (datos_prueba.sess == "2")]
                fuera = [locutores[i]]
            else:
                sus = datos_prueba[(datos_prueba.spk == locutores[i]) & (datos_prueba.sess == sesion_sus)]
                off = datos_prueba[(datos_prueba.spk == locutores[j]) & (datos_prueba.sess == sesion_off)]
                fuera = [locutores[i], locutores[j]]

            referencia = poblacion_sin_na[~poblacion_sin_na.spk.isin(fuera)]
            uc = componentes_varianza(referencia, VARIABLES)
            h = h_optima(uc["medias_grupo"].shape[0], len(VARIABLES))
            c = off[VARIABLES].to_numpy(dtype=float)
            r = sus[VARIABLES].to_numpy(dtype=float)
            scores.append(lr_mvkd(c.mean(axis=0), r.mean(axis=0), c.shape[0], r.shape[0],
                                  uc["U"], uc["C"], uc["medias_grupo"], h))
            pares.append((locutores[i], locutores[j]))
            ultimo = uc

    scores = np.log10(np.array(scores))
    es_ss = np.array([a == b for a, b in pares])
    ss, ds = scores[es_ss], scores[~es_ss]
    ss, ds = ss[~np.isnan(ss)], ds[~np.isnan(ds)]

    w = pesos_fusion(ss.reshape(-1, 1), ds.reshape(-1, 1), PRIOR)
    cal_ss = aplica_fusion(w, ss.reshape(-1, 1))
    cal_ds = aplica_fusion(w, ds.reshape(-1, 1))

    return {
        "w": w, "uc": ultimo, "cal_ss": cal_ss, "cal_ds": cal_ds,
        "cllr_sin_calibrar": float(cllr(ss, ds)),
        "cllr": float(cllr(cal_ss, cal_ds)),
        "error_ss": float(np.mean(cal_ss < 0) * 100),
        "error_ds": float(np.mean(cal_ds >= 0) * 100),
        "n_prueba": n,
        "n_referencia": int(poblacion["spk"].nunique()),
        "n_ss": int(len(ss)), "n_ds": int(len(ds)),
    }


# ---------------------------------------------------------------- Q contra K

def _tippett_png(cal_ss, cal_ds, lr_kq, info):
    ss = np.sort(cal_ss)
    ds = np.sort(cal_ds)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(ss, np.linspace(0, 1, len(ss)), color="red", lw=2.5, label="LR log10 mismo locutor")
    ax.plot(ds, np.linspace(1, 0, len(ds)), color="blue", lw=2.5, ls="dotted",
            label="LR log10 distinto locutor")
    ax.axvline(0, color="black", lw=1)
    ax.grid(color="grey", ls="dotted", lw=0.6)
    ax.set_xlim(-11, 5)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Log10 LR mayor que ...")
    ax.set_ylabel("Proporción acumulada")
    ax.set_title("MVKD calibrado con validación cruzada (DEMOSTRACIÓN TÉCNICA)", fontsize=11)
    ax.legend(loc="lower left")
    ax.text(-4, 0.92, "Cllr = %.2f" % cllr(ss, ds), fontsize=14)
    ax.text(-10.5, 0.45, info, fontsize=9, va="top")
    x = float(np.clip(lr_kq, -11, 5))
    ax.text(-10.5, 0.78, "log10 LR de la comparación Q-K = %.2f" % lr_kq, fontsize=10)
    ax.plot([x], [0], marker="o", color="red", markersize=10, clip_on=False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _formato_lr(lr):
    """LR legible: 39.95, 4.18e+04 → 41,800, 1.3e+10 → 1.3 × 10^10."""
    if lr >= 1e6 or lr < 1e-3:
        e = int(np.floor(np.log10(lr)))
        return "%.2g × 10^%d" % (lr / 10 ** e, e)
    return "{:,.4g}".format(lr) if lr < 1000 else "{:,.0f}".format(float("%.3g" % lr))


def comparar(df, cols, vocal):
    """Comparación Q (dubitada, sesión 2) contra K (indubitada, sesión 1) en una vocal."""
    vc = validacion_cruzada()
    uc = vc["uc"]

    k = _tokens(df, cols, vocal, "voz_indubitada")  # 'sus' en el código original
    q = _tokens(df, cols, vocal, "voz_dubitada")    # 'off' en el código original
    if len(k) < MIN_TOKENS or len(q) < MIN_TOKENS:
        raise ValueError("Se necesitan al menos %d tokens de /%s/ en cada voz." % (MIN_TOKENS, vocal))

    h = h_optima(uc["medias_grupo"].shape[0], len(VARIABLES))
    score = lr_mvkd(q.mean(axis=0), k.mean(axis=0), q.shape[0], k.shape[0],
                    uc["U"], uc["C"], uc["medias_grupo"], h)
    score_log10 = float(np.log10(score))
    lr_log10 = float(aplica_fusion(vc["w"], np.array([[score_log10]]))[0])

    info = ("errores SS = %.1f %%\nerrores DS = %.1f %%\n"
            "locutores de prueba = %d\nlocutores de referencia = %d" %
            (vc["error_ss"], vc["error_ds"], vc["n_prueba"], vc["n_referencia"]))

    return {
        "vocal": vocal,
        "n_k": int(len(k)), "n_q": int(len(q)),
        "media_k": [round(v) for v in k.mean(axis=0)],
        "media_q": [round(v) for v in q.mean(axis=0)],
        "score_log10": score_log10,
        "lr_log10": lr_log10,
        "lr": 10 ** lr_log10,
        "lr_texto": _formato_lr(10 ** lr_log10),
        "peso": float(vc["w"].ravel()[0]),
        "ordenada": float(vc["w"].ravel()[-1]),
        "validacion": vc,
        "tippett_png": _tippett_png(vc["cal_ss"], vc["cal_ds"], lr_log10, info),
    }
