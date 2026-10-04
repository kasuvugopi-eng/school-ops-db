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
  const [selectedClassIds, setSelectedClassIds] = useState<string[]>([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState<Set<string>>(new Set());
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    // We fetch all classes for now to avoid the empty classes issue
    api.get<any>('/api/classes').then(res => setClasses(Array.isArray(res) ? res : (res?.items ?? res?.data ?? []))).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedClassIds.length > 0) {
      const qs = selectedClassIds.join(',');
      api.get<any>(`/api/students?class_ids=${qs}`)
         .then(res => {
           const fetchedStudents = Array.isArray(res) ? res : (res?.items ?? res?.data ?? []);
           setStudents(fetchedStudents);
           // Auto-remove students not in the fetched list
           const validIds = new Set(fetchedStudents.map((s: any) => s.id));
           setSelectedStudentIds(prev => {
             const next = new Set<string>();
             prev.forEach(id => {
               if (validIds.has(id)) next.add(id);
             });
             return next;
           });
         })
         .catch(console.error);
    } else {
      setStudents([]);
      setSelectedStudentIds(new Set());
    }
  }, [selectedClassIds]);

  const toggleClass = (id: string) => {
    setSelectedClassIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(c => c !== id);
      }
      return [...prev, id];
    });
  };

  const toggleStudent = (id: string) => {
    const newSet = new Set(selectedStudentIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedStudentIds(newSet);
  };

  const toggleAllStudents = () => {
    if (selectedStudentIds.size === students.length && students.length > 0) {
      setSelectedStudentIds(new Set());
    } else {
      setSelectedStudentIds(new Set(students.map(s => s.id)));
    }
  };
  
  const toggleAllStudentsInClass = (classId: string) => {
    const studentsInClass = students.filter(s => s.class_id === classId);
    const allSelected = studentsInClass.every(s => selectedStudentIds.has(s.id));
    
    setSelectedStudentIds(prev => {
      const next = new Set(prev);
      if (allSelected) {
        studentsInClass.forEach(s => next.delete(s.id));
      } else {
        studentsInClass.forEach(s => next.add(s.id));
      }
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedClassIds.length === 0) {
      setErrorMsg('Please select at least one class.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      const globalStudentIds = Array.from(selectedStudentIds);
      
      const promises = selectedClassIds.map(classId => {
        const classStudents = students.filter(s => s.class_id === classId);
        const selectedInClass = classStudents.filter(s => selectedStudentIds.has(s.id)).map(s => s.id);
        
        // If some global students were selected but NONE in this class, we still create the assignment?
        // Let's pass the specific students if any are selected globally.
        // Wait, if no students are selected AT ALL globally, it means "All students in all selected classes".
        let finalStudentIds = null;
        if (globalStudentIds.length > 0) {
            finalStudentIds = selectedInClass; 
        }

        return api.post<any>('/api/assignments', {
          title: formData.title,
          subject: formData.subject,
          instructions: formData.instructions,
          due_date: formData.due_date || null,
          target_type: 'CLASS',
          target_class_id: classId,
          student_ids: finalStudentIds
        });
      });

      const results = await Promise.all(promises);
      const assignmentId = results[0]?.id ?? results[0]?.data?.id;
      router.push(`/dashboard/teacher/assignments/${assignmentId}`);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to create assignment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
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

        <div className="grid grid-cols-2 gap-6 border-t border-gray-100 pt-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target Classes</label>
            <div className="border border-gray-200 rounded-md p-3 max-h-64 overflow-y-auto space-y-2 bg-gray-50">
              {classes.length === 0 ? (
                <p className="text-sm text-gray-500">No classes found.</p>
              ) : (
                classes.map(c => (
                  <label key={c.id} className="flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      checked={selectedClassIds.includes(c.id)}
                      onChange={() => toggleClass(c.id)}
                      className="rounded text-indigo-600 focus:ring-indigo-500" 
                    />
                    <span>{c.grade_level ? `Grade ${c.grade_level} - ` : ''}{c.name}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target Students</label>
            <div className={`border border-gray-200 rounded-md p-3 max-h-64 overflow-y-auto space-y-4 ${selectedClassIds.length === 0 ? 'bg-gray-100 opacity-60' : 'bg-gray-50'}`}>
              {selectedClassIds.length === 0 ? (
                <p className="text-sm text-gray-500">Select a class first.</p>
              ) : students.length === 0 ? (
                <p className="text-sm text-gray-500">No students found in selected classes.</p>
              ) : (
                <>
                  <label className="flex items-center gap-2 pb-2 border-b border-gray-200 mb-2 font-medium">
                    <input 
                      type="checkbox" 
                      checked={selectedStudentIds.size === students.length && students.length > 0}
                      onChange={toggleAllStudents}
                      className="rounded text-indigo-600 focus:ring-indigo-500" 
                    />
                    <span>Select All Students</span>
                  </label>
                  
                  {selectedClassIds.map(classId => {
                    const classObj = classes.find(c => c.id === classId);
                    const classStudents = students.filter(s => s.class_id === classId);
                    if (classStudents.length === 0) return null;
                    
                    const allInClass = classStudents.every(s => selectedStudentIds.has(s.id));
                    
                    return (
                      <div key={classId} className="space-y-2">
                        <div className="font-semibold text-gray-700 text-sm border-b pb-1 flex items-center justify-between">
                          <span>{classObj?.name || 'Class'}</span>
                          <label className="flex items-center gap-1 font-normal text-xs cursor-pointer">
                            <input 
                              type="checkbox" 
                              checked={allInClass}
                              onChange={() => toggleAllStudentsInClass(classId)}
                              className="rounded text-indigo-600 focus:ring-indigo-500" 
                            />
                            <span>Select all</span>
                          </label>
                        </div>
                        <div className="pl-2 space-y-2">
                          {classStudents.map(s => (
                            <label key={s.id} className="flex items-center gap-2 text-sm">
                              <input 
                                type="checkbox" 
                                checked={selectedStudentIds.has(s.id)}
                                onChange={() => toggleStudent(s.id)}
                                className="rounded text-indigo-600 focus:ring-indigo-500" 
                              />
                              <span>{s.full_name || s.email}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </>
              )}
            </div>
            {selectedClassIds.length > 0 && selectedStudentIds.size === 0 && (
              <p className="mt-2 text-xs text-indigo-600">
                Hint: No students selected means this assignment will be sent to <strong>all students</strong> in the selected classes.
              </p>
            )}
          </div>
        </div>

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
