import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useGlobalState } from '../state/globalState';

const Layout: React.FC<{ routes: Array<{ route: string; component: string; allowedRoles: string[] }> }> = ({ routes }) => {
  const { user, logout } = useGlobalState();
  const navigate = useNavigate();

  const filteredRoutes = routes.filter(route => route.allowedRoles.includes(user.role));

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleResetProcess = () => {
    // Implement reset process logic here
    console.log('Reset process called');
  };

  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-gray-800 text-white p-4">
        <ul>
          {filteredRoutes.map(route => (
            <li key={route.route}>
              <a href={route.route} className="block px-4 py-2 hover:bg-gray-700">
                {route.component.replace('Page', '')}
              </a>
            </li>
          ))}
        </ul>
      </aside>
      <div className="flex flex-col flex-1">
        <header className="bg-blue-900 text-white p-4">
          <h1>Project Name</h1>
          <p>{user.name} ({user.role})</p>
        </header>
        <main className="flex-1 p-4">
          <button onClick={handleLogout} className="px-4 py-2 bg-red-500 text-white rounded">Logout</button>
          <button onClick={handleResetProcess} className="px-4 py-2 bg-yellow-500 text-white rounded">Reset Process</button>
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;