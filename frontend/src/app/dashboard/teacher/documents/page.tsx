'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import FileUpload from '@/components/ui/FileUpload';
import StatusBadge from '@/components/ui/StatusBadge';
import Link from 'next/link';

export default function TeacherDocumentsPage() {
  const router = useRouter();

  const [documents, setDocuments] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [targetClassId, setTargetClassId] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [parsingId, setParsingId] = useState<string | null>(null);
  const [docType, setDocType] = useState('ASSIGNMENT_BRIEF');
  const [activeTab, setActiveTab] = useState<'MY_UPLOADS' | 'SCHOOL_POLICIES'>('MY_UPLOADS');

  const fetchDocsAndClasses = async () => {
    try {
      const [docRes, classRes] = await Promise.all([
        api.get<any>('/api/documents'),
        api.get<any>('/api/classes')
      ]);
      setDocuments(Array.isArray(docRes) ? docRes : (docRes?.items ?? docRes?.data ?? []));
      setClasses(Array.isArray(classRes) ? classRes : (classRes?.items ?? classRes?.data ?? []));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { 
    fetchDocsAndClasses(); 
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      // @ts-ignore
      await api.uploadFile<any>('/api/documents/upload', file, { 
          document_type: docType,
          ...(docType === 'CLASS_MATERIAL' && targetClassId ? { target_class_id: targetClassId } : {})
      });
      fetchDocsAndClasses();
      alert('Document uploaded successfully!');
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
      await api.post<any>(`/api/documents/${id}/parse`);
      await fetchDocsAndClasses();
      router.push(`/dashboard/teacher/parse-review/${id}`);
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Unknown error';
      alert(`Parse failed: ${detail}`);
    } finally {
      setParsingId(null);
    }
  };

  const docTypes = [
    { value: 'ASSIGNMENT_BRIEF', label: 'Assignment Brief' },
    { value: 'CLASS_MATERIAL', label: 'Class Material / Study Sheet' },
  ];

  const getDocTypeLabel = (type: string) => {
    const map: Record<string, string> = {
      ASSIGNMENT_BRIEF: 'Assignment Brief',
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

  const schoolPolicies = documents.filter((d) => d.document_type === 'POLICY');
  const myUploads = documents.filter((d) => d.document_type !== 'POLICY');

  const activeDocuments = activeTab === 'SCHOOL_POLICIES' ? schoolPolicies : myUploads;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">📚 Teacher Documents & Resources</h1>
        <p className="text-sm text-gray-600">
          Upload class materials & assignments, or view official school policies.
        </p>
      </div>

      {/* Upload Box for Teachers */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-lg font-medium text-gray-900 mb-4">📤 Upload New Class Document</h2>
        <div className="flex gap-4 mb-4">
          <div className="flex-1 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">Select Document Category</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              {docTypes.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {dt.label}
                </option>
              ))}
            </select>
          </div>
          
          {docType === 'CLASS_MATERIAL' && (
            <div className="flex-1 max-w-xs">
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Class (Optional)</label>
              <select
                value={targetClassId}
                onChange={(e) => setTargetClassId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="">-- All Classes / None --</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        <FileUpload onFileSelect={handleUpload} loading={uploading} />
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('MY_UPLOADS')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'MY_UPLOADS'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📝 My Uploads & Materials ({myUploads.length})
          </button>
          <button
            onClick={() => setActiveTab('SCHOOL_POLICIES')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'SCHOOL_POLICIES'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📢 School Policies ({schoolPolicies.length})
          </button>
        </nav>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading documents...</div>
        ) : activeDocuments.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {activeTab === 'SCHOOL_POLICIES'
              ? 'No school policies published yet.'
              : 'No documents uploaded yet. Upload your first class assignment above.'}
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Filename
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uploaded At
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {activeDocuments.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {doc.original_filename}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {getDocTypeLabel(doc.document_type)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {doc.approval_state ? (
                      <StatusBadge state={doc.approval_state} />
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        Uploaded
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                    <button
                      onClick={() => {
                        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
                        window.open(`http://localhost:8000/api/documents/${doc.id}/download?token=${encodeURIComponent(token)}`, '_blank');
                      }}
                      className="text-blue-600 hover:text-blue-900 inline-flex items-center gap-1 font-medium"
                    >
                      📥 Download
                    </button>
                    {doc.document_type === 'ASSIGNMENT_BRIEF' && (
                      doc.approval_state ? (
                        <Link
                          href={`/dashboard/teacher/parse-review/${doc.id}`}
                          className="text-emerald-600 hover:text-emerald-900 inline-flex items-center gap-1 font-medium"
                        >
                          👁️ View Review
                        </Link>
                      ) : (
                        <button
                          onClick={() => handleParse(doc.id)}
                          disabled={parsingId === doc.id}
                          className="text-emerald-600 hover:text-emerald-900 inline-flex items-center gap-1 font-medium disabled:opacity-50"
                        >
                          {parsingId === doc.id ? '⚡ Parsing AI...' : '✨ Parse AI Assignment'}
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
