// AUTO-GENERATED — VALIDATION FAILED — REVIEW NEEDED
import create from 'zustand';

type Role = 'customer' | 'carwashmachine';

type ProcessState = {
  [key in keyof typeof stateSchema]?: boolean | string;
};

const useGlobalState = create<Store>((set, get) => ({
  isAuthenticated: !!sessionStorage.getItem('auth'),
  user: JSON.parse(sessionStorage.getItem('auth') || 'null') as { name: string; role: Role } | null,
  login(name: string, role: Role): void {
    sessionStorage.setItem('auth', JSON.stringify({ name, role }));
    set({ isAuthenticated: true, user: { name, role } });
  },
  logout(): void {
    sessionStorage.removeItem('auth');
    localStorage.removeItem('processState');
    set({ isAuthenticated: false, user: null, processState: {} });
  },
  processState: JSON.parse(localStorage.getItem('processState') || '{}') as ProcessState,
  updateProcessState(updates: Partial<ProcessState>): void {
    const newProcessState = { ...get().processState, ...updates };
    localStorage.setItem('processState', JSON.stringify(newProcessState));
    set({ processState: newProcessState });
  },
  resetProcess(): void {
    localStorage.removeItem('processState');
    set({ processState: {} });
  }
}));

const handler = (event: StorageEvent) => {
  if (event.key === 'processState') {
    const parsed = JSON.parse(event.newValue || '{}');
    useGlobalState.setState({ processState: parsed });
  }
};

window.addEventListener('storage', handler);

export type Store = ReturnType<typeof useGlobalState>;
export { useGlobalState };