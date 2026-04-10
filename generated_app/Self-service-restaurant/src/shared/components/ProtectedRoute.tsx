import { useNavigate, Navigate } from 'react-router-dom';
import { useGlobalState } from '../state/globalState';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
    const { isAuthenticated, user } = useGlobalState();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        // Redirect to their home page based on role if they try to access unauthorized area
        const home = user.role === 'guest' ? '/guest' : `/${user.role}`;
        return <Navigate to={home} replace />;
    }

    return <>{children}</>;
};
