'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function ParentDashboardPage() {
  const [children, setChildren] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>('/api/dashboard');
        setChildren(res.data?.children || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Guardian Dashboard</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {children.map(child => (
          <div key={child.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div className="flex items-center gap-4 mb-6 pb-4 border-b border-gray-100">
              <div className="h-12 w-12 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xl font-bold">
                {child.full_name?.charAt(0)}
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">{child.full_name}</h2>
                <p className="text-sm text-gray-500">{child.class_name}</p>
              </div>
            </div>

            <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Assignment Status</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-green-50 p-3 rounded-lg border border-green-100">
                <div className="text-2xl font-bold text-green-700">{child.completed_assignments || 0}</div>
                <div className="text-xs text-green-600 font-medium">Completed</div>
              </div>
              <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                <div className="text-2xl font-bold text-blue-700">{child.active_assignments || 0}</div>
                <div className="text-xs text-blue-600 font-medium">Active</div>
              </div>
              <div className="bg-red-50 p-3 rounded-lg border border-red-100">
                <div className="text-2xl font-bold text-red-700">{child.overdue_assignments || 0}</div>
                <div className="text-xs text-red-600 font-medium">Overdue</div>
              </div>
            </div>
            
            {child.overdue_assignments > 0 && (
              <div className="mt-4 p-3 bg-red-100 text-red-800 rounded-md text-sm flex items-center gap-2">
                <span>⚠️</span> Please check in with {child.full_name} regarding overdue work.
              </div>
            )}
          </div>
        ))}
        {children.length === 0 && <p className="text-gray-500">No linked student accounts found.</p>}
      </div>
    </div>
  );
}
