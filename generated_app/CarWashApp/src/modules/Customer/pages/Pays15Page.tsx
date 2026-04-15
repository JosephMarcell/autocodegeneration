import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const Pays15Page = () => {
  const navigate = useNavigate();
  const { updateProcessState, processState } = useGlobalState();

  const handleCompleteClick = () => {
    updateProcessState({
      pays_15_completed: true,
      soft_cloth_wash_triggered: true
    });
    navigate('/customer/drives-away');
  };

  return (
    <Card title="Pays 15" hint="Page for BPMN task 'Pays 15' (write-navigate).">
      <Button label="Complete: Pays 15" onClick={handleCompleteClick} />
    </Card>
  );
};