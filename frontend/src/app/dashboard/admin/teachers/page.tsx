'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

export default function AdminTeachersPage() {
  const [teachers, setTeachers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [classes, setClasses] = useState<any[]>([]);
  const [inviteLink, setInviteLink] = useState('');

  const [formData, setFormData] = useState({ role: 'TEACHER', class_id: '' });
  const [selectedGrade, setSelectedGrade] = useState('');
  const [inviteName, setInviteName] = useState('');

  const availableGrades = Array.from(new Set(classes.map(c => c.grade_level).filter(Boolean)));
  const filteredClasses = selectedGrade 
    ? classes.filter(c => String(c.grade_level) === String(selectedGrade))
    : classes;

  useEffect(() => {
    async function load() {
      try {
        const [teachersRes, classRes] = await Promise.all([
          api.get<any>('/api/users?role=TEACHER'),
          api.get<any>('/api/classes')
        ]);
        setTeachers(Array.isArray(teachersRes) ? teachersRes : (teachersRes?.data ?? []));
        setClasses(Array.isArray(classRes) ? classRes : (classRes?.items ?? classRes?.data ?? []));
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to load teachers');
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
      const nameParam = inviteName.trim() ? `?name=${encodeURIComponent(inviteName.trim())}` : '';
      const link = `${window.location.origin}/invite/${token}${nameParam}`;
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

  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignTeacherObj, setAssignTeacherObj] = useState<any>(null);
  const [selectedClassIdsForTeacher, setSelectedClassIdsForTeacher] = useState<string[]>([]);
  const [savingAssignments, setSavingAssignments] = useState(false);

  const openAssignModal = (teacher: any) => {
    setAssignTeacherObj(teacher);
    const assignedNames = new Set(teacher.class_names || []);
    const matchingIds = classes.filter(c => assignedNames.has(c.name)).map(c => c.id);
    setSelectedClassIdsForTeacher(matchingIds);
    setAssignModalOpen(true);
  };

  const toggleClassForTeacher = (classId: string) => {
    setSelectedClassIdsForTeacher(prev => 
      prev.includes(classId) ? prev.filter(id => id !== classId) : [...prev, classId]
    );
  };

  const handleSaveClassAssignments = async () => {
    if (!assignTeacherObj) return;
    setSavingAssignments(true);
    try {
      for (const classId of selectedClassIdsForTeacher) {
        await api.post(`/api/classes/${classId}/teachers?teacher_id=${assignTeacherObj.id}`, {});
      }
      alert('Class assignments updated successfully!');
      setAssignModalOpen(false);
      const teachersRes = await api.get<any>('/api/users?role=TEACHER');
      setTeachers(Array.isArray(teachersRes) ? teachersRes : (teachersRes?.data ?? []));
    } catch (err: any) {
      alert(err.message || 'Failed to update class assignments');
    } finally {
      setSavingAssignments(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Teachers</h1>
        <button onClick={() => { setModalOpen(true); setInviteLink(''); }} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Invite Teacher</button>
      </div>

      {error && <div className="p-4 bg-red-50 text-red-700 rounded-md">{error}</div>}

      {!error && loading ? <div>Loading...</div> : (!error && (
        <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned Classes</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {teachers.map(t => (
                <tr key={t.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{t.full_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.class_names?.join(', ') || 'None'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => openAssignModal(t)}
                      className="text-indigo-600 hover:text-indigo-900 bg-indigo-50 px-3 py-1 rounded-md text-xs font-semibold border border-indigo-100"
                    >
                      + Assign Classes
                    </button>
                  </td>
                </tr>
              ))}
              {teachers.length === 0 && <tr><td colSpan={4} className="px-6 py-4 text-center text-gray-500">No teachers found.</td></tr>}
            </tbody>
          </table>
        </div>
      ))}

<Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Invite Teacher">
{
  !inviteLink ? (
    <form onSubmit={handleInvite} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Teacher Name (Optional / Pre-fill)</label>
        <input
          type="text"
          value={inviteName}
          onChange={e => setInviteName(e.target.value)}
          placeholder="e.g. Ramesh Sir"
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Grade</label>
        <select 
          value={selectedGrade} 
          onChange={e => {
            setSelectedGrade(e.target.value);
            setFormData({ ...formData, class_id: '' });
          }} 
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        >
          <option value="">All Grades</option>
          {availableGrades.map((g, idx) => {
            const label = g.toLowerCase().startsWith('grade') ? g : `Grade ${g}`;
            return <option key={idx} value={g}>{label}</option>;
          })}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Assign to Class (Optional)</label>
        <select value={formData.class_id} onChange={e => setFormData({ ...formData, class_id: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-md">
          <option value="">-- None --</option>
          {filteredClasses.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Selected Summary Card */}
      <div className="bg-indigo-50 border border-indigo-100 p-3 rounded-md text-sm space-y-1 text-indigo-900">
        <p className="font-semibold text-xs text-indigo-700 uppercase tracking-wider">Selection Summary</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs sm:text-sm">
          <div><span className="font-medium text-gray-600">Teacher:</span> {inviteName || 'Not specified'}</div>
          <div><span className="font-medium text-gray-600">Grade:</span> {selectedGrade ? (selectedGrade.toLowerCase().startsWith('grade') ? selectedGrade : `Grade ${selectedGrade}`) : 'All Grades'}</div>
          <div><span className="font-medium text-gray-600">Class:</span> {formData.class_id ? (classes.find(c => c.id === formData.class_id)?.name || 'Selected') : 'None'}</div>
        </div>
      </div>

      <div className="flex justify-end gap-3 mt-6">
        <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
        <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Generate Invite Link</button>
      </div>
          </form >
        ) : (
  <div className="space-y-4">
    < p className ="text-sm text-gray-600">Share this link with the teacher to join:</p>
      < div className ="flex gap-2">
        < input type ="text" readOnly value={inviteLink} className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm" />
          < button type="button" onClick = { (e) => { 
            navigator.clipboard.writeText(inviteLink);
            const btn = e.currentTarget;
            const originalText = btn.innerText;
            btn.innerText = 'Copied!';
            setTimeout(() => { btn.innerText = originalText; }, 2000);
          } } className ="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Copy</button>
            </div >
          <div className="flex justify-end mt-4">
            <button type="button" onClick={() => { setModalOpen(false); setInviteLink(''); }} className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Done</button>
          </div>
        </div>
      )}
    </Modal>

    {/* Assign Multiple Classes Modal */}
    <Modal isOpen={assignModalOpen} onClose={() => setAssignModalOpen(false)} title={`Assign Classes - ${assignTeacherObj?.full_name || 'Teacher'}`}>
      <div className="space-y-4">
        <p className="text-sm text-gray-600">Select the classes you want to assign to <strong>{assignTeacherObj?.full_name}</strong>:</p>
        
        <div className="border border-gray-200 rounded-md p-3 max-h-60 overflow-y-auto space-y-2 bg-gray-50">
          {classes.length === 0 ? (
            <p className="text-sm text-gray-500">No classes found in school.</p>
          ) : (
            classes.map(c => {
              const gLabel = c.grade_level ? (c.grade_level.toLowerCase().startsWith('grade') ? c.grade_level : `Grade ${c.grade_level}`) : '';
              return (
                <label key={c.id} className="flex items-center space-x-2 text-sm text-gray-800 cursor-pointer hover:bg-gray-100 p-1 rounded">
                  <input 
                    type="checkbox"
                    checked={selectedClassIdsForTeacher.includes(c.id)}
                    onChange={() => toggleClassForTeacher(c.id)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>{c.name} {gLabel ? `(${gLabel})` : ''}</span>
                </label>
              );
            })
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button type="button" onClick={() => setAssignModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
          <button 
            type="button" 
            onClick={handleSaveClassAssignments} 
            disabled={savingAssignments}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {savingAssignments ? 'Saving...' : 'Save Assignments'}
          </button>
        </div>
      </div>
    </Modal>
  </div>
);
}
