"""
Script de ejemplo para tabla con una sola fecha.
Muestra profundidad, desplazamiento A y desplazamiento B
para la fecha seleccionada (o la última campaña disponible).
"""

from datetime import datetime


def ejemplo_tabla_kk(data, parametros):
    """
    Genera datos para una tabla simple de inclinometría con una única fecha.

    Args:
        data: Datos del inclinómetro (dict con info, umbrales y fechas ISO como claves).
        parametros: Diccionario de configuración.
            - fecha_seleccionada: Fecha de corte (slider en Graficar).
            - fecha_final: Alternativa a fecha_seleccionada.

    Returns:
        dict con:
            - encabezados_nivel_1: Lista con una sola fecha formateada.
            - filas: Lista de dicts con 'prof', 'desp_a_1', 'desp_b_1'.
    """
    try:
        # Claves que NO son fechas de campaña
        claves_especiales = {
            "info", "umbrales", "fecha_seleccionada", "ultimas_camp",
            "fecha_inicial", "fecha_final", "total_camp", "cadencia_dias",
            "eje", "orden", "color_scheme", "escala_desplazamiento",
            "escala_incremento", "sensor", "nombre_sensor", "leyenda_umbrales",
            "valor_positivo_desplazamiento", "valor_negativo_desplazamiento",
            "valor_positivo_incremento", "valor_negativo_incremento",
            "escala_temporal", "valor_positivo_temporal", "valor_negativo_temporal",
        }

        # 1. Filtrar fechas válidas (con 'calc' y activas)
        fechas_validas = []
        for k in data.keys():
            if k in claves_especiales:
                continue
            fecha_data = data[k]
            if isinstance(fecha_data, dict) and "calc" in fecha_data:
                campaign_info = fecha_data.get("campaign_info", {})
                if campaign_info.get("active", True):
                    fechas_validas.append(k)

        if not fechas_validas:
            return {"encabezados_nivel_1": [], "filas": []}

        fechas_validas.sort(key=lambda x: datetime.fromisoformat(x))

        # 2. Determinar la fecha a mostrar
        fecha_corte_str = parametros.get("fecha_seleccionada") or parametros.get("fecha_final")

        idx = len(fechas_validas) - 1  # por defecto la última
        if fecha_corte_str:
            try:
                if "T" in fecha_corte_str:
                    fecha_corte_dt = datetime.fromisoformat(fecha_corte_str)
                else:
                    fecha_corte_dt = datetime.fromisoformat(fecha_corte_str.replace(" ", "T"))

                for i, f in enumerate(fechas_validas):
                    if datetime.fromisoformat(f) >= fecha_corte_dt:
                        idx = i
                        break
            except ValueError:
                pass

        fecha_elegida = fechas_validas[idx]
        fecha_formateada = fecha_elegida.split("T")[0] if "T" in fecha_elegida else fecha_elegida.split(" ")[0]

        # 3. Obtener lecturas de la fecha elegida
        lecturas = data[fecha_elegida].get("calc", [])
        if not lecturas:
            return {"encabezados_nivel_1": [fecha_formateada], "filas": []}

        # 4. Construir filas
        filas = []
        for lectura in lecturas:
            profundidad = lectura.get("depth", 0)
            desp_a = lectura.get("desp_a", 0)
            desp_b = lectura.get("desp_b", 0)
            filas.append({
                "prof": f"{profundidad:.1f}",
                "desp_a_1": f"{desp_a:.2f}",
                "desp_b_1": f"{desp_b:.2f}",
            })

        return {
            "encabezados_nivel_1": [fecha_formateada],
            "filas": filas,
        }

    except Exception as e:
        print(f"Error en ejemplo_tabla_kk: {e}")
        import traceback
        traceback.print_exc()
        return {"encabezados_nivel_1": [], "filas": [], "error": str(e)}
