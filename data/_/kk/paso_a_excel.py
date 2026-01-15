import json
import pandas as pd

# Cargar el archivo JSON
with open('ejemplo.json', 'r') as f:
    data = json.load(f)

# Crear un archivo Excel con un writer de pandas
with pd.ExcelWriter('ejemplo.xlsx', engine='openpyxl') as writer:
    # Iterar por cada fecha en el JSON
    for fecha, valores in data.items():
        # Remover caracteres inválidos del nombre de la hoja
        fecha = fecha.replace(':', '_').replace('/', '_').replace('?', '_')
        # Extraer el diccionario 'calc'
        calc_data = valores.get('calc', {})

        # Crear un DataFrame donde las columnas son las claves de 'calc' y las filas son los 'depth'
        df = pd.DataFrame(calc_data)

        # Guardar el DataFrame en una nueva hoja del archivo Excel
        df.to_excel(writer, sheet_name=fecha, index=True)

print("Archivo Excel creado exitosamente: ejemplo.xlsx")
