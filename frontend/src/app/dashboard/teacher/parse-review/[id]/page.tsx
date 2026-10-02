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

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<any>(`/api/documents/${id}/parse-result`);
        setData(res.data);
        setFormData(res.data.fields || {});
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleApprove = async () => {
    try {
      await api.post<any>(`/api/documents/${id}/approve`, { corrected_fields: formData });
      router.push('/dashboard/teacher/assignments');
    } catch (err) {
      console.error(err);
      alert('Failed to approve');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!data) return <div>Parse result not found</div>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Review Parsed Document</h1>
        <div className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-medium">
          Confidence: {Math.round((data.confidence_score || 0) * 100)}%
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-6">
        {Object.entries(formData).map(([key, value]: [string, any]) => {
          const isAmbiguous = data.ambiguities?.includes(key);
          return (
            <div key={key} className={`p-4 rounded-lg border ${isAmbiguous ? 'bg-yellow-50 border-yellow-200' : 'border-gray-100'}`}>
              <div className="flex items-center gap-2 mb-2">
                <label className="block text-sm font-medium text-gray-700 capitalize">{key.replace('_', ' ')}</label>
                {isAmbiguous && <span className="text-yellow-600 text-xs font-bold flex items-center gap-1">⚠️ Please verify</span>}
              </div>
              {key === 'instructions' ? (
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

        <div className="flex justify-end gap-3 pt-4">
          <button onClick={() => router.back()} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700">Cancel</button>
          <button onClick={handleApprove} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700">Approve & Create Assignment</button>
        </div>
      </div>
    </div>
  );
}
