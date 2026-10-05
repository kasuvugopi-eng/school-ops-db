'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function SettingsPage() {
  const [school, setSchool] = useState<any>(null);
  const [quietHours, setQuietHours] = useState<{ start_hour: number; end_hour: number; is_active: bool }>({
    start_hour: 21,
    end_hour: 7,
    is_active: true
  });
  const [loading, setLoading] = useState(true);
  const [savingSchool, setSavingSchool] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);

  // School Profile Form
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [timezone, setTimezone] = useState('Asia/Kolkata');

  const fetchData = async () => {
    try {
      const [schoolRes, policyRes] = await Promise.all([
        api.get<any>('/api/schools/mine'),
        api.get<any>('/api/schools/policies/quiet-hours')
      ]);
      setSchool(schoolRes);
      setName(schoolRes?.name || '');
      setAddress(schoolRes?.address || '');
      setTimezone(schoolRes?.timezone || 'Asia/Kolkata');

      if (policyRes) {
        setQuietHours({
          start_hour: policyRes.start_hour ?? 21,
          end_hour: policyRes.end_hour ?? 7,
          is_active: policyRes.is_active ?? true
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUpdateSchool = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSchool(true);
    try {
      await api.put<any>('/api/schools/mine', { name, address, timezone });
      alert('✅ School profile updated successfully!');
      fetchData();
    } catch (err: any) {
      console.error(err);
      alert(`Failed to update school profile: ${err.message || 'Error'}`);
    } finally {
      setSavingSchool(false);
    }
  };

  const handleUpdateQuietHours = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPolicy(true);
    try {
      await api.put<any>('/api/schools/policies/quiet-hours', quietHours);
      alert('✅ Quiet Hours policy updated successfully!');
      fetchData();
    } catch (err: any) {
      console.error(err);
      alert(`Failed to update quiet hours: ${err.message || 'Error'}`);
    } finally {
      setSavingPolicy(false);
    }
  };

  const formatHourLabel = (hour: number) => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 === 0 ? 12 : hour % 12;
    return `${displayHour}:00 ${period} (${hour}:00 IST)`;
  };

  if (loading) return <div>Loading school settings...</div>;

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">⚙️ School Settings & Notification Policies</h1>
        <p className="text-gray-500">Configure your institution details, quiet hours, and notification rules.</p>
      </div>

      {/* Quiet Hours Policy Configuration Section */}
      <div className="bg-white shadow-sm rounded-xl border border-indigo-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-indigo-100 bg-indigo-50/50 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-indigo-900">🌙 Notification Quiet Hours Policy</h2>
            <p className="text-xs text-indigo-700">Set non-disruptive time slots when automated assignment reminders are muted.</p>
          </div>
          <span className={`px-3 py-1 text-xs font-semibold rounded-full ${quietHours.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
            {quietHours.is_active ? 'Active' : 'Disabled'}
          </span>
        </div>

        <form onSubmit={handleUpdateQuietHours} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                🛑 Quiet Hours Start Time (Reminders Pause)
              </label>
              <select
                value={quietHours.start_hour}
                onChange={(e) => setQuietHours(prev => ({ ...prev, start_hour: parseInt(e.target.value) }))}
                className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-900 bg-white"
              >
                {Array.from({ length: 24 }).map((_, i) => (
                  <option key={i} value={i}>{formatHourLabel(i)}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">Automatic reminders will stop sending at this hour.</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                🌅 Quiet Hours End Time (Reminders Resume)
              </label>
              <select
                value={quietHours.end_hour}
                onChange={(e) => setQuietHours(prev => ({ ...prev, end_hour: parseInt(e.target.value) }))}
                className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-900 bg-white"
              >
                {Array.from({ length: 24 }).map((_, i) => (
                  <option key={i} value={i}>{formatHourLabel(i)}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">Reminders will resume sending after this hour.</p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <input
              type="checkbox"
              id="is_active"
              checked={quietHours.is_active}
              onChange={(e) => setQuietHours(prev => ({ ...prev, is_active: e.target.checked }))}
              className="w-4 h-4 text-indigo-600 rounded"
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-800 cursor-pointer">
              Enforce Quiet Hours Rule for all automated student reminders
            </label>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={savingPolicy}
              className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 font-semibold text-sm shadow-sm disabled:opacity-50"
            >
              {savingPolicy ? 'Saving Policy...' : '💾 Save Quiet Hours Policy'}
            </button>
          </div>
        </form>
      </div>

      {/* School Profile Info Form */}
      <div className="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 font-bold text-gray-800">
          🏫 School Profile & Information
        </div>

        <form onSubmit={handleUpdateSchool} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">School Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3.5 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address / Campus Location</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-3.5 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3.5 py-2 border border-gray-300 rounded-md"
            >
              <option value="Asia/Kolkata">Asia/Kolkata (IST +5:30)</option>
              <option value="UTC">UTC</option>
              <option value="America/New_York">America/New_York (EST)</option>
            </select>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={savingSchool}
              className="bg-gray-900 text-white px-5 py-2 rounded-md hover:bg-gray-800 font-medium text-sm disabled:opacity-50"
            >
              {savingSchool ? 'Saving Profile...' : 'Save School Info'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
