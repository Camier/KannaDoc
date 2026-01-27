import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Alert from './Alert';

describe('Alert Component', () => {
  it('renders success message when visible', () => {
    render(
      <Alert 
        showAlert={{ 
          show: true, 
          type: 'success', 
          message: 'Operation successful' 
        }} 
      />
    );

    const messageElement = screen.getByText('Operation successful');
    expect(messageElement).toBeInTheDocument();
    
    // Check for success styling (indigo gradient)
    const alertContainer = messageElement.closest('div');
    expect(alertContainer).toHaveClass('opacity-100');
    expect(alertContainer).toHaveClass('from-indigo-500');
  });

  it('renders error message with correct styling', () => {
    render(
      <Alert 
        showAlert={{ 
          show: true, 
          type: 'error', 
          message: 'Operation failed' 
        }} 
      />
    );

    const messageElement = screen.getByText('Operation failed');
    expect(messageElement).toBeInTheDocument();
    
    // Check for error styling (red gradient)
    const alertContainer = messageElement.closest('div');
    expect(alertContainer).toHaveClass('opacity-100');
    expect(alertContainer).toHaveClass('from-red-500');
  });

  it('is hidden when show is false', () => {
    render(
      <Alert 
        showAlert={{ 
          show: false, 
          type: 'success', 
          message: 'Hidden message' 
        }} 
      />
    );

    const messageElement = screen.getByText('Hidden message');
    const alertContainer = messageElement.closest('div');
    expect(alertContainer).toHaveClass('opacity-0');
  });
});
