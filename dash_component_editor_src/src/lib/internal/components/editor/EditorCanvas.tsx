import { useDroppable } from '@dnd-kit/core';
import { useTemplateStore } from '@/store/templateStore';
import { CanvasElement } from './CanvasElement';
import { motion } from 'framer-motion';

// A4 dimensions in cm: 21cm x 29.7cm
const A4_WIDTH_CM = 21;
const A4_HEIGHT_CM = 29.7;
const CM_TO_PX = 37.8; // Screen conversion factor

export const EditorCanvas = () => {
  const { paginas, pagina_actual, selectElement } = useTemplateStore();
  const currentPage = paginas[pagina_actual];
  
  const { setNodeRef, isOver } = useDroppable({
    id: 'canvas-drop-area',
    data: { pageId: pagina_actual }
  });

  if (!currentPage) return null;

  const isLandscape = currentPage.configuracion.orientacion === 'landscape';
  const canvasWidth = (isLandscape ? A4_HEIGHT_CM : A4_WIDTH_CM) * CM_TO_PX;
  const canvasHeight = (isLandscape ? A4_WIDTH_CM : A4_HEIGHT_CM) * CM_TO_PX;

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
        {/* Grid overlay */}
        <div 
          className="absolute inset-0 pointer-events-none opacity-30"
          style={{
            backgroundImage: `
              linear-gradient(to right, hsl(var(--canvas-grid)) 1px, transparent 1px),
              linear-gradient(to bottom, hsl(var(--canvas-grid)) 1px, transparent 1px)
            `,
            backgroundSize: `${CM_TO_PX}cm ${CM_TO_PX}cm`,
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
  );
};

export { CM_TO_PX };
