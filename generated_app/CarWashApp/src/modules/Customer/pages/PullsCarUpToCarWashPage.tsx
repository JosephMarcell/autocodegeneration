import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const PullsCarUpToCarWashPage = () => {
  const navigate = useNavigate();
  const { processState, updateProcessState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      pulls_car_up_to_car_wash_completed: true,
    });
    navigate('/customer/chooses-wash');
  };

  return (
    <Card title="Pulls car up to car wash" hint="Page for BPMN task 'Pulls car up to car wash' (write-navigate).">
      <Button label={`Complete: PullsCarUpToCarWash`} onClick={handleComplete} />
    </Card>
  );
};