import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';

export const GetmealPage = () => {
    const navigate = useNavigate();

    return (
        <div className="max-w-md mx-auto">
            <Card title="Meal Ready!">
                <p className="mb-6 text-slate-500">
                    Your meal is ready at the counter. Please return the buzzer and collect your food.
                </p>
                <div className="bg-green-50 p-6 rounded-xl border border-green-100 text-center mb-6">
                    <span className="text-3xl block mb-2">🎁</span>
                    <span className="text-green-800 font-medium">Order #42</span>
                </div>
                <Button onClick={() => navigate('/guest/eat-meal')} fullWidth>
                    Collect Meal
                </Button>
            </Card>
        </div>
    );
};
