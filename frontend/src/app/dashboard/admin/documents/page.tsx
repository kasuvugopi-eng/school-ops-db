'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import api from '@/lib/api';
import FileUpload from '@/components/ui/FileUpload';
import StatusBadge from '@/components/ui/StatusBadge';
import Link from 'next/link';

export default function AdminDocumentsPage() {
  const pathname = usePathname();
  const router = useRouter();
  const isTeacher = pathname?.includes('/teacher');

  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [parsingId, setParsingId] = useState<string | null>(null);
  const [docType, setDocType] = useState(isTeacher ? 'ASSIGNMENT_BRIEF' : 'POLICY');

  const fetchDocs = async () => {
    try {
      const res = await api.get<any>('/api/documents');
      setDocuments(Array.isArray(res) ? res : (res?.items ?? res?.data ?? []));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { 
    setDocType(isTeacher ? 'ASSIGNMENT_BRIEF' : 'POLICY');
    fetchDocs(); 
  }, [isTeacher]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      // @ts-ignore
      await api.uploadFile<any>('/api/documents/upload', file, { document_type: docType });
      fetchDocs();
    } catch (err: any) {
      console.error(err);
      alert(`Upload failed: ${err.message || 'Unknown error'}`);
    } finally {
      setUploading(false);
    }
  };

  const handleParse = async (id: string) => {
    setParsingId(id);
    try {
      const res = await api.post<any>(`/api/documents/${id}/parse`);
      const data = res?.data ?? res;
      await fetchDocs();
      router.push(`/dashboard/${isTeacher ? 'teacher' : 'admin'}/parse-review/${id}`);
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Unknown error';
      alert(`Parse failed: ${detail}`);
    } finally {
      setParsingId(null);
    }
  };

  const docTypes = isTeacher
    ? [
        { value: 'ASSIGNMENT_BRIEF', label: 'Assignment Brief' },
        { value: 'CLASS_MATERIAL', label: 'Class Material' },
      ]
    : [
        { value: 'ROSTER', label: 'Class Roster' },
        { value: 'POLICY', label: 'School Policy' },
        { value: 'CLASS_MATERIAL', label: 'Class Material' },
      ];

  const getDocTypeLabel = (type: string) => {
    const map: Record<string, string> = {
      ASSIGNMENT_BRIEF: 'Assignment Brief',
      ROSTER: 'Class Roster',
      POLICY: 'School Policy',
      CLASS_MATERIAL: 'Class Material',
    };
    return map[type] || type;
  };

  const getStatusLabel = (state: string) => {
    const map: Record<string, string> = {
      UPLOADED: 'Uploaded',
      PENDING: 'Pending review',
      NEEDS_CLARIFICATION: 'Needs clarification',
      APPROVED: 'Approved',
      REJECTED: 'Rejected'
    };
    return map[state] || state;
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
      
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <h2 className="text-lg font-medium mb-4">Upload Document</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
          <select value={docType} onChange={e => setDocType(e.target.value)} className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md">
            {docTypes.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
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
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{doc.original_filename}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{getDocTypeLabel(doc.document_type)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(doc.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {getStatusLabel(doc.approval_state || 'UPLOADED')}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 space-x-4">
                  {!doc.approval_state && ['ASSIGNMENT_BRIEF', 'ROSTER'].includes(doc.document_type) && (
                    <button 
                      onClick={() => handleParse(doc.id)} 
                      disabled={parsingId === doc.id}
                      className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50 font-medium"
                    >
                      {parsingId === doc.id ? 'Parsing...' : 'Parse'}
                    </button>
                  )}
                  {doc.approval_state && (
                    <Link 
                      href={`/dashboard/${isTeacher ? 'teacher' : 'admin'}/parse-review/${doc.id}`} 
                      className="text-green-600 hover:text-green-900 font-medium"
                    >
                      Review
                    </Link>
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
