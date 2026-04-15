import React from 'react';
import { Navigate } from 'react-router-dom';
import useGlobalState from '../state/globalState';

interface ProtectedRouteProps {
  allowedRoles: string[];
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { isAuthenticated, user, defaultRoutesPerRole } = useGlobalState();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={defaultRoutesPerRole[user.role] ?? '/login'} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;