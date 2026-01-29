import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SaveCustomNode from './SaveNode';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: (key: string) => (str: string) => {
    const translations: Record<string, Record<string, string>> = {
      SaveCustomNode: {
        title: 'Save Custom Node',
        placeholder: 'Enter node name',
        cancel: 'Cancel',
        confirm: 'Confirm',
      },
    };
    return translations[key]?.[str] || str;
  },
}));

describe('SaveCustomNode Component', () => {
  const mockSetShowSaveNode = vi.fn();
  const mockSetNameError = vi.fn();
  const mockSetNewNodeName = vi.fn();
  const mockOnCreateConfirm = vi.fn();

  const defaultProps = {
    setShowSaveNode: mockSetShowSaveNode,
    nameError: null,
    setNameError: mockSetNameError,
    newNodeName: '',
    setNewNodeName: mockSetNewNodeName,
    onCreateConfirm: mockOnCreateConfirm,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly with default props', () => {
    render(<SaveCustomNode {...defaultProps} />);

    expect(screen.getByText('Save Custom Node')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter node name')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('renders with initial node name value', () => {
    const props = {
      ...defaultProps,
      newNodeName: 'Test Node',
    };

    render(<SaveCustomNode {...props} />);

    const input = screen.getByPlaceholderText('Enter node name') as HTMLInputElement;
    expect(input.value).toBe('Test Node');
  });

  it('updates input value when user types', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const input = screen.getByPlaceholderText('Enter node name');
    fireEvent.change(input, { target: { value: 'New Node Name' } });

    expect(mockSetNewNodeName).toHaveBeenCalledWith('New Node Name');
    expect(mockSetNameError).toHaveBeenCalledWith(null);
  });

  it('calls onCreateConfirm when confirm button is clicked', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const confirmButton = screen.getByText('Confirm');
    fireEvent.click(confirmButton);

    expect(mockOnCreateConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls setShowSaveNode(false) when cancel button is clicked', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockSetShowSaveNode).toHaveBeenCalledWith(false);
  });

  it('displays error message when nameError is present', () => {
    const props = {
      ...defaultProps,
      nameError: 'Node name already exists',
    };

    render(<SaveCustomNode {...props} />);

    expect(screen.getByText('Node name already exists')).toBeInTheDocument();
  });

  it('applies error styling to input when nameError is present', () => {
    const props = {
      ...defaultProps,
      nameError: 'Error message',
    };

    render(<SaveCustomNode {...props} />);

    const input = screen.getByPlaceholderText('Enter node name');
    expect(input).toHaveClass('border-red-500');
  });

  it('does not apply error styling when nameError is null', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const input = screen.getByPlaceholderText('Enter node name');
    expect(input).toHaveClass('border-gray-300');
    expect(input).not.toHaveClass('border-red-500');
  });

  it('calls onCreateConfirm when Enter key is pressed', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const input = screen.getByPlaceholderText('Enter node name');
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnCreateConfirm).toHaveBeenCalledTimes(1);
  });

  it('clears nameError when user starts typing', () => {
    const props = {
      ...defaultProps,
      nameError: 'Initial error',
    };

    render(<SaveCustomNode {...props} />);

    const input = screen.getByPlaceholderText('Enter node name');
    fireEvent.change(input, { target: { value: 'a' } });

    expect(mockSetNameError).toHaveBeenCalledWith(null);
  });

  it('input has autofocus', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const input = screen.getByPlaceholderText('Enter node name');
    expect(input).toHaveFocus();
  });

  it('renders as fixed overlay', () => {
    const { container } = render(<SaveCustomNode {...defaultProps} />);

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('fixed');
    expect(overlay).toHaveClass('inset-0');
  });

  it('has correct z-index for modal', () => {
    const { container } = render(<SaveCustomNode {...defaultProps} />);

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('z-50');
  });

  it('has semi-transparent background', () => {
    const { container } = render(<SaveCustomNode {...defaultProps} />);

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('bg-black/50');
  });

  it('modal content has rounded corners', () => {
    const { container } = render(<SaveCustomNode {...defaultProps} />);

    const modalContent = container.querySelector('.bg-gray-800');
    expect(modalContent).toHaveClass('rounded-3xl');
  });

  it('centers content both horizontally and vertically', () => {
    const { container } = render(<SaveCustomNode {...defaultProps} />);

    const overlay = container.firstChild as HTMLElement;
    expect(overlay).toHaveClass('flex');
    expect(overlay).toHaveClass('items-center');
    expect(overlay).toHaveClass('justify-center');
  });

  it('displays icon in header', () => {
    const { container } = render(<SaveCustomNode {...defaultProps} />);

    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveClass('size-6');
  });

  it('confirm button has correct styling', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).toHaveClass('px-4');
    expect(confirmButton).toHaveClass('py-2');
    expect(confirmButton).toHaveClass('text-white');
    expect(confirmButton).toHaveClass('bg-indigo-500');
    expect(confirmButton).toHaveClass('rounded-full');
    expect(confirmButton).toHaveClass('hover:bg-indigo-700');
  });

  it('cancel button has correct styling', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const cancelButton = screen.getByText('Cancel');
    expect(cancelButton).toHaveClass('px-4');
    expect(cancelButton).toHaveClass('py-2');
    expect(cancelButton).toHaveClass('text-gray-700');
    expect(cancelButton).toHaveClass('border');
    expect(cancelButton).toHaveClass('border-gray-300');
    expect(cancelButton).toHaveClass('rounded-full');
    expect(cancelButton).toHaveClass('hover:bg-gray-100');
  });

  it('does not call onCreateConfirm for other key presses', () => {
    render(<SaveCustomNode {...defaultProps} />);

    const input = screen.getByPlaceholderText('Enter node name');
    fireEvent.keyDown(input, { key: 'a' });
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(mockOnCreateConfirm).not.toHaveBeenCalled();
  });
});
