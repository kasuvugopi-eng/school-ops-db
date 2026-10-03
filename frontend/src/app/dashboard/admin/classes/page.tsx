'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

export default function AdminClassesPage() {
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  
  const [formData, setFormData] = useState({ name: '', grade_level: '1' });
  const [teachers, setTeachers] = useState<any[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [assignData, setAssignData] = useState<{[key: string]: { teacher_id: string, student_id: string }}>({});

  const fetchClasses = async () => {
    try {
      const res = await api.get<any>('/api/classes');
      setClasses(Array.isArray(res) ? res : (res?.items ?? res?.data ?? []));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const [t, s] = await Promise.all([
        api.get<any>('/api/users?role=TEACHER'),
        api.get<any>('/api/users?role=STUDENT')
      ]);
      setTeachers(Array.isArray(t) ? t : (t?.data ?? []));
      setStudents((Array.isArray(s) ? s : (s?.data ?? [])).filter((st: any) => !st.class_name));
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { 
    fetchClasses();
    fetchUsers();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post<any>('/api/classes', {
        name: formData.name,
        grade_level: String(formData.grade_level),
      });
      setModalOpen(false);
      fetchClasses();
      setFormData({ name: '', grade_level: '1' });
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Failed to create class');
    }
  };

  const handleAssign = async (classId: string, type: 'teachers' | 'students') => {
    const data = assignData[classId] || {};
    const userId = type === 'teachers' ? data.teacher_id : data.student_id;
    if (!userId) return;
    try {
      const key = type === 'teachers' ? 'teacher_id' : 'student_id';
      const url = `/api/classes/${classId}/${type}?${key}=${userId}`;
      await api.post<any>(url, {});
      alert('Success');
      fetchClasses();
    } catch (err: any) {
      alert(err.message || 'Failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Classes</h1>
        <button onClick={() => setModalOpen(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Create Class</button>
      </div>

      {loading ? <div>Loading...</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {classes.map(c => (
            <div key={c.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">{c.name}</h3>
              <p className="text-sm text-gray-500 mb-4">Grade Level: {c.grade_level}</p>
              <div className="flex gap-4 text-sm text-gray-600 mb-4">
                <div>Teachers: {c.teacher_count || 0}</div>
                <div>Students: {c.student_count || 0}</div>
              </div>
              <div className="space-y-2 border-t pt-4">
                <div className="flex gap-2">
                  <select className="flex-1 text-sm border rounded-md px-2 py-1" 
                    value={assignData[c.id]?.teacher_id || ''} 
                    onChange={e => setAssignData({...assignData, [c.id]: {...(assignData[c.id] || {}), teacher_id: e.target.value}})}>
                    <option value="">Select Teacher</option>
                    {teachers.map(t => <option key={t.id} value={t.id}>{t.full_name}</option>)}
                  </select>
                  <button onClick={() => handleAssign(c.id, 'teachers')} className="text-sm bg-indigo-50 text-indigo-700 px-3 rounded-md hover:bg-indigo-100">Assign</button>
                </div>
                <div className="flex gap-2">
                  <select className="flex-1 text-sm border rounded-md px-2 py-1" 
                    value={assignData[c.id]?.student_id || ''} 
                    onChange={e => setAssignData({...assignData, [c.id]: {...(assignData[c.id] || {}), student_id: e.target.value}})}>
                    <option value="">Select Student</option>
                    {students.map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}
                  </select>
                  <button onClick={() => handleAssign(c.id, 'students')} className="text-sm bg-green-50 text-green-700 px-3 rounded-md hover:bg-green-100">Enroll</button>
                </div>
              </div>
            </div>
          ))}
          {classes.length === 0 && <p className="text-gray-500">No classes found.</p>}
        </div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Create Class">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Class Name</label>
            <input type="text" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Grade Level</label>
            <input type="text" required value={formData.grade_level} onChange={e => setFormData({...formData, grade_level: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-md">Create</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
