import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Bell, Loader } from 'lucide-react';

export const TakebuzzerPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();
    const [hasTakenBuzzer, setHasTakenBuzzer] = useState(false);

    // Waiting for Employee to offer buzzer
    const isBuzzerOffered = processState.buzzerOffered;
    const isBuzzerRinging = processState.buzzerRinging;

    const handleTakeBuzzer = () => {
        setHasTakenBuzzer(true);
        updateProcessState({ buzzerTaken: true });
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Wait for Buzzer">
                {!hasTakenBuzzer ? (
                    <div className="text-center py-6">
                        {!isBuzzerOffered ? (
                            <>
                                <Loader className="animate-spin mx-auto text-blue-500 mb-4" size={32} />
                                <p className="text-slate-600">Waiting for staff to provide buzzer...</p>
                            </>
                        ) : (
                            <div className="animate-in slide-in-from-bottom duration-500">
                                <Bell className="mx-auto text-blue-600 mb-4 animate-bounce" size={48} />
                                <p className="text-slate-800 font-medium mb-6">Staff is handing you the buzzer.</p>
                                <Button onClick={handleTakeBuzzer} fullWidth>
                                    Accept Buzzer
                                </Button>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <div className={`w-32 h-32 mx-auto mb-6 rounded-full flex items-center justify-center transition-all duration-500 ${isBuzzerRinging ? 'bg-red-50 border-4 border-red-500 animate-pulse' : 'bg-slate-50 border-2 border-slate-200'}`}>
                            <Bell className={isBuzzerRinging ? 'text-red-600 animate-ping' : 'text-slate-400'} size={48} />
                        </div>
                        {isBuzzerRinging ? (
                            <>
                                <h3 className="text-2xl font-bold text-red-600 mb-2">Order Ready!</h3>
                                <p className="mb-6 text-slate-800 font-medium">Please proceed to the counter.</p>
                                <Button variant="secondary" onClick={() => navigate('/guest/get-meal')} fullWidth>
                                    Go to Counter
                                </Button>
                            </>
                        ) : (
                            <p className="text-slate-500">Waiting for your meal... Buzzer is silent.</p>
                        )}
                    </div>
                )}
            </Card>
        </div>
    );
};
