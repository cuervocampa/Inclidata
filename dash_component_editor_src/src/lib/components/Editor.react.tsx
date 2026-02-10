import React, { useEffect, Suspense } from 'react';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TemplateEditor } from '@/components/editor/TemplateEditor';
import { useTemplateStore } from '@/store/templateStore';
import '../internal/index.css'; // Import styles

// Create a client
const queryClient = new QueryClient();

// Sync component to handle Dash <-> Zustand communication
const StoreSync = (props: any) => {
    const { setProps, data } = props;
    const store = useTemplateStore();

    // 1. Listen to Dash props change (load template)
    useEffect(() => {
        if (data && Object.keys(data).length > 0) {
            const { chartScripts, ...templateData } = data;
            console.log("Loading template from Dash data", templateData);
            store.loadTemplate(templateData);
            if (chartScripts) {
                store.setChartScripts(chartScripts);
            }
        }
    }, [data]);

    // 2. Listen to Store changes and update Dash
    useEffect(() => {
        const unsubscribe = useTemplateStore.subscribe((state) => {
            if (setProps) {
                // Debounce could be added here if performance is an issue
                // extracting the clean JSON payload
                const payload: any = {
                    paginas: state.paginas,
                    pagina_actual: state.pagina_actual,
                    configuracion: state.configuracion
                };

                if (state.pendingAction) {
                    payload.action = state.pendingAction;
                }

                // Only sending back if meaningful change? 
                // For now send everything to keep state in sync for "Save" button in Dash
                setProps({ value: payload });
            }
        });
        return () => unsubscribe();
    }, [setProps]);

    return null;
};


type Props = {
    id?: string;
    setProps?: (props: any) => void;
    data?: any; // The template JSON to load
    value?: any; // The current state JSON (for Output in Dash)
};

const Editor = (props: Props) => {
    return (
        <div id={props.id}>
            <QueryClientProvider client={queryClient}>
                <TooltipProvider>
                    <Suspense fallback={<div>Loading Editor...</div>}>
                        <StoreSync {...props} />
                        <TemplateEditor />
                        <Toaster />
                        <Sonner />
                    </Suspense>
                </TooltipProvider>
            </QueryClientProvider>
        </div>
    );
}

export default Editor;
