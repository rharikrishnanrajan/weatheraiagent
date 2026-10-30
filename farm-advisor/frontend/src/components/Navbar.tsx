import { NavLink } from 'react-router-dom';
import { Sprout, CloudSun, UserCheck, BookOpen, MapPin } from 'lucide-react';
import { useFarmStore } from '../store/useFarmStore';

export const Navbar = () => {
  const profile = useFarmStore((s) => s.profile);
  const weather = useFarmStore((s) => s.weather);

  const navItems = [
    { to: '/', label: 'Chat Advisor', icon: Sprout },
    { to: '/weather', label: 'Weather Dashboard', icon: CloudSun },
    { to: '/profile', label: 'Farm Profile', icon: UserCheck },
    { to: '/kb', label: 'Knowledge Base', icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-stone-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-farm-600 flex items-center justify-center text-white shadow-sm">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-stone-900">AgriPulse</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-farm-100 text-farm-800 font-semibold border border-farm-200">
                  AI Agent
                </span>
              </div>
              <p className="text-xs text-stone-500 hidden sm:block">Weather-Based Precision Farming Advisor</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-farm-50 text-farm-700 border border-farm-200 shadow-sm'
                        : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Right Status Badge & Farm Location */}
          <div className="flex items-center space-x-3">
            {profile && (
              <div className="hidden lg:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-stone-100 border border-stone-200 text-xs font-medium text-stone-700">
                <MapPin className="w-3.5 h-3.5 text-farm-600" />
                <span className="max-w-[140px] truncate">{profile.location_name}</span>
                {weather && (
                  <span className="font-semibold text-stone-900 ml-1">
                    {Math.round(weather.current.temperature_2m)}°C
                  </span>
                )}
              </div>
            )}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>NVIDIA NIM</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
