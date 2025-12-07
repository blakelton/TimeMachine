import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { queryClient } from "./lib/query";
import { Layout } from "./components/Layout";
import { LoginModal } from "./components/LoginModal";
import { ToastContainer } from "./components/Toast";
import { HomePage } from "./pages/HomePage";
import { SystemPage } from "./pages/SystemPage";
import { CameraPage } from "./pages/CameraPage";
import {
  CamerasPanel,
  OutputConfigPanel,
  NotificationsPanel,
  TemperaturePanel,
} from "./components/settings";
import "./App.css";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <LoginModal />
            <ToastContainer />
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<HomePage />} />
                <Route path="camera/:cameraId/:tab?" element={<CameraPage />} />
                <Route path="system" element={<SystemPage />}>
                  <Route path="cameras" element={<CamerasPanel />} />
                  <Route path="output" element={<OutputConfigPanel />} />
                  <Route path="notifications" element={<NotificationsPanel />} />
                  <Route path="temperature" element={<TemperaturePanel />} />
                </Route>
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
