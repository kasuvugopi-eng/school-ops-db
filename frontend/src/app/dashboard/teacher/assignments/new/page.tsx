'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function NewAssignmentPage() {
  const router = useRouter();
  const [classes, setClasses] = useState<any[]>([]);
  const [formData, setFormData] = useState({
    title: '',
    subject: '',
    instructions: '',
    due_date: '',
    target_class_id: ''
  });
  const [loading, setLoading] = useState(false);

  const [students, setStudents] = useState<any[]>([]);
  const [targetMode, setTargetMode] = useState<'CLASS' | 'SELECTED'>('CLASS');
  const [selectedStudentIds, setSelectedStudentIds] = useState<Set<string>>(new Set());
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    api.get<any>('/api/classes').then(res => setClasses(Array.isArray(res) ? res : (res?.items ?? res?.data ?? []))).catch(console.error);
  }, []);

  useEffect(() => {
    if (formData.target_class_id) {
      api.get<any>(`/api/classes/${formData.target_class_id}/students`)
         .then(res => setStudents(Array.isArray(res) ? res : (res?.items ?? res?.data ?? [])))
         .catch(console.error);
    } else {
      setStudents([]);
    }
    // reset selection on class change
    setSelectedStudentIds(new Set());
  }, [formData.target_class_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    try {
      let targetType = 'CLASS';
      let studentIds: string[] = [];
      if (targetMode === 'SELECTED') {
        studentIds = Array.from(selectedStudentIds);
        targetType = studentIds.length === 1 ? 'INDIVIDUAL' : 'GROUP';
        if (studentIds.length === 0) {
          setErrorMsg('Please select at least one student.');
          setLoading(false);
          return;
        }
      }

      const res = await api.post<any>('/api/assignments', {
        ...formData,
        target_type: targetType,
        target_student_ids: studentIds
      });
      const assignmentId = res?.id ?? res?.data?.id;
      router.push(`/dashboard/teacher/assignments/${assignmentId}`);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Failed to create assignment');
    } finally {
      setLoading(false);
    }
  };

  const toggleStudent = (id: string) => {
    const newSet = new Set(selectedStudentIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedStudentIds(newSet);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Create New Assignment</h1>
      
      {errorMsg && (
        <div className="bg-red-50 text-red-700 p-4 rounded-md border border-red-200">
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input type="text" required value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
            <input type="text" required value={formData.subject} onChange={e => setFormData({...formData, subject: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
            <input type="datetime-local" required value={formData.due_date} onChange={e => setFormData({...formData, due_date: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target Class</label>
          <select required value={formData.target_class_id} onChange={e => setFormData({...formData, target_class_id: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option value="">Select a class...</option>
            {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        {formData.target_class_id && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target</label>
            <div className="flex gap-4 mb-4">
              <label className="flex items-center gap-2">
                <input type="radio" name="targetMode" checked={targetMode === 'CLASS'} onChange={() => setTargetMode('CLASS')} className="text-indigo-600 focus:ring-indigo-500" />
                <span>Whole class</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" name="targetMode" checked={targetMode === 'SELECTED'} onChange={() => setTargetMode('SELECTED')} className="text-indigo-600 focus:ring-indigo-500" />
                <span>Selected students</span>
              </label>
            </div>
            
            {targetMode === 'SELECTED' && (
              <div className="border border-gray-200 rounded-md p-4 max-h-48 overflow-y-auto space-y-2">
                {students.length === 0 ? (
                  <p className="text-sm text-gray-500">No students found.</p>
                ) : (
                  students.map(s => (
                    <label key={s.id} className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={selectedStudentIds.has(s.id)}
                        onChange={() => toggleStudent(s.id)}
                        className="rounded text-indigo-600 focus:ring-indigo-500" 
                      />
                      <span>{s.full_name || s.email}</span>
                    </label>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
          <textarea required rows={6} value={formData.instructions} onChange={e => setFormData({...formData, instructions: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md"></textarea>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
          <button type="button" onClick={() => router.back()} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">Cancel</button>
          <button type="submit" disabled={loading} className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50">
            {loading ? 'Creating...' : 'Create Assignment'}
          </button>
        </div>
      </form>
    </div>
  );
}
