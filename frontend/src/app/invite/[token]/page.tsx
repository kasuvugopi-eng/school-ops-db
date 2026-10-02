'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';

export default function InviteAcceptPage() {
  const { token } = useParams();
  const router = useRouter();
  
  const [invite, setInvite] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    phone: ''
  });
  const [submitting, setSubmitting] = useState(false);

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
      alert('Account created successfully! Please login.');
      router.push('/login');
    } catch (err: any) {
      setError(err.message || 'Failed to create account');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50">Loading...</div>;
  
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" required value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
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
