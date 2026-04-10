import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';

export const CallguestPage = () => {
    const navigate = useNavigate();

    return (
        <div className="max-w-xl mx-auto">
            <Card title="Order Complete">
                <div className="flex flex-col items-center justify-center py-8">
                    <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4">
                        <span className="text-2xl">✓</span>
                    </div>
                    <h3 className="text-xl font-bold text-slate-800 mb-2">Success!</h3>
                    <p className="mb-8 text-slate-500 text-center">
                        Order #42 has been completed and handed over.
                    </p>
                    <Button onClick={() => navigate('/employee')} fullWidth>
                        Start New Order
                    </Button>
                </div>
            </Card>
        </div>
    );
};
