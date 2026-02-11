import { 
  Type, 
  Image, 
  Minus, 
  Square, 
  BarChart3, 
  Table2,
  Plus,
  ChevronLeft,
  ChevronRight,
  MonitorSmartphone,
  Smartphone
} from 'lucide-react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { useTemplateStore, ElementType } from '@/store/templateStore';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';

interface ToolItemProps {
  type: ElementType;
  label: string;
  icon: React.ReactNode;
}

const DraggableToolItem = ({ type, label, icon }: ToolItemProps) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `tool-${type}`,
    data: { type, isNew: true }
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="tool-item"
    >
      <div className="tool-item-icon">
        {icon}
      </div>
      <span className="text-sm font-medium text-foreground">{label}</span>
    </div>
  );
};

const tools: ToolItemProps[] = [
  { type: 'texto', label: 'Texto', icon: <Type className="w-4 h-4" /> },
  { type: 'imagen', label: 'Imagen', icon: <Image className="w-4 h-4" /> },
  { type: 'linea', label: 'Línea', icon: <Minus className="w-4 h-4" /> },
  { type: 'rectangulo', label: 'Rectángulo', icon: <Square className="w-4 h-4" /> },
  { type: 'grafico', label: 'Gráfico', icon: <BarChart3 className="w-4 h-4" /> },
  { type: 'tabla', label: 'Tabla', icon: <Table2 className="w-4 h-4" /> },
];

export const ToolsSidebar = () => {
  const { 
    paginas, 
    pagina_actual, 
    configuracion,
    addPage, 
    setCurrentPage,
    setPageOrientation 
  } = useTemplateStore();
  
  const currentPage = paginas[pagina_actual];
  const pageIds = Object.keys(paginas).sort((a, b) => Number(a) - Number(b));
  const currentIndex = pageIds.indexOf(pagina_actual);

  const goToPrevPage = () => {
    if (currentIndex > 0) {
      setCurrentPage(pageIds[currentIndex - 1]);
    }
  };

  const goToNextPage = () => {
    if (currentIndex < pageIds.length - 1) {
      setCurrentPage(pageIds[currentIndex + 1]);
    }
  };

  return (
    <motion.aside 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-64 bg-card border-r border-border flex flex-col"
    >
      {/* Tools Section */}
      <div className="p-4 border-b border-border">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Componentes
        </h3>
        <div className="space-y-1">
          {tools.map((tool) => (
            <DraggableToolItem key={tool.type} {...tool} />
          ))}
        </div>
      </div>

      {/* Page Management Section */}
      <div className="p-4 flex-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Páginas
        </h3>
        
        {/* Page Navigation */}
        <div className="flex items-center justify-between mb-4 p-1">
          <button 
            onClick={goToPrevPage}
            disabled={currentIndex === 0}
            className="page-nav-btn"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          
          <span className="text-sm font-medium">
            Página {pagina_actual} de {configuracion.num_paginas}
          </span>
          
          <button 
            onClick={goToNextPage}
            disabled={currentIndex === pageIds.length - 1}
            className="page-nav-btn"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Add Page Button */}
        <Button
          onClick={addPage}
          variant="outline"
          className="w-full mb-4"
        >
          <Plus className="w-4 h-4 mr-2" />
          Añadir Página
        </Button>

        {/* Orientation Toggle */}
        <h4 className="text-xs font-medium text-muted-foreground mb-2">Orientación</h4>
        <div className="flex gap-2">
          <button
            onClick={() => setPageOrientation(pagina_actual, 'portrait')}
            className={`orientation-btn flex-1 ${currentPage?.configuracion.orientacion === 'portrait' ? 'active' : ''}`}
          >
            <Smartphone className="w-5 h-5" />
          </button>
          <button
            onClick={() => setPageOrientation(pagina_actual, 'landscape')}
            className={`orientation-btn flex-1 ${currentPage?.configuracion.orientacion === 'landscape' ? 'active' : ''}`}
          >
            <MonitorSmartphone className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Page Thumbnails */}
      <div className="p-4 border-t border-border max-h-48 overflow-y-auto scrollbar-thin">
        <div className="grid grid-cols-3 gap-2">
          {pageIds.map((pageId) => (
            <button
              key={pageId}
              onClick={() => setCurrentPage(pageId)}
              className={`aspect-[3/4] rounded border-2 text-xs font-medium transition-all ${
                pageId === pagina_actual 
                  ? 'border-primary bg-primary/5 text-primary' 
                  : 'border-border bg-secondary hover:border-primary/50'
              }`}
            >
              {pageId}
            </button>
          ))}
        </div>
      </div>
    </motion.aside>
  );
};
