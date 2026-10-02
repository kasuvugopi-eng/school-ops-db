'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import StatusBadge from '@/components/ui/StatusBadge';
import Link from 'next/link';

export default function StudentDashboardPage() {
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>('/api/submissions/mine');
        setSubmissions(Array.isArray(res) ? res : (res?.items ?? res?.data ?? []));
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
      <h1 className="text-2xl font-bold text-gray-900">My Assignments</h1>

      {loading ? <div>Loading...</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {submissions.map(sub => {
            const dueDate = sub.assignment?.due_date ?? sub.assignment_due_date;
            const title = sub.assignment?.title ?? sub.assignment_title ?? 'Unknown Assignment';
            const subject = sub.assignment?.subject ?? sub.assignment_subject;
            const isOverdue = dueDate && new Date(dueDate) < new Date() && sub.state !== 'COMPLETED';
            return (
              <Link key={sub.id} href={`/dashboard/student/assignments/${sub.assignment_id}`} className={`block bg-white p-6 rounded-xl shadow-sm border transition-colors ${isOverdue ? 'border-red-300 hover:border-red-400' : 'border-gray-200 hover:border-indigo-300'}`}>
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-bold text-gray-900">{title}</h3>
                  <StatusBadge state={sub.state} />
                </div>
                <div className="text-sm text-gray-600 mb-2">{subject}</div>
                <div className={`text-sm font-medium ${isOverdue ? 'text-red-600 flex items-center gap-1' : 'text-gray-500'}`}>
                  {isOverdue && <span>⚠️</span>}
                  Due: {dueDate ? new Date(dueDate).toLocaleDateString() : 'No date'}
                </div>
              </Link>
            );
          })}
          {submissions.length === 0 && <p className="text-gray-500">You have no active assignments.</p>}
        </div>
      )}
    </div>
  );
}
