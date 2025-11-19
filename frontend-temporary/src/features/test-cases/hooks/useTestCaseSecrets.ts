import { useState, useCallback } from 'react';

export const useTestCaseSecrets = () => {
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [copiedSecret, setCopiedSecret] = useState<string | null>(null);

  const toggleSecretVisibility = useCallback((secretId: string) => {
    setVisibleSecrets(prev => {
      const newVisibleSecrets = new Set(prev);
      if (newVisibleSecrets.has(secretId)) {
        newVisibleSecrets.delete(secretId);
      } else {
        newVisibleSecrets.add(secretId);
      }
      return newVisibleSecrets;
    });
  }, []);

  const copySecret = useCallback(async (value: string, secretId: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedSecret(secretId);
      setTimeout(() => setCopiedSecret(null), 2000);
    } catch (error) {
      console.error('Failed to copy secret:', error);
    }
  }, []);

  return {
    visibleSecrets,
    copiedSecret,
    toggleSecretVisibility,
    copySecret,
  };
};
