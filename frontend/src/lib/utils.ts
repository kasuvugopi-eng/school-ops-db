export function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

export function formatDateTime(dateString: string | null): string {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function timeAgo(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function getStateColor(state: string): string {
  const normalized = state?.toUpperCase();
  const colors: Record<string, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    PENDING_APPROVAL: 'bg-yellow-100 text-yellow-700',
    ACTIVE: 'bg-blue-100 text-blue-700',
    COMPLETED: 'bg-green-100 text-green-700',
    CANCELLED: 'bg-red-100 text-red-700',
    NOT_STARTED: 'bg-gray-100 text-gray-700',
    IN_PROGRESS: 'bg-blue-100 text-blue-700',
    BLOCKED: 'bg-red-100 text-red-700',
    SUBMITTED: 'bg-purple-100 text-purple-700',
    REVISION_REQUESTED: 'bg-orange-100 text-orange-700',
    RESUBMITTED: 'bg-indigo-100 text-indigo-700',
  };
  return colors[normalized] || colors[state] || 'bg-gray-100 text-gray-700';
}

export function getStateLabel(state: string): string {
  if (!state) return '';
  return state.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
}

export function classNames(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function getDashboardRoute(role: string): string {
  const r = (role || '').toUpperCase();
  if (r === 'ADMIN') return '/dashboard/admin';
  if (r === 'TEACHER') return '/dashboard/teacher';
  if (r === 'STUDENT') return '/dashboard/student';
  if (r === 'GUARDIAN') return '/dashboard/parent';
  return '/dashboard/admin';
}

