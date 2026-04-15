import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const WheelLusterWheelCleanPage = () => {
  const navigate = useNavigate();
  const { updateProcessState, processState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      wheel_luster_wheel_clean_completed: true,
    });
    navigate('/car-wash-machine/dry');
  };

  return (
    <Card>
      <h2 className="text-lg font-bold mb-4">{processState.ui.title}</h2>
      <p className="mb-8">{processState.ui.hint}</p>
      <Button onClick={handleComplete} className="mt-4">
        Complete: Wheel Luster Wheel Clean
      </Button>
    </Card>
  );
};