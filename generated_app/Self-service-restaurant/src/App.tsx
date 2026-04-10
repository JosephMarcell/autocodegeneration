import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './shared/components/Layout';
import LoginPage from './shared/pages/LoginPage';
import { ProtectedRoute } from './shared/components/ProtectedRoute';

// Guest
import { EnterrestaurantPage } from './modules/GuestFoodConsumption/pages/EnterrestaurantPage';
import { ChoosedishPage } from './modules/GuestFoodConsumption/pages/ChoosedishPage';
import { PlaceorderPage } from './modules/GuestFoodConsumption/pages/PlaceorderPage';
import { PaymoneyPage } from './modules/GuestFoodConsumption/pages/PaymoneyPage';
import { TakebuzzerPage } from './modules/GuestFoodConsumption/pages/TakebuzzerPage';
import { GetmealPage } from './modules/GuestFoodConsumption/pages/GetmealPage';
import { EatmealPage } from './modules/GuestFoodConsumption/pages/EatmealPage';

// Employee
import { EnterorderPage } from './modules/EmployeeOrderProcessing/pages/EnterorderPage';
import { CollectmoneyPage } from './modules/EmployeeOrderProcessing/pages/CollectmoneyPage';
import { SetupbuzzerPage } from './modules/EmployeeOrderProcessing/pages/SetupbuzzerPage';
import { HandoverbuzzerPage } from './modules/EmployeeOrderProcessing/pages/HandoverbuzzerPage';
import { InformchefPage } from './modules/EmployeeOrderProcessing/pages/InformchefPage';
import { SetoffbuzzerPage } from './modules/EmployeeOrderProcessing/pages/SetoffbuzzerPage';
import { HandovermealPage } from './modules/EmployeeOrderProcessing/pages/HandovermealPage';
import { CallguestPage } from './modules/EmployeeOrderProcessing/pages/CallguestPage';

// Chef
import { PreparemealPage } from './modules/ChefMealPreparation/pages/PreparemealPage';
import { PlacemealinhatchPage } from './modules/ChefMealPreparation/pages/PlacemealinhatchPage';
import { InformemployeePage } from './modules/ChefMealPreparation/pages/InformemployeePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<Layout />}>
          {/* Guest Routes - Accessible by Guest Role */}
          {/* Guest Routes - Accessible by Guest Role */}
          <Route path="/guest" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <EnterrestaurantPage />
            </ProtectedRoute>
          } />
          <Route path="/guest/choose-dish" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <ChoosedishPage />
            </ProtectedRoute>
          } />
          <Route path="/guest/place-order" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <PlaceorderPage />
            </ProtectedRoute>
          } />
          <Route path="/guest/pay-money" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <PaymoneyPage />
            </ProtectedRoute>
          } />
          <Route path="/guest/take-buzzer" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <TakebuzzerPage />
            </ProtectedRoute>
          } />
          <Route path="/guest/get-meal" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <GetmealPage />
            </ProtectedRoute>
          } />
          <Route path="/guest/eat-meal" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <EatmealPage />
            </ProtectedRoute>
          } />

          {/* Employee Routes */}
          <Route path="/employee" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <EnterorderPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/collect-money" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <CollectmoneyPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/set-up-buzzer" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <SetupbuzzerPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/hand-over-buzzer" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <HandoverbuzzerPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/inform-chef" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <InformchefPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/set-off-buzzer" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <SetoffbuzzerPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/hand-over-meal" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <HandovermealPage />
            </ProtectedRoute>
          } />
          <Route path="/employee/call-guest" element={
            <ProtectedRoute allowedRoles={['employee']}>
              <CallguestPage />
            </ProtectedRoute>
          } />

          {/* Chef Routes */}
          <Route path="/chef" element={
            <ProtectedRoute allowedRoles={['chef']}>
              <PreparemealPage />
            </ProtectedRoute>
          } />
          <Route path="/chef/place-meal-in-hatch" element={
            <ProtectedRoute allowedRoles={['chef']}>
              <PlacemealinhatchPage />
            </ProtectedRoute>
          } />
          <Route path="/chef/inform-employee" element={
            <ProtectedRoute allowedRoles={['chef']}>
              <InformemployeePage />
            </ProtectedRoute>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
