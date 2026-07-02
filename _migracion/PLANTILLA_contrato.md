# PLANTILLA DE CONTRATO DE INTERFAZ
Todo contrato (inclidata y maketador) usa EXACTAMENTE estas secciones, en este orden.
Vocabulario canónico = el de maketador (ver GLOSARIO). inclidata mapea sus términos
a ese vocabulario cuando exista equivalencia. El entregable es una INTERFAZ, no código.

## 1. Propósito y frontera
Qué expone este proyecto a la integración y qué queda fuera de alcance.

## 2. Objetos de datos
Cada objeto que cruza la frontera: nombre, estructura, campos (nombre · tipo · unidad),
y un ejemplo mínimo real.

## 3. Parámetros y clasificación
Lista de parámetros/variables. Por cada uno: unidad, convenio de signo y clasificación
primario/secundario (mapear a params_clasificacion de maketador).

## 4. Convenios y unidades
Ejes, lectura de referencia/base, cota vs profundidad, signos, campañas, fechas.

## 5. Puntos de extensión
- maketador: alta de script (ScriptRegistry), entrada en la dispatch table, resolución
  de tokens $CURRENT*, diferencias motor PDF (ReportLab/Matplotlib) vs web (HTML/Playwright).
- inclidata: dónde y en qué formato quedan disponibles los objetos YA calculados
  (¿se serializan? ¿solo se renderizan en Dash?).

## 6. Gráficos
Cada gráfico producido/esperado: tipo, ejes, series, etiquetas/leader-lines, motor(es) que lo soportan.

## 7. Supuestos, límites y preguntas abiertas
Lo que no se resuelve leyendo código y requiere decisión tuya o mía.