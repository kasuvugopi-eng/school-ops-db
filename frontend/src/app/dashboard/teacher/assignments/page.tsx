'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import StatusBadge from '@/components/ui/StatusBadge';
import Link from 'next/link';

export default function TeacherAssignmentsPage() {
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>('/api/assignments');
        setAssignments(Array.isArray(res) ? res : (res?.items ?? res?.data ?? []));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Assignments</h1>
        <Link href="/dashboard/teacher/assignments/new" className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
          Create Assignment
        </Link>
      </div>

      {loading ? <div>Loading...</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assignments.map(a => {
            const summary = a.submission_summary || {};
            const completedCount = a.completed_submissions ?? (summary.COMPLETED || 0);
            const totalCount = a.total_submissions ?? Object.values(summary).reduce((acc: number, val: any) => acc + (typeof val === 'number' ? val : 0), 0);
            return (
              <Link key={a.id} href={`/dashboard/teacher/assignments/${a.id}`} className="block bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:border-indigo-300 transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-bold text-gray-900">{a.title}</h3>
                  <StatusBadge state={a.state || 'DRAFT'} />
                </div>
                <p className="text-sm text-gray-500 mb-4">{a.subject} • Due: {a.due_date ? new Date(a.due_date).toLocaleDateString() : 'No date'}</p>
                
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                  <div className="bg-indigo-600 h-2.5 rounded-full" style={{ width: `${(completedCount / (totalCount || 1)) * 100}%` }}></div>
                </div>
                <p className="text-xs text-gray-500 text-right">{completedCount} / {totalCount} submitted</p>
              </Link>
            );
          })}
          {assignments.length === 0 && <p className="text-gray-500">No assignments found.</p>}
        </div>
      )}
    </div>
  );
}
