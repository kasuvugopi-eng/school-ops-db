'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

export default function AdminTeachersPage() {
  const [teachers, setTeachers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [classes, setClasses] = useState<any[]>([]);
  const [inviteLink, setInviteLink] = useState('');
  
  const [formData, setFormData] = useState({ role: 'TEACHER', class_id: '' });
  
  useEffect(() => {
    async function load() {
      try {
        const [dashRes, classRes] = await Promise.all([
          api.get<any>('/api/dashboard'),
          api.get<any>('/api/classes')
        ]);
        // Mocked from dashboard or actual endpoint
        const recentTeachers = dashRes?.recent_teachers ?? dashRes?.data?.recent_teachers;
        setTeachers(Array.isArray(recentTeachers) ? recentTeachers : (recentTeachers?.items ?? []));
        setClasses(Array.isArray(classRes) ? classRes : (classRes?.items ?? classRes?.data ?? []));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post<any>('/api/invites', {
        role: formData.role,
        target_class_id: formData.class_id || null
      });
      const token = res?.token ?? res?.data?.token;
      const link = `${window.location.origin}/invite/${token}`;
      setInviteLink(link);
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Failed to generate invite');
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(inviteLink);
    alert('Copied to clipboard');
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Teachers</h1>
        <button onClick={() => { setModalOpen(true); setInviteLink(''); }} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Invite Teacher</button>
      </div>

      {loading ? <div>Loading...</div> : (
        <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned Classes</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {teachers.map(t => (
                <tr key={t.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{t.full_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.username}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.classes?.join(', ') || 'None'}</td>
                </tr>
              ))}
              {teachers.length === 0 && <tr><td colSpan={3} className="px-6 py-4 text-center text-gray-500">No teachers found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Invite Teacher">
        {!inviteLink ? (
          <form onSubmit={handleInvite} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Assign to Class (Optional)</label>
              <select value={formData.class_id} onChange={e => setFormData({...formData, class_id: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md">
                <option value="">-- None --</option>
                {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-md">Generate Invite Link</button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Share this link with the teacher to join:</p>
            <div className="flex gap-2">
              <input type="text" readOnly value={inviteLink} className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm" />
              <button onClick={copyToClipboard} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Copy</button>
            </div>
            <div className="flex justify-end mt-4">
              <button onClick={() => setModalOpen(false)} className="px-4 py-2 bg-indigo-600 text-white rounded-md">Done</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
