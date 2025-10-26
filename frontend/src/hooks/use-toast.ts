import * as React from 'react';

type ToastProps = {
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
};

export function useToast() {
  const toast = React.useCallback(({ title, description, variant = 'default' }: ToastProps) => {
    // Simple console-based toast for now
    // In a real app, this would integrate with a toast notification library
    const prefix = variant === 'destructive' ? '❌' : '✅';
    console.log(`${prefix} ${title}${description ? `: ${description}` : ''}`);

    // Also show browser alert for visibility during testing
    if (variant === 'destructive') {
      alert(`Error: ${title}\n${description || ''}`);
    }
  }, []);

  return { toast };
}
