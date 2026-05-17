import { NavLink } from "react-router-dom";

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm ${isActive ? "bg-indigo-50 text-indigo-600" : "hover:bg-stone-100"}`;

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-60 h-screen border-r border-stone-200 bg-white p-4 flex-col gap-1 sticky top-0">
      <div className="font-mono text-sm font-semibold mb-4">home·agent</div>
      <NavLink to="/chat" className={navItemClass}>
        ◐ 챗
      </NavLink>
      <NavLink to="/calendar" className={navItemClass}>
        ▣ 캘린더
      </NavLink>
      <NavLink to="/schedule" className={navItemClass}>
        ◆ 일정
      </NavLink>
    </aside>
  );
}
