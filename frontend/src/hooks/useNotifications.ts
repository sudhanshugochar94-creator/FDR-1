import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Notification } from '@/types';

const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: 'notif-1',
    title: 'High Priority Duplicate Flagged',
    message: 'Potential duplicate detected between FDR-2024-8901 and FDR-2023-1102 (State Bank of India).',
    notification_type: 'DUPLICATE_ALERT',
    entity_type: 'fdr',
    entity_id: 'fdr-8901',
    is_read: false,
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
  },
  {
    id: 'notif-2',
    title: 'Maturity Threshold Approaching',
    message: 'FDR-2022-4412 for National Institute of Design matures in 14 days.',
    notification_type: 'MATURITY_WARNING',
    entity_type: 'fdr',
    entity_id: 'fdr-4412',
    is_read: false,
    due_date: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
  },
  {
    id: 'notif-3',
    title: 'Bank Verification Response Received',
    message: 'Punjab National Bank confirmed authenticity for FDR-2024-3390.',
    notification_type: 'VERIFICATION_SUCCESS',
    entity_type: 'fdr',
    entity_id: 'fdr-3390',
    is_read: true,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
  },
  {
    id: 'notif-4',
    title: 'Correction Required by Reviewer',
    message: 'Branch IFSC mismatch flagged on FDR-2024-7721 submitted by Delhi Tech University.',
    notification_type: 'CORRECTION_REQUIRED',
    entity_type: 'fdr',
    entity_id: 'fdr-7721',
    is_read: false,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
];

export const useNotifications = () => {
  const queryClient = useQueryClient();
  const [localNotifications, setLocalNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);

  const { data: notifications = localNotifications, isLoading, isError, refetch } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      try {
        const res = await apiClient.get<Notification[]>('/api/notifications');
        return res.data;
      } catch (err) {
        // Return local state if backend API is not available
        return localNotifications;
      }
    },
    staleTime: 30000,
  });

  // Keep local notifications in sync when fetched
  useEffect(() => {
    if (notifications && notifications.length > 0) {
      setLocalNotifications(notifications);
    }
  }, [notifications]);

  const markAsReadMutation = useMutation({
    mutationFn: async (id: string) => {
      try {
        await apiClient.patch(`/api/notifications/${id}/read`);
      } catch (e) {
        // Fallback local update
      }
      return id;
    },
    onSuccess: (id) => {
      setLocalNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      queryClient.setQueryData<Notification[]>(['notifications'], (old) =>
        old ? old.map((n) => (n.id === id ? { ...n, is_read: true } : n)) : []
      );
    },
  });

  const markAllAsReadMutation = useMutation({
    mutationFn: async () => {
      try {
        await apiClient.post('/api/notifications/mark-all-read');
      } catch (e) {
        // Fallback local update
      }
    },
    onSuccess: () => {
      setLocalNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      queryClient.setQueryData<Notification[]>(['notifications'], (old) =>
        old ? old.map((n) => ({ ...n, is_read: true })) : []
      );
    },
  });

  const markAsRead = useCallback(
    (id: string) => {
      markAsReadMutation.mutate(id);
    },
    [markAsReadMutation]
  );

  const markAllAsRead = useCallback(() => {
    markAllAsReadMutation.mutate();
  }, [markAllAsReadMutation]);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return {
    notifications,
    unreadCount,
    isLoading,
    isError,
    markAsRead,
    markAllAsRead,
    refetch,
  };
};

export default useNotifications;
