# utils/funciones_correcciones.py
import pandas as pd
import plotly.graph_objs as go

def grafico_violines(df, fecha_seleccionada):
    # Convertir las profundidades a índice si no lo están
    df.index.name = 'Profundidad'

    # Reiniciar el índice para convertirlo en una columna y facilitar el uso de Plotly
    df_reset = df.reset_index()

    # Cambiar el formato del DataFrame a largo (long format) para usar con plotly.graph_objs
    # Esto facilitará tener columnas de 'Profundidad', 'Fecha' y 'Valor'
    df_long = df_reset.melt(id_vars=['Profundidad'], var_name='Fecha', value_name='Valor')

    # Crear el gráfico de violines utilizando plotly.graph_objs
    fig = go.Figure()
    for profundidad in df_long['Profundidad'].unique():
        df_profundidad = df_long[df_long['Profundidad'] == profundidad]
        # Añadir gráfico de violín
        fig.add_trace(go.Violin(x=df_profundidad['Valor'], y=df_profundidad['Profundidad'],
                                orientation='h', name=f'Profundidad {profundidad} m', box_visible=True,
                                points='all', meanline_visible=True, line_color='mediumblue', marker=dict(color='skyblue')))

    # Añadir los puntos correspondientes a la fecha seleccionada en rojo
    df_fecha_seleccionada = df_long[df_long['Fecha'] == fecha_seleccionada]
    fig.add_trace(go.Scatter(x=df_fecha_seleccionada['Valor'], y=df_fecha_seleccionada['Profundidad'],
                             mode='markers', name=f'Fecha Seleccionada ({fecha_seleccionada})',
                             marker=dict(color='red', size=8),
                             showlegend=True))

    # Configurar el título y las etiquetas
    # fig.update_layout(title='Distribución de los Valores para Cada Profundidad',
    fig.update_layout(xaxis_title='Valor de la Medida')
    # yaxis_title='Profundidad (m)')

    # Invertir el eje y para mostrar las profundidades en orden inverso
    fig.update_yaxes(autorange='reversed')

    # Mostrar el gráfico
    #fig.show()
    return fig

def dict_a_df(data, variables, fechas_seleccionadas):
    # pasa el diccionario json a un df con las variables seleccionadas
    # se cogen sólo las fechas que importan
    # devuelve tantos df como variables, en un diccionario de df's

    # Inicializar diccionarios para cada DataFrame
    df_dicts = {key: {} for key in variables}

    # Rellenar los diccionarios para cada DataFrame
    for fecha in fechas_seleccionadas:
        if fecha in data:
            rows = data[fecha]['calc']
            for row in rows:
                for key in variables:
                    df_dicts[key].setdefault(fecha, {})[row['depth']] = row[key]

    # Crear los DataFrames dinámicamente
    dfs = {f"{key}": pd.DataFrame(df_dicts[key]) for key in variables}

    return dfs

def creacion_df_bias(calc_ref, calc_corr):
    # calcula el df_bias para la corrección posterior:
    # calc_ref y calc_corr: datos de ['calc'] en las campañas selecc y ref
    # Output: df_bias

    # 3.a. extrae los valores del diccionario json
    depths = [entry['depth'] for entry in calc_corr]
    dev_a_ref = [entry['dev_a'] for entry in calc_ref]
    dev_b_ref = [entry['dev_b'] for entry in calc_ref]
    dev_a_corr = [entry['dev_a'] for entry in calc_corr]
    dev_b_corr = [entry['dev_b'] for entry in calc_corr]
    checksum_a_ref = [entry['checksum_a'] for entry in calc_ref]
    checksum_b_ref = [entry['checksum_b'] for entry in calc_ref]
    checksum_a_corr = [entry['checksum_a'] for entry in calc_corr]
    checksum_b_corr = [entry['checksum_b'] for entry in calc_corr]
    # 3.b. inserta los valores en df_bias
    df_bias = pd.DataFrame({
        'depth': depths,
        'dev_a_ref': dev_a_ref,
        'dev_b_ref': dev_b_ref,
        'dev_a_corr': dev_a_corr,
        'dev_b_corr': dev_b_corr,
        'checksum_a_ref': [entry[0] if isinstance(entry, list) else entry for entry in checksum_a_ref],
        'checksum_b_ref': [entry[0] if isinstance(entry, list) else entry for entry in checksum_b_ref],
        'checksum_a_corr': [entry[0] if isinstance(entry, list) else entry for entry in checksum_a_corr],
        'checksum_b_corr': [entry[0] if isinstance(entry, list) else entry for entry in checksum_b_corr],
    })

    # 4. Añadir columnas incrementales y desplazamientos
    df_bias['incr_dev_a'] = df_bias['dev_a_corr'] - df_bias['dev_a_ref']
    df_bias['incr_dev_b'] = df_bias['dev_b_corr'] - df_bias['dev_b_ref']

    # Calcular desplazamientos acumulativos (sumatorio desde la más profunda)
    df_bias['desp_a'] = df_bias['incr_dev_a'][::-1].cumsum()[::-1]
    df_bias['desp_b'] = df_bias['incr_dev_b'][::-1].cumsum()[::-1]

    # para hacer pruebas, añado incrChecksum ¿se usa esto?
    df_bias['incr_checksum_a'] = df_bias['checksum_a_corr'] - df_bias['checksum_a_ref']
    df_bias['incr_checksum_b'] = df_bias['checksum_b_corr'] - df_bias['checksum_b_ref']

    # Invertir las filas, calcular promedio acumulativo y volver a invertir
    df_bias['avg_Incr_A'] = df_bias['incr_dev_a'][::-1].expanding().mean()[::-1]
    df_bias['avg_Incr_B'] = df_bias['incr_dev_b'][::-1].expanding().mean()[::-1]

    return df_bias
"""
def calculos_bias(df_bias, h_inf_A_1, h_sup_A_1, h_inf_B_1, h_sup_B_1, delta_a_1, delta_b_1):
    # df_bias: datos de las campañas ref y a corregir
    # h's tramos de aplicación de las correcciones
    # deltas: correcciones a aplicar
    # Output: df_bias con las rectas de corrección y las series corregidas

    # serie recta
    # falta por personalizarlo para los tramos. Sólo funciona para inicial
    last_index = df_bias.index[-1]  # Última fila del índice
    df_bias['recta_a'] = delta_a_1 * (last_index - df_bias.index)  # es una recta, sólo depende de la pendiente (delta)
    df_bias['recta_b'] = delta_b_1 * (last_index - df_bias.index)
    # serie corregida, resta el abatimiento a el desplazamiento medido
    df_bias['corr_a'] = df_bias['desp_a'] - df_bias['recta_a']
    df_bias['corr_b'] = df_bias['desp_b'] - df_bias['recta_b']

    return df_bias
"""
def calculos_bias(df_bias,
                  h_inf_A_1, h_sup_A_1, h_inf_B_1, h_sup_B_1, delta_a_1, delta_b_1,
                  h_inf_A_2, h_sup_A_2, h_inf_B_2, h_sup_B_2, delta_a_2, delta_b_2,):
    """
    Calcula las correcciones para las columnas `recta_a` y `recta_b` en el DataFrame `df_bias`, simulando una polilínea.
    Se incluyen las correcciones de los pasos 1 y 2
    El segundo paso de corrección no es recomendable

    Args:
        df_bias (DataFrame): Datos de las campañas de referencia y a corregir.
        h_inf_A_1 (float): Inicio del rango de corrección para A.
        h_sup_A_1 (float): Fin del rango de corrección para A.
        h_inf_B_1 (float): Inicio del rango de corrección para B.
        h_sup_B_1 (float): Fin del rango de corrección para B.
        delta_a_1 (float): Pendiente de corrección para A dentro del rango.
        delta_b_1 (float): Pendiente de corrección para B dentro del rango.

    Returns:
        DataFrame: El DataFrame actualizado con las columnas `recta_a`, `recta_b`, `corr_a`, `corr_b`.
    """
    # Convertir delta_a_1 y delta_b_1 a números; si no son convertibles, establecer en 0
    try:
        delta_a_1 = float(delta_a_1)
    except (ValueError, TypeError):
        delta_a_1 = 0.0

    try:
        delta_b_1 = float(delta_b_1)
    except (ValueError, TypeError):
        delta_b_1 = 0.0

    # Validar que no haya división por cero
    count_a = df_bias.loc[(df_bias['depth'] <= h_inf_A_1) & (df_bias['depth'] >= h_sup_A_1), 'depth'].count()
    count_b = df_bias.loc[(df_bias['depth'] <= h_inf_B_1) & (df_bias['depth'] >= h_sup_B_1), 'depth'].count()

    if count_a == 0 or count_b == 0:
        # Evitar la división por cero estableciendo los incrementos en 0
        delta_a_1 = 0.0
        delta_b_1 = 0.0
    else:
        # Convertir las pendientes en incrementos unitarios
        delta_a_1 /= count_a
        delta_b_1 /= count_b

    # Inicialización de las rectas como ceros
    df_bias['recta_a'] = 0
    df_bias['recta_b'] = 0

    # evito un deprecated
    df_bias['recta_a'] = df_bias['recta_a'].astype(float)
    df_bias['recta_b'] = df_bias['recta_b'].astype(float)

    # Construcción de la recta para A
    offset = 0 # offset inicial
    for i in range(len(df_bias.index) - 1, -1, -1):
        depth = df_bias.loc[i, 'depth']
        if depth <= h_inf_A_1 and depth >= h_sup_A_1:  # Si está dentro del rango, aplica pendiente delta_a_1
            df_bias.loc[i, 'recta_a'] = offset + delta_a_1 * (df_bias[df_bias["depth"] == h_inf_A_1].index[0] - i)
        else:  # Si está fuera rango, continúa con el offset anterior
            df_bias.loc[i, 'recta_a'] = offset

        # offset para los cambios de pendiente de la polilínea
        if depth == h_inf_A_1 or depth == h_sup_A_1:
            offset = df_bias.loc[i, 'recta_a']

    # Construcción de la recta para B
    offset = 0 # offset inicial
    for i in range(len(df_bias.index) - 1, -1, -1):
        depth = df_bias.loc[i, 'depth']
        if depth <= h_inf_B_1 and depth >= h_sup_B_1:  # Si está dentro del rango, aplica pendiente delta_a_1
            df_bias.loc[i, 'recta_b'] = offset + delta_b_1 * (df_bias[df_bias["depth"] == h_inf_B_1].index[0] - i)
        else:  # Si está fuera rango, continúa con el offset anterior
            df_bias.loc[i, 'recta_b'] = offset

        # offset para los cambios de pendiente de la polilínea
        if depth == h_inf_B_1 or depth == h_sup_B_1:
            offset = df_bias.loc[i, 'recta_b']

    # Serie corregida: resta el abatimiento a los desplazamientos medidos
    df_bias['corr_a'] = df_bias['desp_a'] - df_bias['recta_a']
    df_bias['corr_b'] = df_bias['desp_b'] - df_bias['recta_b']

    return df_bias

