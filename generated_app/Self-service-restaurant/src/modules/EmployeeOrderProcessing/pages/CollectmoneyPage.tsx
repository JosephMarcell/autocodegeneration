import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Loader2, CheckCircle, CreditCard } from 'lucide-react';

export const CollectmoneyPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();

    // Check if payment process is complete
    const isPaid = processState.paymentReceived;

    useEffect(() => {
        // Automatically set paymentRequested to true when landing here
        if (!processState.paymentRequested) {
            updateProcessState({ paymentRequested: true });
        }
    }, [processState.paymentRequested, updateProcessState]);

    const handleNext = () => {
        navigate('/employee/set-up-buzzer');
    };

    return (
        <div className="max-w-xl mx-auto">
            <Card title="Collect Payment">
                <div className="space-y-6">
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-slate-500">Amount Due</span>
                            <span className="text-xl font-bold text-slate-900">
                                {new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(processState.pendingOrder?.price || 0)}
                            </span>
                        </div>
                        <p className="text-sm text-slate-500">
                            Waiting for guest to pay...
                        </p>
                    </div>

                    {!isPaid ? (
                        <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-blue-200 rounded-xl bg-blue-50/50">
                            <Loader2 className="animate-spin text-blue-500 mb-2" size={32} />
                            <p className="font-semibold text-blue-800">Waiting for Payment</p>
                            <p className="text-sm text-blue-600">Please ask the guest to tap their card/phone.</p>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center p-8 border-2 border-green-200 rounded-xl bg-green-50 animate-in fade-in zoom-in duration-300">
                            <CheckCircle className="text-green-500 mb-2" size={48} />
                            <p className="font-bold text-xl text-green-800">Payment Received!</p>
                            <p className="text-sm text-green-600">Transaction approved.</p>
                        </div>
                    )}

                    <Button onClick={handleNext} disabled={!isPaid} fullWidth>
                        Next: Set Up Buzzer
                    </Button>
                </div>
            </Card>
        </div>
    );
};
