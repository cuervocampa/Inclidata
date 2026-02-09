import { useDroppable } from '@dnd-kit/core';
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
  const { paginas, pagina_actual, selectElement } = useTemplateStore();
  const currentPage = paginas[pagina_actual];

  const { setNodeRef, isOver } = useDroppable({
    id: 'canvas-drop-area',
    data: { pageId: pagina_actual }
  });

  if (!currentPage) return null;

  const isLandscape = currentPage.configuracion.orientacion === 'landscape';
  const widthCm = isLandscape ? A4_HEIGHT_CM : A4_WIDTH_CM;
  const heightCm = isLandscape ? A4_WIDTH_CM : A4_HEIGHT_CM;
  const canvasWidth = widthCm * CM_TO_PX;
  const canvasHeight = heightCm * CM_TO_PX;

  const elements = Object.values(currentPage.elementos || {}).sort(
    (a, b) => (a.metadata?.zIndex || 0) - (b.metadata?.zIndex || 0)
  );

  const handleCanvasClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      selectElement(null);
    }
  };

  return (
    <div className="canvas-container flex items-center justify-center p-8">
      <div className="flex flex-col items-start">
        {/* Horizontal ruler */}
        <div className="flex" style={{ marginLeft: RULER_SIZE }}>
          <svg
            width={canvasWidth}
            height={RULER_SIZE}
            className="canvas-ruler canvas-ruler-h"
          >
            <rect width="100%" height="100%" fill="hsl(var(--secondary))" />
            <RulerTicks length={canvasWidth} cmToPx={CM_TO_PX} direction="h" />
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
            <RulerTicks length={canvasHeight} cmToPx={CM_TO_PX} direction="v" />
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
                backgroundSize: `${CM_TO_PX}px ${CM_TO_PX}px, ${CM_TO_PX}px ${CM_TO_PX}px, ${CM_TO_PX / 2}px ${CM_TO_PX / 2}px, ${CM_TO_PX / 2}px ${CM_TO_PX / 2}px`,
              }}
            />

            {/* Render elements */}
            {elements.map((element) => (
              <CanvasElement
                key={element.id}
                element={element}
                pageId={pagina_actual}
                cmToPx={CM_TO_PX}
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
