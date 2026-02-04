import { useState, useRef, useEffect } from 'react';
import { useTemplateStore, TemplateElement } from '@/store/templateStore';
import { motion } from 'framer-motion';

interface CanvasElementProps {
  element: TemplateElement;
  pageId: string;
  cmToPx: number;
}

export const CanvasElement = ({ element, pageId, cmToPx }: CanvasElementProps) => {
  const { selectedElementId, selectElement, updateElement } = useTemplateStore();
  const isSelected = selectedElementId === element.id;
  
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);
  
  const elementRef = useRef<HTMLDivElement>(null);
  const startPos = useRef({ x: 0, y: 0 });
  const startGeometry = useRef({ x: 0, y: 0, ancho: 0, alto: 0 });

  const { geometria, estilo, contenido, tipo, metadata } = element;

  // Convert cm to px for display
  const style: React.CSSProperties = {
    left: geometria.x * cmToPx,
    top: geometria.y * cmToPx,
    width: geometria.ancho * cmToPx,
    height: geometria.alto * cmToPx,
    backgroundColor: estilo.backgroundColor || (tipo === 'rectangulo' ? '#e2e8f0' : 'transparent'),
    color: estilo.color || '#000000',
    fontSize: estilo.tamano ? estilo.tamano : 14,
    fontWeight: estilo.fontWeight || 'normal',
    fontStyle: estilo.fontStyle || 'normal',
    textAlign: estilo.textAlign || 'left',
    borderWidth: estilo.borderWidth || (tipo === 'rectangulo' ? 1 : 0),
    borderColor: estilo.borderColor || '#cbd5e1',
    borderStyle: 'solid',
    opacity: estilo.opacity ?? 1,
    zIndex: metadata.zIndex,
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectElement(element.id);
    
    if ((e.target as HTMLElement).classList.contains('resize-handle')) return;
    
    setIsDragging(true);
    startPos.current = { x: e.clientX, y: e.clientY };
    startGeometry.current = { ...geometria };
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
            {contenido.texto || 'Texto de ejemplo'}
          </div>
        );
      case 'imagen':
        return contenido.src ? (
          <img src={contenido.src} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted text-muted-foreground text-xs">
            Imagen
          </div>
        );
      case 'linea':
        return (
          <div 
            className="absolute top-1/2 left-0 right-0 h-0.5"
            style={{ backgroundColor: estilo.borderColor || '#000' }}
          />
        );
      case 'rectangulo':
        return null;
      case 'grafico':
        return (
          <div className="w-full h-full flex items-center justify-center bg-muted/50 text-muted-foreground text-xs border border-dashed border-border rounded">
            📊 Gráfico
          </div>
        );
      case 'tabla':
        return (
          <div className="w-full h-full flex items-center justify-center bg-muted/50 text-muted-foreground text-xs border border-dashed border-border rounded">
            📋 Tabla
          </div>
        );
      default:
        return null;
    }
  };

  const resizeHandles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];

  return (
    <motion.div
      ref={elementRef}
      className={`canvas-element ${isSelected ? 'selected' : ''}`}
      style={style}
      onMouseDown={handleMouseDown}
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.15 }}
    >
      {renderContent()}
      
      {isSelected && resizeHandles.map((handle) => (
        <div
          key={handle}
          className={`resize-handle resize-handle-${handle}`}
          onMouseDown={(e) => handleResizeStart(e, handle)}
        />
      ))}
    </motion.div>
  );
};
