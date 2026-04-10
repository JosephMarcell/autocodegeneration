import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';

export const EatmealPage = () => {
    const navigate = useNavigate();

    return (
        <div className="max-w-md mx-auto">
            <Card title="Enjoy Your Meal">
                <div className="text-center py-8">
                    <span className="text-6xl block mb-4">🍽️</span>
                    <h3 className="text-xl font-bold text-slate-800 mb-2">Bon Appétit!</h3>
                    <p className="mb-8 text-slate-500">
                        Thank you for dining with us.
                    </p>
                    <Button variant="secondary" onClick={() => navigate('/guest')} fullWidth>
                        Leave Restaurant
                    </Button>
                </div>
            </Card>
        </div>
    );
};
