/**
 * FlowEditor Module
 *
 * Decomposed from a monolithic 2259-line component into focused, single-responsibility modules.
 *
 * Architecture:
 * - FlowEditor.tsx: Main orchestrator (995 lines, -56% reduction)
 * - WorkflowExecutionHandler: SSE and real-time updates (600 lines)
 * - WorkflowToolbar: UI controls and buttons (394 lines)
 * - WorkflowCanvasPanel: Node settings and output display (190 lines)
 * - WorkflowNodeOperations: Node creation and management (230 lines)
 * - WorkflowSaveHandler: Manual and auto-save operations (142 lines)
 * - WorkflowImportExport: Import/export functionality (131 lines)
 *
 * Key improvements:
 * - Each component has a single, well-defined responsibility
 * - Clear separation of concerns
 * - Better testability through isolated components
 * - Improved maintainability with smaller, focused files
 * - Reusable hooks and utilities
 * - Clear data flow and prop interfaces
 *
 * Usage:
 * ```tsx
 * import FlowEditor from '@/components/Workflow/FlowEditor';
 *
 * <FlowEditor
 *   workFlow={workflowData}
 *   setFullScreenFlow={setFullScreen}
 *   fullScreenFlow={isFullScreen}
 * />
 * ```
 */

// Main component (in parent directory)
export { default } from '../FlowEditor';

// Named export for convenience
export { default as FlowEditor } from '../FlowEditor';

// Sub-components (in this directory)
export { WorkflowExecutionHandler } from './WorkflowExecutionHandler';
export { WorkflowToolbar } from './WorkflowToolbar';
export { WorkflowCanvasPanel } from './WorkflowCanvasPanel';

// Hooks (in this directory)
export { useWorkflowImportExport } from './WorkflowImportExport';
export { useWorkflowSaveHandler } from './WorkflowSaveHandler';
export { useWorkflowNodeOperations } from './WorkflowNodeOperations';
