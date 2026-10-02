'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import FileUpload from '@/components/ui/FileUpload';
import StatusBadge from '@/components/ui/StatusBadge';
import Link from 'next/link';

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('POLICY');

  const fetchDocs = async () => {
    try {
      const res = await api.get<any>('/api/documents');
      setDocuments(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      // @ts-ignore
      await api.uploadFile<any>('/api/documents/upload', file, { document_type: docType });
      fetchDocs();
    } catch (err) {
      console.error(err);
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleParse = async (id: string) => {
    try {
      await api.post<any>(`/api/documents/${id}/parse`);
      alert('Parse job triggered');
      fetchDocs();
    } catch (err) {
      console.error(err);
      alert('Parse failed');
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
      
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <h2 className="text-lg font-medium mb-4">Upload Document</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
          <select value={docType} onChange={e => setDocType(e.target.value)} className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md">
            <option value="POLICY">Policy / Guideline</option>
            <option value="ROSTER">Class Roster</option>
            <option value="CLASS_MATERIAL">Class Material</option>
          </select>
        </div>
        <FileUpload onFileSelect={handleUpload} loading={uploading} accept=".pdf,.txt,.docx" />
      </div>

      <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {documents.map(doc => (
              <tr key={doc.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{doc.filename}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.document_type}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(doc.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <StatusBadge state={doc.status || 'UPLOADED'} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {doc.status === 'UPLOADED' && (
                    <button onClick={() => handleParse(doc.id)} className="text-indigo-600 hover:text-indigo-900">Parse</button>
                  )}
                  {doc.status === 'PARSED' && (
                    <Link href={`/dashboard/teacher/parse-review/${doc.id}`} className="text-green-600 hover:text-green-900">Review</Link>
                  )}
                </td>
              </tr>
            ))}
            {documents.length === 0 && !loading && <tr><td colSpan={5} className="px-6 py-4 text-center text-gray-500">No documents found.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
