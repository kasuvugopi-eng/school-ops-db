'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';

export default function ParseReviewPage() {
  const { id } = useParams();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState<any>({});
  const [submitting, setSubmitting] = useState(false);
  const [classes, setClasses] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchParseResult = async () => {
    try {
      const res = await api.get<any>(`/api/documents/${id}/parse-result`);
      const parseData = res?.data ?? res;
      setData(parseData);
      setFormData(parseData?.parsed_data ?? {});
      setErrorMsg(null);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Failed to load parse result');
    }
  };

  useEffect(() => {
    async function load() {
      try {
        const clsRes = await api.get<any>('/api/classes');
        setClasses(clsRes?.data || clsRes || []);
      } catch (err) {
        console.error(err);
      }
      await fetchParseResult();
      setLoading(false);
    }
    load();
  }, [id]);

  const handleApprove = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.post<any>(`/api/documents/${id}/approve`);
      router.back();
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to approve');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClarify = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.post<any>(`/api/documents/${id}/clarify`, {
        title: formData.title || null,
        subject: formData.subject || null,
        due_date: formData.due_date || null,
        target_class_id: formData.target_class_id || null,
        instructions: formData.instructions || null
      });
      await fetchParseResult();
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to clarify');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-6">Loading...</div>;
  if (!data) return <div className="p-6">Parse result not found</div>;

  const confidence = data.confidence_notes?.overall_confidence 
    ? Math.round(data.confidence_notes.overall_confidence * 100) 
    : 0;

  const needsClarification = data.approval_state === 'NEEDS_CLARIFICATION';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Review Parsed Document</h1>
        <div className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-medium">
          Confidence: {confidence}%
        </div>
      </div>
      
      {errorMsg && (
        <div className="bg-red-50 text-red-800 p-4 rounded-md text-sm border border-red-200">
          {errorMsg}
        </div>
      )}

      {data.clarification_question && needsClarification && (
        <div className="bg-yellow-50 text-yellow-800 p-4 rounded-md text-sm border border-yellow-200">
          <p className="font-medium mb-1">Clarification Required:</p>
          <p>{data.clarification_question}</p>
          <p className="mt-2 text-xs text-yellow-700">Please provide the missing details or correct ambiguous fields and save answers.</p>
        </div>
      )}

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input type="text" value={formData.title || ''} onChange={e => setFormData({...formData, title: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
          <input type="text" value={formData.subject || ''} onChange={e => setFormData({...formData, subject: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
          <input type="datetime-local" value={formData.due_date || ''} onChange={e => setFormData({...formData, due_date: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target Class</label>
          <select value={formData.target_class_id || ''} onChange={e => setFormData({...formData, target_class_id: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100">
            <option value="">Select a class...</option>
            {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
          <textarea value={formData.instructions || ''} onChange={e => setFormData({...formData, instructions: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" rows={4} />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <button onClick={() => router.back()} disabled={submitting} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">Cancel</button>
          
          {data.approval_state === 'APPROVED' ? (
            <span className="px-4 py-2 text-green-700 font-medium">Already approved</span>
          ) : (
            <>
              <button 
                onClick={handleClarify} 
                disabled={submitting || (data.approval_state !== 'NEEDS_CLARIFICATION' && data.approval_state !== 'PENDING')} 
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                Save answers
              </button>
              <button 
                onClick={handleApprove} 
                disabled={submitting || data.approval_state !== 'PENDING'} 
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:bg-gray-400"
              >
                Approve
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
