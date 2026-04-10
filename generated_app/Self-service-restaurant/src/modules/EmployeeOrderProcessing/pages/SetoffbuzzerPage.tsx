import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Bell, AlertCircle } from 'lucide-react';

export const SetoffbuzzerPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();

    // Check if Chef has finished cooking
    const isMealReady = processState.chefInformedEmployee;

    const handleSetOff = () => {
        updateProcessState({ buzzerRinging: true });
        navigate('/employee/hand-over-meal');
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Set Off Buzzer">
                {!isMealReady ? (
                    <div className="text-center py-8">
                        <div className="bg-yellow-50 text-yellow-800 p-4 rounded-lg mb-4 flex items-center justify-center gap-2">
                            <AlertCircle size={20} />
                            <span className="font-medium">Meal Not Ready</span>
                        </div>
                        <p className="text-slate-500 mb-6">Waiting for Chef to finish preparation...</p>
                        <div className="opacity-50">
                            <Button disabled fullWidth>
                                Trigger Buzzer #5
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <div className="bg-green-50 text-green-800 p-4 rounded-lg mb-6 flex items-center justify-center gap-2 animate-pulse">
                            <AlertCircle size={20} />
                            <span className="font-medium">Meal Ready in Hatch!</span>
                        </div>
                        <p className="mb-6 text-slate-500">
                            The meal is ready. Alert the guest now.
                        </p>
                        <Button onClick={handleSetOff} fullWidth className="bg-red-500 hover:bg-red-600 border-red-600">
                            <Bell className="mr-2" size={18} />
                            Trigger Buzzer #5
                        </Button>
                    </div>
                )}
            </Card>
        </div>
    );
};
