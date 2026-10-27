import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  Search,
  Menu,
  LogOut,
  User as UserIcon,
  Settings,
  CheckCheck,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useNotifications } from '@/hooks/useNotifications';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface TopBarProps {
  onToggleSidebar: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  // Generate breadcrumb items from pathname
  const pathParts = location.pathname.split('/').filter(Boolean);
  const breadcrumbMap: Record<string, string> = {
    dashboard: 'Dashboard',
    fdrs: 'FDR Records',
    new: 'New Deposit',
    duplicates: 'Duplicate Detection',
    maturity: 'Maturity Calendar',
    renewals: 'Renewals & Releases',
    'ai-assistant': 'AI Compliance Assistant',
    reports: 'Regulatory Reports',
    audit: 'Audit Log',
    admin: 'Administration',
    users: 'User Directory',
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/fdrs?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'FD';

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur-md sm:px-6">
      {/* Left section: Hamburger button + Breadcrumbs */}
      <div className="flex items-center space-x-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleSidebar}
          className="lg:hidden text-foreground"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Breadcrumb navigation */}
        <nav aria-label="Breadcrumb" className="hidden sm:flex items-center space-x-1.5 text-sm">
          <span className="font-semibold text-primary">FDR Portal</span>
          {pathParts.map((part, index) => {
            const isLast = index === pathParts.length - 1;
            const title = breadcrumbMap[part] || part.toUpperCase();
            return (
              <React.Fragment key={index}>
                <span className="text-muted-foreground">/</span>
                <span
                  className={
                    isLast
                      ? 'font-medium text-foreground'
                      : 'text-muted-foreground'
                  }
                >
                  {title}
                </span>
              </React.Fragment>
            );
          })}
        </nav>
      </div>

      {/* Middle/Right section: Search + Notifications + User profile */}
      <div className="flex items-center space-x-2 sm:space-x-4">
        {/* Quick Search */}
        <form onSubmit={handleSearchSubmit} className="relative hidden md:block w-56 lg:w-72">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search FDR #, bank, ref..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 text-xs bg-muted/40 focus:bg-background h-9 rounded-md"
          />
        </form>

        {/* Notifications Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
              <Bell className="h-5 w-5 text-muted-foreground" />
              {unreadCount > 0 && (
                <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 sm:w-96 p-0 shadow-lg">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-sm">Notifications</span>
                {unreadCount > 0 && (
                  <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                    {unreadCount} new
                  </Badge>
                )}
              </div>
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="h-7 text-xs text-muted-foreground hover:text-foreground"
                >
                  <CheckCheck className="mr-1 h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
            </div>

            <div className="max-h-80 overflow-y-auto divide-y divide-border">
              {notifications.length === 0 ? (
                <div className="p-4 text-center text-xs text-muted-foreground">
                  No notifications yet.
                </div>
              ) : (
                notifications.slice(0, 5).map((n) => (
                  <div
                    key={n.id}
                    onClick={() => markAsRead(n.id)}
                    className={`flex cursor-pointer items-start p-3.5 text-xs transition-colors hover:bg-muted/50 ${
                      !n.is_read ? 'bg-primary/5 font-medium' : ''
                    }`}
                  >
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground">{n.title}</span>
                        {!n.is_read && (
                          <span className="h-2 w-2 rounded-full bg-blue-600"></span>
                        )}
                      </div>
                      <p className="text-muted-foreground line-clamp-2">{n.message}</p>
                      <div className="text-[10px] text-muted-foreground">
                        {new Date(n.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="border-t p-2 text-center">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs text-primary"
                onClick={() => navigate('/maturity')}
              >
                View all compliance alerts
                <ExternalLink className="ml-1.5 h-3 w-3" />
              </Button>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center space-x-2 pl-2 pr-2.5 h-10 hover:bg-muted"
            >
              <Avatar className="h-8 w-8 border border-border">
                <AvatarFallback className="bg-primary/10 text-primary font-semibold text-xs">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="hidden text-left sm:block">
                <div className="text-xs font-semibold text-foreground leading-tight">
                  {user?.full_name || 'Regulatory Official'}
                </div>
                <div className="text-[10px] text-muted-foreground capitalize leading-tight">
                  {user?.role ? user.role.replace('_', ' ') : 'Officer'}
                </div>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-semibold leading-none">{user?.full_name}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email || 'officer@regulator.gov'}
                </p>
                <div className="pt-1">
                  <Badge variant="outline" className="text-[10px] uppercase font-mono">
                    {user?.role}
                  </Badge>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate('/dashboard')}>
              <UserIcon className="mr-2 h-4 w-4" />
              <span>Profile Details</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => navigate('/audit')}>
              <Settings className="mr-2 h-4 w-4" />
              <span>Audit & Preferences</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

export default TopBar;
