import { create } from "zustand";

// 类型定义
interface GlobalState {
  globalVariables: {
    [key: string]: string; // 允许动态属性
  };
  addProperty: (key: string, value: string) => void;
  removeProperty: (key: string) => void;
  updateProperty: (key: string, value: string) => void;
  setglobalVariables: (globalVariables:{[key: string]: string}) => void;
  reset: () => void;
}

// 初始状态
const initialState = {};

export const useGlobalStore = create<GlobalState>()((set, get) => ({
  globalVariables: { ...initialState },

  // 添加新属性
  addProperty: (key, value) => {
    if (get().globalVariables.hasOwnProperty(key)) {
      alert(`Property ${key} already exists`);
      return;
    }
    set((state) => ({
      globalVariables: { ...state.globalVariables, [key]: value },
    }));
  },

  // 删除属性（保留初始属性）
  removeProperty: (key) => {
    if (Object.keys(initialState).includes(key)) {
      alert(`Cannot remove initial property: ${key}`);
      return;
    }
    set((state) => {
      const newData = { ...state.globalVariables };
      delete newData[key];
      return { globalVariables: newData };
    });
  },

  // 更新属性值
  updateProperty: (key, value) => {
    if (!get().globalVariables.hasOwnProperty(key)) {
      alert(`Property ${key} does not exist`);
      return;
    }
    set((state) => ({
      globalVariables: { ...state.globalVariables, [key]: value },
    }));
  },
  setglobalVariables: (globalVariables)=>set({ globalVariables: { ...globalVariables } }),
  // 重置到初始状态
  reset: () => set({ globalVariables: { ...initialState } }),
}));
