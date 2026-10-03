'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

export default function AdminStudentsPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [inviteRole, setInviteRole] = useState('STUDENT');
  const [inviteLink, setInviteLink] = useState('');
  
  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>('/api/users?role=STUDENT');
        setStudents(Array.isArray(res) ? res : (res?.data ?? []));
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to load students');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post<any>('/api/invites', { role: inviteRole });
      const token = res?.token ?? res?.data?.token;
      setInviteLink(`${window.location.origin}/invite/${token}`);
    } catch (err) {
      console.error(err);
      alert('Failed to generate invite');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Students & Guardians</h1>
        <div className="flex gap-2">
          <button onClick={() => { setInviteRole('STUDENT'); setModalOpen(true); setInviteLink(''); }} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Invite Student</button>
          <button onClick={() => { setInviteRole('GUARDIAN'); setModalOpen(true); setInviteLink(''); }} className="bg-white text-indigo-600 border border-indigo-600 px-4 py-2 rounded-md hover:bg-indigo-50">Invite Guardian</button>
        </div>
      </div>

      {error && <div className="p-4 bg-red-50 text-red-700 rounded-md">{error}</div>}

      {!error && loading ? <div>Loading...</div> : (!error && (
        <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Class</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {students.map(s => (
                <tr key={s.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{s.full_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.class_name || 'Unassigned'}</td>
                </tr>
              ))}
              {students.length === 0 && <tr><td colSpan={3} className="px-6 py-4 text-center text-gray-500">No students found.</td></tr>}
            </tbody>
          </table>
        </div>
      ))}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={`Invite ${inviteRole === 'STUDENT' ? 'Student' : 'Guardian'}`}>
        {!inviteLink ? (
          <form onSubmit={handleInvite} className="space-y-4">
            <p className="text-sm text-gray-600">Generate an invite link for a new {inviteRole === 'STUDENT' ? 'student' : 'guardian'}.</p>
            <div className="flex justify-end gap-3 mt-6">
              <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-md">Generate Invite Link</button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Share this link to join:</p>
            <div className="flex gap-2">
              <input type="text" readOnly value={inviteLink} className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm" />
              <button onClick={() => navigator.clipboard.writeText(inviteLink)} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Copy</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
