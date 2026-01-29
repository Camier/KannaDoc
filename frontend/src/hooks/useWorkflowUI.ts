// frontend/src/hooks/useWorkflowUI.ts
/**
 * WorkflowUI Hook
 *
 * Centralized UI state management for FlowEditor component.
 * Extracts all UI state patterns (debug, full screen, alerts, etc.)
 * into reusable hooks with clean action interfaces.
 *
 * This hook consolidates 35+ useState declarations from FlowEditor.tsx
 * into a single, cohesive state management interface.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useGlobalStore } from '@/stores/WorkflowVariableStore';
import { useAuthStore } from '@/stores/authStore';

export interface WorkflowUIState {
  // ===== Execution State =====
  taskId: string;
  isExecuting: boolean;
  setIsExecuting: (value: boolean) => void;
  isPaused: boolean;
  setIsPaused: (value: boolean) => void;
  isError: boolean;
  setIsError: (value: boolean) => void;
  errorMessage: string;
  setErrorMessage: (value: string) => void;

  // ===== Debug State =====
  isDebugMode: boolean;
  setIsDebugMode: (value: boolean) => void;
  resumeDebugTaskId: string;
  setResumeDebugTaskId: (value: string) => void;
  resumeInputTaskId: string;
  setResumeInputTaskId: (value: string) => void;

  // ===== UI Preferences =====
  isFullScreen: boolean;
  setIsFullScreen: (value: boolean) => void;
  isCodeFullScreen: boolean;
  setIsCodeFullScreen: (value: boolean) => void;
  showOutput: boolean;
  setShowOutput: (value: boolean) => void;
  sendInputDisabled: boolean;
  setSendInputDisabled: (value: boolean) => void;

  // ===== Alert Management =====
  showAlert: boolean;
  setShowAlert: (value: boolean) => void;
  alertMessage: string;
  setAlertMessage: (value: string) => void;
  alertType: 'success' | 'error' | 'warning';
  setAlertType: (value: 'success' | 'error' | 'warning') => void;
  triggerAlert: (message: string, type?: 'success' | 'error' | 'warning') => void;
  hideAlert: () => void;

  // ===== Custom Node State =====
  customNodes: Record<string, any>;
  setCustomNodes: (value: Record<string, any>) => void;
  showAddNodeDialog: boolean;
  setShowAddNodeDialog: (value: boolean) => void;
  openAddNodeDialog: () => void;
  closeAddNodeDialog: () => void;
  addNodeNameError: string | null;
  setAddNodeNameError: (value: string | null) => void;
  newCustomNodeName: string;
  setNewCustomNodeName: (value: string) => void;
  newCustomNodeData: any;
  setNewCustomNodeData: (value: any) => void;
  isCreatingNode: boolean;
  setIsCreatingNode: (value: boolean) => void;
  createCustomNode: (name: string, data: any) => void;
  updateCustomNode: (id: string, name: string, data: any) => void;
  deleteCustomNode: (id: string) => void;

  // ===== File Management =====
  sendingFiles: any[];
  setSendingFiles: (value: any[]) => void;
  fileMessages: Record<string, any[]>;
  setFileMessages: (value: Record<string, any[]>) => void;
  addFileMessage: (fileId: string, message: any) => void;
  tempKnowledgeBaseId: string;
  setTempKnowledgeBaseId: (value: string) => void;
  cleanTempKnowledgeBase: boolean;
  setCleanTempKnowledgeBase: (value: boolean) => void;
  clearTempKnowledgeBase: () => void;

  // ===== Docker Image State =====
  dockerImageUse: string;
  setDockerImageUse: (value: string) => void;
  saveDockerImage: boolean;
  setSaveDockerImage: (value: boolean) => void;
  saveDockerImageName: string;
  setSaveDockerImageName: (value: string) => void;
  saveDockerImageTag: string;
  setSaveDockerImageTag: (value: string) => void;
  isSavingDockerImage: boolean;
  setIsSavingDockerImage: (value: boolean) => void;
  refreshDockerImages: boolean;
  setRefreshDockerImages: (value: boolean) => void;
  runningChatflowLLMNodes: any[];
  setRunningChatflowLLMNodes: (value: any[]) => void;
  eachChatflowLLMMessages: Record<string, any[]>;
  setEachChatflowLLMMessages: (value: Record<string, any[]>) => void;
  addChatflowLLMMessage: (nodeId: string, message: any) => void;
  showConfirmClear: boolean;
  setConfirmClear: (value: boolean) => void;
  confirmClearWorkflow: () => void;
  triggerSaveDockerImage: () => void;

  // ===== Chatflow State =====
  chatflowId: string;
  setChatflowId: (value: string) => void;

  // ===== Execution Actions =====
  startExecution: () => void;
  pauseExecution: () => void;
  resumeExecution: () => void;
  stopExecution: () => void;

  // ===== Debug Actions =====
  toggleDebugMode: () => void;
  resumeFromDebugTaskId: (taskId: string) => void;
  resumeFromInputTaskId: (taskId: string) => void;

  // ===== UI Preference Actions =====
  toggleFullScreen: () => void;
  toggleCodeFullScreen: () => void;
  toggleOutput: () => void;
  toggleSendInput: () => void;
}

export const useWorkflowUI = (taskId: string = ''): WorkflowUIState => {
  // ===== Execution State =====
  const [currentTaskId, setCurrentTaskId] = useState<string>(taskId || '');
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  
  // ===== Debug State =====
  const [isDebugMode, setIsDebugMode] = useState<boolean>(false);
  const [resumeDebugTaskId, setResumeDebugTaskId] = useState<string>('');
  const [resumeInputTaskId, setResumeInputTaskId] = useState<string>('');
  
  // ===== UI Preferences =====
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
  const [isCodeFullScreen, setIsCodeFullScreen] = useState<boolean>(false);
  const [showOutput, setShowOutput] = useState<boolean>(false);
  const [sendInputDisabled, setSendInputDisabled] = useState<boolean>(true);
  
  // ===== Alert Management =====
  const [showAlert, setShowAlert] = useState<boolean>(false);
  const [alertMessage, setAlertMessage] = useState<string>('');
  const [alertType, setAlertType] = useState<'success' | 'error' | 'warning'>('success');
  
  // ===== Custom Node State =====
  const [customNodes, setCustomNodes] = useState<Record<string, any>>({});
  const [showAddNodeDialog, setShowAddNodeDialog] = useState<boolean>(false);
  const [addNodeNameError, setAddNodeNameError] = useState<string | null>(null);
  const [newCustomNodeName, setNewCustomNodeName] = useState<string>('');
  const [newCustomNodeData, setNewCustomNodeData] = useState<any>(null);
  const [isCreatingNode, setIsCreatingNode] = useState<boolean>(false);
  
  // ===== File Management =====
  const [sendingFiles, setSendingFiles] = useState<any[]>([]);
  const [fileMessages, setFileMessages] = useState<Record<string, any[]>>({});
  const [tempKnowledgeBaseId, setTempKnowledgeBaseId] = useState<string>('');
  const [cleanTempKnowledgeBase, setCleanTempKnowledgeBase] = useState<boolean>(false);
  
  // ===== Docker Image State =====
  const [dockerImageUse, setDockerImageUse] = useState<string>('python-sandbox:latest');
  const [saveDockerImage, setSaveDockerImage] = useState<boolean>(false);
  const [saveDockerImageName, setSaveDockerImageName] = useState<string>('');
  const [saveDockerImageTag, setSaveDockerImageTag] = useState<string>('');
  const [isSavingDockerImage, setIsSavingDockerImage] = useState<boolean>(false);
  const [refreshDockerImages, setRefreshDockerImages] = useState<boolean>(false);
  const [runningChatflowLLMNodes, setRunningChatflowLLMNodes] = useState<any[]>([]);
  const [eachChatflowLLMMessages, setEachChatflowLLMMessages] = useState<Record<string, any[]>>({});
  const [showConfirmClear, setShowConfirmClear] = useState<boolean>(false);
  
  // ===== Chatflow State =====
  const [chatflowId, setChatflowId] = useState<string>('');
  
  // ===== Store References =====
  const { globalDebugVariables, reset, setGlobalDebugVariables } = useGlobalStore();
  const { user } = useAuthStore();
  
  // ===== Execution Hooks =====
  const startExecution = useCallback(() => {
    if (!currentTaskId) return;
    setIsExecuting(true);
    setIsPaused(false);
    setIsError(false);
    setErrorMessage('');
  }, [currentTaskId]);
  
  const pauseExecution = useCallback(() => {
    setIsPaused(true);
  }, []);
  
  const resumeExecution = useCallback(() => {
    setIsPaused(false);
  }, []);
  
  const stopExecution = useCallback(() => {
    setIsExecuting(false);
    setIsPaused(false);
    setCurrentTaskId('');
    setResumeDebugTaskId('');
    setResumeInputTaskId('');
  }, []);
  
  // ===== Debug Hooks =====
  const toggleDebugMode = useCallback(() => {
    setIsDebugMode(prev => !prev);
  }, []);
  
  const resumeFromDebugTaskId = useCallback((taskId: string) => {
    setResumeDebugTaskId(taskId);
  }, []);
  
  const resumeFromInputTaskId = useCallback((taskId: string) => {
    setResumeInputTaskId(taskId);
  }, []);
  
  // ===== UI Preference Hooks =====
  const toggleFullScreen = useCallback(() => {
    setIsFullScreen(prev => !prev);
    setIsCodeFullScreen(false);
  }, []);
  
  const toggleCodeFullScreen = useCallback(() => {
    setIsCodeFullScreen(prev => !prev);
    setIsFullScreen(false);
  }, []);
  
  const toggleOutput = useCallback(() => {
    setShowOutput(prev => !prev);
  }, []);
  
  const toggleSendInput = useCallback(() => {
    setSendInputDisabled(prev => !prev);
  }, []);
  
  // ===== Alert Hooks =====
  const triggerAlert = useCallback((message: string, type: 'success' | 'error' | 'warning' = 'success') => {
    setShowAlert(true);
    setAlertMessage(message);
    setAlertType(type);
  }, []);
  
  const hideAlert = useCallback(() => {
    setShowAlert(false);
    setAlertMessage('');
  }, []);
  
  // ===== Custom Node Hooks =====
  const openAddNodeDialog = useCallback(() => {
    setShowAddNodeDialog(true);
    setAddNodeNameError(null);
    setNewCustomNodeName('');
    setNewCustomNodeData(null);
  }, []);

  const closeAddNodeDialog = useCallback(() => {
    setShowAddNodeDialog(false);
    setAddNodeNameError(null);
    setNewCustomNodeName('');
    setNewCustomNodeData(null);
  }, []);
  
  const createCustomNode = useCallback((name: string, data: any) => {
    setIsCreatingNode(true);
    setCustomNodes(prev => ({ ...prev, [Date.now().toString()]: { name, data, type: 'custom' } }));
    setTimeout(() => setIsCreatingNode(false), 1000);
  }, []);
  
  const updateCustomNode = useCallback((id: string, name: string, data: any) => {
    setCustomNodes(prev => ({ ...prev, [id]: { name, data, type: 'custom' } }));
  }, []);
  
  const deleteCustomNode = useCallback((id: string) => {
    setCustomNodes(prev => {
      const { [id]: deleted, ...rest } = prev;
      return rest;
    });
  }, []);
  
  const updateAddNodeNameError = useCallback((error: string | null) => {
    setAddNodeNameError(error);
  }, []);
  
  // ===== File Management Hooks =====
  const updateSendingFiles = useCallback((files: any[]) => {
    setSendingFiles(files);
  }, []);
  
  const addFileMessage = useCallback((fileId: string, message: any) => {
    setFileMessages(prev => ({
      ...prev,
      [fileId]: [...(prev[fileId] || []), message]
    }));
  }, []);
  
  const updateTempKnowledgeBaseId = useCallback((id: string) => {
    setTempKnowledgeBaseId(id);
  }, []);
  
  const clearTempKnowledgeBase = useCallback(() => {
    updateTempKnowledgeBaseId('');
    setCleanTempKnowledgeBase(true);
  }, [updateTempKnowledgeBaseId]);
  
  // ===== Docker Image Hooks =====
  const setDockerImageName = useCallback((name: string) => {
    setSaveDockerImageName(name);
  }, []);
  
  const setDockerImageTag = useCallback((tag: string) => {
    setSaveDockerImageTag(tag);
  }, []);
  
  const triggerSaveDockerImage = useCallback(() => {
    setIsSavingDockerImage(true);
    // Simulate save - would trigger API call
    setTimeout(() => setIsSavingDockerImage(false), 1000);
  }, []);
  
  const updateRefreshDockerImages = useCallback((refresh: boolean) => {
    setRefreshDockerImages(refresh);
  }, []);
  
  const updateRunningChatflowLLMNodes = useCallback((nodes: any[]) => {
    setRunningChatflowLLMNodes(nodes);
  }, []);
  
  const addChatflowLLMMessage = useCallback((nodeId: string, message: any) => {
    setEachChatflowLLMMessages(prev => ({
      ...prev,
      [nodeId]: [...(prev[nodeId] || []), message]
    }));
  }, []);
  
  // ===== Chatflow Hooks =====
  const setConfirmClear = useCallback((confirm: boolean) => {
    setShowConfirmClear(confirm);
  }, []);
  
  const confirmClearWorkflow = useCallback(() => {
    setCustomNodes({});
    setEachChatflowLLMMessages({});
    setShowConfirmClear(false);
  }, []);
  
  // ===== Refs for cleanup =====
  const currentTaskIdRef = useRef<string>(taskId || '');
  
  // Cleanup effect
  useEffect(() => {
    return () => {
      // Reset when taskId changes
      setCurrentTaskId(taskId || '');
    };
  }, [taskId]);
  
  return {
    // ===== State Values =====
    // Execution State
    taskId: currentTaskId,
    isExecuting,
    setIsExecuting,
    isPaused,
    setIsPaused,
    isError,
    setIsError,
    errorMessage,
    setErrorMessage,
    
    // Debug State
    isDebugMode,
    setIsDebugMode,
    resumeDebugTaskId,
    setResumeDebugTaskId,
    resumeInputTaskId,
    setResumeInputTaskId,
    
    // UI Preferences
    isFullScreen,
    setIsFullScreen,
    isCodeFullScreen,
    setIsCodeFullScreen,
    showOutput,
    setShowOutput,
    sendInputDisabled,
    setSendInputDisabled,
    
    // Alert Management
    showAlert,
    setShowAlert,
    alertMessage,
    setAlertMessage,
    alertType,
    setAlertType,
    triggerAlert,
    hideAlert,

    // Custom Node State
    customNodes,
    setCustomNodes,
    showAddNodeDialog,
    setShowAddNodeDialog,
    openAddNodeDialog,
    closeAddNodeDialog,
    addNodeNameError,
    setAddNodeNameError: updateAddNodeNameError,
    newCustomNodeName,
    setNewCustomNodeName,
    newCustomNodeData,
    setNewCustomNodeData,
    isCreatingNode,
    setIsCreatingNode,
    createCustomNode,
    updateCustomNode,
    deleteCustomNode,

    // File Management
    sendingFiles,
    setSendingFiles: updateSendingFiles,
    fileMessages,
    setFileMessages,
    addFileMessage,
    tempKnowledgeBaseId,
    setTempKnowledgeBaseId: updateTempKnowledgeBaseId,
    cleanTempKnowledgeBase,
    setCleanTempKnowledgeBase,
    clearTempKnowledgeBase,

    // Docker Image
    dockerImageUse,
    setDockerImageUse,
    saveDockerImage,
    setSaveDockerImage,
    triggerSaveDockerImage,
    saveDockerImageName,
    setSaveDockerImageName,
    saveDockerImageTag,
    setSaveDockerImageTag,
    isSavingDockerImage,
    setIsSavingDockerImage,
    refreshDockerImages,
    setRefreshDockerImages: updateRefreshDockerImages,
    runningChatflowLLMNodes,
    setRunningChatflowLLMNodes: updateRunningChatflowLLMNodes,
    eachChatflowLLMMessages,
    setEachChatflowLLMMessages,
    addChatflowLLMMessage,
    showConfirmClear,
    setConfirmClear,
    confirmClearWorkflow,
    
    // Chatflow
    chatflowId,
    setChatflowId,
    
    // ===== Execution Actions =====
    startExecution,
    pauseExecution,
    resumeExecution,
    stopExecution,
    
    // ===== Debug Actions =====
    toggleDebugMode,
    resumeFromDebugTaskId,
    resumeFromInputTaskId,
    
    // ===== UI Preference Actions =====
    toggleFullScreen,
    toggleCodeFullScreen,
    toggleOutput,
    toggleSendInput,
  };
};
