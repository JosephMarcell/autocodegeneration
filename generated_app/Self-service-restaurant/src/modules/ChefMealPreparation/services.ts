export const informEmployeeService = async () => {
    console.log('Informing employee that meal is ready');
    return new Promise(resolve => setTimeout(resolve, 500));
}
