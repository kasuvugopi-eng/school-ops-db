'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';

export default function AdminParseReviewPage() {
  const { id } = useParams();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState<any>({});
  const [submitting, setSubmitting] = useState(false);
  const [classes, setClasses] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [students, setStudents] = useState<any[]>([]);
  const [selectedClassIds, setSelectedClassIds] = useState<string[]>([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState<Set<string>>(new Set());
  const [rosterRows, setRosterRows] = useState<any[] | null>(null);

  const fetchParseResult = async (loadedClasses?: any[]) => {
    try {
      const res = await api.get<any>(`/api/documents/${id}/parse-result`);
      const parseData = res?.data ?? res;
      setData(parseData);
      setFormData(parseData?.parsed_data ?? {});
      
      const targetClasses = (loadedClasses && loadedClasses.length > 0) ? loadedClasses : classes;
      let initialClassIds: string[] = [];
      const llmClassId = parseData?.parsed_data?.target_class_id;
      if (llmClassId) {
        const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(llmClassId);
        if (isUUID) {
          initialClassIds = [llmClassId];
        } else {
          const matchedClass = targetClasses.find((c: any) => 
            c.name.toLowerCase().includes(llmClassId.toLowerCase()) || 
            llmClassId.toLowerCase().includes(c.name.toLowerCase()) ||
            (c.grade_level && llmClassId.includes(c.grade_level))
          );
          if (matchedClass) {
            initialClassIds = [matchedClass.id];
          }
        }
      }
      const finalClassIds = parseData?.parsed_data?.class_ids || initialClassIds;
      setSelectedClassIds(finalClassIds);

      const parsedStudentIds = parseData?.parsed_data?.target_student_ids || parseData?.parsed_data?.student_ids || [];
      if (parsedStudentIds.length > 0) {
        setSelectedStudentIds(new Set(parsedStudentIds));
      }
      setErrorMsg(null);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Failed to load parse result');
    }
  };

  useEffect(() => {
    async function load() {
      let fetchedClasses = [];
      try {
        const clsRes = await api.get<any>('/api/classes');
        fetchedClasses = Array.isArray(clsRes) ? clsRes : (clsRes?.items ?? clsRes?.data ?? []);
        setClasses(fetchedClasses);
      } catch (err) {
        console.error(err);
      }
      await fetchParseResult(fetchedClasses);
      setLoading(false);
    }
    load();
  }, [id]);

  useEffect(() => {
    if (selectedClassIds.length > 0) {
      const qs = selectedClassIds.join(',');
      api.get<any>(`/api/students?class_ids=${qs}`)
         .then(res => {
           const fetchedStudents = Array.isArray(res) ? res : (res?.items ?? res?.data ?? []);
           setStudents(fetchedStudents);
           const validIds = new Set(fetchedStudents.map((s: any) => s.id));
           setSelectedStudentIds(prev => {
             if (prev.size === 0) {
               return new Set(fetchedStudents.map((s: any) => s.id));
             }
             const next = new Set<string>();
             prev.forEach(studentId => {
               if (validIds.has(studentId)) next.add(studentId);
             });
             return next.size > 0 ? next : new Set(fetchedStudents.map((s: any) => s.id));
           });
         })
         .catch(console.error);
    } else {
      setStudents([]);
      setSelectedStudentIds(new Set());
    }
  }, [selectedClassIds]);

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
      const studentIds = Array.from(selectedStudentIds);
      let target_type = "CLASS";
      if (selectedClassIds.length > 0 && studentIds.length > 0 && studentIds.length < students.length) {
        target_type = studentIds.length === 1 ? "INDIVIDUAL" : "GROUP";
      }
      
      await api.post<any>(`/api/documents/${id}/clarify`, {
        title: formData.title || null,
        subject: formData.subject || null,
        due_date: formData.due_date || null,
        target_class_id: selectedClassIds.length > 0 ? selectedClassIds[0] : null,
        target_student_ids: studentIds.length > 0 ? studentIds : null,
        target_type: target_type,
        instructions: formData.instructions || null
      });
      await fetchParseResult(classes);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to clarify');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleClass = (classId: string) => {
    if (data.approval_state === 'APPROVED') return;
    setSelectedClassIds(prev => 
      prev.includes(classId) ? prev.filter(cId => cId !== classId) : [...prev, classId]
    );
  };

  const toggleStudent = (studentId: string) => {
    if (data.approval_state === 'APPROVED') return;
    const newSet = new Set(selectedStudentIds);
    if (newSet.has(studentId)) newSet.delete(studentId);
    else newSet.add(studentId);
    setSelectedStudentIds(newSet);
  };

  const toggleAllStudents = () => {
    if (data.approval_state === 'APPROVED') return;
    if (selectedStudentIds.size === students.length && students.length > 0) {
      setSelectedStudentIds(new Set());
    } else {
      setSelectedStudentIds(new Set(students.map(s => s.id)));
    }
  };

  if (loading) return <div className="p-6">Loading...</div>;
  if (!data) return <div className="p-6">Parse result not found</div>;

  const confidence = data.confidence_notes?.overall_confidence 
    ? Math.round(data.confidence_notes.overall_confidence * 100) 
    : 0;

  const needsClarification = data.approval_state === 'NEEDS_CLARIFICATION';

  const isRoster = Boolean(data.parsed_data?.rows && Array.isArray(data.parsed_data.rows));

  if (isRoster) {
    const rawRows = data.parsed_data.rows || [];
    const rows = rosterRows || rawRows;

    const handleAutoCleanDuplicates = () => {
      // Filter out duplicate candidates / rows with duplicate flags
      const cleaned = rawRows.filter((r: any) => {
        const flagsStr = (r.flags || []).join(' ').toLowerCase();
        return !flagsStr.includes('duplicate');
      });
      setRosterRows(cleaned);
      alert(`✨ Cleaned Roster! Removed ${rawRows.length - cleaned.length} duplicate entry/entries.`);
    };

    const handleDownloadCleanedCSV = () => {
      const csvRows = [
        ['full_name', 'grade_class', 'parent_name', 'parent_contact', 'notes']
      ];

      rows.forEach((r: any) => {
        csvRows.push([
          `"${(r.student_name || '').replace(/"/g, '""')}"`,
          `"${(r.grade_class || '').replace(/"/g, '""')}"`,
          `"${(r.parent_name || '').replace(/"/g, '""')}"`,
          `"${(r.parent_contact || '').replace(/"/g, '""')}"`,
          `"${(r.notes || '').replace(/"/g, '""')}"`
        ]);
      });

      const csvContent = 'data:text/csv;charset=utf-8,' + csvRows.map(e => e.join(',')).join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `cleaned_roster_${id}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">📋 Review Parsed Class Roster</h1>
            <p className="text-sm text-gray-600">Extracted {rows.length} student records from roster document.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleAutoCleanDuplicates}
              className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-md text-sm font-semibold shadow-sm flex items-center gap-1"
            >
              ✨ Remove Duplicates
            </button>
            <button
              onClick={handleDownloadCleanedCSV}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-semibold shadow-sm flex items-center gap-1"
            >
              📥 Download Cleaned CSV
            </button>
            <div className="bg-green-100 text-green-800 px-3 py-1.5 rounded-full text-sm font-medium">
              Confidence: {confidence}%
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="bg-red-50 text-red-800 p-4 rounded-md text-sm border border-red-200">
            {errorMsg}
          </div>
        )}

        <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Student Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Class/Grade</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parent Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parent Contact</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notes & Flags</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200 text-sm">
              {rows.map((r: any, idx: number) => (
                <tr key={idx} className={r.flags?.length ? 'bg-yellow-50/50' : ''}>
                  <td className="px-4 py-3 font-semibold text-gray-900">{r.student_name}</td>
                  <td className="px-4 py-3 text-gray-600">{r.grade_class || 'N/A'}</td>
                  <td className="px-4 py-3 text-gray-600">{r.parent_name || 'N/A'}</td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs">{r.parent_contact || 'N/A'}</td>
                  <td className="px-4 py-3 text-xs">
                    <p className="text-gray-600">{r.notes}</p>
                    {r.flags?.map((f: string, fi: number) => (
                      <span key={fi} className="inline-block mt-0.5 mr-1 px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded font-medium">
                        ⚠️ {f}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={5} className="p-4 text-center text-gray-500">No roster rows found in document.</td></tr>
              )}
            </tbody>
          </table>

          <div className="p-4 bg-gray-50 border-t flex justify-end gap-3">
            <button onClick={() => router.back()} disabled={submitting} className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-100">Back</button>
            {data.approval_state === 'APPROVED' ? (
              <span className="px-4 py-2 text-green-700 font-bold flex items-center gap-1">✅ Approved Roster</span>
            ) : (
              <button 
                onClick={handleApprove} 
                disabled={submitting} 
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-semibold disabled:opacity-50"
              >
                {submitting ? 'Approving...' : '✅ Mark Reviewed & Approved'}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Review Parsed Document (Admin)</h1>
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

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input type="text" value={formData.title || ''} onChange={e => setFormData({...formData, title: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
            <input type="text" value={formData.subject || ''} onChange={e => setFormData({...formData, subject: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" />
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
          <input type="datetime-local" value={formData.due_date || ''} onChange={e => setFormData({...formData, due_date: e.target.value})} disabled={data.approval_state === 'APPROVED'} className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100" />
        </div>

        <div className="grid grid-cols-2 gap-6 border-t border-gray-100 pt-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target Classes</label>
            <div className={`border border-gray-200 rounded-md p-3 max-h-48 overflow-y-auto space-y-2 ${data.approval_state === 'APPROVED' ? 'bg-gray-100' : 'bg-gray-50'}`}>
              {classes.length === 0 ? (
                <p className="text-sm text-gray-500">No classes found.</p>
              ) : (
                classes.map(c => (
                  <label key={c.id} className="flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      checked={selectedClassIds.includes(c.id)}
                      onChange={() => toggleClass(c.id)}
                      disabled={data.approval_state === 'APPROVED'}
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
            <div className={`border border-gray-200 rounded-md p-3 max-h-48 overflow-y-auto space-y-2 ${selectedClassIds.length === 0 || data.approval_state === 'APPROVED' ? 'bg-gray-100 opacity-60' : 'bg-gray-50'}`}>
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
                      disabled={data.approval_state === 'APPROVED'}
                      className="rounded text-indigo-600 focus:ring-indigo-500" 
                    />
                    <span>Select All</span>
                  </label>
                  {students.map(s => (
                    <label key={s.id} className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={selectedStudentIds.has(s.id)}
                        onChange={() => toggleStudent(s.id)}
                        disabled={data.approval_state === 'APPROVED'}
                        className="rounded text-indigo-600 focus:ring-indigo-500" 
                      />
                      <span>{s.full_name || s.email}</span>
                    </label>
                  ))}
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
