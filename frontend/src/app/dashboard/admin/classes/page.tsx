'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

export default function AdminClassesPage() {
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  
  const [formData, setFormData] = useState({ name: '', grade_level: '1' });
  const [expandedTeachers, setExpandedTeachers] = useState<Record<string, boolean>>({});
  const [expandedStudents, setExpandedStudents] = useState<Record<string, boolean>>({});

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

  useEffect(() => { 
    fetchClasses();
  }, []);

  const toggleTeachers = (classId: string) => {
    setExpandedTeachers(prev => {
      const isOpening = !prev[classId];
      if (isOpening) fetchClasses();
      return { ...prev, [classId]: isOpening };
    });
  };

  const toggleStudents = (classId: string) => {
    setExpandedStudents(prev => {
      const isOpening = !prev[classId];
      if (isOpening) fetchClasses();
      return { ...prev, [classId]: isOpening };
    });
  };

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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Classes</h1>
        <button onClick={() => setModalOpen(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Create Class</button>
      </div>

      {loading ? <div>Loading...</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {classes.map(c => {
            const teacherCount = c.teachers?.length ?? c.teacher_count ?? 0;
            const studentCount = c.students?.length ?? c.student_count ?? 0;
            
            return (
              <div key={c.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <h3 className="text-lg font-bold text-gray-900">{c.name}</h3>
                <p className="text-sm text-gray-500 mb-4">Grade Level: {c.grade_level}</p>
                
                {/* Expandable Teachers Accordion Box */}
                <div className="mb-3 border border-gray-200 rounded-md overflow-hidden bg-gray-50">
                  <button 
                    type="button"
                    onClick={() => toggleTeachers(c.id)} 
                    className="w-full px-3 py-2 text-left flex justify-between items-center text-sm font-medium text-gray-700 hover:bg-gray-100"
                  >
                    <span>Teachers ({teacherCount})</span>
                    <span className="text-xs text-gray-500">{expandedTeachers[c.id] ? '▲' : '▼'}</span>
                  </button>
                  {expandedTeachers[c.id] && (
                    <div className="p-3 border-t border-gray-200 bg-white text-xs space-y-1.5 max-h-36 overflow-y-auto">
                      {(!c.teachers || c.teachers.length === 0) ? (
                        <p className="text-gray-400 italic">No teachers assigned</p>
                      ) : (
                        c.teachers.map((t: any) => (
                          <div key={t.id} className="flex justify-between items-center text-gray-800 py-0.5">
                            <span className="font-medium">• {t.full_name}</span>
                            <span className="text-gray-400 text-[10px]">{t.email}</span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Expandable Students Accordion Box */}
                <div className="mb-4 border border-gray-200 rounded-md overflow-hidden bg-gray-50">
                  <button 
                    type="button"
                    onClick={() => toggleStudents(c.id)} 
                    className="w-full px-3 py-2 text-left flex justify-between items-center text-sm font-medium text-gray-700 hover:bg-gray-100"
                  >
                    <span>Students ({studentCount})</span>
                    <span className="text-xs text-gray-500">{expandedStudents[c.id] ? '▲' : '▼'}</span>
                  </button>
                  {expandedStudents[c.id] && (
                    <div className="p-3 border-t border-gray-200 bg-white text-xs space-y-1.5 max-h-36 overflow-y-auto">
                      {(!c.students || c.students.length === 0) ? (
                        <p className="text-gray-400 italic">No students enrolled</p>
                      ) : (
                        c.students.map((s: any) => (
                          <div key={s.id} className="flex justify-between items-center text-gray-800 py-0.5">
                            <span className="font-medium">• {s.full_name}</span>
                            <span className="text-gray-400 text-[10px]">{s.email}</span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
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
