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
        const childrenList = res?.children ?? res?.data?.children;
        setChildren(Array.isArray(childrenList) ? childrenList : (childrenList?.items ?? []));
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
          <div key={child.student_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div className="flex items-center gap-4 mb-6 pb-4 border-b border-gray-100">
              <div className="h-12 w-12 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xl font-bold">
                {child.full_name?.charAt(0)}
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">{child.full_name}</h2>
              </div>
            </div>

            <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Assignments</h3>
            <div className="space-y-3">
              {child.assignments && child.assignments.map((assignment: any, idx: number) => (
                <div key={idx} className="p-3 bg-gray-50 border border-gray-100 rounded-md">
                  <div className="font-medium text-gray-900">{assignment.title}</div>
                  <div className="text-sm text-gray-500 mt-1 flex justify-between">
                    <span>Status: {assignment.state}</span>
                    <span>Due: {assignment.due_date ? new Date(assignment.due_date).toLocaleDateString() : 'N/A'}</span>
                  </div>
                </div>
              ))}
              {(!child.assignments || child.assignments.length === 0) && (
                <div className="text-sm text-gray-500 italic">No assignments found.</div>
              )}
            </div>
            
            {child.assignments && child.assignments.some((a: any) => a.state === 'OVERDUE') && (
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
