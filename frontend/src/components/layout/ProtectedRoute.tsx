'use client';

import { useAuth } from '@/lib/auth';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { getDashboardRoute } from '@/lib/utils';

export default function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: string[] }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push('/login');
      } else {
        const expectedBase = getDashboardRoute(user.role);
        // If they are under /dashboard, enforce they stay in their lane
        if (pathname && pathname.startsWith('/dashboard') && !pathname.startsWith(expectedBase)) {
            router.push(expectedBase);
        } else if (allowedRoles && !allowedRoles.includes(user.role)) {
            router.push(expectedBase);
        }
      }
    }
  }, [user, isLoading, router, pathname, allowedRoles]);

  if (isLoading || !user) {
    return (
      <div className=\"min-h-screen flex items-center justify-center bg-gray-50\">
        <div className=\"animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600\"></div>
      </div>
    );
  }

  const expectedBase = getDashboardRoute(user.role);
  if (pathname && pathname.startsWith('/dashboard') && !pathname.startsWith(expectedBase)) {
    return null;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}
