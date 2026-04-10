import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';

export const InformchefPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();
    const [notes, setNotes] = useState(processState.pendingOrder?.instructions || '');

    const handleInform = (e: React.FormEvent) => {
        e.preventDefault();

        // Send message to Chef
        updateProcessState({
            chefOrder: {
                dishName: processState.pendingOrder?.dishName || 'Standard Meal',
                notes: notes
            }
        });

        navigate('/employee/set-off-buzzer');
    };

    return (
        <div className="max-w-xl mx-auto">
            <Card title="Inform Chef">
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100 mb-6">
                    <h4 className="font-semibold text-yellow-800 mb-2">Order Ticket #42</h4>
                    <p className="text-yellow-900 font-bold text-lg">{processState.pendingOrder?.dishName || 'Unknown Dish'}</p>
                </div>

                <form onSubmit={handleInform}>
                    <p className="mb-4 text-slate-500 text-sm">
                        Verify order details before sending to kitchen display system.
                    </p>
                    <Input
                        label="Kitchen Notes"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                    />
                    <Button type="submit" fullWidth className="mt-4">
                        Send Order to Kitchen
                    </Button>
                </form>
            </Card>
        </div>
    );
};
