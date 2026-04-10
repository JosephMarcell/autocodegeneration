import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Bell } from 'lucide-react';

export const HandoverbuzzerPage = () => {
    const navigate = useNavigate();
    const { updateProcessState } = useGlobalState();

    const handleHandover = () => {
        updateProcessState({ buzzerOffered: true });
        navigate('/employee/inform-chef');
    };

    return (
        <div className="max-w-xl mx-auto">
            <Card title="Hand Over Buzzer">
                <div className="text-center py-8">
                    <div className="w-24 h-24 mx-auto mb-6 bg-indigo-50 rounded-full flex items-center justify-center border-2 border-indigo-100">
                        <Bell className="text-indigo-600" size={40} />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-2">Buzzer Ready</h3>
                    <p className="border-b border-transparent mb-6 text-slate-500">
                        Please hand over the buzzer #5 to the guest.
                    </p>
                    <Button onClick={handleHandover} fullWidth>
                        Confirm Handover
                    </Button>
                </div>
            </Card>
        </div>
    );
};
