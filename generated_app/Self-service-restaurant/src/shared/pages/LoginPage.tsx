import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../state/globalState';
import type { Role } from '../state/globalState';
import { User, Coffee, ChefHat, ArrowRight } from 'lucide-react';

export default function LoginPage() {
    const navigate = useNavigate();
    const { login } = useGlobalState();
    const [name, setName] = useState('');
    const [selectedRole, setSelectedRole] = useState<Role | null>(null);

    const roles: { id: Role; label: string; icon: any; color: string; desc: string }[] = [
        {
            id: 'guest',
            label: 'Guest',
            icon: User,
            color: 'bg-blue-600',
            desc: 'Order food and eat'
        },
        {
            id: 'employee',
            label: 'Employee',
            icon: Coffee,
            color: 'bg-indigo-600',
            desc: 'Process orders and payments'
        },
        {
            id: 'chef',
            label: 'Chef',
            icon: ChefHat,
            color: 'bg-orange-600',
            desc: 'Prepare meals in kitchen'
        },
    ];

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (!name || !selectedRole) return;

        login(name, selectedRole);

        // Redirect based on role
        switch (selectedRole) {
            case 'guest':
                navigate('/guest');
                break;
            case 'employee':
                navigate('/employee');
                break;
            case 'chef':
                navigate('/chef');
                break;
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
            <div className="max-w-4xl w-full bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col md:flex-row">

                {/* Left Side - Hero */}
                <div className="md:w-1/2 bg-slate-900 p-12 text-white flex flex-col justify-between relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-blue-600/20 to-purple-600/20 z-0"></div>
                    <div className="relative z-10">
                        <h1 className="text-4xl font-bold mb-4">Fast Food Process</h1>
                        <p className="text-slate-400 text-lg">
                            An advanced simulation of a restaurant ordering and fulfillment process.
                        </p>
                    </div>
                </div>

                {/* Right Side - Login Form */}
                <div className="md:w-1/2 p-12 flex flex-col justify-center">
                    <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome Back</h2>
                    <p className="text-slate-500 mb-8">Please enter your details to sign in.</p>

                    <form onSubmit={handleLogin} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Your Name
                            </label>
                            <input
                                type="text"
                                required
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. John Doe"
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-4">
                                Select Role
                            </label>
                            <div className="grid grid-cols-1 gap-3">
                                {roles.map((role) => {
                                    const Icon = role.icon;
                                    const isSelected = selectedRole === role.id;

                                    return (
                                        <button
                                            key={role.id}
                                            type="button"
                                            onClick={() => setSelectedRole(role.id)}
                                            className={`flex items-center p-4 rounded-xl border transition-all text-left group ${isSelected
                                                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100'
                                                : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'
                                                }`}
                                        >
                                            <div className={`p-3 rounded-full text-white mr-4 transition-colors ${role.color} ${!isSelected && 'opacity-80 group-hover:opacity-100'}`}>
                                                <Icon size={20} />
                                            </div>
                                            <div>
                                                <div className={`font-semibold ${isSelected ? 'text-blue-900' : 'text-slate-800'}`}>
                                                    {role.label}
                                                </div>
                                                <div className="text-xs text-slate-500">{role.desc}</div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={!name || !selectedRole}
                            className="w-full bg-slate-900 text-white py-4 rounded-xl font-semibold hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 mt-8"
                        >
                            Sign In
                            <ArrowRight size={20} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
