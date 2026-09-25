'use client';

import { LucideIcon } from 'lucide-react';
import { usePathname } from 'next/navigation';


interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
}

interface SettingsNavProps {
  items: NavItem[];
}

export function SettingsNav({ items }: SettingsNavProps) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col space-y-1">
      {items.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
        const cls = isActive ? 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors bg-primary/10 text-primary' : 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors text-muted-foreground hover:bg-muted hover:text-foreground';
        return (
          <a
            key={item.href}
            href={item.href}
            className={cls}
          >
            {<item.icon className="h-4 w-4" />}
            {item.title}
          </a>
        );
      })}
    </nav>
  );
}
