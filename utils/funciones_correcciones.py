# utils/funciones_correcciones.py
import dash
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
    indexs = [entry['index'] for entry in calc_corr]
    cota_abss = [entry['cota_abs'] for entry in calc_corr]
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
        'index': indexs,
        'cota_abs': cota_abss,
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
    df_bias['incr_dev_a'] = (df_bias['dev_a_corr'] - df_bias['dev_a_ref']).round(2)
    df_bias['incr_dev_b'] = (df_bias['dev_b_corr'] - df_bias['dev_b_ref']).round(2)

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
def calculos_bias(df_bias,
                  h_inf_A_1, h_sup_A_1, h_inf_B_1, h_sup_B_1, delta_a_1, delta_b_1,
                  h_inf_A_2, h_sup_A_2, h_inf_B_2, h_sup_B_2, delta_a_2, delta_b_2,):
    """
        Calcula las correcciones para las columnas `recta_a` y `recta_b` en el DataFrame `df_bias`, simulando una polilínea.

        Args:
            df_bias (DataFrame): Datos de las campañas de referencia y a corregir.
            h_inf_A_1, h_sup_A_1 (float): Inicio y fin del rango de corrección para A en el paso 1.
            h_inf_B_1, h_sup_B_1 (float): Inicio y fin del rango de corrección para B en el paso 1.
            delta_a_1, delta_b_1 (float): Pendientes de corrección para A y B en el paso 1.
            h_inf_A_2, h_sup_A_2 (float): Inicio y fin del rango de corrección para A en el paso 2.
            h_inf_B_2, h_sup_B_2 (float): Inicio y fin del rango de corrección para B en el paso 2.
            delta_a_2, delta_b_2 (float): Pendientes de corrección para A y B en el paso 2.

        Returns:
            DataFrame: El DataFrame actualizado con las columnas `recta_a`, `recta_b`, `corr_a`, `corr_b`.
        """

    def validar_parametro(valor, nombre):
        try:
            return float(valor)
        except (ValueError, TypeError):
            print(f"Advertencia: {nombre} no es válido. Se establece en 0.0.")
            return 0.0

    # Validar y convertir pendientes
    delta_a_1 = validar_parametro(delta_a_1, "delta_a_1")
    delta_b_1 = validar_parametro(delta_b_1, "delta_b_1")
    delta_a_2 = validar_parametro(delta_a_2, "delta_a_2")
    delta_b_2 = validar_parametro(delta_b_2, "delta_b_2")

    # Funciones auxiliares para calcular incrementos
    def calcular_incremento(df, h_inf, h_sup, delta):
        count = df.loc[(df['depth'] <= h_inf) & (df['depth'] >= h_sup), 'depth'].count()
        return delta / count if count > 0 else 0.0

    # Calcular incrementos para los dos pasos
    delta_a_1 = calcular_incremento(df_bias, h_inf_A_1, h_sup_A_1, delta_a_1)
    delta_b_1 = calcular_incremento(df_bias, h_inf_B_1, h_sup_B_1, delta_b_1)
    delta_a_2 = calcular_incremento(df_bias, h_inf_A_2, h_sup_A_2, delta_a_2)
    delta_b_2 = calcular_incremento(df_bias, h_inf_B_2, h_sup_B_2, delta_b_2)

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

def calculos_bias_1(df_bias, df_bias_table, json_spikes):
    """
    Calcula las correcciones para las columnas `recta_a` y `recta_b` en el DataFrame `df_bias`, simulando una polilínea.

    Args:
        df_bias (DataFrame): Datos de las campañas de referencia y a corregir.
        df_bias_table (DataFrame): Tabla con los parámetros de corrección en el formato:
            - Correccion (str): Nombre del bias.
            - Selec (bool): Indica si el bias está seleccionado.
            - Prof_inf (float): Inicio del rango de profundidad.
            - Prof_sup (float): Fin del rango de profundidad.
            - Delta (float): Pendiente de corrección.

    Returns:
        DataFrame: El DataFrame actualizado con las columnas `recta_a`, `recta_b`, `corr_a`, `corr_b`.
    """

    # Convertir las columnas a numérico y manejar errores
    columnas_a_convertir = ['Prof_inf', 'Prof_sup', 'Delta']
    for col in columnas_a_convertir:
        if col in df_bias_table.columns:
            df_bias_table[col] = pd.to_numeric(df_bias_table[col], errors='coerce')

    # Reemplazar valores NaN con un valor predeterminado y emitir advertencias
    if df_bias_table[columnas_a_convertir].isna().any().any():
        columnas_con_nan = df_bias_table[columnas_a_convertir].isna().sum()
        print(f"Advertencia: La tabla contiene valores no válidos en las columnas: {columnas_con_nan[columnas_con_nan > 0].to_dict()}.")
        df_bias_table[columnas_a_convertir] = df_bias_table[columnas_a_convertir].fillna(0.0)

    # Extraer parámetros de la tabla
    def obtener_parametros(bias_table, correccion):
        fila = bias_table.loc[bias_table['Correccion'] == correccion]
        if fila.empty:
            raise ValueError(f"No se encontraron datos para la corrección {correccion}.")
        return {
            'h_inf': fila['Prof_inf'].iloc[0],
            'h_sup': fila['Prof_sup'].iloc[0],
            'delta': fila['Delta'].iloc[0] if 'Delta' in fila.columns else 0.0,
            'seleccionado': bool(fila['Selec'].iloc[0])
        }

    try:
        params_1_a = obtener_parametros(df_bias_table, 'Bias_1_A')
        params_1_b = obtener_parametros(df_bias_table, 'Bias_1_B')
        params_2_a = obtener_parametros(df_bias_table, 'Bias_2_A')
        params_2_b = obtener_parametros(df_bias_table, 'Bias_2_B')

        # Funciones auxiliares para calcular incrementos
        def calcular_incremento(df, h_inf, h_sup, delta):
            count = df.loc[(df['depth'] <= h_inf) & (df['depth'] >= h_sup), 'depth'].count()
            return delta / count if count > 0 else 0.0

        # Calcular incrementos para los dos pasos
        delta_a_1 = calcular_incremento(df_bias, params_1_a['h_inf'], params_1_a['h_sup'], params_1_a['delta'])
        delta_b_1 = calcular_incremento(df_bias, params_1_b['h_inf'], params_1_b['h_sup'], params_1_b['delta'])
        delta_a_2 = calcular_incremento(df_bias, params_2_a['h_inf'], params_2_a['h_sup'], params_2_a['delta'])
        delta_b_2 = calcular_incremento(df_bias, params_2_b['h_inf'], params_2_b['h_sup'], params_2_b['delta'])

        # Inicialización de las rectas como ceros
        df_bias['recta_a'] = 0.0
        df_bias['recta_b'] = 0.0


        # Construcción de la recta para A
        offset = 0  # offset inicial
        for i in range(len(df_bias.index) - 1, -1, -1):
            depth = df_bias.loc[i, 'depth']
            # Tramo de corrección 1
            if params_1_a['seleccionado'] and depth < params_1_a['h_inf'] and depth >= params_1_a['h_sup']:
                # Si está dentro del rango, aplica pendiente delta_a_1
                # Nota: depth son profundidades, i.e., van a ser crecientes
                df_bias.loc[i, 'recta_a'] = offset + delta_a_1
                offset = df_bias.loc[i, 'recta_a']
            else:  # Si está fuera rango, continúa con el offset anterior
                df_bias.loc[i, 'recta_a'] = offset

            # Tramo de corrección 2. Por construcción, el tramo 2 siempre será continuación del tramo 1
            if params_2_a['seleccionado'] and depth < params_2_a['h_inf'] and depth >= params_2_a['h_sup']:
                # Si está dentro del rango, aplica pendiente delta_a_1
                df_bias.loc[i, 'recta_a'] = offset + delta_a_2
                offset = df_bias.loc[i, 'recta_a']
            else:  # Si está fuera rango, continúa con el offset anterior
                df_bias.loc[i, 'recta_a'] = offset

        # Construcción de la recta para B
        offset = 0  # offset inicial
        for i in range(len(df_bias.index) - 1, -1, -1):
            depth = df_bias.loc[i, 'depth']
            # Tramo de corrección 1
            if params_1_b['seleccionado'] and depth < params_1_b['h_inf'] and depth >= params_1_b['h_sup']:
                # Si está dentro del rango, aplica pendiente delta_a_1
                df_bias.loc[i, 'recta_b'] = offset + delta_b_1
                offset = df_bias.loc[i, 'recta_b']
            else:  # Si está fuera rango, continúa con el offset anterior
                df_bias.loc[i, 'recta_b'] = offset

            # Tramo de corrección 2. Por construcción, el tramo 2 siempre será continuación del tramo 1
            if params_2_b['seleccionado'] and depth < params_2_b['h_inf'] and depth >= params_2_b['h_sup']:
                # Si está dentro del rango, aplica pendiente delta_a_1
                df_bias.loc[i, 'recta_b'] = offset + delta_b_2
                offset = df_bias.loc[i, 'recta_b']
            else:  # Si está fuera rango, continúa con el offset anterior
                df_bias.loc[i, 'recta_b'] = offset

        # Serie corregida: resta el abatimiento a los desplazamientos medidos
        df_bias['corr_a'] = df_bias['desp_a'] - df_bias['recta_a']
        df_bias['corr_b'] = df_bias['desp_b'] - df_bias['recta_b']

        # Cálculo de las componentes A0-B180 con las correcciones
        # i) Para cada escalón se calcula el incremento que hay que compensar. Es el resultado de
        # la resta en la recta de corrección de la profunidad del escalón con el anterior
        # Crear df_componentes con la columna depth
        df_componentes = df_bias[['depth', 'recta_a', 'recta_b']].copy()

        # Calcular diferencias en orden inverso
        df_componentes['delta_a'] = df_componentes['recta_a'].iloc[::-1].diff().iloc[::-1]
        df_componentes['delta_b'] = df_componentes['recta_b'].iloc[::-1].diff().iloc[::-1]

        # Llenar la última fila con 0 en lugar de NaN
        df_componentes = df_componentes.fillna(0)

        # ii) extrae las columnas a0-a180 de json_spikes y lo añade a df_componentes
        # Obtener la única clave de fecha disponible
        fecha_key = list(json_spikes.keys())[0]

        # Extraer los datos relevantes usando la clave de fecha
        data_list = json_spikes[fecha_key]['calc']

        # Crear el DataFrame con las claves requeridas
        df_extracted_generic = pd.DataFrame(data_list, columns=['depth', 'a0', 'a180', 'b0', 'b180'])

        # Agregar las columnas extraídas a df_componentes usando merge
        df_componentes = df_componentes.merge(df_extracted_generic, on="depth", how="left")
        # Renombrar las columnas de spk
        df_componentes = df_componentes.rename(columns={'a0': 'a0_spk', 'a180': 'a180_spk', 'b0': 'b0_spk', 'b180': 'b180_spk'})

        # iii) Agregar las nuevas columnas con los componentes corregidos
        # la corrección debe sumar -delta
        # ((a0-delta_a)-(a180+delta_a))/2 = (a0-a180)/2 - 2*delta_a/2
        # tener en cuenta que delta es -1*corrección a aplicar
        df_componentes['a0'] = df_componentes['a0_spk'] - df_componentes['delta_a']
        df_componentes['a180'] = df_componentes['a180_spk'] + df_componentes['delta_a']
        df_componentes['b0'] = df_componentes['b0_spk'] - df_componentes['delta_b']
        df_componentes['b180'] = df_componentes['b180_spk'] + df_componentes['delta_b']

        # iv) se meten a0-b180 en df_bias
        df_bias = df_bias.merge(df_componentes[['depth', 'a0', 'a180', 'b0', 'b180']], on="depth", how="left")


        return df_bias

    except ValueError as e:
        return {
            'display': 'block',
            'message': str(e)
        }


# función para construir la tabla-json a partir del archivo json
def tabla_del_json(df, fechas):
    table_data = []
    for fecha in fechas:
        row = {
            'Fecha': fecha,
            'Referencia': df[fecha].get('campaign_info', {}).get('reference', 'N/A'),
            'Activa': df[fecha].get('campaign_info', {}).get('active', 'N/A'),
            'Cuarentena': df[fecha].get('campaign_info', {}).get('quarentine', 'N/A'),
            'spike': True if df.get(fecha, {}).get('spike') else False,
            'bias': True if df.get(fecha, {}).get('bias') else False,
            'Limpiar': False  # Valor por defecto, ojo considerar que esto es para la carga inicial
        }
        table_data.append(row)

    return table_data


def std(variables, fechas_activas, data, profundidad):
    # Inicializar diccionarios para cada DataFrame
    df_dicts = {key: {} for key in variables}

    # Rellenar los diccionarios para cada DataFrame, filtrando por profundidad
    for fecha in fechas_activas:
        if fecha in data:
            rows = data[fecha]['calc']
            for row in rows:
                if row['depth'] >= profundidad:
                    for key in variables:
                        df_dicts[key].setdefault(fecha, {})[row['depth']] = row[key]

    # Crear los DataFrames dinámicamente
    dfs_sigma = {f"{key}": pd.DataFrame(df_dicts[key]) for key in variables}

    # Calcula desviación típica por cada fecha (columna) y crea un único DataFrame combinado
    df_std = pd.DataFrame({var: dfs_sigma[var].std() for var in dfs_sigma})

    # Renombrar las columnas agregando '_std'
    df_std = df_std.rename(columns={col: f"{col}_std" for col in df_std.columns})

    # Renombrar el índice del DataFrame
    df_std.index.name = 'fecha'
    return df_std



