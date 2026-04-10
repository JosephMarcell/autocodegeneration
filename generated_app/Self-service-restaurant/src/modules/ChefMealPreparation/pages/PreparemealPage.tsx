import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Utensils, Clock, CheckCircle } from 'lucide-react';

export const PreparemealPage = () => {
    const navigate = useNavigate();
    const { processState } = useGlobalState();
    const [progress, setProgress] = useState(0);
    const [isCooking, setIsCooking] = useState(false);

    const order = processState.chefOrder;

    useEffect(() => {
        if (isCooking) {
            const interval = setInterval(() => {
                setProgress((prev) => {
                    if (prev >= 100) {
                        clearInterval(interval);
                        return 100;
                    }
                    return prev + 10;
                });
            }, 500); // 5 seconds to cook
            return () => clearInterval(interval);
        }
    }, [isCooking]);

    const handleStartCooking = () => setIsCooking(true);

    const handleFinish = () => {
        navigate('/chef/place-meal-in-hatch');
    };

    if (!order) {
        return (
            <div className="max-w-xl mx-auto">
                <Card title="Kitchen Display System">
                    <div className="text-center py-12 text-slate-400">
                        <Utensils size={48} className="mx-auto mb-4 opacity-50" />
                        <p>No active orders.</p>
                    </div>
                </Card>
            </div>
        )
    }

    return (
        <div className="max-w-xl mx-auto">
            <Card title="Prepare Meal">
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm mb-6">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h2 className="text-2xl font-bold text-slate-900">{order.dishName}</h2>
                            {order.notes && (
                                <p className="text-red-500 font-medium mt-1">Note: {order.notes}</p>
                            )}
                        </div>
                        <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
                            Order #42
                        </span>
                    </div>

                    {isCooking && (
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm font-medium text-slate-600">
                                <span>Preparation Status</span>
                                <span>{progress}%</span>
                            </div>
                            <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-orange-500 transition-all duration-300 ease-out"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                    )}
                </div>

                {!isCooking ? (
                    <Button onClick={handleStartCooking} fullWidth>
                        Start Cooking
                    </Button>
                ) : (
                    <Button onClick={handleFinish} disabled={progress < 100} fullWidth variant={progress < 100 ? 'secondary' : 'primary'}>
                        {progress < 100 ? (
                            <><Clock size={16} className="mr-2 animate-spin" /> Cooking...</>
                        ) : (
                            <><CheckCircle size={16} className="mr-2" /> Finish Preparation</>
                        )}
                    </Button>
                )}
            </Card>
        </div>
    );
};
