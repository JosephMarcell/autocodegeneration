import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Package } from 'lucide-react';

export const HandovermealPage = () => {
    const navigate = useNavigate();
    const { updateProcessState } = useGlobalState();

    const handleHandover = () => {
        updateProcessState({ mealAvailableForGuest: true });
        navigate('/employee/call-guest');
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Hand Over Meal">
                <div className="text-center py-8">
                    <Package size={64} className="mx-auto text-orange-500 mb-4" />
                    <p className="mb-6 text-slate-500">
                        Hand over the packaged meal to the guest at the counter.
                    </p>
                    <Button onClick={handleHandover} fullWidth>
                        Confirm Handover
                    </Button>
                </div>
            </Card>
        </div>
    );
};
