import streamlit as st
import os
import shutil
from datetime import datetime

def obtener_fecha_dux(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lines = file.readlines()
            if len(lines) > 1:
                fecha_linea = lines[1].strip().split(',')[1]  # Extraer la fecha de la segunda línea
                fecha_obj = datetime.strptime(fecha_linea, "%Y/%m/%d %H:%M:%S")
                return fecha_obj.strftime("%Y%m%d")  # Formato AAAAMMDD
    except Exception as e:
        st.error(f"Error al procesar {filepath}: {e}")
    return None

def renombrar_archivos_dux(root_path):
    script_directory = os.getcwd()  # Carpeta del script
    for subdir, _, files in os.walk(root_path):
        for file in files:
            if file.endswith(".dux"):
                old_path = os.path.join(subdir, file)
                fecha = obtener_fecha_dux(old_path)
                if fecha:
                    new_name = f"{fecha}_{file}"
                    new_path = os.path.join(script_directory, new_name)  # Guardar en la carpeta del script
                    shutil.move(old_path, new_path)
                    st.write(f"Renombrado y movido: {file} -> {new_name}")
                else:
                    st.warning(f"No se pudo obtener la fecha para {file}")

st.title("Renombrador de archivos .dux")
root_directory = os.getcwd()  # Carpeta donde se ejecuta el script
st.write(f"Buscando archivos en: {root_directory}")

if st.button("Renombrar archivos .dux"):
    renombrar_archivos_dux(root_directory)
    st.success("Proceso completado")
