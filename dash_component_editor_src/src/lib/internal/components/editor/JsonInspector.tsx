import { useState, useRef, useCallback, useEffect } from 'react';
import { useTemplateStore } from '@/store/templateStore';
import { Copy, Check, X, GripHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface JsonInspectorProps {
  onClose: () => void;
}

type ViewMode = 'template' | 'page' | 'element';

const MIN_HEIGHT = 120;
const MAX_HEIGHT_RATIO = 0.7; // max 70% of viewport

export const JsonInspector = ({ onClose }: JsonInspectorProps) => {
  const {
    paginas,
    pagina_actual,
    configuracion,
    selectedElementId,
  } = useTemplateStore();

  const [viewMode, setViewMode] = useState<ViewMode>('template');
  const [copied, setCopied] = useState(false);
  const [wordWrap, setWordWrap] = useState(false);
  const [height, setHeight] = useState(300);

  const isDragging = useRef(false);
  const startY = useRef(0);
  const startHeight = useRef(0);

  const currentPage = paginas[pagina_actual];
  const selectedElement = selectedElementId
    ? currentPage?.elementos[selectedElementId]
    : null;

  // --- resize logic ---
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    isDragging.current = true;
    startY.current = e.clientY;
    startHeight.current = height;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [height]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging.current) return;
    const delta = startY.current - e.clientY; // drag up = bigger
    const maxH = window.innerHeight * MAX_HEIGHT_RATIO;
    setHeight(Math.min(maxH, Math.max(MIN_HEIGHT, startHeight.current + delta)));
  }, []);

  const onPointerUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  // --- JSON generation ---
  const getJson = (): string => {
    switch (viewMode) {
      case 'element':
        if (!selectedElement) return '// Ningún elemento seleccionado';
        return JSON.stringify(selectedElement, null, 2);
      case 'page':
        if (!currentPage) return '// Página no encontrada';
        return JSON.stringify(
          { [`pagina_${pagina_actual}`]: currentPage },
          null,
          2
        );
      case 'template':
      default:
        return JSON.stringify(
          { paginas, pagina_actual, configuracion },
          null,
          2
        );
    }
  };

  const jsonText = getJson();
  const lineCount = jsonText.split('\n').length;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const tabs: { key: ViewMode; label: string; disabled?: boolean }[] = [
    { key: 'template', label: 'Plantilla' },
    { key: 'page', label: `Página ${pagina_actual}` },
    { key: 'element', label: 'Elemento', disabled: !selectedElement },
  ];

  return (
    <div className="border-t border-border bg-card flex flex-col shrink-0" style={{ height }}>
      {/* Resize handle */}
      <div
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        className="h-2 flex items-center justify-center cursor-ns-resize shrink-0
                   hover:bg-accent/50 active:bg-accent transition-colors"
        title="Arrastrar para redimensionar"
      >
        <GripHorizontal className="w-4 h-3 text-muted-foreground/40" />
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 h-9 border-b border-border shrink-0">
        <div className="flex items-center gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              disabled={tab.disabled}
              onClick={() => setViewMode(tab.key)}
              className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                viewMode === tab.key
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              } disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[10px] text-muted-foreground mr-2">
            {lineCount} líneas
          </span>
          <button
            onClick={() => setWordWrap(!wordWrap)}
            className={`px-2 py-1 text-[10px] rounded transition-colors ${
              wordWrap
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            title="Ajuste de línea"
          >
            wrap
          </button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-6 w-6 p-0"
            title="Copiar JSON"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-6 w-6 p-0"
            title="Cerrar inspector"
          >
            <X className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* JSON content */}
      <pre
        className={`flex-1 overflow-auto p-3 text-xs font-mono leading-relaxed text-foreground/80 select-all scrollbar-thin ${
          wordWrap ? 'whitespace-pre-wrap break-all' : ''
        }`}
      >
        {jsonText}
      </pre>
    </div>
  );
};
