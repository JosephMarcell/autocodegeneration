import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';

export const EnterrestaurantPage = () => {
    const navigate = useNavigate();

    return (
        <div className="max-w-md mx-auto">
            <Card title="Welcome to the Restaurant">
                <p className="mb-6 text-slate-500">
                    Please come in and find a table.
                </p>
                <Button onClick={() => navigate('/guest/choose-dish')} fullWidth>
                    Enter & Choose Dish
                </Button>
            </Card>
        </div>
    );
};
