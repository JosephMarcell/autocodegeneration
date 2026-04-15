import { useNavigate } from 'react-router-dom';
import { useGlobalState, updateProcessState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const Pay8Page = () => {
  const navigate = useNavigate();
  const { processState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      pay_8_completed: true,
      soft_cloth_wash_triggered: true
    });
    navigate('/customer/drives-away');
  };

  return (
    <Card title="Pay 8" hint="Page for BPMN task 'Pay 8' (write-navigate).">
      <p>{processState.description}</p>
      <Button onClick={handleComplete} label={`Complete: Pay 8`} />
    </Card>
  );
};