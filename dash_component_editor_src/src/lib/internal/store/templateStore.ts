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

export interface TemplateState {
  paginas: Record<string, Page>;
  pagina_actual: string;
  configuracion: TemplateConfig;
  selectedElementId: string | null;
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
  
  // Template actions
  updateConfig: (config: Partial<TemplateConfig>) => void;
  loadTemplate: (template: Omit<TemplateState, 'selectedElementId'>) => void;
  resetTemplate: () => void;
  
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
  selectedElementId: null
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
        selectedElementId: null
      };
    });
  },
  
  setCurrentPage: (pageId: string) => {
    set({ pagina_actual: pageId, selectedElementId: null });
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
      selectedElementId: id
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
                metadata: updates.metadata ? { ...element.metadata, ...updates.metadata } : element.metadata
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
        selectedElementId: state.selectedElementId === elementId ? null : state.selectedElementId
      };
    });
  },
  
  selectElement: (elementId: string | null) => {
    set({ selectedElementId: elementId });
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
      selectedElementId: null
    });
  },
  
  resetTemplate: () => {
    set(initialState);
  },
  
  // Helpers
  getSelectedElement: () => {
    const state = get();
    if (!state.selectedElementId) return null;
    return state.paginas[state.pagina_actual]?.elementos[state.selectedElementId] || null;
  },
  
  exportJSON: () => {
    const { selectedElementId, ...templateData } = get();
    return JSON.stringify({
      paginas: templateData.paginas,
      pagina_actual: templateData.pagina_actual,
      configuracion: templateData.configuracion
    }, null, 2);
  }
}));
