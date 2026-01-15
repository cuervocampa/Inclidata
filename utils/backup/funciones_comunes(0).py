# utils/funciones_comunes.py

from datetime import datetime

def import_RST(input_files):
    campaigns_data = {}

    # Procesar cada archivo de entrada
    for input_file in input_files:
        filename = input_file['filename']
        lines = input_file['lines']
        campaign_data = {}

        # Definir listas para almacenar los valores medidos
        depth_values = []
        a0_values = []
        a180_values = []
        b0_values = []
        b180_values = []

        depth_interval = 0.5

        try:
            reading_lines_start = None
            for i, line in enumerate(lines):
                if line.strip() == "" and "Depth,Face" in lines[i + 1]:
                    reading_lines_start = i + 2
                    break

                if ',' in line:
                    try:
                        key, value = line.strip().split(',', 1)
                    except ValueError:
                        print(f"Error al dividir la línea en {filename}: {line.strip()}")
                        continue

                    if key == "Borehole":
                        campaign_data["Nom_campo"] = value
                    elif key == "Reading Date(m/d/y)":
                        campaign_date = value
                    elif key == "Interval":
                        depth_interval = float(value)
                        campaign_data["Interval"] = depth_interval
                    elif key == "Probe Serial#":
                        campaign_data["Probe_serial"] = value
                    elif key == "Reel Serial#":
                        campaign_data["Reel_serial"] = value
                    elif key == "Reading Units":
                        campaign_data["Reading_units"] = value
                    elif key == "Depth Units":
                        campaign_data["Depth_units"] = value
                    elif key == "Operator":
                        campaign_data["Operator"] = value
                    elif key == "Offset Correction":
                        campaign_data["Offset_correction"] = float(value.split(",")[0])
                    elif key == "Incline Angle":
                        campaign_data["Incline_angle"] = float(value.split(",")[1])

            if reading_lines_start is None:
                print(f"No se encontró la línea de inicio de lectura en el archivo {filename}")
                continue

            for line in lines[reading_lines_start:]:
                if line.strip() == "":
                    continue

                parts = line.strip().split(',')
                if len(parts) == 5:
                    depth_values.append(abs(float(parts[0])))
                    a0_values.append(float(parts[1]))
                    a180_values.append(float(parts[2]))
                    b0_values.append(float(parts[3]))
                    b180_values.append(float(parts[4]))

            campaign_data["Depth"] = depth_values
            campaign_data["A0"] = a0_values
            campaign_data["A180"] = a180_values
            campaign_data["B0"] = b0_values
            campaign_data["B180"] = b180_values

            campaigns_data[campaign_date] = campaign_data

        except Exception as e:
            print(f"Error al procesar el archivo {filename}: {e}")

    campaigns_data = dict(
        sorted(campaigns_data.items(), key=lambda item: datetime.strptime(item[0], "%m/%d/%Y,%H:%M:%S")))

    return campaigns_data