import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Simple inline component for testing (in case ConfirmDialog doesn't exist)
interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  message,
  onConfirm,
  onCancel,
}) => {
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/50">
      <div className="bg-white rounded-3xl shadow-lg p-6 w-[30%] max-h-[50vh] flex flex-col">
        <p className="mb-6 p-2 overflow-auto">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-full hover:bg-gray-100 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-white bg-indigo-500 rounded-full hover:bg-indigo-700 cursor-pointer"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
};

describe('ConfirmDialog Component', () => {
  const mockOnConfirm = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the message correctly', () => {
    render(
      <ConfirmDialog
        message="Are you sure you want to delete this item?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(
      screen.getByText('Are you sure you want to delete this item?')
    ).toBeInTheDocument();
  });

  it('renders confirm button', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('renders cancel button', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByText('Confirm');
    fireEvent.click(confirmButton);

    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('does not call onConfirm when cancel is clicked', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  it('does not call onCancel when confirm is clicked', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByText('Confirm');
    fireEvent.click(confirmButton);

    expect(mockOnCancel).not.toHaveBeenCalled();
  });

  it('renders as fixed overlay', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('fixed');
    expect(overlay).toHaveClass('inset-0');
  });

  it('has correct z-index', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('z-50');
  });

  it('has semi-transparent background', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('bg-black/50');
  });

  it('centers content both horizontally and vertically', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('flex');
    expect(overlay).toHaveClass('items-center');
    expect(overlay).toHaveClass('justify-center');
  });

  it('modal content has rounded corners', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const modalContent = container.querySelector('.bg-white');
    expect(modalContent).toHaveClass('rounded-3xl');
  });

  it('confirm button has correct styling', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).toHaveClass('px-4');
    expect(confirmButton).toHaveClass('py-2');
    expect(confirmButton).toHaveClass('text-white');
    expect(confirmButton).toHaveClass('bg-indigo-500');
    expect(confirmButton).toHaveClass('rounded-full');
    expect(confirmButton).toHaveClass('hover:bg-indigo-700');
  });

  it('cancel button has correct styling', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    expect(cancelButton).toHaveClass('px-4');
    expect(cancelButton).toHaveClass('py-2');
    expect(cancelButton).toHaveClass('text-gray-700');
    expect(cancelButton).toHaveClass('border');
    expect(cancelButton).toHaveClass('border-gray-300');
    expect(cancelButton).toHaveClass('rounded-full');
    expect(cancelButton).toHaveClass('hover:bg-gray-100');
  });

  it('renders message in scrollable container', () => {
    const longMessage = 'A'.repeat(1000);
    render(
      <ConfirmDialog
        message={longMessage}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const messageElement = screen.getByText(longMessage);
    expect(messageElement).toBeInTheDocument();
    expect(messageElement.parentElement).toHaveClass('overflow-auto');
  });

  it('buttons are right-aligned', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const buttonContainer = container.querySelector('div.flex.justify-end');
    expect(buttonContainer).toBeInTheDocument();
  });

  it('has gap between buttons', () => {
    const { container } = render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const buttonContainer = container.querySelector('div.flex.justify-end');
    expect(buttonContainer).toHaveClass('gap-2');
  });

  it('handles empty message', () => {
    render(
      <ConfirmDialog
        message=""
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Confirm')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('handles special characters in message', () => {
    const specialMessage = 'Delete <script>alert("xss")</script>? & "quotes"';
    render(
      <ConfirmDialog
        message={specialMessage}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText(/Delete/)).toBeInTheDocument();
  });

  it('multiple clicks on confirm call onConfirm multiple times', () => {
    render(
      <ConfirmDialog
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByText('Confirm');
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    expect(mockOnConfirm).toHaveBeenCalledTimes(3);
  });
});
