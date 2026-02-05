import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  isSidebarVisible: boolean;
  toggleSidebar: () => void;
  setSidebarVisible: (visible: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      isSidebarVisible: true,
      toggleSidebar: () => set((state) => ({ isSidebarVisible: !state.isSidebarVisible })),
      setSidebarVisible: (visible) => set({ isSidebarVisible: visible }),
    }),
    {
      name: "ui-storage", // Key in localStorage
    }
  )
);
