import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { CreditCard, Lock } from 'lucide-react';

export const PaymoneyPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();
    const [processing, setProcessing] = useState(false);

    // Only allow payment if requested by employee
    const canPay = processState.paymentRequested;

    const handlePay = () => {
        setProcessing(true);
        setTimeout(() => {
            updateProcessState({ paymentReceived: true });
            navigate('/guest/take-buzzer');
        }, 1500);
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Secure Payment">
                <div className="mb-6">
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-slate-600 font-medium">Total Amount</span>
                        <span className="text-2xl font-bold text-slate-900">
                            {new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(processState.pendingOrder?.price || 0)}
                        </span>
                    </div>
                </div>

                {canPay ? (
                    <>
                        <Input label="Card Number" placeholder="0000 0000 0000 0000" />
                        <div className="grid grid-cols-2 gap-4">
                            <Input label="Expiry" placeholder="MM/YY" />
                            <Input label="CVC" placeholder="123" />
                        </div>
                        <Button onClick={handlePay} disabled={processing} fullWidth className="mt-4 flex items-center justify-center gap-2">
                            {processing ? 'Processing...' : <><CreditCard size={18} /> Pay Now</>}
                        </Button>
                    </>
                ) : (
                    <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200">
                        <Lock className="mx-auto text-slate-400 mb-2" size={32} />
                        <h3 className="font-semibold text-slate-700">Payment Locked</h3>
                        <p className="text-sm text-slate-500 mt-1">Please wait for the cashier to initiate the payment.</p>
                    </div>
                )}
            </Card>
        </div>
    );
};
