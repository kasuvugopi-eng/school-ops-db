'use client';

import { getStateColor, getStateLabel } from '@/lib/utils';

export default function StatusBadge({ state }: { state: string }) {
  const colorClass = getStateColor(state) || 'bg-gray-100 text-gray-800';
  const label = getStateLabel(state) || state;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}
