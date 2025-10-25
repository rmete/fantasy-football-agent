'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Settings } from 'lucide-react';

const routes = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="border-b">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link href="/dashboard" className="text-2xl font-bold">
            Fantasy AI Manager
          </Link>
          <div className="flex gap-6">
            {routes.map((route) => {
              const Icon = route.icon;
              return (
                <Link
                  key={route.path}
                  href={route.path}
                  className={cn(
                    'text-sm font-medium transition-colors hover:text-primary flex items-center gap-2',
                    pathname === route.path
                      ? 'text-primary'
                      : 'text-muted-foreground'
                  )}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {route.name}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
