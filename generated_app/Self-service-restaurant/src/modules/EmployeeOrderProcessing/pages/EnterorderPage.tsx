import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';
import { Bell } from 'lucide-react';

export const EnterorderPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();
    const [tableNumber, setTableNumber] = useState('');

    // Check if there is a pending order from a guest
    const pendingOrder = processState.pendingOrder;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        // Confirm the order and proceed
        if (pendingOrder) {
            updateProcessState({
                pendingOrder: {
                    ...pendingOrder,
                    tableNumber: tableNumber
                }
            });
        }

        navigate('/employee/collect-money');
    };

    const formatPrice = (p: number) => {
        return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(p);
    };

    return (
        <div className="max-w-xl mx-auto">
            <Card title="POS System: Enter Order">
                <form onSubmit={handleSubmit} className="space-y-4">

                    {pendingOrder ? (
                        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 mb-6 animate-pulse">
                            <div className="flex items-start gap-3">
                                <Bell className="text-blue-600 mt-1" size={20} />
                                <div>
                                    <h4 className="font-semibold text-blue-900">New Order Received!</h4>
                                    <p className="text-sm text-blue-800 mt-1">
                                        Guest placed an order via app.
                                    </p>
                                    <div className="mt-3 bg-white p-3 rounded border border-blue-100 text-sm">
                                        <div className="flex justify-between font-medium">
                                            <span>{pendingOrder.dishName}</span>
                                            <span>{formatPrice(pendingOrder.price)}</span>
                                        </div>
                                        {pendingOrder.instructions && (
                                            <p className="text-slate-500 mt-1 italic">Note: "{pendingOrder.instructions}"</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="bg-slate-50 p-4 rounded-md border border-slate-200 mb-4 text-sm text-slate-600">
                            <p>Waiting for guest orders...</p>
                        </div>
                    )}

                    <div className="opacity-50 pointer-events-none">
                        <Input
                            label="Order Details (Auto-filled)"
                            value={pendingOrder ? `${pendingOrder.dishName} - ${formatPrice(pendingOrder.price)}` : ''}
                            readOnly
                        />
                    </div>

                    <Input
                        label="Table Number"
                        placeholder="e.g. 5"
                        value={tableNumber}
                        onChange={(e) => setTableNumber(e.target.value)}
                        required
                    />

                    <div className="pt-4">
                        <Button type="submit" fullWidth disabled={!pendingOrder}>
                            {pendingOrder ? 'Confirm & Process Order' : 'Waiting for Order...'}
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
};
