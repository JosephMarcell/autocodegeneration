import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { ShoppingCart, CheckCircle, Utensils, Coffee, Pizza, Salad } from 'lucide-react';

const DISHES = [
    { id: 1, name: 'Deluxe Burger', price: 12000, img: Utensils, color: 'text-orange-500 bg-orange-50' },
    { id: 2, name: 'Pepperoni Pizza', price: 15000, img: Pizza, color: 'text-red-500 bg-red-50' },
    { id: 3, name: 'Caesar Salad', price: 8000, img: Salad, color: 'text-green-500 bg-green-50' },
    { id: 4, name: 'Espresso', price: 5000, img: Coffee, color: 'text-amber-500 bg-amber-50' },
];

export const ChoosedishPage = () => {
    const navigate = useNavigate();
    const { updateProcessState } = useGlobalState();
    const [selectedDish, setSelectedDish] = useState<typeof DISHES[0] | null>(null);

    const handleBuy = (dish: typeof DISHES[0]) => {
        updateProcessState({
            dish: {
                name: dish.name,
                price: dish.price,
                description: 'Selected from menu'
            }
        });
        navigate('/guest/place-order');
    };

    const formatPrice = (price: number) => {
        return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(price);
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
            <div>
                <h1 className="text-3xl font-bold text-slate-900">Menu Catalog</h1>
                <p className="text-slate-500 mt-2">Select a dish to place an order.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {DISHES.map((dish) => {
                    const Icon = dish.img;
                    return (
                        <div key={dish.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow flex flex-col">
                            <div className="h-40 bg-slate-50 flex items-center justify-center border-b border-slate-100">
                                <Icon size={64} className={dish.color.replace('bg-', 'text-').split(' ')[0]} />
                            </div>
                            <div className="p-5 flex-1 flex flex-col">
                                <h3 className="font-bold text-lg text-slate-900 mb-1">{dish.name}</h3>
                                <p className="text-slate-500 text-sm mb-4">Freshly prepared {dish.name.toLowerCase()}.</p>

                                <div className="mt-auto flex items-center justify-between">
                                    <span className="font-bold text-slate-900">{formatPrice(dish.price)}</span>
                                    <button
                                        onClick={() => handleBuy(dish)}
                                        className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-blue-200 shadow-md cursor-pointer"
                                        title="Select Dish"
                                    >
                                        <ShoppingCart size={20} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
