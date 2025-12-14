# System Settings - Plan

## Overview

Implement the System tab with left sidebar menu and configuration panels for Cameras, Output, and Temperature.

**Dependencies**: 05-frontend-foundation, 02-database-config
**Estimated Duration**: 2-3 days

---

## Phase 1: Settings Layout

### Goal
Create split layout with sidebar navigation and content panel.

### Desktop Layout
```
+------------------------------------------+
| System Settings                          |
+----------+-------------------------------+
| Cameras  | [Content Panel]              |
| Output   |                               |
| Temp     |                               |
|          |                               |
+----------+-------------------------------+
```

### Mobile Layout
```
+------------------+
| System Settings  |
+------------------+
| [Cameras ▼]      |
+------------------+
| Content Panel    |
|                  |
+------------------+
```

### Tasks

1. **Create `src/pages/System/index.tsx`**
   ```typescript
   import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
   import { useMediaQuery } from '@/hooks/useMediaQuery';
   import { CamerasPanel } from './CamerasPanel';
   import { OutputPanel } from './OutputPanel';
   import { TemperaturePanel } from './TemperaturePanel';
   import styles from './System.module.css';

   const menuItems = [
     { path: 'cameras', label: 'Cameras', icon: '📷' },
     { path: 'output', label: 'Output', icon: '💾' },
     { path: 'temperature', label: 'Temperature', icon: '🌡️' },
   ];

   export default function System() {
     const isMobile = useMediaQuery('(max-width: 768px)');

     return (
       <div className={styles.settings}>
         <h1>System Settings</h1>
         
         <div className={styles.layout}>
           <nav className={styles.sidebar}>
             {menuItems.map((item) => (
               <NavLink
                 key={item.path}
                 to={item.path}
                 className={({ isActive }) =>
                   `${styles.menuItem} ${isActive ? styles.active : ''}`
                 }
               >
                 <span>{item.icon}</span>
                 <span>{item.label}</span>
               </NavLink>
             ))}
           </nav>
           
           <div className={styles.content}>
             <Routes>
               <Route path="cameras" element={<CamerasPanel />} />
               <Route path="output" element={<OutputPanel />} />
               <Route path="temperature" element={<TemperaturePanel />} />
               <Route path="" element={<Navigate to="cameras" replace />} />
             </Routes>
           </div>
         </div>
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Sidebar navigation works
- [ ] Mobile dropdown/tabs
- [ ] Active state indicated

---

## Phase 2: Cameras Panel

### Goal
CRUD interface for camera management.

### Tasks

1. **Create `src/pages/System/CamerasPanel.tsx`**
   ```typescript
   import { useState } from 'react';
   import { useCameras, useDeleteCamera } from '@/api/hooks/useCameras';
   import { Button } from '@/components/common/Button';
   import { Card } from '@/components/common/Card';
   import { CameraModal } from './CameraModal';
   import { DeleteConfirmDialog } from '@/components/common/DeleteConfirmDialog';
   import styles from './CamerasPanel.module.css';

   export function CamerasPanel() {
     const { data: cameras, isLoading } = useCameras();
     const deleteCamera = useDeleteCamera();
     const [editingCamera, setEditingCamera] = useState<number | null>(null);
     const [isCreating, setIsCreating] = useState(false);
     const [deletingId, setDeletingId] = useState<number | null>(null);

     if (isLoading) return <div>Loading...</div>;

     return (
       <Card>
         <div className={styles.header}>
           <h2>Cameras</h2>
           <Button onClick={() => setIsCreating(true)}>Add Camera</Button>
         </div>

         <table className={styles.table}>
           <thead>
             <tr>
               <th>Name</th>
               <th>Type</th>
               <th>Device</th>
               <th>Resolution</th>
               <th>FPS</th>
               <th>Status</th>
               <th>Actions</th>
             </tr>
           </thead>
           <tbody>
             {cameras?.map((camera) => (
               <tr key={camera.id}>
                 <td>{camera.name}</td>
                 <td>{camera.source_type}</td>
                 <td>{camera.device_path}</td>
                 <td>{camera.resolution}</td>
                 <td>{camera.fps}</td>
                 <td>
                   <span className={camera.enabled ? styles.online : styles.offline}>
                     {camera.enabled ? 'Enabled' : 'Disabled'}
                   </span>
                 </td>
                 <td>
                   <Button
                     size="sm"
                     variant="secondary"
                     onClick={() => setEditingCamera(camera.id)}
                   >
                     Edit
                   </Button>
                   <Button
                     size="sm"
                     variant="danger"
                     onClick={() => setDeletingId(camera.id)}
                   >
                     Delete
                   </Button>
                 </td>
               </tr>
             ))}
           </tbody>
         </table>

         {cameras?.length === 0 && (
           <p className={styles.empty}>No cameras configured yet.</p>
         )}

         {(isCreating || editingCamera !== null) && (
           <CameraModal
             cameraId={editingCamera}
             onClose={() => {
               setIsCreating(false);
               setEditingCamera(null);
             }}
           />
         )}

         {deletingId !== null && (
           <DeleteConfirmDialog
             title="Delete Camera"
             message="Are you sure you want to delete this camera?"
             onConfirm={async () => {
               await deleteCamera.mutateAsync(deletingId);
               setDeletingId(null);
             }}
             onCancel={() => setDeletingId(null)}
           />
         )}
       </Card>
     );
   }
   ```

### Acceptance Criteria
- [ ] Camera table displays all cameras
- [ ] Add/Edit/Delete buttons work
- [ ] Status badges show state

---

## Phase 3: Camera Add/Edit Modal

### Goal
Form for creating and editing cameras.

### Form Fields

| Field | Type | Validation |
|-------|------|------------|
| Name | Text | Required, 1-100 chars |
| Source Type | Select | CSI or USB |
| Device Path | Text/Select | Required |
| Resolution | Select | From capabilities |
| FPS | Select | From capabilities |
| H.264 Profile | Select | baseline/main/high |
| Bitrate | Number | 500000-20000000 |
| MJPEG Fallback | Checkbox | - |
| Enabled | Checkbox | - |

### Tasks

1. **Create `src/pages/System/CameraModal.tsx`**
   ```typescript
   import { useEffect, useState } from 'react';
   import { useCamera, useCreateCamera, useUpdateCamera } from '@/api/hooks/useCameras';
   import { Modal } from '@/components/common/Modal';
   import { Input } from '@/components/common/Input';
   import { Button } from '@/components/common/Button';
   import styles from './CameraModal.module.css';

   interface CameraModalProps {
     cameraId: number | null;
     onClose: () => void;
   }

   const RESOLUTIONS = ['1920x1080', '1280x720', '640x480'];
   const FPS_OPTIONS = [30, 24, 15];
   const PROFILES = ['baseline', 'main', 'high'];

   export function CameraModal({ cameraId, onClose }: CameraModalProps) {
     const isEditing = cameraId !== null;
     const { data: camera } = useCamera(cameraId ?? 0);
     const createCamera = useCreateCamera();
     const updateCamera = useUpdateCamera();

     const [form, setForm] = useState({
       name: '',
       source_type: 'USB' as 'CSI' | 'USB',
       device_path: '',
       resolution: '1920x1080',
       fps: 30,
       encoder_settings: {
         profile: 'main',
         bitrate: 4000000,
         mjpeg_fallback: false,
       },
       enabled: true,
     });

     const [errors, setErrors] = useState<Record<string, string>>({});

     useEffect(() => {
       if (camera) {
         setForm({
           name: camera.name,
           source_type: camera.source_type,
           device_path: camera.device_path,
           resolution: camera.resolution,
           fps: camera.fps,
           encoder_settings: camera.encoder_settings || {
             profile: 'main',
             bitrate: 4000000,
             mjpeg_fallback: false,
           },
           enabled: camera.enabled,
         });
       }
     }, [camera]);

     const validate = () => {
       const errs: Record<string, string> = {};
       if (!form.name.trim()) errs.name = 'Name is required';
       if (!form.device_path.trim()) errs.device_path = 'Device path is required';
       setErrors(errs);
       return Object.keys(errs).length === 0;
     };

     const handleSubmit = async () => {
       if (!validate()) return;

       try {
         if (isEditing && cameraId) {
           await updateCamera.mutateAsync({ id: cameraId, data: form });
         } else {
           await createCamera.mutateAsync(form);
         }
         onClose();
       } catch (e) {
         setErrors({ submit: 'Failed to save camera' });
       }
     };

     return (
       <Modal
         title={isEditing ? 'Edit Camera' : 'Add Camera'}
         onClose={onClose}
       >
         <div className={styles.form}>
           <Input
             label="Name"
             value={form.name}
             onChange={(e) => setForm({ ...form, name: e.target.value })}
             error={errors.name}
           />

           <div className={styles.field}>
             <label>Source Type</label>
             <select
               value={form.source_type}
               onChange={(e) =>
                 setForm({ ...form, source_type: e.target.value as 'CSI' | 'USB' })
               }
             >
               <option value="USB">USB</option>
               <option value="CSI">CSI</option>
             </select>
           </div>

           <Input
             label="Device Path"
             value={form.device_path}
             onChange={(e) => setForm({ ...form, device_path: e.target.value })}
             error={errors.device_path}
             placeholder={form.source_type === 'USB' ? '/dev/video0' : 'csi:0'}
           />

           <div className={styles.row}>
             <div className={styles.field}>
               <label>Resolution</label>
               <select
                 value={form.resolution}
                 onChange={(e) => setForm({ ...form, resolution: e.target.value })}
               >
                 {RESOLUTIONS.map((r) => (
                   <option key={r} value={r}>{r}</option>
                 ))}
               </select>
             </div>

             <div className={styles.field}>
               <label>FPS</label>
               <select
                 value={form.fps}
                 onChange={(e) => setForm({ ...form, fps: Number(e.target.value) })}
               >
                 {FPS_OPTIONS.map((f) => (
                   <option key={f} value={f}>{f}</option>
                 ))}
               </select>
             </div>
           </div>

           <div className={styles.field}>
             <label>H.264 Profile</label>
             <select
               value={form.encoder_settings.profile}
               onChange={(e) =>
                 setForm({
                   ...form,
                   encoder_settings: {
                     ...form.encoder_settings,
                     profile: e.target.value,
                   },
                 })
               }
             >
               {PROFILES.map((p) => (
                 <option key={p} value={p}>{p}</option>
               ))}
             </select>
           </div>

           <Input
             label="Bitrate (bps)"
             type="number"
             value={form.encoder_settings.bitrate}
             onChange={(e) =>
               setForm({
                 ...form,
                 encoder_settings: {
                   ...form.encoder_settings,
                   bitrate: Number(e.target.value),
                 },
               })
             }
           />

           <div className={styles.checkbox}>
             <input
               type="checkbox"
               id="enabled"
               checked={form.enabled}
               onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
             />
             <label htmlFor="enabled">Enabled</label>
           </div>

           {errors.submit && <p className={styles.error}>{errors.submit}</p>}

           <div className={styles.actions}>
             <Button variant="secondary" onClick={onClose}>
               Cancel
             </Button>
             <Button onClick={handleSubmit}>
               {isEditing ? 'Save' : 'Create'}
             </Button>
           </div>
         </div>
       </Modal>
     );
   }
   ```

### Acceptance Criteria
- [ ] Form validates on submit
- [ ] Pre-fills data when editing
- [ ] Saves correctly to backend

---

## Phase 4: Output Panel

### Goal
Configure storage paths and formats.

### Tasks

1. **Create `src/pages/System/OutputPanel.tsx`**
   ```typescript
   import { useState, useEffect } from 'react';
   import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
   import { api } from '@/api/client';
   import { Card } from '@/components/common/Card';
   import { Input } from '@/components/common/Input';
   import { Button } from '@/components/common/Button';
   import type { OutputConfig } from '@/types/api';
   import styles from './OutputPanel.module.css';

   export function OutputPanel() {
     const queryClient = useQueryClient();
     
     const { data: config, isLoading } = useQuery({
       queryKey: ['output-config'],
       queryFn: () => api.get<OutputConfig>('/api/v1/outputs'),
     });

     const updateConfig = useMutation({
       mutationFn: (data: Partial<OutputConfig>) =>
         api.put<OutputConfig>('/api/v1/outputs', data),
       onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['output-config'] });
       },
     });

     const testPaths = useMutation({
       mutationFn: () => api.post<{ paths: Record<string, boolean> }>('/api/v1/outputs/test'),
     });

     const [form, setForm] = useState({
       recording_path: '',
       stills_path: '',
       timelapse_path: '',
       video_format: 'mp4',
       image_format: 'jpeg',
       image_quality: 85,
     });

     const [pathStatus, setPathStatus] = useState<Record<string, boolean>>({});

     useEffect(() => {
       if (config) {
         setForm({
           recording_path: config.recording_path,
           stills_path: config.stills_path,
           timelapse_path: config.timelapse_path,
           video_format: config.video_format,
           image_format: config.image_format,
           image_quality: config.image_quality,
         });
       }
     }, [config]);

     const handleSave = async () => {
       await updateConfig.mutateAsync(form);
     };

     const handleTestPaths = async () => {
       const result = await testPaths.mutateAsync();
       setPathStatus(result.paths);
     };

     if (isLoading) return <div>Loading...</div>;

     return (
       <Card>
         <h2>Output Configuration</h2>

         <div className={styles.form}>
           <div className={styles.pathField}>
             <Input
               label="Recording Path"
               value={form.recording_path}
               onChange={(e) => setForm({ ...form, recording_path: e.target.value })}
             />
             {pathStatus.recording !== undefined && (
               <span className={pathStatus.recording ? styles.valid : styles.invalid}>
                 {pathStatus.recording ? '✓' : '✗'}
               </span>
             )}
           </div>

           <div className={styles.pathField}>
             <Input
               label="Stills Path"
               value={form.stills_path}
               onChange={(e) => setForm({ ...form, stills_path: e.target.value })}
             />
             {pathStatus.stills !== undefined && (
               <span className={pathStatus.stills ? styles.valid : styles.invalid}>
                 {pathStatus.stills ? '✓' : '✗'}
               </span>
             )}
           </div>

           <div className={styles.pathField}>
             <Input
               label="Timelapse Path"
               value={form.timelapse_path}
               onChange={(e) => setForm({ ...form, timelapse_path: e.target.value })}
             />
             {pathStatus.timelapse !== undefined && (
               <span className={pathStatus.timelapse ? styles.valid : styles.invalid}>
                 {pathStatus.timelapse ? '✓' : '✗'}
               </span>
             )}
           </div>

           <p className={styles.hint}>
             For NAS storage, ensure the path is mounted before use (e.g., /mnt/nas/cameras)
           </p>

           <Button variant="secondary" onClick={handleTestPaths}>
             Test Paths
           </Button>

           <hr />

           <div className={styles.row}>
             <div className={styles.field}>
               <label>Video Format</label>
               <select
                 value={form.video_format}
                 onChange={(e) => setForm({ ...form, video_format: e.target.value })}
               >
                 <option value="mp4">MP4 (H.264)</option>
                 <option value="mkv">MKV</option>
               </select>
             </div>

             <div className={styles.field}>
               <label>Image Format</label>
               <select
                 value={form.image_format}
                 onChange={(e) => setForm({ ...form, image_format: e.target.value })}
               >
                 <option value="jpeg">JPEG</option>
                 <option value="png">PNG</option>
               </select>
             </div>
           </div>

           <div className={styles.field}>
             <label>Image Quality: {form.image_quality}%</label>
             <input
               type="range"
               min="1"
               max="100"
               value={form.image_quality}
               onChange={(e) => setForm({ ...form, image_quality: Number(e.target.value) })}
             />
           </div>

           <div className={styles.actions}>
             <Button onClick={handleSave} disabled={updateConfig.isPending}>
               Save Configuration
             </Button>
           </div>
         </div>
       </Card>
     );
   }
   ```

### Acceptance Criteria
- [ ] Path inputs with test button
- [ ] Format selectors work
- [ ] Quality slider updates
- [ ] Save persists to backend

---

## Phase 5: Temperature Panel (Stub)

### Goal
Placeholder UI for future temperature control.

### Tasks

1. **Create `src/pages/System/TemperaturePanel.tsx`**
   ```typescript
   import { Card } from '@/components/common/Card';
   import { Input } from '@/components/common/Input';
   import styles from './TemperaturePanel.module.css';

   export function TemperaturePanel() {
     return (
       <Card>
         <h2>Temperature Control</h2>
         
         <div className={styles.comingSoon}>
           <span className={styles.icon}>🚧</span>
           <h3>Coming Soon</h3>
           <p>
             Temperature control functionality is planned for a future release.
             GPIO pin configuration will be available here once hardware
             specifications are finalized.
           </p>
         </div>

         <fieldset disabled className={styles.preview}>
           <legend>Preview (Disabled)</legend>
           
           <div className={styles.field}>
             <label>
               <input type="checkbox" disabled />
               Enable Temperature Control
             </label>
           </div>

           <div className={styles.currentTemp}>
             <span>Current Temperature:</span>
             <span className={styles.value}>N/A</span>
           </div>

           <Input
             label="Target Temperature (°C)"
             type="number"
             value=""
             disabled
             placeholder="25"
           />

           <div className={styles.row}>
             <Input
               label="Sensor Pin"
               type="number"
               value=""
               disabled
               placeholder="GPIO"
             />
             <Input
               label="Heater Pin"
               type="number"
               value=""
               disabled
               placeholder="GPIO"
             />
             <Input
               label="Cooler Pin"
               type="number"
               value=""
               disabled
               placeholder="GPIO"
             />
           </div>
         </fieldset>
       </Card>
     );
   }
   ```

### Acceptance Criteria
- [ ] Clear "Coming Soon" message
- [ ] Disabled preview controls
- [ ] No actual functionality

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| CamerasPanel | Unit | Table, modals |
| CameraModal | Unit | Form validation |
| OutputPanel | Unit | Form updates |
| TemperaturePanel | Unit | Renders disabled |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/07-system-settings.md`
