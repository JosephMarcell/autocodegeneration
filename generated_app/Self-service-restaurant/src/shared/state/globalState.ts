import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type Role = 'guest' | 'employee' | 'chef';

type ProcessState = {
    dish?: {
        name: string;
        price: number;
        description: string;
    };
    pendingOrder?: {
        dishName: string;
        price: number;
        instructions: string;
        tableNumber?: string;
    };
    // Flow 1: Payment
    paymentRequested?: boolean;
    paymentReceived?: boolean;

    // Flow 2: Buzzer Handover
    buzzerSetup?: boolean;
    buzzerOffered?: boolean;
    buzzerTaken?: boolean;

    // Flow 3: Chef Order
    chefOrder?: { dishName: string; notes: string };

    // Flow 4: Chef -> Employee
    mealInHatch?: boolean;
    chefInformedEmployee?: boolean;

    // Flow 5: Buzzer Ring
    buzzerRinging?: boolean;

    // Flow 6: Meal Handover
    mealAvailableForGuest?: boolean;
};

interface User {
    name: string;
    role: Role;
}

interface GlobalState {
    // Auth State (Session Storage - Tab Specific)
    isAuthenticated: boolean;
    user: User | null;
    login: (name: string, role: Role) => void;
    logout: () => void;

    // Process State (Local Storage - Shared)
    processState: ProcessState;
    updateProcessState: (updates: Partial<ProcessState>) => void;
    resetProcess: () => void;
}

export const useGlobalState = create<GlobalState>()((set, get) => ({
    // --- Auth State (Initialized from Session) ---
    isAuthenticated: sessionStorage.getItem('auth_isAuthenticated') === 'true',
    user: sessionStorage.getItem('auth_user') ? JSON.parse(sessionStorage.getItem('auth_user')!) : null,

    login: (name, role) => {
        const user = { name, role };
        sessionStorage.setItem('auth_isAuthenticated', 'true');
        sessionStorage.setItem('auth_user', JSON.stringify(user));
        set({ isAuthenticated: true, user });
    },

    logout: () => {
        sessionStorage.removeItem('auth_isAuthenticated');
        sessionStorage.removeItem('auth_user');
        set({ isAuthenticated: false, user: null });
    },

    // --- Process State (Initialized from LocalStorage) ---
    processState: localStorage.getItem('process_data') ? JSON.parse(localStorage.getItem('process_data')!) : {},

    updateProcessState: (updates) => {
        const currentHelper = get().processState;
        const newState = { ...currentHelper, ...updates };

        localStorage.setItem('process_data', JSON.stringify(newState));
        // Force update local state
        set({ processState: newState });

        // Trigger event for other tabs
        window.dispatchEvent(new StorageEvent('storage', {
            key: 'process_data',
            newValue: JSON.stringify(newState)
        }));
    },

    resetProcess: () => {
        localStorage.removeItem('process_data');
        set({ processState: {} });
        window.dispatchEvent(new StorageEvent('storage', {
            key: 'process_data',
            newValue: null
        }));
    }
}));

// Cross-tab Synchronization Listener
if (typeof window !== 'undefined') {
    window.addEventListener('storage', (e) => {
        // Only sync Process Data, NOT Auth Data
        if (e.key === 'process_data') {
            const newValue = e.newValue ? JSON.parse(e.newValue) : {};
            useGlobalState.setState({ processState: newValue });
        }
    });
}
