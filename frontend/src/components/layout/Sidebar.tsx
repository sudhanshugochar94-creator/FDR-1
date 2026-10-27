import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  PlusCircle,
  AlertTriangle,
  Calendar,
  RefreshCw,
  Bot,
  BarChart3,
  History,
  Users,
  Shield,
  X,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: UserRole[];
  badge?: string | number;
  badgeVariant?: 'default' | 'destructive' | 'secondary' | 'outline' | 'warning';
}

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'FDR Records',
    href: '/fdrs',
    icon: FileText,
  },
  {
    title: 'Submit FDR',
    href: '/fdrs/new',
    icon: PlusCircle,
    roles: ['institution_user', 'admin'],
  },
  {
    title: 'Duplicate Review',
    href: '/duplicates',
    icon: AlertTriangle,
    roles: ['reviewer', 'admin'],
  },
  {
    title: 'Maturity & Alerts',
    href: '/maturity',
    icon: Calendar,
  },
  {
    title: 'Renewals & Releases',
    href: '/renewals',
    icon: RefreshCw,
  },
  {
    title: 'AI Assistant',
    href: '/ai-assistant',
    icon: Bot,
  },
  {
    title: 'Reports & Analytics',
    href: '/reports',
    icon: BarChart3,
    roles: ['reviewer', 'approving_authority', 'admin'],
  },
  {
    title: 'Audit Trail',
    href: '/audit',
    icon: History,
    roles: ['admin', 'approving_authority'],
  },
  {
    title: 'User Management',
    href: '/admin/users',
    icon: Users,
    roles: ['admin'],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const location = useLocation();

  const userRole = user?.role || 'reviewer';

  const filteredItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return item.roles.includes(userRole);
  });

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-border bg-slate-900 text-slate-100 transition-transform duration-200 ease-in-out lg:static lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header / Brand */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 shadow-md">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold tracking-wide text-white uppercase leading-tight">
                FDR Portal
              </div>
              <div className="text-[11px] font-medium text-slate-400 leading-tight">
                Regulatory & Compliance
              </div>
            </div>
          </div>

          {/* Close button on mobile */}
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Institution / Role Indicator */}
        <div className="border-b border-slate-800/80 bg-slate-950/40 px-6 py-3">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Workspace
          </div>
          <div className="mt-0.5 truncate text-xs font-medium text-slate-200">
            {user?.institution?.name || 'Regulatory Authority Central Office'}
          </div>
          <div className="mt-1 flex items-center space-x-2">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400"></span>
            <span className="text-[11px] font-medium capitalize text-slate-400">
              Role: {userRole.replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
          <div className="px-2 pb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Menu
          </div>
          {filteredItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.href ||
              (item.href !== '/dashboard' &&
                item.href !== '/' &&
                location.pathname.startsWith(item.href));

            return (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={onClose}
                className={cn(
                  'group flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
                )}
              >
                <div className="flex items-center space-x-3">
                  <Icon
                    className={cn(
                      'h-5 w-5 shrink-0 transition-colors',
                      isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                    )}
                  />
                  <span>{item.title}</span>
                </div>
                {item.badge && (
                  <Badge
                    variant={item.badgeVariant || 'secondary'}
                    className={cn(
                      'px-1.5 py-0.2 text-[10px] font-bold leading-none',
                      isActive && 'bg-white text-blue-900 border-transparent'
                    )}
                  >
                    {item.badge}
                  </Badge>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Bottom system status badge */}
        <div className="border-t border-slate-800 p-4">
          <div className="rounded-lg bg-slate-800/50 p-3 text-xs">
            <div className="flex items-center justify-between text-slate-300">
              <span className="font-medium">System Compliance</span>
              <span className="font-semibold text-emerald-400">99.8%</span>
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              Security Protocol: <span className="text-slate-300">FIPS-140-2</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
