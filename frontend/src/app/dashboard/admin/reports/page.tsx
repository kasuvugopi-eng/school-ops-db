'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function ReportsPage() {
  const [teacherReport, setTeacherReport] = useState<any[]>([]);
  const [classReport, setClassReport] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    try {
      const [tRes, cRes] = await Promise.all([
        api.get<any>('/api/reports/teacher-performance'),
        api.get<any>('/api/reports/class-completion')
      ]);
      setTeacherReport(Array.isArray(tRes) ? tRes : []);
      setClassReport(Array.isArray(cRes) ? cRes : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const downloadCSV = (type: 'teacher' | 'class') => {
    const token = localStorage.getItem('access_token');
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/reports/export/csv?report_type=${type}`;
    
    // Trigger direct download
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.blob())
      .then(blob => {
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = type === 'teacher' ? 'Teacher_Performance_Report.csv' : 'Class_Completion_Report.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch(err => console.error(err));
  };

  if (loading) return <div>Loading system reports...</div>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">📈 School-wide System Reports & Analytics</h1>
        <p className="text-gray-500">Analyze teacher performance, class assignment completion rates, and export CSV reports.</p>
      </div>

      {/* Teacher Performance Report Section */}
      <div className="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-gray-800">👨‍🏫 Teacher Performance & Review Activity</h2>
            <p className="text-xs text-gray-500">Track assignment creation, total student reviews given, and approvals.</p>
          </div>
          <button
            onClick={() => downloadCSV('teacher')}
            className="bg-green-600 text-white px-3.5 py-1.5 rounded-md hover:bg-green-700 text-sm font-medium flex items-center gap-1.5 shadow-sm"
          >
            <span>📥 Export CSV</span>
          </button>
        </div>

        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Teacher Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assignments Created</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Reviews Given</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Approvals Granted</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {teacherReport.map((t) => (
              <tr key={t.teacher_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{t.teacher_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-semibold">{t.assignments_created}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-semibold">{t.reviews_given}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-semibold">{t.approved_count}</td>
              </tr>
            ))}
            {teacherReport.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-6 text-center text-gray-500 text-sm">No teacher activity recorded yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Class Completion Rate Report Section */}
      <div className="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-gray-800">🏫 Class Assignment Completion & Stuck Analysis</h2>
            <p className="text-xs text-gray-500">Overview of completed, blocked (needs help), and pending submissions by class.</p>
          </div>
          <button
            onClick={() => downloadCSV('class')}
            className="bg-green-600 text-white px-3.5 py-1.5 rounded-md hover:bg-green-700 text-sm font-medium flex items-center gap-1.5 shadow-sm"
          >
            <span>📥 Export CSV</span>
          </button>
        </div>

        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Class Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Grade Level</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Enrolled Students</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Completed Submissions</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Blocked (Needs Help)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pending Review</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {classReport.map((c) => (
              <tr key={c.class_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.class_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.grade_level}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-semibold">{c.total_students}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-semibold">{c.total_completed}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-semibold">{c.total_blocked}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-600 font-semibold">{c.total_pending_review}</td>
              </tr>
            ))}
            {classReport.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-6 text-center text-gray-500 text-sm">No class records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
