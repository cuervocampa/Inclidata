import { useState } from 'react';
import { FileText } from 'lucide-react';
import { useTemplateStore } from '@/store/templateStore';
import { Input } from '@/components/ui/input';
import { motion } from 'framer-motion';

export const EditorHeader = () => {
  const { configuracion, updateConfig } = useTemplateStore();
  const [isEditing, setIsEditing] = useState(false);

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="h-12 bg-card border-b border-border flex items-center px-6"
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

        <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded-md">
          v{configuracion.version || '1.0'}
        </span>
      </div>
    </motion.header>
  );
};
