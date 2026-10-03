'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

export default function AdminStudentsPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [guardians, setGuardians] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [inviteRole, setInviteRole] = useState('STUDENT');
  const [inviteLink, setInviteLink] = useState('');
  const [targetClassId, setTargetClassId] = useState('');
  const [targetStudentId, setTargetStudentId] = useState('');
  const [relationship, setRelationship] = useState('');
  
  useEffect(() => {
    async function load() {
      try {
        const [resStudents, resGuardians, resClasses] = await Promise.all([
          api.get<any>('/api/users?role=STUDENT'),
          api.get<any>('/api/users?role=GUARDIAN'),
          api.get<any>('/api/classes')
        ]);
        setStudents(Array.isArray(resStudents) ? resStudents : (resStudents?.data ?? []));
        setGuardians(Array.isArray(resGuardians) ? resGuardians : (resGuardians?.data ?? []));
        setClasses(Array.isArray(resClasses) ? resClasses : (resClasses?.data ?? []));
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
      const payload: any = { role: inviteRole };
      if (inviteRole === 'STUDENT') {
        payload.target_class_id = targetClassId;
      } else if (inviteRole === 'GUARDIAN') {
        payload.target_student_id = targetStudentId;
        payload.relationship = relationship;
      }
      const res = await api.post<any>('/api/invites', payload);
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
          <button onClick={() => { setInviteRole('STUDENT'); setTargetClassId(''); setModalOpen(true); setInviteLink(''); }} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Invite Student</button>
          <button onClick={() => { setInviteRole('GUARDIAN'); setTargetStudentId(''); setRelationship(''); setModalOpen(true); setInviteLink(''); }} className="bg-white text-indigo-600 border border-indigo-600 px-4 py-2 rounded-md hover:bg-indigo-50">Invite Guardian</button>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Guardians</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {students.map(s => (
                <tr key={s.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{s.full_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.class_name || 'Unassigned'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {s.guardians && s.guardians.length > 0 ? (
                      <ul className="list-disc pl-4">
                        {s.guardians.map((g: any, i: number) => (
                          <li key={i}>{g.name} — {g.relationship}</li>
                        ))}
                      </ul>
                    ) : 'None'}
                  </td>
                </tr>
              ))}
              {students.length === 0 && <tr><td colSpan={4} className="px-6 py-4 text-center text-gray-500">No students found.</td></tr>}
            </tbody>
          </table>
        </div>
      ))}
      
      {!error && !loading && (
        <div className="mt-8 bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
          <h2 className="px-6 py-4 text-lg font-bold text-gray-900 border-b border-gray-200">Guardians</h2>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Linked Students</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {guardians.map(g => (
                <tr key={g.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{g.full_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{g.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {g.guardians && g.guardians.length > 0 ? (
                      <ul className="list-disc pl-4">
                        {g.guardians.map((s: any, i: number) => (
                          <li key={i}>{s.name} ({s.relationship})</li>
                        ))}
                      </ul>
                    ) : 'None'}
                  </td>
                </tr>
              ))}
              {guardians.length === 0 && <tr><td colSpan={3} className="px-6 py-4 text-center text-gray-500">No guardians found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={`Invite ${inviteRole === 'STUDENT' ? 'Student' : 'Guardian'}`}>
        {!inviteLink ? (
          <form onSubmit={handleInvite} className="space-y-4">
            <p className="text-sm text-gray-600">Generate an invite link for a new {inviteRole === 'STUDENT' ? 'student' : 'guardian'}.</p>
            
            {inviteRole === 'STUDENT' && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Class</label>
                <select required value={targetClassId} onChange={e => setTargetClassId(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                  <option value="">Select a class...</option>
                  {classes.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            )}

            {inviteRole === 'GUARDIAN' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Student</label>
                  <select required value={targetStudentId} onChange={e => setTargetStudentId(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                    <option value="">Select a student...</option>
                    {students.map(s => (
                      <option key={s.id} value={s.id}>{s.full_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Relationship</label>
                  <select required value={relationship} onChange={e => setRelationship(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                    <option value="">Select relationship...</option>
                    <option value="mother">mother</option>
                    <option value="father">father</option>
                    <option value="guardian">guardian</option>
                    <option value="other">other</option>
                  </select>
                </div>
              </>
            )}

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
