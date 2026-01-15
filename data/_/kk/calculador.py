import json
from datetime import datetime
import os
import pandas as pd


def buscar_referencia(data, fecha_calc):
    fechas = sorted([datetime.fromisoformat(fecha) for fecha in data.keys() if fecha != 'info'])
    fecha_calc_dt = datetime.fromisoformat(fecha_calc)

    fecha_referencia = None
    for fecha in reversed(fechas):
        if fecha <= fecha_calc_dt and data[fecha.isoformat()]['campaign_info']['reference']:
            fecha_referencia = fecha.isoformat()
            break

    return fecha_referencia


def buscar_ant_referencia(data, fecha_referencia):
    fechas = sorted([datetime.fromisoformat(fecha) for fecha in data.keys() if fecha != 'info'])
    fecha_ref_dt = datetime.fromisoformat(fecha_referencia)

    fecha_ant_referencia = None
    for fecha in reversed(fechas):
        if fecha < fecha_ref_dt and data[fecha.isoformat()]['campaign_info']['active']:
            fecha_ant_referencia = fecha.isoformat()
            break

    return fecha_ant_referencia


def calcular_incrementos(data, fecha_calc):
    fecha_referencia = buscar_referencia(data, fecha_calc)
    fecha_ant_referencia = buscar_ant_referencia(data, fecha_referencia) if fecha_referencia else None

    if not fecha_referencia:
        fecha_referencia = fecha_calc

    calc_fecha_calc = data[fecha_calc]['calc']
    calc_fecha_referencia = data[fecha_referencia]['calc']

    # Calcular incr_dev_a y incr_dev_b
    for depth_info in calc_fecha_calc:
        depth = depth_info['depth']
        referencia_info = next((item for item in calc_fecha_referencia if item['depth'] == depth), None)

        if referencia_info:
            depth_info['incr_dev_a'] = depth_info['dev_a'] - referencia_info['dev_a']
            depth_info['incr_dev_b'] = depth_info['dev_b'] - referencia_info['dev_b']

    # Insertar parámetros calculados en el diccionario data, preservando los campos existentes excepto incr_dev_a y incr_dev_b
    for depth_info in calc_fecha_calc:
        existing_info = next((item for item in data[fecha_calc]['calc'] if item['depth'] == depth_info['depth']), None)
        if existing_info:
            for key, value in depth_info.items():
                if key not in ['incr_dev_a', 'incr_dev_b']:
                    existing_info[key] = value
        else:
            data[fecha_calc]['calc'].append(depth_info)

    # Calcular abs_dev_a y abs_dev_b
    for i, depth_info in enumerate(calc_fecha_calc):
        depth_info['abs_dev_a'] = sum(item['dev_a'] for item in calc_fecha_calc[i:])
        depth_info['abs_dev_b'] = sum(item['dev_b'] for item in calc_fecha_calc[i:])

    # Calcular desp_a y desp_b
    for i, depth_info in enumerate(calc_fecha_calc):
        depth_info['desp_a'] = sum(item.get('incr_dev_a', 0) for item in calc_fecha_calc[i:])
        depth_info['desp_b'] = sum(item.get('incr_dev_b', 0) for item in calc_fecha_calc[i:])

    # Insertar incr_dev_a y incr_dev_b en el diccionario data
    for depth_info in calc_fecha_calc:
        existing_info = next((item for item in data[fecha_calc]['calc'] if item['depth'] == depth_info['depth']), None)
        if existing_info:
            existing_info['incr_dev_a'] = depth_info['incr_dev_a']
            existing_info['incr_dev_b'] = depth_info['incr_dev_b']

    return data


def generar_df(data):
    # Crear listas para el DataFrame
    indices = []
    depths = []
    columns_data = {}

    # Obtener los encabezados de las columnas
    for fecha, valores in data.items():
        if fecha == 'info':
            continue
        for tipo in ['raw', 'calc']:
            for key in valores[tipo][0].keys():
                if key != 'depth':
                    col_name = f"{fecha}-{tipo}-{key}"
                    if col_name not in columns_data:
                        columns_data[col_name] = []

    # Rellenar los datos
    for idx, depth in enumerate([round(i * 0.5, 1) for i in range(1, 101)]):
        indices.append(idx + 1)
        depths.append(depth)
        for col in columns_data.keys():
            parts = col.split('-')
            fecha = '-'.join(parts[:-2])
            tipo = parts[-2]
            key = parts[-1]
            valor = next((item[key] for item in data[fecha][tipo] if item['depth'] == depth), None)
            columns_data[col].append(valor)

    # Crear el DataFrame
    df = pd.DataFrame({'Index': indices, 'Depth': depths, **columns_data})

    # Guardar el DataFrame en un archivo Excel
    df.to_excel('resultado.xlsx', index=False)


def main():
    # Leer el archivo ejemplo.json
    with open('ejemplo.json', 'r') as file:
        data = json.load(file)

    fecha_calc = "2017-07-24T08:48:32"
    data = calcular_incrementos(data, fecha_calc)

    # Guardar los cambios en el archivo ejemplo.json
    with open('ejemplo.json', 'w') as file:
        json.dump(data, file, indent=4)

    # Generar el DataFrame y guardarlo en Excel
    generar_df(data)


if __name__ == "__main__":
    main()