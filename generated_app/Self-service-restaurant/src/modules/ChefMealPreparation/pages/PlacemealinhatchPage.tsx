import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { ArrowUpCircle } from 'lucide-react';

export const PlacemealinhatchPage = () => {
    const navigate = useNavigate();
    const { updateProcessState } = useGlobalState();

    const handlePlace = () => {
        updateProcessState({ mealInHatch: true });
        navigate('/chef/inform-employee');
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Service Hatch">
                <div className="text-center py-8">
                    <ArrowUpCircle size={64} className="mx-auto text-slate-300 mb-4" />
                    <p className="mb-6 text-slate-500">
                        Place the finished meal into the service hatch.
                    </p>
                    <Button onClick={handlePlace} fullWidth>
                        Place Meal
                    </Button>
                </div>
            </Card>
        </div>
    );
};
