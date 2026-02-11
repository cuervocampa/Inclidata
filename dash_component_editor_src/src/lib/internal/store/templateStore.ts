import { create } from 'zustand';

// Types
export type ElementType = 'texto' | 'imagen' | 'linea' | 'rectangulo' | 'grafico' | 'tabla';
export type Orientation = 'portrait' | 'landscape';

export interface Geometry {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

export interface ElementStyle {
  color?: string;
  backgroundColor?: string;
  tamano?: number;
  fontFamily?: string;
  fontWeight?: 'normal' | 'bold';
  fontStyle?: 'normal' | 'italic';
  textAlign?: 'left' | 'center' | 'right';
  borderWidth?: number;
  borderColor?: string;
  opacity?: number;
  mantener_proporcion?: boolean;
}

export interface ElementContent {
  texto?: string;
  src?: string;
}

export interface ImageData {
  formato?: string;
  datos_temp?: string;
  ruta_original?: string;
  ruta_nueva?: string;
  nombre_archivo?: string;
  estado?: string;
}

export interface ChartConfig {
  script: string;
  formato: 'svg' | 'png';
  parametros: Record<string, unknown>;
}

export interface ColumnBorder {
  activo: boolean;
  grosor: number;
  color: string;
}

export interface ColumnBorders {
  superior: ColumnBorder;
  inferior: ColumnBorder;
  izquierdo: ColumnBorder;
  derecho: ColumnBorder;
}

export interface ColumnFormat {
  fuente: string;
  tamano: number;
  color_texto: string;
  color_fondo: string;
  alineacion: 'left' | 'center' | 'right';
  negrita: boolean;
}

export interface GridColumn {
  ancho: number;
  contenido: string;
  formato: ColumnFormat;
  bordes: ColumnBorders;
}

export interface DynamicConfig {
  sombreado_alterno: boolean;
  color_par: string;
  color_impar: string;
}

export interface GridLevel {
  id: number;
  tipo: 'estatico' | 'autorrelleno';
  num_columnas: number;
  alto_fila: number;
  estilo: { fuente: string; tamano: number };
  columnas: GridColumn[];
  configuracion_dinamica?: DynamicConfig;
}

export interface Cuadricula {
  niveles: GridLevel[];
}

export interface ElementMetadata {
  zIndex: number;
  visible: boolean;
  grupo?: string;
}

export interface TemplateElement {
  id: string;
  tipo: ElementType;
  geometria: Geometry;
  estilo: ElementStyle;
  contenido: ElementContent;
  metadata: ElementMetadata;
  imagen?: ImageData;
  configuracion?: ChartConfig;
  cuadricula?: Cuadricula;
}

export interface PageConfig {
  orientacion: Orientation;
}

export interface Page {
  elementos: Record<string, TemplateElement>;
  configuracion: PageConfig;
}

export interface TemplateConfig {
  nombre_plantilla: string;
  num_paginas: number;
  version?: string;
}

export interface PendingAction {
  type: string;
  elementIds?: string[];
  [key: string]: unknown;
}

export interface TemplateState {
  paginas: Record<string, Page>;
  pagina_actual: string;
  configuracion: TemplateConfig;
  selectedElementId: string | null;
  selectedElementIds: string[];
  pendingAction: PendingAction | null;
  chartScripts: string[];
  tableScripts: string[];
  zoom: number;
}

interface TemplateActions {
  // Page actions
  addPage: () => void;
  deletePage: (pageId: string) => void;
  setCurrentPage: (pageId: string) => void;
  setPageOrientation: (pageId: string, orientation: Orientation) => void;
  
  // Element actions
  addElement: (pageId: string, element: Omit<TemplateElement, 'id'>) => string;
  updateElement: (pageId: string, elementId: string, updates: Partial<TemplateElement>) => void;
  deleteElement: (pageId: string, elementId: string) => void;
  selectElement: (elementId: string | null) => void;
  toggleSelectElement: (elementId: string) => void;
  selectGroup: (groupName: string) => void;
  clearSelection: () => void;
  
  // Template actions
  updateConfig: (config: Partial<TemplateConfig>) => void;
  loadTemplate: (template: Omit<TemplateState, 'selectedElementId'>) => void;
  resetTemplate: () => void;
  dispatchAction: (action: PendingAction) => void;
  setChartScripts: (scripts: string[]) => void;
  setTableScripts: (scripts: string[]) => void;
  setZoom: (zoom: number) => void;

  // Helpers
  getSelectedElement: () => TemplateElement | null;
  exportJSON: () => string;
}

const generateId = () => `el_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

const initialState: TemplateState = {
  paginas: {
    '1': {
      elementos: {},
      configuracion: { orientacion: 'portrait' }
    }
  },
  pagina_actual: '1',
  configuracion: {
    nombre_plantilla: 'Nueva Plantilla',
    num_paginas: 1,
    version: '1.0'
  },
  selectedElementId: null,
  selectedElementIds: [],
  pendingAction: null,
  chartScripts: [],
  tableScripts: [],
  zoom: 1
};

export const useTemplateStore = create<TemplateState & TemplateActions>((set, get) => ({
  ...initialState,
  
  // Page actions
  addPage: () => {
    set((state) => {
      const newPageNum = state.configuracion.num_paginas + 1;
      const newPageId = String(newPageNum);
      return {
        paginas: {
          ...state.paginas,
          [newPageId]: {
            elementos: {},
            configuracion: { orientacion: 'portrait' }
          }
        },
        configuracion: {
          ...state.configuracion,
          num_paginas: newPageNum
        },
        pagina_actual: newPageId
      };
    });
  },
  
  deletePage: (pageId: string) => {
    set((state) => {
      if (state.configuracion.num_paginas <= 1) return state;
      
      const { [pageId]: deleted, ...remainingPages } = state.paginas;
      const pageIds = Object.keys(remainingPages).sort((a, b) => Number(a) - Number(b));
      const newCurrentPage = state.pagina_actual === pageId ? pageIds[0] : state.pagina_actual;
      
      return {
        paginas: remainingPages,
        pagina_actual: newCurrentPage,
        configuracion: {
          ...state.configuracion,
          num_paginas: state.configuracion.num_paginas - 1
        },
        selectedElementId: null,
        selectedElementIds: []
      };
    });
  },
  
  setCurrentPage: (pageId: string) => {
    set({ pagina_actual: pageId, selectedElementId: null, selectedElementIds: [] });
  },
  
  setPageOrientation: (pageId: string, orientation: Orientation) => {
    set((state) => ({
      paginas: {
        ...state.paginas,
        [pageId]: {
          ...state.paginas[pageId],
          configuracion: { orientacion: orientation }
        }
      }
    }));
  },
  
  // Element actions
  addElement: (pageId: string, element: Omit<TemplateElement, 'id'>) => {
    const id = generateId();
    set((state) => ({
      paginas: {
        ...state.paginas,
        [pageId]: {
          ...state.paginas[pageId],
          elementos: {
            ...state.paginas[pageId].elementos,
            [id]: { ...element, id }
          }
        }
      },
      selectedElementId: id,
      selectedElementIds: []
    }));
    return id;
  },
  
  updateElement: (pageId: string, elementId: string, updates: Partial<TemplateElement>) => {
    set((state) => {
      const element = state.paginas[pageId]?.elementos[elementId];
      if (!element) return state;
      
      return {
        paginas: {
          ...state.paginas,
          [pageId]: {
            ...state.paginas[pageId],
            elementos: {
              ...state.paginas[pageId].elementos,
              [elementId]: {
                ...element,
                ...updates,
                geometria: updates.geometria ? { ...element.geometria, ...updates.geometria } : element.geometria,
                estilo: updates.estilo ? { ...element.estilo, ...updates.estilo } : element.estilo,
                contenido: updates.contenido ? { ...element.contenido, ...updates.contenido } : element.contenido,
                metadata: updates.metadata ? { ...element.metadata, ...updates.metadata } : element.metadata,
                configuracion: updates.configuracion
                  ? { ...element.configuracion, ...updates.configuracion }
                  : element.configuracion,
                cuadricula: updates.cuadricula !== undefined
                  ? updates.cuadricula
                  : element.cuadricula
              }
            }
          }
        }
      };
    });
  },
  
  deleteElement: (pageId: string, elementId: string) => {
    set((state) => {
      const { [elementId]: deleted, ...remainingElements } = state.paginas[pageId].elementos;
      return {
        paginas: {
          ...state.paginas,
          [pageId]: {
            ...state.paginas[pageId],
            elementos: remainingElements
          }
        },
        selectedElementId: state.selectedElementId === elementId ? null : state.selectedElementId,
        selectedElementIds: state.selectedElementIds.filter(id => id !== elementId)
      };
    });
  },
  
  selectElement: (elementId: string | null) => {
    set({ selectedElementId: elementId, selectedElementIds: elementId ? [elementId] : [] });
  },

  toggleSelectElement: (elementId: string) => {
    set((state) => {
      const ids = state.selectedElementIds.includes(elementId)
        ? state.selectedElementIds.filter(id => id !== elementId)
        : [...state.selectedElementIds, elementId];
      return {
        selectedElementIds: ids,
        selectedElementId: ids.length === 1 ? ids[0] : ids.length === 0 ? null : state.selectedElementId,
      };
    });
  },

  selectGroup: (groupName: string) => {
    set((state) => {
      const page = state.paginas[state.pagina_actual];
      if (!page) return state;
      const ids = Object.values(page.elementos)
        .filter(el => el.metadata?.grupo === groupName)
        .map(el => el.id);
      return {
        selectedElementIds: ids,
        selectedElementId: ids.length === 1 ? ids[0] : null,
      };
    });
  },

  clearSelection: () => {
    set({ selectedElementId: null, selectedElementIds: [] });
  },
  
  // Template actions
  updateConfig: (config: Partial<TemplateConfig>) => {
    set((state) => ({
      configuracion: { ...state.configuracion, ...config }
    }));
  },
  
  loadTemplate: (template) => {
    // Ensure every element has the required sub-objects to prevent crashes
    // when loading templates from the old editor format.
    const safePaginas: Record<string, Page> = {};
    for (const [pageId, page] of Object.entries(template.paginas || {})) {
      const safeElementos: Record<string, TemplateElement> = {};
      for (const [elemId, elem] of Object.entries((page as Page).elementos || {})) {
        const e = elem as any;
        safeElementos[elemId] = {
          ...e,
          id: e.id || elemId,
          estilo: e.estilo || {},
          contenido: e.contenido || {},
          metadata: e.metadata || { zIndex: 0, visible: true },
          geometria: e.geometria || { x: 0, y: 0, ancho: 1, alto: 1 },
        };
      }
      safePaginas[pageId] = {
        ...(page as Page),
        elementos: safeElementos,
      };
    }
    set({
      ...template,
      paginas: safePaginas,
      selectedElementId: null,
      selectedElementIds: []
    });
  },
  
  resetTemplate: () => {
    set(initialState);
  },
  
  dispatchAction: (action: PendingAction) => {
    set({ pendingAction: action });
  },

  setChartScripts: (scripts: string[]) => {
    set({ chartScripts: scripts });
  },

  setTableScripts: (scripts: string[]) => {
    set({ tableScripts: scripts });
  },

  setZoom: (zoom: number) => {
    set({ zoom: Math.min(3, Math.max(0.25, Math.round(zoom * 100) / 100)) });
  },

  // Helpers
  getSelectedElement: () => {
    const state = get();
    if (!state.selectedElementId) return null;
    return state.paginas[state.pagina_actual]?.elementos[state.selectedElementId] || null;
  },
  
  exportJSON: () => {
    const { selectedElementId, selectedElementIds, pendingAction, chartScripts, tableScripts, zoom, ...templateData } = get();
    return JSON.stringify({
      paginas: templateData.paginas,
      pagina_actual: templateData.pagina_actual,
      configuracion: templateData.configuracion
    }, null, 2);
  }
}));
