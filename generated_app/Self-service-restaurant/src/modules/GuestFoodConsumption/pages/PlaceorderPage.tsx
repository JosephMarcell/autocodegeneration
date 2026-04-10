import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../../../shared/components/UI';
import { useGlobalState } from '../../../shared/state/globalState';

export const PlaceorderPage = () => {
    const navigate = useNavigate();
    const { processState, updateProcessState } = useGlobalState();
    const [instructions, setInstructions] = useState('');

    const dish = processState.dish || { name: 'Unknown', price: 0 };
    const price = dish.price;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        // Simulate message flow: Send order to Employee's POS system
        updateProcessState({
            pendingOrder: {
                dishName: dish.name,
                price: dish.price,
                instructions: instructions
            }
        });

        navigate('/guest/pay-money');
    };

    const formatPrice = (p: number) => {
        return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(p);
    };

    return (
        <div className="max-w-md mx-auto">
            <Card title="Place Order">
                <form onSubmit={handleSubmit}>
                    <p className="mb-6 text-slate-500">
                        Review your order and proceed to payment.
                    </p>
                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 mb-6 space-y-2">
                        <div className="flex justify-between text-sm text-slate-600">
                            <span>{dish.name}</span>
                            <span>{formatPrice(price)}</span>
                        </div>
                        <div className="pt-2 mt-2 border-t border-slate-200 flex justify-between font-semibold text-slate-800">
                            <span>Total</span>
                            <span>{formatPrice(price)}</span>
                        </div>
                    </div>
                    <Input
                        label="Special Instructions"
                        placeholder="No onions, etc."
                        value={instructions}
                        onChange={(e) => setInstructions(e.target.value)}
                    />
                    <Button type="submit" fullWidth className="mt-2">
                        Place Order & Inform Staff
                    </Button>
                </form>
            </Card>
        </div>
    );
};
