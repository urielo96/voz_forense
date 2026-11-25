"""
MVKD (multivariate kernel density) para comparacion forense de locutores.
Traduccion a Python del codigo en R de multifeature_MVLR_cal_X-val_4_Fernanda_v3.r
y two-level-MVRA-functions.r (Aitken & Lucy 2004, Morrison 2011).

Archivos que se necesitan en la carpeta CARPETA para correrlo tal como esta:

    er_mid_target_F-patt_vals_no_Alison_Maxine.txt   poblacion de referencia, formantes
    Sally_er_8_lpccs_to_5k_no_Alison_Maxine.txt      poblacion de referencia, lpccs
    Maxine_er_mid_F123.txt                           locutor Q (Maxine), formantes
    Maxine_er_8_lpccs_to_5k.txt                      locutor Q (Maxine), lpccs
    Alison_er_mid_F123.txt                           locutor K (Alison), formantes
    Alison_er_8_lpccs_to_5k.txt                      locutor K (Alison), lpccs

Los archivos de los locutores Q y K se buscan como <locutor>_<segmento>.txt,
igual que en el codigo original. Si se cambia K_SPK a otro locutor, hacen
falta sus archivos con ese mismo formato. Si Q_SPK y K_SPK son el mismo
locutor se comparan sus grabaciones 1 y 2, y solo se leen sus archivos.

Uso:  python mvkd.py

Requiere numpy, pandas y matplotlib.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------- parametros

CARPETA = r"C:\Users\super\Downloads\MVLR_v3_lista-20261014T145129Z-1-001\MVLR_v3_lista" #Cambiar segun la ubicacion de los archivos

Q_SPK = "Dubitada"
K_SPK = "Indubitada"
PARTICION = "R1.R2"       # R1.R1, R1.R2, R2.R2 o R2.R1 para las comparaciones DS
PRIOR = 0.5

SEGMENTOS = ["er_mid_F123"]

# locutores con una sola grabacion, se quedan en la poblacion de referencia
# pero no se usan como locutores de prueba
UN_SOLO_REC = ["Anna", "Clea", "Dom", "Anon", "Nat"]

ARCHIVO_POBLACION = {
    "er_mid_F123": "er_mid_target_F-patt_vals_no_Alison_Maxine.txt",
    "er_8_lpccs_to_5k": "Sally_er_8_lpccs_to_5k_no_Alison_Maxine.txt",
}

VARIABLES = {
    "er_mid_F123": ["mid.target.F1", "mid.target.F2", "mid.target.F3"],
    "er_8_lpccs_to_5k": ["CC.2", "CC.3", "CC.4", "CC.5", "CC.6", "CC.7", "CC.8"],
}

NOMBRE_FIGURA = "tippett_demo_e.png"


# ------------------------------------------------------------------- lectura

def leer_tabla(nombre):
    """Equivalente a read.table(header=TRUE, na.strings='na')."""
    ruta = os.path.join(CARPETA, nombre)
    tabla = pd.read_csv(ruta, sep=r"\s+", na_values="na")
    # en un archivo la sesion viene como 1 y 2 y en otro como texto ('ref'),
    # se pasa todo a texto para poder comparar igual en los dos casos
    tabla["sess"] = tabla["sess"].astype(str)
    return tabla


# ------------------------------------------- componentes de varianza U y C

def componentes_varianza(poblacion, variables, col_grupo="spk"):
    """Varianza dentro (U) y entre (C) locutores, mas las medias por locutor.

    Es la funcion within.between.var.covar del codigo en R. Acepta un numero
    distinto de tokens por locutor, en ese caso usa el promedio de tokens.
    """
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

    # criterio de Cox & Solomon para decidir si hace falta la version ponderada
    rho = np.sqrt(np.trace(U / n_por_grupo) / np.trace(C + U / n_por_grupo))
    if rho > 0.5:
        raise ValueError("rho mayor a 0.5, harian falta estimadores ponderados")

    return {"U": U, "C": C, "medias_grupo": medias_grupo,
            "media_global": media_global, "grupos": grupos, "rho": rho}


# --------------------------------------------------------------- modelo MVKD

def h_optima(m, p):
    """Ancho de ventana del kernel a partir de m grupos y p variables."""
    return ((4.0 / (2 * p + 1)) ** (1.0 / (p + 4))) * (m ** (-1.0 / (p + 4)))


def medias_muestras(control, recuperado, variables):
    """Medias y numero de tokens de las dos muestras que se comparan."""
    c = control[variables].to_numpy(dtype=float)
    r = recuperado[variables].to_numpy(dtype=float)
    return {"media_control": c.mean(axis=0), "media_recuperado": r.mean(axis=0),
            "Nc": c.shape[0], "Nr": r.shape[0]}


def determinante(M):
    # el codigo en R usa prod(eigen(M)$values) en lugar de det(M) porque
    # algunas matrices se acercan a ser singulares
    return float(np.prod(np.real(np.linalg.eigvals(M))))


def forma_cuadratica(diferencias, M):
    return np.einsum("ij,jk,ik->i", diferencias, M, diferencias)


def lr_mvkd(media_control, media_recuperado, Nc, Nr, U, C, medias_grupo, h):
    """Razon de verosimilitudes con densidad kernel entre locutores.

    Es two.level.multivariate.density.LR del codigo en R.
    """
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
    inv_A = U / (Nc + Nr)          # forma corta de invertir A
    y_estrella = inv_A @ (inv_D1 @ y1 + inv_D2 @ y2)

    inv_h2_C = np.linalg.inv((h ** 2) * C)
    dif = y1 - y2

    arriba1 = np.sqrt(determinante(C))
    arriba2 = m * (h ** p)
    arriba3 = 1.0 / np.sqrt(determinante(A + inv_h2_C))
    arriba4 = float(np.exp(-0.5 * (dif.T @ np.linalg.inv(D1 + D2) @ dif)).item())

    K = np.linalg.inv(inv_A + (h ** 2) * C)
    arriba5 = np.sum(np.exp(-0.5 * forma_cuadratica(y_estrella.ravel() - medias_grupo, K)))

    numerador = arriba1 * arriba2 * arriba3 * arriba4 * arriba5

    abajo1 = 1.0 / np.sqrt(determinante(inv_D1 + inv_h2_C))
    K1 = np.linalg.inv(D1 + (h ** 2) * C)
    abajo2 = np.sum(np.exp(-0.5 * forma_cuadratica(y1.ravel() - medias_grupo, K1)))

    abajo3 = 1.0 / np.sqrt(determinante(inv_D2 + inv_h2_C))
    K2 = np.linalg.inv(D2 + (h ** 2) * C)
    abajo4 = np.sum(np.exp(-0.5 * forma_cuadratica(y2.ravel() - medias_grupo, K2)))

    denominador = abajo1 * abajo2 * abajo3 * abajo4

    return numerador / denominador


# ----------------------------------------------------- fusion y calibracion

def direccion_conjugada(u, g, g_vieja):
    delta = g - g_vieja
    den = float((u.T @ delta).item())
    if den == 0:
        return g * 0.0
    beta = float(((g.T @ delta) / den).item())
    return g - beta * u


def pesos_fusion(scores_ss, scores_ds, prior=0.5, max_iter=1000, verbose=True):
    """Regresion logistica con gradiente conjugado, como train_llr_fusion de Focal.

    Entran los scores en log10 (una columna por sistema) y salen d+1 pesos:
    los primeros d multiplican a los scores en logaritmo natural y el ultimo
    es la ordenada al origen.
    """
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
        u = g if iteracion == 1 else direccion_conjugada(u, g, g_vieja)

        ug = float((u.T @ g).item())
        ux = u.T @ x
        a = pesos * s1 * (1 - s1)
        uhu = float(((ux ** 2) @ a.T).item())

        w = w + (ug / uhu) * u
        g_vieja = g

        if np.max(np.abs(w - w_vieja)) < 1e-5:
            if verbose:
                print("   la fusion convergio en", iteracion, "iteraciones")
            break
    else:
        print("aviso: se acabaron las iteraciones sin converger")

    return w


def aplica_fusion(w, scores):
    """Aplica los pesos a los scores en log10 y regresa los LR calibrados en log10."""
    s = np.log(10.0 ** np.atleast_2d(scores))
    X = np.vstack([s.T, np.ones((1, s.shape[0]))])
    return (w.T @ X).ravel() / np.log(10)


# --------------------------------------------------------------- evaluacion

def cllr(ss_log10, ds_log10):
    ss = 10.0 ** np.asarray(ss_log10, dtype=float)
    ds = 10.0 ** np.asarray(ds_log10, dtype=float)
    return (np.mean(np.log2(1 + 1 / ss)) + np.mean(np.log2(1 + ds))) / 2


def tasas_de_error(ss_log10, ds_log10):
    """Porcentaje de LR contrarios a la verdad conocida."""
    error_ss = np.mean(np.asarray(ss_log10) < 0) * 100
    error_ds = np.mean(np.asarray(ds_log10) >= 0) * 100
    return error_ss, error_ds


def grafica_tippett(ss_log10, ds_log10, titulo, lr_kq=None, info=None,
                    archivo=None):
    ss = np.sort(np.asarray(ss_log10, dtype=float))
    ds = np.sort(np.asarray(ds_log10, dtype=float))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(ss, np.linspace(0, 1, len(ss)), color="red", lw=2.5,
            label="LR log10 mismo locutor")
    ax.plot(ds, np.linspace(1, 0, len(ds)), color="blue", lw=2.5, ls="dotted",
            label="LR log10 distinto locutor")

    ax.axvline(0, color="black", lw=1)
    ax.grid(color="grey", ls="dotted", lw=0.6)
    ax.set_xlim(-11, 5)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Log10 LR mayor que ...")
    ax.set_ylabel("proporcion acumulada")
    ax.set_title(titulo, fontsize=11)
    ax.legend(loc="lower left")

    ax.text(-4, 0.92, "Cllr = %.2f" % cllr(ss, ds), fontsize=14)
    if info:
        ax.text(-10.5, 0.45, info, fontsize=9, va="top")
    if lr_kq is not None:
        ax.text(-10.5, 0.78, "log10 LR de la comparacion Q-K = %.1f" % lr_kq,
                fontsize=10)
        ax.plot([lr_kq], [0], marker="o", color="red", markersize=10)

    fig.tight_layout()
    if archivo:
        fig.savefig(archivo, dpi=150)
        print("figura guardada en", archivo)
    plt.show()


# ------------------------------------------------------------- procesamiento

def scores_validacion_cruzada(segmento, verbose=True):
    """Scores MVKD de todos los pares de locutores de prueba, con validacion
    cruzada dejando fuera de la poblacion a los dos locutores comparados."""
    variables = VARIABLES[segmento]
    poblacion = leer_tabla(ARCHIVO_POBLACION[segmento])

    datos_prueba = poblacion[~poblacion["spk"].isin(UN_SOLO_REC)]
    poblacion_sin_na = poblacion.dropna()

    locutores = list(pd.unique(datos_prueba["spk"]))
    n = len(locutores)

    sesion_sus, sesion_off = PARTICION.split(".")
    sesion_sus = sesion_sus[1]
    sesion_off = sesion_off[1]

    scores = []
    pares = []
    ultimo = None

    for i in range(n):
        for j in range(i, n):
            if i == j:
                # las comparaciones de mismo locutor siempre son grabacion 1 vs 2
                sus = datos_prueba[(datos_prueba.spk == locutores[i]) &
                                   (datos_prueba.sess == "1")]
                off = datos_prueba[(datos_prueba.spk == locutores[j]) &
                                   (datos_prueba.sess == "2")]
                fuera = [locutores[i]]
            else:
                sus = datos_prueba[(datos_prueba.spk == locutores[i]) &
                                   (datos_prueba.sess == sesion_sus)]
                off = datos_prueba[(datos_prueba.spk == locutores[j]) &
                                   (datos_prueba.sess == sesion_off)]
                fuera = [locutores[i], locutores[j]]

            referencia = poblacion_sin_na[~poblacion_sin_na.spk.isin(fuera)]
            uc = componentes_varianza(referencia, variables)
            h = h_optima(uc["medias_grupo"].shape[0], len(variables))

            z = medias_muestras(off, sus, variables)
            lr = lr_mvkd(z["media_control"], z["media_recuperado"], z["Nc"], z["Nr"],
                         uc["U"], uc["C"], uc["medias_grupo"], h)

            scores.append(lr)
            pares.append((locutores[i], locutores[j]))
            ultimo = uc

            if verbose and len(scores) <= 5:
                print("   %-10s vs %-10s  log10 score = %6.2f" %
                      (locutores[i], locutores[j], np.log10(lr)))

    scores = np.log10(np.array(scores))
    es_ss = np.array([a == b for a, b in pares])

    return {"scores": scores, "pares": pares, "es_ss": es_ss,
            "uc": ultimo, "n_locutores": n,
            "n_referencia": poblacion["spk"].nunique()}


def score_q_k(segmento, uc):
    """Score MVKD de la comparacion entre el locutor cuestionado y el conocido."""
    variables = VARIABLES[segmento]

    datos_q = leer_tabla("%s_%s.txt" % (Q_SPK, segmento))
    datos_k = leer_tabla("%s_%s.txt" % (K_SPK, segmento))

    if Q_SPK == K_SPK:
        sus = datos_k[datos_k.sess == "1"]
        off = datos_k[datos_k.sess == "2"]
    else:
        sesion_sus, sesion_off = PARTICION.split(".")
        sus = datos_k[datos_k.sess == sesion_sus[1]]
        off = datos_q[datos_q.sess == sesion_off[1]]

    h = h_optima(uc["medias_grupo"].shape[0], len(variables))
    z = medias_muestras(off, sus, variables)

    return lr_mvkd(z["media_control"], z["media_recuperado"], z["Nc"], z["Nr"],
                   uc["U"], uc["C"], uc["medias_grupo"], h)


def main():
    print("Comparacion Q =", Q_SPK, " K =", K_SPK, " particion", PARTICION)

    columnas_ss = []
    columnas_ds = []
    scores_kq = []
    pares_ss = None
    pares_ds = None
    resumen = None

    for segmento in SEGMENTOS:
        print("\nsegmento:", segmento, "  variables:", ", ".join(VARIABLES[segmento]))
        r = scores_validacion_cruzada(segmento)

        ss = r["scores"][r["es_ss"]]
        ds = r["scores"][~r["es_ss"]]
        columnas_ss.append(ss)
        columnas_ds.append(ds)

        # igual que en R, los nombres de los pares salen del ultimo segmento
        pares = np.array(r["pares"])
        pares_ss = pares[r["es_ss"]]
        pares_ds = pares[~r["es_ss"]]
        resumen = r

        print("   %d comparaciones SS y %d comparaciones DS" % (len(ss), len(ds)))
        print("   Cllr sin calibrar = %.2f" % cllr(ss, ds))

        # el codigo en R reutiliza aqui la U y la C de la ultima iteracion del
        # ciclo, o sea la poblacion sin el ultimo par de locutores de prueba
        scores_kq.append(score_q_k(segmento, r["uc"]))
        print("   log10 score Q-K (sin calibrar) = %.2f" % np.log10(scores_kq[-1]))

    ss = np.column_stack(columnas_ss)
    ds = np.column_stack(columnas_ds)

    # se quitan los scores que salieron NaN, si es que hubo
    buenos_ss = ~np.isnan(ss).any(axis=1)
    buenos_ds = ~np.isnan(ds).any(axis=1)
    ss, pares_ss = ss[buenos_ss], pares_ss[buenos_ss]
    ds, pares_ds = ds[buenos_ds], pares_ds[buenos_ds]

    print("\nfusion y calibracion de los scores")
    w = pesos_fusion(ss, ds, PRIOR)
    pesos = w.ravel()
    for segmento, peso in zip(SEGMENTOS, pesos):
        print("   peso %-18s = %.4f" % (segmento, peso))
    print("   ordenada                   = %.4f" % pesos[-1])

    cal_ss = aplica_fusion(w, ss)
    cal_ds = aplica_fusion(w, ds)

    lr_kq = float(aplica_fusion(w, np.log10(np.array(scores_kq)).reshape(1, -1))[0])

    error_ss, error_ds = tasas_de_error(cal_ss, cal_ds)

    print("\n\nResultados finales:")
    print("=" * 52)
    print("Comparacion Q =", Q_SPK, " K =", K_SPK, " particion", PARTICION)
    print("\nCllr calibrado          = %.2f" % cllr(cal_ss, cal_ds))
    print("errores SS              = %.1f %%" % error_ss)
    print("errores DS              = %.1f %%" % error_ds)
    print("locutores de prueba     =", resumen["n_locutores"])
    print("locutores de referencia =", resumen["n_referencia"])
    print("\npeor LR de mismo locutor    : %s %.2f" %
          (pares_ss[np.argmin(cal_ss)][0], cal_ss.min()))
    print("mejor LR de mismo locutor   : %s %.2f" %
          (pares_ss[np.argmax(cal_ss)][0], cal_ss.max()))
    print("peor LR de distinto locutor : %s %.2f" %
          (" y ".join(pares_ds[np.argmax(cal_ds)]), cal_ds.max()))
    print("mejor LR de distinto locutor: %s %.2f" %
          (" y ".join(pares_ds[np.argmin(cal_ds)]), cal_ds.min()))
    print("\nlog10 LR de la comparacion entre %s y %s = %.2f" % (Q_SPK, K_SPK, lr_kq))
    print("o sea un LR de %.4g" % (10 ** lr_kq))
    print("=" * 52)

    info = ("errores SS = %.1f %%\nerrores DS = %.1f %%\n"
            "locutores de prueba = %d\nlocutores de referencia = %d" %
            (error_ss, error_ds, resumen["n_locutores"], resumen["n_referencia"]))

    titulo = "MVKD calibrado con validacion cruzada, " + " + ".join(SEGMENTOS)
    grafica_tippett(cal_ss, cal_ds, titulo, lr_kq=lr_kq, info=info,
                    archivo=NOMBRE_FIGURA)


if __name__ == "__main__":
    main()
