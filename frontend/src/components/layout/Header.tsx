'use client';

import { useAuth } from '@/lib/auth';

export default function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const { user } = useAuth();
  
  return (
    <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-4">
        <button 
          onClick={onMenuClick}
          className="md:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <h2 className="text-lg font-semibold text-gray-800 hidden sm:block">SchoolOps Dashboard</h2>
      </div>
      
      {user && (
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-medium text-gray-900">{user.full_name}</div>
            <div className="text-xs text-gray-500 capitalize">{user.role}</div>
          </div>
          <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold">
            {user.full_name?.charAt(0).toUpperCase()}
          </div>
        </div>
      )}
    </header>
  );
}
