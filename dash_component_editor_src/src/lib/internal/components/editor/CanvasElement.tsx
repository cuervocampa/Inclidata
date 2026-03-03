import { useState, useRef, useEffect } from 'react';
import { useTemplateStore, TemplateElement } from '@/store/templateStore';
import { motion } from 'framer-motion';
import { BarChart3, Table2 } from 'lucide-react';

interface CanvasElementProps {
  element: TemplateElement;
  pageId: string;
  cmToPx: number;
}

/**
 * Read helpers that understand the canonical JSON format.
 * Fields use Spanish names as stored in the JSON files.
 * Fallback to English names for elements created inside the visual editor.
 */
function getBackgroundColor(estilo: any, tipo: string): string {
  return estilo.color_relleno || estilo.backgroundColor || (tipo === 'rectangulo' ? '#e2e8f0' : 'transparent');
}
function getBorderColor(estilo: any): string {
  return estilo.color_borde || estilo.borderColor || '#cbd5e1';
}
function getBorderWidth(estilo: any, tipo: string): number {
  return estilo.grosor_borde ?? estilo.borderWidth ?? (tipo === 'rectangulo' ? 1 : 0);
}
function getOpacity(estilo: any): number {
  const raw = estilo.opacidad ?? estilo.opacity;
  if (raw == null) return 1;
  return raw > 1 ? raw / 100 : raw;
}
function getFontFamily(estilo: any): string {
  return estilo.familia_fuente || estilo.fontFamily || 'Arial';
}
function getFontWeight(estilo: any): string {
  return estilo.negrita || estilo.fontWeight || 'normal';
}
function getFontStyle(estilo: any): string {
  return estilo.cursiva || estilo.fontStyle || 'normal';
}
function getTextAlign(estilo: any): string {
  return estilo.alineacion_h || estilo.textAlign || 'left';
}
function getImageSrc(element: any): string {
  // Canonical: imagen.datos_temp or imagen.ruta_nueva
  // Visual editor format: contenido.src
  const img = element.imagen || {};
  const cont = element.contenido || {};
  return img.datos_temp || img.ruta_nueva || cont.src || '';
}
function getTexto(element: any): string {
  const cont = element.contenido || {};
  return cont.texto || '';
}

/** Deterministic pastel color from group name */
const GROUP_COLORS = [
  '#818cf8', '#f472b6', '#34d399', '#fbbf24', '#60a5fa',
  '#a78bfa', '#fb923c', '#2dd4bf', '#f87171', '#a3e635',
];
function getGroupColor(groupName: string): string {
  let hash = 0;
  for (let i = 0; i < groupName.length; i++) {
    hash = ((hash << 5) - hash + groupName.charCodeAt(i)) | 0;
  }
  return GROUP_COLORS[Math.abs(hash) % GROUP_COLORS.length];
}

export const CanvasElement = ({ element, pageId, cmToPx }: CanvasElementProps) => {
  const { selectedElementId, selectedElementIds, selectElement, toggleSelectElement, selectGroup, updateElement } = useTemplateStore();
  const isSelected = selectedElementId === element.id;
  const isMultiSelected = selectedElementIds.includes(element.id);

  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);

  const elementRef = useRef<HTMLDivElement>(null);
  const startPos = useRef({ x: 0, y: 0 });
  const startGeometry = useRef({ x: 0, y: 0, ancho: 0, alto: 0 });
  const startGeometries = useRef<Record<string, { x: number; y: number }>>({});

  const geometria = element.geometria || { x: 0, y: 0, ancho: 1, alto: 1 };
  const estilo = element.estilo || {};
  const tipo = element.tipo;
  const metadata = element.metadata || { zIndex: 0, visible: true };

  // Convert cm to px for display
  const style: React.CSSProperties = {
    left: geometria.x * cmToPx,
    top: geometria.y * cmToPx,
    width: (geometria.ancho || (geometria as any).ancho_maximo || 1) * cmToPx,
    height: (geometria.alto || (geometria as any).alto_maximo || 1) * cmToPx,
    backgroundColor: getBackgroundColor(estilo, tipo),
    color: estilo.color || '#000000',
    fontSize: estilo.tamano ? estilo.tamano : 14,
    fontFamily: getFontFamily(estilo),
    fontWeight: getFontWeight(estilo) as any,
    fontStyle: getFontStyle(estilo),
    textAlign: getTextAlign(estilo) as any,
    borderWidth: getBorderWidth(estilo, tipo),
    borderColor: getBorderColor(estilo),
    borderStyle: 'solid',
    opacity: getOpacity(estilo),
    zIndex: metadata.zIndex || 0,
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (e.shiftKey) {
      toggleSelectElement(element.id);
      return;
    }

    if (!isMultiSelected || selectedElementIds.length <= 1) {
      selectElement(element.id);
    }

    if ((e.target as HTMLElement).classList.contains('resize-handle')) return;

    setIsDragging(true);
    startPos.current = { x: e.clientX, y: e.clientY };
    startGeometry.current = { ...geometria };

    // Capture starting positions of all selected elements for group drag
    if (selectedElementIds.length > 1 && isMultiSelected) {
      const page = useTemplateStore.getState().paginas[pageId];
      const geoms: Record<string, { x: number; y: number }> = {};
      for (const id of selectedElementIds) {
        const el = page?.elementos[id];
        if (el) {
          geoms[id] = { x: el.geometria.x, y: el.geometria.y };
        }
      }
      startGeometries.current = geoms;
    } else {
      startGeometries.current = {};
    }
  };

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const grupo = metadata.grupo;
    if (grupo) {
      selectGroup(grupo);
    }
  };

  const handleResizeStart = (e: React.MouseEvent, handle: string) => {
    e.stopPropagation();
    setIsResizing(true);
    setResizeHandle(handle);
    startPos.current = { x: e.clientX, y: e.clientY };
    startGeometry.current = { ...geometria };
  };

  useEffect(() => {
    if (!isDragging && !isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = (e.clientX - startPos.current.x) / cmToPx;
      const deltaY = (e.clientY - startPos.current.y) / cmToPx;

      if (isDragging) {
        // Move all selected elements together if multi-selected
        const otherIds = Object.keys(startGeometries.current).filter(id => id !== element.id);
        if (otherIds.length > 0) {
          for (const id of otherIds) {
            const sg = startGeometries.current[id];
            updateElement(pageId, id, {
              geometria: {
                x: Math.max(0, sg.x + deltaX),
                y: Math.max(0, sg.y + deltaY),
              } as any
            });
          }
        }
        updateElement(pageId, element.id, {
          geometria: {
            ...geometria,
            x: Math.max(0, startGeometry.current.x + deltaX),
            y: Math.max(0, startGeometry.current.y + deltaY),
          }
        });
      } else if (isResizing && resizeHandle) {
        let newGeom = { ...startGeometry.current };

        if (resizeHandle.includes('e')) {
          newGeom.ancho = Math.max(1, startGeometry.current.ancho + deltaX);
        }
        if (resizeHandle.includes('w')) {
          newGeom.ancho = Math.max(1, startGeometry.current.ancho - deltaX);
          newGeom.x = startGeometry.current.x + deltaX;
        }
        if (resizeHandle.includes('s')) {
          newGeom.alto = Math.max(0.5, startGeometry.current.alto + deltaY);
        }
        if (resizeHandle.includes('n')) {
          newGeom.alto = Math.max(0.5, startGeometry.current.alto - deltaY);
          newGeom.y = startGeometry.current.y + deltaY;
        }

        updateElement(pageId, element.id, { geometria: newGeom });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
      setResizeHandle(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, resizeHandle, cmToPx, element.id, geometria, pageId, updateElement]);

  const renderContent = () => {
    switch (tipo) {
      case 'texto':
        return (
          <div className="w-full h-full p-1 overflow-hidden flex items-start">
            {getTexto(element) || 'Texto de ejemplo'}
          </div>
        );
      case 'imagen': {
        const src = getImageSrc(element);
        const mantenerProporcion = estilo.mantener_proporcion ?? true;
        return src ? (
          <img
            src={src}
            alt=""
            className="w-full h-full"
            style={{ objectFit: mantenerProporcion ? 'contain' : 'fill' }}
            draggable={false}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center bg-muted/50 text-muted-foreground border border-dashed border-border rounded gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 opacity-40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
              <circle cx="9" cy="9" r="2"/>
              <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
            </svg>
            <span className="text-[10px]">Sin imagen</span>
          </div>
        );
      }
      case 'linea':
        return (
          <div
            className="absolute top-1/2 left-0 right-0 h-0.5"
            style={{ backgroundColor: getBorderColor(estilo) }}
          />
        );
      case 'rectangulo':
        return null;
      case 'grafico': {
        const config = (element as any).configuracion || {};
        const scriptName = config.script ? config.script.replace('.py', '') : 'Sin script';
        const formato = config.formato || 'svg';
        return (
          <div className="w-full h-full flex flex-col items-center justify-center bg-muted/50 text-muted-foreground border border-dashed border-border rounded gap-0.5">
            <BarChart3 className="w-6 h-6 opacity-40" />
            <span className="text-[10px] font-medium truncate max-w-[90%]">{scriptName}</span>
            <span className="text-[8px] opacity-60 uppercase">{formato}</span>
          </div>
        );
      }
      case 'tabla': {
        const cuadricula = (element as any).cuadricula;
        const niveles = cuadricula?.niveles || [];
        const tableConfig = (element as any).configuracion || {};
        const scriptLabel = tableConfig.script ? tableConfig.script.replace('.py', '') : '';

        if (niveles.length === 0) {
          return (
            <div className="w-full h-full flex flex-col items-center justify-center bg-muted/50 text-muted-foreground border border-dashed border-border rounded gap-0.5">
              <Table2 className="w-6 h-6 opacity-40" />
              <span className="text-[10px]">Tabla vacía</span>
            </div>
          );
        }

        return (
          <div className="w-full h-full flex flex-col overflow-hidden bg-white rounded">
            {niveles.map((nivel: any) => {
              const rowCount = nivel.tipo === 'autorrelleno' ? 2 : 1;
              const rowHeightPx = (nivel.alto_fila || 0.5) * cmToPx;
              const nivelFontSize = nivel.estilo?.tamano || 10;
              return Array.from({ length: rowCount }, (_, rowIdx) => (
                <div key={`${nivel.id}-${rowIdx}`} className="flex w-full" style={{ height: rowHeightPx }}>
                  {(nivel.columnas || []).map((col: any, colIdx: number) => {
                    const pct = col.ancho || 10;
                    let bgColor = col.formato?.color_fondo || '#ffffff';
                    if (nivel.tipo === 'autorrelleno' && nivel.configuracion_dinamica?.sombreado_alterno) {
                      bgColor = rowIdx % 2 === 0
                        ? nivel.configuracion_dinamica.color_par || '#ffffff'
                        : nivel.configuracion_dinamica.color_impar || '#f0f0f0';
                    }
                    const text = nivel.tipo === 'autorrelleno' ? '...' : (col.contenido || '').slice(0, 8);
                    const borders = col.bordes || {};
                    const align = col.formato?.alineacion || 'left';
                    const justify = align === 'center' ? 'center' : align === 'right' ? 'flex-end' : 'flex-start';
                    const colFont = col.formato?.fuente || nivel.estilo?.fuente || 'sans-serif';
                    return (
                      <div key={colIdx} style={{
                        width: `${pct}%`,
                        backgroundColor: bgColor,
                        color: col.formato?.color_texto || '#000',
                        fontSize: nivelFontSize,
                        fontFamily: colFont,
                        fontWeight: col.formato?.negrita ? 'bold' : 'normal',
                        borderTop: borders.superior?.activo ? `${borders.superior.grosor || 1}px solid ${borders.superior.color || '#000'}` : 'none',
                        borderBottom: borders.inferior?.activo ? `${borders.inferior.grosor || 1}px solid ${borders.inferior.color || '#000'}` : 'none',
                        borderLeft: borders.izquierdo?.activo ? `${borders.izquierdo.grosor || 1}px solid ${borders.izquierdo.color || '#000'}` : 'none',
                        borderRight: borders.derecho?.activo ? `${borders.derecho.grosor || 1}px solid ${borders.derecho.color || '#000'}` : 'none',
                        padding: '1px 2px',
                        overflow: 'hidden',
                        whiteSpace: 'nowrap' as const,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: justify,
                      }}>
                        {text}
                      </div>
                    );
                  })}
                </div>
              ));
            })}
            {scriptLabel && (
              <div className="text-[8px] text-muted-foreground text-center mt-auto py-0.5 bg-muted/30 truncate">
                {scriptLabel}
              </div>
            )}
          </div>
        );
      }
      default:
        return null;
    }
  };

  return (
    <motion.div
      ref={elementRef}
      className={`canvas-element ${isSelected ? 'selected' : ''} ${isMultiSelected && !isSelected ? 'multi-selected' : ''}`}
      style={style}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.15 }}
    >
      {renderContent()}

      {/* Group indicator tag */}
      {metadata.grupo && (
        <div
          className="group-indicator"
          style={{ backgroundColor: getGroupColor(metadata.grupo) }}
          title={`Grupo: ${metadata.grupo}`}
        >
          {metadata.grupo}
        </div>
      )}

      {/* Single resize handle at bottom-right corner */}
      {(isSelected && selectedElementIds.length <= 1) && (
        <div
          className="resize-handle-corner"
          onMouseDown={(e) => handleResizeStart(e, 'se')}
        />
      )}
    </motion.div>
  );
};
