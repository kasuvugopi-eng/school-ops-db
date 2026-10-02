'use client';

import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  const links = {
    ADMIN: [
      { href: '/dashboard/admin', label: 'Overview', icon: '📊' },
      { href: '/dashboard/admin/classes', label: 'Classes', icon: '🏫' },
      { href: '/dashboard/admin/teachers', label: 'Teachers', icon: '👨‍🏫' },
      { href: '/dashboard/admin/students', label: 'Students', icon: '🎓' },
      { href: '/dashboard/admin/documents', label: 'Documents', icon: '📄' },
      { href: '/dashboard/admin/audit', label: 'Audit Log', icon: '📋' },
    ],
    TEACHER: [
      { href: '/dashboard/teacher', label: 'Overview', icon: '📊' },
      { href: '/dashboard/teacher/assignments', label: 'Assignments', icon: '📝' },
      { href: '/dashboard/teacher/documents', label: 'Documents', icon: '📄' },
    ],
    STUDENT: [
      { href: '/dashboard/student', label: 'My Assignments', icon: '🎒' },
    ],
    GUARDIAN: [
      { href: '/dashboard/parent', label: 'Child Progress', icon: '📈' },
    ],
  }[user.role as 'ADMIN' | 'TEACHER' | 'STUDENT' | 'GUARDIAN'] || [];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-50 z-40 md:hidden" onClick={onClose} />
      )}
      
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-slate-300 transform transition-transform duration-200 ease-in-out md:translate-x-0 md:static md:flex-shrink-0 flex flex-col ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-6 flex items-center justify-between md:justify-center">
          <h1 className="text-2xl font-bold text-white">SchoolOps</h1>
          <button className="md:hidden text-gray-400" onClick={onClose}>✕</button>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {links.map((link) => {
            const isActive = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link 
                key={link.href} 
                href={link.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive ? 'bg-indigo-600 text-white' : 'hover:bg-slate-800 hover:text-white'}`}
                onClick={() => onClose()}
              >
                <span className="text-xl">{link.icon}</span>
                <span className="font-medium">{link.label}</span>
              </Link>
            );
          })}
        </nav>
        
        <div className="p-4 border-t border-slate-800">
          <button 
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <span className="text-xl">🚪</span>
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </div>
    </>
  );
}
