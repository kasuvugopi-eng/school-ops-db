'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useParams } from 'next/navigation';
import StatusBadge from '@/components/ui/StatusBadge';
import { useSchoolWebSocket } from '@/lib/websocket';
import { useAuth } from '@/lib/auth';

export default function AssignmentDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [assignment, setAssignment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  const [feedbackState, setFeedbackState] = useState<{ [key: string]: string }>({});

  const fetchAssignment = async () => {
    try {
      const res = await api.get<any>(`/api/assignments/${id}`);
      const assignmentData = res?.data ?? res;
      if (assignmentData) {
        assignmentData.submissions = Array.isArray(assignmentData.submissions) 
          ? assignmentData.submissions 
          : (assignmentData.submissions?.items ?? []);
      }
      setAssignment(assignmentData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAssignment(); }, [id]);

  useSchoolWebSocket(user?.school_id || null, (e: any) => {
    if (e.detail?.resource_id === id || e.detail?.event_type?.includes('SUBMISSION')) {
      fetchAssignment();
    }
  });

  const updateState = async (newState: string) => {
    try {
      await api.put<any>(`/api/assignments/${id}/state`, { state: newState });
      fetchAssignment();
    } catch (err) {
      console.error(err);
      alert('Failed to update state');
    }
  };

  const submitFeedback = async (subId: string, action: string) => {
    try {
      const feedbackText = feedbackState[subId] || '';
      await api.post<any>(`/api/submissions/${subId}/feedback`, {
        content: feedbackText,
        feedback_text: feedbackText,
        action: action
      });
      setFeedbackState(prev => ({ ...prev, [subId]: '' }));
      fetchAssignment();
    } catch (err) {
      console.error(err);
      alert('Failed to submit feedback');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!assignment) return <div>Assignment not found</div>;

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{assignment.title}</h1>
            <p className="text-gray-500">{assignment.subject} • Due: {assignment.due_date ? new Date(assignment.due_date).toLocaleString() : 'N/A'}</p>
          </div>
          <StatusBadge state={assignment.state} />
        </div>
        
        <div className="prose max-w-none text-gray-700 mb-6 border-l-4 border-indigo-100 pl-4 py-1">
          {assignment.instructions}
        </div>

        <div className="flex gap-2">
          {assignment.state === 'DRAFT' && <button onClick={() => updateState('ACTIVE')} className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Activate</button>}
          {assignment.state === 'ACTIVE' && <button onClick={() => updateState('COMPLETED')} className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700">Mark Completed</button>}
          {['DRAFT', 'ACTIVE'].includes(assignment.state) && (
            <button onClick={() => updateState('CANCELLED')} className="bg-white text-red-600 border border-red-600 px-4 py-2 rounded-md hover:bg-red-50">Cancel</button>
          )}
        </div>
      </div>

      <h2 className="text-xl font-bold text-gray-900">Student Submissions</h2>
      <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
        <ul className="divide-y divide-gray-200">
          {(assignment.submissions || []).map((sub: any) => (
            <li key={sub.id} className="p-6">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-4">
                  <h3 className="text-lg font-medium text-gray-900">{sub.student_name || 'Student'}</h3>
                  <StatusBadge state={sub.state} />
                </div>
                <div className="text-sm text-gray-500">
                  {sub.submitted_at ? `Submitted: ${new Date(sub.submitted_at).toLocaleString()}` : 'Not submitted yet'}
                </div>
              </div>
              
              {sub.state === 'BLOCKED' && (
                <div className="bg-red-50 p-4 rounded-md text-red-800 text-sm mb-4 border border-red-200">
                  <div className="font-bold mb-1">🚨 Student Needs Help (Stuck):</div>
                  <div>{sub.blocked_reason || 'No specific doubt mentioned.'}</div>
                </div>
              )}

              {(sub.content_text || sub.content) && (
                <div className="bg-indigo-50/60 p-4 rounded-md text-gray-800 text-sm mb-4 border border-indigo-100">
                  <div className="text-xs font-semibold text-indigo-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                    📄 Parsed Content / Submission Preview
                  </div>
                  <div className="whitespace-pre-wrap font-sans">{sub.content_text || sub.content}</div>
                </div>
              )}

              {sub.state !== 'NOT_STARTED' && (
                <div className="mt-4 border-t border-gray-100 pt-4">
                  <textarea 
                    value={feedbackState[sub.id] || ''} 
                    onChange={e => setFeedbackState(prev => ({...prev, [sub.id]: e.target.value}))}
                    placeholder="Provide feedback..." 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-2"
                    rows={2}
                  ></textarea>
                  <div className="flex justify-end gap-2">
                    <button onClick={() => submitFeedback(sub.id, 'COMMENT')} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md text-sm">Comment</button>
                    <button onClick={() => submitFeedback(sub.id, 'REVISION_REQUEST')} className="px-3 py-1.5 bg-yellow-100 text-yellow-800 rounded-md text-sm">Request Revision</button>
                    <button onClick={() => submitFeedback(sub.id, 'APPROVAL')} className="px-3 py-1.5 bg-green-600 text-white rounded-md text-sm">Approve</button>
                  </div>
                </div>
              )}
            </li>
          ))}
          {(!assignment.submissions || assignment.submissions.length === 0) && (
            <li className="p-6 text-center text-gray-500">No submissions yet.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
