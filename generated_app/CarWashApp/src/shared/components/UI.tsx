import React from 'react';

export const Card: React.FC<{ title?: string; children: React.ReactNode; className?: string }> = ({ title, children, className }) => (
  <div className={`white rounded-xl shadow-md p-6 ${className}`}>
    {title && <h2>{title}</h2>}
    {children}
  </div>
);

export const Button: React.FC<{ children: React.ReactNode; onClick?: () => void; type?: 'button' | 'submit' | 'reset'; disabled?: boolean; fullWidth?: boolean; variant?: 'primary' | 'secondary' }> = ({ children, onClick, type = 'button', disabled = false, fullWidth = false, variant = 'primary' }) => (
  <button
    className={`${
      variant === 'primary'
        ? 'bg-blue-500 text-white hover:bg-blue-700'
        : 'border border-gray-300 text-gray-700 hover:bg-gray-100'
    } ${fullWidth ? 'w-full' : ''} px-4 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed`}
    onClick={onClick}
    type={type}
    disabled={disabled}
  >
    {children}
  </button>
);

export const Input: React.FC<{ label: string; value: string; onChange: React.ChangeEventHandler<HTMLInputElement>; placeholder?: string; type?: string }> = ({ label, value, onChange, placeholder, type = 'text' }) => (
  <div className="mb-4">
    <label htmlFor={label} className="block text-gray-700 font-bold mb-2">
      {label}
    </label>
    <input
      id={label}
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
    />
  </div>
);