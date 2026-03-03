import { useDroppable } from '@dnd-kit/core';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTemplateStore } from '@/store/templateStore';
import { CanvasElement } from './CanvasElement';
import { motion } from 'framer-motion';

// A4 dimensions in cm: 21cm x 29.7cm
const A4_WIDTH_CM = 21;
const A4_HEIGHT_CM = 29.7;
const CM_TO_PX = 37.8; // Screen conversion factor
const RULER_SIZE = 24; // px – ruler thickness

/** Generates tick marks for a ruler */
const RulerTicks = ({ length, cmToPx, direction }: { length: number; cmToPx: number; direction: 'h' | 'v' }) => {
  const totalCm = Math.ceil(length / cmToPx);
  const ticks = [];

  for (let cm = 0; cm <= totalCm; cm++) {
    const pos = cm * cmToPx;
    const isMajor = cm % 5 === 0;
    const tickLen = isMajor ? 12 : cm % 1 === 0 ? 7 : 4;

    if (direction === 'h') {
      ticks.push(
        <line key={cm} x1={pos} y1={RULER_SIZE} x2={pos} y2={RULER_SIZE - tickLen}
          stroke="hsl(var(--muted-foreground))" strokeWidth={isMajor ? 1 : 0.5} />
      );
      if (isMajor) {
        ticks.push(
          <text key={`t${cm}`} x={pos + 2} y={10} fontSize="9"
            fill="hsl(var(--muted-foreground))" fontFamily="Inter, sans-serif">
            {cm}
          </text>
        );
      }
    } else {
      ticks.push(
        <line key={cm} x1={RULER_SIZE} y1={pos} x2={RULER_SIZE - tickLen} y2={pos}
          stroke="hsl(var(--muted-foreground))" strokeWidth={isMajor ? 1 : 0.5} />
      );
      if (isMajor) {
        ticks.push(
          <text key={`t${cm}`} x={3} y={pos + 11} fontSize="9"
            fill="hsl(var(--muted-foreground))" fontFamily="Inter, sans-serif">
            {cm}
          </text>
        );
      }
    }
  }
  return <>{ticks}</>;
};

export const EditorCanvas = () => {
  const { paginas, pagina_actual, zoom, setZoom, clearSelection } = useTemplateStore();
  const currentPage = paginas[pagina_actual];
  const containerRef = useRef<HTMLDivElement>(null);

  // ── Pan state ──────────────────────────────────────────────────────────────
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const panOffsetRef = useRef({ x: 0, y: 0 });
  const isPanningRef = useRef(false);
  const [isPanning, setIsPanning] = useState(false);
  const isSpacePressedRef = useRef(false);
  const [isSpaceActive, setIsSpaceActive] = useState(false);
  const panStartRef = useRef<{ mouseX: number; mouseY: number; startX: number; startY: number } | null>(null);

  const { setNodeRef, isOver } = useDroppable({
    id: 'canvas-drop-area',
    data: { pageId: pagina_actual }
  });

  // ── Ctrl+wheel zoom ────────────────────────────────────────────────────────
  const handleWheel = useCallback((e: WheelEvent) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(useTemplateStore.getState().zoom + delta);
  }, [setZoom]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // ── Space key for pan mode ─────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return;
      const tag = (document.activeElement as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      e.preventDefault();
      isSpacePressedRef.current = true;
      setIsSpaceActive(true);
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return;
      isSpacePressedRef.current = false;
      setIsSpaceActive(false);
      if (isPanningRef.current) {
        isPanningRef.current = false;
        setIsPanning(false);
        panStartRef.current = null;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // ── Global mouse move / up (so pan continues outside the container) ────────
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isPanningRef.current || !panStartRef.current) return;
      const dx = e.clientX - panStartRef.current.mouseX;
      const dy = e.clientY - panStartRef.current.mouseY;
      const newOffset = {
        x: panStartRef.current.startX + dx,
        y: panStartRef.current.startY + dy,
      };
      panOffsetRef.current = newOffset;
      setPanOffset(newOffset);
    };
    const handleMouseUp = () => {
      if (!isPanningRef.current) return;
      isPanningRef.current = false;
      setIsPanning(false);
      panStartRef.current = null;
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // ── Start pan on container mousedown ──────────────────────────────────────
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const isMiddle = e.button === 1;
    const isSpaceDrag = e.button === 0 && isSpacePressedRef.current;
    if (!isMiddle && !isSpaceDrag) return;

    e.preventDefault(); // Prevents text selection and (for space+drag) click event
    isPanningRef.current = true;
    setIsPanning(true);
    panStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      startX: panOffsetRef.current.x,
      startY: panOffsetRef.current.y,
    };
  }, []);

  if (!currentPage) return null;

  const effectiveCmToPx = CM_TO_PX * zoom;

  const isLandscape = currentPage.configuracion.orientacion === 'landscape';
  const widthCm = isLandscape ? A4_HEIGHT_CM : A4_WIDTH_CM;
  const heightCm = isLandscape ? A4_WIDTH_CM : A4_HEIGHT_CM;
  const canvasWidth = widthCm * effectiveCmToPx;
  const canvasHeight = heightCm * effectiveCmToPx;

  const elements = Object.values(currentPage.elementos || {}).sort(
    (a, b) => (a.metadata?.zIndex || 0) - (b.metadata?.zIndex || 0)
  );

  const handleCanvasClick = (e: React.MouseEvent) => {
    // Ignore click if a pan drag just happened (e.preventDefault on mousedown prevents this anyway,
    // but guard here for safety)
    if (e.target === e.currentTarget) {
      clearSelection();
    }
  };

  // Double-click on the background resets pan to center
  const handleContainerDoubleClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      panOffsetRef.current = { x: 0, y: 0 };
      setPanOffset({ x: 0, y: 0 });
    }
  };

  const cursor = isPanning ? 'grabbing' : isSpaceActive ? 'grab' : undefined;

  return (
    <div
      ref={containerRef}
      className="canvas-container flex items-center justify-center p-8 overflow-hidden select-none"
      style={{ cursor }}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleContainerDoubleClick}
      title="Doble clic para centrar • Rueda+Ctrl para zoom • Espacio+arrastre o botón central para desplazar"
    >
      {/* Pan hint tooltip */}
      {isSpaceActive && !isPanning && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-50 pointer-events-none
          bg-foreground/80 text-background text-xs px-2.5 py-1 rounded-full shadow">
          Arrastra para desplazar
        </div>
      )}

      <div
        className="flex flex-col items-start"
        style={{ transform: `translate(${panOffset.x}px, ${panOffset.y}px)` }}
      >
        {/* Horizontal ruler */}
        <div className="flex" style={{ marginLeft: RULER_SIZE }}>
          <svg
            width={canvasWidth}
            height={RULER_SIZE}
            className="canvas-ruler canvas-ruler-h"
          >
            <rect width="100%" height="100%" fill="hsl(var(--secondary))" />
            <RulerTicks length={canvasWidth} cmToPx={effectiveCmToPx} direction="h" />
            <line x1={0} y1={RULER_SIZE - 0.5} x2={canvasWidth} y2={RULER_SIZE - 0.5}
              stroke="hsl(var(--border))" strokeWidth={1} />
          </svg>
        </div>

        <div className="flex">
          {/* Vertical ruler */}
          <svg
            width={RULER_SIZE}
            height={canvasHeight}
            className="canvas-ruler canvas-ruler-v"
          >
            <rect width="100%" height="100%" fill="hsl(var(--secondary))" />
            <RulerTicks length={canvasHeight} cmToPx={effectiveCmToPx} direction="v" />
            <line x1={RULER_SIZE - 0.5} y1={0} x2={RULER_SIZE - 0.5} y2={canvasHeight}
              stroke="hsl(var(--border))" strokeWidth={1} />
          </svg>

          {/* Canvas paper */}
          <motion.div
            ref={setNodeRef}
            className={`canvas-paper rounded-sm ${isOver ? 'ring-2 ring-primary ring-offset-4' : ''}`}
            style={{
              width: canvasWidth,
              height: canvasHeight,
              minWidth: canvasWidth,
              minHeight: canvasHeight,
            }}
            onClick={handleCanvasClick}
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {/* Grid overlay – 1cm major + 0.5cm minor */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                backgroundImage: `
                  linear-gradient(to right, hsl(var(--canvas-grid) / 0.35) 1px, transparent 1px),
                  linear-gradient(to bottom, hsl(var(--canvas-grid) / 0.35) 1px, transparent 1px),
                  linear-gradient(to right, hsl(var(--canvas-grid) / 0.15) 1px, transparent 1px),
                  linear-gradient(to bottom, hsl(var(--canvas-grid) / 0.15) 1px, transparent 1px)
                `,
                backgroundSize: `${effectiveCmToPx}px ${effectiveCmToPx}px, ${effectiveCmToPx}px ${effectiveCmToPx}px, ${effectiveCmToPx / 2}px ${effectiveCmToPx / 2}px, ${effectiveCmToPx / 2}px ${effectiveCmToPx / 2}px`,
              }}
            />

            {/* Render elements */}
            {elements.map((element) => (
              <CanvasElement
                key={element.id}
                element={element}
                pageId={pagina_actual}
                cmToPx={effectiveCmToPx}
              />
            ))}

            {/* Drop indicator */}
            {isOver && (
              <div className="absolute inset-4 border-2 border-dashed border-primary/50 rounded-lg pointer-events-none flex items-center justify-center">
                <span className="text-primary font-medium bg-primary/10 px-3 py-1.5 rounded-full text-sm">
                  Soltar aquí
                </span>
              </div>
            )}

            {/* Page info */}
            <div className="absolute bottom-2 right-2 text-xs text-muted-foreground/50">
              {isLandscape ? '29.7 × 21 cm' : '21 × 29.7 cm'} • Página {pagina_actual}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export { CM_TO_PX };
