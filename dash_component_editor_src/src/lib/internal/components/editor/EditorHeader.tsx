import { useState } from 'react';
import { FileText, Braces } from 'lucide-react';
import { useTemplateStore } from '@/store/templateStore';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';

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

        <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded-md">
          v{configuracion.version || '1.0'}
        </span>
      </div>

      {/* Right-side actions */}
      <div className="flex items-center gap-1">
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
