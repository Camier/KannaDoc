import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NodeTypeSelector from './NodeTypeSelector';
import { CustomNode } from '@/types/types';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: (key: string) => (str: string) => {
    const translations: Record<string, any> = {
      NodeTypeSelector: {
        baseNodeSection: 'Base Nodes',
        customNodeSection: 'Custom Nodes',
        searchPlaceholder: 'Search nodes...',
        deleteConfirm: 'Delete node "{nodeName}"?',
        label: {
          start: 'Start',
          end: 'End',
          llm: 'LLM',
          knowledge: 'Knowledge',
          condition: 'Condition',
          loop: 'Loop',
          function: 'Function',
          mcp: 'MCP',
          vlm: 'LLM',
          output: 'Output',
        },
      },
    };
    
    const namespace = translations[key];
    if (!namespace) return str;

    if (str.includes('.')) {
      return str.split('.').reduce((obj, k) => obj?.[k], namespace) || str;
    }
    
    return namespace[str] || str;
  },
}));

// Mock stores
vi.mock('@/stores/flowStore', () => ({
  useFlowStore: vi.fn((selector) => {
    const state = {
      selectedType: null,
      setSelectedType: vi.fn(),
    };
    return selector ? selector(state) : state;
  }),
}));

// Mock ConfirmDialog
vi.mock('../ConfirmDialog', () => ({
  default: ({ onConfirm, onCancel, message }: any) => (
    <div data-testid="confirm-dialog">
      <p>{message}</p>
      <button onClick={onConfirm}>Confirm</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

// Mock date utility
vi.mock('@/utils/date', () => ({
  parseToBeijingTime: vi.fn((dateStr: string) => {
    const date = new Date(dateStr);
    return {
      toISOString: () => date.toISOString(),
    };
  }),
}));

describe('NodeTypeSelector Component', () => {
  const mockAddNode = vi.fn();
  const mockAddCustomNode = vi.fn();
  const mockDeleteCustomNode = vi.fn();
  const mockSetCustomNodes = vi.fn();

  const mockCustomNodes: Record<string, CustomNode> = {
    'customNode1': {
      id: 'customNode1',
      name: 'Custom Node 1',
      type: 'custom',
      data: {},
      position: { x: 0, y: 0 },
    },
    'customNode2': {
      id: 'customNode2',
      name: 'Custom Node 2',
      type: 'custom',
      data: {},
      position: { x: 0, y: 0 },
    },
  };

  const defaultProps = {
    deleteCustomNode: mockDeleteCustomNode,
    workflowName: 'Test Workflow',
    addNode: mockAddNode,
    addCustomNode: mockAddCustomNode,
    customNodes: mockCustomNodes,
    setCustomNodes: mockSetCustomNodes,
    lastModifyTime: '2024-01-27T10:30:00',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders workflow name correctly', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    expect(screen.getByText('Test Workflow')).toBeInTheDocument();
  });

  it('renders last modified time', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    expect(screen.getByText(/2024-01-27/)).toBeInTheDocument();
  });

  it('renders base node section', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    expect(screen.getByText('Base Nodes')).toBeInTheDocument();
  });

  it('renders custom node section', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    expect(screen.getByText('Custom Nodes')).toBeInTheDocument();
  });

  it('renders all custom nodes', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    expect(screen.getByText('customNode1')).toBeInTheDocument();
    expect(screen.getByText('customNode2')).toBeInTheDocument();
  });

  it('calls addNode when base node is clicked', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    const startNode = screen.getByText('Start');
    fireEvent.click(startNode);

    expect(mockAddNode).toHaveBeenCalledWith('start');
  });

  it('calls addCustomNode when custom node is clicked', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    const customNode = screen.getByText('customNode1');
    fireEvent.click(customNode);

    expect(mockAddCustomNode).toHaveBeenCalledWith('customNode1');
  });

  it('filters custom nodes based on search term', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText('Search nodes...');
    fireEvent.change(searchInput, { target: { value: 'customNode1' } });

    expect(screen.getByText('customNode1')).toBeInTheDocument();
    expect(screen.queryByText('customNode2')).not.toBeInTheDocument();
  });

  it('displays all nodes when search is empty', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText('Search nodes...');
    fireEvent.change(searchInput, { target: { value: '' } });

    expect(screen.getByText('customNode1')).toBeInTheDocument();
    expect(screen.getByText('customNode2')).toBeInTheDocument();
  });

  it('search is case-insensitive', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText('Search nodes...');
    fireEvent.change(searchInput, { target: { value: 'CUSTOMNODE1' } });

    expect(screen.getByText('customNode1')).toBeInTheDocument();
  });

  it('shows delete confirmation when delete icon is clicked', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const deleteIcons = container.querySelectorAll('svg.size-4\\.5.shrink-0');
    expect(deleteIcons.length).toBeGreaterThan(0);
    
    fireEvent.click(deleteIcons[0]);
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
  });

  it('renders search input in custom nodes section', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText('Search nodes...');
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveClass('w-full');
  });

  it('renders search icon', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const searchIcon = container.querySelector('svg.absolute.right-2\\.5');
    expect(searchIcon).toBeInTheDocument();
  });

  it('renders workflow icon', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const workflowIcon = container.querySelector('svg.size-5');
    expect(workflowIcon).toBeInTheDocument();
  });

  it('renders node icons for each node type', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const icons = container.querySelectorAll('svg');
    expect(icons.length).toBeGreaterThan(0);
  });

  it('handles empty custom nodes', () => {
    const props = {
      ...defaultProps,
      customNodes: {},
    };

    render(<NodeTypeSelector {...props} />);

    expect(screen.getByText('Custom Nodes')).toBeInTheDocument();
    expect(screen.queryByText('customNode1')).not.toBeInTheDocument();
  });

  it('renders multiple base nodes', () => {
    render(<NodeTypeSelector {...defaultProps} />);

    expect(screen.getByText('Start')).toBeInTheDocument();
    expect(screen.getByText('Loop')).toBeInTheDocument();
    expect(screen.getByText('LLM')).toBeInTheDocument();
  });

  it('has proper styling for node items', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const nodeItems = container.querySelectorAll('.cursor-pointer');
    expect(nodeItems.length).toBeGreaterThan(0);
  });

  it('base nodes section has border separator', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const separators = container.querySelectorAll('.border-b-2');
    expect(separators.length).toBeGreaterThan(0);
  });

  it('custom nodes section has border separator', () => {
    const { container } = render(<NodeTypeSelector {...defaultProps} />);

    const separators = container.querySelectorAll('.border-b-2');
    expect(separators.length).toBeGreaterThan(0);
  });
});
