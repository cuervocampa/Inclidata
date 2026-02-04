import { useState } from 'react';
import { Save, Upload, FileDown, FileText } from 'lucide-react';
import { useTemplateStore } from '@/store/templateStore';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { motion } from 'framer-motion';

export const EditorHeader = () => {
  const { configuracion, updateConfig, exportJSON, loadTemplate } = useTemplateStore();
  const [isEditing, setIsEditing] = useState(false);

  const handleSave = () => {
    const json = exportJSON();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${configuracion.nombre_plantilla.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Plantilla guardada exitosamente');
  };

  const handleLoad = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const template = JSON.parse(event.target?.result as string);
            loadTemplate(template);
            toast.success('Plantilla cargada exitosamente');
          } catch {
            toast.error('Error al cargar la plantilla');
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  const handleGeneratePDF = () => {
    toast.info('Generación de PDF - Funcionalidad próximamente');
  };

  return (
    <motion.header 
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="h-16 bg-card border-b border-border flex items-center justify-between px-6"
    >
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <FileText className="w-5 h-5 text-primary" />
        </div>
        
        {isEditing ? (
          <Input
            value={configuracion.nombre_plantilla}
            onChange={(e) => updateConfig({ nombre_plantilla: e.target.value })}
            onBlur={() => setIsEditing(false)}
            onKeyDown={(e) => e.key === 'Enter' && setIsEditing(false)}
            className="w-64 h-9 text-lg font-semibold"
            autoFocus
          />
        ) : (
          <button 
            onClick={() => setIsEditing(true)}
            className="text-lg font-semibold text-foreground hover:text-primary transition-colors"
          >
            {configuracion.nombre_plantilla}
          </button>
        )}
        
        <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded-md">
          v{configuracion.version || '1.0'}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLoad}
          className="header-btn header-btn-secondary"
        >
          <Upload className="w-4 h-4 mr-2" />
          Cargar
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={handleSave}
          className="header-btn header-btn-secondary"
        >
          <Save className="w-4 h-4 mr-2" />
          Guardar
        </Button>
        
        <Button
          onClick={handleGeneratePDF}
          className="header-btn header-btn-primary"
        >
          <FileDown className="w-4 h-4 mr-2" />
          Generar PDF
        </Button>
      </div>
    </motion.header>
  );
};
