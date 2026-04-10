export const setupBuzzerService = async (buzzerId: string) => {
    return new Promise(resolve => setTimeout(resolve, 500));
}

export const handoverBuzzerService = async () => {
    return new Promise(resolve => setTimeout(resolve, 500));
}

export const informChefService = async (orderId: string) => {
    console.log('Informing chef about order', orderId);
    return new Promise(resolve => setTimeout(resolve, 500));
}

export const setOffBuzzerService = async () => {
    console.log('Setting off buzzer');
    return new Promise(resolve => setTimeout(resolve, 500));
}

export const handoverMealService = async () => {
    return new Promise(resolve => setTimeout(resolve, 500));
}

export const callGuestService = async () => {
    console.log('Calling guest');
    return new Promise(resolve => setTimeout(resolve, 500));
}
