import { useTemplateStore } from '@/store/templateStore';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlignLeft,
  AlignCenter,
  AlignRight,
  Bold,
  Italic,
  Trash2,
  Layers,
  Settings2
} from 'lucide-react';
import { motion } from 'framer-motion';

const CM_TO_PX = 37.8;

/**
 * Read helpers that understand the canonical JSON format (Spanish field names)
 * with fallback to visual-editor names (English).
 */
function getBackgroundColor(estilo: any): string {
  return estilo.color_relleno || estilo.backgroundColor || '#ffffff';
}
function getBorderColor(estilo: any): string {
  return estilo.color_borde || estilo.borderColor || '#cbd5e1';
}
function getBorderWidth(estilo: any): number {
  return estilo.grosor_borde ?? estilo.borderWidth ?? 1;
}
function getOpacity(estilo: any): number {
  const raw = estilo.opacidad ?? estilo.opacity;
  if (raw == null) return 1;
  return raw > 1 ? raw / 100 : raw;
}
function getFontWeight(estilo: any): string {
  return estilo.negrita || estilo.fontWeight || 'normal';
}
function getFontStyle(estilo: any): string {
  return estilo.cursiva || estilo.fontStyle || 'normal';
}
function getTextAlign(estilo: any): string {
  return estilo.alineacion_h || estilo.textAlign || 'left';
}
function getTexto(element: any): string {
  return (element.contenido || {}).texto || '';
}
function getImageSrc(element: any): string {
  const img = element.imagen || {};
  const cont = element.contenido || {};
  return img.datos_temp || img.ruta_nueva || cont.src || '';
}

export const PropertiesPanel = () => {
  const {
    paginas,
    pagina_actual,
    selectedElementId,
    configuracion,
    updateElement,
    deleteElement,
    updateConfig
  } = useTemplateStore();

  const currentPage = paginas[pagina_actual];
  const selectedElement = selectedElementId
    ? currentPage?.elementos[selectedElementId]
    : null;

  // Safe accessors
  const estilo = (selectedElement as any)?.estilo || {};
  const contenido = (selectedElement as any)?.contenido || {};
  const metadata = (selectedElement as any)?.metadata || { zIndex: 0, visible: true };
  const geometria = (selectedElement as any)?.geometria || { x: 0, y: 0, ancho: 1, alto: 1 };

  const handleGeometryChange = (field: string, value: string) => {
    if (!selectedElement) return;
    const numValue = parseFloat(value) || 0;
    updateElement(pagina_actual, selectedElement.id, {
      geometria: { ...geometria, [field]: numValue }
    });
  };

  const handleStyleChange = (field: string, value: string | number) => {
    if (!selectedElement) return;
    updateElement(pagina_actual, selectedElement.id, {
      estilo: { ...estilo, [field]: value }
    });
  };

  const handleContentChange = (field: string, value: string) => {
    if (!selectedElement) return;
    updateElement(pagina_actual, selectedElement.id, {
      contenido: { ...contenido, [field]: value }
    });
  };

  const handleMetadataChange = (field: string, value: number | boolean | string) => {
    if (!selectedElement) return;
    updateElement(pagina_actual, selectedElement.id, {
      metadata: { ...metadata, [field]: value }
    });
  };

  const handleDelete = () => {
    if (!selectedElement) return;
    deleteElement(pagina_actual, selectedElement.id);
  };

  // Template settings view when no element is selected
  if (!selectedElement) {
    return (
      <motion.aside
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="w-72 bg-card border-l border-border p-4 overflow-y-auto scrollbar-thin"
      >
        <div className="flex items-center gap-2 mb-4">
          <Settings2 className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-semibold text-sm">Configuración de Plantilla</h3>
        </div>

        <div className="property-section">
          <div className="property-section-title">General</div>

          <div className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground mb-1.5 block">
                Nombre de la plantilla
              </Label>
              <Input
                value={configuracion.nombre_plantilla}
                onChange={(e) => updateConfig({ nombre_plantilla: e.target.value })}
                className="h-9"
              />
            </div>

            <div>
              <Label className="text-xs text-muted-foreground mb-1.5 block">
                Versión
              </Label>
              <Input
                value={configuracion.version || '1.0'}
                onChange={(e) => updateConfig({ version: e.target.value })}
                className="h-9"
              />
            </div>
          </div>
        </div>

        <div className="property-section">
          <div className="property-section-title">Estadísticas</div>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Páginas: {configuracion.num_paginas}</p>
            <p>Elementos en página actual: {Object.keys(currentPage?.elementos || {}).length}</p>
          </div>
        </div>

        <div className="mt-6 p-4 bg-accent/50 rounded-lg text-center">
          <p className="text-sm text-muted-foreground">
            Selecciona un elemento en el lienzo para editar sus propiedades
          </p>
        </div>
      </motion.aside>
    );
  }

  return (
    <motion.aside
      initial={{ x: 20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      key={selectedElement.id}
      className="w-72 bg-card border-l border-border p-4 overflow-y-auto scrollbar-thin"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-sm capitalize">{selectedElement.tipo}</h3>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDelete}
          className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      {/* Geometry Section */}
      <div className="property-section">
        <div className="property-section-title">Geometría (cm)</div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">X</Label>
            <Input
              type="number"
              step="0.1"
              value={(geometria.x || 0).toFixed(1)}
              onChange={(e) => handleGeometryChange('x', e.target.value)}
              className="h-8 text-sm"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Y</Label>
            <Input
              type="number"
              step="0.1"
              value={(geometria.y || 0).toFixed(1)}
              onChange={(e) => handleGeometryChange('y', e.target.value)}
              className="h-8 text-sm"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Ancho</Label>
            <Input
              type="number"
              step="0.1"
              value={(geometria.ancho || geometria.ancho_maximo || 1).toFixed(1)}
              onChange={(e) => handleGeometryChange('ancho', e.target.value)}
              className="h-8 text-sm"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Alto</Label>
            <Input
              type="number"
              step="0.1"
              value={(geometria.alto || geometria.alto_maximo || 1).toFixed(1)}
              onChange={(e) => handleGeometryChange('alto', e.target.value)}
              className="h-8 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Content Section - for text elements */}
      {selectedElement.tipo === 'texto' && (
        <div className="property-section">
          <div className="property-section-title">Contenido</div>
          <textarea
            value={getTexto(selectedElement)}
            onChange={(e) => handleContentChange('texto', e.target.value)}
            className="w-full h-24 px-3 py-2 text-sm border border-input rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Escribe tu texto..."
          />
        </div>
      )}

      {/* Image URL - for image elements */}
      {selectedElement.tipo === 'imagen' && (
        <div className="property-section">
          <div className="property-section-title">Fuente</div>
          <Input
            value={getImageSrc(selectedElement)}
            onChange={(e) => handleContentChange('src', e.target.value)}
            placeholder="URL de la imagen"
            className="h-8 text-sm"
          />
        </div>
      )}

      {/* Style Section */}
      <div className="property-section">
        <div className="property-section-title">Estilo</div>

        {/* Text styling */}
        {selectedElement.tipo === 'texto' && (
          <>
            <div className="mb-3">
              <Label className="text-xs text-muted-foreground mb-1.5 block">Tamaño</Label>
              <Input
                type="number"
                value={estilo.tamano || 14}
                onChange={(e) => handleStyleChange('tamano', parseInt(e.target.value))}
                className="h-8 text-sm"
              />
            </div>

            <div className="mb-3">
              <Label className="text-xs text-muted-foreground mb-1.5 block">Formato</Label>
              <div className="flex gap-1">
                <Button
                  variant={getFontWeight(estilo) === 'bold' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => handleStyleChange('negrita', getFontWeight(estilo) === 'bold' ? 'normal' : 'bold')}
                  className="h-8 w-8 p-0"
                >
                  <Bold className="w-4 h-4" />
                </Button>
                <Button
                  variant={getFontStyle(estilo) === 'italic' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => handleStyleChange('cursiva', getFontStyle(estilo) === 'italic' ? 'normal' : 'italic')}
                  className="h-8 w-8 p-0"
                >
                  <Italic className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="mb-3">
              <Label className="text-xs text-muted-foreground mb-1.5 block">Alineación</Label>
              <div className="flex gap-1">
                <Button
                  variant={getTextAlign(estilo) === 'left' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => handleStyleChange('alineacion_h', 'left')}
                  className="h-8 w-8 p-0"
                >
                  <AlignLeft className="w-4 h-4" />
                </Button>
                <Button
                  variant={getTextAlign(estilo) === 'center' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => handleStyleChange('alineacion_h', 'center')}
                  className="h-8 w-8 p-0"
                >
                  <AlignCenter className="w-4 h-4" />
                </Button>
                <Button
                  variant={getTextAlign(estilo) === 'right' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => handleStyleChange('alineacion_h', 'right')}
                  className="h-8 w-8 p-0"
                >
                  <AlignRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        )}

        {/* Colors */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div>
            <Label className="text-xs text-muted-foreground mb-1.5 block">Color</Label>
            <div className="flex gap-1">
              <input
                type="color"
                value={estilo.color || '#000000'}
                onChange={(e) => handleStyleChange('color', e.target.value)}
                className="w-8 h-8 rounded cursor-pointer border border-input"
              />
              <Input
                value={estilo.color || '#000000'}
                onChange={(e) => handleStyleChange('color', e.target.value)}
                className="h-8 text-xs flex-1"
              />
            </div>
          </div>

          {(selectedElement.tipo === 'rectangulo' || selectedElement.tipo === 'texto') && (
            <div>
              <Label className="text-xs text-muted-foreground mb-1.5 block">Fondo</Label>
              <div className="flex gap-1">
                <input
                  type="color"
                  value={getBackgroundColor(estilo)}
                  onChange={(e) => handleStyleChange('color_relleno', e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer border border-input"
                />
                <Input
                  value={getBackgroundColor(estilo)}
                  onChange={(e) => handleStyleChange('color_relleno', e.target.value)}
                  className="h-8 text-xs flex-1"
                />
              </div>
            </div>
          )}
        </div>

        {/* Border */}
        {(selectedElement.tipo === 'rectangulo' || selectedElement.tipo === 'linea') && (
          <div className="mb-3">
            <Label className="text-xs text-muted-foreground mb-1.5 block">Borde</Label>
            <div className="flex gap-2">
              <Input
                type="number"
                value={getBorderWidth(estilo)}
                onChange={(e) => handleStyleChange('grosor_borde', parseFloat(e.target.value))}
                className="h-8 text-sm w-16"
                min={0}
                step={0.5}
              />
              <input
                type="color"
                value={getBorderColor(estilo)}
                onChange={(e) => handleStyleChange('color_borde', e.target.value)}
                className="w-8 h-8 rounded cursor-pointer border border-input"
              />
            </div>
          </div>
        )}

        {/* Opacity */}
        <div className="mb-3">
          <Label className="text-xs text-muted-foreground mb-1.5 block">
            Opacidad: {Math.round(getOpacity(estilo) * 100)}%
          </Label>
          <Slider
            value={[getOpacity(estilo) * 100]}
            onValueChange={([value]) => handleStyleChange('opacidad', value)}
            max={100}
            step={1}
            className="mt-2"
          />
        </div>
      </div>

      {/* Metadata Section */}
      <div className="property-section">
        <div className="property-section-title">Capas y Grupos</div>

        <div className="mb-3">
          <Label className="text-xs text-muted-foreground mb-1.5 block">Z-Index</Label>
          <Input
            type="number"
            value={metadata.zIndex || 0}
            onChange={(e) => handleMetadataChange('zIndex', parseInt(e.target.value))}
            className="h-8 text-sm"
          />
        </div>

        <div>
          <Label className="text-xs text-muted-foreground mb-1.5 block">Grupo</Label>
          <Select
            value={metadata.grupo || 'ninguno'}
            onValueChange={(value) => handleMetadataChange('grupo', value === 'ninguno' ? '' : value)}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ninguno">Ninguno</SelectItem>
              <SelectItem value="encabezado">Encabezado</SelectItem>
              <SelectItem value="cuerpo">Cuerpo</SelectItem>
              <SelectItem value="pie">Pie de página</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </motion.aside>
  );
};
