import React, { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useGlobalState } from '../state/globalState';
import {
    UtensilsCrossed,
    ChefHat,
    User,
    Coffee,
    Menu,
    X,
    LogOut,
    Bell,
    RefreshCw
} from 'lucide-react';

export const Layout = () => {
    const { user, logout, resetProcess } = useGlobalState();
    const location = useLocation();
    const navigate = useNavigate();
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    const currentRole = user?.role || 'guest';

    // Theme Config based on Role
    const theme = {
        guest: {
            sidebar: 'bg-slate-900',
            activeItem: 'bg-blue-600 shadow-blue-900/50',
            accent: 'text-blue-400',
            badge: 'bg-blue-50 text-blue-700 border-blue-100'
        },
        employee: {
            sidebar: 'bg-indigo-950',
            activeItem: 'bg-indigo-600 shadow-indigo-900/50',
            accent: 'text-indigo-400',
            badge: 'bg-indigo-50 text-indigo-700 border-indigo-100'
        },
        chef: {
            sidebar: 'bg-orange-950',
            activeItem: 'bg-orange-600 shadow-orange-900/50',
            accent: 'text-orange-400',
            badge: 'bg-orange-50 text-orange-700 border-orange-100'
        }
    }[currentRole];

    const getMenuItems = () => {
        // Show only relevant links for the logged-in role
        if (!user) return [];

        switch (user.role) {
            case 'guest':
                return [
                    { path: '/guest', label: 'Welcome', icon: User, role: 'guest' },
                    { path: '/guest/choose-dish', label: 'Choose Dish', icon: UtensilsCrossed, role: 'guest' }
                ];
            case 'employee':
                return [
                    { path: '/employee', label: 'Order Processing', icon: Coffee, role: 'employee' }
                ];
            case 'chef':
                return [
                    { path: '/chef', label: 'Kitchen Display', icon: ChefHat, role: 'chef' }
                ];
            default:
                return [];
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const handleReset = () => {
        if (confirm('Are you sure you want to reset the simulation? All progress will be lost.')) {
            resetProcess();
            // Redirect to start of flow for that role
            const home = user?.role === 'guest' ? '/guest' : user?.role === 'employee' ? '/employee' : '/chef';
            navigate(home);
            window.location.reload();
        }
    };

    const menuItems = getMenuItems();

    return (
        <div className="min-h-screen bg-slate-50 flex">
            {/* Sidebar */}
            <aside
                className={`${theme.sidebar} text-white transition-all duration-300 ease-in-out ${isSidebarOpen ? 'w-64' : 'w-20'
                    } flex-shrink-0 fixed h-full z-20 shadow-xl`}
            >
                <div className="h-16 flex items-center justify-between px-4 bg-black/20">
                    {isSidebarOpen && (
                        <span className={`font-bold text-lg tracking-wider ${theme.accent}`}>RESTAURANT</span>
                    )}
                    <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="p-2 rounded hover:bg-white/10 transition-colors cursor-pointer"
                    >
                        {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                <div className="flex flex-col h-[calc(100%-4rem)] justify-between">
                    <nav className="mt-6 px-2 space-y-2">
                        {menuItems.map((item) => {
                            const Icon = item.icon;
                            // Active if currently in that role section
                            const isActive = location.pathname === item.path;

                            return (
                                <Link
                                    key={item.path}
                                    to={item.path}
                                    className={`flex items-center px-4 py-3 rounded-lg transition-colors ${isActive
                                        ? `${theme.activeItem} text-white shadow-lg`
                                        : 'text-slate-400 hover:bg-white/10 hover:text-white'
                                        }`}
                                >
                                    <Icon size={20} />
                                    {isSidebarOpen && <span className="ml-3 font-medium">{item.label}</span>}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* User Profile & Actions */}
                    <div className="p-4 bg-black/20">
                        {isSidebarOpen ? (
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${theme.activeItem} text-white font-bold`}>
                                        {user?.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="overflow-hidden">
                                        <p className="text-sm font-semibold text-white truncate capitalize">{user?.name}</p>
                                        <p className={`text-xs ${theme.accent} truncate capitalize`}>{user?.role}</p>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <button
                                        onClick={handleReset}
                                        className="w-full flex items-center justify-center gap-2 py-2 rounded bg-white/5 hover:bg-white/20 hover:text-white transition-colors text-sm text-slate-300 cursor-pointer"
                                    >
                                        <RefreshCw size={16} />
                                        <span>Reset Sim</span>
                                    </button>

                                    <button
                                        onClick={handleLogout}
                                        className="w-full flex items-center justify-center gap-2 py-2 rounded bg-white/10 hover:bg-red-500/20 hover:text-red-400 transition-colors text-sm text-slate-300 cursor-pointer"
                                    >
                                        <LogOut size={16} />
                                        <span>Sign Out</span>
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center gap-4">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${theme.activeItem} text-white font-bold text-xs`}>
                                    {user?.name.charAt(0).toUpperCase()}
                                </div>
                                <button
                                    onClick={handleReset}
                                    className="text-slate-400 hover:text-white transition-colors cursor-pointer"
                                    title="Reset Simulation"
                                >
                                    <RefreshCw size={20} />
                                </button>
                                <button
                                    onClick={handleLogout}
                                    className="text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                                    title="Sign Out"
                                >
                                    <LogOut size={20} />
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main
                className={`flex-1 transition-all duration-300 ease-in-out ${isSidebarOpen ? 'ml-64' : 'ml-20'
                    }`}
            >
                {/* Header */}
                <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10 shadow-sm/50 backdrop-blur-sm bg-white/80">
                    <h2 className="text-xl font-semibold text-slate-800 capitalize">
                        {menuItems.find(i => i.path === location.pathname)?.label || 'Dashboard'}
                    </h2>
                    <div className="flex items-center space-x-4">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium border ${theme.badge} capitalize`}>
                            Role: {currentRole}
                        </div>
                        <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors">
                            <Bell size={20} />
                        </button>
                    </div>
                </header>

                {/* Page Content */}
                <div className="p-8">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};
