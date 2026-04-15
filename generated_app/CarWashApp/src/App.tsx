import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './LoginPage';
import Layout from './Layout';
import DrivesAwayPage from './DrivesAwayPage';
import PullsCarUpToCarWashPage from './PullsCarUpToCarWashPage';
import ChoosesWashPage from './ChoosesWashPage';
import Pay8Page from './Pay8Page';
import Pays15Page from './Pays15Page';
import DoublePolishPage from './DoublePolishPage';
import DryPage from './DryPage';
import WheelLusterWheelCleanPage from './WheelLusterWheelCleanPage';
import SoftClothWashPage from './SoftClothWashPage';
import WheelCleanPage from './WheelCleanPage';
import ClearCoatProtectionPage from './ClearCoatProtectionPage';

const allRoutes = [
  { route: '/customer/drives-away', role: 'customer', component: DrivesAwayPage, allowedRoles: ['customer'] },
  { route: '/customer/pulls-car-up-to-car-wash', role: 'customer', component: PullsCarUpToCarWashPage, allowedRoles: ['customer'] },
  { route: '/customer/chooses-wash', role: 'customer', component: ChoosesWashPage, allowedRoles: ['customer'] },
  { route: '/customer/pay-8', role: 'customer', component: Pay8Page, allowedRoles: ['customer'] },
  { route: '/customer/pays-15', role: 'customer', component: Pays15Page, allowedRoles: ['customer'] },
  { route: '/car-wash-machine/double-polish', role: 'carwashmachine', component: DoublePolishPage, allowedRoles: ['carwashmachine'] },
  { route: '/car-wash-machine/dry', role: 'carwashmachine', component: DryPage, allowedRoles: ['carwashmachine'] },
  { route: '/car-wash-machine/wheel-luster-wheel-clean', role: 'carwashmachine', component: WheelLusterWheelCleanPage, allowedRoles: ['carwashmachine'] },
  { route: '/car-wash-machine/soft-cloth-wash', role: 'carwashmachine', component: SoftClothWashPage, allowedRoles: ['carwashmachine'] },
  { route: '/car-wash-machine/wheel-clean', role: 'carwashmachine', component: WheelCleanPage, allowedRoles: ['carwashmachine'] },
  { route: '/car-wash-machine/clear-coat-protection', role: 'carwashmachine', component: ClearCoatProtectionPage, allowedRoles: ['carwashmachine'] }
];

const defaultRoutesPerRole = {
  customer: '/customer/pulls-car-up-to-car-wash',
  carwashmachine: '/car-wash-machine/soft-cloth-wash'
};

const ProtectedRoute = ({ allowedRoles, defaultRoutesPerRole, children }: { allowedRoles: string[], defaultRoutesPerRole: Record<string, string>, children: React.ReactNode }) => {
  const userRole = 'customer'; // Replace with actual role retrieval logic
  if (allowedRoles.includes(userRole)) {
    return <>{children}</>;
  } else {
    return <Navigate to={defaultRoutesPerRole[userRole]} replace />;
  }
};

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout routes={allRoutes} />}>
        {allRoutes.map((route) => (
          <Route key={route.route} path={route.route} element={
            <ProtectedRoute allowedRoles={route.allowedRoles} defaultRoutesPerRole={defaultRoutesPerRole}>
              {React.createElement(route.component)}
            </ProtectedRoute>
          } />
        ))}
      </Route>
      <Route path="*" element={<div>404 — Page not found</div>} />
    </Routes>
  </BrowserRouter>
);

export default App;