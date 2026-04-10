import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';

export const InformemployeePage = () => {
    const navigate = useNavigate();
    const { updateProcessState } = useGlobalState();

    const handleInform = () => {
        // Send message flow: Meal Ready
        updateProcessState({ chefInformedEmployee: true });

        // Reset local Chef view for demo purposes (or redirect to home)
        // In a real app, Chef might go back to queue.
        alert("Employee has been informed!");
        navigate('/chef');
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Inform Employee">
                <p className="mb-6 text-slate-500">
                    Notify the service staff that order #42 is ready in the service hatch.
                </p>
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 mb-6 flex items-center gap-3">
                    <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-blue-800 font-medium">System Connected</span>
                </div>
                <Button onClick={handleInform} fullWidth>
                    Send "Meal Ready" Signal
                </Button>
            </Card>
        </div>
    );
};
