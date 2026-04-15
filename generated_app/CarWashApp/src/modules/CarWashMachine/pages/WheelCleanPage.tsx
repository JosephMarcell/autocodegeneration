import { useNavigate } from 'react-router-dom';
import { useGlobalState, updateProcessState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const WheelCleanPage = () => {
  const navigate = useNavigate();
  const { processState } = useGlobalState();

  const handleCompleteClick = () => {
    updateProcessState({
      wheel_clean_completed: true
    });
    navigate('/car-wash-machine/dry');
  };

  return (
    <Card title={processState.ui.title} hint={processState.ui.hint}>
      <Button label={`Complete: ${processState.task.name}`} onClick={handleCompleteClick} />
    </Card>
  );
};