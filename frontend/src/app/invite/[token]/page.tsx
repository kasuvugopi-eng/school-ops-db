'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useParams, useRouter, useSearchParams } from 'next/navigation';

export default function InviteAcceptPage() {
  const { token } = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const [invite, setInvite] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    full_name: searchParams.get('name') || '',
    email: '',
    password: '',
    phone: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const prefilledName = searchParams.get('name');
    if (prefilledName) {
      setFormData(prev => ({ ...prev, full_name: prefilledName }));
    }
  }, [searchParams]);

  useEffect(() => {
    async function validate() {
      try {
        const res = await api.get<any>(`/api/invites/${token}/validate`);
        setInvite(res?.data ?? res);
      } catch (err) {
        setError('Invalid or expired invite link.');
      } finally {
        setLoading(false);
      }
    }
    validate();
  }, [token]);

  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        token: token as string,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        phone: formData.phone.trim() ? formData.phone.trim() : null
      };
      await api.post<any>(`/api/invites/${token}/accept`, payload);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Failed to create account');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50">Loading...</div>;
  
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 p-4">
        <div className="bg-white p-8 rounded-xl shadow-xl w-full max-w-md text-center">
          <div className="text-green-500 text-5xl mb-4">✓</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Account Created!</h2>
          <p className="text-gray-600 mb-6">You've successfully joined {invite?.school_name}.</p>
          
          <div className="bg-indigo-50 rounded-lg p-4 mb-6 text-left border border-indigo-100">
            <h3 className="font-semibold text-indigo-900 mb-2 flex items-center gap-2">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.892-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
              Next Step: Connect Telegram
            </h3>
            <p className="text-sm text-indigo-800 mb-2">Get instant notifications and interact with your school by linking your Telegram account.</p>
            <p className="text-sm text-indigo-800 font-medium">Send this message to @SchoolOpsBot:</p>
            <code className="block bg-white px-3 py-2 mt-2 border border-indigo-200 rounded text-center font-mono font-bold text-indigo-600 select-all">
              /link {token}
            </code>
          </div>
          
          <button 
            onClick={() => router.push('/login')}
            className="w-full bg-indigo-600 text-white py-2 rounded-md hover:bg-indigo-700 transition font-medium"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }
  
  if (error && !invite) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="bg-white p-8 rounded-xl shadow-xl w-full max-w-md text-center">
        <div className="text-red-500 text-4xl mb-4">❌</div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">Invalid Invite</h2>
        <p className="text-gray-600">{error}</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 p-4">
      <div className="bg-white p-8 rounded-xl shadow-xl w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">You've been invited!</h2>
          <p className="text-gray-600 mt-2">Join <span className="font-semibold">{invite.school_name}</span> as a <span className="font-semibold capitalize">{invite.role}</span></p>
        </div>
        
        {error && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md text-sm">{error}</div>}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input type="text" required value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type={showPassword ? 'text' : 'password'} required value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-12" />
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-8 text-xs text-gray-500 font-medium">
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone (Optional)</label>
            <input type="tel" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          
          <button type="submit" disabled={submitting} className="w-full bg-indigo-600 text-white py-2 rounded-md hover:bg-indigo-700 transition disabled:opacity-50 mt-6">
            {submitting ? 'Creating Account...' : 'Accept Invite & Join'}
          </button>
        </form>
      </div>
    </div>
  );
}
