'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useParams } from 'next/navigation';
import StatusBadge from '@/components/ui/StatusBadge';

export default function StudentAssignmentDetailPage() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState('');
  const [blockReason, setBlockReason] = useState('');
  const [showBlock, setShowBlock] = useState(false);

  const fetchData = async () => {
    try {
      const res = await api.get<any>('/api/submissions/mine');
      const list = Array.isArray(res) ? res : (res?.items ?? res?.data ?? []);
      const sub = list.find((s: any) => s.assignment_id === id);
      if (sub && !sub.assignment && sub.assignment_title) {
        sub.assignment = {
          title: sub.assignment_title,
          subject: sub.assignment_subject,
          due_date: sub.assignment_due_date,
          instructions: sub.assignment_instructions,
        };
      }
      setData(sub);
      const initialContent = sub?.content_text ?? sub?.content;
      if (initialContent) setContent(initialContent);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleUpdate = async (state: string) => {
    try {
      await api.put<any>(`/api/submissions/${data.id}`, { state, content_text: content });
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to update submission');
    }
  };

  const handleBlock = async () => {
    try {
      await api.put<any>(`/api/submissions/${data.id}`, { state: 'BLOCKED', blocked_reason: blockReason });
      setShowBlock(false);
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to update status');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!data || !data.assignment) return <div>Assignment not found</div>;

  const { assignment, state } = data;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{assignment.title}</h1>
            <p className="text-gray-500">{assignment.subject} • Due: {assignment.due_date ? new Date(assignment.due_date).toLocaleString() : 'N/A'}</p>
          </div>
          <StatusBadge state={state} />
        </div>
        
        <div className="prose max-w-none text-gray-700 mb-6 bg-gray-50 p-4 rounded-lg border border-gray-100">
          <h3 className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-wider">Instructions</h3>
          {assignment.instructions}
        </div>

        {state !== 'COMPLETED' && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-gray-900">Your Work</h3>
            <textarea 
              value={content} 
              onChange={e => setContent(e.target.value)}
              placeholder="Type your answer or paste a link here..." 
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={8}
            ></textarea>
            
            <div className="flex gap-3">
              <button onClick={() => handleUpdate(state === 'NOT_STARTED' ? 'IN_PROGRESS' : state)} className="px-4 py-2 bg-white text-indigo-600 border border-indigo-600 rounded-md">Save Draft</button>
              <button onClick={() => handleUpdate('SUBMITTED')} className="px-4 py-2 bg-indigo-600 text-white rounded-md">Submit Assignment</button>
              <button onClick={() => setShowBlock(!showBlock)} className="px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-md ml-auto">I'm Stuck</button>
            </div>
            
            {showBlock && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <label className="block text-sm font-medium text-red-800 mb-1">What are you stuck on?</label>
                <textarea 
                  value={blockReason} 
                  onChange={e => setBlockReason(e.target.value)}
                  className="w-full px-3 py-2 border border-red-300 rounded-md mb-2"
                  rows={2}
                ></textarea>
                <button onClick={handleBlock} className="px-4 py-2 bg-red-600 text-white rounded-md text-sm">Notify Teacher</button>
              </div>
            )}
          </div>
        )}

        {state === 'COMPLETED' && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <h3 className="text-green-800 font-bold mb-2">Completed!</h3>
            <div className="text-gray-700 bg-white p-4 rounded border border-green-100">{data.content_text || data.content}</div>
          </div>
        )}
      </div>
      
      {data.feedback && data.feedback.length > 0 && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mt-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Teacher Feedback</h3>
          <div className="space-y-4">
            {data.feedback.map((fb: any, i: number) => (
              <div key={i} className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
                <div className="text-sm font-semibold text-blue-900 mb-1">{new Date(fb.created_at).toLocaleString()}</div>
                <div className="text-gray-800">{fb.content || fb.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
