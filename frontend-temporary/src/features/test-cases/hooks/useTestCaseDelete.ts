import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { TestCaseService } from '../services/testCaseService';

export const useTestCaseDelete = (testCaseId?: string) => {
  const navigate = useNavigate();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteTestCase = useCallback(() => {
    setShowDeleteModal(true);
    setDeleteError(null);
  }, []);

  const confirmDeleteTestCase = useCallback(async () => {
    if (!testCaseId) return;
    
    try {
      setDeleteLoading(true);
      setDeleteError(null);
      await TestCaseService.deleteTestCase(testCaseId);
      navigate('/');
    } catch (error: any) {
      console.error('Failed to delete test case:', error);
      setDeleteError(error.message || 'Failed to delete test case');
    } finally {
      setDeleteLoading(false);
    }
  }, [testCaseId, navigate]);

  const cancelDeleteTestCase = useCallback(() => {
    setShowDeleteModal(false);
    setDeleteError(null);
  }, []);

  return {
    showDeleteModal,
    deleteLoading,
    deleteError,
    handleDeleteTestCase,
    confirmDeleteTestCase,
    cancelDeleteTestCase,
  };
};
