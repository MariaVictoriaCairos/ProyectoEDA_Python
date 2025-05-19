# ——————————————————————————————
# Importaciones de las librerías 
# ——————————————————————————————

import datetime       # Para normalizar y manipular fechas
import re             # Para normalización y validación de cadenas de fecha
import math           # Para operaciones matemáticas básicas (p.ej. funciones trigonométricas)

# ——————————————————————————————
# Importaciones para tipado
# ——————————————————————————————

from typing import Union, List  
# Union: para anotar parámetros o retornos que pueden tener varios tipos  
# List: para anotar listas con tipos de elemento específicos

# ——————————————————————————————
# Librerías de terceros: cálculo y análisis de datos
# ——————————————————————————————

import numpy as np    # Cálculo numérico y álgebra de matrices
import pandas as pd   # Manipulación y análisis de estructuras de datos tabulares

from scipy.stats import gaussian_kde  
# gaussian_kde: estimación de densidad kernel univariada/multivariada

# ——————————————————————————————
# Librería de visualización
# ——————————————————————————————

import matplotlib.pyplot as plt  
# plt: interfaz de Matplotlib para crear gráficos (líneas, histogramas, scatter, etc.)


# ----------------------------------------------------------------
# Constantes / Mapas
# ----------------------------------------------------------------
MONTH_MAP_ES: dict[str,str] = {
    'enero':      '01',
    'febrero':    '02',
    'marzo':      '03',
    'abril':      '04',
    'mayo':       '05',
    'junio':      '06',
    'julio':      '07',
    'agosto':     '08',
    'septiembre': '09',
    'octubre':    '10',
    'noviembre':  '11',
    'diciembre':  '12',
}

# ------------------------------------------------------
# Función para imputar valores nulos en columnas de un DataFrame por distribución de los datos
# --------------------------------------------------------
def imputar_nulos_por_distribucion(
    df: pd.DataFrame,
    columnas: Union[str, List[str]],
    skew_threshold: float = 0.5
) -> pd.DataFrame:
    """
    Imputa los valores nulos en una o varias columnas del DataFrame `df`
    según la simetría de su distribución:
      - Si |skewness| < skew_threshold: se imputa con la mediana.
      - En caso contrario: se imputa con la moda.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame de entrada (modificado in-place).
    columnas : str o list[str]
        Nombre de la columna, o lista de nombres de columnas, a imputar.
    skew_threshold : float, opcional
        Umbral de asimetría para elegir mediana vs. moda (por defecto 0.5).

    Devuelve
    -------
    pd.DataFrame
        El mismo DataFrame con las columnas imputadas.
    """
    # Si recibimos varias columnas, iteramos recursivamente
    if isinstance(columnas, (list, tuple)):
        for col in columnas:
            imputar_nulos_por_distribucion(df, col, skew_threshold)
        return df

    # A partir de aquí, 'columnas' es un único nombre de columna (string)
    col = columnas

    # Calculamos asimetría, media, mediana y moda
    skewness = df[col].skew()
    media    = df[col].mean()
    mediana  = df[col].median()
    modos    = df[col].mode()
    moda     = modos[0] if not modos.empty else None

    print(f"Asimetría (skewness) de '{col}': {skewness:.3f}")
    print(f"Media    de '{col}': {media:.3f}")
    print(f"Mediana  de '{col}': {mediana:.3f}")
    print(f"Moda     de '{col}': {moda}")

    # Elegimos criterio de imputación
    if abs(skewness) < skew_threshold:
        print(f"Distribución aproximadamente simétrica (|skew| < {skew_threshold}), imputando con mediana.")
        df[col] = df[col].fillna(mediana)
    else:
        print(f"Distribución asimétrica (|skew| ≥ {skew_threshold}), imputando con moda.")
        df[col] = df[col].fillna(moda)

    return df


# ------------------------------------------------------
# Función para verificar si hay columnas con valores NaN
# -------------------------------------------------------
def verificar_columnas_con_nan(
    df: pd.DataFrame,
    *listas_de_columnas: List[str]
) -> List[str]:
    """
    Verifica en el DataFrame `df` cuáles de las columnas dadas contienen valores NaN.
    Imprime un mensaje para cada columna y devuelve la lista de columnas con NaN.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame a verificar.
    *listas_de_columnas : List[str]
        Uno o más listados de nombres de columna a comprobar.

    Devuelve
    -------
    List[str]
        Lista de nombres de columna que tienen al menos un NaN.
    """
    columnas_con_nan: List[str] = []

    for lista in listas_de_columnas:
        for col in lista:
            if df[col].isnull().any():
                print(f"Columna '{col}' SI tiene valores NaN.")
                columnas_con_nan.append(col)
            else:
                print(f"Columna '{col}' NO tiene valores NaN.")

    return columnas_con_nan

# ------------------------------------------------------
# Covertir columnas date de object a datetime
# -------------------------------------------------------
def convertir_columnas_a_datetime(
    df: pd.DataFrame,
    columnas: Union[str, List[str]]
) -> pd.DataFrame:
    """
    Convierte columna(s) de object a datetime, genera contact_year y 
    contact_month a partir de la columna 'date', y no deja columnas 
    intermedias en el DataFrame.
    """
    if isinstance(columnas, (list, tuple)):
        for col in columnas:
            convertir_columnas_a_datetime(df, col)
        return df

    col = columnas  # nombre de la columna a procesar

    # Función interna de parseo
    def parse_val(x):
        norm = normalize_date(str(x))
        if norm is None:
            return pd.NaT
        return pd.to_datetime(norm, format='%d/%m/%Y', errors='coerce')

    # 1) Parsing directo de la columna
    df[col] = df[col].apply(parse_val)

    # 2) Extracción de año y mes en columnas nuevas
    df['contact_year'] = df[col].dt.year
    df['contact_month'] = df[col].dt.month

    return df
# ------------------------------------------------------
# Función para normalizar fechas
# -------------------------------------------------------
# Esta función toma una cadena de texto que representa una fecha en varios formatos
# y la normaliza a un formato estándar 'DD/MM/YYYY'. Si la cadena no es válida, devuelve None.
# La función maneja fechas en español y en inglés, así como diferentes separadores.

def normalize_date(s: str) -> Union[str, None]:
    """
    Toma '14-septiembre-2016' o '2/8/19' y devuelve 'DD/MM/YYYY',
    o None si no encaja.
    """
    if not s:
        return None
    s = s.strip().lower().replace('⁄','/').replace('–','-')
    # dd/mm/yy o dd/mm/yyyy
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', s)
    if m:
        d, mo, y = m.groups()
        y = '20' + y if len(y) == 2 else y
        return f"{int(d):02d}/{int(mo):02d}/{y}"
    # dd-MES-yy(yy) o dd MES yy(yy)
    m = re.match(r'^(\d{1,2})[- ]([a-zñ]+)[- ](\d{2,4})$', s)
    if m:
        d, mes_txt, y = m.groups()
        mm = MONTH_MAP_ES.get(mes_txt)
        if mm:
            y = '20' + y if len(y) == 2 else y
            return f"{int(d):02d}/{mm}/{y}"
    return None
    


# ------------------------------------------------------
# Estadistica personalizada para columnas numericas
# -------------------------------------------------------
def estadisticas_personalizadas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula para cada columna numérica del DataFrame:
      - mean  : media
      - median: mediana
      - std   : desviación estándar
      - min   : valor mínimo
      - 25%   : primer cuartil
      - 50%   : segundo cuartil (mediana)
      - 75%   : tercer cuartil
      - max   : valor máximo

    Devuelve un DataFrame con esas métricas como columnas
    y las variables originales como índice.
    
    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame de entrada.
    Devuelve
    -------
    pd.DataFrame
        DataFrame con las métricas calculadas.
    """
    # 1) Seleccionamos solo columnas numéricas
    num = df.select_dtypes(include='number')
    
    # 2) Calculamos todas las métricas
    stats = pd.DataFrame({
        'mean'  : num.mean(),
        'median': num.median(),
        'std'   : num.std(ddof=1),
        'min'   : num.min(),
        '25%'   : num.quantile(0.25),
        '50%'   : num.quantile(0.50),
        '75%'   : num.quantile(0.75),
        'max'   : num.max()
    })
    
    # 3) Reordenamos las columnas en el orden deseado,
    #    rellenando con NaN en caso de que alguna métrica falte
    desired_order = ['mean','median','std','min','25%','50%','75%','max']
    stats = stats.reindex(columns=desired_order)
    
    # 4) Redondeamos a 3 decimales
    stats = stats.round(3)
    
    # Identificación de las principales variables nnumericas que serán atributos principales para el conjunto de datos
    # Para identificar cuáles de las variables numéricas son “principales” (es decir, las que más aportan 
    # variabilidad y, por tanto, más información) nos apoyamos en dos medidas claves:
    #       -   Desviación estándar: cuanto mayor, más dispersión tiene la variable.
    #       -   Rango (max − min) o IQR (75 % − 25 %): dan idea de cuán separadas están sus observaciones.
        
    # 1) Creamos rango e IQR
    stats['range'] = stats['max'] - stats['min']
    stats['IQR']   = stats['75%'] - stats['25%']

    # 2) Top 5 por desviación estándar
    top_std   = stats['std'].sort_values(ascending=False).head(5)

    # 3) Top 5 por rango
    top_range = stats['range'].sort_values(ascending=False).head(5)

    print("→ Top 5 variables por DESVIACIÓN ESTÁNDAR:")
    print(top_std)

    print("\n→ Top 5 variables por RANGO:")
    print(top_range)
    
    return stats


# ------------------------------------------------------
# Visualización gráfica de atributos numéricos
# ------------------------------------------------------
# Esta función toma un DataFrame y una lista de nombres de columnas,
# y genera histogramas para cada columna, superponiendo una línea discontinua
# que indica la media de los datos. Los histogramas se organizan en una cuadrícula de 2 filas y 3 columnas.
# Se utiliza la biblioteca matplotlib para crear las visualizaciones.


def plot_hist_with_mean_and_kde(df, atributos, bins=30):
    """
    Grafica histogramas de las columnas de `atributos` de df,
    superpone una línea discontinua indicando la media,
    y dibuja la curva de densidad (KDE) en rojo.
    
    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame que contiene los datos a graficar.
    atributos : list[str]
        Lista de nombres de columnas a graficar.
    bins : int, opcional
        Número de bins para el histograma (por defecto 30).
    """
    # Creamos el grid (2 filas x 3 columnas)
    fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(12, 8))
    axes = axes.flatten()
    
    for ax, col in zip(axes, atributos):
        data = df[col].dropna()
        
        # Histograma normalizado
        ax.hist(data, bins=bins, density=True, alpha=0.6, edgecolor='black')
        
        # Línea vertical de la media
        mu = data.mean()
        ax.axvline(mu, linestyle='--', linewidth=2, label=f'Media: {mu:.3f}')
        
        # Curva de densidad (KDE)
        kde = gaussian_kde(data)
        x_vals = np.linspace(data.min(), data.max(), 200)
        ax.plot(x_vals, kde(x_vals), color='red', linewidth=2, label='KDE')
        
        ax.set_title(col)
        ax.set_ylabel('Densidad')
        ax.legend()
    
    # Apagamos subplots sobrantes
    for ax in axes[len(atributos):]:
        ax.axis('off')
    
    plt.tight_layout()
    plt.show()
    
    
# ------------------------------------------------------
# Función para identificar y eliminar outliers
# -------------------------------------------------------       

def listar_outliers_y_boxplot(df, atributos):
    """
    Para cada columna en `atributos`:
     - Detecta outliers con el método IQR (1.5*IQR)
     - Almacena los valores atípicos en un dict
     - Dibuja un boxplot horizontal
    Retorna:
      outliers_dict: {columna: Series de outliers}
      fig: objeto matplotlib.figure.Figure
    """
    outliers_dict = {}
    n = len(atributos)
    
    # Creamos la figura y los ejes
    cols = 4
    rows = (n + cols - 1) // cols  # Redondeo hacia arriba
    if rows == 0:
        rows = 1

    # Creamos un grid de rows x cols
    fig, axes = plt.subplots(rows, cols,
                             figsize=(4 * cols, 4 * rows),
                             squeeze=False)
    axes = axes.flatten()
    
    for ax, col in zip(axes, atributos):
        data = df[col].dropna()
        
        # Cálculo de cuartiles e IQR
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        
        # Máscara de outliers
        mask = (data < lower) | (data > upper)
        outliers = data[mask]
        outliers_dict[col] = outliers
        
        # Boxplot Vertical
        ax.boxplot(data, vert=True, showfliers=True)
        ax.set_title(f'Boxplot de {col}')
        ax.set_xlabel(col)
        
        # Opcional: anotar número de outliers
        ax.annotate(f"n outliers={len(outliers)}",
                    xy=(0.95, 0.85), xycoords='axes fraction',
                    ha='right', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", 
                                                      fc="white", ec="gray"))
    
    plt.tight_layout()
    return outliers_dict, fig
# ------------------------------------------------------
def robust_scale_duration(df, column):
    """
    Reemplaza en la columna indicada todos los valores por encima del umbral
    de outliers (Q3 + 1.5 * IQR) con la mediana de la columna.
    
    Parámetros:
    - df: pandas.DataFrame
    - column: nombre de la columna a procesar
    
    Devuelve:
    - df modificado in-place con los outliers capados a la mediana.
    """
    # Cálculo de estadísticos
    median = df[column].median()
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    upper_bound = Q3 + 1.5 * IQR

    # Reemplazar outliers por la mediana
    df.loc[df[column] > upper_bound, column] = median
    return df

# ------------------------------------------------------
# función para graficar histogramas de atributos categóricos
# -------------------------------------------------------
# Esta función toma un DataFrame y una lista de nombres de columnas categóricas,
# y genera histogramas (barcharts) para cada columna, organizados en un grid de hasta 4 columnas.
# Se utiliza la biblioteca matplotlib para crear las visualizaciones.
# Se asume que las columnas categóricas son de tipo 'object' o 'category'.
# Se pueden rotar las etiquetas del eje x para mejorar la legibilidad.
# Se pueden ocultar los ejes sobrantes si hay menos columnas que filas*columnas.

def plot_categorical_histograms(df, columns, cols=4, rotation=45):
    """
    Dibuja histogramas (barcharts) de frecuencia para cada atributo categórico en 'columns',
    organizados en un grid de hasta 'cols' columnas.
    
    Parámetros:
    - df: pandas.DataFrame con los datos.
    - columns: lista de nombres de columnas categóricas a graficar.
    - cols: número de columnas en el grid.
    - rotation: ángulo de rotación de las etiquetas del eje x.
    """
    n = len(columns)
    rows = (n + cols - 1) // cols
    if rows == 0:
        rows = 1

    # Creamos la figura y los ejes en un grid rows x cols
    fig, axes = plt.subplots(rows, cols,
                             figsize=(4 * cols, 4 * rows),
                             squeeze=False)
    axes = axes.flatten()

    # Para cada columna, ploteamos en su eje correspondiente
    for ax, col in zip(axes, columns):
        counts = df[col].value_counts(dropna=False)
        counts.plot(kind='bar', ax=ax)
        ax.set_title(f'Histograma de {col}')
        ax.set_xlabel(col)
        ax.set_ylabel('Frecuencia')
        ax.tick_params(axis='x', rotation=rotation)

    # Ocultamos los ejes sobrantes (si n < rows*cols)
    for ax in axes[n:]:
        ax.set_visible(False)

    plt.tight_layout()
    plt.show()






