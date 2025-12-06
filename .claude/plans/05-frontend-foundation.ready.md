# Frontend Foundation - Plan

## Overview

Create React + Vite + TypeScript scaffold with responsive navigation, API client, and design system foundation.

**Dependencies**: None (parallel with backend)
**Estimated Duration**: 2 days

---

## Phase 1: Project Scaffold

### Goal
Set up Vite with React and TypeScript.

### Tasks

1. **Initialize project**
   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install
   ```

2. **Directory structure**
   ```
   frontend/
   ├── src/
   │   ├── main.tsx
   │   ├── App.tsx
   │   ├── api/
   │   │   ├── client.ts
   │   │   ├── websocket.ts
   │   │   └── hooks/
   │   │       ├── useHealth.ts
   │   │       ├── useStats.ts
   │   │       └── useCameras.ts
   │   ├── components/
   │   │   ├── common/
   │   │   │   ├── Button.tsx
   │   │   │   ├── Card.tsx
   │   │   │   ├── Input.tsx
   │   │   │   ├── Modal.tsx
   │   │   │   ├── Tabs.tsx
   │   │   │   └── LoadingSpinner.tsx
   │   │   └── layout/
   │   │       ├── AppShell.tsx
   │   │       ├── Navigation.tsx
   │   │       └── Header.tsx
   │   ├── pages/
   │   │   ├── Home/
   │   │   │   └── index.tsx
   │   │   ├── System/
   │   │   │   ├── index.tsx
   │   │   │   ├── CamerasPanel.tsx
   │   │   │   ├── OutputPanel.tsx
   │   │   │   └── TemperaturePanel.tsx
   │   │   └── Camera/
   │   │       └── [id].tsx
   │   ├── hooks/
   │   │   └── useMediaQuery.ts
   │   ├── types/
   │   │   ├── api.ts
   │   │   └── camera.ts
   │   ├── utils/
   │   │   └── format.ts
   │   └── styles/
   │       ├── globals.css
   │       └── tokens.css
   ├── index.html
   ├── vite.config.ts
   ├── tsconfig.json
   ├── package.json
   └── .env.example
   ```

3. **Configure `tsconfig.json`**
   ```json
   {
     "compilerOptions": {
       "target": "ES2020",
       "useDefineForClassFields": true,
       "lib": ["ES2020", "DOM", "DOM.Iterable"],
       "module": "ESNext",
       "skipLibCheck": true,
       "moduleResolution": "bundler",
       "allowImportingTsExtensions": true,
       "resolveJsonModule": true,
       "isolatedModules": true,
       "noEmit": true,
       "jsx": "react-jsx",
       "strict": true,
       "noUnusedLocals": true,
       "noUnusedParameters": true,
       "noFallthroughCasesInSwitch": true,
       "baseUrl": ".",
       "paths": {
         "@/*": ["src/*"]
       }
     },
     "include": ["src"],
     "references": [{ "path": "./tsconfig.node.json" }]
   }
   ```

4. **Install dependencies**
   ```bash
   npm install @tanstack/react-query react-router-dom
   npm install -D @types/react-router-dom eslint prettier
   ```

### Acceptance Criteria
- [ ] `npm run dev` starts dev server
- [ ] TypeScript strict mode enabled
- [ ] Path aliases configured

---

## Phase 2: API Client Layer

### Goal
Type-safe API client with error handling.

### Tasks

1. **Create `src/api/client.ts`**
   ```typescript
   const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

   interface ApiResponse<T> {
     data: T;
     meta: {
       timestamp: string;
       request_id?: string;
     };
   }

   interface ApiError {
     error: {
       code: string;
       message: string;
       details?: Record<string, unknown>;
     };
     meta: {
       timestamp: string;
     };
   }

   class ApiClient {
     private baseUrl: string;

     constructor(baseUrl: string) {
       this.baseUrl = baseUrl;
     }

     private async request<T>(
       endpoint: string,
       options: RequestInit = {}
     ): Promise<T> {
       const url = `${this.baseUrl}${endpoint}`;
       
       const response = await fetch(url, {
         ...options,
         headers: {
           'Content-Type': 'application/json',
           ...options.headers,
         },
       });

       if (!response.ok) {
         const error: ApiError = await response.json();
         throw new Error(error.error?.message || 'Request failed');
       }

       const result: ApiResponse<T> = await response.json();
       return result.data;
     }

     get<T>(endpoint: string): Promise<T> {
       return this.request<T>(endpoint, { method: 'GET' });
     }

     post<T>(endpoint: string, data?: unknown): Promise<T> {
       return this.request<T>(endpoint, {
         method: 'POST',
         body: data ? JSON.stringify(data) : undefined,
       });
     }

     put<T>(endpoint: string, data: unknown): Promise<T> {
       return this.request<T>(endpoint, {
         method: 'PUT',
         body: JSON.stringify(data),
       });
     }

     delete<T>(endpoint: string): Promise<T> {
       return this.request<T>(endpoint, { method: 'DELETE' });
     }
   }

   export const api = new ApiClient(API_URL);
   ```

2. **Create `src/api/websocket.ts`**
   ```typescript
   type MessageHandler = (data: unknown) => void;

   class WebSocketClient {
     private ws: WebSocket | null = null;
     private url: string;
     private handlers: Map<string, Set<MessageHandler>> = new Map();
     private reconnectAttempts = 0;
     private maxReconnectAttempts = 5;

     constructor(url: string) {
       this.url = url;
     }

     connect(): void {
       this.ws = new WebSocket(this.url);

       this.ws.onopen = () => {
         console.log('WebSocket connected');
         this.reconnectAttempts = 0;
       };

       this.ws.onmessage = (event) => {
         try {
           const message = JSON.parse(event.data);
           const handlers = this.handlers.get(message.type);
           handlers?.forEach((handler) => handler(message.payload));
         } catch (e) {
           console.error('Failed to parse WebSocket message', e);
         }
       };

       this.ws.onclose = () => {
         console.log('WebSocket closed');
         this.scheduleReconnect();
       };

       this.ws.onerror = (error) => {
         console.error('WebSocket error', error);
       };
     }

     private scheduleReconnect(): void {
       if (this.reconnectAttempts < this.maxReconnectAttempts) {
         const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 16000);
         this.reconnectAttempts++;
         setTimeout(() => this.connect(), delay);
       }
     }

     subscribe(type: string, handler: MessageHandler): () => void {
       if (!this.handlers.has(type)) {
         this.handlers.set(type, new Set());
       }
       this.handlers.get(type)!.add(handler);

       return () => {
         this.handlers.get(type)?.delete(handler);
       };
     }

     send(message: unknown): void {
       if (this.ws?.readyState === WebSocket.OPEN) {
         this.ws.send(JSON.stringify(message));
       }
     }

     disconnect(): void {
       this.ws?.close();
       this.ws = null;
     }
   }

   const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
   export const wsClient = new WebSocketClient(WS_URL);
   ```

3. **Create `src/types/api.ts`**
   ```typescript
   export interface HealthResponse {
     status: string;
     version: string;
     uptime_seconds: number;
   }

   export interface StatsResponse {
     cpu_percent: number;
     memory_percent: number;
     memory_used_mb: number;
     memory_total_mb: number;
     disk: {
       total_gb: number;
       used_gb: number;
       free_gb: number;
       percent_used: number;
     };
     temperature_celsius: number | null;
   }

   export interface Camera {
     id: number;
     name: string;
     source_type: 'CSI' | 'USB';
     device_path: string;
     resolution: string;
     fps: number;
     encoder_settings: {
       profile: string;
       bitrate: number;
       mjpeg_fallback: boolean;
     } | null;
     enabled: boolean;
     created_at: string;
     updated_at: string;
   }

   export interface OutputConfig {
     id: number;
     recording_path: string;
     stills_path: string;
     timelapse_path: string;
     video_format: string;
     image_format: string;
     image_quality: number;
     created_at: string;
     updated_at: string;
   }
   ```

### Acceptance Criteria
- [ ] API client handles errors
- [ ] WebSocket reconnects automatically
- [ ] Types match backend schemas

---

## Phase 3: State Management

### Goal
Configure TanStack Query for server state.

### Tasks

1. **Create `src/api/hooks/useHealth.ts`**
   ```typescript
   import { useQuery } from '@tanstack/react-query';
   import { api } from '../client';
   import type { HealthResponse } from '@/types/api';

   export const useHealth = () => {
     return useQuery({
       queryKey: ['health'],
       queryFn: () => api.get<HealthResponse>('/api/v1/health'),
       refetchInterval: 30000,
     });
   };
   ```

2. **Create `src/api/hooks/useStats.ts`**
   ```typescript
   import { useQuery } from '@tanstack/react-query';
   import { api } from '../client';
   import type { StatsResponse } from '@/types/api';

   export const useStats = (enabled = true) => {
     return useQuery({
       queryKey: ['stats'],
       queryFn: () => api.get<StatsResponse>('/api/v1/stats'),
       refetchInterval: 5000,
       enabled,
     });
   };
   ```

3. **Create `src/api/hooks/useCameras.ts`**
   ```typescript
   import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
   import { api } from '../client';
   import type { Camera } from '@/types/api';

   export const useCameras = () => {
     return useQuery({
       queryKey: ['cameras'],
       queryFn: () => api.get<Camera[]>('/api/v1/cameras'),
     });
   };

   export const useCamera = (id: number) => {
     return useQuery({
       queryKey: ['cameras', id],
       queryFn: () => api.get<Camera>(`/api/v1/cameras/${id}`),
       enabled: id > 0,
     });
   };

   export const useCreateCamera = () => {
     const queryClient = useQueryClient();
     return useMutation({
       mutationFn: (data: Partial<Camera>) =>
         api.post<Camera>('/api/v1/cameras', data),
       onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['cameras'] });
       },
     });
   };

   export const useUpdateCamera = () => {
     const queryClient = useQueryClient();
     return useMutation({
       mutationFn: ({ id, data }: { id: number; data: Partial<Camera> }) =>
         api.put<Camera>(`/api/v1/cameras/${id}`, data),
       onSuccess: (_, { id }) => {
         queryClient.invalidateQueries({ queryKey: ['cameras'] });
         queryClient.invalidateQueries({ queryKey: ['cameras', id] });
       },
     });
   };

   export const useDeleteCamera = () => {
     const queryClient = useQueryClient();
     return useMutation({
       mutationFn: (id: number) => api.delete(`/api/v1/cameras/${id}`),
       onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['cameras'] });
       },
     });
   };
   ```

4. **Configure QueryClient in `src/main.tsx`**
   ```typescript
   import React from 'react';
   import ReactDOM from 'react-dom/client';
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
   import App from './App';
   import './styles/globals.css';

   const queryClient = new QueryClient({
     defaultOptions: {
       queries: {
         staleTime: 1000 * 60,
         retry: 2,
       },
     },
   });

   ReactDOM.createRoot(document.getElementById('root')!).render(
     <React.StrictMode>
       <QueryClientProvider client={queryClient}>
         <App />
       </QueryClientProvider>
     </React.StrictMode>
   );
   ```

### Acceptance Criteria
- [ ] Queries cache and refetch properly
- [ ] Mutations invalidate related queries
- [ ] Loading/error states handled

---

## Phase 4: Routing

### Goal
Set up React Router with lazy-loaded routes.

### Tasks

1. **Create `src/App.tsx`**
   ```typescript
   import { lazy, Suspense } from 'react';
   import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
   import { AppShell } from '@/components/layout/AppShell';
   import { LoadingSpinner } from '@/components/common/LoadingSpinner';

   const Home = lazy(() => import('@/pages/Home'));
   const System = lazy(() => import('@/pages/System'));
   const CameraView = lazy(() => import('@/pages/Camera/[id]'));

   function App() {
     return (
       <BrowserRouter>
         <AppShell>
           <Suspense fallback={<LoadingSpinner />}>
             <Routes>
               <Route path="/" element={<Home />} />
               <Route path="/system/*" element={<System />} />
               <Route path="/camera/:id" element={<CameraView />} />
               <Route path="*" element={<Navigate to="/" replace />} />
             </Routes>
           </Suspense>
         </AppShell>
       </BrowserRouter>
     );
   }

   export default App;
   ```

### Acceptance Criteria
- [ ] Routes lazy load correctly
- [ ] Navigation works
- [ ] 404 redirects to home

---

## Phase 5: Layout & Navigation

### Goal
Responsive app shell with tabs/hamburger navigation.

### Tasks

1. **Create `src/components/layout/Navigation.tsx`**
   ```typescript
   import { useState, useEffect } from 'react';
   import { NavLink, useLocation } from 'react-router-dom';
   import { useCameras } from '@/api/hooks/useCameras';
   import styles from './Navigation.module.css';

   interface NavigationProps {
     isMobile: boolean;
     isOpen: boolean;
     onClose: () => void;
   }

   export function Navigation({ isMobile, isOpen, onClose }: NavigationProps) {
     const { data: cameras } = useCameras();
     const location = useLocation();

     useEffect(() => {
       if (isMobile) onClose();
     }, [location.pathname]);

     const navItems = [
       { path: '/', label: 'Home', icon: '🏠' },
       { path: '/system', label: 'System', icon: '⚙️' },
       ...(cameras?.map((cam) => ({
         path: `/camera/${cam.id}`,
         label: cam.name,
         icon: '📷',
       })) || []),
     ];

     if (isMobile && !isOpen) return null;

     return (
       <nav className={`${styles.nav} ${isMobile ? styles.mobile : ''}`}>
         {navItems.map((item) => (
           <NavLink
             key={item.path}
             to={item.path}
             className={({ isActive }) =>
               `${styles.link} ${isActive ? styles.active : ''}`
             }
           >
             <span className={styles.icon}>{item.icon}</span>
             <span className={styles.label}>{item.label}</span>
           </NavLink>
         ))}
       </nav>
     );
   }
   ```

2. **Create `src/components/layout/AppShell.tsx`**
   ```typescript
   import { useState } from 'react';
   import { useMediaQuery } from '@/hooks/useMediaQuery';
   import { Header } from './Header';
   import { Navigation } from './Navigation';
   import styles from './AppShell.module.css';

   interface AppShellProps {
     children: React.ReactNode;
   }

   export function AppShell({ children }: AppShellProps) {
     const isMobile = useMediaQuery('(max-width: 768px)');
     const [menuOpen, setMenuOpen] = useState(false);

     return (
       <div className={styles.shell}>
         <Header
           isMobile={isMobile}
           menuOpen={menuOpen}
           onMenuToggle={() => setMenuOpen(!menuOpen)}
         />
         <div className={styles.body}>
           <Navigation
             isMobile={isMobile}
             isOpen={menuOpen}
             onClose={() => setMenuOpen(false)}
           />
           <main className={styles.content}>{children}</main>
         </div>
       </div>
     );
   }
   ```

3. **Create `src/hooks/useMediaQuery.ts`**
   ```typescript
   import { useState, useEffect } from 'react';

   export function useMediaQuery(query: string): boolean {
     const [matches, setMatches] = useState(
       () => window.matchMedia(query).matches
     );

     useEffect(() => {
       const mediaQuery = window.matchMedia(query);
       const handler = (e: MediaQueryListEvent) => setMatches(e.matches);

       mediaQuery.addEventListener('change', handler);
       return () => mediaQuery.removeEventListener('change', handler);
     }, [query]);

     return matches;
   }
   ```

### Acceptance Criteria
- [ ] Tabs on desktop, hamburger on mobile
- [ ] Dynamic camera tabs appear
- [ ] Navigation closes on route change

---

## Phase 6: Design System Foundation

### Goal
Establish design tokens and common components.

### Tasks

1. **Create `src/styles/tokens.css`**
   ```css
   :root {
     /* Colors */
     --color-primary: #2563eb;
     --color-primary-hover: #1d4ed8;
     --color-success: #16a34a;
     --color-warning: #ca8a04;
     --color-error: #dc2626;
     
     --color-bg: #ffffff;
     --color-bg-secondary: #f3f4f6;
     --color-text: #111827;
     --color-text-secondary: #6b7280;
     --color-border: #e5e7eb;
     
     /* Spacing */
     --space-1: 0.25rem;
     --space-2: 0.5rem;
     --space-3: 0.75rem;
     --space-4: 1rem;
     --space-6: 1.5rem;
     --space-8: 2rem;
     
     /* Typography */
     --font-sans: system-ui, -apple-system, sans-serif;
     --font-mono: ui-monospace, monospace;
     --text-sm: 0.875rem;
     --text-base: 1rem;
     --text-lg: 1.125rem;
     --text-xl: 1.25rem;
     --text-2xl: 1.5rem;
     
     /* Radius */
     --radius-sm: 0.25rem;
     --radius-md: 0.375rem;
     --radius-lg: 0.5rem;
     
     /* Shadows */
     --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
     --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
   }
   ```

2. **Create common components** (Button, Card, Input, Modal, Tabs, LoadingSpinner)

### Acceptance Criteria
- [ ] Tokens used consistently
- [ ] Components are accessible
- [ ] Responsive at all breakpoints

---

## Phase 7: Build Configuration

### Goal
Optimize for production deployment.

### Tasks

1. **Update `vite.config.ts`**
   ```typescript
   import { defineConfig } from 'vite';
   import react from '@vitejs/plugin-react';
   import path from 'path';

   export default defineConfig({
     plugins: [react()],
     resolve: {
       alias: {
         '@': path.resolve(__dirname, './src'),
       },
     },
     build: {
       outDir: 'dist',
       sourcemap: false,
       rollupOptions: {
         output: {
           manualChunks: {
             vendor: ['react', 'react-dom', 'react-router-dom'],
             query: ['@tanstack/react-query'],
           },
         },
       },
     },
     server: {
       proxy: {
         '/api': 'http://localhost:8000',
         '/ws': {
           target: 'ws://localhost:8000',
           ws: true,
         },
       },
     },
   });
   ```

2. **Create `.env.example`**
   ```
   VITE_API_URL=http://localhost:8000
   VITE_WS_URL=ws://localhost:8000/ws
   ```

### Acceptance Criteria
- [ ] Production build < 200KB gzipped
- [ ] Code splitting works
- [ ] Dev proxy configured

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| API client | Unit | Error handling |
| Hooks | Unit | Query/mutation |
| Components | Unit | Rendering |
| Navigation | Integration | Route changes |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/05-frontend-foundation.md`
