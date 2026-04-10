import React from 'react';
import type { ButtonHTMLAttributes, InputHTMLAttributes } from 'react';

// Card Component
export const Card = ({ children, className = '', title }: { children: React.ReactNode; className?: string; title?: string }) => (
    <div className={`bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden ${className}`}>
        {title && (
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
            </div>
        )}
        <div className="p-6">
            {children}
        </div>
    </div>
);

// Button Component
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger';
    fullWidth?: boolean;
}

export const Button = ({ children, variant = 'primary', fullWidth, className = '', disabled, ...props }: ButtonProps) => {
    const baseStyle = "inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "bg-blue-600 hover:bg-blue-700 text-white shadow-sm shadow-blue-500/30 focus:ring-blue-500",
        secondary: "bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 shadow-sm focus:ring-slate-400",
        danger: "bg-red-500 hover:bg-red-600 text-white shadow-sm shadow-red-500/30 focus:ring-red-500"
    };

    const widthClass = fullWidth ? 'w-full' : '';

    return (
        <button
            {...props}
            disabled={disabled}
            className={`${baseStyle} ${variants[variant]} ${widthClass} ${className}`}
        >
            {children}
        </button>
    );
};

// Input Component
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
}

export const Input = ({ label, className = '', ...props }: InputProps) => (
    <div className="mb-4">
        {label && (
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
                {label}
            </label>
        )}
        <input
            {...props}
            className={`w-full px-4 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all ${className}`}
        />
    </div>
);
