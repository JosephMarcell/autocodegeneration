import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';

export const SetupbuzzerPage = () => {
    const navigate = useNavigate();
    const { updateProcessState } = useGlobalState();
    const [buzzerId, setBuzzerId] = useState('5');

    const handleSetup = (e: React.FormEvent) => {
        e.preventDefault();
        updateProcessState({ buzzerSetup: true });
        navigate('/employee/hand-over-buzzer');
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Set Up Buzzer">
                <form onSubmit={handleSetup}>
                    <p className="mb-6 text-slate-500">
                        Assign a buzzer to the order.
                    </p>
                    <Input
                        label="Buzzer ID"
                        value={buzzerId}
                        onChange={(e) => setBuzzerId(e.target.value)}
                    />
                    <Button type="submit" fullWidth className="mt-4">
                        Activate Buzzer
                    </Button>
                </form>
            </Card>
        </div>
    );
};
