'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function AnnouncementsPage() {
  const [announcements, setAnnouncements] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [targetClassId, setTargetClassId] = useState('ALL');
  const [targetRole, setTargetRole] = useState('ALL');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      const [annRes, clsRes] = await Promise.all([
        api.get<any>('/api/announcements'),
        api.get<any>('/api/classes')
      ]);
      setAnnouncements(Array.isArray(annRes) ? annRes : (annRes?.items ?? []));
      setClasses(Array.isArray(clsRes) ? clsRes : (clsRes?.items ?? []));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !message.trim()) return;

    setSubmitting(true);
    try {
      const res = await api.post<any>('/api/announcements', {
        title,
        message,
        target_class_id: targetClassId,
        target_role: targetRole
      });

      alert(`📢 Announcement Broadcasted Successfully!\nTelegram Delivered Count: ${res.telegram_sent_count || 0}`);
      setTitle('');
      setMessage('');
      setTargetClassId('ALL');
      setTargetRole('ALL');
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      console.error(err);
      alert(`Failed to broadcast: ${err.message || 'Error occurred'}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div>Loading announcements...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📢 School Broadcast Announcements</h1>
          <p className="text-gray-500">Send emergency notices and school announcements to Students, Teachers & Parents via Telegram.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 font-medium flex items-center gap-2 shadow-sm"
        >
          <span>➕ Send New Announcement</span>
        </button>
      </div>

      {/* Announcements History */}
      <div className="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 font-bold text-gray-800">
          Previous Broadcast History
        </div>
        <ul className="divide-y divide-gray-200">
          {announcements.map((ann) => (
            <li key={ann.id} className="p-6 hover:bg-gray-50/50 transition">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-bold text-gray-900">{ann.title}</h3>
                <span className="text-xs text-gray-500">{new Date(ann.created_at).toLocaleString()}</span>
              </div>
              <p className="text-gray-700 whitespace-pre-wrap mb-4 bg-gray-50 p-4 rounded-lg border border-gray-100 text-sm">
                {ann.message}
              </p>
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span className="bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-full font-medium">Target Class: {ann.target_class_name}</span>
                <span className="bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">Role: {ann.target_role}</span>
                <span className="bg-green-50 text-green-700 px-2.5 py-1 rounded-full font-medium">Recipients: {ann.recipient_count}</span>
                <span className="ml-auto text-gray-400">By: {ann.author_name}</span>
              </div>
            </li>
          ))}
          {announcements.length === 0 && (
            <li className="p-8 text-center text-gray-500">No broadcast announcements sent yet.</li>
          )}
        </ul>
      </div>

      {/* Broadcast Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-center border-b pb-3">
              <h2 className="text-lg font-bold text-gray-900">📢 Broadcast Announcement</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <form onSubmit={handleBroadcast} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., School Holiday Notice / Sports Day Info"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Class</label>
                  <select
                    value={targetClassId}
                    onChange={(e) => setTargetClassId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="ALL">All Classes</option>
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} {c.grade_level ? `(Grade ${c.grade_level})` : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Audience</label>
                  <select
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="ALL">Everyone (All Roles)</option>
                    <option value="STUDENT">Students Only</option>
                    <option value="TEACHER">Teachers Only</option>
                    <option value="GUARDIAN">Parents/Guardians Only</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Message Content</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Type the announcement message to broadcast..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                ></textarea>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? 'Broadcasting...' : '📢 Send Broadcast Now'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
