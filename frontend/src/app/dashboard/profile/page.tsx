'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import api from '@/lib/api';

export default function ProfilePage() {
  const { user, logout } = useAuth();
  
  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMsg, setPasswordMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [changingPass, setChangingPass] = useState(false);

  // Show/Hide Password states
  const [showCurrentPass, setShowCurrentPass] = useState(false);
  const [showNewPass, setShowNewPass] = useState(false);
  const [showConfirmPass, setShowConfirmPass] = useState(false);

  // Telegram state
  const [chatId, setChatId] = useState('');
  const [telegramStatus, setTelegramStatus] = useState<any>(null);
  const [telegramMsg, setTelegramMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [linkingTelegram, setLinkingTelegram] = useState(false);

  useEffect(() => {
    async function loadTelegramStatus() {
      try {
        const res = await api.get<any>('/api/users/me/telegram');
        setTelegramStatus(res);
        if (res?.telegram_chat_id) {
          setChatId(res.telegram_chat_id);
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadTelegramStatus();
  }, []);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);

    if (newPassword !== confirmPassword) {
      setPasswordMsg({ type: 'error', text: 'New password and confirm password do not match.' });
      return;
    }

    if (newPassword.length < 6) {
      setPasswordMsg({ type: 'error', text: 'New password must be at least 6 characters long.' });
      return;
    }

    setChangingPass(true);
    try {
      await api.put('/api/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMsg({ type: 'success', text: '🎉 Password changed successfully! Logging out... Please log in with your new password.' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => {
        logout();
      }, 2000);
    } catch (err: any) {
      setPasswordMsg({ type: 'error', text: err.message || 'Failed to change password.' });
    } finally {
      setChangingPass(false);
    }
  };

  const handleLinkTelegram = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramMsg(null);

    if (!chatId.trim()) {
      setTelegramMsg({ type: 'error', text: 'Please enter your Telegram Chat ID.' });
      return;
    }

    setLinkingTelegram(true);
    try {
      const res = await api.post<any>('/api/users/me/telegram-chat-id', {
        chat_id: chatId,
      });
      setTelegramMsg({ type: 'success', text: '📲 Telegram connected successfully!' });
      setTelegramStatus({ ...telegramStatus, is_linked: true });
    } catch (err: any) {
      setTelegramMsg({ type: 'error', text: err.message || 'Failed to connect Telegram.' });
    } finally {
      setLinkingTelegram(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">👤 My Profile & Security Settings</h1>
        <p className="text-sm text-gray-600">Manage your account credentials, password, and Telegram notifications.</p>
      </div>

      {/* Account Details Card */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-3">
        <h2 className="text-lg font-bold text-gray-800 border-b pb-2">User Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500 font-medium">Full Name:</span>
            <p className="text-gray-900 font-semibold">{user?.full_name}</p>
          </div>
          <div>
            <span className="text-gray-500 font-medium">Email Address:</span>
            <p className="text-gray-900 font-semibold">{user?.email}</p>
          </div>
          <div>
            <span className="text-gray-500 font-medium">Role:</span>
            <span className="ml-2 inline-block px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">
              {user?.role}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Password Change Card */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-4">
          <h2 className="text-lg font-bold text-gray-800 border-b pb-2 flex items-center gap-2">
            <span>🔐</span> Change Password
          </h2>

          {passwordMsg && (
            <div className={`p-3 rounded text-sm ${passwordMsg.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
              {passwordMsg.text}
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Password / Temp Password</label>
              <div className="relative">
                <input
                  type={showCurrentPass ? 'text' : 'password'}
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPass(!showCurrentPass)}
                  className="absolute right-3 top-2.5 text-xs font-semibold text-gray-500 hover:text-indigo-600"
                >
                  {showCurrentPass ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
              <div className="relative">
                <input
                  type={showNewPass ? 'text' : 'password'}
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPass(!showNewPass)}
                  className="absolute right-3 top-2.5 text-xs font-semibold text-gray-500 hover:text-indigo-600"
                >
                  {showNewPass ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
              <div className="relative">
                <input
                  type={showConfirmPass ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat new password"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPass(!showConfirmPass)}
                  className="absolute right-3 top-2.5 text-xs font-semibold text-gray-500 hover:text-indigo-600"
                >
                  {showConfirmPass ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={changingPass}
              className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md text-sm transition-colors disabled:opacity-50"
            >
              {changingPass ? 'Updating Password...' : 'Update Password'}
            </button>
          </form>
        </div>

        {/* Telegram Integration Card */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-4">
          <h2 className="text-lg font-bold text-gray-800 border-b pb-2 flex items-center gap-2">
            <span>📲</span> Telegram Notifications
          </h2>

          <div className="p-3 bg-blue-50 border border-blue-100 rounded text-xs text-blue-900 space-y-1">
            <p className="font-bold">How to connect Telegram:</p>
            <p>1. Open Telegram app and search for <b>@school_ops_tetris_bot</b>.</p>
            <p>2. Click <b>START</b>. The bot will display your <b>Chat ID</b> (e.g. 123456789).</p>
            <p>3. Enter your Chat ID below to link your account for instant updates!</p>
          </div>

          {telegramStatus?.is_linked ? (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800 space-y-1">
              <div className="flex items-center gap-2 font-bold text-sm">
                <span>✅</span> Telegram Linked & Active
              </div>
              <p className="text-xs text-green-700">You will receive instant alerts for assignments, announcements, and reminders directly on Telegram.</p>
            </div>
          ) : (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800 font-medium">
              ⚠️ Telegram is not linked yet.
            </div>
          )}

          {telegramMsg && (
            <div className={`p-3 rounded text-sm ${telegramMsg.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
              {telegramMsg.text}
            </div>
          )}

          <form onSubmit={handleLinkTelegram} className="space-y-4 pt-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Telegram Chat ID</label>
              <input
                type="text"
                required
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                placeholder="e.g. 123456789"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={linkingTelegram}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md text-sm transition-colors disabled:opacity-50"
            >
              {linkingTelegram ? 'Connecting Telegram...' : 'Connect Telegram'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
