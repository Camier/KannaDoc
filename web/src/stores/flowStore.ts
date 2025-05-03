// store/flowStore.ts
import { create } from "zustand";
import { CustomNode, CustomEdge, NodeTypeKey } from "@/types/types";

interface FlowState {
  nodes: CustomNode[];
  edges: CustomEdge[];
  history: { nodes: CustomNode[]; edges: CustomEdge[] }[];
  future: { nodes: CustomNode[]; edges: CustomEdge[] }[];
  selectedType: NodeTypeKey;
  selectedNodeId: string | null; // 替换 selectedNode
  selectedEdgeId: string | null; // 替换 selectedNode
  maxHistory: number;

  // Actions
  setNodes: (nodes: CustomNode[]) => void;
  setEdges: (edges: CustomEdge[]) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setSelectedEdgeId: (edgeId: string | null) => void;
  setSelectedType: (type: NodeTypeKey) => void;
  pushHistory: () => void;
  undo: () => void;
  redo: () => void;
  deleteEdge: (edgeId: string) => void;
  deleteNode: (nodeId: string) => void;
  updateNodeLabel: (nodeId: string, label: string) => void;
  updateCode: (nodeId: string, code: string) => void;
  updateOutput: (nodeId: string, output: string) => void;
  updateConditions: (nodeId: string, key: number, value: string) => void;
  updateLoopType: (nodeId: string, loopType: string) => void;
  updateMaxCount: (nodeId: string, maxCount: number) => void;
  updateCondition: (nodeId: string, condition: string) => void;
  removeCondition: (nodeId: string, key: number) => void;
  updateConditionCount: (nodeId: string, conditionCount: number) => void;
  getConditionCount: (nodeId: string) => number|undefined;
}

export const useFlowStore = create<FlowState>((set, get) => ({
  nodes: [],
  edges: [],
  history: [],
  future: [],
  selectedType: "start",
  selectedNodeId: null,
  selectedEdgeId: null,
  maxHistory: 50,

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setSelectedType: (type) => set({ selectedType: type }),
  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),
  setSelectedEdgeId: (edgeId) => set({ selectedEdgeId: edgeId }),

  pushHistory: () => {
    const { nodes, edges, history, maxHistory } = get();
    const newHistory = [...history, { nodes, edges }].slice(-maxHistory);
    set({ history: newHistory, future: [] });
  },

  undo: () => {
    const { history, future, nodes, edges } = get();
    if (history.length > 0) {
      const previous = history[history.length - 2];
      set({
        history: history.slice(0, -1),
        future: [{ nodes, edges }, ...future],
        nodes: previous.nodes,
        edges: previous.edges,
      });
    }
  },

  redo: () => {
    const { future, history, nodes, edges } = get();
    if (future.length > 0) {
      const next = future[0];
      set({
        history: [...history, { nodes: next.nodes, edges: next.edges }],
        future: future.slice(1),
        nodes: next.nodes,
        edges: next.edges,
      });
    }
  },

  deleteEdge: (edgeId) => {
    const edge = get().edges.find((e) => e.id === edgeId) 
      if (edge?.data?.conditionLabel) {
        const conditionNodeId = edge.source;
        get().removeCondition(conditionNodeId, parseInt(edge.data.conditionLabel));
      }
    set((state) => ({ edges: state.edges.filter((e) => e.id !== edgeId) }));
    get().pushHistory();
  },

  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter(
        (e) => e.source !== nodeId && e.target !== nodeId
      ),
    }));
    get().pushHistory();
  },

  updateNodeLabel: (nodeId, label) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, label } } : node
      ),
    }));
    get().pushHistory();
  },

  updateCode: (nodeId, code) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, code } } : node
      ),
    }));
  },

  updateOutput: (nodeId, output) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, output } } : node
      ),
    }));
  },
  updateConditions: (nodeId, key, value) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, conditions:{...node.data.conditions, [key]: value} } }
          : node
      ),
    }));
  },
  removeCondition: (nodeId: string, key: number) => {
    set((state) => ({
      nodes: state.nodes.map((node) => {
        if (node.id === nodeId) {
          // 使用对象解构删除指定 key
          const { [key]: removed, ...remainingConditions } = node.data.conditions || {};
          return {
            ...node,
            data: {
              ...node.data,
              conditions: remainingConditions
            }
          };
        }
        return node;
      })
    }));
  },
  updateLoopType: (nodeId, loopType) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, loopType } }
          : node
      ),
    }));
  },
  updateMaxCount: (nodeId, maxCount) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, maxCount } }
          : node
      ),
    }));
  },
  updateCondition: (nodeId, condition) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, condition } }
          : node
      ),
    }));
  },
  updateConditionCount: (nodeId, conditionCount) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, conditionCount } }
          : node
      ),
    }));
  },
  getConditionCount: (nodeId) => {
    const { nodes } = get();
    const node = nodes.find((node) => node.id === nodeId);
    return node?.data.conditionCount
  },
}));
