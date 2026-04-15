import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const ClearCoatProtectionPage = () => {
  const navigate = useNavigate();
  const { updateProcessState, processState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      clear_coat_protection_completed: true,
    });
    navigate('/car-wash-machine/wheel-luster-wheel-clean');
  };

  return (
    <Card title="Clear Coat Protection" hint="Page for BPMN task 'Clear Coat Protection' (write-navigate).">
      <p>{processState.description}</p>
      <Button label={`Complete: Clear Coat Protection`} onClick={handleComplete} />
    </Card>
  );
};