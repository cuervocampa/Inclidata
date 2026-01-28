"""
Script para generar datos de tabla de inclinometría.
Rellena la tabla con las últimas 3 fechas (campañas) del sensor,
mostrando profundidad, desplazamiento A y desplazamiento B para cada fecha.
"""

from datetime import datetime


def tabla_datos_inc(data, parametros):
    """
    Genera datos para una tabla de inclinometría mostrando las últimas campañas.
    
    Args:
        data: Datos completos del inclinómetro (diccionario con info, umbrales y fechas).
        parametros: Diccionario de configuración.
            - fecha_seleccionada: La fecha seleccionada en el slider (última fecha a mostrar).
            - fecha_final: Alternativa a fecha_seleccionada.
            - ultimas_camp: Cantidad de campañas a mostrar (default: 3).
    
    Returns:
        dict con:
            - encabezados_nivel_1: Lista de fechas formateadas para la fila 2.
            - filas: Lista de diccionarios con 'prof', 'desp_a_1', 'desp_b_1', etc.
    """
    try:
        # Definir claves especiales que no son fechas ISO
        claves_especiales = {"info", "umbrales", "fecha_seleccionada", "ultimas_camp", 
                             "fecha_inicial", "fecha_final", "total_camp", "cadencia_dias",
                             "eje", "orden", "color_scheme", "escala_desplazamiento", 
                             "escala_incremento", "sensor", "nombre_sensor", "leyenda_umbrales",
                             "valor_positivo_desplazamiento", "valor_negativo_desplazamiento",
                             "valor_positivo_incremento", "valor_negativo_incremento",
                             "escala_temporal", "valor_positivo_temporal", "valor_negativo_temporal"}
        
        # 1. Determinar la fecha de corte (la seleccionada en el slider o fecha final)
        fecha_corte_str = parametros.get("fecha_seleccionada") or parametros.get("fecha_final")
        
        print(f"DEBUG tabla_datos_inc: fecha_corte_str = {fecha_corte_str}")
        print(f"DEBUG tabla_datos_inc: ultimas_camp = {parametros.get('ultimas_camp')}")
        
        # Filtrar solo claves que sean fechas válidas y tengan datos calculados ('calc')
        # Además deben estar marcadas como activas (active=true en campaign_info)
        fechas_validas = []
        for k in data.keys():
            if k not in claves_especiales:
                # Verificar que tiene 'calc' y que está activa
                fecha_data = data[k]
                if isinstance(fecha_data, dict) and "calc" in fecha_data:
                    campaign_info = fecha_data.get("campaign_info", {})
                    if campaign_info.get("active", True):  # Por defecto activa si no existe el campo
                        fechas_validas.append(k)
        
        if not fechas_validas:
            print("DEBUG tabla_datos_inc: No se encontraron fechas válidas")
            return {"encabezados_nivel_1": [], "filas": []}
        
        # Ordenar cronológicamente
        fechas_validas.sort(key=lambda x: datetime.fromisoformat(x))
        print(f"DEBUG tabla_datos_inc: {len(fechas_validas)} fechas válidas encontradas")
        print(f"DEBUG tabla_datos_inc: Primera fecha: {fechas_validas[0]}")
        print(f"DEBUG tabla_datos_inc: Última fecha: {fechas_validas[-1]}")
        
        # 2. Seleccionar las campañas a mostrar
        # Buscar el índice de la fecha de corte. Si no existe o no se pasa, usar la última.
        idx_corte = len(fechas_validas) - 1
        if fecha_corte_str:
            print(f"DEBUG tabla_datos_inc: Buscando fecha de corte: {fecha_corte_str}")
            try:
                # Convertir la fecha de corte a datetime para comparación robusta
                # Manejar formato con o sin 'T' separador
                if 'T' in fecha_corte_str:
                    fecha_corte_dt = datetime.fromisoformat(fecha_corte_str)
                else:
                    fecha_corte_dt = datetime.fromisoformat(fecha_corte_str.replace(' ', 'T'))
                
                # Buscar la fecha más cercana o igual a la fecha de corte
                for i, f in enumerate(fechas_validas):
                    fecha_i_dt = datetime.fromisoformat(f)
                    if fecha_i_dt >= fecha_corte_dt:
                        # Si es exactamente igual o posterior, este es el índice
                        idx_corte = i
                        break
                    # Si estamos en la última y aún es anterior, usar la última
                    if i == len(fechas_validas) - 1:
                        idx_corte = i
                
                print(f"DEBUG tabla_datos_inc: idx_corte encontrado = {idx_corte} (fecha: {fechas_validas[idx_corte]})")
            except ValueError as e:
                print(f"DEBUG tabla_datos_inc: Error al parsear fecha_corte_str: {e}")
                # Fallback: usar la última fecha
                idx_corte = len(fechas_validas) - 1
        
        # Determinar cuántas campañas mostrar (por defecto 3)
        try:
            n_camp = int(parametros.get("ultimas_camp", 3))
        except (ValueError, TypeError):
            n_camp = 3
        
        # Seleccionar el rango: desde (idx_corte - n + 1) hasta idx_corte
        inicio = max(0, idx_corte - n_camp + 1)
        fechas_reporte = fechas_validas[inicio:idx_corte + 1]
        
        if not fechas_reporte:
            return {"encabezados_nivel_1": [], "filas": []}
        
        # 3. Configurar encabezados de Nivel 2 (Las Fechas)
        # Formatear fechas para que ocupen menos espacio (ej: 2023-10-25)
        # Orden: antepenúltima (fecha_1), penúltima (fecha_2), última (fecha_3)
        encabezados_fechas = []
        for f in fechas_reporte:
            # Extraer solo la parte de la fecha (YYYY-MM-DD)
            fecha_formateada = f.split("T")[0] if "T" in f else f.split(" ")[0]
            encabezados_fechas.append(fecha_formateada)
        
        # Si hay menos de 3 fechas, rellenar desde la izquierda
        # (las columnas de la derecha quedarán vacías si no hay datos)
        
        # 4. Obtener profundidades de la primera fecha válida
        primera_fecha = fechas_reporte[0]
        datos_referencia = data[primera_fecha].get("calc", [])
        
        if not datos_referencia:
            return {"encabezados_nivel_1": encabezados_fechas, "filas": []}
        
        # 5. Construir las filas
        filas = []
        
        for i, lectura_ref in enumerate(datos_referencia):
            # Obtener profundidad (depth) - usar 1 decimal
            profundidad = lectura_ref.get("depth", 0)
            
            # Crear objeto fila con la profundidad formateada
            fila = {
                "prof": f"{profundidad:.1f}",
            }
            
            # Para cada fecha en fechas_reporte, obtener desp_a y desp_b
            valores = []
            for fecha_idx, fecha in enumerate(fechas_reporte):
                datos_fecha = data[fecha].get("calc", [])
                
                # Buscar la lectura correspondiente a esta profundidad
                lectura_encontrada = None
                
                # Primero intentar por índice directo
                if i < len(datos_fecha):
                    if abs(datos_fecha[i].get("depth", -999) - profundidad) < 0.01:
                        lectura_encontrada = datos_fecha[i]
                
                # Si no coincide, buscar manualmente
                if lectura_encontrada is None:
                    for lectura in datos_fecha:
                        if abs(lectura.get("depth", -999) - profundidad) < 0.01:
                            lectura_encontrada = lectura
                            break
                
                if lectura_encontrada:
                    desp_a = lectura_encontrada.get("desp_a", 0)
                    desp_b = lectura_encontrada.get("desp_b", 0)
                    # Formatear con 2 decimales
                    valores.append(f"{desp_a:.2f}")
                    valores.append(f"{desp_b:.2f}")
                else:
                    # Si no hay dato para esa fecha/profundidad
                    valores.append("")
                    valores.append("")
            
            # Añadir los valores al diccionario de fila
            # Estructura: desp_a_1, desp_b_1, desp_a_2, desp_b_2, desp_a_3, desp_b_3
            for v_idx, val in enumerate(valores):
                fecha_num = (v_idx // 2) + 1
                tipo = "desp_a" if v_idx % 2 == 0 else "desp_b"
                fila[f"{tipo}_{fecha_num}"] = val
            
            filas.append(fila)
        
        # 6. Retornar estructura completa
        return {
            "encabezados_nivel_1": encabezados_fechas,
            "filas": filas
        }

    except Exception as e:
        print(f"Error en tabla_datos_inc: {e}")
        import traceback
        traceback.print_exc()
        return {"encabezados_nivel_1": [], "filas": [], "error": str(e)}
