'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Link from 'next/link';

export default function AdminDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [dashRes, auditRes] = await Promise.all([
          api.get<any>('/api/dashboard'),
          api.get<any>('/api/audit?page_size=10')
        ]);
        setData(dashRes);
        setAudit(Array.isArray(auditRes) ? auditRes : (auditRes?.items ?? []));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div>Loading dashboard...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-indigo-100 border-l-4 border-l-indigo-500">
          <div className="flex items-center gap-4">
            <div className="text-3xl">👨‍🏫</div>
            <div>
              <p className="text-sm font-medium text-gray-500">Total Teachers</p>
              <p className="text-2xl font-bold text-gray-900">{data?.total_teachers || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-green-100 border-l-4 border-l-green-500">
          <div className="flex items-center gap-4">
            <div className="text-3xl">🎓</div>
            <div>
              <p className="text-sm font-medium text-gray-500">Total Students</p>
              <p className="text-2xl font-bold text-gray-900">{data?.total_students || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-blue-100 border-l-4 border-l-blue-500">
          <div className="flex items-center gap-4">
            <div className="text-3xl">📝</div>
            <div>
              <p className="text-sm font-medium text-gray-500">Active Assignments</p>
              <p className="text-2xl font-bold text-gray-900">{data?.active_assignments || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-yellow-100 border-l-4 border-l-yellow-500">
          <div className="flex items-center gap-4">
            <div className="text-3xl">⏳</div>
            <div>
              <p className="text-sm font-medium text-gray-500">Pending Reviews</p>
              <p className="text-2xl font-bold text-gray-900">{data?.pending_reviews || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-4 mb-8">
        <Link href="/dashboard/admin/classes" className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Create Class</Link>
        <Link href="/dashboard/admin/teachers" className="bg-white text-indigo-600 border border-indigo-600 px-4 py-2 rounded-md hover:bg-indigo-50">Invite Teacher</Link>
        <Link href="/dashboard/admin/documents" className="bg-white text-indigo-600 border border-indigo-600 px-4 py-2 rounded-md hover:bg-indigo-50">Upload Document</Link>
      </div>

      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">Recent Audit Events</h2>
        <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
          <ul className="divide-y divide-gray-200">
            {audit.map((event, idx) => (
              <li key={idx} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {event.event_type}
                    </span>
                    <p className="mt-1 text-sm text-gray-900">Actor: {event.actor_id}</p>
                    <p className="text-xs text-gray-500">Resource: {event.resource_type} ({event.resource_id})</p>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(event.created_at || event.timestamp).toLocaleString()}
                  </div>
                </div>
              </li>
            ))}
            {audit.length === 0 && <li className="p-4 text-gray-500">No recent events.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
