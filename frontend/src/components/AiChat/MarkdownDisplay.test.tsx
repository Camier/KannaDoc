import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MarkdownDisplay from './MarkdownDisplay';
import { Message } from '@/types/types';
import { NextIntlClientProvider } from 'next-intl';
import * as base64Processor from '@/utils/file';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: (key: string) => (str: string) => {
    const translations: Record<string, Record<string, string>> = {
      MarkdownDisplay: {
        deepThinking: 'Deep Thinking',
        copy: 'Copy',
        copied: 'Copied',
        copyFallback: 'Please copy manually',
        totalTokenUsage: 'Total: ',
        completionTokenUsage: 'Completion: ',
        promptTokenUsage: 'Prompt: ',
      },
    };
    return translations[key]?.[str] || str;
  },
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock base64Processor
vi.mock('@/utils/file', () => ({
  base64Processor: {
    encode: (str: string) => str,
    decode: (str: string) => str,
  },
}));

// Mock navigator.clipboard
// In happy-dom/jsdom the `clipboard` property can be a getter-only.
// Define it explicitly to avoid "has only a getter" crashes during module evaluation.
const mockClipboard = {
  writeText: vi.fn(() => Promise.resolve()),
};

Object.defineProperty(navigator, "clipboard", {
  value: mockClipboard,
  writable: true,
});

describe('MarkdownDisplay Component', () => {
  const mockMessage: Message = {
    type: 'text',
    content: 'Test message',
    from: 'ai',
    messageId: '1',
  };

  const defaultProps = {
    md_text: '# Test Header\n\nThis is a test message.',
    message: mockMessage,
    showTokenNumber: false,
    isThinking: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders markdown content correctly', () => {
    render(<MarkdownDisplay {...defaultProps} />);

    expect(screen.getByText('Test Header')).toBeInTheDocument();
    expect(screen.getByText('This is a test message.')).toBeInTheDocument();
  });

  it('renders user messages with different styling', () => {
    const userProps = {
      ...defaultProps,
      message: { ...mockMessage, from: 'user' as const },
    };

    const { container } = render(<MarkdownDisplay {...userProps} />);

    const messageContainer = container.querySelector('.ml-auto');
    expect(messageContainer).toBeInTheDocument();
    expect(messageContainer).toHaveClass('bg-indigo-200');
  });

  it('renders AI messages without user styling', () => {
    const { container } = render(<MarkdownDisplay {...defaultProps} />);

    const messageContainer = container.querySelector('.mr-auto');
    expect(messageContainer).toBeInTheDocument();
    expect(messageContainer).not.toHaveClass('bg-indigo-200');
  });

  it('displays thinking state when isThinking is true', () => {
    const thinkingProps = {
      ...defaultProps,
      isThinking: true,
      md_text: 'Thinking content',
    };

    render(<MarkdownDisplay {...thinkingProps} />);

    expect(screen.getByText('Deep Thinking')).toBeInTheDocument();
  });

  it('toggles thinking content visibility', async () => {
    const thinkingProps = {
      ...defaultProps,
      isThinking: true,
      md_text: 'Hidden thinking content',
    };

    const { container } = render(<MarkdownDisplay {...thinkingProps} />);

    const toggleButton = screen.getByText('Deep Thinking').closest('div');
    expect(toggleButton).toBeInTheDocument();

    // Initially visible
    expect(screen.getByText('Hidden thinking content')).toBeInTheDocument();

    // Click to hide
    if (toggleButton) {
      fireEvent.click(toggleButton);
      await waitFor(() => {
        expect(screen.queryByText('Hidden thinking content')).not.toBeInTheDocument();
      });
    }
  });

  it('displays token usage when showTokenNumber is true', () => {
    const tokenProps = {
      ...defaultProps,
      message: {
        ...mockMessage,
        token_number: {
          total_token: 100,
          completion_tokens: 60,
          prompt_tokens: 40,
        },
      },
      showTokenNumber: true,
    };

    render(<MarkdownDisplay {...tokenProps} />);

    expect(screen.getByText(/Total:/)).toBeInTheDocument();
    expect(screen.getByText(/100/)).toBeInTheDocument();
    expect(screen.getByText(/Completion:/)).toBeInTheDocument();
    expect(screen.getByText(/60/)).toBeInTheDocument();
    expect(screen.getByText(/Prompt:/)).toBeInTheDocument();
    expect(screen.getByText(/40/)).toBeInTheDocument();
  });

  it('does not display token usage when showTokenNumber is false', () => {
    const tokenProps = {
      ...defaultProps,
      message: {
        ...mockMessage,
        token_number: {
          total_token: 100,
          completion_tokens: 60,
          prompt_tokens: 40,
        },
      },
      showTokenNumber: false,
    };

    render(<MarkdownDisplay {...tokenProps} />);

    expect(screen.queryByText(/Total:/)).not.toBeInTheDocument();
  });

  it('renders code blocks with copy button', () => {
    const codeProps = {
      ...defaultProps,
      md_text: '```javascript\nconst test = "hello";\n```',
    };

    const { container } = render(<MarkdownDisplay {...codeProps} />);

    expect(screen.getByText('javascript')).toBeInTheDocument();
    expect(screen.getByText('const test = "hello";')).toBeInTheDocument();

    // Check for copy button
    const copyButton = container.querySelector('button[aria-label="Copy"]');
    expect(copyButton).toBeInTheDocument();
  });

  it('copies code to clipboard when copy button is clicked', async () => {
    const codeProps = {
      ...defaultProps,
      md_text: '```python\nprint("hello")\n```',
    };

    const { container } = render(<MarkdownDisplay {...codeProps} />);

    const copyButton = container.querySelector('button[aria-label="Copy"]');
    expect(copyButton).toBeInTheDocument();

    if (copyButton) {
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith('print("hello")');
      });
    }
  });

  it('renders inline code correctly', () => {
    const inlineCodeProps = {
      ...defaultProps,
      md_text: 'This is `inline code` test.',
    };

    render(<MarkdownDisplay {...inlineCodeProps} />);

    expect(screen.getByText('This is')).toBeInTheDocument();
    expect(screen.getByText('inline code')).toBeInTheDocument();
    expect(screen.getByText('test.')).toBeInTheDocument();
  });

  it('renders markdown tables correctly', () => {
    const tableProps = {
      ...defaultProps,
      md_text: '| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |',
    };

    render(<MarkdownDisplay {...tableProps} />);

    expect(screen.getByText('Header 1')).toBeInTheDocument();
    expect(screen.getByText('Header 2')).toBeInTheDocument();
    expect(screen.getByText('Cell 1')).toBeInTheDocument();
    expect(screen.getByText('Cell 2')).toBeInTheDocument();
  });

  it('renders links with correct attributes', () => {
    const linkProps = {
      ...defaultProps,
      md_text: '[Test Link](https://example.com)',
    };

    const { container } = render(<MarkdownDisplay {...linkProps} />);

    const link = container.querySelector('a[href="https://example.com"]');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('handles empty content gracefully', () => {
    const emptyProps = {
      ...defaultProps,
      md_text: '',
    };

    const { container } = render(<MarkdownDisplay {...emptyProps} />);

    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders markdown lists correctly', () => {
    const listProps = {
      ...defaultProps,
      md_text: '- Item 1\n- Item 2\n- Item 3',
    };

    render(<MarkdownDisplay {...listProps} />);

    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
    expect(screen.getByText('Item 3')).toBeInTheDocument();
  });
});
