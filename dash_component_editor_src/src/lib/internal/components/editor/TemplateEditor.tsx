import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { useState } from 'react';
import { EditorHeader } from './EditorHeader';
import { ToolsSidebar } from './ToolsSidebar';
import { EditorCanvas } from './EditorCanvas';
import { PropertiesPanel } from './PropertiesPanel';
import { JsonInspector } from './JsonInspector';
import { useTemplateStore, ElementType } from '@/store/templateStore';
import { Type, Image, Minus, Square, BarChart3, Table2 } from 'lucide-react';

const CM_TO_PX = 37.8;

const defaultElements: Record<ElementType, { ancho: number; alto: number; estilo: Record<string, unknown>; contenido: Record<string, string> }> = {
  texto: {
    ancho: 5,
    alto: 1,
    estilo: { color: '#000000', tamano: 14, textAlign: 'left' },
    contenido: { texto: 'Nuevo texto' }
  },
  imagen: {
    ancho: 5,
    alto: 4,
    estilo: {},
    contenido: { src: '' }
  },
  linea: {
    ancho: 5,
    alto: 0.2,
    estilo: { borderColor: '#000000', borderWidth: 2 },
    contenido: {}
  },
  rectangulo: {
    ancho: 4,
    alto: 3,
    estilo: { backgroundColor: '#e2e8f0', borderWidth: 1, borderColor: '#cbd5e1' },
    contenido: {}
  },
  grafico: {
    ancho: 10,
    alto: 8,
    estilo: { opacity: 1 },
    contenido: {},
    configuracion: { script: '', formato: 'svg', parametros: {} }
  },
  tabla: {
    ancho: 10,
    alto: 5,
    estilo: {},
    contenido: {}
  }
};

const toolIcons: Record<ElementType, React.ReactNode> = {
  texto: <Type className="w-4 h-4" />,
  imagen: <Image className="w-4 h-4" />,
  linea: <Minus className="w-4 h-4" />,
  rectangulo: <Square className="w-4 h-4" />,
  grafico: <BarChart3 className="w-4 h-4" />,
  tabla: <Table2 className="w-4 h-4" />
};

const toolLabels: Record<ElementType, string> = {
  texto: 'Texto',
  imagen: 'Imagen',
  linea: 'Línea',
  rectangulo: 'Rectángulo',
  grafico: 'Gráfico',
  tabla: 'Tabla'
};

export const TemplateEditor = () => {
  const { addElement, pagina_actual, paginas } = useTemplateStore();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeType, setActiveType] = useState<ElementType | null>(null);
  const [jsonInspectorOpen, setJsonInspectorOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    if (active.data.current?.isNew) {
      const type = active.data.current.type as ElementType;
      setActiveId(active.id as string);
      setActiveType(type);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    setActiveId(null);
    setActiveType(null);

    if (!over || over.id !== 'canvas-drop-area') return;
    
    if (active.data.current?.isNew) {
      const type = active.data.current.type as ElementType;
      const defaults = defaultElements[type];
      
      // Get drop position relative to canvas
      const canvasRect = document.querySelector('.canvas-paper')?.getBoundingClientRect();
      if (!canvasRect) return;
      
      // Calculate position in cm
      const dropX = Math.max(0, ((event.activatorEvent as MouseEvent).clientX - canvasRect.left) / CM_TO_PX);
      const dropY = Math.max(0, ((event.activatorEvent as MouseEvent).clientY - canvasRect.top) / CM_TO_PX);
      
      // Get current max zIndex
      const currentPage = paginas[pagina_actual];
      const maxZIndex = Object.values(currentPage.elementos).reduce(
        (max, el) => Math.max(max, el.metadata.zIndex),
        0
      );

      addElement(pagina_actual, {
        tipo: type,
        geometria: {
          x: dropX,
          y: dropY,
          ancho: defaults.ancho,
          alto: defaults.alto
        },
        estilo: defaults.estilo as never,
        contenido: defaults.contenido,
        metadata: {
          zIndex: maxZIndex + 1,
          visible: true
        },
        ...((defaults as any).configuracion ? { configuracion: (defaults as any).configuracion } : {})
      });
    }
  };

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="h-screen flex flex-col bg-background">
        <EditorHeader
          jsonInspectorOpen={jsonInspectorOpen}
          onToggleJsonInspector={() => setJsonInspectorOpen(!jsonInspectorOpen)}
        />

        <div className="flex-1 flex overflow-hidden">
          <ToolsSidebar />
          <EditorCanvas />
          <PropertiesPanel />
        </div>

        {jsonInspectorOpen && (
          <JsonInspector onClose={() => setJsonInspectorOpen(false)} />
        )}
      </div>

      <DragOverlay>
        {activeId && activeType && (
          <div className="drag-overlay flex items-center gap-2">
            {toolIcons[activeType]}
            <span>{toolLabels[activeType]}</span>
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
};
