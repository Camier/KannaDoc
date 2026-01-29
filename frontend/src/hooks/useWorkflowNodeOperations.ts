import { useState, useRef, useCallback, useMemo } from 'react';
import { useFlowStore } from '@/stores/flowStore';
import { v4 as uuidv4 } from 'uuid';
import { NodeTypeKey } from '@/types/types';

export interface WorkflowNodeOperationsState {
  // ===== Node Selection =====
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  selectedType: string | null;
  
  // ===== Node Type Selection =====
  addNodeNameError: string | null;
  newCustomNodeName: string;
  newCustomNodeData: any;
  isCreatingNode: boolean;
}

export const useWorkflowNodeOperations = () => {
  // ===== Store References =====
  const {
    deleteNode,
    deleteEdge,
    setSelectedType: setSelectedTypeInStore,
    getConditionCount,
    updateConditions,
    removeCondition,
    updateOutput,
    updateChat,
    updateConditionCount,
    updateStatus,
    updateVlmModelConfig,
    updateVlmInput,
  } = useFlowStore();

  // ===== Node Selection State =====
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  
  // ===== Node Type Selection State =====
  const [addNodeNameError, setAddNodeNameError] = useState<string | null>(null);
  const [newCustomNodeName, setNewCustomNodeName] = useState<string>('');
  const [newCustomNodeData, setNewCustomNodeData] = useState<any>(null);
  const [isCreatingNode, setIsCreatingNode] = useState<boolean>(false);
  
  // ===== Node Type Colors =====
  const nodeTypeColors = useMemo(() => ({
    start: '#10b981',
    end: '#10b981',
    llm: '#3b82f6',
    vlm: '#8b5cf6',
    condition: '#f59e0b',
    python: '#3776ab',
    tool: '#d97706',
    code: '#64748b',
  }), []);
  
  // ===== Node Type Icons =====
  const getNodeTypeIcon = useCallback((nodeType: string): string => {
    const iconMap: Record<string, string> = {
      start: 'Play',
      end: 'Stop',
      llm: 'Message',
      vlm: 'Camera',
      condition: 'GitBranch',
      python: 'Code',
      tool: 'Terminal',
      code: 'Code',
    };
    return iconMap[nodeType] || 'Code';
  }, []);
  
  const getNodeTypeColor = useCallback((nodeType: string): string => {
    const colorMap: Record<string, string> = nodeTypeColors;
    return colorMap[nodeType] || '#10b981';
  }, [nodeTypeColors]);
  
  // ===== Node ID Generation =====
  const generateNodeId = useCallback((): string => {
    return `node_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  }, []);
  
  // ===== Node Type Selection Hooks =====
  const setSelectedNodeType = useCallback((nodeType: string) => {
    const validNodeType = nodeType === 'start' || nodeType === 'loop' || nodeType === 'condition' || nodeType === 'vlm' || nodeType === 'code'
      ? nodeType as NodeTypeKey
      : 'code' as NodeTypeKey;
    setSelectedType(validNodeType);
    setSelectedTypeInStore(validNodeType);
  }, [setSelectedType, setSelectedTypeInStore]);

  const clearSelectedNodeType = useCallback(() => {
    const defaultType: NodeTypeKey = 'code';
    setSelectedType(defaultType);
    setSelectedTypeInStore(defaultType);
  }, [setSelectedType, setSelectedTypeInStore]);
  
  // ===== Node Name Validation Hooks =====
  const validateNodeName = useCallback((name: string): boolean => {
    if (!name || name.trim().length === 0) {
      setAddNodeNameError('Node name is required');
      return false;
    }
    if (name.trim().length > 100) {
      setAddNodeNameError('Node name must be 100 characters or less');
      return false;
    }
    setAddNodeNameError(null);
    return true;
  }, [setAddNodeNameError]);
  
  // ===== Node Creation Hooks =====
  const createCustomNode = useCallback((name: string, type: string, data: any) => {
    setIsCreatingNode(true);
    
    try {
      const nodeId = generateNodeId();
      const newNode = {
        id: nodeId,
        type: type || 'custom',
        data: data || {},
        position: { x: Math.random() * 800, y: Math.random() * 400 },
      };
      
      setNewCustomNodeData(newNode);
      
      // Note: This would call store.addNode(newNode)
      // We need to import addNode from useFlowStore
      
      setTimeout(() => setIsCreatingNode(false), 1000);
    } catch (error) {
      console.error('Failed to create custom node:', error);
      setIsCreatingNode(false);
    }
  }, [setIsCreatingNode, generateNodeId, setNewCustomNodeData]);
  
  const startCustomNodeCreation = useCallback(() => {
    if (!newCustomNodeName) {
      setAddNodeNameError('Node name is required');
      return;
    }
    if (!validateNodeName(newCustomNodeName)) {
      return;
    }
    createCustomNode(newCustomNodeName, newCustomNodeData.type, newCustomNodeData.data);
  }, [newCustomNodeName, newCustomNodeData, validateNodeName, createCustomNode]);
  
  const cancelCustomNodeCreation = useCallback(() => {
    setIsCreatingNode(false);
    setNewCustomNodeName('');
    setNewCustomNodeData(null);
    setAddNodeNameError(null);
  }, [setIsCreatingNode, setNewCustomNodeName, setNewCustomNodeData, setAddNodeNameError]);
  
  // ===== Node Deletion Hooks =====
  const deleteNodeById = useCallback((nodeId: string) => {
    deleteNode(nodeId);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    updateOutput(nodeId, 'Node deleted');
  }, [deleteNode, setSelectedNodeId, setSelectedEdgeId, updateOutput]);
  
  const deleteEdgeById = useCallback((edgeId: string) => {
    deleteEdge(edgeId);
    setSelectedEdgeId(null);
  }, [deleteEdge, setSelectedEdgeId]);
  
  const clearSelection = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    const defaultType: NodeTypeKey = 'code';
    setSelectedType(defaultType);
    setSelectedTypeInStore(defaultType);
  }, [setSelectedNodeId, setSelectedEdgeId, setSelectedType, setSelectedTypeInStore]);
  
  // ===== Node Condition Hooks =====
  const getConditionCountWrapper = useCallback((nodeId: string): number => {
    return getConditionCount(nodeId) || 0;
  }, [getConditionCount]);

  const updateConditionsWrapper = useCallback((nodeId: string, key: number, value: string) => {
    updateConditions(nodeId, key, value);
  }, [updateConditions]);

  const removeConditionWrapper = useCallback((nodeId: string, key: number) => {
    removeCondition(nodeId, key);
  }, [removeCondition]);
  
  // ===== Node Output Hooks =====
  const updateOutputWrapper = useCallback((nodeId: string, message: string) => {
    updateOutput(nodeId, message);
  }, [updateOutput]);
  
  const clearNodeOutput = useCallback((nodeId: string) => {
    updateOutput(nodeId, 'init');
  }, [updateOutput]);
  
  // ===== Node Chat Hooks =====
  const updateNodeChatWrapper = useCallback((nodeId: string, content: string) => {
    updateChat(nodeId, content);
  }, [updateChat]);

  const clearNodeChat = useCallback((nodeId: string) => {
    updateChat(nodeId, '');
  }, [updateChat]);
  
  // ===== Node Status Hooks =====
  const updateNodeStatusWrapper = useCallback((nodeId: string, status: string) => {
    updateStatus(nodeId, status);
  }, [updateStatus]);
  
  const resetNodeStatus = useCallback((nodeId: string) => {
    updateStatus(nodeId, 'init');
    updateOutput(nodeId, 'awaitRunning');
  }, [updateStatus, updateOutput]);
  
  // ===== VLM Config Hooks =====
  const updateVlmModelConfigWrapper = useCallback((nodeId: string, config: any) => {
    updateVlmModelConfig(nodeId, config);
  }, [updateVlmModelConfig]);
  
  const updateVlmInputWrapper = useCallback((nodeId: string, input: string) => {
    updateVlmInput(nodeId, input);
  }, [updateVlmInput]);
  
  // ===== Node State Management =====
  const resetAllNodeStates = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    const defaultType: NodeTypeKey = 'code';
    setSelectedType(defaultType);
    setSelectedTypeInStore(defaultType);
    setAddNodeNameError(null);
    setNewCustomNodeName('');
    setNewCustomNodeData(null);
    setIsCreatingNode(false);
  }, [setSelectedNodeId, setSelectedEdgeId, setSelectedType, setSelectedTypeInStore, setAddNodeNameError, setNewCustomNodeName, setNewCustomNodeData, setIsCreatingNode]);
  
  // ===== Chatflow Integration =====
  const getChatflowNodeCount = useCallback((chatflowId: string): number => {
    // This would need to call store to get node count for a chatflow
    // Implementation depends on store interface
    return 0;
  }, []);
  
  const refreshChatflowNodes = useCallback((chatflowId: string) => {
    // Refresh all nodes for a specific chatflow
    // This would call store method
  }, []);
  
  return {
    // ===== Node Selection State =====
    selectedNodeId,
    setSelectedNodeId,
    selectedEdgeId,
    setSelectedEdgeId,
    selectedType,
    setSelectedNodeType,
    
    // ===== Node Type Selection State =====
    addNodeNameError,
    setAddNodeNameError,
    newCustomNodeName,
    setNewCustomNodeName,
    newCustomNodeData,
    setNewCustomNodeData,
    isCreatingNode,
    setIsCreatingNode,
    startCustomNodeCreation,
    cancelCustomNodeCreation,
    
    // ===== Node Type Utilities =====
    getNodeTypeIcon,
    getNodeTypeColor,
    generateNodeId,
    nodeTypeColors,
    
    // ===== Node CRUD Hooks =====
    deleteNodeById,
    deleteEdgeById,
    clearSelection,
    
    // ===== Node Condition Hooks =====
    getConditionCount: getConditionCountWrapper,
    updateConditions: updateConditionsWrapper,
    removeCondition: removeConditionWrapper,
    
    // ===== Node Output Hooks =====
    updateOutput: updateOutputWrapper,
    clearNodeOutput,
    updateNodeChat: updateNodeChatWrapper,
    clearNodeChat: clearNodeChat,
    
    // ===== Node Status Hooks =====
    updateNodeStatus: updateNodeStatusWrapper,
    resetNodeStatus,
    
    // ===== VLM Config Hooks =====
    updateVlmModelConfig: updateVlmModelConfigWrapper,
    updateVlmInput: updateVlmInputWrapper,
    
    // ===== State Management =====
    resetAllNodeStates,
    
    // ===== Chatflow Integration =====
    getChatflowNodeCount,
    refreshChatflowNodes,
  };
};
