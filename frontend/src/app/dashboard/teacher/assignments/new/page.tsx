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

  useEffect(() => {
    api.get<any>('/api/classes').then(res => setClasses(res.data)).catch(console.error);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post<any>('/api/assignments', formData);
      router.push(`/dashboard/teacher/assignments/${res.data.id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to create assignment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Create New Assignment</h1>
      
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
