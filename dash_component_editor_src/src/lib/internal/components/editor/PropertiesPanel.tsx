import { useRef, useCallback } from 'react';
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
  Settings2,
  Ban,
  Upload,
  ImageIcon,
  Link,
  RatioIcon,
  X
} from 'lucide-react';
import { motion } from 'framer-motion';

/** Color input with transparent toggle */
const ColorInput = ({
  label,
  value,
  fallback,
  onChange,
}: {
  label: string;
  value: string;
  fallback: string;
  onChange: (v: string) => void;
}) => {
  const isTransparent = value === 'transparent';
  const displayColor = isTransparent ? fallback : value;

  return (
    <div>
      <Label className="text-xs text-muted-foreground mb-1.5 block">{label}</Label>
      <div className="flex gap-1 items-center">
        {isTransparent ? (
          <button
            type="button"
            onClick={() => onChange(fallback)}
            className="w-8 h-8 rounded border border-input flex items-center justify-center shrink-0"
            style={{
              backgroundImage: 'linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)',
              backgroundSize: '8px 8px',
              backgroundPosition: '0 0, 0 4px, 4px -4px, -4px 0',
            }}
            title="Sin color – clic para asignar color"
          />
        ) : (
          <input
            type="color"
            value={displayColor}
            onChange={(e) => onChange(e.target.value)}
            className="w-8 h-8 rounded cursor-pointer border border-input shrink-0"
          />
        )}
        <Input
          value={isTransparent ? 'transparent' : value}
          onChange={(e) => onChange(e.target.value)}
          className="h-8 text-xs flex-1 min-w-0"
          placeholder={fallback}
        />
        <Button
          variant={isTransparent ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => onChange(isTransparent ? fallback : 'transparent')}
          className="h-8 w-8 p-0 shrink-0"
          title={isTransparent ? 'Restaurar color' : 'Sin color (transparente)'}
        >
          <Ban className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  );
};

/** Extracts format from a data URI (e.g. "data:image/png;base64,..." → "png") */
function formatFromDataUri(dataUri: string): string {
  const match = dataUri.match(/^data:image\/(\w+)/);
  return match ? match[1] : 'png';
}

/** Full image properties panel with upload, URL, preview and aspect ratio */
const ImageSection = ({
  element,
  pageId,
  updateElement,
}: {
  element: any;
  pageId: string;
  updateElement: (pageId: string, elementId: string, updates: any) => void;
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const imgSrc = getImageSrc(element);
  const estilo = element.estilo || {};
  const mantenerProporcion = estilo.mantener_proporcion ?? true;

  /** Store image data in both contenido.src and imagen.* for compatibility */
  const setImageData = useCallback((dataUri: string, fileName?: string) => {
    const formato = formatFromDataUri(dataUri);
    const nombre = fileName || `${element.id}.${formato}`;
    updateElement(pageId, element.id, {
      contenido: { ...(element.contenido || {}), src: dataUri },
      imagen: {
        formato,
        datos_temp: dataUri,
        nombre_archivo: nombre,
        ruta_nueva: `assets/${nombre}`,
        estado: 'nueva',
      },
    });
  }, [element, pageId, updateElement]);

  /** Handle file selection via input or drop */
  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUri = reader.result as string;
      setImageData(dataUri, file.name);
    };
    reader.readAsDataURL(file);
  }, [setImageData]);

  /** Handle URL input: if it looks like a URL, set it directly */
  const handleUrlSet = useCallback((url: string) => {
    updateElement(pageId, element.id, {
      contenido: { ...(element.contenido || {}), src: url },
      imagen: {
        ...(element.imagen || {}),
        ruta_nueva: url,
        estado: url ? 'url' : 'faltante',
      },
    });
  }, [element, pageId, updateElement]);

  const handleClear = useCallback(() => {
    updateElement(pageId, element.id, {
      contenido: { ...(element.contenido || {}), src: '' },
      imagen: { datos_temp: '', ruta_nueva: '', nombre_archivo: '', estado: 'faltante' },
    });
  }, [element, pageId, updateElement]);

  const handleStyleChange = useCallback((field: string, value: any) => {
    updateElement(pageId, element.id, {
      estilo: { ...estilo, [field]: value },
    });
  }, [element, estilo, pageId, updateElement]);

  // Drag-and-drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('image-drop-active');
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove('image-drop-active');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('image-drop-active');
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div className="property-section">
      <div className="property-section-title">Imagen</div>

      {/* Preview / Upload zone */}
      <div
        ref={dropZoneRef}
        className="image-upload-zone mb-3"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !imgSrc && fileInputRef.current?.click()}
      >
        {imgSrc ? (
          <div className="relative w-full">
            <img
              src={imgSrc}
              alt="Vista previa"
              className="w-full rounded"
              style={{
                maxHeight: 140,
                objectFit: mantenerProporcion ? 'contain' : 'fill',
              }}
            />
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); handleClear(); }}
              className="absolute top-1 right-1 w-5 h-5 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center hover:opacity-80"
              title="Eliminar imagen"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1.5 py-3 text-muted-foreground">
            <ImageIcon className="w-8 h-8 opacity-40" />
            <span className="text-xs">Arrastra una imagen o haz clic</span>
          </div>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = '';
        }}
      />

      {/* Buttons: upload file + paste URL */}
      <div className="flex gap-1.5 mb-3">
        <Button
          variant="secondary"
          size="sm"
          className="flex-1 h-8 text-xs gap-1.5"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-3.5 h-3.5" />
          Subir archivo
        </Button>
      </div>

      {/* URL input */}
      <div className="mb-3">
        <Label className="text-xs text-muted-foreground mb-1.5 block">
          <Link className="w-3 h-3 inline mr-1" />
          URL de imagen
        </Label>
        <Input
          value={(!imgSrc?.startsWith('data:') && imgSrc) || ''}
          onChange={(e) => handleUrlSet(e.target.value)}
          placeholder="https://..."
          className="h-8 text-xs"
        />
      </div>

      {/* Aspect ratio toggle */}
      <div className="flex items-center justify-between">
        <Label className="text-xs text-muted-foreground flex items-center gap-1.5">
          <RatioIcon className="w-3.5 h-3.5" />
          Mantener proporción
        </Label>
        <button
          type="button"
          role="switch"
          aria-checked={mantenerProporcion}
          onClick={() => handleStyleChange('mantener_proporcion', !mantenerProporcion)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            mantenerProporcion ? 'bg-primary' : 'bg-muted'
          }`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
              mantenerProporcion ? 'translate-x-4' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>
    </div>
  );
};

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

      {/* Image section - for image elements */}
      {selectedElement.tipo === 'imagen' && (
        <ImageSection
          element={selectedElement}
          pageId={pagina_actual}
          updateElement={updateElement}
        />
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
        <div className="space-y-3 mb-3">
          <ColorInput
            label="Color"
            value={estilo.color || '#000000'}
            fallback="#000000"
            onChange={(v) => handleStyleChange('color', v)}
          />

          {(selectedElement.tipo === 'rectangulo' || selectedElement.tipo === 'texto') && (
            <ColorInput
              label="Fondo"
              value={getBackgroundColor(estilo)}
              fallback={selectedElement.tipo === 'rectangulo' ? '#e2e8f0' : '#ffffff'}
              onChange={(v) => handleStyleChange('color_relleno', v)}
            />
          )}
        </div>

        {/* Border */}
        {(selectedElement.tipo === 'rectangulo' || selectedElement.tipo === 'linea') && (
          <div className="mb-3">
            <Label className="text-xs text-muted-foreground mb-1.5 block">Borde</Label>
            <div className="flex gap-2 items-center">
              <Input
                type="number"
                value={getBorderWidth(estilo)}
                onChange={(e) => handleStyleChange('grosor_borde', parseFloat(e.target.value))}
                className="h-8 text-sm w-16"
                min={0}
                step={0.5}
              />
              <div className="flex-1">
                <ColorInput
                  label=""
                  value={getBorderColor(estilo)}
                  fallback="#cbd5e1"
                  onChange={(v) => handleStyleChange('color_borde', v)}
                />
              </div>
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
