import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Sidebar } from "@/components/Sidebar";
import Calendar from "@/pages/Calendar";
import Chat from "@/pages/Chat";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex">
        <Sidebar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/calendar" element={<Calendar />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
