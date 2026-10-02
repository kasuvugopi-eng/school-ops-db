'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useSchoolWebSocket } from '@/lib/websocket';
import { useAuth } from '@/lib/auth';

export default function TeacherDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  const load = async () => {
    try {
      const res = await api.get<any>('/api/dashboard');
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [user]);
  
  // Connect to WS and pass load as handler
  useSchoolWebSocket(user?.school_id || null, load);

  if (loading) return <div>Loading dashboard...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Teacher Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500">My Assignments</p>
          <p className="text-2xl font-bold text-gray-900">{data?.my_assignments || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500">Submissions Today</p>
          <p className="text-2xl font-bold text-gray-900">{data?.submissions_today || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-red-200 border-l-4 border-l-red-500">
          <p className="text-sm font-medium text-red-500">Blocked Students</p>
          <p className="text-2xl font-bold text-gray-900">{data?.blocked_students?.length || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-yellow-200 border-l-4 border-l-yellow-500">
          <p className="text-sm font-medium text-yellow-600">Pending Reviews</p>
          <p className="text-2xl font-bold text-gray-900">{data?.pending_reviews || 0}</p>
        </div>
      </div>

      {data?.blocked_students?.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-red-600 mb-4">Attention Needed: Blocked Students</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.blocked_students.map((student: any) => (
              <div key={student.id} className="bg-red-50 p-4 rounded-lg border border-red-200">
                <p className="font-semibold text-red-900">{student.name}</p>
                <p className="text-sm text-red-700 mt-1">Blocked on: {student.assignment_title}</p>
                <p className="text-sm text-red-600 mt-2 italic">"{student.block_reason}"</p>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
