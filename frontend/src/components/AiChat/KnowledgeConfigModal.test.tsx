import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import KnowledgeConfigModal from './KnowledgeConfigModal';
import { ModelConfig, KnowledgeBase } from '@/types/types';
import * as knowledgeBaseApi from '@/lib/api/knowledgeBaseApi';
import * as configApi from '@/lib/api/configApi';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: (key: string) => (str: string) => {
    const translations: Record<string, Record<string, string>> = {
      ChatKnowledgeConfigModal: {
        title: 'Knowledge Configuration',
        addKnowledgeBase: 'Add Knowledge Base',
        tutorials: 'Tutorials',
        llmSettings: 'LLM Settings',
        llmEngine: 'LLM Engine',
        addNewConfiguration: 'Add New Configuration',
        llmUrl: 'LLM URL',
        apiKey: 'API Key',
        chooseDB: 'Choose Knowledge Base',
        systemPrompt: 'System Prompt',
        advancedSettings: 'Advanced Settings',
        temperature: 'Temperature',
        range_0_1: '(0-1)',
        useModelDefault: 'Use Model Default',
        maxToken: 'Max Token',
        range_1024_1048576: '(1024-1048576)',
        topP: 'Top-P',
        knowledgeBaseTopK: 'Knowledge Base Top-K',
        range_1_30: '(1-30)',
        retrievalScoreThreshold: 'Retrieval Score Threshold',
        range_0_20: '(0-20)',
        suggestedRetrievalScoreThreshold: 'Suggested: 10-15',
        cancel: 'Cancel',
        save: 'Save',
        deleteModelConfigConfirmation: 'Delete configuration ',
      },
    };
    return translations[key]?.[str] || str;
  },
}));

// Mock API calls
vi.mock('@/lib/api/knowledgeBaseApi');
vi.mock('@/lib/api/configApi');

vi.mock('@/stores/configStore', () => ({
  default: vi.fn(() => ({
    modelConfig: {
      modelId: '1',
      modelName: 'GPT-4',
      modelURL: 'https://api.openai.com/v1',
      apiKey: 'sk-test',
      systemPrompt: 'You are a helpful assistant',
      temperature: 0.7,
      maxLength: 4096,
      topP: 0.9,
      topK: 5,
      scoreThreshold: 10,
      baseUsed: [],
      useTemperatureDefault: false,
      useMaxLengthDefault: false,
      useTopPDefault: false,
      useTopKDefault: false,
      useScoreThresholdDefault: false,
    },
    setModelConfig: vi.fn(),
  })),
}));

vi.mock('react-use', () => ({
  useClickAway: vi.fn(() => {}),
}));

// Mock child components
vi.mock('../AddLLMEngine', () => ({
  default: ({ setShowAddLLM }: any) => (
    <div data-testid="add-llm-engine">
      <button onClick={() => setShowAddLLM(false)}>Close</button>
    </div>
  ),
}));

vi.mock('../ConfirmDialog', () => ({
  default: ({ onConfirm, onCancel }: any) => (
    <div data-testid="confirm-dialog">
      <button onClick={onConfirm}>Confirm</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

describe('KnowledgeConfigModal Component', () => {
  const mockOnSave = vi.fn();
  const mockSetVisible = vi.fn();

  const mockKnowledgeBases: KnowledgeBase[] = [
    { id: '1', name: 'KB 1', selected: false },
    { id: '2', name: 'KB 2', selected: false },
  ];

  const mockModelConfigs: ModelConfig[] = [
    {
      modelId: '1',
      modelName: 'GPT-4',
      modelURL: 'https://api.openai.com/v1',
      apiKey: 'sk-test',
      systemPrompt: 'You are a helpful assistant',
      temperature: 0.7,
      maxLength: 4096,
      topP: 0.9,
      topK: 5,
      scoreThreshold: 10,
      baseUsed: [],
      useTemperatureDefault: false,
      useMaxLengthDefault: false,
      useTopPDefault: false,
      useTopKDefault: false,
      useScoreThresholdDefault: false,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(knowledgeBaseApi, 'getAllKnowledgeBase').mockResolvedValue({
      data: mockKnowledgeBases.map((kb) => ({
        knowledge_base_name: kb.name,
        knowledge_base_id: kb.id,
      })),
    });
    vi.spyOn(configApi, 'getAllModelConfig').mockResolvedValue({
      data: {
        models: mockModelConfigs.map((m) => ({
          model_id: m.modelId,
          model_name: m.modelName,
          model_url: m.modelURL,
          api_key: m.apiKey,
          base_used: m.baseUsed,
          system_prompt: m.systemPrompt,
          temperature: m.temperature,
          max_length: m.maxLength,
          top_P: m.topP,
          top_K: m.topK,
          score_threshold: m.scoreThreshold,
        })),
        selected_model: '1',
      },
    });
  });

  it('renders correctly when visible', () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByText('Knowledge Configuration')).toBeInTheDocument();
    expect(screen.getByText('LLM Settings')).toBeInTheDocument();
    expect(screen.getByText('Choose Knowledge Base')).toBeInTheDocument();
  });

  it('does not render when not visible', () => {
    const { container } = render(
      <KnowledgeConfigModal
        visible={false}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('fetches knowledge bases and model configs on mount', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(knowledgeBaseApi.getAllKnowledgeBase).toHaveBeenCalledWith('testuser');
      expect(configApi.getAllModelConfig).toHaveBeenCalledWith('testuser');
    });
  });

  it('toggles knowledge base selection', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('KB 1')).toBeInTheDocument();
    });

    const kb1Checkbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(kb1Checkbox);

    await waitFor(() => {
      expect(kb1Checkbox).toBeChecked();
    });
  });

  it('opens dropdown when model selector is clicked', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    const modelSelector = screen.getByText('GPT-4').closest('div');
    if (modelSelector) {
      fireEvent.click(modelSelector);
    }

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });
  });

  it('updates model URL input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('https://api.example.com/v1')).toBeInTheDocument();
    });

    const urlInput = screen.getByPlaceholderText('https://api.example.com/v1');
    fireEvent.change(urlInput, { target: { value: 'https://new-url.com/v1' } });

    await waitFor(() => {
      expect(urlInput).toHaveValue('https://new-url.com/v1');
    });
  });

  it('updates API key input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('sk-xxxxxxxx')).toBeInTheDocument();
    });

    const apiKeyInput = screen.getByPlaceholderText('sk-xxxxxxxx');
    fireEvent.change(apiKeyInput, { target: { value: 'sk-new-key' } });

    await waitFor(() => {
      expect(apiKeyInput).toHaveValue('sk-new-key');
    });
  });

  it('updates system prompt textarea', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const systemPromptSection = screen.getByText('System Prompt');
    fireEvent.click(systemPromptSection);

    await waitFor(() => {
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'New system prompt' } });
      expect(textarea).toHaveValue('New system prompt');
    });
  });

  it('updates temperature input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const advancedSection = screen.getByText('Advanced Settings');
    fireEvent.click(advancedSection);

    await waitFor(() => {
      const tempInput = screen.getByDisplayValue('0.7');
      fireEvent.change(tempInput, { target: { value: '0.5' } });
      expect(tempInput).toHaveValue(0.5);
    });
  });

  it('toggles use default temperature checkbox', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const advancedSection = screen.getByText('Advanced Settings');
    fireEvent.click(advancedSection);

    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox');
      const tempDefaultCheckbox = checkboxes.find(cb =>
        cb.nextElementSibling?.textContent?.includes('Use Model Default')
      );
      if (tempDefaultCheckbox) {
        fireEvent.click(tempDefaultCheckbox);
        expect(tempDefaultCheckbox).toBeChecked();
      }
    });
  });

  it('calls onSave with correct config when save is clicked', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalled();
      expect(mockSetVisible).toHaveBeenCalledWith(false);
    });
  });

  it('calls setVisible(false) when cancel is clicked', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(mockSetVisible).toHaveBeenCalledWith(false);
    });
  });

  it('displays delete confirmation dialog when delete icon is clicked', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    const modelSelector = screen.getByText('GPT-4').closest('div');
    if (modelSelector) {
      fireEvent.click(modelSelector);
    }

    await waitFor(() => {
      const deleteButtons = screen.getAllByTestId(/delete/i);
      if (deleteButtons.length > 0) {
        fireEvent.click(deleteButtons[0]);
      }
    });
  });

  it('updates max token input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const advancedSection = screen.getByText('Advanced Settings');
    fireEvent.click(advancedSection);

    await waitFor(() => {
      const maxTokenInput = screen.getByDisplayValue('4096');
      fireEvent.change(maxTokenInput, { target: { value: '8192' } });
      expect(maxTokenInput).toHaveValue(8192);
    });
  });

  it('updates top-P input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const advancedSection = screen.getByText('Advanced Settings');
    fireEvent.click(advancedSection);

    await waitFor(() => {
      const topPInput = screen.getByDisplayValue('0.9');
      fireEvent.change(topPInput, { target: { value: '0.8' } });
      expect(topPInput).toHaveValue(0.8);
    });
  });

  it('updates knowledge base top-K input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const advancedSection = screen.getByText('Advanced Settings');
    fireEvent.click(advancedSection);

    await waitFor(() => {
      const topKInput = screen.getByDisplayValue('5');
      fireEvent.change(topKInput, { target: { value: '10' } });
      expect(topKInput).toHaveValue(10);
    });
  });

  it('updates retrieval score threshold input', async () => {
    render(
      <KnowledgeConfigModal
        visible={true}
        setVisible={mockSetVisible}
        onSave={mockOnSave}
      />
    );

    const advancedSection = screen.getByText('Advanced Settings');
    fireEvent.click(advancedSection);

    await waitFor(() => {
      const scoreThresholdInput = screen.getByDisplayValue('10');
      fireEvent.change(scoreThresholdInput, { target: { value: '15' } });
      expect(scoreThresholdInput).toHaveValue(15);
    });
  });
});
