'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function AdminAuditPage() {
  const [audit, setAudit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>('/api/audit?page_size=50');
        setAudit(res.data.items || []);
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
      <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>

      <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <p className="text-sm text-gray-600">Showing last 50 events across the school.</p>
        </div>
        <ul className="divide-y divide-gray-200">
          {audit.map((event, idx) => (
            <li key={idx} className="p-4 hover:bg-gray-50">
              <div className="flex justify-between items-start">
                <div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    event.event_type.includes('ERROR') ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
                  }`}>
                    {event.event_type}
                  </span>
                  <div className="mt-2 text-sm text-gray-900">
                    <span className="font-semibold">Actor:</span> {event.actor_id}
                  </div>
                  <div className="text-sm text-gray-900">
                    <span className="font-semibold">Resource:</span> {event.resource_type} ({event.resource_id})
                  </div>
                  {event.details && (
                    <pre className="mt-2 text-xs bg-gray-100 p-2 rounded text-gray-700 overflow-x-auto max-w-3xl">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  )}
                </div>
                <div className="text-sm text-gray-500 whitespace-nowrap">
                  {new Date(event.timestamp).toLocaleString()}
                </div>
              </div>
            </li>
          ))}
          {audit.length === 0 && !loading && <li className="p-4 text-gray-500">No events found.</li>}
        </ul>
      </div>
    </div>
  );
}
