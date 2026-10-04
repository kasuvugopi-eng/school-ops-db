'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';

interface TelegramStatus {
  is_linked: boolean;
  linked_at: string | null;
  linking_code: string | null;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await api.get<TelegramStatus>('/api/users/me/telegram');
        setStatus(res?.data ?? res);
      } catch (err: any) {
        setError(err.message || 'Failed to load settings');
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, []);

  const copyCode = () => {
    if (status?.linking_code) {
      navigator.clipboard.writeText(status.linking_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <div className="p-6">Loading settings...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Profile & Settings</h1>
      
      {error && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md text-sm">{error}</div>}

      <div className="bg-white shadow rounded-lg overflow-hidden mb-6">
        <div className="px-6 py-5 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Personal Information</h3>
        </div>
        <div className="px-6 py-5">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Full name</dt>
              <dd className="mt-1 text-sm text-gray-900">{user?.full_name}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Email address</dt>
              <dd className="mt-1 text-sm text-gray-900">{user?.email}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Role</dt>
              <dd className="mt-1 text-sm text-gray-900 capitalize">{user?.role}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg leading-6 font-medium text-gray-900 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
              <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.892-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
            </svg>
            Telegram Integration
          </h3>
          {status?.is_linked ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Connected
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
              Not Connected
            </span>
          )}
        </div>
        
        <div className="px-6 py-5">
          {status?.is_linked ? (
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Your account is successfully linked to Telegram. You will receive notifications and can interact with the school bot.
              </p>
              <p className="text-xs text-gray-500">
                Linked on: {status.linked_at ? new Date(status.linked_at).toLocaleDateString() : 'Unknown'}
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-600 mb-6">
                Connect your Telegram account to get instant notifications and interact with the school bot for assignment updates.
              </p>
              
              <div className="bg-gray-50 p-4 rounded-md border border-gray-200 mb-6">
                <h4 className="text-sm font-semibold text-gray-800 mb-3">Step 1: Copy your linking code</h4>
                {status?.linking_code ? (
                  <div className="flex items-center gap-3">
                    <code className="bg-white px-4 py-2 border border-gray-300 rounded text-lg font-mono text-indigo-600 select-all">
                      {status.linking_code}
                    </code>
                    <button 
                      onClick={copyCode}
                      className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      {copied ? 'Copied!' : 'Copy Code'}
                    </button>
                  </div>
                ) : (
                  <div className="text-sm text-red-600">
                    No invite token found. Only invited users can link Telegram currently.
                  </div>
                )}
              </div>
              
              <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-800 mb-3">Step 2: Send code to the bot</h4>
                <ol className="list-decimal list-inside text-sm text-gray-600 space-y-2">
                  <li>Open the Telegram app and search for our bot (or click <a href="#" className="text-indigo-600 hover:underline">@SchoolOpsBot</a>).</li>
                  <li>Start a chat with the bot.</li>
                  <li>Send the following command: <code className="bg-gray-200 px-1 py-0.5 rounded">/link {status?.linking_code || '<your-code>'}</code></li>
                </ol>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
