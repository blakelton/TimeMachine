import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./contexts/AuthContext";
import { queryClient } from "./lib/query";
import { Layout } from "./components/Layout";
import { LoginModal } from "./components/LoginModal";
import { HomePage } from "./pages/HomePage";
import { SystemPage } from "./pages/SystemPage";
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
        <BrowserRouter>
          <LoginModal />
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="system" element={<SystemPage />}>
                <Route path="cameras" element={<CamerasPanel />} />
                <Route path="output" element={<OutputConfigPanel />} />
                <Route path="notifications" element={<NotificationsPanel />} />
                <Route path="temperature" element={<TemperaturePanel />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
