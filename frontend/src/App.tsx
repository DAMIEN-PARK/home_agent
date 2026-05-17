import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { DeviceSetup } from "@/components/DeviceSetup";
import { Sidebar } from "@/components/Sidebar";
import { getDeviceName } from "@/lib/device";
import Calendar from "@/pages/Calendar";
import Chat from "@/pages/Chat";
import Schedule from "@/pages/Schedule";

export default function App() {
  const [deviceName, setDeviceNameState] = useState<string | null>(() =>
    getDeviceName(),
  );

  if (!deviceName) {
    return <DeviceSetup onSaved={setDeviceNameState} />;
  }

  return (
    <BrowserRouter>
      <div className="flex">
        <Sidebar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/schedule" element={<Schedule />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
