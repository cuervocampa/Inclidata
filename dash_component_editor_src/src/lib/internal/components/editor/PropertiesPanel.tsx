import { useRef, useCallback, useState, useEffect } from 'react';
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
  X,
  Group,
  Package,
  BarChart3,
  Table2,
  Plus,
  Minus,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react';
import type { GridLevel, GridColumn, ColumnBorders, Cuadricula } from '@/store/templateStore';
import { motion } from 'framer-motion';

/**
 * Controlled numeric input with local state.
 * Handles both typing (allows empty field while editing) and spinner arrows.
 * Commits valid values to the store on change and onBlur.
 */
const NumericField = ({
  value: propValue,
  onChange: commitValue,
  min,
  max,
  step,
  className,
  syncKey,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  className?: string;
  syncKey?: string;
}) => {
  const [localValue, setLocalValue] = useState(String(propValue));

  // Sync local state when the store value changes externally
  useEffect(() => {
    setLocalValue(String(propValue));
  }, [propValue, syncKey]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    setLocalValue(raw);
    // Commit immediately if it parses to a valid number (handles spinner arrows)
    const parsed = parseFloat(raw);
    if (!isNaN(parsed) && (min === undefined || parsed >= min)) {
      commitValue(parsed);
    }
  };

  const handleBlur = () => {
    const parsed = parseFloat(localValue);
    if (!isNaN(parsed) && (min === undefined || parsed >= min)) {
      commitValue(parsed);
      setLocalValue(String(parsed));
    } else {
      // Revert to prop value if invalid
      setLocalValue(String(propValue));
    }
  };

  return (
    <Input
      type="number"
      min={min}
      max={max}
      step={step}
      value={localValue}
      onChange={handleChange}
      onBlur={handleBlur}
      className={className}
    />
  );
};

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

/** JSON textarea for graph parametros — local state, commits on blur */
const ParamsTextarea = ({
  params,
  elementId,
  onChange,
}: {
  params: Record<string, unknown>;
  elementId: string;
  onChange: (params: Record<string, unknown>) => void;
}) => {
  const toText = (p: Record<string, unknown>) => {
    if (!p || Object.keys(p).length === 0) return '';
    try {
      const s = JSON.stringify(p, null, 2);
      return s.slice(1, -1).trim();
    } catch {
      return '';
    }
  };

  const [text, setText] = useState(toText(params));
  const [error, setError] = useState('');

  // Reset when a different element is selected
  useEffect(() => {
    setText(toText(params));
    setError('');
  }, [elementId]);

  const handleBlur = () => {
    const raw = text.trim();
    if (!raw) { onChange({}); setError(''); return; }
    try {
      const parsed = JSON.parse('{' + raw + '}');
      onChange(parsed);
      setError('');
    } catch (e) {
      setError('JSON inválido: ' + (e as Error).message);
    }
  };

  return (
    <div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={handleBlur}
        rows={6}
        placeholder={'"sensor": "$CURRENT",\n"mostrar_titulo": true,\n"dpi": 600'}
        className="w-full font-mono text-[11px] p-2 border border-border rounded-md bg-background resize-y focus:outline-none focus:ring-1 focus:ring-primary"
      />
      {error && <p className="text-[10px] text-red-500 mt-1">{error}</p>}
    </div>
  );
};

/** Chart configuration panel */
const ChartSection = ({
  element,
  pageId,
  updateElement,
  chartScripts,
}: {
  element: any;
  pageId: string;
  updateElement: (pageId: string, elementId: string, updates: any) => void;
  chartScripts: string[];
}) => {
  const config = element.configuracion || { script: '', formato: 'svg', parametros: {} };

  const handleConfigChange = useCallback((field: string, value: any) => {
    updateElement(pageId, element.id, {
      configuracion: { ...config, [field]: value },
    });
  }, [element, config, pageId, updateElement]);

  return (
    <div className="property-section">
      <div className="property-section-title">
        <BarChart3 className="w-3.5 h-3.5 inline mr-1" />
        Configuración de Gráfico
      </div>

      {/* Script selector */}
      <div className="mb-3">
        <Label className="text-xs text-muted-foreground mb-1.5 block">Script</Label>
        <Select
          value={config.script || '__none__'}
          onValueChange={(v) => handleConfigChange('script', v === '__none__' ? '' : v)}
        >
          <SelectTrigger className="h-8">
            <SelectValue placeholder="Seleccionar script..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">Sin script</SelectItem>
            {chartScripts.map((s) => (
              <SelectItem key={s} value={s}>{s.replace('.py', '')}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Format selector */}
      <div className="mb-3">
        <Label className="text-xs text-muted-foreground mb-1.5 block">Formato</Label>
        <Select
          value={config.formato || 'svg'}
          onValueChange={(v) => handleConfigChange('formato', v)}
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="svg">SVG</SelectItem>
            <SelectItem value="png">PNG</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Parameters textarea */}
      <div className="mb-2">
        <Label className="text-xs text-muted-foreground mb-1.5 block">Parámetros JSON</Label>
        <ParamsTextarea
          params={config.parametros || {}}
          elementId={element.id}
          onChange={(params) => handleConfigChange('parametros', params)}
        />
      </div>

      {/* Token reference — collapsed by default */}
      <details className="group mb-1">
        <summary className="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground hover:text-foreground select-none py-1">
          <Info className="w-3.5 h-3.5" />
          <span>Tokens disponibles</span>
        </summary>
        <div className="mt-1 p-2 bg-muted/50 border border-border rounded-md text-[10px] text-muted-foreground space-y-0.5">
          <p><code className="bg-muted px-0.5 rounded">$CURRENT</code> → sensor activo</p>
          <p><code className="bg-muted px-0.5 rounded">$CURRENT_fecha_seleccionada</code> → fecha de corte</p>
          <p><code className="bg-muted px-0.5 rounded">$CURRENT_fecha_inicial</code> / <code className="bg-muted px-0.5 rounded">$CURRENT_fecha_final</code></p>
          <p><code className="bg-muted px-0.5 rounded">$CURRENT_ultimas_camp</code> → n.º campañas</p>
        </div>
      </details>
    </div>
  );
};

/** ── Border preset helpers ── */
const BORDER_PRESETS: Record<string, (g: number, c: string) => ColumnBorders> = {
  ninguno: () => ({
    superior: { activo: false, grosor: 1, color: '#000000' },
    inferior: { activo: false, grosor: 1, color: '#000000' },
    izquierdo: { activo: false, grosor: 1, color: '#000000' },
    derecho: { activo: false, grosor: 1, color: '#000000' },
  }),
  todos: (g, c) => ({
    superior: { activo: true, grosor: g, color: c },
    inferior: { activo: true, grosor: g, color: c },
    izquierdo: { activo: true, grosor: g, color: c },
    derecho: { activo: true, grosor: g, color: c },
  }),
  externos: (g, c) => ({
    superior: { activo: true, grosor: g, color: c },
    inferior: { activo: true, grosor: g, color: c },
    izquierdo: { activo: true, grosor: g, color: c },
    derecho: { activo: true, grosor: g, color: c },
  }),
  inferior: (g, c) => ({
    superior: { activo: false, grosor: g, color: c },
    inferior: { activo: true, grosor: g, color: c },
    izquierdo: { activo: false, grosor: g, color: c },
    derecho: { activo: false, grosor: g, color: c },
  }),
  superior: (g, c) => ({
    superior: { activo: true, grosor: g, color: c },
    inferior: { activo: false, grosor: g, color: c },
    izquierdo: { activo: false, grosor: g, color: c },
    derecho: { activo: false, grosor: g, color: c },
  }),
  horizontal: (g, c) => ({
    superior: { activo: true, grosor: g, color: c },
    inferior: { activo: true, grosor: g, color: c },
    izquierdo: { activo: false, grosor: g, color: c },
    derecho: { activo: false, grosor: g, color: c },
  }),
  vertical: (g, c) => ({
    superior: { activo: false, grosor: g, color: c },
    inferior: { activo: false, grosor: g, color: c },
    izquierdo: { activo: true, grosor: g, color: c },
    derecho: { activo: true, grosor: g, color: c },
  }),
};

function detectBorderPreset(bordes: ColumnBorders): string {
  if (!bordes) return 'ninguno';
  const s = bordes.superior?.activo;
  const i = bordes.inferior?.activo;
  const iz = bordes.izquierdo?.activo;
  const d = bordes.derecho?.activo;
  if (!s && !i && !iz && !d) return 'ninguno';
  if (s && i && iz && d) return 'todos';
  if (s && i && !iz && !d) return 'horizontal';
  if (!s && !i && iz && d) return 'vertical';
  if (!s && i && !iz && !d) return 'inferior';
  if (s && !i && !iz && !d) return 'superior';
  return 'todos';
}

const FONT_OPTIONS = ['Aptos', 'Arial', 'Helvetica', 'Times New Roman', 'Courier'];

function makeDefaultColumn(anchoPct: number, index: number): GridColumn {
  return {
    ancho: anchoPct,
    contenido: `Col ${index}`,
    formato: { fuente: 'Aptos', tamano: 10, color_texto: '#000000', color_fondo: '#ffffff', alineacion: 'left', negrita: false },
    bordes: BORDER_PRESETS.todos(1, '#000000'),
  };
}

function makeDefaultLevel(id: number, tipo: 'estatico' | 'autorrelleno'): GridLevel {
  const level: GridLevel = {
    id, tipo, num_columnas: 3, alto_fila: 0.5,
    estilo: { fuente: 'Aptos', tamano: 10 },
    columnas: [makeDefaultColumn(33.33, 1), makeDefaultColumn(33.33, 2), makeDefaultColumn(33.34, 3)],
  };
  if (tipo === 'autorrelleno') {
    level.configuracion_dinamica = { sombreado_alterno: false, color_par: '#ffffff', color_impar: '#f0f0f0' };
  }
  return level;
}

/** Table configuration panel */
const TableSection = ({
  element,
  pageId,
  updateElement,
  tableScripts,
}: {
  element: any;
  pageId: string;
  updateElement: (pageId: string, elementId: string, updates: any) => void;
  tableScripts: string[];
}) => {
  const config = element.configuracion || { script: '', formato: 'svg', parametros: {} };
  const cuadricula: Cuadricula = element.cuadricula || { niveles: [] };
  const niveles = cuadricula.niveles || [];

  const [expandedLevel, setExpandedLevel] = useState<number | null>(niveles.length > 0 ? niveles[0].id : null);

  const handleConfigChange = useCallback((field: string, value: any) => {
    updateElement(pageId, element.id, {
      configuracion: { ...config, [field]: value },
    });
  }, [element, config, pageId, updateElement]);

  /** Always read fresh niveles from the store to avoid stale closures */
  const getFreshNiveles = useCallback((): GridLevel[] => {
    const state = useTemplateStore.getState();
    const el = state.paginas[pageId]?.elementos[element.id];
    return el?.cuadricula?.niveles || [];
  }, [pageId, element.id]);

  const setNiveles = useCallback((newNiveles: GridLevel[]) => {
    updateElement(pageId, element.id, { cuadricula: { niveles: newNiveles } });
  }, [element.id, pageId, updateElement]);

  const updateLevel = useCallback((levelId: number, patch: Partial<GridLevel>) => {
    const fresh = getFreshNiveles();
    setNiveles(fresh.map(n => n.id === levelId ? { ...n, ...patch } : n));
  }, [getFreshNiveles, setNiveles]);

  const updateColumn = useCallback((levelId: number, colIdx: number, patch: Partial<GridColumn>) => {
    const fresh = getFreshNiveles();
    setNiveles(fresh.map(n => {
      if (n.id !== levelId) return n;
      const newCols = n.columnas.map((c, i) => i === colIdx ? { ...c, ...patch } : c);
      return { ...n, columnas: newCols };
    }));
  }, [getFreshNiveles, setNiveles]);

  const addLevel = useCallback((tipo: 'estatico' | 'autorrelleno') => {
    const fresh = getFreshNiveles();
    const maxId = fresh.reduce((m, n) => Math.max(m, n.id), 0);
    const newLevel = makeDefaultLevel(maxId + 1, tipo);
    setNiveles([...fresh, newLevel]);
    setExpandedLevel(newLevel.id);
  }, [getFreshNiveles, setNiveles]);

  const removeLastLevel = useCallback(() => {
    const fresh = getFreshNiveles();
    if (fresh.length === 0) return;
    const newNiveles = fresh.slice(0, -1);
    setNiveles(newNiveles);
    if (expandedLevel === fresh[fresh.length - 1].id) {
      setExpandedLevel(newNiveles.length > 0 ? newNiveles[newNiveles.length - 1].id : null);
    }
  }, [getFreshNiveles, setNiveles, expandedLevel]);

  const handleNumColumnsChange = useCallback((levelId: number, newCount: number) => {
    const fresh = getFreshNiveles();
    const level = fresh.find(n => n.id === levelId);
    if (!level) return;
    const current = level.columnas.length;
    let newCols = [...level.columnas];
    if (newCount > current) {
      // Repartir el espacio libre entre las nuevas columnas
      const usedPct = newCols.reduce((s, c) => s + c.ancho, 0);
      const freePct = Math.max(0, 100 - usedPct);
      const toAdd = newCount - current;
      const eachNew = toAdd > 0 ? Math.round((freePct / toAdd) * 100) / 100 : 10;
      for (let i = current; i < newCount; i++) {
        newCols.push(makeDefaultColumn(Math.max(1, eachNew), i + 1));
      }
    } else {
      // Simplemente quitar las últimas, sin redistribuir
      newCols = newCols.slice(0, newCount);
    }
    setNiveles(fresh.map(n => n.id === levelId ? { ...n, num_columnas: newCount, columnas: newCols } : n));
  }, [getFreshNiveles, setNiveles]);

  return (
    <div className="property-section">
      <div className="property-section-title">
        <Table2 className="w-3.5 h-3.5 inline mr-1" />
        Configuración de Tabla
      </div>

      {/* ── Script selector ── */}
      <div className="mb-3">
        <Label className="text-xs text-muted-foreground mb-1.5 block">Script</Label>
        <Select
          value={config.script || '__none__'}
          onValueChange={(v) => handleConfigChange('script', v === '__none__' ? '' : v)}
        >
          <SelectTrigger className="h-8">
            <SelectValue placeholder="Seleccionar script..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">Sin script</SelectItem>
            {tableScripts.map((s) => (
              <SelectItem key={s} value={s}>{s.replace('.py', '')}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* ── Parameter & cell content help ── */}
      <details className="group mb-3">
        <summary className="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground hover:text-foreground select-none py-1">
          <Info className="w-3.5 h-3.5" />
          <span>Ayuda: parámetros y contenido de celdas</span>
        </summary>
        <div className="mt-1.5 p-2.5 bg-muted/50 border border-border rounded-md text-[10px] text-muted-foreground leading-relaxed space-y-2">
          <p>
            Los parámetros se almacenan en el JSON del elemento
            (<strong>Inspector JSON → Elemento</strong>).
          </p>
          <div>
            <p className="font-semibold text-foreground/70 mb-0.5">Contenido de celdas por tipo de nivel:</p>
            <ul className="list-none space-y-0.5 ml-1">
              <li><span className="inline-block px-1 py-0.5 rounded text-[9px] font-bold bg-blue-100 text-blue-700 mr-1">E</span> Estático: texto fijo → <code className="bg-muted px-0.5 rounded">Prof.</code>, <code className="bg-muted px-0.5 rounded">A</code>, <code className="bg-muted px-0.5 rounded">B</code></li>
              <li><span className="inline-block px-1 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-700 mr-1">D</span> Dinámico: <code className="bg-muted px-0.5 rounded">[campo]</code> → datos del script</li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-foreground/70 mb-0.5">Campos dinámicos comunes:</p>
            <ul className="list-none space-y-0.5 ml-1">
              <li><code className="bg-muted px-0.5 rounded">[prof]</code> → profundidad</li>
              <li><code className="bg-muted px-0.5 rounded">[desp_a]</code> / <code className="bg-muted px-0.5 rounded">[desp_b]</code> → desplazamiento eje A/B</li>
              <li><code className="bg-muted px-0.5 rounded">fecha_1</code>, <code className="bg-muted px-0.5 rounded">fecha_2</code>… → reemplazados por fechas reales</li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-foreground/70 mb-0.5">Valores dinámicos (desde Graficar):</p>
            <ul className="list-none space-y-0.5 ml-1">
              <li><code className="bg-muted px-0.5 rounded">$CURRENT</code> → sensor activo</li>
              <li><code className="bg-muted px-0.5 rounded">$CURRENT_fecha_seleccionada</code> → fecha de corte</li>
              <li><code className="bg-muted px-0.5 rounded">$CURRENT_ultimas_camp</code> → n.º campañas</li>
            </ul>
          </div>
          <div className="font-mono bg-background/80 rounded p-1.5 border border-border/50 text-[9px] leading-snug">
            <div className="text-foreground/50 mb-0.5">{'// Ejemplo: nivel estático'}</div>
            <div>Col 1: <strong>Prof.</strong> | Col 2: <strong>A</strong> | Col 3: <strong>B</strong></div>
            <div className="text-foreground/50 mt-1 mb-0.5">{'// Ejemplo: nivel dinámico'}</div>
            <div>Col 1: <strong>[prof]</strong> | Col 2: <strong>[desp_a]</strong> | Col 3: <strong>[desp_b]</strong></div>
          </div>
        </div>
      </details>

      {/* ── Level management ── */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-2">
          <Label className="text-xs text-muted-foreground">
            Niveles <span className="ml-1 px-1.5 py-0.5 bg-primary/10 text-primary rounded text-[10px] font-medium">{niveles.length}</span>
          </Label>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" className="h-6 text-[10px] px-2 gap-1" onClick={() => addLevel('estatico')}>
              <Plus className="w-3 h-3" /> Estático
            </Button>
            <Button variant="outline" size="sm" className="h-6 text-[10px] px-2 gap-1" onClick={() => addLevel('autorrelleno')}>
              <Plus className="w-3 h-3" /> Dinámico
            </Button>
            {niveles.length > 0 && (
              <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 gap-1 text-destructive" onClick={removeLastLevel}>
                <Minus className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* ── Accordion of levels ── */}
      {niveles.map((nivel) => {
        const isExpanded = expandedLevel === nivel.id;
        return (
          <div key={nivel.id} className="mb-2 border border-border rounded-md overflow-hidden">
            {/* Header */}
            <button
              type="button"
              className="w-full flex items-center gap-2 px-2 py-1.5 bg-muted/50 hover:bg-muted text-xs font-medium"
              onClick={() => setExpandedLevel(isExpanded ? null : nivel.id)}
            >
              {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              <span className={`px-1 py-0.5 rounded text-[9px] font-bold ${nivel.tipo === 'estatico' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                {nivel.tipo === 'estatico' ? 'E' : 'D'}
              </span>
              <span>Nivel {nivel.id}</span>
              <span className="text-muted-foreground ml-auto">{nivel.num_columnas} cols</span>
            </button>

            {isExpanded && (
              <div className="p-2 space-y-2">
                {/* Level settings */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-[10px] text-muted-foreground">Columnas</Label>
                    <Input type="number" min={1} max={20} value={nivel.num_columnas}
                      onChange={(e) => handleNumColumnsChange(nivel.id, Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                      className="h-7 text-xs" />
                  </div>
                  <div>
                    <Label className="text-[10px] text-muted-foreground">Alto fila (cm)</Label>
                    <NumericField
                      value={nivel.alto_fila}
                      onChange={(v) => updateLevel(nivel.id, { alto_fila: v })}
                      min={0.3} max={3} step={0.1}
                      syncKey={`af-${element.id}-${nivel.id}`}
                      className="h-7 text-xs" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-[10px] text-muted-foreground">Fuente</Label>
                    <Select value={nivel.estilo?.fuente || 'Aptos'}
                      onValueChange={(v) => updateLevel(nivel.id, { estilo: { ...nivel.estilo, fuente: v } })}>
                      <SelectTrigger className="h-7 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {FONT_OPTIONS.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-[10px] text-muted-foreground">Tamaño</Label>
                    <NumericField
                      value={nivel.estilo?.tamano || 10}
                      onChange={(v) => updateLevel(nivel.id, { estilo: { ...nivel.estilo, tamano: Math.round(v) } })}
                      min={6} max={72} step={1}
                      syncKey={`ts-${element.id}-${nivel.id}`}
                      className="h-7 text-xs" />
                  </div>
                </div>

                {/* Dynamic config (autorrelleno only) */}
                {nivel.tipo === 'autorrelleno' && (
                  <div className="p-2 bg-amber-50 rounded border border-amber-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-[10px] text-muted-foreground">Sombreado alterno</Label>
                      <button type="button" role="switch"
                        aria-checked={nivel.configuracion_dinamica?.sombreado_alterno ?? false}
                        onClick={() => updateLevel(nivel.id, {
                          configuracion_dinamica: {
                            ...(nivel.configuracion_dinamica || { sombreado_alterno: false, color_par: '#ffffff', color_impar: '#f0f0f0' }),
                            sombreado_alterno: !(nivel.configuracion_dinamica?.sombreado_alterno)
                          }
                        })}
                        className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${nivel.configuracion_dinamica?.sombreado_alterno ? 'bg-primary' : 'bg-muted'}`}>
                        <span className={`inline-block h-3 w-3 rounded-full bg-white transition-transform ${nivel.configuracion_dinamica?.sombreado_alterno ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                      </button>
                    </div>
                    {nivel.configuracion_dinamica?.sombreado_alterno && (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label className="text-[10px] text-muted-foreground">Color par</Label>
                          <input type="color" value={nivel.configuracion_dinamica.color_par || '#ffffff'}
                            onChange={(e) => updateLevel(nivel.id, {
                              configuracion_dinamica: { ...nivel.configuracion_dinamica!, color_par: e.target.value }
                            })}
                            className="w-full h-6 rounded cursor-pointer border border-input" />
                        </div>
                        <div>
                          <Label className="text-[10px] text-muted-foreground">Color impar</Label>
                          <input type="color" value={nivel.configuracion_dinamica.color_impar || '#f0f0f0'}
                            onChange={(e) => updateLevel(nivel.id, {
                              configuracion_dinamica: { ...nivel.configuracion_dinamica!, color_impar: e.target.value }
                            })}
                            className="w-full h-6 rounded cursor-pointer border border-input" />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ── Column config ── */}
                <div className="space-y-1.5">
                  {(() => {
                    const totalPct = nivel.columnas.reduce((s, c) => s + (c.ancho || 0), 0);
                    const exceeds = totalPct > 100.01;
                    return (
                      <>
                        <div className="flex items-center justify-between">
                          <Label className="text-[10px] text-muted-foreground font-medium">Columnas</Label>
                          <span className={`text-xs font-mono ${exceeds ? 'text-red-600 font-bold' : 'text-muted-foreground'}`}>
                            {totalPct.toFixed(1)}%
                          </span>
                        </div>
                        {exceeds && (
                          <div className="flex items-center gap-1.5 px-2 py-1.5 bg-red-50 border border-red-300 rounded text-red-700 text-xs">
                            <span className="text-base">⚠</span>
                            <span>El ancho total excede el 100% ({(totalPct - 100).toFixed(1)}% de más)</span>
                          </div>
                        )}
                      </>
                    );
                  })()}
                  {nivel.columnas.map((col, colIdx) => (
                    <div key={colIdx} className="p-1.5 bg-muted/30 rounded border border-border/50 space-y-1.5">
                      <div className="text-[10px] font-medium text-muted-foreground">Col {colIdx + 1}</div>
                      <div className="grid grid-cols-2 gap-1.5">
                        <div>
                          <Label className="text-[9px] text-muted-foreground">Ancho (%)</Label>
                          <Input type="number" step={1} min={1} max={100}
                            value={col.ancho}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value) || 1;
                              // Calcular máximo permitido: 100 - suma de las demás columnas
                              const otrasSum = nivel.columnas.reduce((s, c, i) => i === colIdx ? s : s + c.ancho, 0);
                              const maxAllowed = Math.round((100 - otrasSum) * 100) / 100;
                              updateColumn(nivel.id, colIdx, { ancho: Math.min(val, Math.max(1, maxAllowed)) });
                            }}
                            className="h-6 text-[10px]" />
                        </div>
                        <div>
                          <Label className="text-[9px] text-muted-foreground">Contenido</Label>
                          <Input
                            defaultValue={col.contenido}
                            key={`ct-${element.id}-${nivel.id}-${colIdx}`}
                            onBlur={(e) => updateColumn(nivel.id, colIdx, { contenido: e.target.value })}
                            className="h-6 text-[10px]" />
                        </div>
                      </div>
                      {/* Format row */}
                      <div className="flex items-center gap-1">
                        <Button variant={col.formato?.negrita ? 'secondary' : 'ghost'} size="sm" className="h-5 w-5 p-0"
                          onClick={() => updateColumn(nivel.id, colIdx, { formato: { ...col.formato, negrita: !col.formato?.negrita } })}>
                          <Bold className="w-3 h-3" />
                        </Button>
                        {(['left', 'center', 'right'] as const).map(align => (
                          <Button key={align}
                            variant={col.formato?.alineacion === align ? 'secondary' : 'ghost'}
                            size="sm" className="h-5 w-5 p-0"
                            onClick={() => updateColumn(nivel.id, colIdx, { formato: { ...col.formato, alineacion: align } })}>
                            {align === 'left' ? <AlignLeft className="w-3 h-3" /> : align === 'center' ? <AlignCenter className="w-3 h-3" /> : <AlignRight className="w-3 h-3" />}
                          </Button>
                        ))}
                        <div className="flex items-center gap-0.5 ml-auto">
                          <Label className="text-[8px] text-muted-foreground">Txt</Label>
                          <input type="color" value={col.formato?.color_texto || '#000000'}
                            onChange={(e) => updateColumn(nivel.id, colIdx, { formato: { ...col.formato, color_texto: e.target.value } })}
                            className="w-5 h-5 rounded cursor-pointer border border-input" />
                          <Label className="text-[8px] text-muted-foreground ml-1">Fnd</Label>
                          <input type="color" value={col.formato?.color_fondo || '#ffffff'}
                            onChange={(e) => updateColumn(nivel.id, colIdx, { formato: { ...col.formato, color_fondo: e.target.value } })}
                            className="w-5 h-5 rounded cursor-pointer border border-input"
                            disabled={nivel.tipo === 'autorrelleno'} />
                        </div>
                      </div>
                      {/* Borders row */}
                      <div className="flex items-center gap-1.5">
                        <div className="flex-1">
                          <Label className="text-[9px] text-muted-foreground">Bordes</Label>
                          <Select value={detectBorderPreset(col.bordes)}
                            onValueChange={(preset) => {
                              const grosor = col.bordes?.superior?.grosor || 1;
                              const color = col.bordes?.superior?.color || '#000000';
                              updateColumn(nivel.id, colIdx, { bordes: BORDER_PRESETS[preset](grosor, color) });
                            }}>
                            <SelectTrigger className="h-6 text-[10px]"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="ninguno">Ninguno</SelectItem>
                              <SelectItem value="todos">Todos</SelectItem>
                              <SelectItem value="externos">Externos</SelectItem>
                              <SelectItem value="inferior">Inferior</SelectItem>
                              <SelectItem value="superior">Superior</SelectItem>
                              <SelectItem value="horizontal">Horizontal</SelectItem>
                              <SelectItem value="vertical">Vertical</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-[9px] text-muted-foreground">Grosor</Label>
                          <Input type="number" min={0.5} max={3} step={0.5}
                            value={col.bordes?.superior?.grosor || 1}
                            onChange={(e) => {
                              const g = parseFloat(e.target.value) || 1;
                              const preset = detectBorderPreset(col.bordes);
                              const color = col.bordes?.superior?.color || '#000000';
                              updateColumn(nivel.id, colIdx, { bordes: BORDER_PRESETS[preset](g, color) });
                            }}
                            className="h-6 text-[10px] w-14" />
                        </div>
                        <div>
                          <Label className="text-[9px] text-muted-foreground">Color</Label>
                          <input type="color" value={col.bordes?.superior?.color || '#000000'}
                            onChange={(e) => {
                              const grosor = col.bordes?.superior?.grosor || 1;
                              const preset = detectBorderPreset(col.bordes);
                              updateColumn(nivel.id, colIdx, { bordes: BORDER_PRESETS[preset](grosor, e.target.value) });
                            }}
                            className="w-full h-6 rounded cursor-pointer border border-input" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {niveles.length === 0 && (
        <div className="text-center py-4 text-xs text-muted-foreground">
          Sin niveles. Añade un nivel estático o dinámico.
        </div>
      )}
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
    selectedElementIds,
    configuracion,
    chartScripts,
    tableScripts,
    updateElement,
    deleteElement,
    updateConfig,
    dispatchAction,
    clearSelection
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

  // Multi-selection panel
  if (selectedElementIds.length > 1) {
    const selectedElements = selectedElementIds
      .map(id => currentPage?.elementos[id])
      .filter(Boolean);

    const handleCreateGroup = () => {
      dispatchAction({
        type: 'create_group',
        elementIds: selectedElementIds,
      });
    };

    const handleDeleteSelected = () => {
      for (const id of selectedElementIds) {
        deleteElement(pagina_actual, id);
      }
      clearSelection();
    };

    return (
      <motion.aside
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="w-72 bg-card border-l border-border p-4 overflow-y-auto scrollbar-thin"
      >
        <div className="flex items-center gap-2 mb-4">
          <Group className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-sm">{selectedElementIds.length} elementos seleccionados</h3>
        </div>

        <div className="property-section">
          <div className="property-section-title">Acciones</div>
          <div className="space-y-2">
            <Button
              variant="default"
              size="sm"
              className="w-full gap-2"
              onClick={handleCreateGroup}
            >
              <Package className="w-4 h-4" />
              Crear Grupo
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="w-full gap-2"
              onClick={handleDeleteSelected}
            >
              <Trash2 className="w-4 h-4" />
              Eliminar seleccionados
            </Button>
          </div>
        </div>

        <div className="property-section">
          <div className="property-section-title">Elementos</div>
          <div className="space-y-1">
            {selectedElements.map(el => (
              <div key={el.id} className="text-xs text-muted-foreground flex items-center gap-2 py-1">
                <span className="capitalize font-medium">{el.tipo}</span>
                <span className="truncate opacity-60">{el.id}</span>
              </div>
            ))}
          </div>
        </div>
      </motion.aside>
    );
  }

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

      {/* Chart section - for chart elements */}
      {selectedElement.tipo === 'grafico' && (
        <ChartSection
          element={selectedElement}
          pageId={pagina_actual}
          updateElement={updateElement}
          chartScripts={chartScripts}
        />
      )}

      {/* Table section - for table elements */}
      {selectedElement.tipo === 'tabla' && (
        <TableSection
          element={selectedElement}
          pageId={pagina_actual}
          updateElement={updateElement}
          tableScripts={tableScripts}
        />
      )}

      {/* Style Section */}
      <div className="property-section">
        <div className="property-section-title">Estilo</div>

        {/* Text styling */}
        {selectedElement.tipo === 'texto' && (
          <>
            <div className="mb-3">
              <Label className="text-xs text-muted-foreground mb-1.5 block">Fuente</Label>
              <Select
                value={estilo.fontFamily || estilo.familia_fuente || ''}
                onValueChange={(v) => handleStyleChange('fontFamily', v)}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Arial (por defecto)" />
                </SelectTrigger>
                <SelectContent>
                  {FONT_OPTIONS.map(f => (
                    <SelectItem key={f} value={f}>{f}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!(estilo.fontFamily || estilo.familia_fuente) && (
                <p className="text-[10px] text-amber-500 mt-1 flex items-center gap-1">
                  ⚠ fuente por defecto
                </p>
              )}
            </div>

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
