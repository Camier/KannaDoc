import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfirmAlert from './ConfirmAlert';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: (key: string) => (str: string) => {
    const translations: Record<string, Record<string, string>> = {
      ConfirmAlert: {
        notice: 'Notice',
        error: 'Error',
        close: 'Close',
      },
    };
    return translations[key]?.[str] || str;
  },
}));

describe('ConfirmAlert Component', () => {
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders success alert correctly', () => {
    render(
      <ConfirmAlert
        type="success"
        message="Operation successful!"
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Notice')).toBeInTheDocument();
    expect(screen.getByText('Operation successful!')).toBeInTheDocument();
    expect(screen.getByText('Close')).toBeInTheDocument();
  });

  it('renders error alert correctly', () => {
    render(
      <ConfirmAlert
        type="error"
        message="Operation failed!"
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Operation failed!')).toBeInTheDocument();
    expect(screen.getByText('Close')).toBeInTheDocument();
  });

  it('applies correct styling for success type', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Success message"
        onCancel={mockOnCancel}
      />
    );

    const titleElement = screen.getByText('Notice');
    expect(titleElement).toHaveClass('text-indigo-500');
  });

  it('applies correct styling for error type', () => {
    const { container } = render(
      <ConfirmAlert
        type="error"
        message="Error message"
        onCancel={mockOnCancel}
      />
    );

    const titleElement = screen.getByText('Error');
    expect(titleElement).toHaveClass('text-red-500');
  });

  it('calls onCancel when close button is clicked', () => {
    render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const closeButton = screen.getByText('Close');
    fireEvent.click(closeButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('renders as fixed overlay', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('fixed');
    expect(overlay).toHaveClass('inset-0');
  });

  it('has correct z-index for modal', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('z-50');
  });

  it('has semi-transparent background', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('bg-black/50');
  });

  it('renders message in scrollable container', () => {
    const longMessage = 'A'.repeat(1000);
    render(
      <ConfirmAlert
        type="success"
        message={longMessage}
        onCancel={mockOnCancel}
      />
    );

    const messageElement = screen.getByText(longMessage);
    expect(messageElement).toBeInTheDocument();
    expect(messageElement.parentElement).toHaveClass('overflow-auto');
  });

  it('displays close button at the end', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const buttonContainer = container.querySelector('div.flex.justify-end');
    expect(buttonContainer).toBeInTheDocument();
  });

  it('has proper button styling', () => {
    render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const closeButton = screen.getByText('Close');
    expect(closeButton).toHaveClass('px-4');
    expect(closeButton).toHaveClass('py-2');
    expect(closeButton).toHaveClass('text-gray-700');
    expect(closeButton).toHaveClass('border');
    expect(closeButton).toHaveClass('border-gray-300');
    expect(closeButton).toHaveClass('rounded-full');
    expect(closeButton).toHaveClass('hover:bg-gray-100');
  });

  it('renders with rounded corners', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const modalContent = container.querySelector('.bg-white');
    expect(modalContent).toHaveClass('rounded-3xl');
  });

  it('centers content both horizontally and vertically', () => {
    const { container } = render(
      <ConfirmAlert
        type="success"
        message="Test message"
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('flex');
    expect(overlay).toHaveClass('items-center');
    expect(overlay).toHaveClass('justify-center');
  });
});
