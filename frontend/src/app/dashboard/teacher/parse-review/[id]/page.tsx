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

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>(`/api/documents/${id}/parse-result`);
        const parseData = res?.data ?? res;
        setData(parseData);
        setFormData(parseData?.parsed_data ?? parseData?.fields ?? {});
      } catch (err: any) {
        console.error(err);
        alert(`Failed to load parse result: ${err.message || 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await api.post<any>(`/api/documents/${id}/approve`);
      alert('Approved successfully');
      router.back();
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Unknown error';
      alert(`Failed to approve: ${detail}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = () => {
    alert('Reject not yet implemented on the backend');
  };

  if (loading) return <div className="p-6">Loading...</div>;
  if (!data) return <div className="p-6">Parse result not found</div>;

  const confidence = data.confidence_notes?.overall_confidence 
    ? Math.round(data.confidence_notes.overall_confidence * 100) 
    : 0;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Review Parsed Document</h1>
        <div className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-medium">
          Confidence: {confidence}%
        </div>
      </div>
      
      {data.confidence_notes && Object.keys(data.confidence_notes).length > 1 && (
        <div className="bg-blue-50 text-blue-800 p-4 rounded-md text-sm border border-blue-200">
          <p className="font-medium mb-1">Confidence Notes:</p>
          <ul className="list-disc pl-5">
            {Object.entries(data.confidence_notes).map(([k, v]) => (
              k !== 'overall_confidence' && <li key={k}>{k}: {String(v)}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-6">
        {Object.entries(formData).map(([key, value]: [string, any]) => {
          const isAmbiguous = data.ambiguity_flags?.includes(key);
          return (
            <div key={key} className={`p-4 rounded-lg border ${isAmbiguous ? 'bg-yellow-50 border-yellow-200' : 'border-gray-100'}`}>
              <div className="flex items-center gap-2 mb-2">
                <label className="block text-sm font-medium text-gray-700 capitalize">{key.replace('_', ' ')}</label>
                {isAmbiguous && <span className="text-yellow-600 text-xs font-bold flex items-center gap-1">⚠️ Please verify</span>}
              </div>
              {key === 'instructions' || key === 'description' ? (
                <textarea 
                  value={value || ''} 
                  onChange={e => setFormData({...formData, [key]: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  rows={4}
                />
              ) : (
                <input 
                  type={key === 'due_date' ? 'datetime-local' : 'text'}
                  value={value || ''} 
                  onChange={e => setFormData({...formData, [key]: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                />
              )}
            </div>
          );
        })}

        <div className="flex justify-between items-center pt-4">
          <button 
            onClick={handleReject} 
            disabled={submitting}
            className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 disabled:opacity-50"
          >
            Reject
          </button>
          <div className="flex gap-3">
            <button onClick={() => router.back()} disabled={submitting} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
            <button onClick={handleApprove} disabled={submitting} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50">Approve</button>
          </div>
        </div>
      </div>
    </div>
  );
}
