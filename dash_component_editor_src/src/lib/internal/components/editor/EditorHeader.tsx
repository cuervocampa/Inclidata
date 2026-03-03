import { useState } from 'react';
import { FileText, Braces, ZoomIn, ZoomOut, RotateCcw, Grid3x3 } from 'lucide-react';
import { useTemplateStore } from '@/store/templateStore';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';

const ZOOM_STEPS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3];

const ZoomControls = () => {
  const { zoom, setZoom } = useTemplateStore();
  const pct = Math.round(zoom * 100);

  const zoomIn = () => {
    const next = ZOOM_STEPS.find(s => s > zoom + 0.01);
    setZoom(next ?? 3);
  };
  const zoomOut = () => {
    const prev = [...ZOOM_STEPS].reverse().find(s => s < zoom - 0.01);
    setZoom(prev ?? 0.25);
  };

  return (
    <div className="flex items-center gap-0.5">
      <Button
        variant="ghost" size="sm"
        onClick={zoomOut}
        disabled={zoom <= 0.25}
        className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
        title="Reducir zoom"
      >
        <ZoomOut className="w-3.5 h-3.5" />
      </Button>
      <button
        type="button"
        onClick={() => setZoom(1)}
        className="text-xs font-mono min-w-[3rem] text-center text-muted-foreground hover:text-foreground transition-colors"
        title="Restaurar 100%"
      >
        {pct}%
      </button>
      <Button
        variant="ghost" size="sm"
        onClick={zoomIn}
        disabled={zoom >= 3}
        className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
        title="Aumentar zoom"
      >
        <ZoomIn className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
};

const GridToggle = () => {
  const { showGrid, setShowGrid } = useTemplateStore();
  return (
    <Button
      variant={showGrid ? 'secondary' : 'ghost'}
      size="sm"
      onClick={() => setShowGrid(!showGrid)}
      className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
      title={showGrid ? 'Ocultar rejilla' : 'Mostrar rejilla'}
    >
      <Grid3x3 className="w-3.5 h-3.5" />
    </Button>
  );
};

interface EditorHeaderProps {
  jsonInspectorOpen?: boolean;
  onToggleJsonInspector?: () => void;
}

export const EditorHeader = ({ jsonInspectorOpen, onToggleJsonInspector }: EditorHeaderProps) => {
  const { configuracion, updateConfig } = useTemplateStore();
  const [isEditing, setIsEditing] = useState(false);

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="h-12 bg-card border-b border-border flex items-center justify-between px-6"
    >
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <FileText className="w-4 h-4 text-primary" />
        </div>

        {isEditing ? (
          <Input
            value={configuracion.nombre_plantilla}
            onChange={(e) => updateConfig({ nombre_plantilla: e.target.value })}
            onBlur={() => setIsEditing(false)}
            onKeyDown={(e) => e.key === 'Enter' && setIsEditing(false)}
            className="w-64 h-8 text-sm font-semibold"
            autoFocus
          />
        ) : (
          <button
            onClick={() => setIsEditing(true)}
            className="text-sm font-semibold text-foreground hover:text-primary transition-colors"
            title="Clic para editar nombre"
          >
            {configuracion.nombre_plantilla}
          </button>
        )}

        <span className="text-xs text-foreground/55 border border-border/60 px-2 py-0.5 rounded-md">
          v{configuracion.version || '1.0'}
        </span>
      </div>

      {/* Right-side actions */}
      <div className="flex items-center gap-2">
        {/* Zoom controls */}
        <ZoomControls />

        {/* Grid toggle */}
        <GridToggle />

        {onToggleJsonInspector && (
          <Button
            variant={jsonInspectorOpen ? 'secondary' : 'ghost'}
            size="sm"
            onClick={onToggleJsonInspector}
            className="h-8 gap-1.5 text-xs"
            title="Inspector JSON"
          >
            <Braces className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">JSON</span>
          </Button>
        )}
      </div>
    </motion.header>
  );
};
